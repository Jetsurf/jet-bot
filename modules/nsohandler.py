import discord, asyncio
import mysqlhandler, nsotoken
import time, requests
import json, os
import urllib, urllib.request
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class nsoHandler():
	def __init__(self, client, mysqlHandler, nsotoken, splatInfo):
		self.client = client
		self.splatInfo = splatInfo
		self.sqlBroker = mysqlHandler
		self.app_timezone_offset = str(int((time.mktime(time.gmtime()) - time.mktime(time.localtime()))/60))
		self.scheduler = AsyncIOScheduler()
		self.scheduler.add_job(self.doStoreDM, 'cron', hour="*/2", minute='5') 
		self.scheduler.add_job(self.updateS2JSON, 'cron', hour="*/2", minute='0', second='15')
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

	async def addStoreDM(self, message, args):
		if len(args) == 0:
			await message.channel.send("I need an ability to be able to DM you when it appears in the shop! Here are the options: " + abilitiesStr)
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
				await message.channel.send("Didn't find any partial matches for you. Search for Abilities/Gear Brand/Gear Name!")
				return

			embed = discord.Embed(colour=0xF9FC5F)
			embed.title = "Did you mean?"

			if len(match1.items) > 0:
				embed.add_field(name="Abilities", value=", ".join(map(lambda item: item.name(), match1.items)), inline=False)
			if len(match2.items) > 0:
				embed.add_field(name="Brands", value=", ".join(map(lambda item: item.name(), match2.items)), inline=False)
			if len(match3.items) > 0:
				embed.add_field(name="Gear", value=", ".join(map(lambda item: item.name(), match3.items)), inline=False)

			await message.channel.send(embed=embed)
			return

		cur = await self.sqlBroker.connect()

		if match1.isValid():
			stmt = "SELECT COUNT(*) FROM storedms WHERE clientid = %s AND ability = %s"
		elif match2.isValid():
			stmt = "SELECT COUNT(*) FROM storedms WHERE clientid = %s AND brand = %s"
		else:
			stmt = "SELECT COUNT(*) FROM storedms WHERE clientid = %s AND gearname = %s"

		await cur.execute(stmt, (str(message.author.id), term,))
		count = await cur.fetchone()
		if count[0] > 0:
			if match1.isValid():
				await message.channel.send("You will already be DM'ed when gear with ability " + term + " appears in the shop? (Respond Yes/No)")
			elif match2.isValid():
				await message.channel.send("You will already be DM'ed when gear by brand " + term + " appears in the shop? (Respond Yes/No)")
			else:
				await message.channel.send("You will already be DM'ed when " + term + " appears in the shop? (Respond Yes/No)")

			await self.sqlBroker.close(cur)
			return
		else:
			def check2(m):
				return m.author == message.author and m.channel == message.channel

			if match1.isValid():
				await message.channel.send(message.author.name + " do you want me to DM you when gear with ability " + term + " appears in the shop? (Respond Yes/No)")
			elif match2.isValid():
				await message.channel.send(message.author.name + " do you want me to DM you when gear by brand " + term + " appears in the shop? (Respond Yes/No)")
			else:
				await message.channel.send(message.author.name + " do you want me to DM you when " + term + " appears in the shop? (Respond Yes/No)")

			resp = await self.client.wait_for('message', check=check2)
			if 'yes' not in resp.content.lower():
				await message.channel.send("Ok!")
				return

		if match1.isValid():
			stmt = 'INSERT INTO storedms (clientid, serverid, ability) VALUES(%s, %s, %s)'
		elif match2.isValid():
			stmt = 'INSERT INTO storedms (clientid, serverid, brand) VALUES(%s, %s, %s)'
		else:
			stmt = 'INSERT INTO storedms (clientid, serverid, gearname) VALUES(%s, %s, %s)'

		await cur.execute(stmt, (str(message.author.id), str(message.guild.id), term,))
		await self.sqlBroker.commit(cur)

		if match1.isValid():
			await message.channel.send("Added you to recieve a DM when gear with " + term + " appears in the shop!")
		elif match2.isValid():
			await message.channel.send("Added you to recieve a DM when gear by brand " + term + " appears in the shop!")
		else:
			await message.channel.send("Added you to recieve a DM when " + term + " appears in the shop!")
		
	async def handleDM(self, theMem, theGear):
		def checkDM(m):
			return m.author.id == theMem.id and m.guild == None

		theSkill = theGear['skill']['name']
		theType = theGear['gear']['name']
		theBrand = theGear['gear']['brand']['name']

		embed = self.makeGearEmbed(theGear, "Gear you wanted to be notified about has appeared in the shop!", "Respond with 'order' to order, or 'stop' to stop recieving notifications (within the next two hours)")
		await theMem.send(embed=embed)
		print('Messaged ' + theMem.name)

		def check1(m):
			if isinstance(m.channel, discord.DMChannel) and m.channel.recipient.name == theMem.name and not m.author.bot:
				return True
			else:
				return False
		
		# Discord.py changed timeouts to throw exceptions...
		try:	
			resp = await self.client.wait_for('message', timeout=7100, check=check1)
		except:
			print("TIMEOUT: Keeping " + theMem.name + " in DM's")
			await theMem.send("Didn't get a message from you (or didn't understand your response), I'll DM you again when gear with " + theSkill + " appears in the shop!")
			return

		if 'stop' in resp.content.lower():
			cur = await self.sqlBroker.connect()
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
							string+=theSkill + "/"
						if i[1] != None:
							branFlag = True
							string+=theBrand + "/"
						if i[2] != None:
							gearFlag = True
							string+=theType + "/"
			
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
						await theMem.send("Ok, removed you from being DM'ed when gear with ability " + theSkill + " appears in the shop!")
					elif confirm.content.lower() == theBrand.lower() and branFlag:
						stmt = 'DELETE FROM storedms WHERE (clientid = %s) AND (brand = %s)'
						await cur.execute(stmt, (theMem.id, theBrand, ))
						branFlag = False
						await theMem.send("Ok, removed you from being DM'ed when gear by brand " + theBrand + " appears in the shop!")
					elif confirm.content.lower() == theType.lower() and abilFlag:
						stmt = 'DELETE FROM storedms WHERE (clientid = %s) AND (gearname = %s)'
						await cur.execute(stmt, (theMem.id, theType, ))
						await self.sqlBroker.commit(cur)
						gearFlag = False
						await theMem.send("Ok, removed you from being DM'ed when " + theAbility + " appears in the shop!")
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
					await theMem.send("Ok, I won't DM you again when gear with ability " + theSkill + " appears in the shop.")
				elif fields[1] != None:
					await theMem.send("Ok, I won't DM you again when gear by " + theBrand  + " appears in the shop.")
				else:
					await theMem.send("Ok, I won't DM you again when " + theType + " appears in the shop.")

				stmt = 'DELETE FROM storedms WHERE (clientid = %s) AND ((ability = %s) OR (brand = %s) OR (gearname = %s))'

				await cur.execute(stmt, (theMem.id, theSkill, theBrand, theType, ))
				await self.sqlBroker.commit(cur)
				
		elif 'order' in resp.content.lower():
			await self.orderGear(resp, order=5)
		else:
			print("Keeping " + theMem.name + " in DM's")
			await theMem.send("Didn't get a message from you about gear. I'll DM you again when gear with " + theSkill + " appears in the shop!")

	async def doStoreDM(self):
		cur = await self.sqlBroker.connect()
		theGear = self.storeJSON['merchandises'][5]

		theSkill = theGear['skill']['name']
		theType = theGear['gear']['name']
		theBrand = theGear['gear']['brand']['name']
		print("Doing Store DM! Checking " + theType + ' Brand: ' + theBrand + ' Ability: ' + theSkill)

		stmt = "SELECT DISTINCT clientid,serverid FROM storedms WHERE (ability = %s) OR (brand = %s) OR (gearname = %s)"
		await cur.execute(stmt, (theSkill, theBrand, theType,))
		toDM = await cur.fetchall()
		print("DM TEST: " + str(toDM))
		await self.sqlBroker.close(cur)

		for id in range(len(toDM)):
			memid = toDM[id][0]
			servid = toDM[id][1]
			flag = True
			for server in self.client.guilds:
				if str(server.id) != str(servid):
					continue
				theMem = server.get_member(memid)
				if theMem != None:
					asyncio.ensure_future(self.handleDM(theMem, theGear))

	async def getStoreJSON(self, message):
		theGear = self.storeJSON['merchandises'][5]
		await message.channel.send('```' + str(theGear) + '```')

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
			url = "https://app.splatoon2.nintendo.net/api/results/" + num
			header = self.app_head
			jsontype = 'fullbattle' + num
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

		with open("../" + jsontype + ".json", "w") as f:
			json.dump(thejson, f)
		
		with open("../" + jsontype + ".json", "r") as f:
			jsonToSend = discord.File(fp=f)
			await message.channel.send(file=jsonToSend)

		os.remove("../" + jsontype + ".json")

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

	async def getNSOJSON(self, message, header, url):
		Session_token = await self.nsotoken.get_iksm_token_mysql(message.author.id)
		results_list = requests.get(url, headers=header, cookies=dict(iksm_session=Session_token))
		thejson = json.loads(results_list.text)	

		if 'AUTHENTICATION_ERROR' in str(thejson):
			iksm = await self.nsotoken.do_iksm_refresh(message)
			results_list = requests.get(url, headers=header, cookies=dict(iksm_session=iksm))
			thejson = json.loads(results_list.text)
			if 'AUTHENTICATION_ERROR' in str(thejson):
				return None

		return thejson

	async def weaponParser(self, message, weapid):
		if not await self.checkDuplicate(message.author.id):
			await message.channel.send("You don't have a token setup with me! Please DM me !token with how to get one setup!")
			return

		thejson = await self.getNSOJSON(message, self.app_head, "https://app.splatoon2.nintendo.net/api/records")
		if thejson == None:
			await message.channel.send(message.author.name + " there is a problem with your token")
			return

		weapondata = thejson['records']['weapon_stats']
		theweapdata = None
		gotweap = False
		for i in weapondata:
			if int(i) == weapid:
				gotweap = True
				theweapdata = weapondata[i]
				break
		
		if not gotweap:
			await message.channel.send("I have no stats for that weapon for you")
			return

		name = thejson['records']['player']['nickname']
		turfinked = theweapdata['total_paint_point']
		wins = theweapdata['win_count']
		loss = theweapdata['lose_count']
		if (wins + loss) != 0:
			winper = int(wins / (wins + loss) * 100)
		else:
			winper = 0

		freshcur = theweapdata['win_meter']
		freshmax = theweapdata['max_win_meter']

		embed = discord.Embed(colour=0x0004FF)
		embed.title = str(name) + "'s Stats for " + theweapdata['weapon']['name']
		embed.set_thumbnail(url='https://splatoon2.ink/assets/splatnet' + theweapdata['weapon']['image'])
		embed.add_field(name="Wins/Losses/%", value=str(wins) + "/" + str(loss) + "/" + str(winper) + "%", inline=True)
		embed.add_field(name="Turf Inked", value=str(turfinked), inline=True)
		embed.add_field(name="Freshness (Current/Max)", value=str(freshcur) + "/" + str(freshmax), inline=True)

		await message.channel.send(embed=embed)

	async def mapParser(self, message, mapid):
		if not await self.checkDuplicate(message.author.id):
			await message.channel.send("You don't have a token setup with me! Please DM me !token with how to get one setup!")
			return

		thejson = await self.getNSOJSON(message, self.app_head, "https://app.splatoon2.nintendo.net/api/records")
		if thejson == None:
			await message.channel.send(message.author.name + " there is a problem with your token")
			return

		allmapdata = thejson['records']['stage_stats']
		themapdata = None
		for i in allmapdata:
			if int(i) == mapid:
				themapdata = allmapdata[i]
				break

		name = thejson['records']['player']['nickname']
		embed = discord.Embed(colour=0x0004FF)
		embed.title = str(name) + "'s Stats for " + themapdata['stage']['name'] + " (Wins/Losses/%)"

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

		embed.set_thumbnail(url='https://splatoon2.ink/assets/splatnet' + themapdata['stage']['image'])
		embed.add_field(name="Splat Zones", value=str(szwin) + "/" + str(szloss) + "/" + str(szpercent) + "%", inline=True)
		embed.add_field(name="Rainmaker", value=str(rmwin) + "/" + str(rmloss) + "/" + str(rmpercent) + "%", inline=True)
		embed.add_field(name="Tower Control", value=str(tcwin) + "/" + str(tcloss) + "/" + str(tcpercent) + "%", inline=True)
		embed.add_field(name="Clam Blitz", value=str(cbwin) + "/" + str(cbloss) + "/" + str(cbpercent) + "%", inline=True)
		await message.channel.send(embed=embed)

	async def getStats(self, message):
		if not await self.checkDuplicate(message.author.id):
			await message.channel.send("You don't have a token setup with me! Please DM me !token with how to get one setup!")
			return

		thejson = await self.getNSOJSON(message, self.app_head, "https://app.splatoon2.nintendo.net/api/records")
		if thejson == None:
			await message.channel.send(message.author.name + " there is a problem with your token")
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

		embed.title = str(name) + " - " + species + ' ' + gender + " - Stats"
		embed.add_field(name='Turf Inked', value='Squid: ' + str(turfsquid) + '\nOcto: ' + str(turfocto) + '\nTotal: ' + str(turfinked), inline=True)
		embed.add_field(name='Wins/Losses', value='Last 50: ' + str(recentwins) + '/' + str(recentloss) + '\nTotal: ' + str(totalwins) + '/' + str(totalloss), inline=True)
		embed.add_field(name='Top League Points', value='Team League: ' + str(maxleagueteam) + '\nPair League: ' + str(maxleaguepair), inline=True)
		embed.add_field(name='Team League Medals', value='Gold: ' + str(leagueteamgold) + '\nSilver: ' + str(leagueteamsilver) + '\nBronze: ' + str(leagueteambronze) + '\nUnranked: ' + str(leagueteamnone), inline=True)
		embed.add_field(name='Pair League Medals', value='Gold: ' + str(leaguepairgold) + '\nSilver: ' + str(leaguepairsilver) + '\nBronze: ' + str(leaguepairbronze) + '\nUnranked: ' + str(leaguepairnone), inline=True)
		embed.add_field(name='Favorite Weapon', value=topweap['weapon']['name'] + " with " + str(topink) + " turf inked total", inline=True)

		await message.channel.send(embed=embed)

	async def getSRStats(self, message):
		if not await self.checkDuplicate(message.author.id):
			await message.channel.send("You don't have a token setup with me! Please DM me !token with how to get one setup!")
			return

		thejson = await self.getNSOJSON(message, self.app_head_coop, "https://app.splatoon2.nintendo.net/api/coop_results")
		if thejson == None:
			await message.channel.send(message.author.name + " there is a problem with your token")
			return

		name = thejson['results'][0]['my_result']['name']	
		jobresults = thejson['results']
		jobcard = thejson['summary']['card']
		rank = thejson['summary']['stats'][0]['grade']['name']
		points = thejson['summary']['stats'][0]['grade_point']
		embed = discord.Embed(colour=0xFF9B00)
		embed.title = name + " - " + rank + " " + str(points) + " - Salmon Run Stats"

		embed.add_field(name="Overall Stats", value="Shifts Worked: " + str(jobcard['job_num']) + '\nTeammates Rescued: ' + str(jobcard['help_total']) + '\nGolden Eggs Collected: ' +
			str(jobcard['golden_ikura_total']) + '\nPower Eggs Collected: ' + str(jobcard['ikura_total']) + '\nTotal Points: ' + str(jobcard['kuma_point_total']), inline=True)

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
		embed.add_field(name=" Average Stats (Last " + str(matches) + " Games)", value="Average Teammates Rescued: " + str(resavg) + "\nAverage Times Died: " + str(deathsavg) + "\nAverage Golden Eggs: " + str(geggsavg) + "\nAverage Power Eggs: " + str(peggsavg) +
			"\nAverage Hazard Level: " + str(hazardavg) + "%", inline=True)
		embed.add_field(name=" Total Stats (Last " + str(matches) + " Games)", value="Total Teammates Rescued: " + str(rescnt) + "\nTotal Times Died: " + str(deathcnt) + "\nTotal Golden Eggs: " + str(geggs) + "\nTotal Power Eggs: " + str(peggs), inline=True)
		embed.add_field(name="Boss Kill Counts (Last " + str(matches) + " games)", value='Steelhead: ' + str(sheadcnt) + '\nStinger: ' + str(stingcnt) + '\nFlyfish: ' + str(flyfshcnt) + '\nSteel Eel: ' + str(seelcnt) +
			'\nScrapper: ' + str(scrapcnt) + '\nMaws: ' + str(mawscnt) + '\nDrizzler: ' + str(drizcnt), inline=True)

		await message.channel.send(embed=embed)

	async def getRanks(self, message):
		if not await self.checkDuplicate(message.author.id):
			await message.channel.send("You don't have a token setup with me! Please DM me !token with how to get one setup!")
			return

		thejson = await self.getNSOJSON(message, self.app_head, "https://app.splatoon2.nintendo.net/api/records")
		if thejson == None:
			await message.channel.send(message.author.name + " there is a problem with your token")
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
		await message.channel.send(embed=embed)

	def makeGearEmbed(self, gear, title, dirs):
		embed = discord.Embed(colour=0xF9FC5F)
		embed.title = title
		embed.set_thumbnail(url='https://splatoon2.ink/assets/splatnet' + gear['gear']['image'])
		embed.add_field(name="Brand", value=gear['gear']['brand']['name'], inline=True)
		embed.add_field(name="Name", value=gear['gear']['name'], inline=True)
		embed.add_field(name="Type", value=gear['gear']['kind'], inline=True)
		embed.add_field(name="Main Ability", value=gear['skill']['name'], inline=True)
		embed.add_field(name="Available Sub Slots", value=gear['gear']['rarity'], inline=True)
		embed.add_field(name="Common Ability", value=gear['gear']['brand']['frequent_skill']['name'], inline=True)
		embed.add_field(name="Price", value=gear['price'], inline=True)
		embed.add_field(name="Directions", value=dirs, inline=False)
		return embed

	async def orderGear(self, message, args=None, order=-1):
		await message.channel.trigger_typing()

		def check(m):
			return m.author == message.author and m.channel == message.channel

		if not await self.checkDuplicate(message.author.id) and order == -1:
			await message.channel.send("You don't have a token setup with me! Please DM me !token with how to get one setup!")
			return
		elif not await self.checkDuplicate(message.author.id) and order != -1:
			await message.channel.send("You don't have a token setup with me, would you like to set one up now? (Yes/No)")
			resp = await self.client.wait_for('message', check=check)
			if resp.content.lower() == "yes":
				await self.nsotoken.login(message, flag=1)
			else:
				await message.channel.send("Ok! If you want to setup a token to order in the future, DM me !token")
				return

		if order != -1:
			orderID = order
		elif args != None:
			if len(args) == 0:
				await message.channel.send("I need an item to order, please use 'ID to order' from splatnetgear!")
				return
			elif args[0].isdigit() and int(args[0]) <= 5 and int(args[0]) >= 0:
				orderID = args[0]
			else:
				await message.channel.send("I didn't quite understand that, please use 'ID to order' from splatnetgear!")
				return
		else:
			await message.channel.send("Order called improperly! Please report this to my support discord!")
			return

		thejson = await self.getNSOJSON(message, self.app_head, "https://app.splatoon2.nintendo.net/api/timeline")
		if thejson == None:
			await message.channel.send(message.author.name + " there is a problem with your token")
			return
		tmp_app_head_shop = self.app_head_shop
		tmp_app_head_shop['x-unique-id'] = thejson['unique_id']

		thejson = await self.getNSOJSON(message, self.app_head, "https://app.splatoon2.nintendo.net/api/onlineshop/merchandises")
		gearToBuy = thejson['merchandises'][int(orderID)]
		orderedFlag = 'ordered_info' in thejson

		if order == -1:
			embed = self.makeGearEmbed(gearToBuy, message.author.name + ' - Order gear?', "Respond with 'yes' to place your order, 'no' to cancel")
			await message.channel.send(embed=embed)
			confirm = await self.client.wait_for('message', check=check)
		else:
			confirm = message

		await message.channel.trigger_typing()
		if ('yes' in confirm.content.lower() or order != -1) and not orderedFlag:
			if await self.postNSOStore(message, gearToBuy['id'], tmp_app_head_shop):
				await message.channel.send(message.author.name + " - ordered!")
			else:
				await message.channel.send(message.author.name + "  - failed to order")
		elif ('yes' in confirm.content.lower() or order != -1) and orderedFlag:
			ordered = thejson['ordered_info']
			embed = self.makeGearEmbed(ordered, message.author.name + ", you already have an item on order!", "Respond with 'yes' to replace your order, 'no' to cancel")
			await message.channel.send(embed=embed)
			confirm = await self.client.wait_for('message', check=check)
			if 'yes' in confirm.content.lower():
				if await self.postNSOStore(message, gearToBuy['id'], tmp_app_head_shop, override=True):
					await message.channel.send(message.author.name + " - ordered!")
				else:
					await message.channel.send(message.author.name + "  - failed to order")
			else:
				await message.channel.send(message.author.name + " - order canceled")			
		else:
			await message.channel.send(message.author.name + " - order canceled")

	async def postNSOStore(self, message, gid, app_head, override=False):
		iksm = await self.nsotoken.get_iksm_token_mysql(message.author.id)
		url = 'https://app.splatoon2.nintendo.net/api/onlineshop/order/' + gid
		if override:
			payload = { "override" : 1 }
			response = requests.post(url, headers=app_head, cookies=dict(iksm_session=iksm), data=payload)
		else:
			response = requests.post(url, headers=app_head, cookies=dict(iksm_session=iksm))
		resp = json.loads(response.text)

		return '200' in str(response)

	async def gearParser(self, message):
		theTime = int(time.mktime(time.gmtime()))
		gear = self.storeJSON['merchandises']
		embed = discord.Embed(colour=0xF9FC5F)
		embed.title = "Current Splatnet Gear For Sale"
		theString = ''

		j = 0
		for i in gear:
			skill = i['skill']
			equip = i['gear']
			price = i['price']
			end = i['end_time']
			eqName = equip['name']
			eqBrand = equip['brand']['name']
			commonSub = equip['brand']['frequent_skill']['name']
			eqKind = equip['kind']
			slots = equip['rarity'] + 1

			timeRemaining = end - theTime
			timeRemaining = timeRemaining % 86400
			hours = int(timeRemaining / 3600)
			timeRemaining = timeRemaining % 3600
			minutes = int(timeRemaining / 60)

			theString += '	 ID to order: ' + str(j) + '\n'
			theString += '    Skill      : ' + str(skill['name']) + '\n'
			theString += '    Common Sub : ' + str(commonSub) + '\n'
			theString += '    Subs       : ' + str(slots) + '\n'
			theString += '    Type       : ' + eqKind + '\n'
			theString += '    Price      : ' + str(price) + '\n'
			theString += '    Time Left  : ' + str(hours) + ' Hours and ' + str(minutes) + ' minutes'

			embed.add_field(name=eqName + ' : ' + eqBrand, value=theString, inline=False)

			theString = ''
			j = j + 1

		await message.channel.send(embed=embed)

	async def maps(self, message, offset=0):
		theTime = int(time.mktime(time.gmtime()))
		trfWar = self.mapsJSON['regular']
		ranked = self.mapsJSON['gachi']
		league = self.mapsJSON['league']
		embed = discord.Embed(colour=0x3FFF33)

		if offset == 0:
			embed.title = "Current Splatoon 2 Maps"
		elif offset == 1:
			embed.title = "Upcoming Splatoon 2 Maps"

		mapA = trfWar[offset]['stage_a']
		mapB = trfWar[offset]['stage_b']
		end = trfWar[offset]['end_time']

		embed.add_field(name="<:turfwar:550103899084816395> Turf War", value=mapA['name'] + "\n" + mapB['name'], inline=True)

		mapA = ranked[offset]['stage_a']
		mapB = ranked[offset]['stage_b']
		game = ranked[offset]['rule']

		embed.add_field(name="<:ranked:550104072456372245> Ranked: " + game['name'], value=mapA['name'] + "\n" + mapB['name'], inline=True)

		mapA = league[offset]['stage_a']
		mapB = league[offset]['stage_b']
		game = league[offset]['rule']

		embed.add_field(name="<:league:550104147463110656> League: " + game['name'], value=mapA['name'] + "\n" + mapB['name'], inline=True)

		timeRemaining = end - theTime
		timeRemaining = timeRemaining % 86400
		hours = int(timeRemaining / 3600)
		timeRemaining = timeRemaining % 3600
		minutes = int(timeRemaining / 60)

		if offset == 0:
			embed.add_field(name="Time Remaining", value=str(hours) + ' Hours, and ' + str(minutes) + ' minutes', inline=False)
		elif offset >= 1:
			hours = hours - 2
			embed.add_field(name="Time Until Map Rotation", value=str(hours) + ' Hours, and ' + str(minutes) + ' minutes', inline=False)

		await message.channel.send(embed=embed)

	async def srParser(self, message, getNext=0):
		theTime = int(time.mktime(time.gmtime()))
		currentSR = self.srJSON['details']
		gotData = 0
		start = 0
		end = 0
		embed = discord.Embed(colour=0xFF8633)
		theString = ''	

		if getNext == 0:
			embed.title = "Current Salmon Run"
		else:
			embed.title = "Upcoming Salmon Run"

		for i in currentSR:
			gotData = 0
			start = i['start_time']
			end = i['end_time']
			map = i['stage']
			weaps = i['weapons']

			if start <= theTime and theTime <= end:
				gotData = 1

			if (gotData == 1 and getNext == 0) or (gotData == 0 and getNext == 1):
				embed.set_thumbnail(url='https://splatoon2.ink/assets/splatnet' + map['image'])
				embed.add_field(name='Map', value=map['name'], inline=False)
				for j in i['weapons']:
					try:
						weap = j['weapon']
					except:
						weap = j['coop_special_weapon']
					theString = theString + weap['name'] + '\n'
				break

			elif gotData == 1 and getNext == 1:
				gotData = 0
				continue

		embed.add_field(name='Weapons', value=theString, inline=False)

		if gotData == 0 and getNext == 0:
			await message.channel.send('No SR Currently Running')
			return
		elif getNext == 1:
			timeRemaining = start - theTime
		else:
			timeRemaining = end - theTime

		days = int(timeRemaining / 86400)
		timeRemaining = timeRemaining % 86400
		hours = int(timeRemaining / 3600)
		timeRemaining = timeRemaining % 3600
		minutes = int(timeRemaining / 60)

		if getNext == 1:
			embed.add_field(name='Time Until Rotation', value=str(days) + ' Days, ' + str(hours) + ' Hours, and ' + str(minutes) + ' Minutes')
		else:
			embed.add_field(name="Time Remaining ", value=str(days) + ' Days, ' + str(hours) + ' Hours, and ' + str(minutes) + ' Minutes')

		await message.channel.send(embed=embed)

	async def battleParser(self, message, num=1):
		if not await self.checkDuplicate(message.author.id):
			await message.channel.send("You don't have a token setup with me! Please DM me !token with how to get one setup!")
			return

		recordjson = await self.getNSOJSON(message, self.app_head, "https://app.splatoon2.nintendo.net/api/records")
		if recordjson == None:
			await message.channel.send(message.author.name + " there is a problem with your token")
			return

		embed = discord.Embed(colour=0x0004FF)
		battlejson = await self.getNSOJSON(message, self.app_head, "https://app.splatoon2.nintendo.net/api/results")

		accountname = recordjson['records']['player']['nickname']
		thebattle = battlejson['results'][num - 1]
		battletype = thebattle['game_mode']['name']
		battleid = thebattle['battle_number']

		fullbattle = await self.getNSOJSON(message, self.app_head, "https://app.splatoon2.nintendo.net/api/results/" + battleid)
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
			embed.title = "Stats for " + str(accountname) +"'s last battle - " + str(battletype) + " - " + str(rule) + " (Kills/Deaths/Specials)"
		else:
			embed.title = "Stats for " + str(accountname) +"'s battle " + str(num) + " matches ago - " + str(battletype) + " - " + str(rule) + " (Kills/Deaths/Specials)"

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
					teamstring += " - " + myrank
				teamstring += " - " + myweapon + " - " + str(mykills) + "(" + str(myassists) + ")/" + str(mydeaths) + "/" + str(specials) + "\n"
			if rule != "Turf War" and mykills > i['kill_count'] + i['assist_count'] and not placedPlayer:
				placedPlayer = True
				teamstring += matchname
				if myrank != None:
					teamstring += " - " + myrank
				teamstring += " - " + myweapon + " - " + str(mykills) + "(" + str(myassists) + ")/" + str(mydeaths) + "/" + str(specials) + "\n"
			
			teamstring += tname
			if 'udemae' in i['player']:
				teamstring += " - " + i['player']['udemae']['name']
			teamstring += " - " + i['player']['weapon']['name'] + " - " + str(i['kill_count'] + i['assist_count']) + "(" + str(i['assist_count']) + ")/" + str(i['death_count']) + "/" + str(i['special_count']) + "\n"

		if not placedPlayer:
			if myrank != None:
				teamstring += " - " + myrank
			teamstring += " - " + myweapon + " - " + str(mykills) + "(" + str(myassists) + ")/" + str(mydeaths) + "/" + str(specials) + "\n"

		for i in enemyteam:
			ename = i['player']['nickname']
			enemystring += ename
			if 'udemae' in i['player']:
				enemystring += " - " + i['player']['udemae']['name']
			
			enemystring += " - " + i['player']['weapon']['name'] + " - " + str(i['kill_count'] + i['assist_count']) + "(" + str(i['assist_count']) + ")/" + str(i['death_count']) + "/" + str(i['special_count']) + "\n"
		if 'VICTORY' in myresult:
			embed.add_field(name=str(matchname) + "'s team - " + str(myresult), value=teamstring, inline=True)
			embed.add_field(name="Enemy Team - " + str(enemyresult), value=enemystring, inline=True)
		else:
			embed.add_field(name="Enemy Team - " + str(enemyresult), value=enemystring, inline=True)
			embed.add_field(name=str(matchname) + "'s team - " + str(myresult), value=teamstring, inline=True)

		await message.channel.send(embed=embed)

	async def cmdMaps(self, message, args):
		if len(args) == 0:
			await message.channel.send("Try 'maps help' for help")
			return

		subcommand = args[0].lower()
		if subcommand == "help":
			await message.channel.send("**maps random [n]**: Generate a list of random maps\n"
				"**maps stats MAP**: Show player stats for MAP\n"
				"**maps callout MAP**: Show callouts for MAP\n"
				"**maps list**: Lists all maps with abbreviations")
		elif subcommand == "list":
			embed = discord.Embed(colour=0xF9FC5F)
			embed.title = "Maps List"
			embed.add_field(name="Maps (abbreviation)", value=", ".join(map(lambda item: item.format(), self.splatInfo.getAllMaps())), inline=False)
			await message.channel.send(embed=embed)
		elif subcommand == "stats":
			if len(args) > 1:
				themap = " ".join(args[1:])
				match = self.splatInfo.matchMaps(themap)
				if not match.isValid():
					await message.channel.send(match.errorMessage())
					return
				id = match.get().id()
				await self.mapParser(message, id)
		elif subcommand == "random":
			count = 1
			if len(args) > 1:
				if not args[1].isdigit():
					await message.channel.send("Argument to 'maps random' must be numeric")
					return
				elif (int(args[1]) < 1) or (int(args[1]) > 10):
					await message.channel.send("Number of random maps must be within 1..10")
					return
				else:
					count = int(args[1])

			if count == 1:
				await message.channel.send("Random map: " + self.splatInfo.getRandomMap().name())
			else:
				out = "Random maps:\n"
				for i in range(count):
					out += "%d: %s\n" % (i + 1, self.splatInfo.getRandomMap().name())
				await message.channel.send(out)
		elif "callout" in subcommand:
			themap = self.splatInfo.matchMaps(" ".join(args[1:]))
			if not themap.isValid():
				await message.channel.send(themap.errorMessage())
				return

			shortname = themap.get().shortname().lower().replace(" ", "-")
			url = "http://db-files.crmea.de/images/bot/callouts/" + shortname + ".png"
			embed = discord.Embed(colour=0x0004FF)
			embed.set_image(url=url)
			await message.channel.send(embed=embed)
		else:
			await message.channel.send("Unknown subcommand. Try 'maps help'")

	async def cmdWeaps(self, message, args):
		if len(args) == 0:
			await message.channel.send("Try 'weapons help' for help")
			return

		subcommand = args[0].lower()
		if subcommand == "help":
			await message.channel.send("**weapons random [n]**: Generate a list of random weapons\n"
				"**weapons stats WEAPON**: Show player stats for WEAPON\n"
				"**weapons sub SUB**: Show all weapons with SUB\n"
				"**weapons list TYPE**: Shows all weapons of TYPE\n"
				"**weapons special SPECIAL**: Show all weapons with SPECIAL")
			return
		elif subcommand == "info":
			if len(args) > 1:
				theWeapon = " ".join(args[1:])
				match = self.splatInfo.matchWeapons(theWeapon)
				if not match.isValid():
					await message.channel.send(match.errorMessage())
					return
				weap = match.get()
				embed = discord.Embed(colour=0x0004FF)
				embed.title = weap.name() + " Info"
				embed.add_field(name="Sub", value=weap.sub().name(), inline=True)
				embed.add_field(name="Sepcial", value=weap.special().name(), inline=True)
				embed.add_field(name="Pts for Special", value=str(weap.specpts), inline=True)
				embed.add_field(name="Level to Purchase", value=str(weap.level), inline=True)
				await message.channel.send(embed=embed)
		elif subcommand == "sub":
			if len(args) > 1:
				theSub = " ".join(args[1:])
				actualSub = self.splatInfo.matchSubweapons(theSub)
				if not actualSub.isValid():
					await message.channel.send(actualSub.errorMessage())
					return
				weaponsList = self.splatInfo.getWeaponsBySub(actualSub.get())
				embed = discord.Embed(colour=0x0004FF)
				embed.title = "Weapons with Subweapon: " + actualSub.get().name()
				for i in weaponsList:
					embed.add_field(name=i.name(), value="Special: " + i.special().name() +
						"\nPts for Special: " + str(i.specpts) +
						"\nLevel To Purchase: " + str(i.level), inline=True)
				await message.channel.send(embed=embed)
		elif subcommand == "special":
			if len(args) > 1:
				theSpecial = " ".join(args[1:])
				actualSpecial = self.splatInfo.matchSpecials(theSpecial)
				if not actualSpecial.isValid():
					await message.channel.send(actualSpecial.errorMessage())
					return
				weaponsList = self.splatInfo.getWeaponsBySpecial(actualSpecial.get())
				embed = discord.Embed(colour=0x0004FF)
				embed.title = "Weapons with Special: " + actualSpecial.get().name()
				for i in weaponsList:
					embed.add_field(name=i.name(), value="Subweapon: " + i.sub().name() +
						"\nPts for Special: " + str(i.specpts) +
						"\nLevel To Purchase: " + str(i.level), inline=True)
				await message.channel.send(embed=embed)
		elif subcommand == "list":
			if len(args) > 1:
				t = self.splatInfo.matchWeaponType(args[1])
				if not t.isValid():
					await message.channel.send("I don't know of any weapontype named " + args[1] + ". Try command 'weapons list' for a list.")
					return

				weaps = self.splatInfo.getWeaponsByType(t.get())
				embed = discord.Embed(colour=0x0004FF)
				weapString = ""
				for w in weaps:
					weapString += w.name() + '\n'
				embed.title = "Weapons List"
				embed.add_field(name=t.get().name() + 's', value=weapString, inline=False)
				await message.channel.send(embed=embed)
			else:
				await message.channel.send("Need a type to search, types are Shooter, Blaster, Roller, Charger, Slosher, Splatling, and Brella, ")
			return
		elif subcommand == "stats":
			if len(args) > 1:
				theWeapon = " ".join(args[1:])
				match = self.splatInfo.matchWeapons(theWeapon)
				if not match.isValid():
					await message.channel.send(match.errorMessage())
					return
				id = match.get().id()
				await self.weaponParser(message, id)
		elif subcommand == "random":
			count = 1
			if len(args) > 1:
				if not args[1].isdigit():
					await message.channel.send("Argument to 'weapons random' must be numeric")
					return
				elif (int(args[1]) < 1) or (int(args[1]) > 10):
					await message.channel.send("Number of random weapons must be within 1..10")
					return
				else:
					count = int(args[1])

			if count == 1:
				await message.channel.send("Random weapon: " + self.splatInfo.getRandomWeapon().name())
			else:
				out = "Random weapons:\n"
				for i in range(count):
					out += "%d: %s\n" % (i + 1, self.splatInfo.getRandomWeapon().name())
				await message.channel.send(out)
		else:
			await message.channel.send("Unknown subcommand. Try 'weapons help'")

	async def cmdBattles(self, message, args):
		if len(args) == 0:
			await message.channel.send("Try 'battles help' for help")
			return

		subcommand = args[0].lower()
		if subcommand == "help":
			await message.channel.send("**battles last**: Get the stats from the last battle\n"
				"**num NUM**: Get a battle from the last 50 you have played (1 is most recent)")
		elif subcommand == "last":
			await self.battleParser(message)
		elif subcommand == "num":
			if len(args) > 1:
				if args[1].isdigit() and int(args[1]) <= 50 and int(args[1]) > 0:
					await self.battleParser(message, num=int(args[1]))
				else:
					await message.channel.send("Battle num must be number 1-50")
			else:
				await message.channel.send("Must provide a number of the battle to get")
		else:
			await message.channel.send("Unknown subcommand. Try 'battles help'")
