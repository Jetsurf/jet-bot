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
import nsotoken
from subprocess import call

client = discord.Client()
mysqlConnect = None
nsoHandler = None
nsoTokens = None
serverVoices = {}
serverAdmins = {}
serverPunish = {}
token = ''
log = ''
soundsDir = ''
commands = ''
configData = None

def loadConfig(firstRun=0):
	global token, adminIDs, soundsDir, lists, commands, mysqlConnect

	try:
		with open('./discordbot.json', 'r') as json_config:
			configData = json.load(json_config)

		if firstRun == 1:
			token = configData['token']

		soundsDir = configData['soundsdir']
		commands = configData['commands']
		mysqlConnect = mysqlinfo.mysqlInfo(configData['mysql_host'], configData['mysql_user'], configData['mysql_pw'], configData['mysql_db'])

		print('Config Loaded')
		if firstRun == 0:
			return True
	except Exception as e:
		print('Failed to load config: ' + str(e))
		if firstRun == 1:
			quit(1)
		else:
			return False

async def setCRole(message):
	us = discord.utils.get(message.server.roles, name='Americas')
	eu = discord.utils.get(message.server.roles, name='Europe')
	jp = discord.utils.get(message.server.roles, name='Japan/Asia')

	await client.remove_roles(message.author, us)
	await client.remove_roles(message.author, eu)
	await client.remove_roles(message.author, jp)

	if message.content.startswith('!us'):
		await client.add_roles(message.author, us)
	elif message.content.startswith('!eu'):
		await client.add_roles(message.author, eu)
	elif message.content.startswith('!jp'):
		await client.add_roles(message.author, jp)

	await client.add_reaction(message, '👍')

@asyncio.coroutine
async def joinVoiceChannel(channelName, message):
	await serverVoices[message.server.id].joinVoiceChannel(channelName, message)

def scanAdmins():
	global serverAdmins

	for server in client.servers:
		serverAdmins[server.id] = []
		for mem in server.members:
			if mem.server_permissions.administrator and mem not in serverAdmins[server.id]:
				serverAdmins[server.id].append(mem)
				
@client.event
async def on_member_update(before, after):
	scanAdmins()

@client.event
async def on_role_update(before, after):
	scanAdmins()

@client.event
async def on_ready():
	global client, soundsDir, lists, mysqlConnect, serverPunish, nsohandler, nsoTokens

	print('Logged in as,', client.user.name, client.user.id)
	print('------')
	await client.change_presence(game=discord.Game(name="Use !help for directions!", type=0))
	for server in client.servers:
		serverVoices[server.id] = vserver.voiceServer(client, mysqlConnect, server.id, soundsDir)
		serverPunish[server.id] = punish.Punish(client, server.id, mysqlConnect)

	nsohandler = nsohandler.nsoHandler(client, mysqlConnect)
	nsoTokens = nsotoken.Nsotoken(client, nsohandler)
	scanAdmins()
	
@client.event
async def on_member_remove(member):
	global serverAdmins, serverPunish

	theServer = member.server.id
	for mem in serverAdmins[theServer]:
		if mem.id != client.user.id and serverPunish[theServer].checkDM(mem.id):
			await client.send_message(mem, member.name + " left " + member.server.name)
			
@client.event
async def on_server_join(server):
	global client, soundsDir, serverVoices, serverPunish
	print("I joined server: " + server.name)
	sys.stdout.flush()
	serverVoices[server.id] = vserver.voiceServer(client, mysqlConnect, server.id, soundsDir)
	serverPunish[server.id] = punish.Punish(client, server.id, mysqlConnect)

@client.event
async def on_message(message):
	global serverVoices, serverAdmins, soundsDir, serverPunish, nsohandler

	command = message.content.lower()
	
	if message.server == None:
		if '!token' in command:
			#await nsohandler.addToken(message)
			await nsoTokens.login(message)
		return
	else:
		theServer = message.server.id

	if serverPunish[theServer].checkSquelch(message.author):
		await client.delete_message(message)
		return	

	if message.author.bot:
		return
	if message.author.name == client.user.name:
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
				await client.send_message(message.channel, message.content[11:], tts=True)
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
			await client.send_message(message.channel, message.author.name + " you are not an admin... :cop:")
	elif command.startswith('!alive'):
		await client.send_message(message.channel, "Hey " + message.author.name + ", I'm alive so shut up! :japanese_goblin:")
	elif command.startswith('!rank'):
		await nsohandler.getRanks(message)
	elif command.startswith('!order'):
		await nsohandler.orderGear(message)
	elif command.startswith('!stats'):
		await nsohandler.getStats(message)
	elif command.startswith('!github'):
		await client.send_message(message.channel, 'Here is my github page! : https://github.com/Jetsurf/jet-bot')
	elif command.startswith('!commands') or command.startswith('!help'):
		theString = ''
		with open(commands, 'r') as f:
			for line in f:
				theString = theString + line
		await client.send_message(message.channel, theString)
	elif command.startswith('!sounds'):
		theSounds = subprocess.check_output(["ls", soundsDir])
		theSounds = theSounds.decode("utf-8")
		theSounds = theSounds.replace('.mp3', '')
		theSounds = theSounds.replace('\n', ', ')
		await client.send_message(message.channel, "Current Sounds:\n```" + theSounds + "```")
	elif command.startswith('!join'):
		if len(message.content) > 6:
			await joinVoiceChannel(message.content.split(" ", 1)[1], message)
		else:
			await joinVoiceChannel(command, message)
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
		await client.send_message(message.channel, 'Don\'t ever think pineapple and pizza go together ' + message.author.name + '!!!')
	elif serverVoices[theServer].vclient is not None:
		if command.startswith('!currentsong'):
			if serverVoices[theServer].ytPlayer is not None:
				await client.send_message(message.channel, 'Currently Playing Video: ' + serverVoices[theServer].ytPlayer.url)
			else:
				await client.send_message(message.channel, 'I\'m not playing anything.')
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
			await client.send_message(message.channel, "Setting Volume to " + str(vol) + "%")
			serverVoices[theServer].ytPlayer.volume = float(vol / 100)
		elif command.startswith('!queue'):
			await serverVoices[theServer].printQueue(message)
		elif command.startswith('!'):
			await serverVoices[theServer].playSound(command, message)
	sys.stdout.flush()

#Setup
sys.stdout = open('./discordbot.log', 'a')

print('**********NEW SESSION**********')
loadConfig(firstRun=1)

print('Logging into discord')

sys.stdout.flush()
client.run(token)
