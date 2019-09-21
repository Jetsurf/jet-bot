#!/usr/bin/python3

import discord
import asyncio
import sys
import subprocess
import json
import time
import vserver
import mysqlinfo
import serverutils
import nsohandler
import urllib
import urllib.request
import requests
import nsotoken
import aiomysql
import commandparser
import splatinfo
from subprocess import call
from ctypes import *

client = discord.Client()
splatInfo = splatinfo.SplatInfo()
commandParser = commandparser.CommandParser()
mysqlConnect = None
nsoHandler = None
nsoTokens = None
serverVoices = {}
serverAdmins = {}
serverUtils = None
token = ''
owners = None
dev = 1
soundsDir = ''
commands = ''
configData = None
head = {}
url = ''

def loadConfig():
	global token, soundsDir, commands, mysqlConnect, dev, head, url
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
			print('No ID/Token for discordbots.org, skipping')

		mysqlConnect = mysqlinfo.mysqlInfo(configData['mysql_host'], configData['mysql_user'], configData['mysql_pw'], configData['mysql_db'])

		print('Config Loaded')
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
		serverAdmins[id.id] = []
		for mem in id.members:
			try:
				if mem.guild_permissions.administrator and mem not in serverAdmins[id.id]:
					serverAdmins[id.id].append(mem)
			except:
					return
				
@client.event
async def on_member_update(before, after):
	if before.guild_permissions.administrator or after.guild_permissions.administrator:
		scanAdmins(id=before.guild)

@client.event
async def on_guild_role_update(before, after):
	scanAdmins(id=before.guild)

@client.event
async def on_ready():
	global client, soundsDir, mysqlConnect, serverUtils, serverVoices
	global nsoHandler, nsoTokens, head, url, dev, owners, commandParser

	print('Logged in as,', client.user.name, client.user.id)

	#Get owners from Discord team api
	print("Loading owners...")
	theapp = await client.application_info()
	owners = [x.id for x in theapp.team.members]

	await client.change_presence(status=discord.Status.online, activity=discord.Game("Use !help for directions!"))

	if dev == 0:
		print('I am in ' + str(len(client.guilds)) + ' servers, posting to discordbots.org')
		body = { 'server_count' : len(client.guilds) }
		requests.post(url, headers=head, json=body)
	else:	
		print('I am in ' + str(len(client.guilds)) + ' servers')

	print("Doing Startup...")
	for server in client.guilds:
		#Don't recreate serverVoices on reconnect
		if server.id not in serverVoices:
			serverVoices[server.id] = vserver.voiceServer(client, mysqlConnect, server.id, soundsDir)

	if nsoHandler == None:
		commandParser.setMysqlInfo(mysqlConnect)
		commandParser.setUserid(client.user.id)
		serverUtils = serverutils.serverUtils(mysqlConnect)
		nsoTokens = nsotoken.Nsotoken(client, mysqlConnect)
		nsoHandler = nsohandler.nsoHandler(client, mysqlConnect, nsoTokens)
	scanAdmins(startup=1)
	print('Done\n------')
	sys.stdout.flush()
	
@client.event
async def on_member_remove(member):
	global serverAdmins, serverUtils

	for mem in serverAdmins[member.guild.id]:
		if mem.id != client.user.id and serverUtils.checkDM(mem.id, member.guild.id):
			await mem.send(member.name + " left " + member.guild.name)
			
@client.event
async def on_guild_join(server):
	global serverVoices, head, url, dev, owners
	print("I joined server: " + server.name)
	serverVoices[server.id] = vserver.voiceServer(client, mysqlConnect, server.id, soundsDir)
	scanAdmins(id=server)

	if dev == 0:
		print('I am now in ' + str(len(client.guilds)) + ' servers, posting to discordbots.org')
		body = { 'server_count' : len(client.guilds) }
		r = requests.post(url, headers=head, json=body)
	else:
		print('I am now in ' + str(len(client.guilds)) + ' servers')
	sys.stdout.flush()

