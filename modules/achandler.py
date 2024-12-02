import discord, asyncio
import mysqlhandler, nsotoken
import time, requests
import json, os, io
import urllib, urllib.request
from PIL import Image
import re

class acHandler():
	def __init__(self, client, mysqlHandler, nsotoken, configData):
		self.client = client
		self.sqlBroker = mysqlHandler
		self.nsotoken = nsotoken
		self.webDir = configData.get('web_dir')

	async def passport(self, ctx):
		await ctx.defer()

		nso = await self.nsotoken.get_nso_client(ctx.user.id)		
		if not nso.is_logged_in():
			await ctx.respond("You don't have a NSO token setup! Run /token to get started.")
			return

		userjson = nso.acnh.get_users_json()
		if userjson == None:
			await ctx.respond("Something went wrong. Please let my owners in my support guild know this broke as it's a new feature!")
			print(f"ACNH: Passport call returned nothing: userid {str(ctx.user.id)}")
			#TODO: Best place to break if "account" doesn't have ACNH? - TO TEST
			return
		else:
			user = userjson['users'][0]

		detaileduser = nso.acnh.get_detailed_user_json()
		landjson = nso.acnh.get_lands_json()
		profilepic = Image.open(io.BytesIO(requests.get(user['image']).content))

		embed = discord.Embed(colour=0x0004FF)
		embed.title = str(user['name']) + "'s Passport - Animal Crossing New Horizons"

		image_io = io.BytesIO()
		profilepic.save(image_io, 'JPEG')
		image_io.seek(0)
		file = discord.File(fp = image_io, filename = 'profilepic.jpg', description = 'Passport')
		embed.set_thumbnail(url = "attachment://profilepic.jpg")

		embed.add_field(name='Title', value=str(detaileduser['mHandleName']), inline=True)
		embed.add_field(name='Comment', value=str(detaileduser['mComment']), inline=True)
		embed.add_field(name='Registered On', value=f"{str(detaileduser['mTimeStamp']['month'])}/{str(detaileduser['mTimeStamp']['day'])}/{str(detaileduser['mTimeStamp']['year'])}", inline=True)
		embed.add_field(name='Island Name', value=user['land']['name'], inline=True)

		npcstring = ''

		for npc in landjson['mNormalNpc']:
			npcstring+=f"{npc['name']} - {str(npc['birthMonth'])}/{str(npc['birthDay'])}\n"

		embed.add_field(name="NPC's (Name - Birthday)", value=npcstring, inline=True)

		await ctx.respond(embed=embed, file=file)
		print("Got a passport!")

	async def ac_emote(self, ctx, emote):
		await ctx.defer()

		nso = await self.nsotoken.get_nso_client(ctx.user.id)
		if not nso.is_logged_in():
			await ctx.respond("You don't have a NSO token setup! Run /token to get started.")
			return
		
		resp = nso.acnh.send_emote(emote)
		if resp == None:
			await ctx.respond("Something went wrong. Please let my owners in my support guild know this broke as it's a new feature!")
			print(f"ACNH: Emote call returned nothing: userid {str(ctx.user.id)} with emote {emote}")
		elif 'code' in resp and resp['code'] == '1001':
			await ctx.respond("You aren't online in ACNH! Go talk to Orville at the airport to go online.")
		elif 'code' in resp and resp['code'] == '3002':
			await ctx.respond("Invalid emote! Run /acnh getemotes to see your available emotes. Must match exactly.")
		elif 'status' in resp and resp['status'] == 'success':
			await ctx.respond("Emote sent!")
		else:
			await ctx.respond("Something went wrong! Please let me owners know this broke in my support guild, as it's a new feature!")
			print(f"ACNH: Emote call returned something unexpected: {resp} with user {str(ctx.user.id)} and emote {emote}")

		return

	async def get_ac_emotes(self, ctx):
		await ctx.defer()

		nso = await self.nsotoken.get_nso_client(ctx.user.id)
		if not nso.is_logged_in():
			await ctx.respond("You don't have a NSO token setup! Run /token to get started.")
			return

		resp = nso.acnh.get_emotes()
		if resp == None:
			await ctx.respond("Something went wrong. Please let my owners know this broke as it's a new feature!")
			return

		embed = discord.Embed(colour=0x0004FF)
		embed.title = "Available ACNH Emotes"
		emoteString = ""
		emotes={}
		for emote in resp['emoticons']:
			emote.pop('url')
			emoteString += f"{emote['label']}\n"

		embed.add_field(name="Emotes", value=emoteString, inline=False)
		await ctx.respond(embed=embed)
		return

	async def ac_message(self, ctx, msg):
		await ctx.defer()

		nso = await self.nsotoken.get_nso_client(ctx.user.id)
		if not nso.is_logged_in():
			await ctx.respond("You don't have a NSO token setup! Run /token to get started.")
			return
		
		resp = nso.acnh.send_message(msg)
		if resp == None:
			await ctx.respond("Something went wrong. Please let my owners in my support guild know this broke as it's a new feature!")
			print(f"ACNH: Message call returned nothing: userid {str(ctx.user.id)} with emote {emote}")
		elif 'code' in resp and resp['code'] == '1001':
			await ctx.respond("You aren't online in ACNH! Go talk to Orville at the airport to go online.")
		elif 'status' in resp and resp['status'] == 'success':
			await ctx.respond("Message sent!")
		else:
			await ctx.respond("Something went wrong! Please let me owners know this broke in my support guild, as it's a new feature!")
			print(f"ACNH: Message call returned something unexpected: {resp} with user {str(ctx.user.id)} and emote {emote}")

		return