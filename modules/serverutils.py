import discord
import asyncio
import mysqlhandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class serverUtils():
	def __init__(self, client, mysqlhandler, serverconfig, helpfldr):
		self.sqlBroker = mysqlhandler
		self.helpfldr = helpfldr
		self.serverConfig = serverconfig
		self.client = client
		self.statusnum = 1
		self.valid_commands = {
			'base'		: 		[ "help", "github", "support" ],
			'base_sn' 	: 		[ "currentmaps", "nextmaps", "nextsr", "currentsr", "splatnetgear", "storedm" ],
			'user_sn'	:		[ "rank", "stats", "srstats", "order", "passport" ],
			'hybrid_sn' : 		[ "weapon", "weapons","map", "maps", "battle", "battles" ],
			'voice' 	:	 	[ "join", "play", "playrandom", "currentsong", "queue", "stop", "skip", "volume", "sounds", "leavevoice" ]
		}
		self.scheduler = AsyncIOScheduler()
		self.scheduler.add_job(self.changeStatus, 'cron', minute='*/5') 
		self.scheduler.start()

	async def deleteFeed(self, ctx, is_slash=False, bypass=False):
		cur = await self.sqlBroker.connect()
		stmt = "SELECT * FROM feeds WHERE serverid = %s AND channelid = %s"
		await cur.execute(stmt, (ctx.guild.id, ctx.channel.id,))
		chan = await cur.fetchone()
		mapflag, srflag, gearflag = False, False, False

		def check(m):
			return m.author == ctx.user and m.channel == ctx.channel

		if chan != None:
			if bypass == False:
				await ctx.respond("Delete feed for this channel (yes/no)? ")

				createfeed = await self.client.wait_for('message', check=check)
				if 'yes' in createfeed.content.lower():
					saidYes = True
				else:
					saidYes = False
			else:
				saidYes = False

			if saidYes or bypass:
				stmt = "DELETE FROM feeds WHERE serverid = %s AND channelid = %s"
				await cur.execute(stmt, (ctx.guild.id, ctx.channel.id,))
				if cur.lastrowid != None:
					await self.sqlBroker.commit(cur)
					if is_slash:
						await ctx.respond("Ok, deleted feed.")
					return True
				else:
					await self.sqlBroker.rollback(cur)
					await ctx.respond("Error in deleting feed.")
					return False
		else:
			await ctx.respond("No feed setup for this channel.")
			return False

	async def createFeed(self, ctx, args=None):
		cur = await self.sqlBroker.connect()
		stmt = "SELECT * FROM feeds WHERE serverid = %s AND channelid = %s"
		await cur.execute(stmt, (ctx.guild.id, ctx.channel.id,))
		chan = await cur.fetchone()
		mapflag, srflag, gearflag = False, False, False

		def check(m):
			return m.author == ctx.user and m.channel == ctx.channel
		if args == None:
			if chan != None:
				await ctx.respond("Feed already setup for this channel, create a new one? ")

				createfeed = await self.client.wait_for('message', check=check)

				if 'yes' in createfeed.content.lower():
					stmt = "DELETE FROM feeds WHERE serverid = %s AND channelid = %s"
					await cur.execute(stmt, (message.guild.id, message.channel.id,))
					if cur.lastrowid != None:
						await ctx.respond("Ok, creating feed. Would you like the feed notification to include Map rotations (yes/no)?")
					else:
						await ctx.respond("Error in setting up create feed.")
						return False
				else:
					await ctx.respond("Ok, canceling.")
					return False
			else:
				await ctx.respond("No feed is setup for this channel. Would you like to create one (yes/no)?")

				feedresp = await self.client.wait_for('message', check=check)

				if 'yes' in feedresp.content.lower():
					await ctx.respond("Ok, creating feed. Would you like the feed notification to include Map rotations (yes/no)?")
				else:
					await ctx.respond("Ok, canceling.")
					return False

			mapresp = await self.client.wait_for('message', check=check)

			if 'yes' in mapresp.content.lower():
				await ctx.respond("Ok, adding Map rotations to the feed. Would you like the feed notification to include Salmon Run rotations (yes/no)?")
				mapflag = True
			else:
				await ctx.respond("Ok, not adding Map rotations to the feed. Would you like the feed notification to include Salmon Run rotations (yes/no)?")

			srresp = await self.client.wait_for('message', check=check)

			if 'yes' in srresp.content.lower():
				await ctx.respond("Ok, adding Salmon Run rotations to the feed. Would you like the feed notification to include Gear rotations (yes/no)?")
				srflag = True
			else:
				await ctx.respond("Ok, not adding Salmon Run rotations to the feed. Would you like the feed notifications to include Gear rotations (yes/no)?")

			gearresp = await self.client.wait_for('message', check=check)

			if 'yes' in gearresp.content.lower():
				await ctx.respond("Ok, adding Gear rotations to the feed. ")
				gearflag = True
			else:
				await ctx.respond("Ok, not adding Gear rotations to the feed.")
		elif chan != None and args[3] == True:
			mapflag = args[0]
			srflag = args[1]
			gearflag = args[2]
			await self.deleteFeed(ctx, bypass=True)
		elif chan == None:
			mapflag = args[0]
			srflag = args[1]
			gearflag = args[2]
		else:
			await ctx.respond("Feed already created for this channel, please delete it or set recreate to True")
			return

		stmt = "INSERT INTO feeds (serverid, channelid, maps, sr, gear) VALUES(%s, %s, %s, %s, %s)"
		feed = (str(ctx.guild.id), str(ctx.channel.id), int(mapflag == True), int(srflag == True), int(gearflag == True),)

		await cur.execute(stmt, feed)
		if cur.lastrowid != None:
			await self.sqlBroker.commit(cur)
			await ctx.respond("Feed created! Feed will start when the next rotation happens.")
			return True
		else:
			await self.sqlBroker.rollback(cur)
			await ctx.respond("Feed failed to create.")
			return False

	async def changeStatus(self):
		status = [ "Check Slash Commands!",
					"{} guilds",
					"\U0001F355 \U00002795 \U0001F34D \U000027A1 \U0001F4A9" ]

		if self.statusnum%2 == 0:
			await self.client.change_presence(status=discord.Status.online, activity=discord.Game(status[0]))
		elif self.statusnum%3 == 0:
			theStatus = status[1].format(len(self.client.guilds))
			await self.client.change_presence(status=discord.Status.online, activity=discord.Activity(name=theStatus, type=discord.ActivityType(3)))
		elif self.statusnum%101 == 0:
			await self.client.change_presence(status=discord.Status.online, activity=discord.Game(status[2]))
			self.statusnum = 0

		self.statusnum += 1

	async def setAnnounceChannel(self, ctx, args):
		if not isinstance( args, (discord.TextChannel, tuple)) and len(args) < 2:
			await ctx.respond("No channel given, please specify a channel")
			return

		if not isinstance( args, (discord.TextChannel, tuple)):
			channelname = args[2].lower()
			channelid = None

			for channel in ctx.guild.channels:
				if channel.name.lower() == channelname and channel.type == discord.ChannelType.text:
					channelid = channel.id
		else:
			channelid = args.id
			channelname = args.name

		if channelid == None:
			await ctx.respond(f"Could not find a channel with name: {channelname}")
		else:
			await self.serverConfig.setConfigValue(ctx.guild.id, 'announcement.channelid', channelid)
			await ctx.respond(f"Set announcement channel to: {channelname}")

	async def getAnnounceChannel(self, serverid):
		channelid = await self.serverConfig.getConfigValue(serverid, 'announcement.channelid')
		if channelid != None:
			server = discord.utils.get(self.client.guilds, id=serverid)
			return discord.utils.get(server.channels, id=channelid)
		else:
			return None

	async def doAnnouncement(self, message):
		announcemsg = message.content.split(None, 1)[1]
		print(f"Sending announcement: {announcemsg}")

		for guild in self.client.guilds:
			channel = await self.getAnnounceChannel(guild.id)
			if channel == None:
				continue
			else:
				try:
					await channel.send(f"ANNOUNCEMENT: {announcemsg}")
				except discord.Forbidden:
					print(f"Forbidden on announcement: {guild.id} : removing announcement channel from config")
					await self.serverConfig.removeConfigValue(guild.id, 'announcement.channelid')

	async def stopAnnouncements(self, ctx):
		await self.serverConfig.removeConfigValue(ctx.guild.id, "announcement.channelid")
		await ctx.respond("Your guild is now unsubscribed from receiving announcements")

	async def getAllDM(self, serverid):
		cur = await self.sqlBroker.connect()
		stmt = "SELECT clientid FROM dms WHERE serverid = %s"
		await cur.execute(stmt, (serverid,))
		mems = await cur.fetchall()
		await self.sqlBroker.close(cur)
		return mems

	async def checkDM(self, clientid, serverid):
		cur = await self.sqlBroker.connect()
		stmt = "SELECT COUNT(*) FROM dms WHERE serverid = %s AND clientid = %s"
		await cur.execute(stmt, (serverid, clientid,))
		count = await cur.fetchone()
		await self.sqlBroker.close(cur)
		if count[0] > 0:
			return True
		else:
			return False

	async def print_help(self, message, prefix):
		embed = discord.Embed(colour=0x2AE5B8)

		if 'admin' in message.content:
			file = self.helpfldr + '/admin.txt'
		elif 'generalsn' in message.content:
			file = self.helpfldr + '/basesplatnet.txt'
		elif 'usersn' in message.content:
			file = self.helpfldr + '/usersplatnet.txt'
		elif 'voice' in message.content:
			file = self.helpfldr + '/voice.txt'
		elif 'ac' in message.content:
			file = self.helpfldr + '/ac.txt'
		else:
			file = self.helpfldr + '/base.txt'

		theString = ''
		title = ''
		with open(file, 'r') as f:
			for line in f:
				if '*' in line:
					embed.title = line.replace('*', '')
				else:
					if line.startswith('!'):
						line = line.replace('!', prefix)
						theString = theString + "**" + line.replace(":", ":**")
					else:
						theString = theString + line
			embed.add_field(name='Commands', value=theString, inline=False)	
			embed.set_footer(text="If you want something added or want to report a bug/error, run /support")
		await message.channel.send(embed=embed)

	async def report_cmd_totals(self, message):
		embed = discord.Embed(colour=0x00FFF3)
		embed.title = "Command Totals"
		cur = await self.sqlBroker.connect()

		for cmd_set in self.valid_commands:
			theString = ""
			for cmd in self.valid_commands[cmd_set]:
				stmt = "SELECT IFNULL(SUM(count), 0) FROM commandcounts WHERE (command = %s)"
				await cur.execute(stmt, (cmd,))
				count = await cur.fetchone()
				theString = f"{theString} **{cmd}** : {str(count[0])}\n"
			embed.add_field(name=f"**{cmd_set}**", value=theString, inline=True)
		await self.sqlBroker.close(cur)
		await message.channel.send(embed=embed)

	async def increment_cmd(self, ctx, cmd):
		#Needs a try catch to prevent failures if mysql is acting up to allow slash commands to not have repetitive code for handling the exception there
		#This will also catch DM'ed slash commands trying to be incremented
		try:
			if cmd not in self.valid_commands['base'] and cmd not in self.valid_commands['base_sn'] and cmd not in self.valid_commands['user_sn'] and cmd not in self.valid_commands['hybrid_sn'] and cmd not in self.valid_commands['voice']:
				return

			cur = await self.sqlBroker.connect()
			stmt = "INSERT INTO commandcounts (serverid, command, count) VALUES (%s, %s, 1) ON DUPLICATE KEY UPDATE count = count + 1;"
			if ctx.guild == None:
				await cur.execute(stmt, ('0', cmd,))
			else:
				await cur.execute(stmt, (ctx.guild.id, cmd,))
			await self.sqlBroker.commit(cur)
		except:
			pass

	async def addDM(self, ctx):
		if await self.checkDM(ctx.user.id, ctx.guild.id):
			await ctx.respond("You are already in my list of people to DM")
			return

		cur = await self.sqlBroker.connect()
		stmt = "INSERT INTO dms(serverid, clientid) values(%s, %s)"
		await cur.execute(stmt, (ctx.guild.id, ctx.user.id,))
		if cur.lastrowid != None:
			await self.sqlBroker.commit(cur)
			await ctx.respond(f"Added {ctx.user.name} to my DM list!")
		else:
			await self.sqlBroker.rollback(cur)
			await ctx.respond("Something went wrong!")

	async def removeDM(self, ctx):
		if not await self.checkDM(ctx.user.id, ctx.guild.id):
			await ctx.respond("You aren't in my list of people to DM")
			return

		cur = await self.sqlBroker.connect()
		stmt = "DELETE FROM dms WHERE serverid = %s AND clientid = %s"
		await cur.execute(stmt, (ctx.guild.id, str(ctx.user.id),))
		if cur.lastrowid != None:
			await self.sqlBroker.commit(cur)
			await ctx.respond(f"Removed {ctx.user.name} from my DM list!")
		else:
			await self.sqlBroker.rollback(cur)
			await ctx.respond("Something went wrong!")

	async def trim_db_from_leave(self, serverid):
		cur = await self.sqlBroker.connect()
		stmt = "DELETE FROM storedms WHERE serverid = %s"
		input = (serverid,)
		await cur.execute(stmt, input)

		stmt = "DELETE FROM playlist WHERE serverid = %s"
		await cur.execute(stmt, input)

		stmt = "DELETE FROM server_config WHERE serverid = %s"
		await cur.execute(stmt, input)

		stmt = "DELETE FROM feeds WHERE serverid = %s"
		await cur.execute(stmt, input)

		stmt = "DELETE FROM dms WHERE serverid = %s"
		await cur.execute(stmt, input)
		if cur.lastrowid != None:
			await self.sqlBroker.commit(cur)
			print(f"Cleaned up DB on server {str(serverid)}")
		else:
			await self.sqlBroker.rollback(cur)
			print(f"Error on DB cleanup for server {str(serverid)}")

