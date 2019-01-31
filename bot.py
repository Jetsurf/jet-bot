#!/usr/bin/python3

import discord
import asyncio
import queue
import sys
import urllib
import urllib.request
import subprocess
import json
import time
import signal
import json
import datetime
import calendar
from bs4 import BeautifulSoup
from subprocess import call
from random import randint

client = discord.Client()
vclient = None
ytQueue = queue.Queue()
ytplayer = None
player = None
joshIsGay = 0
doingRestart = 0
memberJet = None
email = ''
password = ''
log = ''
soundsDir = ''
playlist = ''
commands = ''
admin = ''
configData = None

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

async def spParser(message):
	theTime = int(time.mktime(time.gmtime()))
	data = getJSON("https://splatoon2.ink/data/merchandises.json")
	gear = data['merchandises']
	theString = ''

	theString = theString + 'Current SplatNet Gear:\n```'

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

async def joinVoiceChannel(channelName, message):
	global vclient

	if vclient != None:
		print("Disconnecting from Voice")
		await vclient.disconnect()

	id = 0
	print ("Trying to join voice  channel: " + str(channelName))

	server = message.server
	for channel in server.channels:
		#print (channel.id + " " + channel.name)
		if channel.name == channelName:
			id = channel.id

	if id != 0:
		print("Joining Voice Channel: " + id)
		vclient = await client.join_voice_channel(client.get_channel(id))
		return vclient
	else:
		print ("Fail?")
		await client.send_message(message.channel, "I could not join channel " + str(channelName))

@asyncio.coroutine
async def playRandom(message, queue, debug=0):
	global vclient
	global ytplayer
	global ytQueue
	x = []
	toPlay = []
	tempytplayer = None

	with open(playlist, 'r') as f:
		for line in f:
			x.append(line)

	queue = min(queue, len(x))
	for y in range(queue):
		if debug == 0:
			while 1:
				numToPlay = randint(1, len(x))
				if numToPlay in toPlay:
					continue
				else:
					toPlay.append(numToPlay)
					print("Num to play: " + str(numToPlay))
					print("I am going to play track " + str(numToPlay) + " " + x[numToPlay - 1])
					break
		else:
		
			numToPlay = debug
			print("Num to play: " + str(debug))

		tempytplayer = await vclient.create_ytdl_player(x[numToPlay - 1])
		tempytplayer.after = playNext
		ytQueue.put(tempytplayer)


		if ytplayer == None and vclient != None:
			await client.send_message(message.channel, "Playing : " + x[toPlay[0] - 1])
			print("Queued up!")
		if y == 1:
			print("I am queueing song " + str(numToPlay) + " " + x[numToPlay - 1])
		play()

	if queue > 1:
		await client.send_message(message.channel, "Also queued " + str(queue - 1) + " more song(s) from my playlist")
	

@client.event
async def on_ready():
	global memberJet
	gotJet = 0
	
	print('Logged in as,', client.user.name, client.user.id)
	print('------')
	await client.change_presence(game=discord.Game(name="Use !help for directions!", type=0))

	for server in client.servers:
		if gotJet == 1:
			break

		for mem in server.members:
			if mem.id == admin:
				print('Found my admin, all good for DM\'s')
				memberJet = mem
				gotJet = 1
				break
	if memberJet == None:
		print('Failed to find admin for some reason, logging will be borked')
	sys.stdout.flush()

def playNext():
	global ytQueue
	global ytplayer

	if ytQueue.empty():
		print("Done playing")
		ytplayer = None
	else:
		print("Playing next video")
		ytplayer = ytQueue.get()
		ytplayer.volume = .07
		ytplayer.start()

def play():
	global ytplayer
	global ytQueue

	if ytplayer == None and ytQueue.qsize() == 1:
		ytplayer = ytQueue.get()
		print("Starting playing...")
		ytplayer.volume = .07
		ytplayer.start()
	else:
		print("Currently playing, waiting to play")

async def playSound(command, message):
	global player
	global ytplayer

	if ytplayer == None:
		if player != None:
			player.stop()

		player = vclient.create_ffmpeg_player(soundsDir + '/' + command[1:] + '.mp3')

		if '!wtfboom' in command or '!johncena' in command or '!ohmygod' in command or "!leeroy" in command:
			player.volume = .1
		elif '!whosaidthat' in command or '!chrishansen' in command:
			player.volume = .4
		else:
			player.volume = .25

		player.start()

@client.event
async def on_member_remove(member):
	global myAdmin

	if myAdmin == None:
		return
	else:
		await client.send_message(myAdmin, member.nick + " left a server")
		print(member.nick + " left a server")
		sys.stdout.flush()
	
