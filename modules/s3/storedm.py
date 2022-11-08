import discord, asyncio
import mysqlhandler, nsotoken, s3handler
import json, time

from .embedbuilder import S3EmbedBuilder

from apscheduler.schedulers.asyncio import AsyncIOScheduler

class s3OrderView(discord.ui.View):
	def __init__(self, gear, s3handler, nsotoken, user, splat3info):
		super().__init__()
		self.nsoToken = nsotoken
		self.s3Handler = s3handler
		self.user = user
		self.confirm = False
		self.timeout = 14300.0
		self.gear = gear
		self.splat3info = splat3info

	async def initView(self):
		orderBut = discord.ui.Button(label="Order Item")
		self.nso = await self.nsoToken.get_nso_client(self.user.id)
		if self.nso.is_logged_in():
			orderBut.callback = self.orderItem
		else:
			self.stop()
			return None
		self.add_item(orderBut)

	async def orderItem(self, interaction: discord.Interaction):
		req = self.nso.s3.do_store_order(self.gear['id'], self.confirm)
		if req['data']['orderGesotownGear']['userErrors'] == None:
			await interaction.response.send_message("Ordered!")
			self.clear_items()
			self.stop()
		elif req['data']['orderGesotownGear']['userErrors'][0]['code'] == "GESOTOWN_ALREADY_ORDERED":
			await interaction.response.send_message("You already have an item on order, hit order again to cancel that item and order this one.")
			self.confirm = True
		else:
			#TODO Update this
			await interaction.response.send_message("Something went wrong.")

