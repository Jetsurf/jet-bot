import mysql.connector
from mysql.connector.cursor import MySQLCursorPrepared
import discord
import asyncio
import mysqlinfo
import time
import requests
import json

class nsoHandler():
	def __init__(self, client, mysqlinfo):
		self.client = client
		self.theDB = mysql.connector.connect(host=mysqlinfo.host, user=mysqlinfo.user, password=mysqlinfo.pw, database=mysqlinfo.db)
		self.cursor = self.theDB.cursor(cursor_class=MySQLCursorPrepared)
		self.app_timezone_offset = str(int((time.mktime(time.gmtime()) - time.mktime(time.localtime()))/60))
		self.app_head = {
			'Host': 'app.splatoon2.nintendo.net',
			'x-unique-id': '32449507786579989234',
			'x-requested-with': 'XMLHttpRequest',
			'x-timezone-offset': self.app_timezone_offset,
			'User-Agent': 'Mozilla/5.0 (Linux; Android 7.1.2; Pixel Build/NJH47D; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/59.0.3071.125 Mobile Safari/537.36',
			'Accept': '*/*',
			'Referer': 'https://app.splatoon2.nintendo.net/home',
			'Accept-Encoding': 'gzip, deflate',
			'Accept-Language': 'en-us'
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
			await self.client.send_message(message.channel, "You don't have a token sent to me! Please DM me your iksm_session token with !token your_token")
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
			await self.client.send_message(message.channel, "You don't have a token sent to me! Please DM me your iksm_session token with !token your_token")
			return

		stmt = 'SELECT token FROM tokens WHERE clientid = %s'
		self.cursor.execute(stmt, (message.author.id,))
		Session_token = self.cursor.fetchone()[0]
		url = "https://app.splatoon2.nintendo.net/api/records"
		results_list = requests.get(url, headers=self.app_head, cookies=dict(iksm_session=Session_token))
		thejson = json.loads(results_list.text)

		try:
			name = thejson['records']['player']['nickname']
		except:
			await self.client.send_message(message.channel, message.author.name + " there is a problem with your token")
			return

		szrank = thejson['records']['player']['udemae_zones']['name']
		rmrank = thejson['records']['player']['udemae_rainmaker']['name']
		tcrank = thejson['records']['player']['udemae_tower']['name']
		cbrank = thejson['records']['player']['udemae_clam']['name']
		embed = discord.Embed(colour=0xFF7800)
		embed.title = name + "'s Ranks"
		embed.add_field(name="Splat Zones", value=szrank, inline=True)
		embed.add_field(name="Tower Control", value=tcrank, inline=True)
		embed.add_field(name="Rainmaker", value=rmrank, inline=True)
		embed.add_field(name="Clam Blitz", value=cbrank, inline=True)
		await self.client.send_message(message.channel, embed=embed)