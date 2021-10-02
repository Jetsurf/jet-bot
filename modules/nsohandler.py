import discord, asyncio
import mysqlhandler, nsotoken
import time, requests
import json, os
import urllib, urllib.request
import splatinfo
import messagecontext
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord.app import *

class nsoHandler():
	def __init__(self, client, mysqlHandler, nsotoken, splatInfo, cmdOrder):
		self.client = client
		self.splatInfo = splatInfo
		self.sqlBroker = mysqlHandler
		self.cmdOrder = cmdOrder
		self.app_timezone_offset = str(int((time.mktime(time.gmtime()) - time.mktime(time.localtime()))/60))
		self.scheduler = AsyncIOScheduler()
		self.scheduler.add_job(self.doStoreDM, 'cron', hour="*/2", minute='5') 
		self.scheduler.add_job(self.updateS2JSON, 'cron', hour="*/2", minute='0', second='15')
		self.scheduler.add_job(self.doFeed, 'cron', hour="*/2", minute='0', second='25')
		self.scheduler.start()
		self.mapJSON = None
		self.storeJSON = None
		self.srJSON= None
		self.nsotoken = nsotoken
		self.app_head = {
			'Host': 'app.splatoon2.nintendo.net',
			'x-unique-id': '8386546935489260343',
			'x-requested-with': 'XMLHttpRequest',
			'x-timezone-offset': self.app_timezone_offset,
			'User-Agent': 'Mozilla/5.0 (Linux; Android 7.1.2; Pixel Build/NJH47D; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/59.0.3071.125 Mobile Safari/537.36',
			'Accept': '*/*',
			'Referer': 'https://app.splatoon2.nintendo.net/home',
			'Accept-Encoding': 'gzip, deflate',
			'Accept-Language': 'en-us'
		}
		self.app_head_shop = {
 		   "origin": "https://app.splatoon2.nintendo.net",
    		"x-unique-id": '16131049444609162796',
    		"x-requested-with": "XMLHttpRequest",
    		"x-timezone-offset": self.app_timezone_offset,
    		"User-Agent": "Mozilla/5.0 (Linux; Android 7.1.2; Pixel Build/NJH47D; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/59.0.3071.125 Mobile Safari/537.36",
    		"Accept": "*/*",
    		"Referer": "https://app.splatoon2.nintendo.net/results",
    		"Accept-Encoding": "gzip, deflate",
    		"Accept-Language": "en-US"
		}
		self.app_head_coop = {
			'Host': 'app.splatoon2.nintendo.net',
			'x-unique-id': '8386546935489260343',
			'x-requested-with': 'XMLHttpRequest',
			'x-timezone-offset': self.app_timezone_offset,
			'User-Agent': 'Mozilla/5.0 (Linux; Android 7.1.2; Pixel Build/NJH47D; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/59.0.3071.125 Mobile Safari/537.36',
			'Accept': '*/*',
			'Referer': 'https://app.splatoon2.nintendo.net/coop',
			'Accept-Encoding': 'gzip, deflate',
			'Accept-Language': 'en-us'
		}

	async def doFeed(self):
		cur = await self.sqlBroker.connect()
		stmt = "SELECT * FROM feeds"
		feeds = await cur.execute(stmt)
		feeds = await cur.fetchall()
		print(f"Processing: {str(len(feeds))} feeds")

		for server in range(len(feeds)):
			serverid = feeds[server][0]
			channelid = feeds[server][1]
			mapflag = feeds[server][2]
			srflag = feeds[server][3]
			gearflag = feeds[server][4]

			theServer = self.client.get_guild(serverid)
			if theServer == None:
				continue

			theChannel = theServer.get_channel(channelid)
			if theChannel is None:
				continue;

			await theChannel.send(embed=await self.make_notification(bool(mapflag), bool(srflag), bool(gearflag)))

		await self.sqlBroker.close(cur)

	async def make_notification(self, mapflag, srflag, gearflag):
		embed = discord.Embed(colour=0x3FFF33)
		embed.title = "Rotation Feed"

		if mapflag:
			data = self.maps(offset=0)
			turf = data['turf']
			ranked = data['ranked']
			league = data['league']

			embed.add_field(name="Maps", value="Maps currently on rotation", inline=False)
			embed.add_field(name="<:turfwar:550107083911987201> Turf War", value=f"{turf['stage_a']['name']}\n{turf['stage_b']['name']}", inline=True)
			embed.add_field(name=f"<:ranked:550107084684001350> Ranked: {ranked['rule']['name']}", value=f"{ranked['stage_a']['name']}\n{ranked['stage_b']['name']}", inline=True)
			embed.add_field(name=f"<:league:550107083660328971> League: {league['rule']['name']}", value=f"{league['stage_a']['name']}\n{league['stage_b']['name']}", inline=True)

		if srflag:
			flag = 0
			srdata = self.srParser()
			if srdata == None:
				srdata = self.srParser(getNext=True)
				flag = 1

			days = srdata['days']
			hours = srdata['hours']
			mins = srdata['mins']

			if flag == 1:
				titleval = 'Next SR Rotation'
				timename = 'Time Remaining for SR Rotation'
			else:
				titleval = 'Current SR Rotation'
				timename = 'Time Until SR Rotation'
			#TODO Check this
			embed.add_field(name="Salmon Run", value=titleval, inline=False)
			embed.add_field(name='Map', value=srdata['map']['name'], inline=True)
			embed.add_field(name='Weapons', value=srdata['weapons'].replace('\n', ', ', 3), inline=True)
			embed.add_field(name=timename, value=f"{str(days)} Days, {str(hours)} Hours, and {str(mins)} Minutes", inline=False)

		if gearflag:
			gear = await self.gearParser(flag=1)
			embed.add_field(name="Gear", value="Gear on rotation", inline=False)
			embed.add_field(name=f"**{gear['gear']['name']}**", value=f"{gear['gear']['brand']['name']} : {gear['kind']}", inline=False)
			embed.add_field(name="ID/Subs/Price", value=f"5/{str(gear['gear']['rarity'] + 1)}/{str(gear['price'])}", inline=True)
			if 'frequent_skill' in gear['gear']['brand']:
				embed.add_field(name="Ability/Common Sub", value=f"{gear['skill']['name']}/{gear['gear']['brand']['frequent_skill']['name']}", inline=True)
			else:
				embed.add_field(name="Ability/Common Sub", value=f"{gear['skill']['name']}/None", inline=True)

		return embed

	async def updateS2JSON(self):
		useragent = { 'User-Agent' : 'jet-bot/1.0 (discord:jetsurf#8514)' }
		print("S2JSON CACHE: Updating...")
		#Do store JSON update
		req = urllib.request.Request('https://splatoon2.ink/data/merchandises.json', headers=useragent)
		response = urllib.request.urlopen(req)
		self.storeJSON = json.loads(response.read().decode())
		#Do maps JSON update
		req = urllib.request.Request('https://splatoon2.ink/data/schedules.json', headers=useragent)
		response = urllib.request.urlopen(req)
		self.mapsJSON = json.loads(response.read().decode())
		#Do sr JSON update
		req = urllib.request.Request('https://splatoon2.ink/data/coop-schedules.json', headers=useragent)
		response = urllib.request.urlopen(req)
		self.srJSON = json.loads(response.read().decode())

		#TODO: This ideally will be for updating the order command with choices to contain current gear in the store, have to wait for pycord to progress
		if False:
			print("DEBUG: Updating gear for order command")
			for cmd in await self.client.http.get_global_commands(application_id=self.client.user.id):
				if cmd['name'] != 'order':
					continue;
				else:
					orderid = cmd['id']
					print(f"{str(cmd)}")
					print(f"{str(cmd['id'])}")
			list1 = []
			for item in self.storeJSON['merchandises']:
				gear = item['gear']
				theHash = {}
				theHash['name'] = str(gear['name'])
				theHash['value'] = str(gear['name'])
				list1.append(theHash)

			print(f'LIST1 {str(list1)}')
			payload = { 'options': [ {'type': 3, 'name': 'id', 'description': 'ID of gear to order (get this from splatnetgear command) (0-5)', 'required': True, 'choices': list1 } ] }
			print(f"{str(payload.items())}")
			await self.client.http.edit_global_command(application_id=self.client.user.id, command_id=orderid, payload=payload)
			await self.client.register_commands()

	async def addStoreDM(self, ctx, args, is_slash=False):
		if len(args) == 0:
			await ctx.respond("I need an item/brand/ability to search for!")
			return

		term = " ".join(args).lower()

		flag = False

		#Search Abilities
		if flag != True: #Pre-emptive for adding in pure gear
			match1 = self.splatInfo.matchAbilities(term)			
			if match1.isValid():
				flag = True
				term = match1.get().name()

		#Search brands
		if flag != True:
			match2 = self.splatInfo.matchBrands(term)
			if match2.isValid():
				flag = True
				term = match2.get().name()

		#Search Items
		match3 = None
		if flag != True:
			match3 = self.splatInfo.matchGear(term)
			if match3.isValid():
				flag = True
				term = match3.get().name()
	
		if not flag:
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
			return

		if match3 != None:
			if match3.isValid() and match3.get().price() == 0:
				await ctx.respond(f"{match3.get().name()} won't appear on the store. Here is where to get it: {match3.get().source()}")
				return

		cur = await self.sqlBroker.connect()

		if match1.isValid():
			stmt = "SELECT COUNT(*) FROM storedms WHERE clientid = %s AND ability = %s"
		elif match2.isValid():
			stmt = "SELECT COUNT(*) FROM storedms WHERE clientid = %s AND brand = %s"
		else:
			stmt = "SELECT COUNT(*) FROM storedms WHERE clientid = %s AND gearname = %s"

		await cur.execute(stmt, (str(ctx.user.id), term,))
		count = await cur.fetchone()
		if count[0] > 0:
			if match1.isValid():
				await ctx.respond(f"You will already be DM'ed when gear with ability {term} appears in the shop.")
			elif match2.isValid():
				await ctx.respond(f"You will already be DM'ed when gear by brand {term} appears in the shop.")
			else:
				await ctx.respond(f"You will already be DM'ed when {term} appears in the shop.")

			await self.sqlBroker.close(cur)
			return
		else:
			if not is_slash:
				def check2(m):
					return m.author == message.author and m.channel == message.channel

				if match1.isValid():
					await ctx.respond(f"{ctx.user.name} do you want me to DM you when gear with ability {term} appears in the shop? (Respond Yes/No)")
				elif match2.isValid():
					await ctx.respond(f"{ctx.user.name} do you want me to DM you when gear by brand {term} appears in the shop? (Respond Yes/No)")
				else:
					await ctx.respond(f"{ctx.user.name} do you want me to DM you when {term} appears in the shop? (Respond Yes/No)")

				resp = await self.client.wait_for('message', check=check2)
				if 'yes' not in resp.content.lower():
					await ctx.respond("Ok, I haven't added you to receive a DM.")
					return

		if match1.isValid():
			stmt = 'INSERT INTO storedms (clientid, serverid, ability) VALUES(%s, %s, %s)'
		elif match2.isValid():
			stmt = 'INSERT INTO storedms (clientid, serverid, brand) VALUES(%s, %s, %s)'
		else:
			stmt = 'INSERT INTO storedms (clientid, serverid, gearname) VALUES(%s, %s, %s)'

		await cur.execute(stmt, (str(ctx.user.id), str(ctx.guild.id), term,))
		await self.sqlBroker.commit(cur)

		if match1.isValid():
			await ctx.respond(f"Added you to recieve a DM when gear with {term} appears in the shop!")
		elif match2.isValid():
			await ctx.respond(f"Added you to recieve a DM when gear by brand {term} appears in the shop!")
		elif match3.isValid():
			await ctx.respond(f"Added you to recieve a DM when {term} appears in the shop!")

	async def removeStoreDM(self, ctx, args):
		if len(args) == 0:
			await ctx.respond("I need an item/brand/ability to search for!")
			return

		term = " ".join(args).lower()

		flag = False

		#Search Abilities
		if flag != True: #Pre-emptive for adding in pure gear
			match1 = self.splatInfo.matchAbilities(term)			
			if match1.isValid():
				flag = True
				term = match1.get().name()

		#Search brands
		if flag != True:
			match2 = self.splatInfo.matchBrands(term)
			if match2.isValid():
				flag = True
				term = match2.get().name()

		#Search Items
		match3 = None
		if flag != True:
			match3 = self.splatInfo.matchGear(term)
			if match3.isValid():
				flag = True
				term = match3.get().name()
	
		if not flag:
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
			return

		if match3 != None:
			if match3.isValid() and match3.get().price() == 0:
				await ctx.respond(f"{match3.get().name()} won't appear on the store. Here is where to get it: {match3.get().source()}")
				return

		cur = await self.sqlBroker.connect()

		if match1.isValid():
			stmt = "SELECT COUNT(*) FROM storedms WHERE clientid = %s AND ability = %s"
		elif match2.isValid():
			stmt = "SELECT COUNT(*) FROM storedms WHERE clientid = %s AND brand = %s"
		else:
			stmt = "SELECT COUNT(*) FROM storedms WHERE clientid = %s AND gearname = %s"

		await cur.execute(stmt, (str(ctx.user.id), term,))
		count = await cur.fetchone()
		if count[0] > 0:
			if match1.isValid():
				stmt = 'DELETE FROM storedms WHERE clientid=%s AND ability=%s'
			elif match2.isValid():
				stmt = 'DELETE FROM storedms WHERE clientid=%s AND brand=%s'
			else:
				stmt = 'DELETE FROM storedms WHERE clientid=%s AND gearname=%s'	
		else:
			if match1.isValid():
				await ctx.respond(f"Doesn't look like you are set to receive a DM when gear with {term} appears in the store.")
			elif match2.isValid():
				await ctx.respond(f"Doesn't look like you are set to receive a DM when gear by {term} appears in the store.")
			else:
				await ctx.respond(f"Doesn't look like you are set to receive a DM when {term} appears in the store.")
			return

		await cur.execute(stmt, (str(ctx.user.id), term,))
		await self.sqlBroker.commit(cur)

		if match1.isValid():
			await ctx.respond(f"Removed you from recieving a DM when gear with {term} appears in the store.")
		elif match2.isValid():
			await ctx.respond(f"Removed you from recieving a DM when gear by brand {term} appears in the store.")
		else:
			await ctx.respond(f"Removed you from recieving a DM when {term} appears in the store.")	

			
	async def listStoreDM(self, ctx):
		cur = await self.sqlBroker.connect()

		stmt1 = "SELECT ability FROM storedms WHERE clientid = %s"
		stmt2 = "SELECT brand FROM storedms WHERE clientid = %s"
		stmt3 = "SELECT gearname FROM storedms WHERE clientid = %s"

		await cur.execute(stmt1, (str(ctx.user.id),))
		abilities = await cur.fetchall()
		await cur.execute(stmt2, (str(ctx.user.id),))
		brands = await cur.fetchall()
		await cur.execute(stmt3, (str(ctx.user.id),))
		gear = await cur.fetchall()

		embed = discord.Embed(colour=0x0004FF)
		embed.title = f"Storedm triggers for {ctx.user.name}"

		ablString = ""
		for abl in abilities:
			if abl[0] != None:
				ablString += f"{abl[0]}\n"

		brandString = ""
		for brnd in brands:
			if brnd[0] != None:
				brandString += f"{brnd[0]}"

		gearString = ""
		for gr in gear:
			if gr[0] != None:
				gearString += f"{gr[0]}"

		embed.add_field(name="Ability Triggers", value= ablString if ablString != '' else "None", inline=False)
		embed.add_field(name="Brand Triggers", value=brandString if brandString != '' else "None", inline=False)
		embed.add_field(name="Gear Triggers", value=gearString if gearString != '' else "None", inline=False)

		await ctx.respond(embed=embed)

	async def handleDM(self, theMem, theGear):
		def checkDM(m):
			return m.author.id == theMem.id and m.guild == None

		theSkill = theGear['skill']['name']
		theType = theGear['gear']['name']
		theBrand = theGear['gear']['brand']['name']

		embed = self.makeGearEmbed(theGear, "Gear you wanted to be notified about has appeared in the shop!", "Respond with 'order' to order, or 'stop' to stop recieving notifications (within the next two hours)")
		try:
			await theMem.send(embed=embed)
		except discord.errors.Forbidden:
			print(f"Forbidden from messaging user {str(theMem.id)}, removing from DMs")
			cur = await self.sqlBroker.connect()
			stmt = "DELETE FROM storedms WHERE clientid = %s"
			await cur.execute(stmt, (theMem.id,))
			await self.sqlBroker.commit(cur)
			print(f"Removed {str(theMem.id)} from storedm")
			return

		print(f"Messaged {theMem.name}")

		def check1(m):
			return True if isinstance(m.channel, discord.channel.DMChannel) and m.author.name == theMem.name and not m.author.bot else False
				
		# Discord.py changed timeouts to throw exceptions...
		try:
			resp = await self.client.wait_for('message', timeout=7100, check=check1)
		except:
			return

		cur = await self.sqlBroker.connect()
		if 'stop' in resp.content.lower():
			stmt = "SELECT COUNT(*) FROM storedms WHERE (clientid = %s) AND ((ability = %s) OR (brand = %s) OR (gearname = %s))"
			await cur.execute(stmt, (theMem.id, theSkill, theBrand, theType, ))
			count = await cur.fetchone()
			if count[0] > 1:
				while True:
					stmt = 'SELECT ability, brand, gearname FROM storedms WHERE (clientid = %s) AND ((ability = %s) OR (brand = %s) OR (gearname = %s))'
					await cur.execute(stmt, (theMem.id, theSkill, theBrand, theType, ))
					fields = await cur.fetchall()
					abilFlag = False
					branFlag = False
					gearFlag = False
					string = "You have multiple flags from this item to notify you on, which of the following would you like to remove? ("
					for i in fields:
						if i[0] != None:
							abilFlag = True
							string+=f"{theSkill}/"
						if i[1] != None:
							branFlag = True
							string+=f"{theBrand}/"
						if i[2] != None:
							gearFlag = True
							string+=f"{theType}/"

					string+= "all/quit to stop removing DM triggers)"

					await theMem.send(string)
					try:
						confirm = await self.client.wait_for('message', timeout=5, check=checkDM)
					except:
						await theMem.send("Didn't get a response from you on DM flags")
						break
					if confirm.content.lower() == theSkill.lower() and abilFlag:
						stmt = 'DELETE FROM storedms WHERE (clientid = %s) AND (ability = %s)'
						await cur.execute(stmt, (theMem.id, theSkill, ))
						abilFlag = False
						await theMem.send(f"Ok, removed you from being DM'ed when gear with ability {theSkill} appears in the shop!")
					elif confirm.content.lower() == theBrand.lower() and branFlag:
						stmt = 'DELETE FROM storedms WHERE (clientid = %s) AND (brand = %s)'
						await cur.execute(stmt, (theMem.id, theBrand, ))
						branFlag = False
						await theMem.send(f"Ok, removed you from being DM'ed when gear by brand {theBrand} appears in the shop!")
					elif confirm.content.lower() == theType.lower() and abilFlag:
						stmt = 'DELETE FROM storedms WHERE (clientid = %s) AND (gearname = %s)'
						await cur.execute(stmt, (theMem.id, theType, ))
						await self.sqlBroker.commit(cur)
						gearFlag = False
						await theMem.send(f"Ok, removed you from being DM'ed when {theAbility} appears in the shop!")
					elif confirm.content.lower() == 'all':
						stmt = 'DELETE FROM storedms WHERE (clientid = %s) AND ((ability = %s) OR (brand = %s) OR (gearname = %s))'
						await cur.execute(stmt, (theMem.id, theSkill, theBrand, theType, ))
						await theMem.send("Ok removed you from all flags to be DM'ed on associated with this item")
						break
					elif confirm.content.lower() == 'quit':
						await theMem.send("Ok, stopping removal of DM flags!")
						break
					else:
						await theMem.send("Didn't understand that")

					if not abilFlag and not branFlag and not gearFlag:
						await theMem.send("Ok, no more flags on this item to DM you on!")
						break
				await self.sqlBroker.commit(cur)
			else:
				stmt = 'SELECT ability, brand, gearname FROM storedms WHERE (clientid = %s) AND ((ability = %s) OR (brand = %s) OR (gearname = %s))'
				await cur.execute(stmt, (theMem.id, theSkill, theBrand, theType, ))
				fields = await cur.fetchone()
				if fields[0] != None:
					await theMem.send(f"Ok, I won't DM you again when gear with ability {theSkill} appears in the shop.")
				elif fields[1] != None:
					await theMem.send(f"Ok, I won't DM you again when gear by {theBrand} appears in the shop.")
				else:
					await theMem.send(f"Ok, I won't DM you again when {theType} appears in the shop.")

				stmt = 'DELETE FROM storedms WHERE (clientid = %s) AND ((ability = %s) OR (brand = %s) OR (gearname = %s))'

				await cur.execute(stmt, (theMem.id, theSkill, theBrand, theType, ))
				await self.sqlBroker.commit(cur)

		elif 'order' in resp.content.lower():
			await self.sqlBroker.close(cur)
			context = messagecontext.MessageContext(resp)
			print(f"Ordering gear for: {str(context.user.name)}")
			await self.orderGearCommand(context, order=5, is_slash=False, override=True)
		else:
			#Response but nothing understood
			print(f"Keeping {theMem.name} in DM's")
			stmt = 'SELECT ability, brand, gearname FROM storedms WHERE (clientid = %s) AND ((ability = %s) OR (brand = %s) OR (gearname = %s))'
			await cur.execute(stmt, (theMem.id, theSkill, theBrand, theType, ))
			fields = await cur.fetchall()
			string = "Didn't understand that. The item I notified you about will be on the store for another 10 hours. I'll DM you again when gear with "
			for i in fields:
				if i[0] != None:
					string+=theSkill + ", "
				if i[1] != None:
					string+=theBrand + ", "
				if i[2] != None:
					string+=theType + ", "

			string = "".join(string.rsplit(", ", 1)) + " appears in the shop"
			string = " or ".join(string.rsplit(", ", 1))
			await theMem.send(string)

	async def doStoreDM(self):
		cur = await self.sqlBroker.connect()
		theGear = self.storeJSON['merchandises'][5]

		theSkill = theGear['skill']['name']
		theType = theGear['gear']['name']
		theBrand = theGear['gear']['brand']['name']
		print(f"Doing Store DM! Checking {theType} Brand: {theBrand} Ability: {theSkill}")

		stmt = "SELECT DISTINCT clientid,serverid FROM storedms WHERE (ability = %s) OR (brand = %s) OR (gearname = %s)"
		await cur.execute(stmt, (theSkill, theBrand, theType,))
		toDM = await cur.fetchall()
		await self.sqlBroker.close(cur)

		for id in range(len(toDM)):
			memid = toDM[id][0]
			servid = toDM[id][1]

			server = self.client.get_guild(int(servid))

			await server.chunk()
			#THIS NEEDS IMPROVEMENT
			theMem = server.get_member(int(memid))
			if theMem is None:
				print(f"Suggested cleanup on user: {str(memid)}")
				continue

			asyncio.ensure_future(self.handleDM(theMem, theGear))

	async def getStoreJSON(self, ctx):
		theGear = self.storeJSON['merchandises'][5]
		await ctx.respond(f"```{str(theGear)}```")

	#TODO: Convert this owner only command
	async def getRawJSON(self, message):
		if not await self.checkDuplicate(message.author.id):
			await message.channel.send("You don't have a token setup with me! Please DM me !token with how to get one setup!")
			return

		Session_token = await self.nsotoken.get_iksm_token_mysql(message.author.id)

		if 'base' in message.content:
			url = "https://app.splatoon2.nintendo.net/api/records"
			jsontype = 'base'
			header = self.app_head
		elif 'sr' in message.content:
			url = "https://app.splatoon2.nintendo.net/api/coop_results"
			jsontype = 'sr'
			header = self.app_head_coop
		elif 'fullbattle' in message.content:
			num = message.content[20:]
			url = f"https://app.splatoon2.nintendo.net/api/results/{num}"
			header = self.app_head
			jsontype = f"fullbattle{num}"
		elif 'battle' in message.content:
			url = "https://app.splatoon2.nintendo.net/api/results"
			jsontype = 'battle'
			header = self.app_head

		results_list = requests.get(url, headers=header, cookies=dict(iksm_session=Session_token))
		thejson = json.loads(results_list.text)	

		if 'AUTHENTICATION_ERROR' in str(thejson):
			iksm = await self.nsotoken.do_iksm_refresh(message)
			results_list = requests.get(url, headers=header, cookies=dict(iksm_session=iksm))
			thejson = json.loads(results_list.text)

		with open(f"../{jsontype}.json", "w") as f:
			json.dump(thejson, f)

		with open(f"../{jsontype}.json", "r") as f:
			jsonToSend = discord.File(fp=f)
			await message.channel.send(file=jsonToSend)

		os.remove(f"../{jsontype}.json")

	async def checkDuplicate(self, id):
		cur = await self.sqlBroker.connect()
		stmt = "SELECT COUNT(*) FROM tokens WHERE clientid = %s"
		await cur.execute(stmt, (str(id),))
		count = await cur.fetchone()
		await self.sqlBroker.close(cur)
		if count[0] > 0:
			return True
		else:
			return False

	async def getNSOJSON(self, ctx, header, url):
		Session_token = await self.nsotoken.get_iksm_token_mysql(ctx.user.id)
		results_list = requests.get(url, headers=header, cookies=dict(iksm_session=Session_token))
		thejson = json.loads(results_list.text)	

		if 'AUTHENTICATION_ERROR' in str(thejson):
			iksm = await self.nsotoken.do_iksm_refresh(ctx)
			results_list = requests.get(url, headers=header, cookies=dict(iksm_session=iksm))
			thejson = json.loads(results_list.text)
			if 'AUTHENTICATION_ERROR' in str(thejson):
				return None

		return thejson

	async def weaponParser(self, ctx, weapid):
		if not await self.checkDuplicate(ctx.user.id):
			await ctx.channel.send("You don't have a token setup with me! Please DM me !token with how to get one setup!")
			return

		thejson = await self.getNSOJSON(ctx, self.app_head, "https://app.splatoon2.nintendo.net/api/records")
		if thejson == None:
			return

		try:
			weapondata = thejson['records']['weapon_stats']
		except:
			await message.channel.send("Error while retrieving json for weapon stats, this has been logged with my owners.")
			print(f"ERROR IN WEAPON JSON:\n{str(thejson)}")
			return

		theweapdata = None
		gotweap = False
		for i in weapondata:
			if int(i) == weapid:
				gotweap = True
				theweapdata = weapondata[i]
				break

		if not gotweap:
			await ctx.respond("I have no stats for that weapon for you")
			return

		name = thejson['records']['player']['nickname']
		turfinked = theweapdata['total_paint_point']
		turfstring = str(turfinked)
		if turfinked >= 100000:
			turfstring = f"{str(turfinked)}<:badge_100k:863924861809197096>"
		if turfinked >= 500000:
			turfstring = f"{str(turfinked)}<:badge_500k:863925109278507038>"
		if turfinked >= 1000000:
			turfstring = f"{str(turfinked)}<:badge_1M:863925025388101632>"
		if turfinked >= 9999999:
			turfstring = f"{str(turfinked)}<:badge_10M:863924949748416542>"
		wins = theweapdata['win_count']
		loss = theweapdata['lose_count']
		if (wins + loss) != 0:
			winper = int(wins / (wins + loss) * 100)
		else:
			winper = 0

		freshcur = theweapdata['win_meter']
		freshmax = theweapdata['max_win_meter']

		embed = discord.Embed(colour=0x0004FF)
		embed.title = f"{str(name)}'s Stats for {theweapdata['weapon']['name']}"
		embed.set_thumbnail(url=f"https://splatoon2.ink/assets/splatnet{theweapdata['weapon']['image']}")
		embed.add_field(name="Wins/Losses/%", value=f"{str(wins)}/{str(loss)}/{str(winper)}%", inline=True)
		embed.add_field(name="Turf Inked", value=turfstring, inline=True)
		embed.add_field(name="Freshness (Current/Max)", value=f"{str(freshcur)}/{str(freshmax)}", inline=True)

		await ctx.respond(embed=embed)

	async def mapParser(self, ctx, mapid):
		if not await self.checkDuplicate(ctx.user.id):
			await ctx.channel.send("You don't have a token setup with me! Please DM me !token with how to get one setup!")
			return

		thejson = await self.getNSOJSON(ctx, self.app_head, "https://app.splatoon2.nintendo.net/api/records")
		if thejson == None:
			return

		try:
			allmapdata = thejson['records']['stage_stats']
		except:
			await ctx.channel.send("Error retrieving json for stage_stats. This has been logged for my owners.")
			print(f"ERROR IN MAP JSON:\n{str(thejson)}")
			return

		themapdata = None
		for i in allmapdata:
			if int(i) == mapid:
				themapdata = allmapdata[i]
				break

		name = thejson['records']['player']['nickname']
		embed = discord.Embed(colour=0x0004FF)
		embed.title = f"{str(name)}'s Stats for {themapdata['stage']['name']} (Wins/Losses/%)"

		rmwin = themapdata['hoko_win']
		rmloss = themapdata['hoko_lose']
		szwin = themapdata['area_win']
		szloss = themapdata['area_lose']
		tcwin = themapdata['yagura_win']
		tcloss = themapdata['yagura_lose']
		cbwin = themapdata['asari_win']
		cbloss = themapdata['asari_lose']

		if (rmwin + rmloss) != 0:
			rmpercent = int(rmwin / (rmwin + rmloss) * 100)
		else:
			rmpercent = 0
		if (szwin + szloss) != 0:
			szpercent = int(szwin / (szwin + szloss) * 100)
		else:
			szpercent = 0
		if (tcwin + tcloss) != 0:
			tcpercent = int(tcwin / (tcwin + tcloss) * 100)
		else:
			tcpercent = 0
		if (cbwin + cbloss) != 0:
			cbpercent = int(cbwin / (cbwin + cbloss) * 100)
		else:
			cbpercent = 0

		embed.set_thumbnail(url=f"https://splatoon2.ink/assets/splatnet{themapdata['stage']['image']}")
		embed.add_field(name="Splat Zones", value=f"{str(szwin)}/{str(szloss)}/{str(szpercent)}%", inline=True)
		embed.add_field(name="Rainmaker", value=f"{str(rmwin)}/{str(rmloss)}/{str(rmpercent)}%", inline=True)
		embed.add_field(name="Tower Control", value=f"{str(tcwin)}/{str(tcloss)}/{str(tcpercent)}%", inline=True)
		embed.add_field(name="Clam Blitz", value=f"{str(cbwin)}/{str(cbloss)}/{str(cbpercent)}%", inline=True)
		await ctx.respond(embed=embed)

	async def getStats(self, ctx):
		if not await self.checkDuplicate(ctx.user.id):
			await ctx.respond("You don't have a token setup with me! Please DM me !token with how to get one setup!")
			return

		thejson = await self.getNSOJSON(ctx, self.app_head, "https://app.splatoon2.nintendo.net/api/records")
		if thejson == None:
			return

		embed = discord.Embed(colour=0x0004FF)
		name = thejson['records']['player']['nickname']
		turfinked = thejson['challenges']['total_paint_point_octa'] + thejson['challenges']['total_paint_point']
		turfsquid = thejson['challenges']['total_paint_point']
		turfocto = thejson['challenges']['total_paint_point_octa']
		totalwins = thejson['records']['win_count']
		totalloss = thejson['records']['lose_count']
		recentwins = thejson['records']['recent_win_count']
		recentloss = thejson['records']['recent_lose_count']
		maxleagueteam = thejson['records']['player']['max_league_point_team']
		maxleaguepair = thejson['records']['player']['max_league_point_pair']
		species = thejson['records']['player']['player_type']['species']
		gender = thejson['records']['player']['player_type']['style']
		leaguepairgold = thejson['records']['league_stats']['pair']['gold_count']
		leaguepairsilver = thejson['records']['league_stats']['pair']['silver_count']
		leaguepairbronze = thejson['records']['league_stats']['pair']['bronze_count']
		leaguepairnone = thejson['records']['league_stats']['pair']['no_medal_count']
		leagueteamgold = thejson['records']['league_stats']['team']['gold_count']
		leagueteamsilver = thejson['records']['league_stats']['team']['silver_count']
		leagueteambronze = thejson['records']['league_stats']['team']['bronze_count']
		leagueteamnone = thejson['records']['league_stats']['team']['no_medal_count']

		topweap = None
		topink = 0
		for i in thejson['records']['weapon_stats']:
			j = thejson['records']['weapon_stats'][i]
			if topink < int(j['total_paint_point']):
				topink = int(j['total_paint_point'])
				topweap = j

		if 'octoling' in species:
			species = 'Octoling'
		else:
			species = 'Inkling'

		embed.title = f"{str(name)} - {species} {gender} - Stats"
		embed.add_field(name='Turf Inked', value=f"Squid: {str(turfsquid)}\nOcto: {str(turfocto)}\nTotal: {str(turfinked)}", inline=True)
		embed.add_field(name='Wins/Losses', value=f"Last 50: {str(recentwins)}/{str(recentloss)}\nTotal: {str(totalwins)}/{str(totalloss)}", inline=True)
		embed.add_field(name='Top League Points', value=f"Team League: {str(maxleagueteam)}\nPair League: {str(maxleaguepair)}", inline=True)
		embed.add_field(name='Team League Medals', value=f"Gold: {str(leagueteamgold)}\nSilver: {str(leagueteamsilver)}\nBronze: {str(leagueteambronze)}\nUnranked: {str(leagueteamnone)}", inline=True)
		embed.add_field(name='Pair League Medals', value=f"Gold: {str(leaguepairgold)}\nSilver: {str(leaguepairsilver)}\nBronze: {str(leaguepairbronze)}\nUnranked: {str(leaguepairnone)}", inline=True)
		embed.add_field(name='Favorite Weapon', value=f"{topweap['weapon']['name']} with {str(topink)} turf inked total", inline=True)

		await ctx.respond(embed=embed)

	async def getSRStats(self, ctx):
		if not await self.checkDuplicate(ctx.user.id):
			await ctx.respond("You don't have a token setup with me! Please DM me !token with how to get one setup!")
			return

		thejson = await self.getNSOJSON(ctx, self.app_head_coop, "https://app.splatoon2.nintendo.net/api/coop_results")
		if thejson == None:
			return

		name = thejson['results'][0]['my_result']['name']	
		jobresults = thejson['results']
		jobcard = thejson['summary']['card']
		rank = thejson['summary']['stats'][0]['grade']['name']
		points = thejson['summary']['stats'][0]['grade_point']
		embed = discord.Embed(colour=0xFF9B00)
		embed.title = f"{name} - {rank} {str(points)} - Salmon Run Stats"

		embed.add_field(name="Overall Stats", value=f"Shifts Worked: {str(jobcard['job_num'])}\nTeammates Rescued: {str(jobcard['help_total'])}\nGolden Eggs Collected: {str(jobcard['golden_ikura_total'])}\nPower Eggs Collected: {str(jobcard['ikura_total'])}\nTotal Points: {str(jobcard['kuma_point_total'])}", inline=True)

		sheadcnt, stingcnt, flyfshcnt, seelcnt, scrapcnt, mawscnt, drizcnt, deathcnt, rescnt, matches, hazardpts, geggs, peggs = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
		for i in jobresults:
			matches += 1
			deathcnt += i['my_result']['dead_count']
			rescnt += i['my_result']['help_count']
			hazardpts += i['danger_rate']
			geggs += i['my_result']['golden_ikura_num']
			peggs += i['my_result']['ikura_num']
			for j in i['my_result']['boss_kill_counts']:
				y = i['my_result']['boss_kill_counts'][j]
				if 'Steelhead' in y['boss']['name']:
					sheadcnt += y['count']
				if 'Stinger' in y['boss']['name']:
					stingcnt += y['count']
				if 'Flyfish' in y['boss']['name']:
					flyfshcnt += y['count']
				if 'Steel Eel' in y['boss']['name']:
					seelcnt += y['count']
				if 'Scrapper' in y['boss']['name']:
					scrapcnt += y['count']
				if 'Maws' in y['boss']['name']:
					mawscnt += y['count']
				if 'Drizzler' in y['boss']['name']:
					drizcnt += y['count']

		hazardavg = int(hazardpts / matches)
		geggsavg = int(geggs / matches)
		peggsavg = int(peggs / matches)
		deathsavg = int(deathcnt / matches)
		resavg = int(rescnt / matches)
		embed.add_field(name=f"Avgerage Stats (Last {str(matches)} Games)", value=f"Teammates Rescued: {str(resavg)}\nTimes Died: {str(deathsavg)}\nGolden Eggs: {str(geggsavg)}\nPower Eggs: {str(peggsavg)} \nHazard Level: {str(hazardavg)}%", inline=True)
		embed.add_field(name=f"Total Stats (Last {str(matches)} Games)", value=f"Teammates Rescued: {str(rescnt)}\nTimes Died: {str(deathcnt)}\nGolden Eggs: {str(geggs)}\nPower Eggs: {str(peggs)}", inline=True)
		embed.add_field(name=f"Boss Kill Counts (Last {str(matches)} games)", value=f"Steelhead: {str(sheadcnt)}\nStinger: {str(stingcnt)}\nFlyfish: {str(flyfshcnt)}\nSteel Eel: {str(seelcnt)}\nScrapper: {str(scrapcnt)}\nMaws: {str(mawscnt)}\nDrizzler: {str(drizcnt)}", inline=True)

		await ctx.respond(embed=embed)

	async def getRanks(self, ctx):
		if not await self.checkDuplicate(ctx.user.id):
			await ctx.respond("You don't have a token setup with me! Please DM me !token with how to get one setup!")
			return

		thejson = await self.getNSOJSON(ctx, self.app_head, "https://app.splatoon2.nintendo.net/api/records")
		if thejson == None:
			return

		name = thejson['records']['player']['nickname']
		szrank = thejson['records']['player']['udemae_zones']['name']
		if szrank == "S+":
			szrank += str(thejson['records']['player']['udemae_zones']['s_plus_number'])

		rmrank = thejson['records']['player']['udemae_rainmaker']['name']
		if rmrank == "S+":
			rmrank += str(thejson['records']['player']['udemae_rainmaker']['s_plus_number'])

		tcrank = thejson['records']['player']['udemae_tower']['name']
		if tcrank == "S+":
			tcrank += str(thejson['records']['player']['udemae_tower']['s_plus_number'])

		cbrank = thejson['records']['player']['udemae_clam']['name']
		if cbrank == "S+":
			cbrank += str(thejson['records']['player']['udemae_clam']['s_plus_number'])

		embed = discord.Embed(colour=0xFF7800)
		embed.title = name + "'s Ranks"
		embed.add_field(name="Splat Zones", value=szrank, inline=True)
		embed.add_field(name="Tower Control", value=tcrank, inline=True)
		embed.add_field(name="Rainmaker", value=rmrank, inline=True)
		embed.add_field(name="Clam Blitz", value=cbrank, inline=True)
		await ctx.respond(embed=embed)

	def makeGearEmbed(self, gear, title, dirs):
		embed = discord.Embed(colour=0xF9FC5F)
		embed.title = title
		embed.set_thumbnail(url=f"https://splatoon2.ink/assets/splatnet{gear['gear']['image']}")
		embed.add_field(name="Brand", value=gear['gear']['brand']['name'], inline=True)
		embed.add_field(name="Name", value=gear['gear']['name'], inline=True)
		embed.add_field(name="Type", value=gear['gear']['kind'], inline=True)
		embed.add_field(name="Main Ability", value=gear['skill']['name'], inline=True)
		embed.add_field(name="Available Sub Slots", value=gear['gear']['rarity'], inline=True)
		if 'frequent_skill' in gear['gear']['brand']:
			embed.add_field(name="Common Ability", value=gear['gear']['brand']['frequent_skill']['name'], inline=True)
		else:
			embed.add_field(name="Common Ability", value='None', inline=True)

		embed.add_field(name="Price", value=gear['price'], inline=True)
		embed.add_field(name="Directions", value=dirs, inline=False)
		return embed

	async def orderGearCommand(self, ctx, args=None, order=-1, override=False, is_slash=True):

		def check(m):
			return m.author == ctx.user and m.channel == ctx.channel

		if not await self.checkDuplicate(ctx.user.id) and order == -1:
			await ctx.respond("You don't have a token setup with me! Please DM me !token with how to get one setup!")
			return
		elif not await self.checkDuplicate(ctx.user.id) and order != -1:
			await ctx.respond("You don't have a token setup with me, would you like to set one up now? (Yes/No)")
			resp = await self.client.wait_for('message', check=check)
			if resp.content.lower() == "yes":
				await self.nsotoken.login(ctx, flag=1)
			else:
				await ctx.channel.send("Ok! If you want to setup a token to order in the future, DM me !token")
				return

		if order != -1:
			merchid = self.storeJSON['merchandises'][order]['id']
		elif args != None:
			if len(args) == 0:
				await ctx.respond("I need an item to order, please use 'ID to order' from `/store currentgear!`")
				return

			# Build a list of SplatStoreMerch items to match against
			merchitems = []
			for i in range(0, len(self.storeJSON['merchandises'])):
				merch = self.storeJSON['merchandises'][i]
				merchitems.append(splatinfo.SplatStoreMerch(merch['gear']['name'], i, merch['id']))

			# Try the match
			match = self.splatInfo.matchItems("store merchandise", merchitems, " ".join(args))
			if not match.isValid():
				await ctx.respond(match.errorMessage("Try command `/store currentgear` for a list."))
				return

			merchid = match.get().merchid()
		else:
			await ctx.respond("Order called improperly! Please report this to my support discord!")
			return

		await self.orderGear(ctx, merchid, override=override, is_slash=is_slash)

	async def orderGear(self, ctx, merchid, override=False, is_slash=True):
		# Filter for incoming messages, this is still using regular message objects
		def messageCheck(m):
			return (m.author.id == ctx.user.id) and (m.channel.id == ctx.channel.id)

		thejson = await self.getNSOJSON(ctx, self.app_head, "https://app.splatoon2.nintendo.net/api/timeline")
		if thejson == None:
			return

		tmp_app_head_shop = self.app_head_shop
		tmp_app_head_shop['x-unique-id'] = thejson['unique_id']

		thejson = await self.getNSOJSON(ctx, self.app_head, "https://app.splatoon2.nintendo.net/api/onlineshop/merchandises")
		merches = list(filter(lambda g: g['id'] == merchid, thejson['merchandises']))
		if len(merches) == 0:
			await ctx.channel.send("Can't find that merch in the store!")
			return
		gearToBuy = merches[0]
		orderedFlag = 'ordered_info' in thejson

		#confirm controls wether we ask for confirmation in a message context
		if not is_slash and not override:
			embed = self.makeGearEmbed(gearToBuy, f"{ctx.user.name} - Order gear?", "Respond with 'yes' to place your order, 'no' to cancel")
			await ctx.respond(embed=embed)
			confirmation = await self.client.wait_for('message', check=messageCheck)
			if not 'yes' in confirmation.content.lower():
				await ctx.respond(f"{ctx.user.name} - order canceled")
				return

		if not orderedFlag:
			if await self.postNSOStore(ctx, gearToBuy['id'], tmp_app_head_shop):
				await ctx.respond(f"{ctx.user.name} - ordered!")
			else:
				await ctx.respond(f"{ctx.user.name} - failed to order")
		else:
			ordered = thejson['ordered_info']
			if not override and is_slash:
				embed = self.makeGearEmbed(ordered, f"{ctx.user.name}, you already have an item on order!", "Run this command with override set to True to order")
				await ctx.respond(embed=embed)
				return
			elif not is_slash:
				embed = self.makeGearEmbed(ordered, f"{ctx.user.name}, you already have an item on order!", "Respond with 'yes' to replace your order, 'no' to cancel")
				await ctx.respond(embed=embed)
						
			if not is_slash:
				confirmation = await self.client.wait_for('message', check=messageCheck)
				if 'yes' in confirmation.content.lower():
					if await self.postNSOStore(ctx, gearToBuy['id'], tmp_app_head_shop, override=True):
						await ctx.respond(f"{ctx.user.name} - ordered!")
					else:
						await ctx.respond(f"{ctx.user.name} - failed to order")
			elif is_slash and override: 
				if await self.postNSOStore(ctx, gearToBuy['id'], tmp_app_head_shop, override=True):
					embed = self.makeGearEmbed(gearToBuy, f"{ctx.user.name} ordered!", "Go talk to Murch in game to get it!")
					await ctx.respond(embed=embed)
				else:
					embed = self.makeGearEmbed(gearToBuy, f"{ctx.user.name}, failed to order", "You can try running this command again, but there is likely an issue with NSO")
					await ctx.respond(embed=embed)
			else:
				await ctx.channel.send(f"{ctx.user.name} - something went wrong...")

	async def postNSOStore(self, ctx, gid, app_head, override=False):
		iksm = await self.nsotoken.get_iksm_token_mysql(ctx.user.id)
		url = f"https://app.splatoon2.nintendo.net/api/onlineshop/order/{gid}"
		if override:
			payload = { "override" : 1 }
			response = requests.post(url, headers=app_head, cookies=dict(iksm_session=iksm), data=payload)
		else:
			response = requests.post(url, headers=app_head, cookies=dict(iksm_session=iksm))
		resp = json.loads(response.text)

		return response.status_code == 200

	async def gearParser(self, ctx=None, flag=0):
		theTime = int(time.time())
		gear = self.storeJSON['merchandises']
		embed = discord.Embed(colour=0xF9FC5F)
		embed.title = "Current Splatnet Gear For Sale"
		j = 0
		for i in gear:
			skill = i['skill']
			equip = i['gear']
			price = i['price']
			end = i['end_time']
			eqName = equip['name']
			eqBrand = equip['brand']['name']
			if 'frequent_skill' in equip['brand']:
				commonSub = equip['brand']['frequent_skill']['name']
			else:
				commonSub = "None"

			eqKind = equip['kind']
			slots = equip['rarity'] + 1

			if j == 0:
				timeRemaining = end - theTime
				timeRemaining = timeRemaining % 86400
				hours = int(timeRemaining / 3600)
				timeRemaining = timeRemaining % 3600
				minutes = int(timeRemaining / 60)

			if flag == 0:
				embed.add_field(name=f"**{eqName}**", value=f"{eqBrand} : {eqKind}", inline=False)
				embed.add_field(name="ID/Subs/Price", value=f"{str(j)}/{str(slots)}/{str(price)}", inline=True)
				embed.add_field(name="Ability/Common Sub", value=f"{str(skill['name'])}/{str(commonSub)}", inline=True)
				j = j + 1
			else:
				if j != 5:
					j = j + 1
					continue
				else:
					return i

		embed.set_footer(text=f"Next Item In {str(hours)} Hours {str(minutes)} minutes")
		await ctx.respond(embed=embed)

	def mapsEmbed(self, offset=0) -> discord.Embed:
		embed = discord.Embed(colour=0x3FFF33)
		
		data = self.maps(offset=offset)
		turf = data['turf']
		ranked = data['ranked']
		league = data['league']
		hours = data['hours']
		mins = data['mins']

		if offset == 0:
			embed.title = "Current Splatoon 2 Maps"
		elif offset == 1:
			embed.title = "Upcoming Splatoon 2 Maps"

		embed.add_field(name="<:turfwar:550103899084816395> Turf War", value=f"{turf['stage_a']['name']}\n{turf['stage_a']['name']}", inline=True)
		embed.add_field(name=f"<:ranked:550104072456372245> Ranked: {ranked['rule']['name']}", value=f"{ranked['stage_a']['name']}\n{ranked['stage_b']['name']}", inline=True)
		embed.add_field(name=f"<:league:550104147463110656> League: {league['rule']['name']}", value=f"{league['stage_a']['name']}\n{league['stage_b']['name']}", inline=True)

		if offset == 0:
			embed.add_field(name="Time Remaining", value=f"{str(hours)} Hours, and {str(mins)} minutes", inline=False)
		elif offset >= 1:
			hours = hours - 2
			embed.add_field(name="Time Until Map Rotation", value=f"{str(hours)} Hours, and {str(mins)} minutes", inline=False)

		return embed

	def maps(self, offset=0):
		theTime = int(time.time())
		trfWar = self.mapsJSON['regular']
		ranked = self.mapsJSON['gachi']
		league = self.mapsJSON['league']
		
		turf = {}
		turf['stage_a'] = trfWar[offset]['stage_a']
		turf['stage_b'] = trfWar[offset]['stage_b']
		turf['end']  = trfWar[offset]['end_time']

		end   = trfWar[offset]['end_time']
		theTime  = end - theTime
		theTime  = theTime % 86400
		hours = int(theTime / 3600)
		theTime  = theTime % 3600
		mins  = int(theTime / 60)

		rnk = {}
		rnk['stage_a'] = ranked[offset]['stage_a']
		rnk['stage_b'] = ranked[offset]['stage_b']
		rnk['rule'] = ranked[offset]['rule']

		lge = {}
		lge['stage_a'] = league[offset]['stage_a']
		lge['stage_b'] = league[offset]['stage_b']
		lge['rule'] = league[offset]['rule']

		data = {}
		data['hours']  = hours
		data['mins']   = mins
		data['turf']   = turf
		data['ranked'] = rnk
		data['league'] = lge

		return data

	def srEmbed(self, getNext=False) -> discord.Embed:
		embed = discord.Embed(colour=0xFF8633)

		data = self.srParser(getNext=getNext)
		if data == None:
			data = self.srParser(getNext=True)
			getNext=True

		weaps = data['weapons']
		map = data['map']
		days = data['days']
		hours = data['hours']
		mins = data['mins']

		if getNext == 0:
			embed.title = "Current Salmon Run"
		else:
			embed.title = "Upcoming Salmon Run"

		embed.set_thumbnail(url=f"https://splatoon2.ink/assets/splatnet{map['image']}")
		embed.add_field(name='Map', value=map['name'], inline=False)
		embed.add_field(name='Weapons', value=weaps, inline=False)

		if getNext:
			embed.add_field(name='Time Until Rotation', value=f"{str(days)} Days, {str(hours)} Hours, and {str(mins)} Minutes")
		else:
			embed.add_field(name="Time Remaining ", value=f"{str(days)} Days, {str(hours)} Hours, and {str(mins)} Minutes")

		return embed

	def srParser(self, getNext=False):
		theTime = int(time.time())
		currentSR = self.srJSON['details']
		gotData = 0
		start = 0
		end = 0
		
		theString = ''	
		srdata = {}

		for i in currentSR:
			gotData = 0
			start = i['start_time']
			end = i['end_time']
			map = i['stage']
			weaps = i['weapons']

			if start <= theTime and theTime <= end:
				gotData = 1

			if (gotData == 1 and getNext == 0) or (gotData == 0 and getNext == 1):
				srdata['thumb'] = f"https://splatoon2.ink/assets/splatnet{map['image']}"
				srdata['map'] = map

				for j in i['weapons']:
					if 'weapon' in j:
						weap = j['weapon']
					else:
						weap = j['coop_special_weapon']
					theString = f"{theString}{weap['name']}\n"
				break

			elif gotData == 1 and getNext == 1:
				gotData = 0
				continue

		srdata['weapons'] = theString

		if gotData == 0 and getNext == 0:
			return None
		elif getNext == 1:
			timeleft = start - theTime
		else:
			timeleft = end - theTime

		days = int(timeleft / 86400)
		timeleft = timeleft % 86400
		hours = int(timeleft / 3600)
		timeleft = timeleft % 3600
		mins = int(timeleft / 60)

		srdata['days'] = days
		srdata['hours'] = hours
		srdata['mins'] = mins

		return srdata

	async def battleParser(self, ctx, num=1):
		if not await self.checkDuplicate(ctx.user.id):
			await ctx.send("You don't have a token setup with me! Please DM me !token with how to get one setup!")
			return

		recordjson = await self.getNSOJSON(ctx, self.app_head, "https://app.splatoon2.nintendo.net/api/records")
		if recordjson == None:
			return

		embed = discord.Embed(colour=0x0004FF)
		battlejson = await self.getNSOJSON(ctx, self.app_head, "https://app.splatoon2.nintendo.net/api/results")

		accountname = recordjson['records']['player']['nickname']
		print("TYPE: " + str(type(num)))
		thebattle = battlejson['results'][num - 1]
		battletype = thebattle['game_mode']['name']
		battleid = thebattle['battle_number']

		fullbattle = await self.getNSOJSON(ctx, self.app_head, f"https://app.splatoon2.nintendo.net/api/results/{battlelid}")
		enemyteam = fullbattle['other_team_members']
		myteam = fullbattle['my_team_members']
		mystats = fullbattle['player_result']
		mykills = mystats['kill_count'] + mystats['assist_count']
		myassists = mystats['assist_count']
		mydeaths = mystats['death_count']
		mypoints = mystats['game_paint_point']
		myweapon = mystats['player']['weapon']['name']
		specials = mystats['special_count']
		matchname = mystats['player']['nickname']
		rule = thebattle['rule']['name']
		mystats = fullbattle['player_result']
		myresult = thebattle['my_team_result']['name']
		enemyresult = thebattle['other_team_result']['name']

		if 'udemae' in mystats['player']:
			myrank = mystats['player']['udemae']['name']
		else:
			myrank = None

		if num == 1:
			embed.title = f"Stats for {str(accountname)}'s last battle - {str(battletype)} - {str(rule)} (Kills(Assists)/Deaths/Specials)"
		else:
			embed.title = f"Stats for {str(accountname)}'s battle {str(num)} matches ago - {str(battletype)} - {str(rule)} (Kills(Assists)/Deaths/Specials)"

		teamstring = ""
		enemystring = ""
		placedPlayer = False

		if rule == "Turf War":
			myteam = sorted(myteam, key=lambda i : i['game_paint_point'], reverse=True)
			enemyteam = sorted(enemyteam, key=lambda i : i['game_paint_point'], reverse=True)
		else:
			myteam = sorted(myteam, key=lambda i : i['kill_count'] + i['assist_count'], reverse=True)
			enemyteam = sorted(enemyteam, key=lambda i : i['kill_count'] + i['assist_count'], reverse=True)

		for i in myteam:
			tname = i['player']['nickname']
			if rule == "Turf War" and mypoints > i['game_paint_point'] and not placedPlayer:
				placedPlayer = True
				teamstring += matchname
				if myrank != None:
					teamstring += f" - {myrank}"
				teamstring += f" - {myweapon} - {str(mykills)}({str(myassists)})/{str(mydeaths)}/{str(specials)}\n"
			if rule != "Turf War" and mykills > i['kill_count'] + i['assist_count'] and not placedPlayer:
				placedPlayer = True
				teamstring += matchname
				if myrank != None:
					teamstring += f" - {myrank}"
				teamstring += f" - {myweapon} - {str(mykills)}({str(myassists)})/{str(mydeaths)}/{str(specials)}\n"

			teamstring += tname
			if 'udemae' in i['player']:
				teamstring += " - " + i['player']['udemae']['name']
			teamstring += f" - {i['player']['weapon']['name']} - {str(i['kill_count'] + i['assist_count'])}({str(i['assist_count'])})/{str(i['death_count'])}/{str(i['special_count'])}\n"

		if not placedPlayer:
			if myrank != None:
				teamstring += " - " + myrank
			teamstring += f" - {myweapon} - {str(mykills)}({str(myassists)})/{str(mydeaths)}/{str(specials)}\n"

		for i in enemyteam:
			ename = i['player']['nickname']
			enemystring += ename
			if 'udemae' in i['player']:
				enemystring += f" - {i['player']['udemae']['name']}"

			enemystring += f" - {i['player']['weapon']['name']} - {str(i['kill_count'] + i['assist_count'])}({str(i['assist_count'])})/{str(i['death_count'])}/{str(i['special_count'])}\n"
		if 'VICTORY' in myresult:
			embed.add_field(name=f"{str(matchname)}'s team - {str(myresult)}", value=teamstring, inline=True)
			embed.add_field(name=f"Enemy Team - {str(enemyresult)}", value=enemystring, inline=True)
		else:
			embed.add_field(name=f"Enemy Team - {str(enemyresult)}", value=enemystring, inline=True)
			embed.add_field(name=f"{str(matchname)}'s team - {str(myresult)}", value=teamstring, inline=True)

		await ctx.respond(embed=embed)

	async def cmdMaps(self, ctx, args):
		if len(args) == 0:
			await ctx.respond("Try 'maps help' for help")
			return

		subcommand = args[0].lower()
		if subcommand == "help":
			await ctx.respond("**maps random [n]**: Generate a list of random maps\n"
				"**maps stats MAP**: Show player stats for MAP\n"
				"**maps callout MAP**: Show callouts for MAP\n"
				"**maps list**: Lists all maps with abbreviations")
		elif subcommand == "list":
			embed = discord.Embed(colour=0xF9FC5F)
			embed.title = "Maps List"
			embed.add_field(name="Maps (abbreviation)", value=", ".join(map(lambda item: item.format(), self.splatInfo.getAllMaps())), inline=False)
			await ctx.respond(embed=embed)
		elif subcommand == "stats":
			if len(args) > 1:
				themap = " ".join(args[1:])
				match = self.splatInfo.matchMaps(themap)
				if not match.isValid():
					await ctx.respond(match.errorMessage("Try command 'maps list' for a list."))
					return
				id = match.get().id()
				await self.mapParser(ctx, id)
		elif subcommand == "random":
			count = 1
			if len(args) > 1:
				if not args[1].isdigit():
					await ctx.respond("Argument to 'maps random' must be numeric")
					return
				elif (int(args[1]) < 1) or (int(args[1]) > 10):
					await ctx.respond("Number of random maps must be within 1..10")
					return
				else:
					count = int(args[1])

			if count == 1:
				await ctx.respond(f"Random map: {self.splatInfo.getRandomMap().name()}")
			else:
				out = "Random maps:\n"
				for i in range(count):
					out += "%d: %s\n" % (i + 1, self.splatInfo.getRandomMap().name())
				await ctx.respond(out)
		elif "callout" in subcommand:
			themap = self.splatInfo.matchMaps(" ".join(args[1:]))
			if not themap.isValid():
				await ctx.respond(themap.errorMessage("Try command 'maps list' for a list."))
				return

			shortname = themap.get().shortname().lower().replace(" ", "-")
			url = f"http://db-files.crmea.de/images/bot/callouts/{shortname}.png"
			embed = discord.Embed(colour=0x0004FF)
			embed.title = themap.get().name()
			embed.set_image(url=url)
			await ctx.respond(embed=embed)
		else:
			await ctx.respond("Unknown subcommand. Try 'maps help'")

	async def cmdWeaps(self, ctx, args):
		if len(args) == 0:
			await ctx.channel.send("Try 'weapons help' for help")
			return

		subcommand = args[0].lower()
		if subcommand == "help":
			await ctx.respond("**weapons random [n]**: Generate a list of random weapons\n"
				"**weapons stats WEAPON**: Show player stats for WEAPON\n"
				"**weapons sub SUB**: Show all weapons with SUB\n"
				"**weapons list TYPE**: Shows all weapons of TYPE\n"
				"**weapons special SPECIAL**: Show all weapons with SPECIAL\n"
				"**weapons info WEAPON**: Shows information about specific weapon named WEAPON\n")
			return
		elif subcommand == "info":
			if len(args) > 1:
				theWeapon = " ".join(args[1:])
				match = self.splatInfo.matchWeapons(theWeapon)
				if not match.isValid():
					await ctx.respond(match.errorMessage("Try command 'weapons list' for a list."))
					return
				weap = match.get()
				embed = discord.Embed(colour=0x0004FF)
				embed.title = weap.name() + " Info"
				embed.add_field(name="Sub", value=weap.sub().name(), inline=True)
				embed.add_field(name="Sepcial", value=weap.special().name(), inline=True)
				embed.add_field(name="Pts for Special", value=str(weap.specpts), inline=True)
				embed.add_field(name="Level to Purchase", value=str(weap.level), inline=True)
				await ctx.respond(embed=embed)
		elif subcommand == "sub":
			if len(args) > 1:
				theSub = " ".join(args[1:])
				actualSub = self.splatInfo.matchSubweapons(theSub)
				if not actualSub.isValid():
					await ctx.respond(actualSub.errorMessage())
					return
				weaponsList = self.splatInfo.getWeaponsBySub(actualSub.get())
				embed = discord.Embed(colour=0x0004FF)
				embed.title = f"Weapons with Subweapon: {actualSub.get().name()}"
				for i in weaponsList:
					embed.add_field(name=i.name(), value=f"Special: {i.special().name()}\nPts for Special: {str(i.specpts)}\nLevel To Purchase: {str(i.level)}", inline=True)
				await ctx.respond(embed=embed)
		elif subcommand == "special":
			if len(args) > 1:
				theSpecial = " ".join(args[1:])
				actualSpecial = self.splatInfo.matchSpecials(theSpecial)
				if not actualSpecial.isValid():
					await ctx.respond(actualSpecial.errorMessage())
					return
				weaponsList = self.splatInfo.getWeaponsBySpecial(actualSpecial.get())
				embed = discord.Embed(colour=0x0004FF)
				embed.title = f"Weapons with Special: {actualSpecial.get().name()}"
				for i in weaponsList:
					embed.add_field(name=i.name(), value=f"Subweapon: {i.sub().name()}\nPts for Special: {str(i.specpts)}\nLevel To Purchase: {str(i.level)}", inline=True)
				await ctx.respond(embed=embed)
		elif subcommand == "list":
			if len(args) > 1:
				match = self.splatInfo.matchWeaponType(args[1])
				if not match.isValid():
					await ctx.respond(match.errorMessage("Try command 'weapons list' for a list."))
					return

				type = match.get()
				weaps = self.splatInfo.getWeaponsByType(type)
				embed = discord.Embed(colour=0x0004FF)
				weapString = ""
				for w in weaps:
					weapString += f"{w.name()}\n"
				embed.title = "Weapons List"
				embed.add_field(name=type.pluralname(), value=weapString, inline=False)
				await ctx.respond(embed=embed)
			else:
				types = self.splatInfo.getAllWeaponTypes()
				typelist = f"{', '.join(map(lambda t: t.format(), types[0:-1]))}, or {types[-1].format()}?"
				await ctx.respond(f"Need a type to list. Types are: {typelist}")
			return
		elif subcommand == "stats":
			if len(args) > 1:
				theWeapon = " ".join(args[1:])
				match = self.splatInfo.matchWeapons(theWeapon)
				if not match.isValid():
					await ctx.respond(match.errorMessage("Try command 'weapons list' for a list."))
					return
				id = match.get().id()
				await self.weaponParser(ctx, id)
		elif subcommand == "random":
			count = 1
			if len(args) > 1:
				if not args[1].isdigit():
					await ctx.respond("Argument to 'weapons random' must be numeric")
					return
				elif (int(args[1]) < 1) or (int(args[1]) > 10):
					await ctx.respond("Number of random weapons must be within 1..10")
					return
				else:
					count = int(args[1])

			if count == 1:
				await ctx.respond(f"Random weapon: {self.splatInfo.getRandomWeapon().name()}")
			else:
				out = "Random weapons:\n"
				for i in range(count):
					out += "%d: %s\n" % (i + 1, self.splatInfo.getRandomWeapon().name())
				await ctx.respond(out)
		else:
			await ctx.respond("Unknown subcommand. Try 'weapons help'")

	async def cmdBattles(self, ctx, num):
		if num <= 50 and num > 0:
			await self.battleParser(ctx, num)
		else:
			await ctx.respond("Battlenum needs to be between 1-50!")