class S3StoreHandler():
	def __init__(self, client, nsoToken, splat3info, mysqlHandler, configData):
		self.client = client
		self.sqlBroker = mysqlHandler
		self.nsotoken = nsoToken
		self.splat3info = splat3info
		self.scheduler = AsyncIOScheduler()
		self.configData = configData
		if 'storedm_debug' in configData and configData['storedm_debug']:
			self.scheduler.add_job(self.doStoreRegularDM, 'cron', second = "0", timezone = 'UTC') 
			self.scheduler.add_job(self.doStoreDailyDropDM, 'cron', second = '0', timezone = 'UTC')
		else:
			self.scheduler.add_job(self.doStoreRegularDM, 'cron', hour="*/4", minute='1', timezone = 'UTC') 
			self.scheduler.add_job(self.doStoreDailyDropDM, 'cron', hour="0", minute='1', timezone='UTC')

		self.scheduler.add_job(self.cacheS3JSON, 'cron', hour="*/4", minute='0', second='15', timezone='UTC')
		self.storecache = None
		self.cacheState = False
		self.scheduler.start()

	async def cacheS3JSON(self):
		print("Updating cached S3 json...")
		nso = await self.nsotoken.get_bot_nso_client()

		storejson = nso.s3.get_store_items()
		if storejson is None:
			print("Failure on store cache refresh. Trying again...")
			time.sleep(3) #Give it a bit to try again...
			storejson = nso.s3.get_store_items() #Done 2nd time for 9403 errors w/ token generation
			if storejson is None:
				print("Failed to update store cache for rotation")
				self.cacheState = False
				return
		
		print("Got store cache for this rotation")
		self.storecache = storejson['data']['gesotown']
		self.cacheState = True

	##Trigger Keys: gearname brand mability
	#{ 'gearnames' : ['Gear One', "Two" ], 'brands': ['Toni-Kensa', 'Forge'], 'mabilities' : ['Ink Saver (Main)'] }

	def checkToDM(self, gear, triggers):
		brand = gear['gear']['brand']['name']
		mability = gear['gear']['primaryGearPower']['name']
		gearname = gear['gear']['name']

		for trigger in triggers.values():
			if brand in trigger:
				return True
			if mability in trigger:
				return True
			if gearname in trigger:
				return True
			
		return False

	async def doStoreDailyDropDM(self):
		theDrop = self.storecache['pickupBrand']
		theItems = self.storecache['pickupBrand']['brandGears']
		
		cur = await self.sqlBroker.connect()
		await cur.execute("SELECT * from s3storedms")
		toDM = await cur.fetchall()
		await self.sqlBroker.close(cur)

		print(f"Doing Daily Drop S3 Store DM. Checking:")

		for gear in theItems:
			print(f"Gear: {gear['gear']['name']} Brand: {gear['gear']['brand']['name']} Ability: {gear['gear']['primaryGearPower']['name']}")
			for id in range(len(toDM)):
				servid = toDM[id][0]
				memid = toDM[id][1]
				triggers = json.loads(toDM[id][2])
				server = self.client.get_guild(int(servid))

				await server.chunk()
				theMem = server.get_member(int(memid))
				if theMem is None:
					continue
				elif self.checkToDM(gear, triggers):
					print(f"Messaging {theMem.name}")
					asyncio.ensure_future(self.handleDM(theMem, gear))

		return

	async def handleDM(self, user, gear):
		brand = self.splat3info.brands.getItemByName(gear['gear']['brand']['name'])

		view = s3OrderView(gear, self, self.nsotoken, user, self.splat3info)
		await view.initView()
		#def createStoreEmbed(self, gear, brand, title, configData, instructions = None):
		embed = s3handler.S3EmbedBuilder.createStoreEmbed(gear, brand, "Gear you wanted to be notified about has appeared in the Splatnet 3 shop!", self.configData)
		await user.send(embed = embed, view = view)

	async def doStoreRegularDM(self):
		if not self.cacheState:
			print("Cache was not updated... skipping this daily drop...")
			return

		theGear = self.storecache['limitedGears'][5]
		cur = await self.sqlBroker.connect()

		print(f"Doing S3 Store DM. Checking {theGear['gear']['name']} Brand: {theGear['gear']['brand']['name']} Ability: {theGear['gear']['primaryGearPower']['name']}")
		
		await cur.execute("SELECT * FROM s3storedms")
		toDM = await cur.fetchall()
		await self.sqlBroker.close(cur)

		for id in range(len(toDM)):
			servid = toDM[id][0]
			memid = toDM[id][1]
			triggers = json.loads(toDM[id][2])
			server = self.client.get_guild(int(servid))

			await server.chunk()
			theMem = server.get_member(int(memid))
			if theMem is None:
				continue
			elif self.checkToDM(theGear, triggers):
				print(f"Messaging {theMem.name}")
				asyncio.ensure_future(self.handleDM(theMem, theGear))

	async def addS3StoreDm(self, ctx, trigger):
		cur = await self.sqlBroker.connect()
		await cur.execute("SELECT COUNT(*) FROM s3storedms WHERE clientid = %s", (ctx.user.id,))
		count = await cur.fetchall()
		count = count[0][0]
		if count > 0:
			await cur.execute("SELECT dmtriggers FROM s3storedms WHERE clientid = %s AND serverid = %s", (ctx.user.id, ctx.guild.id,))
			theTriggers = await cur.fetchall()
			theTriggers = json.loads(theTriggers[0][0])
		else:
			theTriggers = { 'mabilities' : [], 'brands' : [], 'gearnames' : [] }

		flag = False		
		#Search abilities
		if flag != True:
			match1 = self.splat3info.abilities.matchItem(trigger)
			if match1.isValid():
				flag = True
				if match1.get().name() in theTriggers['mabilities']:
					await self.sqlBroker.close(cur)
					await ctx.respond(f"You're already recieving DM's when gear with {match2.get().name()} appears in the store.")
					return
				else:
					theTriggers['mabilities'].append(match1.get().name())

		#Search brands
		if flag != True:
			match2 = self.splat3info.brands.matchItem(trigger)
			if match2.isValid():
				flag = True
				if match2.get().name() in theTriggers['brands']:
					await self.sqlBroker.close(cur)
					await ctx.respond(f"You're already recieving DM's when gear by {match2.get().name()} appears in the store.")
					return
				else:
					theTriggers['brands'].append(match2.get().name())

		#Search Items
		if flag != True:
			match3 = self.splat3info.gear.matchItem(trigger)
			if match3.isValid():
				flag = True
				if match3.get().name() in theTriggers['brands']:
					await self.sqlBroker.close(cur)
					await ctx.respond(f"You're already recieving DM's when {match2.get().name()} appears in the store.")
					return
				else:
					theTriggers['gearnames'].append(match3.get().name())

		if flag == True:
			if count == 0:
				#We need to make sure DM's work, could cross check this with S2 storedm?
				try:
					chan = await ctx.user.send("This is a test to ensure that you can receive DM's. Be aware that if I am unable to DM you, I will no longer notify you of items in the store. Rerun /store dm add to be readded.")
				except discord.Forbidden:
					await ctx.respond("I am unable to DM you, please check to ensure you can receive DM's from me before attempting again.", ephemeral=True)
					return

			await cur.execute("REPLACE INTO s3storedms (clientid, serverid, dmtriggers) VALUES (%s, %s, %s)", (ctx.user.id, ctx.guild.id, json.dumps(theTriggers)))
			await self.sqlBroker.commit(cur)

			await ctx.respond(f"Added you to recieve a DM when gear with/by/named {trigger} appears in the Splatnet 3 store!")
		else:
			await self.sqlBroker.close(cur)
			if len(match1.items) + len(match2.items) + len(match3.items) < 1:
				await ctx.respond("Didn't find any partial matches for you.")
				return

			embed = discord.Embed(colour=0xF9FC5F)
			embed.title = "Did you mean?"

			if len(match1.items) > 0:
				embed.add_field(name="Abilities", value=", ".join(map(lambda item: item.name(), match1.items)), inline=False)
			if len(match2.items) > 0:
				embed.add_field(name="Brands", value=", ".join(map(lambda item: item.name(), match2.items)), inline=False)
			if len(match3.items) > 0:
				embed.add_field(name="Gear", value=", ".join(map(lambda item: item.name(), match3.items)), inline=False)

			await ctx.respond(embed=embed)

	async def removeS3StoreDm(self, ctx, trigger):
		cur = await self.sqlBroker.connect()
		await cur.execute("SELECT COUNT(*) FROM s3storedms WHERE clientid = %s", (ctx.user.id,))
		count = await cur.fetchall()
		count = count[0][0]
		if count == 0:
			await ctx.respond("You aren't set to recieve any DM's!")
			return

		await cur.execute("SELECT dmtriggers FROM s3storedms WHERE clientid = %s AND serverid = %s", (ctx.user.id, ctx.guild.id,))
		theTriggers = await cur.fetchall()
		theTriggers = json.loads(theTriggers[0][0])

		flag = False		
		#Search abilities
		if flag != True:
			match1 = self.splat3info.abilities.matchItem(trigger)
			if match1.isValid():
				flag = True
				if match1.get().name() in theTriggers['mabilities']:
					theTriggers['mabilities'].remove(match1.get().name())
				else:
					await self.sqlBroker.close(cur)
					await ctx.respond(f"You aren't set to recieve DM's when gear with {match1.get().name()} appears in the store.")
					return

		#Search brands
		if flag != True:
			match2 = self.splat3info.brands.matchItem(trigger)
			if match2.isValid():
				flag = True
				if match2.get().name() in theTriggers['brands']:
					theTriggers['brands'].remove(match2.get().name())
				else:
					await self.sqlBroker.close(cur)
					await ctx.respond(f"You aren't set to recieve DM's when gear by {match2.get().name()} appears in the store.")
					return

		#Search Items
		if flag != True:
			match3 = self.splat3info.gear.matchItem(trigger)
			if match3.isValid():
				flag = True
				if match3.get().name() in theTriggers['gearnames']:
					theTriggers['gearnames'].remove(match3.get().name())
				else:
					await self.sqlBroker.close(cur)
					await ctx.respond(f"You aren't set to recieve DM's when {match3.get().name()} appears in the store.")
					return

		if flag == True:
			await cur.execute("REPLACE INTO s3storedms (clientid, serverid, dmtriggers) VALUES (%s, %s, %s)", (ctx.user.id, ctx.guild.id, json.dumps(theTriggers)))
			await self.sqlBroker.commit(cur)

			await ctx.respond(f"Removed you from recieving a DM when gear with/by/named {trigger} appears in the Splatnet 3 store!")
		else:
			await self.sqlBroker.close(cur)
			if len(match1.items) + len(match2.items) + len(match3.items) < 1:
				await ctx.respond("Didn't find any partial matches for you.")
				return

			embed = discord.Embed(colour=0xF9FC5F)
			embed.title = "Did you mean?"

			if len(match1.items) > 0:
				embed.add_field(name="Abilities", value=", ".join(map(lambda item: item.name(), match1.items)), inline=False)
			if len(match2.items) > 0:
				embed.add_field(name="Brands", value=", ".join(map(lambda item: item.name(), match2.items)), inline=False)
			if len(match3.items) > 0:
				embed.add_field(name="Gear", value=", ".join(map(lambda item: item.name(), match3.items)), inline=False)

			await ctx.respond(embed=embed)

	async def listS3StoreDm(self, ctx):
		cur = await self.sqlBroker.connect()
		await cur.execute("SELECT dmtriggers FROM s3storedms WHERE clientid = %s", (ctx.user.id,))
		triggers = await cur.fetchall()
		await self.sqlBroker.close(cur)

		embed = discord.Embed(colour=0x0004FF)
		embed.title = f"Splatoon 3 store dm triggers for {ctx.user.name}"

		triggers = json.loads(triggers[0][0])

		embed.add_field(name="Ability Triggers", value="\n".join(triggers['mabilities']) if triggers['mabilities'] else "None", inline=False)
		embed.add_field(name="Brand Triggers", value="\n".join(triggers['brands']) if triggers['brands'] else "None", inline=False)
		embed.add_field(name="Gear Triggers", value="\n".join(triggers['gearnames']) if triggers['gearnames'] else "None", inline=False)

		await ctx.respond(embed=embed)
