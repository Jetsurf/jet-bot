#!/usr/bin/env python3
from nso_api.nso_api import NSO_API
from nso_api.imink import IMink

import os, sys, re

# Figure out bot directory
dirname = os.path.dirname(sys.argv[0]) or '.'
sys.path.append(f"{dirname}/modules")

#Base Stuffs
import discord, asyncio, subprocess, json, time, itertools
from discord.commands import *
from discord.ui import InputText, Modal
from discord.ext import commands

#DBL Posting
import urllib, urllib.request, requests, aiohttp, pymysql

#Our Classes
import nsotoken, commandparser, serverconfig, ownercmds, messagecontext
import vserver, mysqlhandler, mysqlschema, serverutils
import s2handler, achandler, s3handler
import stringcrypt
import fonts
import cachemanager
import groups
import logging
import friendcodes
import gameinfo.splat2
import gameinfo.splat3
import s3.schedule

# Uncomment for verbose logging from pycord
#logging.basicConfig(level=logging.DEBUG)

configData = None
stringCrypt = stringcrypt.StringCrypt()
fonts = fonts.Fonts(f"{dirname}/fonts/")
cachemanager = cachemanager.CacheManager(f"{dirname}/var/cache")
splat2info = gameinfo.splat2.Splat2()
splat3info = gameinfo.splat3.Splat3(f"{dirname}/data/")
intents = discord.Intents.default()
intents.members = True
client = discord.AutoShardedBot(intents=intents, chunk_guilds_at_startup=False)
commandParser = None
serverConfig = None
mysqlHandler = None
s2Handler = None
s3Handler = None
nsoTokens = None
ownerCmds = None
serverVoices = {}
serverUtils = None
acHandler = None
friendCodes = None
doneStartup = False
owners = []
dev = True
topGgHead = None
keyPath = f"{dirname}/config/db-secret-key.hex"

def loadConfig():
	global configData
	try:
		with open(f"{dirname}/config/discordbot.json", 'r') as json_config:
			configData = json.load(json_config)

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

def startUpLogging():
	if configData.get('output_to_log'):
		os.makedirs(f"{dirname}/logs", exist_ok=True)

		sys.stdout = open(f"{dirname}/logs/discordbot.log", 'a+')
		sys.stdout.reconfigure(line_buffering = True)  # Flush stdout at every newline

		sys.stderr = open(f"{dirname}/logs/discordbot.err", 'a+')

def startUpDB():
	global configData, mysqlHandler, client

	mysqlHandler = mysqlhandler.mysqlHandler(configData['mysql_host'], configData['mysql_user'], configData['mysql_pw'], configData['mysql_db'])

	# Get the secrets the F out!
	configData['mysql_host'] = None
	configData['mysql_user'] = None
	configData['mysql_pw'] = None
	configData['mysql_db'] = None

	client.loop.create_task(startUpDBAsync())

async def startUpDBAsync():
	global mysqlHandler

	await mysqlHandler.startUp()

	mysqlSchema = mysqlschema.MysqlSchema(mysqlHandler)
	await mysqlSchema.update()

def startUpTopGg():
	global configData, topGgHead, dev

	if not 'discordbottok' in configData:
		print("[top.gg] No token for top.gg, so I won't send updates there")
		return

	print("[top.gg] I have a token for top.gg, so I'll update the number of servers I am in")
	topGgHead = { 'Authorization': configData['discordbottok'] }
	dev = False

	# Remove secrets from configData
	configData['discordbottok'] = None

def updateTopGg():
	global topGgHead

	if topGgHead is None:
		return  # We aren't updating top.gg

	# NOTE: We use create_task here because there is no reason for the rest of the bot to wait for completion
	client.loop.create_task(updateTopGgAsync())

async def updateTopGgAsync():
	async with aiohttp.ClientSession() as http_client:
		server_count = len(client.guilds)
		url = f"https://top.gg/api/bots/{str(client.user.id)}/stats"
		body = { 'server_count' : server_count }
		response = await http_client.post(url, headers = topGgHead, json = body)
		print(f"[top.gg] Posted server count {server_count}, response: {response.status}")

def startUp():
	# Vital stuff
	ensureEncryptionKey()
	loadConfig()
	startUpLogging()
	startUpDB()

	print(f"--- Starting up at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} ---")

	# Less-important stuff
	startUpTopGg()

startUp()

# S2
s2Cmds = SlashCommandGroup('s2', 'Splatoon 2')
s2MapCmds = s2Cmds.create_subgroup('maps', 'Splatoon 2 maps')
s2WeaponCmds = s2Cmds.create_subgroup('weapons', 'Splatoon 2 Weapons')
s2StoreCmds = s2Cmds.create_subgroup('store', 'Splatnet 2 store')
s2StoredmCmds = s2Cmds.create_subgroup('storedm', description="Gear DM notifications")
s2StatsCmds = s2Cmds.create_subgroup('stats', 'Gameplay stats')

