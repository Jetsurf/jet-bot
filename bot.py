import os, sys, re
sys.path.append('./modules')
#Base Stuffs
import discord, asyncio, subprocess, json, time, itertools
from discord.commands import *
#DBL Posting
import urllib, urllib.request, requests, pymysql
#Our Classes
import nsotoken, commandparser, serverconfig, splatinfo, messagecontext, ownercmds
import vserver, mysqlhandler, mysqlschema, serverutils, nsohandler, achandler
import stringcrypt

configData = None
stringCrypt = stringcrypt.StringCrypt()
splatInfo = splatinfo.SplatInfo()
intents = discord.Intents.default()
intents.members = True
client = discord.Bot(intents=intents, chunk_guilds_at_startup=False)
commandParser = None
serverConfig = None
mysqlHandler = None
nsoHandler = None
nsoTokens = None
ownerCmds = None
serverVoices = {}
serverUtils = None
acHandler = None
doneStartup = False
owners = []
dev = True
head = {}
keyPath = './config/db-secret-key.hex'

#SubCommand Groups
cmdGroups = {}
maps = SlashCommandGroup('maps', 'Commands related to maps for Splatoon 2')
weapon = SlashCommandGroup('weapons', 'Commands realted to weapons for Splatoon 2')
admin = SlashCommandGroup('admin', 'Commands that require guild admin privledges to run')
voice = SlashCommandGroup('voice', 'Commands related to voice functions')
store = SlashCommandGroup('store', 'Commands related to the Splatoon 2 store')
stats = SlashCommandGroup('stats', 'Commands related to Splatoon 2 gameplay stats')
acnh = SlashCommandGroup('acnh', "Commands related to Animal Crossing New Horizons")
owner = SlashCommandGroup('owner', "Commands that are owner only")
dm = admin.command_group(name='dm', description="Admin commands related to DM's on users leaving")
feed = admin.command_group(name='feed', description='Admin commands related to SplatNet rotation feeds')
announce = admin.command_group(name='announcements', description='Admin commands related to developer annoucenments')
play = voice.command_group(name='play', description='Commands realted to playing audio')
storedm = store.command_group('dm', description="Commands related to DM'ing on store changes")

def loadConfig():
	global configData, helpfldr, mysqlHandler, dev, head
	try:
		with open('./config/discordbot.json', 'r') as json_config:
			configData = json.load(json_config)

		try:
			head = { 'Authorization': configData['discordbottok'] }
			configData['discordbottok'] = ""
			dev = False
		except:
			print('No ID/Token for top.gg, skipping')

		mysqlHandler = mysqlhandler.mysqlHandler(configData['mysql_host'], configData['mysql_user'], configData['mysql_pw'], configData['mysql_db'])

		#Get the secrets the F out!
		configData['mysql_host'] = ""
		configData['mysql_user'] = ""
		configData['mysql_pw'] = ""
		configData['mysql_db'] = ""

		print('Config Loaded')
	except Exception as e:
		print(f"Failed to load config: {str(e)}")
		quit(1)

def ensureEncryptionKey():
	global stringCrypt, keyPath

	if os.path.isfile(keyPath):
		stringCrypt.readSecretKeyFile(keyPath)
	else:
		print("Creating new secret key file...")
		stringCrypt.writeSecretKeyFile(keyPath)

@owner.command(name="emotes", description="Sets Emotes for use in Embeds (Custom emotes only)", default_permission=False)
@permissions.is_owner()
async def emotePicker(ctx, turfwar: Option(str, "Emote to use for turfwar"), ranked: Option(str, "Emote to use for ranked"), league: Option(str, "Emote to use for league"), badge100k: Option(str, "Emote to use for the 100k inked badge"),
	badge500k: Option(str, "Emote to use for the 500k inked badge"), badge1m: Option(str, "Emote to use for the 1m inked badge"), badge10m: Option(str, "Emote to use for the 10m inked badge")):
	
	opts = [ turfwar, ranked, league, badge100k, badge500k, badge1m, badge10m ]
	await ownerCmds.emotePicker(ctx, opts)

