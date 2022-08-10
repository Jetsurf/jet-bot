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

	async def passport(self, ctx):
		await ctx.defer()

		nso = await self.nsotoken.get_nso_client(ctx.user.id)
		print(f"DEBUG: TOKENS: {str(nso.get_keys())}")
		userjson = nso.acnh.get_users_json()
		if userjson == None:
			await ctx.respond("No token...")
			return  # TODO: Error message?

		if userjson == None:
			#TODO: Best place to break if "account" doesn't have ACNH?
			return
		else:
			user = userjson['users'][0]

		detaileduser = nso.acnh.get_detailed_user_json()
		landjson = nso.acnh.get_lands_json()
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

	async def ac_emote(self, ctx, emote):
		await ctx.defer()

		nso = await self.nsotoken.get_nso_client(ctx.user.id)
		resp = nso.acnh.send_emote(emote)
		if resp == None:
			await ctx.respond("No token...")
			return
		else:
			await ctx.respond(f"Stuff happened? Here's resp: ```{resp}```")
			return

	async def get_ac_emotes(self, ctx):
		await ctx.defer()

		nso = await self.nsotoken.get_nso_client(ctx.user.id)
		resp = nso.acnh.get_emotes()
		if resp == None:
			await ctx.respond("No token...")
			return
		else:
			emotes={}
			for emote in resp['emoticons']:
				emote.pop('url')

			await ctx.respond(f"Stuff happened? Here's resp: ```{resp}```")
			return

	async def ac_message(self, ctx, msg):
		await ctx.defer()

		nso = await self.nsotoken.get_nso_client(ctx.user.id)
		resp = nso.acnh.send_message(msg)
		if resp == None:
			await ctx.respond("No token...")
			return
		else:
			await ctx.respond(f"Stuff happened? Here's resp: ```{resp}```")
			return