# S3
if not configData.get('s3_top_level', False):
	s3Cmds = SlashCommandGroup('s3', 'Commands related to Splatoon 3')
	s3WeaponCmds = s3Cmds.create_subgroup('weapon', 'Commands related to weapons in Splatoon 3')
	s3StatsCmds = s3Cmds.create_subgroup('stats', 'Commands related to Splatoon 3 gameplay stats')
	s3StoreDmCmds = s3Cmds.create_subgroup('storedm', 'Splatoon 3 Store gear DMs')
	s3StoreCmds = s3Cmds.create_subgroup('store', 'Splatoon 3 store cmds')
	s3ReplayCmds = s3Cmds.create_subgroup("replays", "Splatoon 3 Replay cmds")
else:
	s3Cmds = client
	s3WeaponCmds = SlashCommandGroup('weapon', 'Commands related to weapons in Splatoon 3')
	s3StatsCmds = SlashCommandGroup('stats', 'Commands related to Splatoon 3 gameplay stats')
	s3StoreDmCmds = SlashCommandGroup('storedm', 'Splatoon 3 Store gear DMs')
	s3StoreCmds = SlashCommandGroup('store', 'Splatoon 3 store cmds')
	s3ReplayCmds = SlashCommandGroup("replays", "Splatoon 3 Replay cmds")

# ACNH
acnhCmds = SlashCommandGroup('acnh', "Commands related to Animal Crossing New Horizons")

# Admin
adminCmds = SlashCommandGroup('admin', 'Commands that require guild admin privledges to run')
adminS2feedCmds = adminCmds.create_subgroup(name='s2feed', description='Admin commands related to SplatNet 2 rotation feeds')
adminS3feedCmds = adminCmds.create_subgroup(name="s3feed", description='Admin commands related to SplatNet 3 rotation feeds')
adminDmCmds = adminCmds.create_subgroup(name='dm', description="Admin commands related to DM's on users leaving")
adminAnnounceCmds = adminCmds.create_subgroup(name='announcements', description='Admin commands related to developer announcements')

# Other
voice = SlashCommandGroup('voice', 'Commands related to voice functions')
owner = SlashCommandGroup('owner', "Commands that are owner only")
groupCmds = SlashCommandGroup('group', 'Commands related to finding a group of players')
fcCmds = SlashCommandGroup('fc', 'Commands for friend codes')
play = voice.create_subgroup(name='play', description='Commands related to playing audio')

@client.slash_command(name='token', description='Manages your tokens to use NSO commands')
async def cmdToken(ctx):
	view = nsotoken.tokenMenuView(nsoTokens, configData['hosted_url'])
	await view.init(ctx)
	await ctx.respond(embed=view.makeEmbed(), view=view, ephemeral=True)

@fcCmds.command(name = "get", description = "Shares your Nintendo Switch friend code")
async def cmdFcGet(ctx):
	fc = await friendCodes.getFriendCode(ctx.user.id)
	if not fc is None:
		await ctx.respond(f"Nintendo Switch friend code is: SW-{fc}")
		return

	# No friend code in the DB, but perhaps they have a token set up?
	nso = await nsoTokens.get_nso_client(ctx.user.id)
	if not nso.is_logged_in():
		await ctx.respond("You have no known friend code! You can set one using `/fc set`, or connect to your Nintendo account using `/token`.", ephemeral = True)
		return

	print(f"No friend code in DB, pulling from NSO for user {ctx.user.id}")
	user = nso.account.get_user_self()
	if user is None:
		await ctx.respond("Something went wrong! Please let my owners in my support guild know this broke!", ephemeral = True)
		print(f"NSO call for friend code failed: userid {ctx.user.id}")
		return

	fc = user['links']['friendCode']['id']
	await friendCodes.setFriendCode(ctx.user.id, fc)
	await ctx.respond(f"Nintendo Switch friend code is: SW-{fc}")

@fcCmds.command(name = "set", description = "Set your Nintendo Switch friend code")
async def cmdFcSet(ctx, friend_code: Option(str, "SW-xxxx-xxxx-xxxx")):
	friend_code = friendCodes.formatFriendCode(friend_code)
	if friend_code is None:
		await ctx.respond("That's a strange looking friend code, try one that looks like: SW-xxxx-xxxx-xxxx", ephemeral = True)
		return

	await friendCodes.setFriendCode(ctx.user.id, friend_code)
	await ctx.respond(f"Okay, I'll remember your friend code of SW-{friend_code}", ephemeral = True)

@client.slash_command(name='support', description='Sends a discord invite to my support guild.')
async def cmdSupport(ctx):
	await ctx.respond('Here is a link to my support server: https://discord.gg/TcZgtP5', ephemeral=True)

@client.slash_command(name='github', description='Sends a link to my github page')
async def cmdGithub(ctx):
	await ctx.respond('Here is my github page! : https://github.com/Jetsurf/jet-bot', ephemeral=True)

