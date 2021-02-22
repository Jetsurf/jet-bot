#!/usr/bin/python3

import sys
sys.path.append('./modules')
#Base Stuffs
import discord, asyncio, subprocess, json, time
#DBL Posting
import urllib, urllib.request, requests, pymysql
#Our Classes
import nsotoken, commandparser, serverconfig, splatinfo
import vserver, mysqlhandler, serverutils, nsohandler, achandler
#Eval
import traceback, textwrap, io, signal
from contextlib import redirect_stdout
from subprocess import call

splatInfo = splatinfo.SplatInfo()
intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)
commandParser = None
serverConfig = None
mysqlHandler = None
nsoHandler = None
nsoTokens = None
serverVoices = {}
serverUtils = None
acHandler = None
doneStartup = False
token = ''
owners = []
dev = 1
soundsDir = ''
helpfldr = ''
head = {}
url = ''

def loadConfig():
	global token, soundsDir, helpfldr, mysqlHandler, dev, head, url
	try:
		with open('./config/discordbot.json', 'r') as json_config:
			configData = json.load(json_config)

		token = configData['token']
		soundsDir = configData['soundsdir']
		helpfldr = configData['help']
		try:
			dbid = configData['discordbotid']
			dbtoken = configData['discordbottok']
			head = { 'Authorization': dbtoken }
			url = 'https://top.gg/api/bots/' + str(dbid) + '/stats'
			dev = 0
		except:
			print('No ID/Token for discordbots.org, skipping')

		mysqlHandler = mysqlhandler.mysqlHandler(configData['mysql_host'], configData['mysql_user'], configData['mysql_pw'], configData['mysql_db'])

		print('Config Loaded')
	except Exception as e:
		print('Failed to load config: ' + str(e))
		quit(1)
							
@client.event
async def on_ready():
	global client, soundsDir, mysqlHandler, serverUtils, serverVoices, splatInfo, helpfldr
	global nsoHandler, nsoTokens, head, url, dev, owners, commandParser, doneStartup, acHandler

	if not doneStartup:
		print('Logged in as,', client.user.name, client.user.id)
		#Get owners from Discord team api
		print("Loading owners...")
		theapp = await client.application_info()
		ownerids = [x.id for x in theapp.team.members]
		for mem in client.get_all_members():
			if mem.id in ownerids:
				owners.append(mem)
			if len(owners) == len(ownerids):
				break;
	else:
		print('RECONNECT TO DISCORD')

	if dev == 0:
		print('I am in ' + str(len(client.guilds)) + ' servers, posting to discordbots.org')
		body = { 'server_count' : len(client.guilds) }
		requests.post(url, headers=head, json=body)
	else:	
		print('I am in ' + str(len(client.guilds)) + ' servers')

	if not doneStartup:
		print("Doing Startup...")
		for server in client.guilds:
			#Don't recreate serverVoices on reconnect
			if server.id not in serverVoices:
				serverVoices[server.id] = vserver.voiceServer(client, mysqlHandler, server.id, soundsDir)

		serverConfig = serverconfig.ServerConfig(mysqlHandler)
		commandParser = commandparser.CommandParser(serverConfig, client.user.id)
		serverUtils = serverutils.serverUtils(client, mysqlHandler, serverConfig, helpfldr)
		nsoTokens = nsotoken.Nsotoken(client, mysqlHandler)
		nsoHandler = nsohandler.nsoHandler(client, mysqlHandler, nsoTokens, splatInfo)
		acHandler = achandler.acHandler(client, mysqlHandler, nsoTokens)
		await nsoHandler.updateS2JSON()
		await mysqlHandler.startUp()
		print('Done\n------')
		await client.change_presence(status=discord.Status.online, activity=discord.Game("Use !help for directions!"))
	else:
		print('Finished reconnect')
	doneStartup = True

	print("Starting Chunking")

	for server in client.guilds:
		await server.chunk()

	print("Finished Chunking")

	sys.stdout.flush()
	
