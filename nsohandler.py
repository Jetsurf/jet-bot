import mysql.connector
from mysql.connector.cursor import MySQLCursorPrepared
import discord
import asyncio
import mysqlinfo
import time
import requests
import json
import urllib
import urllib.request

class nsoHandler():
	def __init__(self, client, mysqlinfo):
		self.client = client
		self.theDB = mysql.connector.connect(host=mysqlinfo.host, user=mysqlinfo.user, password=mysqlinfo.pw, database=mysqlinfo.db)
		self.cursor = self.theDB.cursor(cursor_class=MySQLCursorPrepared)
		self.app_timezone_offset = str(int((time.mktime(time.gmtime()) - time.mktime(time.localtime()))/60))
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
    		"User-Agent": "Mozilla/5.0 (Linux; Android 7.1.2; Pixel Build/NJH47D; wv) AppleWebKit/537.36 (KHTML, like Gecko) "
                  			"Version/4.0 Chrome/59.0.3071.125 Mobile Safari/537.36",
    		"Accept": "*/*",
    		"Referer": "https://app.splatoon2.nintendo.net/results",
    		"Accept-Encoding": "gzip, deflate",
    		"Accept-Language": "en-US"
		}

	def checkDuplicate(self, id):
		stmt = "SELECT COUNT(*) FROM tokens WHERE clientid = %s"
		self.cursor.execute(stmt, (id,))
		count = self.cursor.fetchone()

		if count[0] > 0:
			return True
		else:
			return False

	async def addToken(self, message, token):
		if self.checkDuplicate(message.author.id):
			stmt = "UPDATE tokens SET token = %s WHERE clientid = %s"
			input = (token, message.author.id,)
		else:
			stmt = "INSERT INTO tokens (clientid, token) VALUES(%s, %s)"
			input = (message.author.id, token,)

		self.cursor.execute(stmt, input)
		if self.cursor.lastrowid != None:
			if 'UPDATE' in stmt:
				await self.client.send_message(message.channel, 'Token updated for you!')
			else:
				await self.client.send_message(message.channel, 'Token added for you!')
			self.theDB.commit()
		else:
			await self.client.send_message(message.channel, "Something went wrong!")

	async def getStats(self, message):
		if not self.checkDuplicate(message.author.id):
			await self.client.send_message(message.channel, "You don't have a token setup with me! Please DM me !token with how to get one setup!")
			return

		stmt = 'SELECT token FROM tokens WHERE clientid = %s'
		self.cursor.execute(stmt, (message.author.id,))
		Session_token = self.cursor.fetchone()[0].decode('utf-8')
		url = "https://app.splatoon2.nintendo.net/api/records"
		results_list = requests.get(url, headers=self.app_head, cookies=dict(iksm_session=Session_token))
		thejson = json.loads(results_list.text)
		embed = discord.Embed(colour=0x0004FF)
		try:
			name = thejson['records']['player']['nickname']
		except:
			await self.client.send_message(message.channel, message.author.name + " there is a problem with your token")
			return

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

		await self.client.send_message(message.channel, embed=embed)

	async def getRanks(self, message):
		if not self.checkDuplicate(message.author.id):
			await self.client.send_message(message.channel, "You don't have a token setup with me! Please DM me !token with how to get one setup!")
			return

		stmt = 'SELECT token FROM tokens WHERE clientid = %s'
		self.cursor.execute(stmt, (message.author.id,))
		Session_token = self.cursor.fetchone()[0].decode('utf-8')
		url = "https://app.splatoon2.nintendo.net/api/records"
		results_list = requests.get(url, headers=self.app_head, cookies=dict(iksm_session=Session_token))
		thejson = json.loads(results_list.text)

		try:
			name = thejson['records']['player']['nickname']
		except:
			await self.client.send_message(message.channel, message.author.name + " there is a problem with your token")
			return

		szrank = thejson['records']['player']['udemae_zones']['name']
		if szrank == "S+":
			szrank += thejson['records']['player']['udemae_zones']['s_plus_number']

		rmrank = thejson['records']['player']['udemae_rainmaker']['name']
		if rmrank == "S+":
			rmrank += thejson['records']['player']['udemae_rainmaker']['s_plus_number']

		tcrank = thejson['records']['player']['udemae_tower']['name']
		if tcrank == "S+":
			tcrank += thejson['records']['player']['udemae_tower']['s_plus_number']

		cbrank = thejson['records']['player']['udemae_clam']['name']
		if cbrank == "S+"
			cbrank += thejson['records']['player']['udemae_clam']['s_plus_number']

		embed = discord.Embed(colour=0xFF7800)
		embed.title = name + "'s Ranks"
		embed.add_field(name="Splat Zones", value=szrank, inline=True)
		embed.add_field(name="Tower Control", value=tcrank, inline=True)
		embed.add_field(name="Rainmaker", value=rmrank, inline=True)
		embed.add_field(name="Clam Blitz", value=cbrank, inline=True)
		await self.client.send_message(message.channel, embed=embed)

	def getJSON(self, url):
		req = urllib.request.Request(url, headers={ 'User-Agent' : 'Magic!' })
		response = urllib.request.urlopen(req)
		data = json.loads(response.read().decode())
		return data

	async def orderGear(self, message):
		if not self.checkDuplicate(message.author.id):
			await self.client.send_message(message.channel, "You don't have a token setup with me! Please DM me !token with how to get one setup!")
			return

		stmt = 'SELECT token FROM tokens WHERE clientid = %s'
		self.cursor.execute(stmt, (message.author.id,))
		Session_token = self.cursor.fetchone()[0].decode('utf-8')

		data = self.getJSON("https://splatoon2.ink/data/merchandises.json")
		gear = data['merchandises']
		embed = discord.Embed(colour=0xF9FC5F)

		orderID = int(message.content.split(" ", 1)[1])

		url = "https://app.splatoon2.nintendo.net/api/timeline"
		results_list = requests.get(url, headers=self.app_head, cookies=dict(iksm_session=Session_token))
		thejson = json.loads(results_list.text)
		self.app_head_shop['x-unique-id'] = thejson['unique_id']

		url = "https://app.splatoon2.nintendo.net/api/onlineshop/merchandises"
		results_list = requests.get(url, headers=self.app_head, cookies=dict(iksm_session=Session_token))
		thejson = json.loads(results_list.text)
		gearToBuy = thejson['merchandises'][orderID]
		gearToBuyName = thejson['merchandises'][orderID]['gear']['name']
		await self.client.send_message(message.channel, message.author.name + " - do you want to order " + gearToBuyName + "? Respond with yes to buy!")
		confirm = await self.client.wait_for_message(author=message.author, channel=message.channel)

		if 'yes' in confirm.content.lower():
			url = 'https://app.splatoon2.nintendo.net/api/onlineshop/order/' + gearToBuy['id']
			response = requests.post(url, headers=self.app_head_shop, cookies=dict(iksm_session=Session_token))
			responsejson = json.loads(response.text)
			if '200' not in str(response):
				ordered = thejson['ordered_info']

				await self.client.send_message(message.channel, message.author.name + " you already have " + ordered['gear']['name'] + " ordered, respond back yes to confirm you want to replace this order!")
				confirm = await self.client.wait_for_message(author=message.author, channel=message.channel)
				if 'yes' in confirm.content.lower():
					url = 'https://app.splatoon2.nintendo.net/api/onlineshop/order/' + gearToBuy['id']
					payload = { "override" : 1 }
					response = requests.post(url, headers=self.app_head_shop, cookies=dict(iksm_session=Session_token), data=payload)

					if '200' not in str(response):
						await self.client.send_message(message.channel, message.author.name + "  - failed to order")
					else:
						await self.client.send_message(message.channel, message.author.name + " - ordered!")
				else:
					await self.client.send_message(message.channel, message.author.name + " - order canceled")
			else:
				await self.client.send_message(message.channel, message.author.name + " - ordered!")
		else:
			await self.client.send_message(message.channel, message.author.name + " - order canceled")

	async def gearParser(self, message):
		theTime = int(time.mktime(time.gmtime()))
		data = self.getJSON("https://splatoon2.ink/data/merchandises.json")
		gear = data['merchandises']
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

		await self.client.send_message(message.channel, embed=embed)

	async def maps(self, message, offset=0):
		theTime = int(time.mktime(time.gmtime()))
		data = self.getJSON("https://splatoon2.ink/data/schedules.json")
		trfWar = data['regular']
		ranked = data['gachi']
		league = data['league']
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

		await self.client.send_message(message.channel, embed=embed)

	async def srParser(self, message, getNext=0):
		theTime = int(time.mktime(time.gmtime()))
		data = self.getJSON("https://splatoon2.ink/data/coop-schedules.json")
		currentSR = data['details']
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
			await self.client.send_message(message.channel, 'No SR Currently Running')
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

		await self.client.send_message(message.channel, embed=embed)