@client.slash_command(name='help', description='Displays the help menu')
async def cmdHelp(ctx):
	await ctx.respond("Help Menu:", view=serverutils.HelpMenuView(f"{dirname}/help"))

# --- Admin commands ---

@adminCmds.command(name='playlist', description="Menu to manage the playlist for /voice play random")
async def cmdPlaylistAdd(ctx):
	global mysqlHandler

	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if await checkIfAdmin(ctx):
		playlist = vserver.PlayList(ctx, mysqlHandler)
		await playlist.show()
	else:

		await ctx.respond("You aren't a guild administrator", ephemeral=True)

@adminAnnounceCmds.command(name='set', description="Sets a chat channel to receive announcements from my developers")
async def cmdAnnounceAdd(ctx, channel: Option(discord.TextChannel, "Channel to set to receive announcements", required=True)):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if await checkIfAdmin(ctx):
		await serverUtils.setAnnounceChannel(ctx, channel)
	else:
		await ctx.respond("You aren't a guild administrator", ephemeral=True)

@adminAnnounceCmds.command(name='get', description="Gets the channel that is set to receive annoucements")
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

@adminAnnounceCmds.command(name='remove', description="Removes you from being DM'ed on users leaving")
async def cmdDMRemove(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if await checkIfAdmin(ctx):
		await serverUtils.stopAnnouncements(ctx)
	else:
		await ctx.respond("You aren't a guild administrator")

@adminS2feedCmds.command(name='create', description="Sets up a Splatoon 2 rotation feed for a channel")
async def cmdAdminS2FeedCreate(ctx, maps: Option(bool, "Enable maps in the feed?", required=True), sr: Option(bool, "Enable Salmon Run in the feed?", required=True), gear: Option(bool, "Enable gear in the feed?", required=True)):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if await checkIfAdmin(ctx):
		if not map and not sr and not gear:
			await ctx.respond("Not going to create a feed with nothing in it.")
		else:
			await s2Handler.cmdAdminS2FeedCreate(ctx, args = {"maps": maps, "sr": sr, "gear": gear})
	else:
		await ctx.respond("You aren't a guild administrator", ephemeral=True)

@adminS2feedCmds.command(name='delete', description="Deletes an S2 feed from a channel")
async def cmdAdminS2FeedDelete(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if await checkIfAdmin(ctx):
		await s2Handler.cmdAdminS2FeedDelete(ctx)
	else:
		await ctx.respond("You aren't a guild administrator", ephemeral=True)

@adminS3feedCmds.command(name='create', description='Sets up a Splatoon 3 rotation feed for a channel')
async def cmdAdminS3Feed(ctx, maps: Option(bool, "Include maps in the feed?", required=True), sr: Option(bool, "Include Salmon Run in the feed?", required=True), gear: Option(bool, "Enable gear in the feed?", required=True)):
	if ctx.guild is None:
		await ctx.respond("Can't DM me with this command.")
		return
	elif not await checkIfAdmin(ctx):
		await ctx.respond("You aren't a guild administrator", ephemeral=True)
		return

	await s3Handler.cmdAdminS3FeedCreate(ctx, {"maps": maps, "sr": sr, "gear": gear})

@adminS3feedCmds.command(name='delete', description="Deletes a Splatoon 3 feed from a channel")
async def cmdS3AdminDeleteFeed(ctx):
	if ctx.guild is None:
		await ctx.respond("Can't DM me with this command.")
		return
	elif not await checkIfAdmin(ctx):
		await ctx.respond("You aren't a guild administrator", ephemeral=True)
		return

	await s3Handler.cmdAdminS3FeedDelete(ctx)

@adminDmCmds.command(name='remove', description="Removes you from being DM'ed on users leaving")
async def cmdDMRemove(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if await checkIfAdmin(ctx):
		await serverUtils.removeDM(ctx)
	else:
		await ctx.respond("You aren't a guild administrator", ephemeral=True)

@adminDmCmds.command(name='add', description="Adds you to DM's on users leaving")
async def cmdDMAdd(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if await checkIfAdmin(ctx):
		await serverUtils.addDM(ctx)
	else:
		await ctx.respond("You aren't a guild administrator", ephemeral=True)

# --- ACNH commands ---

@acnhCmds.command(name='passport', description="Posts your ACNH Passport")
async def cmdACNHPassport(ctx):
	await acHandler.passport(ctx)

@acnhCmds.command(name='emote', description="Makes your ACNH character do an emote.")
async def cmdACNHEmote(ctx, emote: Option(str, "The emote to do")):
	await acHandler.ac_emote(ctx, emote)

@acnhCmds.command(name='getemotes', description="Gets available emotes for your ACNH character to do")
async def cmdACNHGetEmotes(ctx):
	await acHandler.get_ac_emotes(ctx)

@acnhCmds.command(name='message', description="What to make your ACNH character say.")
async def cmdACNHEmote(ctx, message: Option(str, "The message to send")):
	await acHandler.ac_message(ctx, message)

# --- Splatoon 2 commands ---

@s2MapCmds.command(name='current', description='Shows current map rotation')
async def cmdCurrentMaps(ctx):
	await ctx.respond(embed=await s2Handler.mapsEmbed())

@s2MapCmds.command(name='next', description='Shows the next maps in rotation')
async def cmdNextMaps(ctx, rotation: Option(int, "Map Rotations ahead to show, max of 11 ahead", required=False, default=1)):
	if rotation < 0 or rotation > 11:
		await ctx.respond("Rotation must be between 1-11")
		return
	if rotation == None:
		rotation = 1

	await ctx.respond(embed=await s2Handler.mapsEmbed(rotation))

@s2MapCmds.command(name='nextsr', description='Shows the next Salmon Run rotation')
async def cmdNextSR(ctx):
	await ctx.respond(embed = s2Handler.srEmbed(getNext=True))

@s2MapCmds.command(name='currentsr', description='Shows the current Salmon Run rotation')
async def cmdCurrentSR(ctx):
	await ctx.respond(embed = s2Handler.srEmbed(getNext=False))

@s2MapCmds.command(name='callout', description="View callout locations for a map")
async def cmdMapsCallout(ctx, map: Option(str, "Map to show callout locations for", choices=[ themap.name() for themap in splat2info.getAllMaps() ] ,required=True)):
	await s2Handler.cmdMaps(ctx, args=[ 'callout', str(map) ])

@s2MapCmds.command(name='list', description="Shows all Splatoon 2 maps")
async def cmdMapsStats(ctx):
	await s2Handler.cmdMaps(ctx, args=[ 'list' ])

@s2MapCmds.command(name='random', description="Generates a random list of maps")
async def cmdMapsRandom(ctx, num: Option(int, "Number of maps to include in the list (1-10)", required=True)):
	if num < 1 or num > 10:
		await ctx.respond("Num needs to be between 1-10")
	else:
		await s2Handler.cmdMaps(ctx, args=[ 'random', str(num)])

@s2StatsCmds.command(name='maps', description="Shows gameplay stats for a map")
async def cmdMapsStats(ctx, map: Option(str, "Map to show stats for", choices=[ themap.name() for themap in splat2info.getAllMaps() ] ,required=True)):
	await s2Handler.cmdMaps(ctx, args=[ 'stats', str(map)])

@s2StatsCmds.command(name='ranks', description='Get your ranks in ranked mode from S2 SplatNet')
async def cmdRanks(ctx):
	await s2Handler.getRanks(ctx)

@s2StatsCmds.command(name='sr', description='Get your Salmon Run stats from S2 SplatNet')
async def cmdSRStats(ctx):
	await s2Handler.getSRStats(ctx)

@s2StatsCmds.command(name='multi', description='Get your multiplayer stats from S2 SplatNet')
async def cmdStats(ctx):
	await s2Handler.getStats(ctx)

@s2StatsCmds.command(name='battle', description='Get stats from a battle (1-50)')
async def cmdBattle(ctx, battlenum: Option(int, "Battle Number, 1 being latest, 50 max", required=True, default=1)):
	if battlenum >= 50 or battlenum < 0:
		await ctx.respond("Battlenum needs to be between 1-50!")
		return
	await s2Handler.battleParser(ctx, battlenum)

@s2WeaponCmds.command(name='info', description='Gets info on a weapon')
async def cmdWeapInfo(ctx, name: Option(str, "Name of the weapon to get info for", required=True)):
	await s2Handler.cmdWeaps(ctx, args=[ 'info', str(name) ])

@s2WeaponCmds.command(name='list', description='Gets a list of weapons by type')
async def cmdWeapList(ctx, weaptype: Option(str, "Type of weapon to generate a list for", required=True, choices=[ weaptype.name() for weaptype in splat2info.getAllWeaponTypes() ])):
	await s2Handler.cmdWeaps(ctx, args=[ 'list', str(weaptype) ])

@s2WeaponCmds.command(name='random', description='Generates a random list of weapons')
async def cmdWeapRandom(ctx, num: Option(int, "Number of weapons to include in the list (1-10)", required=True)):
	if num < 0 or num > 10:
		await ctx.respond("Num must be between 1-10!")
		return

	await s2Handler.cmdWeaps(ctx, args=[ 'random', str(num) ])

@s2WeaponCmds.command(name='special', description='Gets all weapons with special type')
async def cmdWeapSpecial(ctx, special: Option(str, "Name of the special to get matching weapons for", choices=[ weap.name() for weap in splat2info.getAllSpecials() ], required=True)):
	await s2Handler.cmdWeaps(ctx, args=[ 'special', str(special) ])

@s2WeaponCmds.command(name='stats', description='Gets stats from a weapon')
async def cmdWeapStats(ctx, name: Option(str, "Name of the weapon to get stats for", required=True)):
	await s2Handler.cmdWeaps(ctx, args=[ 'stats', str(name) ])

@s2WeaponCmds.command(name='sub', description='Gets all weapons with sub type')
async def cmdWeapSub(ctx, sub: Option(str, "Name of the sub to get matching weapons for", choices=[ weap.name() for weap in splat2info.getAllSubweapons() ], required=True)):
	await s2Handler.cmdWeaps(ctx, args=[ 'sub', str(sub) ])

@s2StoreCmds.command(name='currentgear', description="See the current gear on the SplatNet store")
async def cmdStoreCurrent(ctx):
	await s2Handler.gearParser(ctx)

@s2StoreCmds.command(name='order', description='Orders gear from the SplatNet store')
async def cmdOrder(ctx, order: Option(str, "ID or NAME of the gear to order from the store (get both from /store currentgear)", required=True), override: Option(bool, "Override if you have an item already on order", required=False)):
	print(f"Ordering gear for user: {ctx.user.name} and id {str(ctx.user.id)}")
	await s2Handler.orderGearCommand(ctx, args=[str(order)], override=override if override != None else False)

@s2StoredmCmds.command(name='add', description='Sends a DM when gear with ABILITY/BRAND/GEAR appears in the store')
async def cmdStoreDMAbilty(ctx, flag: Option(str, "ABILITY/BRAND/GEAR to DM you with when it appears in the store", required=True)):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	await s2Handler.addStoreDM(ctx, [ str(flag) ])

@s2StoredmCmds.command(name='list', description='Shows you everything you are set to recieve a DM for')
async def cmdStoreDMAbilty(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	await s2Handler.listStoreDM(ctx)

@s2StoredmCmds.command(name='remove', description='Removes you from being DMed when gear with FLAG appears in the store')
async def cmdStoreDMAbilty(ctx, flag: Option(str, "ABILITY/BRAND/GEAR to stop DMing you with when it appears in the store", required=True)):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	await s2Handler.removeStoreDM(ctx, [ str(flag) ])

# --- S3 commands ---

@s3WeaponCmds.command(name='info', description='Gets info on a weapon in Splatoon 3')
async def cmdS3WeaponInfo(ctx, name: Option(str, "Name of the weapon to get info for", required=True)):
	await s3Handler.cmdWeaponInfo(ctx, str(name))

@s3WeaponCmds.command(name='special', description='Lists all Splatoon 3 weapons with a given special weapon')
async def cmdS3WeaponSpecial(ctx, special: Option(str, "Name of the special to get matching weapons for", choices = splat3info.getSpecialNames(), required=True)):
	await s3Handler.cmdWeaponSpecial(ctx, str(special))

@s3WeaponCmds.command(name='sub', description='Lists all Splatoon 3 weapons with a given subweapon')
async def cmdS3WeaponSub(ctx, special: Option(str, "Name of the subweapon to get matching weapons for", choices = splat3info.getSubweaponNames(), required=True)):
	await s3Handler.cmdWeaponSub(ctx, str(special))

@s3WeaponCmds.command(name='random', description='Picks a random weapon')
async def cmdS3WeaponRandom(ctx):
	await s3Handler.cmdWeaponRandom(ctx)

@s3WeaponCmds.command(name='stats', description="Gets stats for a weapon")
async def cmdS3WeaponStats(ctx, weapon: Option(str, "Name of the weapon to get stats for", required=True)):
	await s3Handler.cmdWeaponStats(ctx, weapon)

@s3StatsCmds.command(name = 'battle', description = 'Get stats from a battle (1-50)')
async def cmdS3StatsBattle(ctx, battlenum: Option(int, "Battle Number, 1 being latest, 50 max", required=True, default=1)):
	if battlenum >= 50 or battlenum < 0:
		await ctx.respond("Battlenum needs to be between 1-50!")
		return
	await s3Handler.cmdStatsBattle(ctx, battlenum)

@s3StatsCmds.command(name = 'multi', description = 'Get your Splatoon 3 multiplayer stats')
async def cmdS3StatsMulti(ctx):
	await s3Handler.cmdStatsMulti(ctx)

@s3StatsCmds.command(name = 'sr', description = 'Get your Splatoon 3 Salmon Run stats')
async def cmdS3Stats(ctx):
	await s3Handler.cmdSRStats(ctx)

@s3StoreDmCmds.command(name = "list", description = 'Gets Splatoon 3 Store DM triggers')
async def cmdS3ListS3StoreDm(ctx):
	await s3Handler.storedm.listS3StoreDm(ctx)

@s3StoreDmCmds.command(name = "add", description = 'Add trigger for when gear appears in the Splatnet 3 Store')
async def cmdS3AddStoreDm(ctx, trigger: Option(str, "Trigger for a DM (Gear Name/Brand/Main Ability)", required = True)):
	await s3Handler.storedm.addS3StoreDm(ctx, trigger)

@s3StoreDmCmds.command(name = "remove", description = 'Remove trigger for when gear appears in the Splatnet 3 Store')
async def cmdS3AddStoreDm(ctx, trigger: Option(str, "Trigger for a DM (Gear Name/Brand/Main Ability)", required = True)):
	await s3Handler.storedm.removeS3StoreDm(ctx, trigger)

@s3Cmds.command(name = 'scrim', description = 'Generate a list of Splatoon 3 maps and modes')
async def cmdS3Scrim(ctx, num: Option(int, "Number of battles (1..20)", required = True), modes: Option(str, "Comma-separated list of modes (default: RM,TC,SZ,CB)", required = True, default = "RM,TC,SZ,CB")):
	await s3Handler.cmdScrim(ctx, num, modes)

@s3Cmds.command(name = 'fest', description = 'Show Splatfest information')
async def cmdS3Fest(ctx):
	await s3Handler.cmdFest(ctx)

@s3Cmds.command(name = 'schedule', description = 'Show schedule')
async def cmdS3Schedule(ctx, which: Option(str, "Schedule type", choices = s3.schedule.S3Schedule.schedule_choices)):
	await s3Handler.cmdSchedule(ctx, which)

@s3Cmds.command(name = 'maps', description = 'Show current maps')
async def cmdS3Maps(ctx):
	await s3Handler.cmdMaps(ctx)

@s3Cmds.command(name = 'srmaps', description = 'Show Salmon Run maps')
async def cmdS3SRMaps(ctx):
	await s3Handler.cmdSRMaps(ctx)

@s3StoreCmds.command(name = "list", description = "Show current items in the store")
async def cmdS3StoreList(ctx):
	await s3Handler.cmdStoreList(ctx)

@s3StoreCmds.command(name = "order", description = "Orders gear from Splatnet")
async def cmdS3StoreOrder(ctx, item: Option(str, "Name of gear to order", required = True), override: Option(bool, "Overrides an existing item on order", default = False)):
	await s3Handler.cmdS3StoreOrder(ctx, item, override)

@s3Cmds.command(name = 'fit', description = 'Posts your current gear loadout')
async def cmdS3Fit(ctx):
	await s3Handler.cmdFit(ctx)

@s3Cmds.command(name = 'gearseed', description = 'Export gear seed checker file')
async def cmdS3Gearseed(ctx):
	await s3Handler.cmdGearseed(ctx)

@s3ReplayCmds.command(name = 'watch', description = 'Watches for and posts replays posted to your account')
async def cmdS3ReplayWatch(ctx):
	await s3Handler.cmdReplayPoster(ctx)

# --- Owner Commands ---

@owner.command(name='eval', description="Eval a code block (Owners only)", default_permission=False)
@commands.is_owner()
async def cmdEval(ctx):
	await ctx.send_modal(ownercmds.evalModal(ownerCmds, title="Eval"))

@owner.command(name="emotes", description="Sets Emotes for use in Embeds (Custom emotes only)", default_permission=False)
@commands.is_owner()
async def emotePicker(ctx, turfwar: Option(str, "Emote to use for turfwar"), ranked: Option(str, "Emote to use for ranked"), league: Option(str, "Emote to use for league"), badge100k: Option(str, "Emote to use for the 100k inked badge"),
	badge500k: Option(str, "Emote to use for the 500k inked badge"), badge1m: Option(str, "Emote to use for the 1m inked badge"), badge10m: Option(str, "Emote to use for the 10m inked badge")):
	
	opts = [ turfwar, ranked, league, badge100k, badge500k, badge1m, badge10m ]
	await ownerCmds.emotePicker(ctx, opts)

# --- Voice Commands ---

@voice.command(name='join', description='Join a voice chat channel')
async def cmdVoiceJoin(ctx, channel: Option(discord.VoiceChannel, "Voice Channel to join", required=False)):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if channel == None:
		await serverVoices[ctx.guild.id].joinVoiceChannel(ctx, [])
	else:
		await serverVoices[ctx.guild.id].joinVoiceChannel(ctx, channel)

@voice.command(name='leave', description="Disconnects the bot from voice")
async def cmdVoiceLeave(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if serverVoices[ctx.guild.id] != None:
		await serverVoices[ctx.guild.id].vclient.disconnect()
		serverVoices[ctx.guild.id].vclient = None
		await ctx.respond("Disconnected from voice")
	else:
		await ctx.respond("Not connected to voice", ephemeral=True)

@voice.command(name='volume', description='Changes the volume while in voice chat')
async def cmdVoiceVolume(ctx, vol: Option(int, "What to change the volume to 1-60% (7% is default)", required=True)):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

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

	if serverVoices[ctx.guild.id].vclient is not None:
		await serverVoices[ctx.guild.id].setupPlay(ctx, [ str(url) ])
	else:
		await ctx.respond("Not connected to voice", ephemeral=True)

@play.command(name='search', description="Searches SOURCE for a playable video/song")
async def cmdVoicePlaySearch(ctx, source: Option(str, "Source to search", choices=[ 'youtube', 'soundcloud' ], required=True), search: Option(str, "Video to search for", required=True)):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

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

	if serverVoices[ctx.guild.id].vclient is not None:
		await serverVoices[ctx.guild.id].printQueue(ctx)
	else:
		await ctx.respond("Not connected to voice.", ephemeral=True)

@voice.command(name='disconnect', description="Disconnects me from voice")
async def cmdVoiceDisconnect(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

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

	await ctx.respond(embed=serverVoices[ctx.guild.id].createSoundsEmbed())

@play.command(name='sound', description="Plays one of my sound clips in voice")
async def cmdVoicePlaySound(ctx, sound: Option(str, "Sound clip to play, get with /voice sounds")):
	if not serverVoices[ctx.guild.id].vclient:
		await ctx.respond("Not connected to voice.", ephemeral=True)
	elif not serverVoices[ctx.guild.id].soundExists(sound):
		await ctx.respond(f"I don't know of a sound named '{sound}'.", ephemeral=True)
	else:
		await ctx.respond(f"Attempting to play: {sound}", ephemeral=True)
		await serverVoices[ctx.guild.id].playSound(sound)

## Group Commands

@groupCmds.command(name = 'create', description = 'Create a group')
async def cmdGroupCreate(ctx):
	await groups.GroupCmds.create(ctx)

@groupCmds.command(name = 'edit', description = 'Edit group settings')
async def cmdGroupEdit(ctx):
	await groups.GroupCmds.edit(ctx)

@groupCmds.command(name = 'disband', description = 'Disband your group')
async def cmdGroupDisband(ctx):
	await groups.GroupCmds.disband(ctx)

@groupCmds.command(name = 'channel', description = 'Set group channel')
async def cmdGroupChannel(ctx, channel: discord.Option(discord.SlashCommandOptionType.channel)):
	if (not ctx.user in owners) and (not ctx.user.guild_permissions.administrator):
		await ctx.respond("You're not allowed to do that.", ephemeral = True)
	else:
		await groups.GroupCmds.channel(ctx, channel)

async def checkIfAdmin(ctx):
	if ctx.guild.get_member(ctx.user.id) == None:
		await client.get_guild(ctx.guild.id).chunk()

	return ctx.user.guild_permissions.administrator

# Set the bot's nickname on the given server to the configured nickname, as
#  long as we have permission and no other nickname has been set already.
async def setNickname(guild):
	global configData

	nickname = configData.get('nickname')

	if not nickname:
		return  # No nickname configured
	elif not guild.me.nick is None:
		return  # Nickname was already customized on this server
	elif not guild.me.guild_permissions.change_nickname:
		return  # No permission to change nickname on this server

	try:
		await guild.me.edit(nick = nickname)
	except Exception as e:
		print(f"Exception setting nickname on server {guild.id}: {e}")

	return

async def retrieveOwners():
	global client, owners

	owners = []
	print("Retrieving bot owners...")

	app = await client.application_info()  # Get owners from Discord team api
	if app.team:
		for mem in app.team.members:
			owner = await client.fetch_user(mem.id)
			if not owner:
				print(f"  Can't get user object for team member {str(mem.name)}#{str(mem.discriminator)} id {mem.id}")
			else:
				owners.append(owner)
	else:
		owners = [app.owner]

	for owner in owners:
		print(f"  Loaded owner: {str(owner.name)}#{str(owner.discriminator)} id {owner.id}")

	return

@client.event
async def on_ready():
	global client, mysqlHandler, serverUtils, serverVoices, splat2info, configData, ownerCmds
	global s2Handler, nsoTokens, dev, owners, commandParser, doneStartup, acHandler, stringCrypt
	global friendCodes, s3Handler

	if not doneStartup:
		print(f"Logged in as {client.user.name}#{client.user.discriminator} id {client.user.id}")

		await retrieveOwners()
	else:
		print('RECONNECT TO DISCORD')

	print(f"I am in {str(len(client.guilds))} servers")
	updateTopGg()

	if not doneStartup:
		print("Doing Startup...")
		for server in client.guilds:
			if server.id not in serverVoices:
				serverVoices[server.id] = vserver.voiceServer(client, mysqlHandler, server.id, configData['soundsdir'], configData['ffmpeg_bin'])

		serverConfig = serverconfig.ServerConfig(mysqlHandler)
		commandParser = commandparser.CommandParser(serverConfig, client.user.id)
		ownerCmds = ownercmds.ownerCmds(client, mysqlHandler, commandParser, owners)
		serverUtils = serverutils.serverUtils(client, mysqlHandler, serverConfig)
		friendCodes = friendcodes.FriendCodes(mysqlHandler, stringCrypt)
		nsoTokens = nsotoken.Nsotoken(client, configData, mysqlHandler, stringCrypt, friendCodes)
		s2Handler = s2handler.S2Handler(client, mysqlHandler, nsoTokens, splat2info, configData)
		s3Handler = s3handler.S3Handler(client, mysqlHandler, nsoTokens, splat3info, configData, fonts, cachemanager)
		acHandler = achandler.acHandler(client, mysqlHandler, nsoTokens, configData)

		groups.Groups.setFriendObjects(client, mysqlHandler, friendCodes)
		await groups.Groups.startup()

		await s2Handler.updateS2JSON()

		#Commented out for now...
		client.loop.create_task(vserver.voiceServer.updatePlaylists(mysqlHandler))  # NOTE: Uses create_task because no need to wait for completion

		client.before_invoke(serverUtils.contextIncrementCmd)
		print('Done\n------')
		await client.change_presence(status=discord.Status.online, activity=discord.Game("Check /help for cmd info."))
	else:
		print('Finished reconnect')
	doneStartup = True

@client.event
async def on_member_remove(member):
	global serverUtils, doneStartup

	if not doneStartup:
		return

	await client.get_guild(member.guild.id).chunk()
	for mem in await serverUtils.getAllDM(member.guild.id):
		memid = mem[0]
		memobj = client.get_guild(member.guild.id).get_member(memid)

		if not memobj:
			continue  # No such member in guild anymore
		elif not memobj.guild_permissions.administrator:
			continue  # Not an administrator

		await memobj.send(f"{member.name} left {member.guild.name}")

@client.event
async def on_guild_join(server):
	global client, serverVoices, url, dev, owners, mysqlHandler, configData
	
	print(f"I joined server: {server.name}")
	serverVoices[server.id] = vserver.voiceServer(client, mysqlHandler, server.id, configData['soundsdir'], configData['ffmpeg_bin'])

	print(f"I am now in {str(len(client.guilds))} servers")
	updateTopGg()

	for mem in owners:
		await mem.send(f"I joined server: {server.name} - I am now in {str(len(client.guilds))} servers")

	await setNickname(server)

@client.event
async def on_guild_remove(server):
	global client, serverVoices, dev, owners

	if server == None:
		return

	print("I left server: " + server.name)
	serverVoices[server.id] = None

	print(f"I am now in {str(len(client.guilds))} servers")
	updateTopGg()

	for mem in owners:
		await mem.send(f"I left server: {server.name} ID: {str(server.id)} - I am now in {str(len(client.guilds))} servers")

	print(f"Trimming DB for serverid: {str(server.id)}")
	await serverUtils.trim_db_from_leave(server.id)
	await s3Handler.removeServer(server.id)

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

		serverVoices[server] = vserver.voiceServer(client, mysqlHandler, server, configData['soundsdir'], configData['ffmpeg_bin'])

@client.event
async def on_message(message):
	global serverUtils, mysqlHandler
	global s2Handler, owners, commandParser, doneStartup, ownerCmds

	# Filter out bots and system messages or handling of messages until startup is done
	if message.author.bot or message.type != discord.MessageType.default or not doneStartup:
		return

	command = message.content.lower()
	channel = message.channel
	context = messagecontext.MessageContext(message)

	if message.guild == None and message.author in owners:
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
		elif command == '!nicknames':
			await channel.send("Okay, setting guild nicknames")
			for g in client.guilds:
				await setNickname(g)
				await asyncio.sleep(15)
		return

	parsed = await commandParser.parse(message.content)
	if parsed == None:
		return

	cmd = parsed['cmd']
	args = parsed['args']

	# Owner commands that can work in channels
	if message.author in owners:
		if cmd == 'eval':
			await ownerCmds.eval(context, ' '.join(args))
		elif cmd == 'getcons':
			await mysqlHandler.printCons(message)
		elif cmd == 'eatcon' and dev:
			await mysqlHandler.connect()
			await message.channel.send("Om nom nom, ate a MySQL connection...")
		elif cmd == 'nsoinfo':
			await ownerCmds.cmdNsoInfo(context, nsoTokens)
		elif cmd == 'nsoversion':
			await ownerCmds.cmdNsoVersion(context, args, nsoTokens)
		elif cmd == 'nsoflush':
			await ownerCmds.cmdNsoFlush(context, nsoTokens)

if dev:
	client.add_application_command(owner)

print('Logging into discord')

client.add_application_command(voice)
client.add_application_command(adminCmds)
client.add_application_command(groupCmds)
client.add_application_command(fcCmds)
client.add_application_command(s2Cmds)
if not configData.get('s3_top_level', False):
	client.add_application_command(s3Cmds)
else:
	client.add_application_command(s3WeaponCmds)
	client.add_application_command(s3StatsCmds)
	client.add_application_command(s3StoreDmCmds)
	client.add_application_command(s3StoreCmds)
client.add_application_command(acnhCmds)

token = configData['token']
configData['token'] = ""

client.run(token)

print(f"--- Shutting down at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} ---")
