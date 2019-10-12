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

	async def addStoreDM(self, message):
		abilities = { 'Bomb Defense Up DX',	'Haunt', 'Sub Power Up', 'Ink Resistance Up', 'Swim Speed Up', 'Special Charge Up', 'Main Power Up', 'Ink Recovery Up', 'Respawn Punisher',
						'Quick Super Jump', 'Drop Roller', 'Ink Saver (Main)', 'Ink Saver (Sub)', 'Last-Ditch Effort', 'Ninja Squid', 'Object Shredder', 'Opening Gambit',
						'Quick Respawn', 'Run Speed Up', 'Special Power Up', 'Special Saver', 'Stealth Jump', 'Sub Power Up', 'Swim Speed Up', 'Tenacity', 'Thermal Ink', 'Comeback' }
		abilitiesStr = str(abilities)
		abilitiesStr = abilitiesStr.replace('\'', '')
		abilitiesStr = abilitiesStr.replace('{', '')
		abilitiesStr = abilitiesStr.replace('}', '')

		ability = message.content.split(' ', 1)[1].lower()
		
		flag = False
		for i in abilities:
			if ability == i.lower():
				flag = True
				break;

		if not flag:
			await message.channel.send('The ablility you gave doesn\'t exist!\nValid Abilities are: ' + abilitiesStr)
			return

		cur = await self.sqlBroker.connect()
		stmt = "SELECT COUNT(*) FROM storedms WHERE clientid = %s AND ability = %s"
		await cur.execute(stmt, (str(message.author.id), ability,))
		count = await cur.fetchone()
		if count[0] > 0:
			await message.channel.send("You already will be DM'ed when gear with " + ability + " appears in the store!")
			await self.sqlBroker.close(con)
			return

		stmt = 'INSERT INTO storedms (clientid, serverid, ability) VALUES(%s, %s, %s)'
		await cur.execute(stmt, (str(message.author.id), str(message.guild.id), ability,))
		await self.sqlBroker.commit(cur)
		await message.channel.send("Added you to recieve a DM when gear with " + ability + " appears in the shop!")

	async def handleDM(self, theMem, theSkill):
		await theMem.send("Gear with " + theSkill + " has appeared in the shop! Respond with no within the next 2 hours to stop receiving notifications!")
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
			await theMem.send("Didn't get a message from you, I'll DM you again when gear with " + theSkill + " appears in the shop!")
			return

		if 'no' in resp.content.lower():
			cur = await self.sqlBroker.connect()
			stmt = 'DELETE FROM storedms WHERE clientid = %s AND ability = %s'
			print("Removing " + theMem.name + " from DM's")
			await cur.execute(stmt, (theMem.id, theSkill,))
			await self.sqlBroker.commit(cur)
			await theMem.send("Ok, I won't DM you again when gear with " + theSkill + " appears in the shop.")
		else:
			print("Keeping " + theMem.name + " in DM's")
			await theMem.send("Didn't see no in your message. I'll DM you again when gear with " + theSkill + " appears in the shop!")

	async def doStoreDM(self):
		cur = await self.sqlBroker.connect()
		theGear = self.storeJSON['merchandises'][5]

		theSkill = theGear['skill']['name'].lower()
		print("Doing Store DM! Checking " + theSkill)

		stmt = "SELECT clientid,serverid FROM storedms WHERE ability = %s"
		await cur.execute(stmt, (theSkill,))
		toDM = await cur.fetchall()
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
					asyncio.ensure_future(self.handleDM(theMem, theSkill))

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

	async def orderGear(self, message):
		if not await self.checkDuplicate(message.author.id):
			await message.channel.send("You don't have a token setup with me! Please DM me !token with how to get one setup!")
			return

		Session_token = await self.nsotoken.get_iksm_token_mysql(message.author.id)

		gear = self.storeJSON['merchandises']
		embed = discord.Embed(colour=0xF9FC5F)

		orderID = int(message.content.split(" ", 1)[1])

		thejson = await self.getNSOJSON(message, self.app_head, "https://app.splatoon2.nintendo.net/api/timeline")
		if thejson == None:
			await message.channel.send(message.author.name + " there is a problem with your token")
			return

		self.app_head_shop['x-unique-id'] = thejson['unique_id']
		url = "https://app.splatoon2.nintendo.net/api/onlineshop/merchandises"
		results_list = requests.get(url, headers=self.app_head, cookies=dict(iksm_session=Session_token))
		thejson = json.loads(results_list.text)
		gearToBuy = thejson['merchandises'][orderID]
		gearToBuyName = thejson['merchandises'][orderID]['gear']['name']
		await message.channel.send(message.author.name + " - do you want to order " + gearToBuyName + "? Respond with yes to buy!")

		def check(m):
			return m.author == message.author and m.channel == message.channel

		confirm = await self.client.wait_for('message', check=check)

		if 'yes' in confirm.content.lower():
			url = 'https://app.splatoon2.nintendo.net/api/onlineshop/order/' + gearToBuy['id']
			response = requests.post(url, headers=self.app_head_shop, cookies=dict(iksm_session=Session_token))
			responsejson = json.loads(response.text)

			if '200' not in str(response):
				ordered = thejson['ordered_info']

				await message.channel.send(message.author.name + " you already have " + ordered['gear']['name'] + " ordered, respond back yes to confirm you want to replace this order!")
				confirm = await self.client.wait_for('message', check=check)
				if 'yes' in confirm.content.lower():
					url = 'https://app.splatoon2.nintendo.net/api/onlineshop/order/' + gearToBuy['id']
					payload = { "override" : 1 }
					response = requests.post(url, headers=self.app_head_shop, cookies=dict(iksm_session=Session_token), data=payload)

					if '200' not in str(response):
						await message.channel.send(message.author.name + "  - failed to order")
					else:
						await message.channel.send(message.author.name + " - ordered!")
				else:
					await message.channel.send(message.author.name + " - order canceled")
			else:
				await message.channel.send(message.author.name + " - ordered!")
		else:
			await message.channel.send(message.author.name + " - order canceled")

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

			theString = theString + '	 ID to order: ' + str(j) + '\n'
			theString = theString + '    Skill      : ' + str(skill['name']) + '\n'
			theString = theString + '    Common Sub : ' + str(commonSub) + '\n'
			theString = theString + '    Subs       : ' + str(slots) + '\n'
			theString = theString + '    Type       : ' + eqKind + '\n'
			theString = theString + '    Price      : ' + str(price) + '\n'
			theString = theString + '    Time Left  : ' + str(hours) + ' Hours and ' + str(minutes) + ' minutes'

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

		embed = discord.Embed(colour=0x0004FF)
		embed.title = "Stats for " + str(accountname) +"'s last battle - " + str(battletype) + " - " + str(rule) + " (Kills/Deaths/Specials)"
        
		teamstring = ""
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
				teamstring = teamstring + matchname + " - " + myweapon + " - " + str(mykills) + "(" + str(myassists) + ")/" + str(mydeaths) + "/" + str(specials) + "\n"
			if rule != "Turf War" and mykills > i['kill_count'] + i['assist_count'] and not placedPlayer:
				placedPlayer = True
				teamstring = teamstring + matchname + " - " + myweapon + " - " + str(mykills) + "(" + str(myassists) + ")/" + str(mydeaths) + "/" + str(specials) + "\n"
			
			teamstring = teamstring + tname + " - " + i['player']['weapon']['name'] + " - " + str(i['kill_count'] + i['assist_count']) + "(" + str(i['assist_count']) + ")/" + str(i['death_count']) + "/" + str(i['special_count']) + "\n"

		if not placedPlayer:
			teamstring = teamstring + matchname + " - " + myweapon + " - " + str(mykills) + "(" + str(myassists) + ")/" + str(mydeaths) + "/" + str(specials) + "\n"

		enemystring = ""
		for i in enemyteam:
			ename = i['player']['nickname']
			enemystring = enemystring + ename + " - " + i['player']['weapon']['name'] + " - " + str(i['kill_count'] + i['assist_count']) + "(" + str(i['assist_count']) + ")/" + str(i['death_count']) + "/" + str(i['special_count']) + "\n"

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
				"**maps callout MAP**: Show callouts for MAP")
			return
		elif subcommand == "list":
			print("TODO")
			return
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
			url = "http://crmea.de/images/bot/callouts/" + shortname + ".png"
			embed = discord.Embed(colour=0x0004FF)
			embed.set_image(url=url)
			await message.channel.send(embed=embed)
			#print("NAME: " + shortname + " URL " + url)
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
			print("TODO")
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
				if args[1].isdigit() and int(args[1]) < 50 and int(args[1]) > 0:
					await self.battleParser(message, num=int(args[1]))
				else:
					await message.channel.send("Battle num must be number 1-50")
			else:
				await message.channel.send("Must provide a number of the battle to get")
		else:
			await message.channel.send("Unknown subcommand. Try 'battles help'")