@client.event
async def on_member_remove(member):
	global serverUtils, doneStartup

	if not doneStartup:
		return

	gid = member.guild.id
	for mem in await serverUtils.getAllDM(gid):
		memid = mem[0]
		memobj = client.get_guild(gid).get_member(memid)
		if memobj.guild_permissions.administrator:
			await memobj.send(member.name + " left " + member.guild.name)
			
@client.event
async def on_guild_join(server):
	global serverVoices, head, url, dev, owners, mysqlHandler
	print("I joined server: " + server.name)
	serverVoices[server.id] = vserver.voiceServer(client, mysqlHandler, server.id, soundsDir)

	if dev == 0:
		print('I am now in ' + str(len(client.guilds)) + ' servers, posting to discordbots.org')
		body = { 'server_count' : len(client.guilds) }
		r = requests.post(url, headers=head, json=body)
	else:
		print('I am now in ' + str(len(client.guilds)) + ' servers')

	for mem in owners:
		await mem.send("I joined server: " + server.name + " with " + str(len(server.members)) + " members - I am now in " + str(len(client.guilds)) + " servers with " + str(len(set(client.get_all_members()))) + " total members")
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

	for mem in owners:
		await mem.send("I left server: " + server.name + " ID: " + str(server.id) + " - I am now in " + str(len(client.guilds)) + " servers with " + str(len(set(client.get_all_members()))) + " total members")
	sys.stdout.flush()

@client.event
async def on_voice_state_update(mem, before, after):
	global client, serverVoices, mysqlHandler, soundsDir

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
		print("Disconnect, recreating vserver for " + str(before.channel.guild.id))
		try:
			if serverVoices[server].vclient == None:
				await serverVoices[server].vclient.disconnect()
		except Exception as e:
			print(traceback.format_exc())
			print("Issue in voice disconnect?? Recreating anyway")

		serverVoices[server] = vserver.voiceServer(client, mysqlHandler, server, soundsDir)
		sys.stdout.flush()