@client.event
async def on_guild_remove(server):
	global serverVoices, head, url, dev, owners
	print("I left server: " + server.name)
	serverVoices[server.id] = None

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
	global serverVoices, serverAdmins, soundsDir, serverUtils
	global nsoHandler, owners, commands, commandParser

	# Filter out bots and system messages
	if message.author.bot or message.type != discord.MessageType.default:
		return

	command = message.content.lower()
	channel = message.channel

	if message.guild == None:
		if message.author.id in owners:
			if '!servers' in message.content:
				numServers = str(len(client.guilds))
				serverNames = ""
				for server in client.guilds:
					serverNames = serverNames + str(server.name + '\n')
				await channel.send("I am in: " + str(numServers) + " servers\n" + serverNames)
			elif '!restart' in message.content:
				await channel.send("Going to restart!")
				await client.close()
				sys.stderr.flush()
				sys.stdout.flush()
				sys.exit(0)
			elif '!cmdreport' in message.content:
				await serverUtils.report_cmd_totals(message)
		if '!token' in command:
			await nsoTokens.login(message)
		elif '!deletetoken' in command:
				await nsoTokens.delete_tokens(message)
		elif '!storedm' in command:
			await channel.send("Sorry, for performance reasons, you cannot DM me !storedm :frowning:")
		return
	else:
		theServer = message.guild.id

	if command.startswith('!prefix'):
		await message.channel.send("The command prefix for this server is: " + commandParser.getPrefix(theServer))
	elif message.content.startswith('!help') and commandParser.getPrefix(theServer) not in '!':
		await serverUtils.print_help(message, commands, commandParser.getPrefix(theServer))
	elif ('pizza' in command and 'pineapple' in command) or ('\U0001F355' in message.content and '\U0001F34D' in message.content):
		await channel.send('Don\'t ever think pineapple and pizza go together ' + message.author.name + '!!!')		

	parsed = commandParser.parse(theServer, message.content)
	if parsed == None:
		return

	cmd = parsed['cmd']
	args = parsed['args']

	#Don't just fail if command count can't be incremented
	try:
		serverUtils.increment_cmd(message, cmd)
	except:
		print("Failed to increment command... issue with MySQL?")

	if cmd == "admin":
		if message.author in serverAdmins[theServer]:
			subcommand = args[0].lower()
			if subcommand == 'playlist':
				await serverVoices[theServer].addPlaylist(message)
			elif subcommand == 'blacklist':
				await serverVoices[theServer].addBlacklist(message)
			elif subcommand == 'wtfboom':
				await serverVoices[theServer].playWTF(message)
			elif subcommand == 'tts':
				await channel.send(args[1:].join(" "), tts=True)
			elif subcommand == 'dm':
				subcommand2 = args[1].lower()
				if subcommand2 == 'add':
					await serverUtils.addDM(message)
				elif subcommand2 == 'remove':
					await serverUtils.removeDM(message)
			elif subcommand == 'prefix':
				if (len(args) == 1):
					await channel.send("Current command prefix is: " + commandParser.getPrefix(theServer))
				elif (len(args) != 2) or (len(args[1]) != 1):
					await channel.send("Usage: ```admin prefix <char>``` where *char* is a single character")
				else:
					commandParser.setPrefix(theServer, args[1])
		else:
			await channel.send(message.author.name + " you are not an admin... :cop:")
	elif cmd == 'alive':
		await channel.send("Hey " + message.author.name + ", I'm alive so shut up! :japanese_goblin:")
	elif cmd == 'rank':
		await nsoHandler.getRanks(message)
	elif cmd == 'order':
		await nsohandler.orderGear(message)
	elif cmd == 'stats':
		await nsohandler.getStats(message)
	elif cmd == 'srstats':
		await nsoHandler.getSRStats(message)
	elif cmd == 'storedm':
		await nsoHandler.addStoreDM(message)
	elif cmd == 'github':
		await channel.send('Here is my github page! : https://github.com/Jetsurf/jet-bot')
	elif cmd == 'support':
		await channel.send('Here is a link to my support server: https://discord.gg/TcZgtP5')
	elif cmd == 'commands' or cmd == 'help':
		await serverUtils.print_help(message, commands, commandParser.getPrefix(theServer))
	elif cmd == 'sounds':
		theSounds = subprocess.check_output(["ls", soundsDir])
		theSounds = theSounds.decode("utf-8")
		theSounds = theSounds.replace('.mp3', '')
		theSounds = theSounds.replace('\n', ', ')
		await channel.send("Current Sounds:\n```" + theSounds + "```")
	elif cmd == 'join':
		if len(args) > 0:
			await serverVoices[theServer].joinVoiceChannel(message, channelName=' '.join(args[0:]))
		else:
			await serverVoices[theServer].joinVoiceChannel(message)
	elif cmd == 'currentmaps':
		await nsoHandler.maps(message)
	elif cmd == 'nextmaps':
		await nsoHandler.maps(message, offset=min(11, message.content.count('next')))
	elif cmd == 'currentsr':
		await nsoHandler.srParser(message)
	elif cmd == 'splatnetgear':
		await nsoHandler.gearParser(message)
	elif cmd == 'nextsr':
		await nsoHandler.srParser(message, 1)
	elif (cmd == 'us') or (cmd == 'eu') or (cmd == 'jp'):
		await setCRole(message)
	elif serverVoices[theServer].vclient is not None:
		if cmd == 'currentsong':
			if serverVoices[theServer].source is not None:
				await channel.send('Currently Playing Video: ' + serverVoices[theServer].source.yturl)
			else:
				await channel.send('I\'m not playing anything.')
		elif cmd == 'leavevoice':
			await serverVoices[theServer].vclient.disconnect()
		elif cmd == 'playrandom':
			if len(args) > 0:
				if args[0].isdigit():
					await serverVoices[theServer].playRandom(message, int(args[0]))
				else:
					await message.channel.send("Num to play must be a number")
			else:
				await serverVoices[theServer].playRandom(message, 1)
		elif cmd == 'play':
			await serverVoices[theServer].setupPlay(message)
		elif cmd == 'skip':
			await serverVoices[theServer].stop(message)
		elif (cmd == 'end') or (cmd == 'stop'):
			serverVoices[theServer].end()
		elif cmd == 'volume':
			vol = int(command.split(' ')[1])
			if not vol.isdigit():
				await message.channel.send("Volume must be a digit 1-60")
				return
			if vol > 60:
				vol = 60
			await channel.send("Setting Volume to " + str(vol) + "%")
			serverVoices[theServer].source.volume = float(vol / 100)
		elif cmd == 'queue':
			await serverVoices[theServer].printQueue(message)
		else:
			await serverVoices[theServer].playSound(command, message)
	elif (cmd == 'map') or (cmd == 'maps'):
		await cmdMaps(message, args)
	elif (cmd == 'weapon') or (cmd == 'weapons'):
		await cmdWeaps(message, args)

	sys.stdout.flush()
	sys.stderr.flush()

