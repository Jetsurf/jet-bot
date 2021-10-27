import discord, asyncio
import mysqlhandler, nsotoken
import time, requests
import json, os
import urllib, urllib.request
import re

class acHandler():
	def __init__(self, client, mysqlHandler, nsotoken, configData):
		self.client = client
		self.sqlBroker = mysqlHandler
		self.nsotoken = nsotoken
		self.hostedUrl = configData.get('hosted_url')
		self.webDir = configData.get('web_dir')
		self.user_app_head = {
			'Host': 'web.sd.lp1.acbaa.srv.nintendo.net',
			'User-Agent': 'Mozilla/5.0 (Linux; Android 7.1.2; Pixel Build/NJH47D; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/59.0.3071.125 Mobile Safari/537.36',
			'Accept': 'application/json, text/plain, */*',
			'Connection': 'keep-alive',
			'Referer': 'https://web.sd.lp1.acbaa.srv.nintendo.net/?lang=en-US&na_country=US&na_lang=en-US',
			'Accept-Encoding': 'gzip, deflate, br',
			'Accept-Language': 'en-us'
		}
		self.user_auth_app_head = {
			'Host': 'web.sd.lp1.acbaa.srv.nintendo.net',
			'User-Agent': 'Mozilla/5.0 (Linux; Android 7.1.2; Pixel Build/NJH47D; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/59.0.3071.125 Mobile Safari/537.36',
			'Accept': 'application/json, text/plain, */*',
			'Connection': 'keep-alive',
			'Referer': 'https://web.sd.lp1.acbaa.srv.nintendo.net/players/passport',
			'Authorization' : 'tmp',
			'Accept-Encoding': 'gzip, deflate, br',
			'Accept-Language': 'en-us'
		}
		self.user_gcookie = {
			'_dnt' : '1',
			'_ga' : 'GA1.2.235595523.1520818620',
			'_gtoken' : 'tmp'
		}
		self.user_pcookie = {
			'_dnt' : '1',
			'_ga' : 'GA1.2.235595523.1520818620',
			'_gtoken' : 'tmp',
			'_park_session' : 'tmp'
		}

	async def getNSOJSON(self, ctx, header, url):
		tokens = await self.nsotoken.getGameKey(ctx.user.id, 'ac')
		if tokens == None:
			await self.nsotoken.doGameKeyRefresh(ctx, 'ac')
			tokens = await self.nsotoken.getGameKey(ctx.user.id, 'ac')

		gtoken = tokens['gtoken']
		parktoken = tokens['park_session']
		bearer = tokens['ac_bearer']
		gtokenFlag = False

		if 'users' in url.lower() and '0x' not in url.lower():
			gtokenFlag = True
			self.user_gcookie['_gtoken'] = gtoken
			r = requests.get(url, headers=header, cookies=self.user_gcookie)
			thejson = json.loads(r.text)
		else:
			self.user_pcookie['_gtoken'] = gtoken
			self.user_pcookie['_park_session'] = parktoken
			self.user_auth_app_head['Authorization'] = f"Bearer {bearer}"
			r = requests.get(url, headers=header, cookies=self.user_pcookie)
			thejson = json.loads(r.text)

		if r.status_code == 401:
			await self.nsotoken.doGameKeyRefresh(ctx, 'ac')
			tokens = await self.nsotoken.getGameKeys(ctx.user.id)
			if tokens == None:
				return

			gtoken = tokens['ac']['gtoken']
			parktoken = tokens['ac']['park_session']
			bearer = tokens['ac']['ac_bearer']

			if gtokenFlag:
				self.user_gcookie['_gtoken'] = gtoken
				r = requests.get(url, headers=header, cookies=self.user_gcookie)
				thejson = json.loads(r.text)
			else:
				self.user_pcookie['_gtoken'] = gtoken
				self.user_pcookie['_park_session'] = parktoken
				self.user_auth_app_head['Authorization'] = f"Bearer {bearer}"
				r = requests.get(url, headers=header, cookies=self.user_pcookie)
				thejson = json.loads(r.text)

			if r.status_code == 401:
				print("FAILURE TO RENEW AC TOKENS")
				return None

		return thejson

	async def passport(self, ctx):
		if not await self.nsotoken.checkSessionPresent(ctx):
			await ctx.respond("You don't have a token setup with me! Please DM me !token with how to get one setup!")
			return

		userjson = await self.getNSOJSON(ctx, self.user_app_head, 'https://web.sd.lp1.acbaa.srv.nintendo.net/api/sd/v1/users')
		if userjson == None:
			return
		else:
			user = userjson['users'][0]

		detaileduser = await self.getNSOJSON(ctx, self.user_auth_app_head, f"https://web.sd.lp1.acbaa.srv.nintendo.net/api/sd/v1/users/{user['id']}/profile?language=en-US")
		landjson = await self.getNSOJSON(ctx, self.user_auth_app_head, f"https://web.sd.lp1.acbaa.srv.nintendo.net/api/sd/v1/lands/{user['land']['id']}/profile?language=en-US")
		profilepic = requests.get(user['image'])
		profileid = re.search('(?<=user_profile/).*(?=\?)', user['image']).group()

		embed = discord.Embed(colour=0x0004FF)
		embed.title = str(user['name']) + "'s Passport - Animal Crossing New Horizons"

		if self.webDir and self.hostedUrl:
			open(f'{self.webDir}/acprofiles/{str(profileid)}.jpg', 'wb').write(profilepic.content)
			embed.set_thumbnail(url=f'{self.hostedUrl}/acprofiles/{str(profileid)}.jpg')

		print("PROFILE: " + str(profileid))
		embed.add_field(name='Title', value=str(detaileduser['mHandleName']), inline=True)
		embed.add_field(name='Comment', value=str(detaileduser['mComment']), inline=True)
		embed.add_field(name='Registered On', value=f"{str(detaileduser['mTimeStamp']['month'])}/{str(detaileduser['mTimeStamp']['day'])}/{str(detaileduser['mTimeStamp']['year'])}", inline=True)
		embed.add_field(name='Island Name', value=user['land']['name'], inline=True)

		npcstring = ''

		for npc in landjson['mNormalNpc']:
			npcstring+=f"{npc['name']} - {str(npc['birthMonth'])}/{str(npc['birthDay'])}\n"

		embed.add_field(name="NPC's (Name - Birthday)", value=npcstring, inline=True)

		await ctx.respond(embed=embed)
		print("Got a passport!")
