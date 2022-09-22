#!/usr/bin/env python3
from pynso.nso_api import NSO_API
from pynso.imink import IMink

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
import urllib, urllib.request, requests, pymysql

#Our Classes
import nsotoken, commandparser, serverconfig, splatinfo, ownercmds, messagecontext
import vserver, mysqlhandler, mysqlschema, serverutils
import nsohandler, achandler, s3handler
import stringcrypt
import groups
import logging
import friendcodes
import gameinfo.splat3

# Uncomment for verbose logging from pycord
#logging.basicConfig(level=logging.DEBUG)

configData = None
stringCrypt = stringcrypt.StringCrypt()
splatInfo = splatinfo.SplatInfo()
splat3info = gameinfo.splat3.Splat3()
intents = discord.Intents.default()
intents.members = True
client = discord.AutoShardedBot(intents=intents, chunk_guilds_at_startup=False)
commandParser = None
serverConfig = None
mysqlHandler = None
nsoHandler = None
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
head = {}
keyPath = f"{dirname}/config/db-secret-key.hex"

# S2
s2Cmds = SlashCommandGroup('s2', 'Splatoon 2')
s2MapCmds = s2Cmds.create_subgroup('maps', 'Splatoon 2 maps')
s2WeaponCmds = s2Cmds.create_subgroup('weapons', 'Splatoon 2 Weapons')
s2StoreCmds = s2Cmds.create_subgroup('store', 'Splatnet 2 store')
s2StoredmCmds = s2Cmds.create_subgroup('storedm', description="Gear DM notifications")
s2StatsCmds = s2Cmds.create_subgroup('stats', 'Gameplay stats')

# S3
s3Cmds = SlashCommandGroup('s3', 'Commands related to Splatoon 3')
s3WeaponCmds = s3Cmds.create_subgroup('weapon', 'Commands related to weapons in Splatoon 3')
s3StatsCmds = s3Cmds.create_subgroup('stats', 'Commands related to Splatoon 3 gameplay stats')

# ACNH
acnhCmds = SlashCommandGroup('acnh', "Commands related to Animal Crossing New Horizons")

# Admin
adminCmds = SlashCommandGroup('admin', 'Commands that require guild admin privledges to run')
adminS2feedCmds = adminCmds.create_subgroup(name='s2feed', description='Admin commands related to SplatNet 2 rotation feeds')
adminDmCmds = adminCmds.create_subgroup(name='dm', description="Admin commands related to DM's on users leaving")
adminAnnounceCmds = adminCmds.create_subgroup(name='announcements', description='Admin commands related to developer announcements')

# Other
voice = SlashCommandGroup('voice', 'Commands related to voice functions')
owner = SlashCommandGroup('owner', "Commands that are owner only")
groupCmds = SlashCommandGroup('group', 'Commands related to finding a group of players')
fcCmds = SlashCommandGroup('fc', 'Commands for friend codes')
play = voice.create_subgroup(name='play', description='Commands related to playing audio')

def loadConfig():
	global configData, helpfldr, mysqlHandler, dev, head, pynso
	try:
		with open(f"{dirname}/config/discordbot.json", 'r') as json_config:
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

@client.slash_command(name='token', description='Manages your tokens to use NSO commands')
async def cmdToken(ctx):
	view = nsotoken.tokenMenuView(nsoTokens, configData['hosted_url'])
	await view.init(ctx)

	if view.isDupe:
		embed = discord.Embed(colour=0x3FFF33)
		embed.title = "Token Management"
		embed.add_field(name="Token is already setup", value="Press cancel to close or 'Delete Token' to delete your tokens")
	else:
		embed = discord.Embed(colour=0x3FFF33)
		embed.title = "Instructions"
		embed.add_field(name="Sign In", value="1) Click the \"Sign In Link\" button\n2) Sign into your nintendo account\n3) Right click the \"Select this person\" button and copy the link address\n3) Hit \"Submit URL\" and paste in the link to complete setup.", inline=False)
		embed.set_image(url=f"{configData['hosted_url']}/images/nsohowto.png")

	await ctx.respond(embed=embed, view=view, ephemeral=True)

@fcCmds.command(name = "get", description = "Shares your Nintendo Switch friend code")
async def cmdFcGet(ctx):
	await serverUtils.increment_cmd(ctx, 'fc')

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

