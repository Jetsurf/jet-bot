import discord, asyncio
import mysqlhandler, nsotoken
import json, time

from .embedbuilder import S3EmbedBuilder
from .imagebuilder import S3ImageBuilder

from apscheduler.schedulers.asyncio import AsyncIOScheduler

class S3OrderView(discord.ui.View):
	def __init__(self, gear, nsoToken, showOrderButton, user, splat3info):
		super().__init__()
		self.nsoToken = nsoToken
		self.user = user
		self.confirm = False
		self.timeout = 14300.0
		self.gear = gear
		self.splat3info = splat3info

		# Add order button
		if showOrderButton:
			orderButton = discord.ui.Button(label = "Order Item", style = discord.ButtonStyle.primary)
			orderButton.callback = self.orderItem
			self.add_item(orderButton)

		# Add app button
		url = "https://s.nintendo.com/av5ja-lp1/znca/game/4834290508791808?p=/gesotown/" + gear['id']
		appButton = discord.ui.Button(label = 'NSO App', style = discord.ButtonStyle.gray, url = url)
		self.add_item(appButton)

	async def orderItem(self, interaction: discord.Interaction):
		nsoclient = await self.nsoToken.get_nso_client(self.user.id)
		if (nsoclient is None) or (not nsoclient.is_logged_in()):
			await interaction.response.send_message("Sorry, I can't order this item for you unless I have an active NSO token for you. You can use `/token` to set one up.")
			return

		req = nsoclient.s3.do_store_order(self.gear['id'], self.confirm)
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
	def __init__(self, client, nsoToken, splat3info, mysqlHandler, cachemanager, store):
		self.client = client
		self.sqlBroker = mysqlHandler
		self.nsoToken = nsoToken
		self.splat3info = splat3info
		self.scheduler = AsyncIOScheduler()
		self.cachemanager = cachemanager
		self.store = store

		store.onUpdate(self.onStoreUpdate)

	def onStoreUpdate(self, items):
		asyncio.create_task(self.doStoreDM([i['data'] for i in items]))

	##Trigger Keys: gearname brand mability
	#{ 'gearnames' : ['Gear One', "Two" ], 'brands': ['Toni-Kensa', 'Forge'], 'mabilities' : ['Ink Saver (Main)'] }
	def checkToDM(self, gear, criteria):
		brand = gear['gear']['brand']['name']
		mability = gear['gear']['primaryGearPower']['name']
		gearname = gear['gear']['name']

		if brand in criteria['brands']:
			return True
		elif mability in criteria['mabilities']:
			return True
		elif gearname in criteria['gearnames']:
			return True

		return False

	async def doStoreDM(self, items):
		async with self.sqlBroker.context() as sql:
			triggers = await sql.query("SELECT * from s3_storedms")

		for item in items:
			print(f"S3 doStoreDM(): new gear: name '{item['gear']['name']}' brand '{item['gear']['brand']['name']}' ability '{item['gear']['primaryGearPower']['name']}'")

			for trigger in triggers:
				criteria = json.loads(trigger['dmtriggers'])

				user = await self.client.fetch_user(trigger['clientid'])
				if user is None:
					continue

				if self.checkToDM(item, criteria):
					print(f"  Messaging {user.name}")
					await self.handleDM(user, item)

	async def handleDM(self, user, gear):
		# Get an NSO client for this user
		nsoclient = await self.nsoToken.get_nso_client(user.id)
		showOrderButton = False
		if (not nsoclient is None) and (nsoclient.is_logged_in()):
			showOrderButton = True

		brand = self.splat3info.brands.getItemByName(gear['gear']['brand']['name'])

		view = S3OrderView(gear, self.nsoToken, showOrderButton, user, self.splat3info)

		embed = S3EmbedBuilder.createStoreEmbed(gear, brand, "Gear you wanted to be notified about has appeared in the Splatnet 3 shop!")

		# Add gear card image as embed thumbnail
		file = None
		if gearcard_io := S3ImageBuilder.getGearCardIO(gear, self.cachemanager):
			file = discord.File(fp = gearcard_io, filename = 'gearcard.png', description = 'Gear card')
			embed.set_thumbnail(url = "attachment://gearcard.png")

		await user.send(file = file, embed = embed, view = view)
		return

	async def addS3StoreDm(self, ctx, trigger):
		cur = await self.sqlBroker.connect()
		await cur.execute("SELECT COUNT(*) FROM s3_storedms WHERE clientid = %s", (ctx.user.id,))
		count = await cur.fetchall()
		count = count[0][0]
		term = None

		if count > 0:
			await cur.execute("SELECT dmtriggers FROM s3_storedms WHERE clientid = %s AND serverid = %s", (ctx.user.id, ctx.guild.id,))
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
					term = match1.get().name()

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
					term = match2.get().name()

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
					term = match3.get().name()

		if flag == True:
			if count == 0:
				#We need to make sure DM's work, could cross check this with S2 storedm?
				try:
					#TODO - Move this to await user.create_dm() -> channel.can_send():
					chan = await ctx.user.send("This is a test to ensure that you can receive DM's. Be aware that if I am unable to DM you, I will no longer notify you of items in the store. Rerun /s3 store dm add to be readded.")
				except discord.Forbidden:
					await ctx.respond("I am unable to DM you, please check to ensure you can receive DM's from me before attempting again.", ephemeral=True)
					return

			await cur.execute("REPLACE INTO s3_storedms (clientid, serverid, dmtriggers) VALUES (%s, %s, %s)", (ctx.user.id, ctx.guild.id, json.dumps(theTriggers)))
			await self.sqlBroker.commit(cur)

			await ctx.respond(f"Added you to recieve a DM when gear with/by/named {term} appears in the Splatnet 3 store!")
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

	async def removeServerStoreDm(self, serverid):
		async with self.sqlBroker.context() as sql:
			await sql.query('DELETE FROM s3_feeds WHERE serverid = %s', (serverid, ))

	async def removeS3StoreDm(self, ctx, trigger):
		cur = await self.sqlBroker.connect()
		await cur.execute("SELECT COUNT(*) FROM s3_storedms WHERE clientid = %s", (ctx.user.id,))
		count = await cur.fetchall()
		count = count[0][0]
		if count == 0:
			await ctx.respond("You aren't set to recieve any DM's!")
			return

		await cur.execute("SELECT dmtriggers FROM s3_storedms WHERE clientid = %s AND serverid = %s", (ctx.user.id, ctx.guild.id,))
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
			await cur.execute("REPLACE INTO s3_storedms (clientid, serverid, dmtriggers) VALUES (%s, %s, %s)", (ctx.user.id, ctx.guild.id, json.dumps(theTriggers)))
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
		async with self.sqlBroker.context() as sql:
			rec = await sql.query_first("SELECT * from s3_storedms WHERE (clientid = %s)", (ctx.user.id,))

		if rec is None:
			await ctx.respond("You don't have any Splatoon 3 gear notifications set up. You can add one with `/s3 storedm add`")
			return

		triggers = json.loads(rec['dmtriggers'])

		embed = discord.Embed(colour=0x0004FF)
		embed.title = f"Splatoon 3 store notification triggers for {ctx.user.name}"

		embed.add_field(name="Ability Triggers", value="\n".join(triggers['mabilities']) if triggers['mabilities'] else "None", inline=False)
		embed.add_field(name="Brand Triggers", value="\n".join(triggers['brands']) if triggers['brands'] else "None", inline=False)
		embed.add_field(name="Gear Triggers", value="\n".join(triggers['gearnames']) if triggers['gearnames'] else "None", inline=False)

		await ctx.respond(embed=embed)