@acnh.command(name='passport', description="Posts your ACNH Passport")
async def cmdACNHPassport(ctx):
	await serverUtils.increment_cmd(ctx, 'passport')
	await acHandler.passport(ctx)

@store.command(name='currentgear', description="See the current gear on the SplatNet store")
async def cmdStoreCurrent(ctx):
	await serverUtils.increment_cmd(ctx, 'splatnetgear')
	await nsoHandler.gearParser(ctx)

@store.command(name='order', description='Orders gear from the SplatNet store')
async def cmdOrder(ctx, order: Option(str, "ID or NAME of the gear to order from the store (get both from /store currentgear)", required=True), override: Option(bool, "Override if you have an item already on order", required=False)):
	print(f"Ordering gear for user: {ctx.user.name} and id {str(ctx.user.id)}")
	await serverUtils.increment_cmd(ctx, 'order')
	await nsoHandler.orderGearCommand(ctx, args=[str(order)], override=override if override != None else False)

@storedm.command(name='add', description='Sends a DM when gear with ABILITY/BRAND/GEAR appears in the store')
async def cmdStoreDMAbilty(ctx, flag: Option(str, "ABILITY/BRAND/GEAR to DM you with when it appears in the store", required=True)):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return
	await serverUtils.increment_cmd(ctx, 'storedm')
	await nsoHandler.addStoreDM(ctx, [ str(flag) ], True)

