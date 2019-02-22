#!/usr/bin/python3

import discord
import asyncio
import sys
import subprocess
import json
import time
import vserver
import urllib
import urllib.request
from subprocess import call

client = discord.Client()
serverVoices = {}
serverAdmins = {}
token = ''
log = ''
soundsDir = ''
lists = ''
commands = ''
configData = None

def loadConfig(firstRun=0):
	global token, adminIDs, soundsDir, lists, commands
	try:
		with open('./discordbot.json', 'r') as json_config:
			configData = json.load(json_config)

		if firstRun == 1:
			token = configData['token']

		soundsDir = configData['soundsdir']
		lists = configData['lists']
		commands = configData['commands']

		print('Config Loaded')
		if firstRun == 0:
			return True
	except:
		print('Failed to load config')
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

def getJSON(url):
	req = urllib.request.Request(url, headers={ 'User-Agent' : 'Magic!' })
	response = urllib.request.urlopen(req)
	data = json.loads(response.read().decode())
	return data

async def gearParser(message):
	theTime = int(time.mktime(time.gmtime()))
	data = getJSON("https://splatoon2.ink/data/merchandises.json")
	gear = data['merchandises']
	theString = ''

	theString = 'Current SplatNet Gear:\n```'

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

		theString = theString + eqName + ' : ' + eqBrand + '\n'
		theString = theString + '    Skill      : ' + str(skill['name']) + '\n'
		theString = theString + '    Common Sub : ' + str(commonSub) + '\n'
		theString = theString + '    Subs       : ' + str(slots) + '\n'
		theString = theString + '    Type       : ' + eqKind + '\n'
		theString = theString + '    Price      : ' + str(price) + '\n'
		theString = theString + '    Time Left  : ' + str(hours) + ' Hours and ' + str(minutes) + ' minutes\n\n'

	theString = theString + '```'
	await client.send_message(message.channel, theString)

async def maps(message, offset=0):
	theTime = int(time.mktime(time.gmtime()))
	data = getJSON("https://splatoon2.ink/data/schedules.json")
	trfWar = data['regular']
	ranked = data['gachi']
	league = data['league']
	theString = ''
	embed = discord.Embed(colour=0xFF0000)

	if offset == 0:
		theString = "Current Splatoon 2 Maps"
		embed.title = "Current Splatoon 2 Maps"
	elif offset == 1:
		theString = "Upcoming Splatoon 2 Maps"
		embed.title = "Upcoming Splatoon 2 Maps"

	theString = theString + "```Turf War:\n"

	mapA = trfWar[offset]['stage_a']
	mapB = trfWar[offset]['stage_b']
	end = trfWar[offset]['end_time']
	theString = theString + '{:22}'.format(mapA['name']) + '\t' + mapB['name'] + '\n'

	embed.add_field("Turf War", mapA['name'] + " & " + mapB['name'])

	theString = theString + "\nRanked: "

	mapA = ranked[offset]['stage_a']
	mapB = ranked[offset]['stage_b']
	game = ranked[offset]['rule']

	theString = theString + game['name'] + '\n' + '{:22}'.format(mapA['name']) + '\t' + mapB['name'] + '\n'

	embed.add_field("Ranked: " + game['name'], mapA['name'] + " & " + mapB['name'])

	theString = theString + '\nLeague: '
	mapA = league[offset]['stage_a']
	mapB = league[offset]['stage_b']
	game = league[offset]['rule']

	theString = theString + game['name'] + '\n' +  '{:22}'.format(mapA['name']) + '\t' + mapB['name'] + '\n```\n'

	embed.add_field("League: " + game['name'], mapA['name'] + " & " + mapB['name'])

	timeRemaining = end - theTime
	timeRemaining = timeRemaining % 86400
	hours = int(timeRemaining / 3600)
	timeRemaining = timeRemaining % 3600
	minutes = int(timeRemaining / 60)

	if offset == 0:
		theString = theString + 'Time Remaining: '
		embed.add_field("Time Remaining:", str(hours) + ' Hours, and ' + str(minutes) + ' minutes')
	elif offset >= 1:
		hours = hours - 2
		theString = theString + 'Time Until Map Rotation: '
		embed.add_field("Time Until Map Rotation:", str(hours) + ' Hours, and ' + str(minutes) + ' minutes')

	theString = theString + str(hours) + ' Hours, and ' + str(minutes) + ' minutes'

	await client.send_message(message.channel, None, False, embed)

