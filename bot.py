#!/usr/bin/python3.8

import sys
sys.path.append('./modules')
#Base Stuffs
import discord, asyncio, subprocess, json, time, itertools
from discord.app import Option, SlashCommandGroup
#DBL Posting
import urllib, urllib.request, requests, pymysql
#Our Classes
import nsotoken, commandparser, serverconfig, splatinfo, messagecontext
import vserver, mysqlhandler, serverutils, nsohandler, achandler
#Eval
import traceback, textwrap, io, signal
from contextlib import redirect_stdout
from subprocess import call

splatInfo = splatinfo.SplatInfo()
intents = discord.Intents.default()
intents.members = True
client = discord.Bot(intents=intents, chunk_guilds_at_startup=False)
commandParser = None
serverConfig = None
mysqlHandler = None
nsoAppVer = ''
#nsoHandler = None
nsoTokens = None
serverVoices = {}
serverUtils = None
acHandler = None
doneStartup = False
token = ''
hs = 0
owners = []
dev = 1
soundsDir = ''
helpfldr = ''
head = {}
url = ''

#SubCommand Groups
cmdGroups = {}
maps = SlashCommandGroup('maps', 'Commands related to maps for Splatoon 2')
weapon = SlashCommandGroup("weapons", 'Commands realted to weapons for Splatoon 2')
admin = SlashCommandGroup('admin', 'Commands that require guild admin privledges to run')
voice = SlashCommandGroup('voice', 'Commands related to voice functions')
store = SlashCommandGroup('store', 'Commands related to the Splatoon 2 store')
dm = admin.command_group(name='dm', description="Admin commands related to DM's on users leaving")
feed = admin.command_group(name='feed', description="Admin commands related to SplatNet rotation feeds")
announce = admin.command_group(name='announcements', description="Admin commands related to developer annoucenments")
play = voice.command_group(name="play", description="Commands realted to playing audio")
storedm = store.command_group('dm', "Commands related to DM'ing on store changes")

class blank():
	def __init__(self):
		self.storeJSON = {}
		self.storeJSON['merchandises'] = []

nsoHandler = blank()

def loadConfig():
	global token, nsoAppVer, soundsDir, helpfldr, mysqlHandler, dev, head, url, hs
	try:
		with open('./config/discordbot.json', 'r') as json_config:
			configData = json.load(json_config)

		token = configData['token']
		soundsDir = configData['soundsdir']
		helpfldr = configData['help']
		hs = configData['home_server']
		nsoAppVer = configData['nso_app_ver']

		try:
			dbid = configData['discordbotid']
			dbtoken = configData['discordbottok']
			head = { 'Authorization': dbtoken }
			url = f"https://top.gg/api/bots/{str(dbid)}/stats"
			dev = 0
		except:
			print('No ID/Token for top.gg, skipping')

		mysqlHandler = mysqlhandler.mysqlHandler(configData['mysql_host'], configData['mysql_user'], configData['mysql_pw'], configData['mysql_db'])

		print('Config Loaded')
	except Exception as e:
		print(f"Failed to load config: {str(e)}")
		quit(1)

@store.command(name='currentgear', description="See the current gear on the SplatNet store")
async def cmdStoreCurrent(ctx):
	await serverUtils.increment_cmd(ctx, 'splatnetgear')
	await nsoHandler.gearParser(ctx)

@store.command(name='order', description='Orders gear from the SplatNet store')
async def cmdOrder(ctx, order: Option(str, "ID or NAME of the gear to order from the store (get both from /splatnetgear)", required=True)):
	await serverUtils.increment_cmd(ctx, 'order')
	await nsoHandler.orderGearCommand(ctx, args=[str(order)])

@storedm.command(name='add', description='Sends a DM when gear with this ability appears in the store')
async def cmdStoreDMAbilty(ctx, flag: Option(str, "ABILITY/BRAND/GEAR to DM you with when it appears in the store", required=True)):
	await serverUtils.increment_cmd(ctx, 'storedm') 
	await nsoHandler.addStoreDM(ctx, [ str(flag) ], True)

@storedm.command(name='list', description='Shows you everything you are set to recieve a DM for')
async def cmdStoreDMAbilty(ctx):
	await serverUtils.increment_cmd(ctx, 'storedm') 
	await nsoHandler.listStoreDM(ctx, [ str(flag) ], True)

@storedm.command(name='remove', description='Shows you everything you are set to recieve a DM for')
async def cmdStoreDMAbilty(ctx, flag: Option(str, "ABILITY/BRAND/GEAR to stop DMing you with when it appears in the store", required=True)):
	await serverUtils.increment_cmd(ctx, 'storedm') 
	await nsoHandler.removeStoreDM(ctx, [ str(flag) ], True)

