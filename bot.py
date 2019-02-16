#!/usr/bin/python3

import discord
import asyncio
import sys
import subprocess
import json
import time
import vserver
from subprocess import call

client = discord.Client()
serverVoices = {}
adminObjs = []
adminIDs = ''
token = ''
log = ''
soundsDir = ''
playlist = ''
commands = ''
blacklist = ''
configData = None

def loadConfig(firstRun=0):
	global token, adminIDs, soundsDir, playlist, commands, blacklist
	try:
		with open('./discordbot.json', 'r') as json_config:
			configData = json.load(json_config)

		if firstRun == 1:
			token = configData['token']

		adminIDs = configData['admins']
		soundsDir = configData['soundsdir']
		playlist = configData['playlist']
		commands = configData['commands']
		blacklist = configData['blacklist']

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

	if offset == 0:
		theString = "Current Splatoon 2 Maps"
	elif offset == 1:
		theString = "Upcoming Splatoon 2 Maps"

	theString = theString + "```Turf War:\n"

	mapA = trfWar[offset]['stage_a']
	mapB = trfWar[offset]['stage_b']
	end = trfWar[offset]['end_time']
	theString = theString + '{:22}'.format(mapA['name']) + '\t' + mapB['name'] + '\n'

	theString = theString + "\nRanked: "

	mapA = ranked[offset]['stage_a']
	mapB = ranked[offset]['stage_b']
	game = ranked[offset]['rule']

	theString = theString + game['name'] + '\n' + '{:22}'.format(mapA['name']) + '\t' + mapB['name'] + '\n'

	theString = theString + '\nLeague: '
	mapA = league[offset]['stage_a']
	mapB = league[offset]['stage_b']
	game = league[offset]['rule']

	theString = theString + game['name'] + '\n' +  '{:22}'.format(mapA['name']) + '\t' + mapB['name'] + '\n```\n'

	timeRemaining = end - theTime
	timeRemaining = timeRemaining % 86400
	hours = int(timeRemaining / 3600)
	timeRemaining = timeRemaining % 3600
	minutes = int(timeRemaining / 60)

	if offset == 0:
		theString = theString + 'Time Remaining: '	
	elif offset >= 1:
		hours = hours - 2
		theString = theString + 'Time Until Map Rotation: '

	theString = theString + str(hours) + ' Hours, and ' + str(minutes) + ' minutes'

	await client.send_message(message.channel, str(theString))

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
	global client, soundsDir, playlist, blacklist
	theServer = message.server.id

	if theServer not in serverVoices:
		serverVoices[theServer] = vserver.voiceServer(client, theServer, soundsDir, playlist, blacklist)
	
	await serverVoices[theServer].joinVoiceChannel(channelName, message)
	sys.stdout.flush()

def scanAdmins(firstRun=0):
	global adminObjs, adminIDs

	if firstRun:
		print("Searching for admins: " + str(adminIDs))
	else:
		print("Rescanning for admins")

	for server in client.servers:
		for mem in server.members:
			if mem.id in adminIDs and mem not in adminObjs:
				print('Found admin ' + mem.name)
				adminObjs.append(mem)
				
	if len(adminObjs) == 0:
		print('Failed to find any admins, check the IDs in the config')
	sys.stdout.flush()

@client.event
async def on_ready():
	print('Logged in as,', client.user.name, client.user.id)
	print('------')
	await client.change_presence(game=discord.Game(name="Use !help for directions!", type=0))
	scanAdmins(1)
	
@client.event
async def on_member_remove(member):
	global adminObjs

	if len(adminObjs) == 0:
		return
	else:
		print(member.name + " left the server")
		sys.stdout.flush()
		for mem in adminOjbs:
			await client.send_message(mem, member.name + " left the server")
			
