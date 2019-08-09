#!/usr/bin/python3

import discord
import asyncio
import sys
import subprocess
import json
import time
import vserver
import mysqlinfo
import punish
import nsohandler
import urllib
import urllib.request
import requests
import nsotoken
import aiomysql
from subprocess import call
from ctypes import *

client = discord.Client()
mysqlConnect = None
nsoHandler = None
nsoTokens = None
serverVoices = {}
serverAdmins = {}
serverPunish = {}
token = ''
owners = None
log = ''
dev = 1
soundsDir = ''
commands = ''
configData = None
head = {}
url = ''

def loadConfig():
	global token, adminIDs, soundsDir, lists, commands, mysqlConnect, dev, head, url, owners
	try:
		with open('./discordbot.json', 'r') as json_config:
			configData = json.load(json_config)

		token = configData['token']
		soundsDir = configData['soundsdir']
		commands = configData['commands']
		try:
			dbid = configData['discordbotid']
			dbtoken = configData['discordbottok']
			head = { 'Authorization': dbtoken }
			url = 'https://discordbots.org/api/bots/' + str(dbid) + '/stats'
			dev = 0
		except:
			print('No ID/Token for discordbot.org, skipping')

		owners = configData['owner_ids']
		mysqlConnect = mysqlinfo.mysqlInfo(configData['mysql_host'], configData['mysql_user'], configData['mysql_pw'], configData['mysql_db'])

		print('Config Loaded')
		discord.opus.load_opus('libopus.so.0')
		if discord.opus.is_loaded():
			print("Opus Library Loaded, continuing")
		else:
			print("Failed to load Opus Library... quitting")
			quit(1)
	except Exception as e:
		print('Failed to load config: ' + str(e))
		quit(1)

async def setCRole(message):
	us = discord.utils.get(message.guild.roles, name='Americas')
	eu = discord.utils.get(message.guild.roles, name='Europe')
	jp = discord.utils.get(message.guild.roles, name='Japan/Asia')

	await message.author.remove_roles(us)
	await message.author.remove_roles(eu)
	await message.author.remove_roles(jp)

	if message.content.startswith('!us'):
		await message.author.add_roles(us)
	elif message.content.startswith('!eu'):
		await message.author.add_roles(eu)
	elif message.content.startswith('!jp'):
		await message.author.add_roles(jp)

	await message.add_reaction('👍')

def scanAdmins(startup=0, id=None):
	global serverAdmins

	if startup == 1:
		for server in client.guilds:
			serverAdmins[server.id] = []
			for mem in server.members:
				if mem.guild_permissions.administrator and mem not in serverAdmins[server.id]:
					serverAdmins[server.id].append(mem)

	else:
		serverAdmins[id] = []
		for mem in id.members:
			try:
				if mem.guild_permissions.administrator and mem not in serverAdmins[id.id]:
					serverAdmins[server].append(mem)
			except:
					return
				
@client.event
async def on_member_update(before, after):
	if before.guild_permissions.administrator or after.guild_permissions.administrator:
		scanAdmins(id=before.guild)

@client.event
async def on_server_role_update(before, after):
	scanAdmins(id=before.guild)

@client.event
async def on_ready():
	global client, soundsDir, lists, mysqlConnect, serverPunish, nsohandler, nsoTokens, head, url, dev

	print('Logged in as,', client.user.name, client.user.id)

	game = discord.Game("Use !help for directions!")
	
	await client.change_presence(status=discord.Status.online, activity=game)
	for server in client.guilds:
		serverVoices[server.id] = vserver.voiceServer(client, mysqlConnect, server.id, soundsDir)
		serverPunish[server.id] = punish.Punish(client, server.id, mysqlConnect)

	if dev == 0:
		print('I am in ' + str(len(client.guilds)) + ' servers, posting to discordbots.org')
		body = { 'server_count' : len(client.guilds) }
		requests.post(url, headers=head, json=body)
	else:	
		print('I am in ' + str(len(client.guilds)) + ' servers')

	print('------')
	sys.stdout.flush()
	nsohandler = nsohandler.nsoHandler(client, mysqlConnect)
	nsoTokens = nsotoken.Nsotoken(client, nsohandler)
	scanAdmins(startup=1)
	