@client.slash_command(name='support', description='Sends a discord invite to my support guild.')
async def cmdSupport(ctx):
	await ctx.respond('Here is a link to my support server: https://discord.gg/TcZgtP5', ephemeral=True)

@client.slash_command(name='github', description='Sends a link to my github page')
async def cmdGithub(ctx):
	await ctx.respond('Here is my github page! : https://github.com/Jetsurf/jet-bot')

@announce.command(name='set', description="Sets a chat channel to receive announcements from my developers")
async def cmdDMAdd(ctx, channel: Option(discord.TextChannel, "Channel to set to receive announcements", required=True)):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if await checkIfAdmin(ctx):
		await serverUtils.setAnnounceChannel(ctx, channel)
	else:
		await ctx.respond("You aren't a guild administrator")

@announce.command(name='get', description="Gets the channel that is set to receive annoucements")
async def cmdDMRemove(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if await checkIfAdmin(ctx):
		channel = await serverUtils.getAnnounceChannel(ctx.guild.id)
		if channel == None:
			await ctx.respnd("No channel is set to receive announcements")
		else:
			await ctx.respond(f"Current announcement channel is: {channel.name}")
	else:
		await ctx.respond("You aren't a guild administrator")

@announce.command(name='remove', description="Removes you from being DM'ed on users leaving")
async def cmdDMRemove(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if await checkIfAdmin(ctx):
		await serverUtils.stopAnnouncements(ctx)
	else:
		await ctx.respond("You aren't a guild administrator")

@feed.command(name='create', description="Sets up a Splatoon 2 rotation feed for a channel")
async def cmdAdminFeed(ctx, map: Option(bool, "Enable maps in the feed?", required=True), sr: Option(bool, "Enable Salmon Run in the feed?", required=True), gear: Option(bool, "Enable gear in the feed?", required=True), recreate: Option(bool, "Recreate feed if one is already present.", required=False)):
	args = [ map, sr, gear, recreate ]

	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if await checkIfAdmin(ctx):
		if map == False and sr == False and gear == False:
			await ctx.respond("Not going to create a feed with nothing in it.")
		else:
			await serverUtils.createFeed(ctx, args=args)
	else:
		await ctx.respond("You aren't a guild administrator")

@feed.command(name='delete', description="Deletes a feed from a channel")
async def cmdAdminDeleteFeed(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if await checkIfAdmin(ctx):
		await serverUtils.deleteFeed(ctx, is_slash=True, bypass=True)
	else:
		await ctx.respond("You aren't a guild administrator")

@dm.command(name='remove', description="Removes you from being DM'ed on users leaving")
async def cmdDMRemove(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if await checkIfAdmin(ctx):
		await serverUtils.removeDM(ctx)
	else:
		await ctx.respond("You aren't a guild administrator")

@dm.command(name='add', description="Adds you to DM's on users leaving")
async def cmdDMAdd(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if await checkIfAdmin(ctx):
		await serverUtils.addDM(ctx)
	else:
		await ctx.respond("You aren't a guild administrator")

@maps.command(name='current', description='Shows current map rotation for Turf War/Ranked/League')
async def cmdCurrentMaps(ctx):
	await serverUtils.increment_cmd(ctx, 'currentmaps')
	await nsoHandler.maps(ctx)

@maps.command(name='next', description='Shows the next maps in rotation for Turf War/Ranked/League')
async def cmdNextMaps(ctx, rotation: Option(int, "Map Rotations ahead to show, max of 11 ahead", required=False, default=1)):
	await serverUtils.increment_cmd(ctx, 'nextmaps')
	if rotation < 0 or rotation > 11:
		await ctx.respond("Rotation must be between 1-11")
		return
	if rotation == None:
		rotation = 1

	await nsoHandler.maps(ctx, rotation)

@maps.command(name='nextsr', description='Shows map/weapons for the next Salmon Run rotation')
async def cmdNextSR(ctx):
	await serverUtils.increment_cmd(ctx, 'nextsr')
	await nsoHandler.srParser(ctx, 1)

@maps.command(name='currentsr', description='Shows map/weapons for the current Salmon Run rotation')
async def cmdCurrentSR(ctx):
	await serverUtils.increment_cmd(ctx, 'currentsr')
	await nsoHandler.srParser(ctx)

@maps.command(name='callout', description="Shows callout locations for a Splatoon 2 map")
async def cmdMapsCallout(ctx, map: Option(str, "Map to show callout locations for", choices=[ themap.name() for themap in splatInfo.getAllMaps() ] ,required=True)):
	await nsoHandler.cmdMaps(ctx, args=[ 'callout', str(map) ])

@maps.command(name='list', description="Shows all Splatoon 2 maps")
async def cmdMapsStats(ctx):
	await serverUtils.increment_cmd(ctx, 'maps')
	await nsoHandler.cmdMaps(ctx, args=[ 'list' ])

@maps.command(name='stats', description="Shows Splatoon 2 gameplay stats for a map")
async def cmdMapsStats(ctx, map: Option(str, "Map to show stats for", choices=[ themap.name() for themap in splatInfo.getAllMaps() ] ,required=True)):
	await serverUtils.increment_cmd(ctx, 'maps')
	await nsoHandler.cmdMaps(ctx, args=[ 'stats', str(map)])

@maps.command(name='random', description="Generates a random list of Splatoon 2 maps")
async def cmdMapsRandom(ctx, num: Option(int, "Number of maps to include in the list (1-10)", required=True)):
	await serverUtils.increment_cmd(ctx, 'maps')
	if num < 1 or num > 10:
		await ctx.respond("Num needs to be between 1-10")
	else:
		await nsoHandler.cmdMaps(ctx, args=[ 'random', str(num)])

@weapon.command(name='info', description='Gets info on a weapon in Splatoon 2')
async def cmdWeapInfo(ctx, name: Option(str, "Name of the weapon to get info for", required=True)):
	await serverUtils.increment_cmd(ctx, 'weapons')

	await nsoHandler.cmdWeaps(ctx, args=[ 'info', str(name) ])

@weapon.command(name='list', description='Gets a list pf weapons by type in Splatoon 2')
async def cmdWeapList(ctx, weaptype: Option(str, "Type of weapon to generate a list for", required=True, choices=[ weaptype.name() for weaptype in splatInfo.getAllWeaponTypes() ])):
	await serverUtils.increment_cmd(ctx, 'weapons')

	await nsoHandler.cmdWeaps(ctx, args=[ 'list', str(weaptype) ])

@weapon.command(name='random', description='Generates a random list of weapons')
async def cmdWeapRandom(ctx, num: Option(int, "Number of weapons to include in the list (1-10)", required=True)):
	await serverUtils.increment_cmd(ctx, 'weapons')
	if num < 0 or num > 10:
		await ctx.respond("Num must be between 1-10!")
		return

	await nsoHandler.cmdWeaps(ctx, args=[ 'random', str(num) ])

@weapon.command(name='special', description='Gets all Splatoon 2 weapons with special type')
async def cmdWeapSpecial(ctx, special: Option(str, "Name of the special to get matching weapons for", choices=[ weap.name() for weap in splatInfo.getAllSpecials() ], required=True)):
	await serverUtils.increment_cmd(ctx, 'weapons')

	await nsoHandler.cmdWeaps(ctx, args=[ 'special', str(special) ])

@weapon.command(name='stats', description='Gets stats from a weapon in Splatoon 2')
async def cmdWeapStats(ctx, name: Option(str, "Name of the weapon to get stats for", required=True)):
	await serverUtils.increment_cmd(ctx, 'weapons')

	await nsoHandler.cmdWeaps(ctx, args=[ 'stats', str(name) ])

@weapon.command(name='sub', description='Gets Splatoon 2all weapons with sub type')
async def cmdWeapSub(ctx, sub: Option(str, "Name of the sub to get matching weapons for", choices=[ weap.name() for weap in splatInfo.getAllSubweapons() ], required=True)):
	await serverUtils.increment_cmd(ctx, 'weapons')

	await nsoHandler.cmdWeaps(ctx, args=[ 'sub', str(sub) ])

@client.slash_command(name='rank', description='Get your ranks in ranked mode from S2 SplatNet')
async def cmdRanks(ctx):
	await serverUtils.increment_cmd(ctx, 'rank')
	await nsoHandler.getRanks(ctx)

@client.slash_command(name='srstats', description='Get your Salmon Run stats from S2 SplatNet')
async def cmdSRStats(ctx):
	await serverUtils.increment_cmd(ctx, 'srstats')
	await nsoHandler.getSRStats(ctx)

@client.slash_command(name='stats', description='Get your gameplay stats from S2 SplatNet ')
async def cmdStats(ctx):
	await serverUtils.increment_cmd(ctx, 'stats')
	await nsoHandler.getStats(ctx)

@client.slash_command(name='battle', description='Get stats from a battle (1-50)')
async def cmdBattle(ctx, battlenum: Option(int, "Battle Number, 1 being latest, 50 max", required=True, default=1)):
	await serverUtils.increment_cmd(ctx, 'battle')
	await nsoHandler.cmdBattles(ctx, battlenum)

@voice.command(name='join', description='Join a voice chat channel')
async def cmdVoiceJoin(ctx, channel: Option(discord.VoiceChannel, "Voice Channel to join", required=False)):
	await serverUtils.increment_cmd(ctx, 'join')
	if channel == None:
		await serverVoices[ctx.guild.id].joinVoiceChannel(ctx, [])
	else:
		await serverVoices[ctx.guild.id].joinVoiceChannel(ctx, channel)

@voice.command(name='volume', description='Changes the volume while in voice chat')
async def cmdVoiceVolume(ctx, vol: Option(int, "What to change the volume to 1-60% (7\% is default)"), required=True):
	await serverUtils.increment_cmd(ctx, 'volume')
	if serverVoices[ctx.guild.id].vclient != None:
		if vol > 60:
			vol = 60
		if serverVoices[ctx.guild.id].source != None:
			await ctx.respond(f"Setting Volume to {str(vol)}%")
			serverVoices[ctx.guild.id].source.volume = float(int(vol) / 100)
		else:
			await ctx.respond("Not playing anything")
	else:
		await ctx.respond("Not connected to voice")

@play.command(name='url', description='Plays a video from a URL')
async def cmdVoicePlayUrl(ctx, url: Option(str, "URL of the video to play")):
	await serverUtils.increment_cmd(ctx, 'play')
	if serverVoices[ctx.guild.id].vclient is not None:
		await serverVoices[ctx.guild.id].setupPlay(ctx, [ str(url) ])
	else:
		await ctx.respond("Not connected to voice")

@play.command(name='search', description="Searches SOURCE for a playable video/song")
async def cmdVoicePlaySearch(ctx, source: Option(str, "Source to search", choices=[ 'youtube', 'soundcloud' ], default='youtube', required=True), search: Option(str, "Video to search for", required = True)):
	await serverUtils.increment_cmd(ctx, 'play')
	if serverVoices[ctx.guild.id].vclient is not None:
		theList = []
		for i in itertools.chain([ source ], search.split()):
			theList.append(i)
		
		print(f"{theList}")
		await serverVoices[ctx.guild.id].setupPlay(ctx, theList)

	else:
		await ctx.respond("Not connected to voice")

@voice.command(name='skip', description="Skips the currently playing song")
async def cmdVoiceSkip(ctx):
	await serverUtils.increment_cmd(ctx, 'skip')
	if serverVoices[ctx.guild.id].vclient is not None:
		if serverVoices[ctx.guild.id].source is not None:
			await serverVoices[ctx.guild.id].stop(ctx)
		else:
			await ctx.respond("Not playing anything")
	else:
		ctx.respond("Not connected to voice")
			
@voice.command(name='end', description="Stops playing all videos")
async def cmdVoiceEnd(ctx):
	await serverUtils.increment_cmd(ctx, 'stop')
	if serverVoices[ctx.guild.id].vclient is not None:
		if serverVoices[ctx.guild.id].source is not None:
			serverVoices[theServer].end()
			await ctx.respond("Stopped playing all videos")
		else:
			await ctx.respond("Not playing anything.")
	else:
		await ctx.respond("Not connected to voice")

@voice.command(name='playrandom', description="Plays a number of videos from this servers playlist")
async def cmdVoicePlayRandom(ctx, num: Option(int, "Number of videos to queue up", required=True)):
	await serverUtils.increment_cmd(ctx, 'playrandom')
	if num < 0:
		await ctx.respond("Num needs to be greater than 0.")
	else:
		await serverVoices[theServer].playRandom(context, num)

@voice.command(name='currentvid', description="Shows the currently playing video")
async def cmdVoiceCurrent(ctx):
	await serverUtils.increment_cmd(ctx, 'currentsong')
	if serverVoices[ctx.guild.id].vclient is not None:
		if serverVoices[ctx.guild.id].source is not None:
			await ctx.respond(f"Currently Playing Video: {serverVoices[ctx.guild.id].source.yturl}")
		else:
			await ctx.respond("I'm not playing anything.")
	else:
		await ctx.respond("Not connected to voice")

@voice.command(name='queue', description="Shows the current queue of videos to play")
async def cmdVoiceQueue(ctx):
	await serverUtils.increment_cmd(ctx, 'queue')
	if serverVoices[ctx.guild.id].vclient is not None:
		await serverVoices[theServer].printQueue(context)
	else:
		await ctx.respond("Not connected to voice.")

@voice.command(name='disconnect', description="Disconnects me from voice")
async def cmdVoiceDisconnect(ctx):
	await serverUtils.increment_cmd(ctx, 'leavevoice')
	if serverVoices[ctx.guild.id] != None:
		await serverVoices[ctx.guild.id].vclient.disconnect()
		serverVoices[ctx.guild.id].vclient = None
		await ctx.respond("Disconnected from voice.")
	else:
		await ctx.respond("Not connected to voice.")

@voice.command(name='sounds', description="Shows sounds I can play with /voice soundclip")
async def cmdVoiceSounds(ctx):
	await serverUtils.increment_cmd(ctx, 'sounds')
	theSounds = subprocess.check_output(["ls", soundsDir])
	theSounds = theSounds.decode("utf-8")
	theSounds = theSounds.replace('.mp3', '')
	theSounds = theSounds.replace('\n', ', ')
	await ctx.respond(f"Current Sounds:\n```{theSounds}```")

@voice.command(name='playsound', description="Plays one of my sound clips in voice")
async def cmdVoicePlaySound(ctx, sound: Option(str, "Sound clip to play, get with /voice sounds")):
	if serverVoices[ctx.guild.id].vclient is not None:
		await ctx.respond(f"Attempting to play: {sound}")
		await serverVoices[ctx.guild.id].playSound(sound)
	else:
		await ctx.respond("Not connected to voice.")

async def checkIfAdmin(ctx):
	if ctx.guild.get_member(ctx.user.id) == None:
		await client.get_guild(ctx.guild.id).chunk()

	return ctx.user.guild_permissions.administrator

async def resetNSOVer(message):
	global nsoAppVer, nsoTokens

	try:
		with open('./config/discordbot.json', 'r') as json_config:
			configData = json.load(json_config)
			nsoAppVer = configData['nso_app_ver']
			await nsoTokens.reloadNSOAppVer(nsoAppVer)
	except:
		await message.channel.send("Issue loading config file... whats up with that?")
		return

	await message.channel.send(f"Reloaded NSO Version from config with version: {nsoAppVer}")

@client.event
async def on_ready():
	global client, soundsDir, mysqlHandler, serverUtils, serverVoices, splatInfo, helpfldr, hs
	global nsoHandler, nsoTokens, head, url, dev, owners, commandParser, doneStartup, acHandler, nsoAppVer

	if not doneStartup:
		print('Logged in as,', client.user.name, client.user.id)

		#This is needed due to no prsence intent, prod bot needs to find the devs in its primary server
		print(f"Chunking home server ({str(hs)}) to find owners")
		await client.get_guild(int(hs)).chunk()

		#Get owners from Discord team api
		print("Loading owners...")
		theapp = await client.application_info()
		if theapp.team:
			ownerids = [x.id for x in theapp.team.members]
		else:
			ownerids = [theapp.owner.id]

		for mem in client.get_all_members():
			if mem.id in ownerids:
				owners.append(mem)
				print(f"Loaded owner: {str(mem.name)}")
			if len(owners) == len(ownerids):
				break;
	else:
		print('RECONNECT TO DISCORD')

	if dev == 0:
		print(f"I am in {str(len(client.guilds))} servers, posting to top.gg")
		body = { 'server_count' : len(client.guilds) }
		requests.post(url, headers=head, json=body)
	else:
		print(f"I am in {str(len(client.guilds))} servers")

	if not doneStartup:
		print("Doing Startup...")
		for server in client.guilds:
			#Don't recreate serverVoices on reconnect
			if server.id not in serverVoices:
				serverVoices[server.id] = vserver.voiceServer(client, mysqlHandler, server.id, soundsDir)

		serverConfig = serverconfig.ServerConfig(mysqlHandler)
		commandParser = commandparser.CommandParser(serverConfig, client.user.id)
		serverUtils = serverutils.serverUtils(client, mysqlHandler, serverConfig, helpfldr)
		nsoTokens = nsotoken.Nsotoken(client, mysqlHandler, nsoAppVer)
		nsoHandler = nsohandler.nsoHandler(client, mysqlHandler, nsoTokens, splatInfo, cmdOrder)
		acHandler = achandler.acHandler(client, mysqlHandler, nsoTokens)
		await nsoHandler.updateS2JSON()
		await mysqlHandler.startUp()
		print('Done\n------')
		await client.change_presence(status=discord.Status.online, activity=discord.Game("Use !help for directions!"))
	else:
		print('Finished reconnect')
	doneStartup = True

	sys.stdout.flush()

@client.event
async def on_member_remove(member):
	global serverUtils, doneStartup

	if not doneStartup:
		return

	gid = member.guild.id
	await client.get_guild(gid).chunk()
	for mem in await serverUtils.getAllDM(gid):
		memid = mem[0]
		memobj = client.get_guild(gid).get_member(memid)
		if memobj.guild_permissions.administrator:
			await memobj.send(f"{member.name} left {member.guild.name}")

@client.event
async def on_guild_join(server):
	global serverVoices, head, url, dev, owners, mysqlHandler
	print(f"I joined server: {server.name}")
	serverVoices[server.id] = vserver.voiceServer(client, mysqlHandler, server.id, soundsDir)

	if dev == 0:
		print(f"I am now in {str(len(client.guilds))} servers, posting to top.gg")
		body = { 'server_count' : len(client.guilds) }
		r = requests.post(url, headers=head, json=body)
	else:
		print(f"I am now in {str(len(client.guilds))} servers")

	for mem in owners:
		await mem.send(f"I joined server: {server.name} - I am now in {str(len(client.guilds))} servers")
	sys.stdout.flush()

@client.event
async def on_guild_remove(server):
	global serverVoices, head, url, dev, owners
	print("I left server: " + server.name)
	serverVoices[server.id] = None

	if dev == 0:
		print(f"I am now in {str(len(client.guilds))} servers, posting to top.gg")
		body = { 'server_count' : len(client.guilds) }
		r = requests.post(url, headers=head, json=body)
	else:
		print(f"I am now in {str(len(client.guilds))} servers")

	for mem in owners:
		await mem.send(f"I left server: {server.name} ID: {str(server.id)} - I am now in {str(len(client.guilds))} servers")

	print(f"Trimming DB for serverid: {str(server.id)}")
	await serverUtils.trim_db_from_leave(server.id)
	sys.stdout.flush()

@client.event
async def on_voice_state_update(mem, before, after):
	global client, serverVoices, mysqlHandler, soundsDir, serverUtils

	#Don't care if during startup
	if not doneStartup:
		return
	#Don't do anything if we weren't previously connected
	if before.channel != None:
		server = before.channel.guild.id
	else:
		return
	#Don't do checks if bot is attempting reconnects on its own
	if serverVoices[server].vclient == None:
		return
	#Check for forced disconnects
	if mem.id == client.user.id and after.channel == None:
		print(f"Disconnect, recreating vserver for {str(before.channel.guild.id)}")
		try:
			if serverVoices[server].vclient == None:
				await serverVoices[server].vclient.disconnect()
		except Exception as e:
			print(traceback.format_exc())
			print("Issue in voice disconnect?? Recreating anyway")

		serverVoices[server] = vserver.voiceServer(client, mysqlHandler, server, soundsDir)
		sys.stdout.flush()

def killEval(signum, frame):
	raise asyncio.TimeoutError

async def doEval(message):
	global owners, commandParser
	newout = io.StringIO()
	env = { 'message' : message	}
	env.update(globals())
	env.pop('token')
	env.pop('mysqlHandler')
	env.pop('nsoTokens')
	embed = discord.Embed(colour=0x00FFFF)
	prefix = await commandParser.getPrefix(message.guild.id)
	if message.author not in owners:
		await message.channel.send("You are not an owner, this command is limited to my owners only :cop:")
	else:
		await message.channel.trigger_typing()
		if '```' in message.content:
			code = message.content.replace('`', '').replace(f"{prefix}eval ", '')
			theeval = f"async def func(): \n{textwrap.indent(code, ' ')}"
			try:
				exec(theeval, env)
			except Exception as err:
				embed.title = "**ERROR IN EXEC SETUP**"
				embed.add_field(name="Result", value=str(err), inline=False)
				await message.channel.send(embed=embed)
				return
			func = env['func']
			try:
				signal.signal(signal.SIGALRM, killEval)
				signal.alarm(10)
				with redirect_stdout(newout):
					ret = await func()
				signal.alarm(0)
			except asyncio.TimeoutError:
				embed.title = "**TIMEOUT**"
				embed.add_field(name="TIMEOUT", value="Timeout occured during execution", inline=False)
				await message.channel.send(embed=embed)
				return
			except Exception as err:
				embed.title = "**ERROR IN EXECUTION**"
				embed.add_field(name="Result", value=str(err), inline=False)
				await message.channel.send(embed=embed)
				return
			finally:
				signal.alarm(0)

			embed.title = "**OUTPUT**"
			out = newout.getvalue()
			if (out == ''):
				embed.add_field(name="Result", value="No Output, but succeeded", inline=False)
			else:
				embed.add_field(name="Result", value=out, inline=False)

			await message.channel.send(embed=embed)
		else:
			await message.channel.send("Please provide code in a block")

@client.event
async def on_message(message):
	global serverVoices, soundsDir, serverUtils, mysqlHandler
	global nsoHandler, owners, commandParser, doneStartup, acHandler, nsoTokens

	# Filter out bots and system messages or handling of messages until startup is done
	if message.author.bot or message.type != discord.MessageType.default or not doneStartup:
		return

	command = message.content.lower()
	channel = message.channel
	context = messagecontext.MessageContext(message)

	if message.guild == None:
		if message.author in owners:
			if '!restart' in command:
				await channel.send("Going to restart!")
				await mysqlHandler.close_pool()
				await client.close()
				sys.stderr.flush()
				sys.stdout.flush()
				sys.exit(0)
			elif '!cmdreport' in command:
				await serverUtils.report_cmd_totals(message)
			elif '!nsojson' in command:
				await nsoHandler.getRawJSON(message)
			elif '!announce' in command:
				await serverUtils.doAnnouncement(message)
			elif '!reloadnsoapp' in command:
				await resetNSOVer(message)
		if '!token' in command:
			await nsoTokens.login(message)
		elif '!deletetoken' in command:
				await nsoTokens.delete_tokens(message)
		elif '!storedm' in command:
			await channel.send("Sorry, for performance reasons, you cannot DM me !storedm :frowning:")
		return
	else:
		theServer = message.guild.id

	prefix = await commandParser.getPrefix(theServer)

	if command.startswith('!prefix'):
		await message.channel.send(f"The command prefix for this server is: {prefix}")
	elif message.content.startswith('!help') and prefix not in '!':
		await serverUtils.print_help(message, prefix)
	elif ('pizza' in command and 'pineapple' in command) or ('\U0001F355' in message.content and '\U0001F34D' in message.content):
		await channel.send(f"Don't ever think pineapple and pizza go together {message.author.name}!!!")		

	parsed = await commandParser.parse(theServer, message.content)
	if parsed == None:
		return

	cmd = parsed['cmd']
	args = parsed['args']

	#Don't just fail if command count can't be incremented
	try:
		await serverUtils.increment_cmd(context, cmd)
	except:
		print("Failed to increment command... issue with MySQL?")

	if cmd == 'eval':
		await doEval(message)
	elif cmd == 'getcons' and message.author in owners:
		await mysqlHandler.printCons(message)
	elif cmd == 'reloadnsoapp' and message.author in owners:
		await resetNSOVer(message)
	elif cmd == 'storejson' and message.author in owners:
		await nsoHandler.getStoreJSON(message)
	elif cmd == 'admin':
		if message.guild.get_member(message.author.id) == None:
			await client.get_guild(message.guild.id).chunk()

		if message.author.guild_permissions.administrator:
			if len(args) == 0:
				await message.channel.send("Options for admin commands are playlist, blacklist, dm, prefix, announcement, and feed")
				await serverUtils.print_help(message, prefix)
				return
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
					await serverUtils.addDM(context)
				elif subcommand2 == 'remove':
					await serverUtils.removeDM(context)
			elif subcommand == "announcement":
				subcommand2 = args[1].lower()
				if subcommand2 == 'set':
					await serverUtils.setAnnounceChannel(context, args)
				elif subcommand2 == 'get':
					channel = await serverUtils.getAnnounceChannel(message.guild.id)
					if channel == None:
						await message.channel.send("No channel is set to receive announcements")
					else:
						await message.channel.send(f"Current announcement channel is: {channel.name}")
				elif subcommand2 == 'stop':
					await serverUtils.stopAnnouncements(context)
				else:
					await message.channel.send("Usage: set CHANNEL, get, or stop")
			elif subcommand == 'prefix':
				if (len(args) == 1):
					await channel.send(f"Current command prefix is: {prefix}")
				elif (len(args) != 2) or (len(args[1]) < 0) or (len(args[1]) > 2):
					await channel.send("Usage: ```admin prefix <char>``` where *char* is one or two characters")
				else:
					await commandParser.setPrefix(theServer, args[1])
					await channel.send(f"New command prefix is: {await commandParser.getPrefix(theServer)}")
			elif subcommand == 'feed':
				if len(args) == 1:
					await serverUtils.createFeed(context)
				elif 'delete' in args[1].lower():
					await serverUtils.deleteFeed(context)
		else:
			await channel.send(f"{message.author.name} you are not an admin... :cop:")
	elif cmd == 'alive':
		await channel.send(f"Hey {message.author.name}, I'm alive so shut up! :japanese_goblin:")
	elif cmd == 'rank':
		await nsoHandler.getRanks(context)
	elif cmd == 'order':
		print(f"Ordering gear for user: {message.author.name} and id {str(message.author.id)}")
		await nsoHandler.orderGearCommand(context, args=args)
	elif cmd == 'stats':
		await nsoHandler.getStats(context)
	elif cmd == 'srstats':
		await nsoHandler.getSRStats(context)
	elif cmd == 'storedm':
		await nsoHandler.addStoreDM(context, args)
	elif cmd == 'passport':
		await acHandler.passport(message)
	elif cmd == 'github':
		await channel.send('Here is my github page! : https://github.com/Jetsurf/jet-bot')
	elif cmd == 'support':
		await channel.send('Here is a link to my support server: https://discord.gg/TcZgtP5')
	elif cmd == 'commands' or cmd == 'help':
		await serverUtils.print_help(message, prefix)
	elif cmd == 'sounds':
		theSounds = subprocess.check_output(["ls", soundsDir])
		theSounds = theSounds.decode("utf-8")
		theSounds = theSounds.replace('.mp3', '')
		theSounds = theSounds.replace('\n', ', ')
		await channel.send(f"Current Sounds:\n```{theSounds}```")
	elif cmd == 'join':
		if len(args) > 0:
			await serverVoices[theServer].joinVoiceChannel(context, args)
		else:
			await serverVoices[theServer].joinVoiceChannel(context, args)
	elif cmd == 'currentmaps':
		await nsoHandler.maps(context)
	elif cmd == 'nextmaps':
		await nsoHandler.maps(context, offset=min(11, message.content.count('next')))
	elif cmd == 'currentsr':
		await nsoHandler.srParser(context)
	elif cmd == 'splatnetgear':
		await nsoHandler.gearParser(context)
	elif cmd == 'nextsr':
		await nsoHandler.srParser(context, 1)
	elif (cmd == 'map') or (cmd == 'maps'):
		await nsoHandler.cmdMaps(context, args)
	elif (cmd == 'weapon') or (cmd == 'weapons'):
		await nsoHandler.cmdWeaps(context, args)
	elif (cmd == 'battle') or (cmd == 'battles'):
		if len(args) != 1:
			await message.channel.send("Usage: battle <number>")
		else:
			await nsoHandler.cmdBattles(context, int(args[0]))
	elif serverVoices[theServer].vclient is not None:
		if cmd == 'currentsong':
			if serverVoices[theServer].source is not None:
				await channel.send(f"Currently Playing Video: {serverVoices[theServer].source.yturl}")
			else:
				await channel.send("I'm not playing anything.")
		elif cmd == 'leavevoice':
			await serverVoices[theServer].vclient.disconnect()
			serverVoices[theServer].vclient = None
		elif cmd == 'playrandom':
			if len(args) > 0:
				if args[0].isdigit():
					await serverVoices[theServer].playRandom(context, int(args[0]))
				else:
					await message.channel.send("Num to play must be a number")
			else:
				await serverVoices[theServer].playRandom(context, 1)
		elif cmd == 'play':
			await serverVoices[theServer].setupPlay(context, args)
		elif cmd == 'skip':
			await serverVoices[theServer].stop(ctx)
		elif (cmd == 'end') or (cmd == 'stop'):
			serverVoices[theServer].end()
		elif cmd == 'volume' or cmd == 'vol':
			if len(command.split(' ')) < 2:
				await message.channel.send("Need a value to set volume to!")
				return
			vol = command.split(' ')[1]
			if not vol.isdigit():
				await message.channel.send("Volume must be a digit 1-60")
				return
			if int(vol) > 60:
				vol = 60
			if serverVoices[theServer].source != None:
				await channel.send(f"Setting Volume to {str(vol)}%")
				serverVoices[theServer].source.volume = float(int(vol) / 100)
		elif cmd == 'queue':
			await serverVoices[theServer].printQueue(context)
		else:
			await serverVoices[theServer].playSound(cmd)

	sys.stdout.flush()
	sys.stderr.flush()

#Setup
loadConfig()
if dev == 0:
	sys.stdout = open('./logs/discordbot.log', 'a')
	sys.stderr = open('./logs/discordbot.err', 'a')

print('**********NEW SESSION**********')
print('Logging into discord')

client.add_application_command(maps)
client.add_application_command(admin)
client.add_application_command(weapon)
client.add_application_command(voice)
client.add_application_command(store)

sys.stdout.flush()
sys.stderr.flush()
client.run(token)