@client.event
async def on_message(message):
	global serverVoices, ytplayer, ytQueue, player, adminObjs, playlist, blacklist

	command = message.content
	theServer = message.server.id

	if message.server == None and message.author not in adminObjs:
		return
	if message.author.name == client.user.name:
		return
	if message.content.startswith("!admin"):
		if message.author in adminObjs:
			if 'playlist' in message.content:
				toAdd = ''
				if 'https' in message.content:
					toAdd = message.content[16:]
				else:
					toAdd = ytplayer.url

				if not listCheck(playlist, toAdd):
					listAdd(playlist, toAdd)
					await client.add_reaction(message, '👍')
				else:
					await client.send_message(message.channel, 'That is already in my playlist!')
			if 'blacklist' in message.content:
				toAdd = ''
				if 'https' in message.content:
					toAdd = message.content[16:]
				else:
					toAdd = ytplayer.url

				if not listCheck(blacklist, toAdd):
					listAdd(blacklist, toAdd)
					await client.add_reaction(message, '👍')
				else:
					await client.send_message(message.channel, 'That is already in my blacklist!')
			if 'wtfboom' in message.content:
				if ytplayer == None:
					if player != None:
						player.stop()
					player = vclient.create_ffmpeg_player(soundsDir + '/wtfboom.mp3')
					player.volume = .5
					player.start()
			if 'tts' in message.content:
				await client.send_message(message.channel, message.content[11:], tts=True)
			if 'reload' in message.content:
				if loadConfig():
					await client.send_message(message.channel, "Successfully reloaded config, rescanning admin users")
					scanAdmins()
				else:
					await client.send_message(message.channel, "Failed to reload config")
		else:
			print(message.author.name + " " + message.author.id + " tried to run an admin command")
			await client.send_message(message.channel, message.author.name + " you are not an admin... :cop:")
	elif '!restart' in message.content:
		await client.send_message(message.channel, 'Attempting to restart if I can, give me a second')
		print("Starting restart")

		if ytplayer != None:
			ytplayer.stop()
		if player != None:
			player.stop()
		if vclient != None:
			await vclient.disconnect()

		vclient = None
		player = None
		ytplayer = None
		await client.close()
		print("Disconnected from discord, exiting")
		sys.stdout.flush()
		quit(0)
	elif message.content.startswith('!alive'):
		text = "Hey " + message.author.name + ", I'm alive so shut the fuck up! :japanese_goblin:"
		await client.send_message(message.channel, text)
	elif message.content.startswith('!github'):
		await client.send_message(message.channel, 'Here is my github page! : https://github.com/Jetsurf/jet-bot')
	elif message.content.startswith('!commands') or message.content.startswith('!help'):
		theString = ''
		with open(commands, 'r') as f:
			for line in f:
				theString = theString + line
		await client.send_message(message.channel, theString)
	elif message.content.startswith('!sounds'):
		theSounds = subprocess.check_output(["ls", soundsDir])
		theSounds = theSounds.decode("utf-8")
		theSounds = theSounds.replace('.mp3', '')
		theSounds = theSounds.replace('\n', ', ')
		await client.send_message(message.channel, "Current Sounds:\n```" + theSounds + "```")
	elif message.content.startswith('!joinvoice') or message.content.startswith('!join'):
		vclient = await joinVoiceChannel(message.content.split(" ", 1)[1], message)
	elif message.content.startswith('!currentmaps'):
		await maps(message)
	elif 'nextmaps' in message.content and '!' in message.content:
		await maps(message, offset=min(11, message.content.count('next')))
	elif message.content.startswith('!currentsr'):
		await srParser(message)
	elif message.content.startswith('!splatnetgear'):
		await gearParser(message)
	elif message.content.startswith('!nextsr'):
		await srParser(message, 1)
	elif message.content.startswith('!us') or message.content.startswith('!eu') or message.content.startswith('!jp'):
		await setCRole(message)
	elif ('pizza' in message.content.lower() and 'pineapple' in message.content.lower()) or ('\U0001F355' in message.content and '\U0001F34D' in message.content):
		await client.send_message(message.channel, 'Don\'t ever think pineapple and pizza go together ' + message.author.name + '!!!')
	elif theServer in serverVoices:
		if message.content.startswith('!currentsong'):
			if serverVoices[theServer].ytPlayer != None:
				await client.send_message(message.channel, 'Currently Playing Video: ' + serverVoices[theServer].ytPlayer.url)
			else:
				await client.send_message(message.channel, 'I\'m not playing anything.')
		elif message.content.startswith('!leavevoice'):
			await serverVoices[theServer].vclient.disconnect()
		elif message.content.startswith('!playrandom'):
			if len(message.content) > 11:
				await serverVoices[theServer].playRandom(message, int(message.content.split(' ')[1]))
			else:
				await serverVoices[theServer].playRandom(message, 1)
		elif message.content.startswith('!play'):
			await serverVoices[theServer].setupPlay(message)
		elif message.content.startswith('!stop'):
			await serverVoices[theServer].stop(message)
		elif message.content.startswith('!volume'):
			vol = int(message.content.split(' ')[1])
			if vol > 60:
				vol = 60

			await client.send_message(message.channel, "Setting Volume to " + str(vol) + "%")
			serverVoices[theServer].ytplayer.volume = float(vol / 100)
		elif message.content.startswith('!'):
			await serverVoices[theServer].playSound(command, message)
	sys.stdout.flush()

#Setup
sys.stdout = open('./discordbot.log', 'a')

print('**********NEW SESSION**********')
loadConfig(firstRun=1)

print('Logging into discord')

sys.stdout.flush()
client.run(token)