@client.event
async def on_member_remove(member):
	global serverAdmins, serverPunish

	theServer = member.guild.id
	for mem in serverAdmins[theServer]:
		if mem.id != client.user.id and serverPunish[theServer].checkDM(mem.id):
			await mem.send(member.name + " left " + member.guild.name)
			
@client.event
async def on_server_join(server):
	global client, soundsDir, serverVoices, serverPunish, head, url, dev
	print("I joined server: " + server.name)
	serverVoices[server.id] = vserver.voiceServer(client, mysqlConnect, server.id, soundsDir)
	serverPunish[server.id] = punish.Punish(client, server.id, mysqlConnect)

	if dev == 0:
		print('I am now in ' + str(len(client.guilds)) + ' servers, posting to discordbots.org')
		body = { 'server_count' : len(client.guilds) }
		r = requests.post(url, headers=head, json=body)
	else:
		print('I am now in ' + str(len(client.guilds)) + ' servers')
	sys.stdout.flush()

@client.event
async def on_server_remove(server):
	global serverVoices, serverPunish, head, url, dev
	print("I left server: " + server.name)
	serverVoices[server.id] = None
	serverPunish[server.id] = None

	if dev == 0:
		print('I am now in ' + str(len(client.guilds)) + ' servers, posting to discordbots.org')
		body = { 'server_count' : len(client.guilds) }
		r = requests.post(url, headers=head, json=body)
	else:
		print('I am now in ' + str(len(client.guilds)) + ' servers')
	sys.stdout.flush()

