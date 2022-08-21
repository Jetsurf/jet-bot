import discord, asyncio
from discord.ui import *
import mysqlhandler, nsotoken
import time, requests
import json, os
import urllib, urllib.request
import splatinfo
import messagecontext
import io
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class orderView(discord.ui.View):
	def __init__(self, nsohandler, nsotoken, user):
		super().__init__()
		self.nsoToken = nsotoken
		self.nsoHandler = nsohandler
		self.user = user
		self.confirm = False
		self.timeout = 6900.0

	async def initView(self):
		orderBut = discord.ui.Button(label="Order Item")
		nso = await self.nsoToken.get_nso_client(self.user.id)
		if nso != None:
			orderBut.callback = self.orderItem
		else:
			self.stop()
			return None
		self.add_item(orderBut)

	async def orderItem(self, interaction: discord.Interaction):
		if self.confirm:
			await self.nsoHandler.orderGearCommand(interaction, args=['5'], override=True)
			if self.user != None:
				self.clear_items()
				self.stop()
		else:
			await self.nsoHandler.orderGearCommand(interaction, args=['5'])
			self.confirm=True

class nsoHandler():
	def __init__(self, client, mysqlHandler, nsotoken, splatInfo, hostedUrl):
		self.client = client
		self.splatInfo = splatInfo
		self.sqlBroker = mysqlHandler
		self.hostedUrl = hostedUrl
		self.app_timezone_offset = str(int((time.mktime(time.gmtime()) - time.mktime(time.localtime()))/60))
		self.scheduler = AsyncIOScheduler()
		self.scheduler.add_job(self.doStoreDM, 'cron', hour="*/2", minute='5', timezone='UTC') 
		self.scheduler.add_job(self.updateS2JSON, 'cron', hour="*/2", minute='0', second='15', timezone='UTC')
		self.scheduler.add_job(self.doFeed, 'cron', hour="*/2", minute='0', second='25', timezone='UTC')
		self.scheduler.start()
		self.mapJSON = None
		self.storeJSON = None
		self.srJSON= None
		self.nsotoken = nsotoken

	async def doFeed(self):
		#TODO: Future Update: Is it possible to put the orderid button into gear feeds. Expire the button after that rotation
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
				continue

			try:
				await theChannel.send(embed=await self.make_notification(bool(mapflag), bool(srflag), bool(gearflag)))
			except discord.Forbidden:
				print(f"403 on feed, deleting feed from server: {theServer.id} and channel: {theChannel.id}")
				stmt = 'DELETE FROM feeds WHERE serverid = %s AND channelid = %s'
				await cur.execute(stmt, (theServer.id, theChannel.id, ))
				print(f"Deleted {theServer.id} and channel {theChannel.id} from feeds")
				await self.sqlBroker.c_commit(cur)

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
			cur = await self.sqlBroker.connect()
			await cur.execute("SELECT turfwar, ranked, league FROM emotes WHERE myid = %s", (self.client.user.id,))
			emotes = await cur.fetchone()
			await self.sqlBroker.commit(cur)

			embed.add_field(name=f"{emotes[0] if emotes != None else ''} Turf War", value=f"{turf['stage_a']['name']}\n{turf['stage_b']['name']}", inline=True)
			embed.add_field(name=f"{emotes[1] if emotes != None else ''} Ranked: {ranked['rule']['name']}", value=f"{ranked['stage_a']['name']}\n{ranked['stage_b']['name']}", inline=True)
			embed.add_field(name=f"{emotes[2] if emotes != None else ''} League: {league['rule']['name']}", value=f"{league['stage_a']['name']}\n{league['stage_b']['name']}", inline=True)

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
		#TODO : Make user agent include all owners in this vs my hard coded ID
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

	async def addStoreDM(self, ctx, args):
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

		stmt = "SELECT COUNT(*) FROM storedms WHERE clientid = %s"
		await cur.execute(stmt, (str(ctx.user.id),))
		count = await cur.fetchone()
		if count[0] == 0:
			try:
				chan = await ctx.user.send("This is a test to ensure that you can receive DM's. Be aware that if I am unable to DM you (due to changes in permissions), I will no longer notify you of items in the store, even if you restore permission (rerun /store dm add to be readded).")
			except discord.Forbidden:
				await ctx.respond("I am unable to DM you, please check to ensure you can receive DM's from me before attempting again.", ephemeral=True)
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
		theSkill = theGear['skill']['name']
		theType = theGear['gear']['name']
		theBrand = theGear['gear']['brand']['name']

		embed = self.makeGearEmbed(theGear, "Gear you wanted to be notified about has appeared in the shop!", "You can order with the button below. If you don't see it, run /token.")
		try:
			view = orderView(self, self.nsotoken, theMem)
			await view.initView()
			await theMem.send(embed=embed, view=view)
		except discord.Forbidden:
			print(f"Forbidden from messaging user {str(theMem.id)}, removing from DMs")
			cur = await self.sqlBroker.connect()
			stmt = "DELETE FROM storedms WHERE clientid = %s"
			await cur.execute(stmt, (theMem.id,))
			await self.sqlBroker.commit(cur)
			print(f"Removed {str(theMem.id)} from storedm")
			return

		print(f"Messaged {theMem.name}")

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
			theMem = server.get_member(int(memid))
			if theMem is None:
				continue

			asyncio.ensure_future(self.handleDM(theMem, theGear))

	async def weaponParser(self, ctx, weapid):
		await ctx.defer()

		nso = await self.nsotoken.get_nso_client(ctx.user.id)
		if nso == None:
			ctx.respond("You don't have a NSO token setup! Run /token to get started.")
			return

		data = nso.s2.get_weapon_stats(weapid)
		if data == None:
			print(f"NSOHANDLER: weaponParser call returned None: userid {ctx.user.id}")
			await ctx.respond("Something went wrong! As this is new, please report this to my support guild.")
			return	

		if data['weapon_data'] == None:
			ctx.respond("I can't find any data on that weapon for you.")
			return
		
		cur = await self.sqlBroker.connect()
		await cur.execute("SELECT badge100k, badge500k, badge1m, badge10m FROM emotes WHERE myid = %s", (self.client.user.id,))
		emotes = await cur.fetchone()
		await self.sqlBroker.commit(cur)

		turfinked = data['weapon_data']['turf_inked']
		turfstring = str(turfinked)
		if turfinked >= 100000:
			turfstring = f"{str(turfinked)}{emotes[0] if emotes != None else ''}"
		if turfinked >= 500000:
			turfstring = f"{str(turfinked)}{emotes[1] if emotes != None else ''}"
		if turfinked >= 1000000:
			turfstring = f"{str(turfinked)}{emotes[2] if emotes != None else ''}"
		if turfinked >= 9999999:
			turfstring = f"{str(turfinked)}{emotes[3] if emotes != None else ''}"

		embed = discord.Embed(colour=0x0004FF)
		embed.title = f"{str(data['player_name'])}'s Stats for {data['weapon_data']['name']}"
		embed.set_thumbnail(url=f"https://splatoon2.ink/assets/splatnet{data['weapon_data']['image']}")
		embed.add_field(name="Wins/Losses/%", value=f"{str(data['weapon_data']['wins'])}/{str(data['weapon_data']['losses'])}/{str(data['weapon_data']['percent'])}%", inline=True)
		embed.add_field(name="Turf Inked", value=turfstring, inline=True)
		embed.add_field(name="Freshness (Current/Max)", value=f"{str(data['weapon_data']['freshness_current'])}/{str(data['weapon_data']['freshness_max'])}", inline=True)

		await ctx.respond(embed=embed)

	async def mapParser(self, ctx, mapid):
		await ctx.defer()

		nso = await self.nsotoken.get_nso_client(ctx.user.id)
		if nso == None:
			ctx.respond("You don't have a NSO token setup! Run /token to get started.")
			return

		data = nso.s2.get_map_stats(mapid)
		if data == None:
			print(f"NSOHANDLER: mapParser call returned None: userid {ctx.user.id}")
			await ctx.respond("Something went wrong! As this is new, please report this to my support guild.")
			return			

		embed = discord.Embed(colour=0x0004FF)
		embed.title = f"{data['player_name']}'s Stats for {data['map_name']} (Wins/Losses/%)"

		embed.set_thumbnail(url=f"https://splatoon2.ink/assets/splatnet{data['image']}")
		embed.add_field(name="Splat Zones", value=f"{str(data['SZ']['wins'])}/{str(data['SZ']['losses'])}/{str(data['SZ']['percent'])}%", inline=True)
		embed.add_field(name="Rainmaker", value=f"{str(data['RM']['wins'])}/{str(data['RM']['losses'])}/{str(data['RM']['percent'])}%", inline=True)
		embed.add_field(name="Tower Control", value=f"{str(data['TC']['wins'])}/{str(data['TC']['losses'])}/{str(data['TC']['percent'])}%", inline=True)
		embed.add_field(name="Clam Blitz", value=f"{str(data['CB']['wins'])}/{str(data['CB']['losses'])}/{str(data['CB']['percent'])}%", inline=True)
		await ctx.respond(embed=embed)

	async def getStats(self, ctx):
		await ctx.defer()

		nso = await self.nsotoken.get_nso_client(ctx.user.id)
		if nso == None:
			ctx.respond("You don't have a NSO token setup! Run /token to get started.")
			return

		playerData = nso.s2.get_player_stats()
		if playerData == None:
			print(f"NSOHANDLER: getStats call returned None: userid {ctx.user.id}")
			await ctx.respond("Something went wrong! As this is new, please report this to my support guild.")
			return

		embed = discord.Embed(colour=0x0004FF)
		embed.title = f"{playerData['name']} - {playerData['species']} {playerData['gender']} - Stats"
		embed.add_field(name='Turf Inked', value=f"Squid: {str(playerData['turf_stats']['inked_squid'])}\nOcto: {str(playerData['turf_stats']['inked_octo'])}\nTotal: {str(playerData['turf_stats']['inked_total'])}", inline=True)
		embed.add_field(name='Wins/Losses/%', value=f"Last 50: {str(playerData['wl_stats']['recent_wins'])}/{str(playerData['wl_stats']['recent_loss'])}/{playerData['wl_stats']['recent_percent']}\nTotal: {str(playerData['wl_stats']['total_wins'])}/{str(playerData['wl_stats']['recent_loss'])}/{playerData['wl_stats']['total_percent']}", inline=True)
		embed.add_field(name='Top League Points', value=f"Team League: {str(playerData['league_stats']['max_rank_team'])}\nPair League: {str(playerData['league_stats']['max_rank_pair'])}", inline=True)
		embed.add_field(name='Team League Medals', value=f"Gold: {str(playerData['league_stats']['team_gold'])}\nSilver: {str(playerData['league_stats']['team_silver'])}\nBronze: {str(playerData['league_stats']['team_bronze'])}\nUnranked: {str(playerData['league_stats']['team_none'])}", inline=True)
		embed.add_field(name='Pair League Medals', value=f"Gold: {str(playerData['league_stats']['pair_gold'])}\nSilver: {str(playerData['league_stats']['pair_silver'])}\nBronze: {str(playerData['league_stats']['pair_bronze'])}\nUnranked: {str(playerData['league_stats']['pair_none'])}", inline=True)
		embed.add_field(name='Favorite Weapon', value=f"{playerData['top_weapon']['name']} with {str(playerData['top_weapon']['total_inked'])} turf inked total", inline=True)

		await ctx.respond(embed=embed)

	async def getSRStats(self, ctx):
		await ctx.defer()

		nso = await self.nsotoken.get_nso_client(ctx.user.id)
		srdata = nso.s2.get_sr_stats()
		if srdata == None:
			ctx.respond("You don't have a NSO token setup! Run /token to get started.")
			return

		embed = discord.Embed(colour=0xFF9B00)
		embed.title = f"{srdata['player_name']} - {srdata['rank_name']} {str(srdata['rank_points'])} - Salmon Run Stats"

		embed.add_field(name="Overall Stats", value=f"Shifts Worked: {str(srdata['overall_stats']['matches_total'])}\nTeammates Rescued: {str(srdata['overall_stats']['help_total'])}\nGolden Eggs Collected: {str(srdata['overall_stats']['golden_eggs_total'])}\nPower Eggs Collected: {str(srdata['overall_stats']['power_eggs_total'])}\nTotal Points: {str(srdata['overall_stats']['points_total'])}", inline=True)
		embed.add_field(name=f"Avgerage Stats (Last {str(srdata['recent_stats']['matches_total'])} Games)", value=f"Teammates Rescued: {str(srdata['recent_stats']['help_average'])}\nTimes Died: {str(srdata['recent_stats']['deaths_average'])}\nGolden Eggs: {str(srdata['recent_stats']['golden_eggs_average'])}\nPower Eggs: {str(srdata['recent_stats']['power_eggs_average'])} \nHazard Level: {str(srdata['recent_stats']['hazard_average'])}%", inline=True)
		embed.add_field(name=f"Total Stats (Last {str(srdata['recent_stats']['matches_total'])} Games)", value=f"Teammates Rescued: {str(srdata['recent_stats']['help_total'])}\nTimes Died: {str(srdata['recent_stats']['deaths_total'])}\nGolden Eggs: {str(srdata['recent_stats']['golden_eggs_total'])}\nPower Eggs: {str(srdata['recent_stats']['power_eggs_total'])}", inline=True)

		killstring = ""
		for k, v in srdata['boss_stats'].items():
			killstring += f"{k}: {v}\n"

		embed.add_field(name=f"Boss Kill Counts (Last {str(srdata['recent_stats']['matches_total'])} games)", value=killstring, inline=True)

		await ctx.respond(embed=embed)

	async def getRanks(self, ctx):
		await ctx.defer()

		nso = await self.nsotoken.get_nso_client(ctx.user.id)
		ranks = nso.s2.get_ranks()
		if ranks == None:
			ctx.respond("You don't have a NSO token setup! Run /token to get started.")
			return

		embed = discord.Embed(colour=0xFF7800)
		embed.title = f"{ranks['name']}'s Ranks"
		embed.add_field(name="Splat Zones", value=ranks['SZ'], inline=True)
		embed.add_field(name="Tower Control", value=ranks['TC'], inline=True)
		embed.add_field(name="Rainmaker", value=ranks['RM'], inline=True)
		embed.add_field(name="Clam Blitz", value=ranks['CB'], inline=True)
		await ctx.respond(embed=embed)

	def makeGearEmbed(self, gear, title, dirs, colour=None) -> discord.Embed:
		if colour != None:
			embed = discord.Embed(colour=colour)
		else:
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

	async def orderGearCommand(self, ctx, args=None, override=False):
		if view == None:
			await ctx.defer()

		nso = await self.nsotoken.get_nso_client(ctx.user.id)
		
		if not nso.ensure_api_tokens():
			#The error check for being called by view is not needed, only shows button if tokens are present
			ctx.respond("You don't have a NSO token setup! Run /token to get started.")
			return
		elif args != None:
			if len(args) == 0:
				await ctx.respond("I need an item to order, please use 'ID to order' or the item name from `/store currentgear!`")
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
			ret = nso.s2.post_store_purchase(merchid, override)
			if isinstance(ctx, discord.Interaction):
				if ret == None:
					await ctx.response.send_message("Something went wrong. As this is fairly new, please tell my owners in my support guild!")
					print(f"NSOHANDLER: View Order: ERROR: merchid {str(merchid)} override {str(override)} and userid {str(ctx.user.id)}")
					return
				elif 'code' in ret:
					merch = nso.s2.get_store_json()
					embed = self.makeGearEmbed(merch['ordered_info'], f"{ctx.user.name}, you already have an item on order!", "Hit 'Order Item' again to confirm the order.")
				else:
					embed = self.makeGearEmbed(ret['ordered_info'], f"{ctx.user.name} - Ordered!", "Go talk to Murch in game to get it!")

				await ctx.response.send_message(embed=embed)
			else:
				if ret == None:
					await ctx.response.send_message("Something went wrong. As this is fairly new, please tell my owners in my support guild!")
					print(f"NSOHANDLER: Slash CMD Order: ERROR: merchid {str(merchid)} override {str(override)} and userid {str(ctx.user.id)}")
					return
				elif 'code' in ret:
					merch = nso.s2.get_store_json()
					embed = self.makeGearEmbed(merch['ordered_info'], f"{ctx.user.name}, you already have an item on order!", "Run this command with override set to True to order")
				else:
					embed = self.makeGearEmbed(ret['ordered_info'], f"{ctx.user.name} - Ordered!", "Go talk to Murch in game to get it!")
				await ctx.respond(embed=embed)
		else:
			await ctx.respond("Order called improperly! Please report this to my support discord!")
			return

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

	async def mapsEmbed(self, offset=0) -> discord.Embed:
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

		cur = await self.sqlBroker.connect()
		await cur.execute("SELECT turfwar, ranked, league FROM emotes WHERE myid = %s", (self.client.user.id,))
		emotes = await cur.fetchone()
		await self.sqlBroker.commit(cur)

		embed.add_field(name=f"{emotes[0] if emotes != None else ''} Turf War", value=f"{turf['stage_a']['name']}\n{turf['stage_b']['name']}", inline=True)
		embed.add_field(name=f"{emotes[1] if emotes != None else ''} Ranked: {ranked['rule']['name']}", value=f"{ranked['stage_a']['name']}\n{ranked['stage_b']['name']}", inline=True)
		embed.add_field(name=f"{emotes[2] if emotes != None else ''} League: {league['rule']['name']}", value=f"{league['stage_a']['name']}\n{league['stage_b']['name']}", inline=True)

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
		turf['end']     = trfWar[offset]['end_time']

		end     = trfWar[offset]['end_time']
		theTime = end - theTime
		theTime = theTime % 86400
		hours   = int(theTime / 3600)
		theTime = theTime % 3600
		mins    = int(theTime / 60)

		rnk = {}
		rnk['stage_a'] = ranked[offset]['stage_a']
		rnk['stage_b'] = ranked[offset]['stage_b']
		rnk['rule']    = ranked[offset]['rule']

		lge = {}
		lge['stage_a'] = league[offset]['stage_a']
		lge['stage_b'] = league[offset]['stage_b']
		lge['rule']    = league[offset]['rule']

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
		map   = data['map']
		days  = data['days']
		hours = data['hours']
		mins  = data['mins']

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
		await ctx.defer()

		nso = await self.nsotoken.get_nso_client(ctx.user.id)
		recordjson = nso.s2.do_records_request()
		if recordjson == None:
			ctx.respond("You don't have a NSO token setup! Run /token to get started.")
			return

		embed = discord.Embed(colour=0x0004FF)
		battlejson = nso.s2.get_all_battles()

		accountname = recordjson['records']['player']['nickname']
		thebattle = battlejson['results'][num - 1]
		battletype = thebattle['game_mode']['name']
		battleid = thebattle['battle_number']

		fullbattle = nso.s2.get_full_battle(battleid)
		
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
			teamstring += f"{mystats['player']['nickname']} - "
			if myrank != None:
				teamstring += f" - {myrank}"
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
		#TODO: This can be made better, lets split this up into functions?
		subcommand = args[0].lower()
		if subcommand == "list":
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
				await ctx.respond(themap.errorMessage("Couldn't find that map. Try command 'maps list' for a list."))
				return

			if self.hostedUrl == None:
				await ctx.respond("Sorry, map callouts are disabled in this instance of the bot.")
				return

			shortname = themap.get().shortname().lower().replace(" ", "-")
			url = f"{self.hostedUrl}/callouts/{shortname}.png"
			embed = discord.Embed(colour=0x0004FF)
			embed.title = themap.get().name()
			embed.set_image(url=url)
			await ctx.respond(embed=embed)
		else:
			await ctx.respond("Unknown subcommand. Try 'maps help'")

	async def cmdWeaps(self, ctx, args):
		#TODO: This can be made better, lets split this up into functions?
		subcommand = args[0].lower()
		if subcommand == "info":
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