@client.event
async def on_error(event, *args, **kwargs):
	global mysqlHandler, serverVoices
	exc = sys.exc_info()
	if exc[0] is discord.errors.Forbidden:
		return
	elif exc[0] is pymysql.err.OperationalError:
		##THIS DOES NOT WORK
		cur = args.get('cur')
		mysqlHandler.close(cur)
		print("MYSQL: Disconnect from server, terminating connection", file=sys.stderr)
	else:
		raise exc[1]

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
			code = message.content.replace('`', '').replace(prefix + 'eval ', '')
			theeval = 'async def func(): \n' + textwrap.indent(code, ' ')
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

	if message.guild == None:
		if message.author in owners:
			if '!servers' in message.content:
				numServers = str(len(client.guilds))
				serverNames = ""
				for server in client.guilds:
					serverNames = serverNames + str(server.name + '\n')
				await channel.send("I am in: " + str(numServers) + " servers\n" + serverNames)
			elif '!restart' in message.content:
				await channel.send("Going to restart!")
				await mysqlHandler.close_pool()
				await client.close()
				sys.stderr.flush()
				sys.stdout.flush()
				sys.exit(0)
				print("KEY CHECK: " + str(keys))
			elif '!cmdreport' in message.content:
				await serverUtils.report_cmd_totals(message)
			elif '!nsojson' in command:
				await nsoHandler.getRawJSON(message)
			elif '!announce' in command:
				await serverUtils.doAnnouncement(message)
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
		await message.channel.send("The command prefix for this server is: " + prefix)
	elif message.content.startswith('!help') and prefix not in '!':
		await serverUtils.print_help(message, prefix)
	elif ('pizza' in command and 'pineapple' in command) or ('\U0001F355' in message.content and '\U0001F34D' in message.content):
		await channel.send('Don\'t ever think pineapple and pizza go together ' + message.author.name + '!!!')		

	parsed = await commandParser.parse(theServer, message.content)
	if parsed == None:
		return

	cmd = parsed['cmd']
	args = parsed['args']

	#Don't just fail if command count can't be incremented
	try:
		await serverUtils.increment_cmd(message, cmd)
	except:
		print("Failed to increment command... issue with MySQL?")

	if cmd == 'eval':
		await doEval(message)
	elif cmd == 'getcons' and message.author in owners:
		await mysqlHandler.printCons(message)
	elif cmd == 'storejson' and message.author in owners:
		await nsoHandler.getStoreJSON(message)
	elif cmd == 'admin':
		if message.author.guild_permissions.administrator:
			if len(args) == 0:
				await message.channel.send("Options for admin commands are playlist, blacklist, dm, prefix")
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
					await serverUtils.addDM(message)
				elif subcommand2 == 'remove':
					await serverUtils.removeDM(message)
			elif subcommand == "announcement":
				subcommand2 = args[1].lower()
				if subcommand2 == 'set':
					await serverUtils.setAnnounceChannel(message, args)
				elif subcommand2 == 'get':
					channel = await serverUtils.getAnnounceChannel(message.guild.id)
					if channel == None:
						await message.channel.send("No channel is set to receive announcements")
					else:
						await message.channel.send("Current announcement channel is: " + channel.name)
				elif subcommand2 == 'stop':
					await serverUtils.stopAnnouncements(message)
				else:
					await message.channel.send("Usage: set CHANNEL, get, or stop")
			elif subcommand == 'prefix':
				if (len(args) == 1):
					await channel.send("Current command prefix is: " + prefix)
				elif (len(args) != 2) or (len(args[1]) < 0) or (len(args[1]) > 2):
					await channel.send("Usage: ```admin prefix <char>``` where *char* is one or two characters")
				else:
					await commandParser.setPrefix(theServer, args[1])
					await channel.send("New command prefix is: " + await commandParser.getPrefix(theServer))
			elif subcommand == 'feed':
				if len(args) == 1:
					await serverUtils.createFeed(message)
				elif 'delete' in args[1].lower():
					await serverUtils.deleteFeed(message)
		else:
			await channel.send(message.author.name + " you are not an admin... :cop:")
	elif cmd == 'alive':
		await channel.send("Hey " + message.author.name + ", I'm alive so shut up! :japanese_goblin:")
	elif cmd == 'rank':
		await nsoHandler.getRanks(message)
	elif cmd == 'order':
		await nsoHandler.orderGearCommand(message, args=args)
	elif cmd == 'stats':
		await nsoHandler.getStats(message)
	elif cmd == 'srstats':
		await nsoHandler.getSRStats(message)
	elif cmd == 'storedm':
		await nsoHandler.addStoreDM(message, args)
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
		await channel.send("Current Sounds:\n```" + theSounds + "```")
	elif cmd == 'join':
		if len(args) > 0:
			await serverVoices[theServer].joinVoiceChannel(message, args)
		else:
			await serverVoices[theServer].joinVoiceChannel(message, args)
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
	elif (cmd == 'map') or (cmd == 'maps'):
		await nsoHandler.cmdMaps(message, args)
	elif (cmd == 'weapon') or (cmd == 'weapons'):
		await nsoHandler.cmdWeaps(message, args)
	elif (cmd == 'battle') or (cmd == 'battles'):
		await nsoHandler.cmdBattles(message, args)
	elif serverVoices[theServer].vclient is not None:
		if cmd == 'currentsong':
			if serverVoices[theServer].source is not None:
				await channel.send('Currently Playing Video: ' + serverVoices[theServer].source.yturl)
			else:
				await channel.send('I\'m not playing anything.')
		elif cmd == 'leavevoice':
			await serverVoices[theServer].vclient.disconnect()
			serverVoices[theServer].vclient = None
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
				await channel.send("Setting Volume to " + str(vol) + "%")
				serverVoices[theServer].source.volume = float(int(vol) / 100)
		elif cmd == 'queue':
			await serverVoices[theServer].printQueue(message)
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

sys.stdout.flush()
sys.stderr.flush()
client.chunk_guilds_at_startup = False
client.run(token)
