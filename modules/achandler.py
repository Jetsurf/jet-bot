import discord, asyncio
import mysqlhandler, nsotoken
import time, requests
import json, os
import urllib, urllib.request
import re

class acHandler():
	def __init__(self, client, mysqlHandler, nsotoken):
		self.client = client
		self.sqlBroker = mysqlHandler
		self.nsotoken = nsotoken
		self.user_app_head = {
			'Host': 'web.sd.lp1.acbaa.srv.nintendo.net',
			'User-Agent': 'Mozilla/5.0 (Linux; Android 7.1.2; Pixel Build/NJH47D; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/59.0.3071.125 Mobile Safari/537.36',
			'Accept': 'application/json, text/plain, */*',
			'Connection': 'keep-alive',
			'Referer': 'https://web.sd.lp1.acbaa.srv.nintendo.net/?lang=en-US&na_country=US&na_lang=en-US',
			'Accept-Encoding': 'gzip, deflate, br',
			'Accept-Language': 'en-us'
		}
		self.user_cookie = {
			'_dnt' : '1',
			'_ga' : 'GA1.2.235595523.1520818620',
			'_gtoken' : 'replace'
		}

	async def getNSOJSON(self, message, header, url):
		tokens = await self.nsotoken.get_ac_mysql(message.author.id)
		stoken = await self.nsotoken.get_session_token_mysql(message.author.id)
		gtoken = tokens[0]
		parktoken = tokens[1]
		
		if 'users' in url.lower():
			self.user_cookie['_gtoken'] = gtoken
			r = requests.get(url, headers=header, cookies=self.user_cookie)
			thejson = json.loads(r.text)
		else:
			print("More Stuff")

		if '401' in str(r):
			tokens = await self.nsotoken.do_ac_refresh(message)
			self.user_cookie['_gtoken'] = gtoken
			results_list = requests.get(url, headers=header, cookies=self.user_cookie)
			thejson = json.loads(results_list.text)
			if '401' in str(r):
				return None

		return thejson

	async def get_user_info(self, message):
		thejson = await self.getNSOJSON(message, self.user_app_head, 'https://web.sd.lp1.acbaa.srv.nintendo.net/api/sd/v1/users')

		user = thejson['users'][0]

		profilepic = requests.get(user['image'])
		profileid = re.search('(?<=user_profile/).*(?=\?)', user['image']).group()
		print("PROFILEID: " + str(profileid))

		open('/var/www/db-files/acprofiles/' + str(profileid) + ".png", 'wb').write(profilepic.content)

		embed = discord.Embed(colour=0x0004FF)
		embed.title = user['name'] + "'s Passport - Animal Crossing New Horizons"
		embed.set_thumbnail(url='https://db-files.crmea.de/acprofiles/' + str(profileid) + '.png')
		embed.add_field(name="Island Name", value=user['land']['name'], inline=True)

		await message.channel.send(embed=embed)


	async def passport(self, message):
		await self.get_user_info(message)

	async def print_user(self, message):
		thejson = await self.getNSOJSON(message, self.info_app_head, 'https://web.sd.lp1.acbaa.srv.nintendo.net/api/sd/v1/lands/0x5e5064e0cd85f89/profile?language=en-U')

	#async def get_bearer(self, message):
			#requests.get('https://web.sd.lp1.acbaa.srv.nintendo.net/api/sd/v1/auth_token', header=