async def cmdMaps(message, args):
	if len(args) == 0:
		await message.channel.send("Try 'maps help' for help")
		return

	subcommand = args[0].lower()
	if subcommand == "help":
		await message.channel.send("**maps random [n]**: Generate a list of random maps\n"
			"**maps stats MAP**: Show player stats for MAP")
		return
	elif subcommand == "list":
		print("TODO")
		return
	elif subcommand == "stats":
		if len(args) > 1:
			themap = " ".join(args[1:])
			match = splatInfo.matchMaps(themap)
			if not match.isValid():
				await message.channel.send(match.errorMessage())
				return
			id = match.get().id()
			await nsoHandler.mapParser(message, id)
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
			await message.channel.send("Random map: " + splatInfo.getRandomMap().name())
		else:
			out = "Random maps:\n"
			for i in range(count):
				out += "%d: %s\n" % (i + 1, splatInfo.getRandomMap().name())
			await message.channel.send(out)
	else:
		await message.channel.send("Unknown subcommand. Try 'maps help'")

async def cmdWeaps(message, args):
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
			match = splatInfo.matchWeapons(theWeapon)
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
			actualSub = splatInfo.matchSubweapons(theSub)
			if not actualSub.isValid():
				await message.channel.send(actualSub.errorMessage())
				return
			weaponsList = splatInfo.getWeaponsBySub(actualSub.get())
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
			actualSpecial = splatInfo.matchSpecials(theSpecial)
			if not actualSpecial.isValid():
				await message.channel.send(actualSpecial.errorMessage())
				return
			weaponsList = splatInfo.getWeaponsBySpecial(actualSpecial.get())
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
			match = splatInfo.matchWeapons(theWeapon)
			if not match.isValid():
				await message.channel.send(match.errorMessage())
				return
			id = match.get().id()
			await nsoHandler.weaponParser(message, id)
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
			await message.channel.send("Random weapon: " + splatInfo.getRandomWeapon().name())
		else:
			out = "Random weapons:\n"
			for i in range(count):
				out += "%d: %s\n" % (i + 1, splatInfo.getRandomWeapon().name())
			await message.channel.send(out)
	else:
		await message.channel.send("Unknown subcommand. Try 'weapons help'")

#Setup
loadConfig()
if dev == 0:
	sys.stdout = open('./discordbot.log', 'a')
	sys.stderr = open('./discordbot.err', 'a')

print('**********NEW SESSION**********')
print('Logging into discord')

sys.stdout.flush()
client.run(token)
