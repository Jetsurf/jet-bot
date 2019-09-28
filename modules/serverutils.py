import mysql.connector
from mysql.connector.cursor import MySQLCursorPrepared
import discord
import asyncio
import mysqlinfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class serverUtils():
	def __init__(self, client, mysqlinfo, serverconfig):
		self.mysqlinfo = mysqlinfo
		self.serverConfig = serverconfig
		self.client = client
		self.statusnum = 1
		self.valid_commands = [ "join", "play", "playrandom", "currentsong", "queue", "stop", "skip", "volume", "sounds", "currentmaps", "nextmaps", "weapon", "weapons",
							 "currentsr", "nextsr", "splatnetgear", "leavevoice", "storedm", "rank", "stats", "srstats", "order", "github", "help", "map", "maps", "battle", "battles"]
		self.theDB = mysql.connector.connect(host=self.mysqlinfo.host, user=self.mysqlinfo.user, password=self.mysqlinfo.pw, database=self.mysqlinfo.db)
		self.cursor = self.theDB.cursor(cursor_class=MySQLCursorPrepared)
		self.scheduler = AsyncIOScheduler()
		self.scheduler.add_job(self.changeStatus, 'cron', minute='*/5') 
		self.scheduler.start()

	async def changeStatus(self):
		status = [ "Use !help for directions!",
					"{} guilds for {} users",
					"\U0001F355 \U00002795 \U0001F34D \U000027A1 \U0001F4A9" ]

		if self.statusnum%2 == 0:
			await self.client.change_presence(status=discord.Status.online, activity=discord.Game(status[0]))
		elif self.statusnum%3 == 0:
			theStatus = status[1].format(len(self.client.guilds), len(set(self.client.get_all_members())))
			await self.client.change_presence(status=discord.Status.online, activity=discord.Activity(name=theStatus, type=discord.ActivityType(3)))
		elif self.statusnum%101 == 0:
			await self.client.change_presence(status=discord.Status.online, activity=discord.Game(status[2]))
			self.statusnum = 0

		self.statusnum += 1

	async def setAnnounceChannel(self, message, args):
		if len(args) < 2:
			await message.channel.send("No channel given, please specify a channel")
			return
		
		channelname = args[2].lower()
		channelid = None
		for channel in message.guild.channels:
			if channel.name.lower() == channelname and channel.type == discord.ChannelType.text:
				channelid = channel.id

		if channelid == None:
			await message.channel.send("Could not find a channel with name: " + channelname)
		else:
			self.serverConfig.setConfigValue(message.guild.id, 'announcement.channelid', channelid)
			await message.channel.send("Set announcement channel to: " + channelname)

	def getAnnounceChannel(self, serverid):
		channelid = self.serverConfig.getConfigValue(serverid, 'announcement.channelid')
		if channelid != None:
			server = discord.utils.get(self.client.guilds, id=serverid)
			return discord.utils.get(server.channels, id=channelid)
		else:
			return None

	async def doAnnouncement(self, message):
		announcemsg = message.content.split(None, 1)[1]
		print("Sending announcement: " + announcemsg)

		for guild in self.client.guilds:
			channel = self.getAnnounceChannel(guild.id)
			if channel == None:
				continue
			else:
				await channel.send("ANNOUNCEMENT: " + announcemsg)

	async def stopAnnouncements(self, message):
		self.serverConfig.removeConfigValue(message.guild.id, "announcement.channelid")
		await message.channel.send("Your guild is now unsubscribed from receiving announcements")

	def checkDM(self, clientid, serverid):
		stmt = "SELECT COUNT(*) FROM dms WHERE serverid = %s AND clientid = %s"
		self.cursor.execute(stmt, (serverid, clientid,))
		count = self.cursor.fetchone()
		self.theDB.commit()
		if count[0] > 0:
			return True
		else:
			return False

	async def print_help(self, message, commands, prefix):
		embed = discord.Embed(colour=0x2AE5B8)
		embed.title = "Here is how to control me!"
		titlenum = 0
		theString = ''
		title = ''
		with open(commands, 'r') as f:
			for line in f:
				if '*' in line and titlenum > 0:
					embed.add_field(name=title, value=theString, inline=False)
					title = line[1:]
					theString = ''
					titlenum += 1
				elif titlenum == 0:
					titlenum += 1
					title = line[1:]
				else:
					if line.startswith('!'):
						line = line.replace('!', prefix)
						theString = theString + "**" + line.replace(":", ":**")
					else:
						theString = theString + line
			embed.add_field(name=title, value=theString, inline=False)	
			embed.set_footer(text="If you want something added or want to report a bug/error, tell jetsurf#8514...")
		await message.channel.send(embed=embed)

	async def report_cmd_totals(self, message):
		embed = discord.Embed(colour=0x00FFF3)
		embed.title = "Command Totals"
		
		for cmd in self.valid_commands:
			stmt = "SELECT IFNULL(SUM(count), 0) FROM commandcounts WHERE (command = %s)"
			self.cursor.execute(stmt, (cmd,))
			count = self.cursor.fetchone()
			embed.add_field(name=cmd, value=str(count[0].decode()), inline=True)
		await message.channel.send(embed=embed)

	def increment_cmd(self, message, cmd):
		if cmd not in self.valid_commands:
			return

		stmt = "INSERT INTO commandcounts (serverid, command, count) VALUES (%s, %s, 1) ON DUPLICATE KEY UPDATE count = count + 1;"
		self.cursor.execute(stmt, (message.guild.id, cmd,))
		self.theDB.commit()

	async def addDM(self, message):
		if self.checkDM(message.author.id, message.guild.id):
			await message.channel.send("You are already in my list of people to DM")
			return

		stmt = "INSERT INTO dms(serverid, clientid) values(%s, %s)"
		self.cursor.execute(stmt, (message.guild.id, message.author.id,))
		if self.cursor.lastrowid != None:
			self.theDB.commit()
			await message.channel.send("Added " + message.author.name + " to my DM list!")
		else:
			self.theDB.rollback()
			await message.channel.send("Something went wrong!")

	async def removeDM(self, message):
		if not self.checkDM(message.author.id, message.guild.id):
			await message.channel.send("You aren't in my list of people to DM")
			return

		stmt = "DELETE FROM dms WHERE serverid = %s AND clientid = %s"
		self.cursor.execute(stmt, (message.guild.id, str(message.author.id),))
		if self.cursor.lastrowid != None:
			self.theDB.commit()
			await message.channel.send("Removed " + message.author.name + " from my DM list!")
		else:
			self.theDB.rollback()
			await message.channel.send("Something went wrong!")