@client.event
async def on_message(message):
	global vclient
	global ytplayer
	global ytQueue
	global player
	global joshIsGay
	global doingRestart
	global myAdmin

	command = message.content

	if message.server == None and message.author.id != myAdmin:
		return
	if message.author.name == client.user.name:
		return
	if message.content.startswith("!debug"):
		print(message.author.name + " " + message.author.id + " tried to summon me")

		if message.author.id == myAdmin:
			if 'add' in message.content:
				playlist = open(playlist, 'a')

				await client.send_message(message.channel, 'I am adding ' + ytplayer.title + ' to the random playlist')
				playlist.write('\n' + ytplayer.url)
				playlist.flush()
				playlist.close()
			if 'wtfboom' in message.content:
				if player != None:
					player.stop()
				player = vclient.create_ffmpeg_player(soundsDir + '/wtfboom.mp3')
				player.volume = .5
				player.start()
			if 'tts' in message.content:
				await client.send_message(message.channel, message.content[11:], tts=True)				
		else:
			await client.send_message(message.channel, message.author.name + " you are not my master... :cop:")
	elif '!restart' in message.content:
		if doingRestart == 1:
			await client.send_message(message.channel, 'Im already restarting, staph!!!')
			return
		else:
			doingRestart = 1

		await client.send_message(message.channel, 'Attempting to restart if I can, give me a while')

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
		quit(0)

	elif message.content.startswith('!alive'):
		text = "Hey " + message.author.name + ", I'm alive so shut the fuck up! :japanese_goblin:"
		await client.send_message(message.channel, text)

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

	elif message.content.startswith('!joinvoice'):
		vclient = await joinVoiceChannel(message.content[11:], message)
	elif message.content.startswith('!currentmaps'):
		await maps(message)
	elif 'nextmaps' in message.content and '!' in message.content:
		await maps(message, offset=min(11, message.content.count('next')))
	elif message.content.startswith('!currentsr'):
		await srParser(message)
	elif message.content.startswith('!splatnetgear'):
		await spParser(message)
	elif message.content.startswith('!nextsr'):
		await srParser(message, 1)
	elif message.content.startswith('!us') or message.content.startswith('!eu') or message.content.startswith('!jp'):
		await setCRole(message)
	elif vclient is not None:
		if message.content.startswith('!currentsong'):
			if ytplayer != None:
				await client.send_message(message.channel, 'Currently Playing Video: ' + ytplayer.url)
			else:
				await client.send_message(message.channel, 'I\'m not playing anything.')
		elif message.content.startswith('!leavevoice'):
			await vclient.disconnect()
			vclient = None
		elif message.content.startswith('!playRandom'):
			if len(message.content) > 11:
				await playRandom(message, int(message.content[12:]))
			else:
				await playRandom(message, 1)
		elif message.content.startswith('!playyt'):
			if 'https' in message.content:
				tempytplayer = await vclient.create_ytdl_player(message.content[8:])
				print("Setting up play next")
				tempytplayer.after = playNext
				ytQueue.put(tempytplayer)

				play()
				await client.add_reaction(message, '👍')
			else:
				try:
					print ("Searching : " + message.content[8:])
					query = urllib.request.pathname2url(message.content[8:])
					url = "https://youtube.com/results?search_query=" + query
					response = urllib.request.urlopen(url)
					html = response.read()
					soup = BeautifulSoup(html, "lxml")

					vid =  soup.find(attrs={'class':'yt-uix-tile-link'})
					theURL = "https://youtube.com" + vid['href']

					if ytQueue.empty():
						await client.send_message(message.channel, "Playing : " + theURL)
					else:
						await client.send_message(message.channel, "Queued : " + theURL)

					print("Playing: " + theURL)
					tempytplayer = await vclient.create_ytdl_player(theURL)
					print ("Setting up searched YT vid")
					tempytplayer.after = playNext
					ytQueue.put(tempytplayer)
					
					play()
				except:
					await client.send_message(message.channel, "Sorry, I can't play that")

		elif message.content.startswith('!stop') or message.content.startswith('!pause') or message.content.startswith('!play'):
			if ytplayer != None:
				if message.content.startswith('!stop'):
					ytplayer.stop()
				if message.content.startswith('!pause') and ytplayer.is_playing():
					ytplayer.pause()
				if message.content.startswith('!play') and ytplayer.is_playing() == False:
					ytplayer.resume()
			else: 
				await client.send_message(message.channel, "I'm not playing anything right now")
		elif message.content.startswith('!volume'):
			vol = int(message.content[8:])
			if vol > 50:
				vol = 50

			await client.send_message(message.channel, "Setting Volume to " + str(vol) + "%")
			ytplayer.volume = float(vol / 100)
		elif message.content.startswith('!'):
			await playSound(command, message)
	sys.stdout.flush()

#Setup
sys.stdout = open('../discordbot.log', 'a')

try:
	with open('./discordbot.json.secret', 'r') as json_config:
		configData = json.load(json_config)

	email = configData['email']
	password = configData['password']
	soundsDir = configData['soundsdir']
	playlist = configData['playlist']
	commands = configData['commands']
	admin = configData['admin']
	
	print('Config Loaded')
except:
	print('Failed to load config, exiting...')
	quit(1)

print('**********NEW SESSION**********')
print('Logging into discord')

sys.stdout.flush()
client.run(email, password)