@storedm.command(name='list', description='Shows you everything you are set to recieve a DM for')
async def cmdStoreDMAbilty(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	await serverUtils.increment_cmd(ctx, 'storedm')
	await nsoHandler.listStoreDM(ctx)

@storedm.command(name='remove', description='Removes you from being DMed when gear with FLAG appears in the storer')
async def cmdStoreDMAbilty(ctx, flag: Option(str, "ABILITY/BRAND/GEAR to stop DMing you with when it appears in the store", required=True)):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	await serverUtils.increment_cmd(ctx, 'storedm')
	await nsoHandler.removeStoreDM(ctx, [ str(flag) ])

@client.slash_command(name='support', description='Sends a discord invite to my support guild.')
async def cmdSupport(ctx):
	await ctx.respond('Here is a link to my support server: https://discord.gg/TcZgtP5', ephemeral=True)

@client.slash_command(name='github', description='Sends a link to my github page')
async def cmdGithub(ctx):
	await ctx.respond('Here is my github page! : https://github.com/Jetsurf/jet-bot', ephemeral=True)

@announce.command(name='set', description="Sets a chat channel to receive announcements from my developers")
async def cmdAnnounceAdd(ctx, channel: Option(discord.TextChannel, "Channel to set to receive announcements", required=True)):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if await checkIfAdmin(ctx):
		await serverUtils.setAnnounceChannel(ctx, channel)
	else:
		await ctx.respond("You aren't a guild administrator", ephemeral=True)

@announce.command(name='get', description="Gets the channel that is set to receive annoucements")
async def cmdAnnounceGet(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if await checkIfAdmin(ctx):
		channel = await serverUtils.getAnnounceChannel(ctx.guild.id)
		if channel == None:
			await ctx.respond("No channel is set to receive announcements")
		else:
			await ctx.respond(f"Current announcement channel is: {channel.name}")
	else:
		await ctx.respond("You aren't a guild administrator", ephemeral=True)

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
		await ctx.respond("You aren't a guild administrator", ephemeral=True)

@feed.command(name='delete', description="Deletes a feed from a channel")
async def cmdAdminDeleteFeed(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if await checkIfAdmin(ctx):
		await serverUtils.deleteFeed(ctx, is_slash=True, bypass=True)
	else:
		await ctx.respond("You aren't a guild administrator", ephemeral=True)

@dm.command(name='remove', description="Removes you from being DM'ed on users leaving")
async def cmdDMRemove(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if await checkIfAdmin(ctx):
		await serverUtils.removeDM(ctx)
	else:
		await ctx.respond("You aren't a guild administrator", ephemeral=True)

@dm.command(name='add', description="Adds you to DM's on users leaving")
async def cmdDMAdd(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if await checkIfAdmin(ctx):
		await serverUtils.addDM(ctx)
	else:
		await ctx.respond("You aren't a guild administrator", ephemeral=True)

@maps.command(name='current', description='Shows current map rotation for Turf War/Ranked/League')
async def cmdCurrentMaps(ctx):
	await serverUtils.increment_cmd(ctx, 'currentmaps')
	await ctx.respond(embed=await nsoHandler.mapsEmbed())

@maps.command(name='next', description='Shows the next maps in rotation for Turf War/Ranked/League')
async def cmdNextMaps(ctx, rotation: Option(int, "Map Rotations ahead to show, max of 11 ahead", required=False, default=1)):
	await serverUtils.increment_cmd(ctx, 'nextmaps')
	if rotation < 0 or rotation > 11:
		await ctx.respond("Rotation must be between 1-11")
		return
	if rotation == None:
		rotation = 1

	await ctx.respond(embed=await nsoHandler.mapsEmbed(rotation))

@maps.command(name='nextsr', description='Shows map/weapons for the next Salmon Run rotation')
async def cmdNextSR(ctx):
	await serverUtils.increment_cmd(ctx, 'nextsr')
	await ctx.respond(embed=nsoHandler.srEmbed(getNext=True))

@maps.command(name='currentsr', description='Shows map/weapons for the current Salmon Run rotation')
async def cmdCurrentSR(ctx):
	await serverUtils.increment_cmd(ctx, 'currentsr')
	await ctx.respond(embed=nsoHandler.srEmbed(getNext=False))

@maps.command(name='callout', description="Shows callout locations for a Splatoon 2 map")
async def cmdMapsCallout(ctx, map: Option(str, "Map to show callout locations for", choices=[ themap.name() for themap in splatInfo.getAllMaps() ] ,required=True)):
	await nsoHandler.cmdMaps(ctx, args=[ 'callout', str(map) ])

@maps.command(name='list', description="Shows all Splatoon 2 maps")
async def cmdMapsStats(ctx):
	await serverUtils.increment_cmd(ctx, 'maps')
	await nsoHandler.cmdMaps(ctx, args=[ 'list' ])

@stats.command(name='maps', description="Shows Splatoon 2 gameplay stats for a map")
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

@stats.command(name='ranks', description='Get your ranks in ranked mode from S2 SplatNet')
async def cmdRanks(ctx):
	await serverUtils.increment_cmd(ctx, 'rank')
	await nsoHandler.getRanks(ctx)

@stats.command(name='sr', description='Get your Salmon Run stats from S2 SplatNet')
async def cmdSRStats(ctx):
	await serverUtils.increment_cmd(ctx, 'srstats')
	await nsoHandler.getSRStats(ctx)

@stats.command(name='multi', description='Get your multiplayer stats from S2 SplatNet ')
async def cmdStats(ctx):
	await serverUtils.increment_cmd(ctx, 'stats')
	await nsoHandler.getStats(ctx)

@stats.command(name='battle', description='Get stats from a battle (1-50)')
async def cmdBattle(ctx, battlenum: Option(int, "Battle Number, 1 being latest, 50 max", required=True, default=1)):
	await serverUtils.increment_cmd(ctx, 'battle')
	await nsoHandler.cmdBattles(ctx, battlenum)

#TODO: NEEDS GUILD RESTRICTION - need to dynamically load the home server
@owner.command(name='eval', description="Eval a code block (Owners only)", default_permission=False)
@permissions.is_owner()
async def cmdEval(ctx, code: Option(str, "The code block to eval", required=True)):
	await ownerCmds.eval(ctx, code, slash=True)

@owner.command(name='nsojson', description="Get raw nso json")
@permissions.is_owner()
async def cmdNSOJson(ctx, endpoint: Option(str, "Endpoint to get json from", choices=['base', 'battle', 'fullbattle', 'sr'], required=True), user: Option(str, "ID of a user to mimic", required=False), battleid: Option(str, "If endpoint is fullbattle, provide battleid to get", required=False)):
	if ctx.user not in owners:
		await ctx.respond("Not an owner", ephemeral=True)

	await nsoHandler.getNSOJSONRaw(ctx, { 'endpoint': endpoint, 'user': user, 'battleid': battleid })


@voice.command(name='join', description='Join a voice chat channel')
async def cmdVoiceJoin(ctx, channel: Option(discord.VoiceChannel, "Voice Channel to join", required=False)):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	await serverUtils.increment_cmd(ctx, 'join')
	if channel == None:
		await serverVoices[ctx.guild.id].joinVoiceChannel(ctx, [])
	else:
		await serverVoices[ctx.guild.id].joinVoiceChannel(ctx, channel)

@voice.command(name='leave', description="Disconnects the bot from voice")
async def cmdVoiceLeave(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	await serverUtils.increment_cmd(ctx, 'leavevoice')
	if serverVoices[ctx.guild.id] != None:
		await serverVoices[ctx.guild.id].vclient.disconnect()
		await ctx.respond("Disconnected from voice")
	else:
		await ctx.respond("Not connected to voice", ephemeral=True)

@voice.command(name='volume', description='Changes the volume while in voice chat')
async def cmdVoiceVolume(ctx, vol: Option(int, "What to change the volume to 1-60% (7\% is default)", required=True)):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	await serverUtils.increment_cmd(ctx, 'volume')
	if serverVoices[ctx.guild.id].vclient != None:
		if vol > 60:
			vol = 60
		if serverVoices[ctx.guild.id].source != None:
			await ctx.respond(f"Setting Volume to {str(vol)}%")
			serverVoices[ctx.guild.id].source.volume = float(int(vol) / 100)
		else:
			await ctx.respond("Not playing anything", ephemeral=True)
	else:
		await ctx.respond("Not connected to voice", ephemeral=True)

@play.command(name='url', description='Plays a video from a URL')
async def cmdVoicePlayUrl(ctx, url: Option(str, "URL of the video to play")):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	await serverUtils.increment_cmd(ctx, 'play')
	if serverVoices[ctx.guild.id].vclient is not None:
		await serverVoices[ctx.guild.id].setupPlay(ctx, [ str(url) ])
	else:
		await ctx.respond("Not connected to voice", ephemeral=True)

@play.command(name='search', description="Searches SOURCE for a playable video/song")
async def cmdVoicePlaySearch(ctx, source: Option(str, "Source to search", choices=[ 'youtube', 'soundcloud' ], default='youtube', required=True), search: Option(str, "Video to search for", required = True)):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	await serverUtils.increment_cmd(ctx, 'play')
	if serverVoices[ctx.guild.id].vclient is not None:
		theList = []
		for i in itertools.chain([ source ], search.split()):
			theList.append(i)

		await serverVoices[ctx.guild.id].setupPlay(ctx, theList)
	else:
		await ctx.respond("Not connected to voice", ephemeral=True)

@voice.command(name='skip', description="Skips the currently playing song")
async def cmdVoiceSkip(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	await serverUtils.increment_cmd(ctx, 'skip')
	if serverVoices[ctx.guild.id].vclient is not None:
		if serverVoices[ctx.guild.id].source is not None:
			await serverVoices[ctx.guild.id].stop(ctx)
		else:
			await ctx.respond("Not playing anything", ephemeral=True)
	else:
		ctx.respond("Not connected to voice", ephemeral=True)

@voice.command(name='end', description="Stops playing all videos")
async def cmdVoiceEnd(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	await serverUtils.increment_cmd(ctx, 'stop')
	if serverVoices[ctx.guild.id].vclient is not None:
		if serverVoices[ctx.guild.id].source is not None:
			serverVoices[ctx.guild.id].end()
			await ctx.respond("Stopped playing all videos")
		else:
			await ctx.respond("Not playing anything.", ephemeral=True)
	else:
		await ctx.respond("Not connected to voice", ephemeral=True)

@play.command(name='random', description="Plays a number of videos from this servers playlist")
async def cmdVoicePlayRandom(ctx, num: Option(int, "Number of videos to queue up", required=True)):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	await serverUtils.increment_cmd(ctx, 'playrandom')
	if num < 0:
		await ctx.respond("Num needs to be greater than 0.", ephemeral=True)
	else:
		if serverVoices[ctx.guild.id].vclient is not None:
			await serverVoices[ctx.guild.id].playRandom(ctx, num)
		else:
			await ctx.respond("Not connected to voice", ephemeral=True)

@voice.command(name='currentsong', description="Shows the currently playing video")
async def cmdVoiceCurrent(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	await serverUtils.increment_cmd(ctx, 'currentsong')
	if serverVoices[ctx.guild.id].vclient is not None:
		if serverVoices[ctx.guild.id].source is not None:
			await ctx.respond(f"Currently Playing Video: {serverVoices[ctx.guild.id].source.yturl}")
		else:
			await ctx.respond("I'm not playing anything.", ephemeral=True)
	else:
		await ctx.respond("Not connected to voice", ephemeral=True)

@voice.command(name='queue', description="Shows the current queue of videos to play")
async def cmdVoiceQueue(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	await serverUtils.increment_cmd(ctx, 'queue')
	if serverVoices[ctx.guild.id].vclient is not None:
		await serverVoices[ctx.guild.id].printQueue(ctx)
	else:
		await ctx.respond("Not connected to voice.", ephemeral=True)

@voice.command(name='disconnect', description="Disconnects me from voice")
async def cmdVoiceDisconnect(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	await serverUtils.increment_cmd(ctx, 'leavevoice')
	if serverVoices[ctx.guild.id] != None:
		await serverVoices[ctx.guild.id].vclient.disconnect()
		serverVoices[ctx.guild.id].vclient = None
		await ctx.respond("Disconnected from voice.")
	else:
		await ctx.respond("Not connected to voice.", ephemeral=True)

@voice.command(name='sounds', description="Shows sounds I can play with /voice play sound")
async def cmdVoiceSounds(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	await serverUtils.increment_cmd(ctx, 'sounds')

	await ctx.respond(embed=serverVoices[ctx.guild.id].createSoundsEmbed())

@play.command(name='sound', description="Plays one of my sound clips in voice")
async def cmdVoicePlaySound(ctx, sound: Option(str, "Sound clip to play, get with /voice sounds")):
	if serverVoices[ctx.guild.id].vclient is not None:
		await ctx.respond(f"Attempting to play: {sound}", ephemeral=True)
		await serverVoices[ctx.guild.id].playSound(sound)
	else:
		await ctx.respond("Not connected to voice.", ephemeral=True)

@admin.command(name='playlist', description="Adds a URL or the current video to my playlist for /voice play random")
async def cmdPlaylistAdd(ctx, url: Option(str, "URL to add to my playlist", required=True)):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if await checkIfAdmin(ctx):
		await serverVoices[ctx.guild.id].addGuildList(ctx, [ url ])
	else:
		await ctx.respond("You aren't a guild administrator", ephemeral=True)

async def checkIfAdmin(ctx):
	if ctx.guild.get_member(ctx.user.id) == None:
		await client.get_guild(ctx.guild.id).chunk()

	return ctx.user.guild_permissions.administrator

@client.event
async def on_ready():
	global client, mysqlHandler, serverUtils, serverVoices, splatInfo, configData, ownerCmds
	global nsoHandler, nsoTokens, head, dev, owners, commandParser, doneStartup, acHandler, stringCrypt

	if not doneStartup:
		print('Logged in as,', client.user.name, client.user.id)

		#This is needed due to no prsence intent, prod bot needs to find the devs in its primary server
		print(f"Chunking home server ({str(configData['home_server'])}) to find owners")
		await client.get_guild(int(configData['home_server'])).chunk()

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

	if not dev:
		print(f"I am in {str(len(client.guilds))} servers, posting to top.gg")
		body = { 'server_count' : len(client.guilds) }
		requests.post(f"https://top.gg/api/bots/{str(client.user.id)}/stats", headers=head, json=body)
	else:
		print(f"I am in {str(len(client.guilds))} servers")

	if not doneStartup:
		print("Doing Startup...")
		for server in client.guilds:
			if server.id not in serverVoices:
				serverVoices[server.id] = vserver.voiceServer(client, mysqlHandler, server.id, configData['soundsdir'])

		serverConfig = serverconfig.ServerConfig(mysqlHandler)
		commandParser = commandparser.CommandParser(serverConfig, client.user.id)
		ownerCmds = ownercmds.ownerCmds(client, mysqlHandler, commandParser, owners)
		serverUtils = serverutils.serverUtils(client, mysqlHandler, serverConfig, configData['help'])
		nsoTokens = nsotoken.Nsotoken(client, mysqlHandler, configData.get('hosted_url'), stringCrypt)
		nsoHandler = nsohandler.nsoHandler(client, mysqlHandler, nsoTokens, splatInfo, configData.get('hosted_url'))
		acHandler = achandler.acHandler(client, mysqlHandler, nsoTokens, configData)
		await mysqlHandler.startUp()
		mysqlSchema = mysqlschema.MysqlSchema(mysqlHandler)
		await mysqlSchema.update()
		await nsoTokens.migrateTokensTable()

		await nsoHandler.updateS2JSON()
		await nsoTokens.updateAppVersion()
		print('Done\n------')
		await client.change_presence(status=discord.Status.online, activity=discord.Game("Check Slash Commands!"))
	else:
		print('Finished reconnect')
	doneStartup = True

	sys.stdout.flush()

@client.event
async def on_member_remove(member):
	global serverUtils, doneStartup

	if not doneStartup:
		return

	await client.get_guild(member.guild.id).chunk()
	for mem in await serverUtils.getAllDM(member.guild.id):
		memid = mem[0]
		memobj = client.get_guild(member.guild.id).get_member(memid)
		if memobj.guild_permissions.administrator:
			await memobj.send(f"{member.name} left {member.guild.name}")

@client.event
async def on_guild_join(server):
	global client, serverVoices, head, url, dev, owners, mysqlHandler, configData
	
	print(f"I joined server: {server.name}")
	serverVoices[server.id] = vserver.voiceServer(client, mysqlHandler, server.id, configData['soundsdir'])

	if not dev:
		print(f"I am now in {str(len(client.guilds))} servers, posting to top.gg")
		body = { 'server_count' : len(client.guilds) }
		r = requests.post(f"https://top.gg/api/bots/{str(client.user.id)}/stats", headers=head, json=body)
	else:
		print(f"I am now in {str(len(client.guilds))} servers")

	for mem in owners:
		await mem.send(f"I joined server: {server.name} - I am now in {str(len(client.guilds))} servers")
	sys.stdout.flush()

@client.event
async def on_guild_remove(server):
	global client, serverVoices, head, dev, owners

	if server == None:
		return

	print("I left server: " + server.name)
	serverVoices[server.id] = None

	if not dev:
		print(f"I am now in {str(len(client.guilds))} servers, posting to top.gg")
		body = { 'server_count' : len(client.guilds) }
		r = requests.post(f"https://top.gg/api/bots/{str(client.user.id)}/stats", headers=head, json=body)
	else:
		print(f"I am now in {str(len(client.guilds))} servers")

	for mem in owners:
		await mem.send(f"I left server: {server.name} ID: {str(server.id)} - I am now in {str(len(client.guilds))} servers")

	print(f"Trimming DB for serverid: {str(server.id)}")
	await serverUtils.trim_db_from_leave(server.id)
	sys.stdout.flush()

@client.event
async def on_voice_state_update(mem, before, after):
	global client, serverVoices, mysqlHandler, serverUtils, doneStartup

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
			if serverVoices[server].vclient != None:
				await serverVoices[server].vclient.disconnect()
		except Exception as e:
			print(traceback.format_exc())
			print("Issue in voice disconnect?? Recreating anyway")

		serverVoices[server] = vserver.voiceServer(client, mysqlHandler, server, configData['soundsdir'])
		sys.stdout.flush()

@client.event
async def on_message(message):
	global serverVoices, serverUtils, mysqlHandler
	global nsoHandler, owners, commandParser, doneStartup, acHandler, nsoTokens, ownerCmds

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
			elif '!announce' in command:
				await serverUtils.doAnnouncement(message)
		if '!token' in command:
			await nsoTokens.login(context)
		elif '!deletetoken' in command:
				await nsoTokens.deleteTokens(context)
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
		await ownerCmds.eval(context, args[0])
	elif cmd == 'getcons' and message.author in owners:
		await mysqlHandler.printCons(message)
	elif cmd == 'storejson' and message.author in owners:
		await nsoHandler.getStoreJSON(context)
	elif cmd == 'admin':
		if await checkIfAdmin(context):
			if len(args) == 0:
				await message.channel.send("Options for admin commands are playlist, blacklist, dm, prefix, announcement, and feed")
				await serverUtils.print_help(message, prefix)
				return
			subcommand = args[0].lower()
			if subcommand == 'playlist':
				await serverVoices[theServer].addGuildList(context, args)
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
		await nsoHandler.orderGearCommand(context, args=args, is_slash=False)
	elif cmd == 'stats':
		await nsoHandler.getStats(context)
	elif cmd == 'srstats':
		await nsoHandler.getSRStats(context)
	elif cmd == 'storedm':
		await nsoHandler.addStoreDM(context, args)
	elif cmd == 'passport':
		await acHandler.passport(context)
	elif cmd == 'github':
		await channel.send('Here is my github page! : https://github.com/Jetsurf/jet-bot')
	elif cmd == 'support':
		await channel.send('Here is a link to my support server: https://discord.gg/TcZgtP5')
	elif cmd == 'commands' or cmd == 'help':
		await serverUtils.print_help(message, prefix)
	elif cmd == 'sounds':
		await channel.send(embed=serverVoices[theServer].createSoundsEmbed())
	elif cmd == 'join':
		if len(args) > 0:
			await serverVoices[theServer].joinVoiceChannel(context, args)
		else:
			await serverVoices[theServer].joinVoiceChannel(context, args)
	elif cmd == 'currentmaps':
		await message.channel.send(embed=await nsoHandler.mapsEmbed())
	elif cmd == 'nextmaps':
		await message.channel.send(embed=await nsoHandler.mapsEmbed(offset=min(11, message.content.count('next'))))
	elif cmd == 'currentsr':
		await message.channel.send(embed=nsoHandler.srEmbed())
	elif cmd == 'splatnetgear':
		await nsoHandler.gearParser(context)
	elif cmd == 'nextsr':
		await message.channel.send(embed=nsoHandler.srEmbed(getNext=True))
	elif (cmd == 'map') or (cmd == 'maps'):
		await nsoHandler.cmdMaps(context, args)
	elif (cmd == 'weapon') or (cmd == 'weapons'):
		await nsoHandler.cmdWeaps(context, args)
	elif (cmd == 'battle') or (cmd == 'battles'):
		if len(args) < 1:
			await message.channel.send("Usage: battle num <number> or battle last")
		else:
			if args[0] == 'last':
				await nsoHandler.cmdBattles(context, 1)
			elif args[0] == 'num' and len(args) > 1:
				await nsoHandler.cmdBattles(context, int(args[1]))
			else:
				await message.channel.send("Usage: battle num <number> or battle last")
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
			await serverVoices[theServer].stop(context)
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
if configData.get('output_to_log'):
	os.makedirs('./logs', exist_ok=True)
	sys.stdout = open('./logs/discordbot.log', 'a')
	sys.stderr = open('./logs/discordbot.err', 'a')

ensureEncryptionKey()

print('**********NEW SESSION**********')
print('Logging into discord')

client.add_application_command(store)
client.add_application_command(maps)
client.add_application_command(weapon)
client.add_application_command(stats)
client.add_application_command(voice)
client.add_application_command(admin)
client.add_application_command(acnh)

if dev:
	client.add_application_command(owner)

sys.stdout.flush()
sys.stderr.flush()
token = configData['token']
configData['token'] = ""
client.run(token)