@owner.command(name="emotes", description="Sets Emotes for use in Embeds (Custom emotes only)", default_permission=False)
@commands.is_owner()
async def emotePicker(ctx, turfwar: Option(str, "Emote to use for turfwar"), ranked: Option(str, "Emote to use for ranked"), league: Option(str, "Emote to use for league"), badge100k: Option(str, "Emote to use for the 100k inked badge"),
	badge500k: Option(str, "Emote to use for the 500k inked badge"), badge1m: Option(str, "Emote to use for the 1m inked badge"), badge10m: Option(str, "Emote to use for the 10m inked badge")):
	
	opts = [ turfwar, ranked, league, badge100k, badge500k, badge1m, badge10m ]
	await ownerCmds.emotePicker(ctx, opts)

@client.slash_command(name='support', description='Sends a discord invite to my support guild.')
async def cmdSupport(ctx):
	await serverUtils.increment_cmd(ctx, 'support')
	await ctx.respond('Here is a link to my support server: https://discord.gg/TcZgtP5', ephemeral=True)

@client.slash_command(name='github', description='Sends a link to my github page')
async def cmdGithub(ctx):
	await serverUtils.increment_cmd(ctx, 'github')
	await ctx.respond('Here is my github page! : https://github.com/Jetsurf/jet-bot', ephemeral=True)

@client.slash_command(name='help', description='Displays the help menu')
async def cmdHelp(ctx):
	await serverUtils.increment_cmd(ctx, 'help')
	await ctx.respond("Help Menu:", view=serverutils.HelpMenuView(configData['help']))

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