async def srParser(message, getNext=0):
	theTime = int(time.mktime(time.gmtime()))
	data = getJSON("https://splatoon2.ink/data/coop-schedules.json")
	currentSR = data['details']
	gotData = 0
	start = 0
	end = 0
	theString = ""	

	if getNext == 0:
		theString = theString + "Current Salmon Run:\n```"
	else:
		theString = theString + "Upcoming Salmon Run:\n```"

	for i in currentSR:
		gotData = 0
		start = i['start_time']
		end = i['end_time']
		map = i['stage']
		weaps = i['weapons']

		if start <= theTime and theTime <= end:
			gotData = 1

		if (gotData == 1 and getNext == 0) or (gotData == 0 and getNext == 1):
			theString = theString + "Map: " + map['name'] + '\nWeapons:\n'
			for j in i['weapons']:
				try:
					weap = j['weapon']
				except:
					weap = j['coop_special_weapon']
				theString = theString + '\t' + weap['name'] + '\n'
			break

		elif gotData == 1 and getNext == 1:
			gotData = 0
			continue

	theString = theString + '\n'

	if gotData == 0 and getNext == 0:
		theString = theString + 'No SR currently running```'
		await client.send_message(message.channel, theString)
		return
	elif getNext == 1:
		timeRemaining = start - theTime
		theString = theString + '```Time Until This Rotation : '
	else:
		timeRemaining = end - theTime
		theString = theString + '```Time remaining : '

	days = int(timeRemaining / 86400)
	timeRemaining = timeRemaining % 86400
	hours = int(timeRemaining / 3600)
	timeRemaining = timeRemaining % 3600
	minutes = int(timeRemaining / 60)

	theString = theString + str(days) + ' Days, ' + str(hours) + ' Hours, and ' + str(minutes) + ' minutes'

	await client.send_message(message.channel, theString)

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
	global client, soundsDir, lists

	print('Logged in as,', client.user.name, client.user.id)
	print('------')
	await client.change_presence(game=discord.Game(name="Use !help for directions!", type=0))
	for server in client.servers:
		serverVoices[server.id] = vserver.voiceServer(client, server.id, soundsDir, lists)

	scanAdmins()
	
@client.event
async def on_member_remove(member):
	global serverAdmins

	theServer = member.server.id
	for mem in serverAdmins[theServer]:
		if mem.id != client.user.id:
			await client.send_message(mem, member.name + " left " + member.server.name)
			
@client.event
async def on_server_join(server):
	global client, soundsDir, lists
	serverVoices[server.id] = vserver.voiceServer(client, server.id, soundsDir, lists)

@client.event
async def on_message(message):
	global serverVoices, serverAdmins, soundsDir

	command = message.content.lower()
	
	if message.server == None:
		return
	else:
		theServer = message.server.id

	if message.author.name == client.user.name:
		return
	if command.startswith("!admin"):
		if message.author in serverAdmins[theServer]:
			if 'playlist' in message.content:
				await serverVoices[theServer].addPlaylist(message)
			if 'blacklist' in message.content:
				await serverVoices[theServer].addBlacklist(message)
			if 'wtfboom' in message.content:
				await serverVoices[theServer].playWTF(message)
			if 'tts' in message.content:
				await client.send_message(message.channel, message.content[11:], tts=True)
		else:
			print(message.author.name + " " + message.author.id + " tried to run an admin command")
			await client.send_message(message.channel, message.author.name + " you are not an admin... :cop:")
	elif command.startswith('!alive'):
		text = "Hey " + message.author.name + ", I'm alive so shut the fuck up! :japanese_goblin:"
		await client.send_message(message.channel, text)
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
		await maps(message)
	elif 'nextmaps' in command and '!' in command:
		await maps(message, offset=min(11, message.content.count('next')))
	elif command.startswith('!currentsr'):
		await srParser(message)
	elif command.startswith('!splatnetgear'):
		await gearParser(message)
	elif command.startswith('!nextsr'):
		await srParser(message, 1)
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