test = 0
@client.event
async def on_message(message):
	global serverVoices, serverAdmins, soundsDir, serverPunish, nsohandler, owners

	command = message.content.lower()
	channel = message.channel
	if message.guild == None:
		if message.author.id in owners:
			if '!servers' in message.content:
				numServers = str(len(client.servers))
				serverNames = ""
				for server in client.servers:
					serverNames = serverNames + str(server.name + '\n')
				await channel.send("I am in: " + str(numServers) + " servers\n" + serverNames)
			if '!restart' in message.content:
				await channel.send("Going to restart!")
				await client.close()
				sys.stdout.flush()
				sys.exit(0)
		if message.author.bot:
			return
		if '!token' in command:
			await nsoTokens.login(message)
		if '!storedm' in command:
			await channel.send("Sorry, for performance reasons, you cannot DM me !storedm :frowning:")
		return
	else:
		theServer = message.guild.id

	if message.author.bot:
		return
	if message.author.name == client.user.name:
		return

	if serverPunish[theServer].checkSquelch(message.author):
		await message.delete()
		return	
	if command.startswith("!admin"):
		if message.author in serverAdmins[theServer]:
			if 'playlist' in message.content:
				await serverVoices[theServer].addPlaylist(message)
			elif 'blacklist' in message.content:
				await serverVoices[theServer].addBlacklist(message)
			elif 'wtfboom' in message.content:
				await serverVoices[theServer].playWTF(message)
			elif 'tts' in message.content:
				await channel.send(message.content[11:], tts=True)
			elif 'squelch current' in message.content:
				await serverPunish[theServer].getSquelches(message)
			elif 'squelch log' in message.content:
				await serverPunish[theServer].getSquelches(message, all=1)
			elif 'unsquelch' in message.content:
				await serverPunish[theServer].removeSquelch(message)
			elif 'squelch' in message.content:
				await serverPunish[theServer].doSquelch(message)
			elif 'dm add' in message.content:
				await serverPunish[theServer].addDM(message)
			elif 'dm remove' in message.content:
				await serverPunish[theServer].removeDM(message)
		else:
			await channel.send_message(message.author.name + " you are not an admin... :cop:")
	elif command.startswith('!alive'):
		await channel.send("Hey " + message.author.name + ", I'm alive so shut up! :japanese_goblin:")
	elif command.startswith('!rank'):
		await nsohandler.getRanks(message)
	elif command.startswith('!order'):
		await nsohandler.orderGear(message)
	elif command.startswith('!stats'):
		await nsohandler.getStats(message)
	elif command.startswith('!srstats'):
		await nsohandler.getSRStats(message)
	elif command.startswith('!storedm'):
		await nsohandler.addStoreDM(message)
	elif command.startswith('!github'):
		await channel.send('Here is my github page! : https://github.com/Jetsurf/jet-bot')
	elif command.startswith('!commands') or command.startswith('!help'):
		embed = discord.Embed(colour=0x2AE5B8)
		embed.title = "Here is how to control me!"
		with open(commands, 'r') as f:
			for line in f:
				embed.add_field(name=line.split(":")[0], value=line.split(":")[1], inline=False)
			embed.set_footer(text="If you want something added or want to report a bug/error, tell jetsurf#8514...")
		await channel.send(embed=embed)
	elif command.startswith('!sounds'):
		theSounds = subprocess.check_output(["ls", soundsDir])
		theSounds = theSounds.decode("utf-8")
		theSounds = theSounds.replace('.mp3', '')
		theSounds = theSounds.replace('\n', ', ')
		await channel.send("Current Sounds:\n```" + theSounds + "```")
	elif command.startswith('!join'):
		if len(message.content) > 6:
			await serverVoices[theServer].joinVoiceChannel(message.content.split(" ", 1)[1], message)
		else:
			await serverVoices[theServer].joinVoiceChannel(command, message)
	elif command.startswith('!currentmaps'):
		await nsohandler.maps(message)
	elif 'nextmaps' in command and '!' in command:
		await nsohandler.maps(message, offset=min(11, message.content.count('next')))
	elif command.startswith('!currentsr'):
		await nsohandler.srParser(message)
	elif command.startswith('!splatnetgear'):
		await nsohandler.gearParser(message)
	elif command.startswith('!nextsr'):
		await nsohandler.srParser(message, 1)
	elif command.startswith('!us') or message.content.startswith('!eu') or message.content.startswith('!jp'):
		await setCRole(message)
	elif ('pizza' in command and 'pineapple' in command) or ('\U0001F355' in message.content and '\U0001F34D' in message.content):
		await channel.send('Don\'t ever think pineapple and pizza go together ' + message.author.name + '!!!')
	elif serverVoices[theServer].vclient is not None:
		if command.startswith('!currentsong'):
			if serverVoices[theServer].source is not None:
				await channel.send('Currently Playing Video: ' + serverVoices[theServer].source.url)
			else:
				await channel.send('I\'m not playing anything.')
		elif command.startswith('!leavevoice'):
			await serverVoices[theServer].vclient.disconnect()
		elif command.startswith('!playrandom'):
			if len(command) > 11:
				await serverVoices[theServer].playRandom(message, int(message.content.split(' ')[1]))
			else:
				await serverVoices[theServer].playRandom(message, 1)
		elif command.startswith('!play'):
			await serverVoices[theServer].setupPlay(message)
		elif command.startswith('!skip'):
			await serverVoices[theServer].stop(message)
		elif command.startswith('!end') or command.startswith('!stop'):
			serverVoices[theServer].end()
		elif command.startswith('!volume'):
			vol = int(command.split(' ')[1])
			if vol > 60:
				vol = 60
			await channel.send("Setting Volume to " + str(vol) + "%")
			serverVoices[theServer].source.volume = float(vol / 100)
		elif command.startswith('!queue'):
			await serverVoices[theServer].printQueue(message)
		elif command.startswith('!'):
			await serverVoices[theServer].playSound(command, message)
	sys.stdout.flush()
	sys.stderr.flush()

#Setup
loadConfig()
if dev == 0:
	sys.stdout = open('./discordbot.log', 'a')
	sys.stderr = open('./discordbot.err', 'a')

print('**********NEW SESSION**********')
print('Logging into discord')

sys.stdout.flush()
client.run(token)