@adminS2feedCmds.command(name='delete', description="Deletes a feed from a channel")
async def cmdAdminDeleteFeed(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if await checkIfAdmin(ctx):
		#TODO: Add view to confirm delete, better than using an argument - this will be a future update
		await serverUtils.deleteFeed(ctx, bypass=True)
	else:
		await ctx.respond("You aren't a guild administrator", ephemeral=True)

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
	await serverUtils.increment_cmd(ctx, 'passport')
	await acHandler.passport(ctx)

@acnhCmds.command(name='emote', description="Makes your ACNH character do an emote.")
async def cmdACNHEmote(ctx, emote: Option(str, "The emote to do")):
	await serverUtils.increment_cmd(ctx, 'emote')
	await acHandler.ac_emote(ctx, emote)

@acnhCmds.command(name='getemotes', description="Gets available emotes for your ACNH character to do")
async def cmdACNHGetEmotes(ctx):
	await serverUtils.increment_cmd(ctx, 'getemotes')
	await acHandler.get_ac_emotes(ctx)

@acnhCmds.command(name='message', description="What to make your ACNH character say.")
async def cmdACNHEmote(ctx, message: Option(str, "The message to send")):
	await serverUtils.increment_cmd(ctx, 'message')
	await acHandler.ac_message(ctx, message)

# --- Splatoon 2 commands ---

@s2MapCmds.command(name='current', description='Shows current map rotation')
async def cmdCurrentMaps(ctx):
	await serverUtils.increment_cmd(ctx, 'currentmaps')
	await ctx.respond(embed=await nsoHandler.mapsEmbed())

@s2MapCmds.command(name='next', description='Shows the next maps in rotation')
async def cmdNextMaps(ctx, rotation: Option(int, "Map Rotations ahead to show, max of 11 ahead", required=False, default=1)):
	await serverUtils.increment_cmd(ctx, 'nextmaps')
	if rotation < 0 or rotation > 11:
		await ctx.respond("Rotation must be between 1-11")
		return
	if rotation == None:
		rotation = 1

	await ctx.respond(embed=await nsoHandler.mapsEmbed(rotation))

@s2MapCmds.command(name='nextsr', description='Shows the next Salmon Run rotation')
async def cmdNextSR(ctx):
	await serverUtils.increment_cmd(ctx, 'nextsr')
	await ctx.respond(embed=nsoHandler.srEmbed(getNext=True))

@s2MapCmds.command(name='currentsr', description='Shows the current Salmon Run rotation')
async def cmdCurrentSR(ctx):
	await serverUtils.increment_cmd(ctx, 'currentsr')
	await ctx.respond(embed=nsoHandler.srEmbed(getNext=False))

@s2MapCmds.command(name='callout', description="View callout locations for a map")
async def cmdMapsCallout(ctx, map: Option(str, "Map to show callout locations for", choices=[ themap.name() for themap in splatInfo.getAllMaps() ] ,required=True)):
	await nsoHandler.cmdMaps(ctx, args=[ 'callout', str(map) ])

@s2MapCmds.command(name='list', description="Shows all Splatoon 2 maps")
async def cmdMapsStats(ctx):
	await serverUtils.increment_cmd(ctx, 'maps')
	await nsoHandler.cmdMaps(ctx, args=[ 'list' ])

@s2MapCmds.command(name='random', description="Generates a random list of maps")
async def cmdMapsRandom(ctx, num: Option(int, "Number of maps to include in the list (1-10)", required=True)):
	await serverUtils.increment_cmd(ctx, 'maps')
	if num < 1 or num > 10:
		await ctx.respond("Num needs to be between 1-10")
	else:
		await nsoHandler.cmdMaps(ctx, args=[ 'random', str(num)])

@s2StatsCmds.command(name='maps', description="Shows gameplay stats for a map")
async def cmdMapsStats(ctx, map: Option(str, "Map to show stats for", choices=[ themap.name() for themap in splatInfo.getAllMaps() ] ,required=True)):
	await serverUtils.increment_cmd(ctx, 'maps')
	await nsoHandler.cmdMaps(ctx, args=[ 'stats', str(map)])

@s2StatsCmds.command(name='ranks', description='Get your ranks in ranked mode from S2 SplatNet')
async def cmdRanks(ctx):
	await serverUtils.increment_cmd(ctx, 'rank')
	await nsoHandler.getRanks(ctx)

@s2StatsCmds.command(name='sr', description='Get your Salmon Run stats from S2 SplatNet')
async def cmdSRStats(ctx):
	await serverUtils.increment_cmd(ctx, 'srstats')
	await nsoHandler.getSRStats(ctx)

@s2StatsCmds.command(name='multi', description='Get your multiplayer stats from S2 SplatNet')
async def cmdStats(ctx):
	await serverUtils.increment_cmd(ctx, 'stats')
	await nsoHandler.getStats(ctx)

@s2StatsCmds.command(name='battle', description='Get stats from a battle (1-50)')
async def cmdBattle(ctx, battlenum: Option(int, "Battle Number, 1 being latest, 50 max", required=True, default=1)):
	if battlenum >= 50 or battlenum < 0:
		await ctx.respond("Battlenum needs to be between 1-50!")
		return
	await serverUtils.increment_cmd(ctx, 'battle')
	await nsoHandler.battleParser(ctx, battlenum)

@s2WeaponCmds.command(name='info', description='Gets info on a weapon')
async def cmdWeapInfo(ctx, name: Option(str, "Name of the weapon to get info for", required=True)):
	await serverUtils.increment_cmd(ctx, 'weapons')

	await nsoHandler.cmdWeaps(ctx, args=[ 'info', str(name) ])

@s2WeaponCmds.command(name='list', description='Gets a list of weapons by type')
async def cmdWeapList(ctx, weaptype: Option(str, "Type of weapon to generate a list for", required=True, choices=[ weaptype.name() for weaptype in splatInfo.getAllWeaponTypes() ])):
	await serverUtils.increment_cmd(ctx, 'weapons')

	await nsoHandler.cmdWeaps(ctx, args=[ 'list', str(weaptype) ])

@s2WeaponCmds.command(name='random', description='Generates a random list of weapons')
async def cmdWeapRandom(ctx, num: Option(int, "Number of weapons to include in the list (1-10)", required=True)):
	await serverUtils.increment_cmd(ctx, 'weapons')
	if num < 0 or num > 10:
		await ctx.respond("Num must be between 1-10!")
		return

	await nsoHandler.cmdWeaps(ctx, args=[ 'random', str(num) ])

@s2WeaponCmds.command(name='special', description='Gets all weapons with special type')
async def cmdWeapSpecial(ctx, special: Option(str, "Name of the special to get matching weapons for", choices=[ weap.name() for weap in splatInfo.getAllSpecials() ], required=True)):
	await serverUtils.increment_cmd(ctx, 'weapons')

	await nsoHandler.cmdWeaps(ctx, args=[ 'special', str(special) ])

@s2WeaponCmds.command(name='stats', description='Gets stats from a weapon')
async def cmdWeapStats(ctx, name: Option(str, "Name of the weapon to get stats for", required=True)):
	await serverUtils.increment_cmd(ctx, 'weapons')

	await nsoHandler.cmdWeaps(ctx, args=[ 'stats', str(name) ])

@s2WeaponCmds.command(name='sub', description='Gets all weapons with sub type')
async def cmdWeapSub(ctx, sub: Option(str, "Name of the sub to get matching weapons for", choices=[ weap.name() for weap in splatInfo.getAllSubweapons() ], required=True)):
	await serverUtils.increment_cmd(ctx, 'weapons')

	await nsoHandler.cmdWeaps(ctx, args=[ 'sub', str(sub) ])

@s2StoreCmds.command(name='currentgear', description="See the current gear on the SplatNet store")
async def cmdStoreCurrent(ctx):
	await serverUtils.increment_cmd(ctx, 'splatnetgear')
	await nsoHandler.gearParser(ctx)

@s2StoreCmds.command(name='order', description='Orders gear from the SplatNet store')
async def cmdOrder(ctx, order: Option(str, "ID or NAME of the gear to order from the store (get both from /store currentgear)", required=True), override: Option(bool, "Override if you have an item already on order", required=False)):
	print(f"Ordering gear for user: {ctx.user.name} and id {str(ctx.user.id)}")
	await serverUtils.increment_cmd(ctx, 'order')
	await nsoHandler.orderGearCommand(ctx, args=[str(order)], override=override if override != None else False)

@s2StoredmCmds.command(name='add', description='Sends a DM when gear with ABILITY/BRAND/GEAR appears in the store')
async def cmdStoreDMAbilty(ctx, flag: Option(str, "ABILITY/BRAND/GEAR to DM you with when it appears in the store", required=True)):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return
	await serverUtils.increment_cmd(ctx, 'storedm')
	await nsoHandler.addStoreDM(ctx, [ str(flag) ])

@s2StoredmCmds.command(name='list', description='Shows you everything you are set to recieve a DM for')
async def cmdStoreDMAbilty(ctx):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	await serverUtils.increment_cmd(ctx, 'storedm')
	await nsoHandler.listStoreDM(ctx)

@s2StoredmCmds.command(name='remove', description='Removes you from being DMed when gear with FLAG appears in the store')
async def cmdStoreDMAbilty(ctx, flag: Option(str, "ABILITY/BRAND/GEAR to stop DMing you with when it appears in the store", required=True)):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	await serverUtils.increment_cmd(ctx, 'storedm')
	await nsoHandler.removeStoreDM(ctx, [ str(flag) ])

# --- S3 commands ---

@s3WeaponCmds.command(name='info', description='Gets info on a weapon in Splatoon 3')
async def cmdS3WeaponInfo(ctx, name: Option(str, "Name of the weapon to get info for", required=True)):
	await s3Handler.cmdWeaponInfo(ctx, str(name))

@s3WeaponCmds.command(name='special', description='Lists all Splatoon 3 weapons a given special weapon')
async def cmdS3WeaponSpecial(ctx, special: Option(str, "Name of the special to get matching weapons for", choices = splat3info.getSpecialNames(), required=True)):
	await s3Handler.cmdWeaponSpecial(ctx, str(special))

@s3WeaponCmds.command(name='sub', description='Lists all Splatoon 3 weapons a given subweapon')
async def cmdS3WeaponSub(ctx, special: Option(str, "Name of the subweapon to get matching weapons for", choices = splat3info.getSubweaponNames(), required=True)):
	await s3Handler.cmdWeaponSub(ctx, str(special))

@s3Cmds.command(name = 'scrim', description = 'Generate a list of Splatoon 3 maps and modes')
async def cmdS3Scrim(ctx, num: Option(int, "Number of battles (1..20)", required = True), modes: Option(str, "Comma-separated list of modes (default: RM,TC,SZ,CB)", required = True, default = "RM,TC,SZ,CB")):
	await s3Handler.cmdScrim(ctx, num, modes)

@s3Cmds.command(name = 'fest', description = 'Show Splatfest information')
async def cmdS3Fest(ctx):
	await s3Handler.cmdFest(ctx)

@s3StatsCmds.command(name = 'battle', description = 'Get stats from a battle (1-50)')
async def cmdS3StatsBattle(ctx, battlenum: Option(int, "Battle Number, 1 being latest, 50 max", required=True, default=1)):
	if battlenum >= 50 or battlenum < 0:
		await ctx.respond("Battlenum needs to be between 1-50!")
		return
	await s3Handler.cmdStatsBattle(ctx, battlenum)

@s3StatsCmds.command(name = 'multi', description = 'Get your Splatoon 3 multiplayer stats')
async def cmdS3Stats(ctx):
	await s3Handler.cmdStats(ctx)

#@s3StatsCmds.command(name = 'sr', description = 'Get your Splatoon 3 Salmon Run stats')
#async def cmdS3Stats(ctx):#
#	await s3Handler.cmdSRStats(ctx)

@s3StatsCmds.command(name = 'fit', description = 'Posts your current gear loadout')
async def cmdS3Fit(ctx):
	await s3Handler.cmdFit(ctx)

@owner.command(name='eval', description="Eval a code block (Owners only)", default_permission=False)
@commands.is_owner()
async def cmdEval(ctx):
	await ctx.send_modal(ownercmds.evalModal(ownerCmds, title="Eval"))

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
async def cmdVoicePlaySearch(ctx, source: Option(str, "Source to search", choices=[ 'youtube', 'soundcloud' ], required=True), search: Option(str, "Video to search for", required=True)):
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
	if not serverVoices[ctx.guild.id].vclient:
		await ctx.respond("Not connected to voice.", ephemeral=True)
	elif not serverVoices[ctx.guild.id].soundExists(sound):
		await ctx.respond(f"I don't know of a sound named '{sound}'.", ephemeral=True)
	else:
		await ctx.respond(f"Attempting to play: {sound}", ephemeral=True)
		await serverVoices[ctx.guild.id].playSound(sound)

@adminCmds.command(name='playlist', description="Adds a URL or the current video to my playlist for /voice play random")
async def cmdPlaylistAdd(ctx, url: Option(str, "URL to add to my playlist", required=True)):
	if ctx.guild == None:
		await ctx.respond("Can't DM me with this command.")
		return

	if await checkIfAdmin(ctx):
		await serverVoices[ctx.guild.id].addGuildList(ctx, [ url ])
	else:
		await ctx.respond("You aren't a guild administrator", ephemeral=True)

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

@client.event
async def on_ready():
	global client, mysqlHandler, serverUtils, serverVoices, splatInfo, configData, ownerCmds, pynso
	global nsoHandler, nsoTokens, head, dev, owners, commandParser, doneStartup, acHandler, stringCrypt
	global friendCodes, s3Handler

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
				break
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
		s3Handler = s3handler.S3Handler(client, mysqlHandler, nsoTokens, splat3info, configData)
		acHandler = achandler.acHandler(client, mysqlHandler, nsoTokens, configData)
		await mysqlHandler.startUp()
		mysqlSchema = mysqlschema.MysqlSchema(mysqlHandler)
		await mysqlSchema.update()
		friendCodes = friendcodes.FriendCodes(mysqlHandler, stringCrypt)
		await nsoTokens.migrate_tokens_if_needed()

		groups.Groups.setFriendObjects(client, mysqlHandler, friendCodes)
		await groups.Groups.startup()

		await nsoHandler.updateS2JSON()
		await nsoTokens.updateAppVersion()
		print('Done\n------')
		await client.change_presence(status=discord.Status.online, activity=discord.Game("Check /help for cmd info."))
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
	global serverUtils, mysqlHandler
	global nsoHandler, owners, commandParser, doneStartup, ownerCmds

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
		return
	else:
		theServer = message.guild.id

	parsed = await commandParser.parse(theServer, message.content)
	if parsed == None:
		return

	cmd = parsed['cmd']
	args = parsed['args']

	if cmd == 'eval' and message.author in owners:
		await ownerCmds.eval(context, args[0])
	elif cmd == 'getcons' and message.author in owners:
		await mysqlHandler.printCons(message)

	sys.stdout.flush()
	sys.stderr.flush()

#Setup
loadConfig()
if configData.get('output_to_log'):
	os.makedirs(f"{dirname}/logs", exist_ok=True)
	sys.stdout = open("{dirname}/logs/discordbot.log", 'a')
	sys.stderr = open("{dirname}/logs/discordbot.err", 'a')

ensureEncryptionKey()

if dev:
	client.add_application_command(owner)	

print('**********NEW SESSION**********')
print('Logging into discord')

client.add_application_command(voice)
client.add_application_command(adminCmds)
client.add_application_command(groupCmds)
client.add_application_command(fcCmds)
client.add_application_command(s2Cmds)
client.add_application_command(s3Cmds)
client.add_application_command(acnhCmds)

sys.stdout.flush()
sys.stderr.flush()
token = configData['token']
configData['token'] = ""

client.run(token)
