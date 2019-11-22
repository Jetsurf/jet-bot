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
			'user_sn'	:		[ "rank", "stats", "srstats", "order" ],
			'hybrid_sn' : 		[ "weapon", "weapons","map", "maps", "battle", "battles" ],
			'voice' 	:	 	[ "join", "play", "playrandom", "currentsong", "queue", "stop", "skip", "volume", "sounds", "leavevoice" ]
		}
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
			await self.serverConfig.setConfigValue(message.guild.id, 'announcement.channelid', channelid)
			await message.channel.send("Set announcement channel to: " + channelname)

	async def getAnnounceChannel(self, serverid):
		channelid = await self.serverConfig.getConfigValue(serverid, 'announcement.channelid')
		if channelid != None:
			server = discord.utils.get(self.client.guilds, id=serverid)
			return discord.utils.get(server.channels, id=channelid)
		else:
			return None

	async def doAnnouncement(self, message):
		announcemsg = message.content.split(None, 1)[1]
		print("Sending announcement: " + announcemsg)

		for guild in self.client.guilds:
			channel = await self.getAnnounceChannel(guild.id)
			if channel == None:
				continue
			else:
				await channel.send("ANNOUNCEMENT: " + announcemsg)

	async def stopAnnouncements(self, message):
		await self.serverConfig.removeConfigValue(message.guild.id, "announcement.channelid")
		await message.channel.send("Your guild is now unsubscribed from receiving announcements")

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
			embed.set_footer(text="If you want something added or want to report a bug/error, run " + prefix + "support")
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
				theString = theString + "**" + cmd + "** : " + str(count[0]) + "\n"
			embed.add_field(name="**" + cmd_set + "**", value=theString, inline=True)
		await self.sqlBroker.close(cur)
		await message.channel.send(embed=embed)

	async def increment_cmd(self, message, cmd):
		if cmd not in self.valid_commands['base'] and cmd not in self.valid_commands['base_sn'] and cmd not in self.valid_commands['user_sn'] and cmd not in self.valid_commands['hybrid_sn'] and cmd not in self.valid_commands['voice']:
			return

		cur = await self.sqlBroker.connect()
		stmt = "INSERT INTO commandcounts (serverid, command, count) VALUES (%s, %s, 1) ON DUPLICATE KEY UPDATE count = count + 1;"
		await cur.execute(stmt, (message.guild.id, cmd,))
		await self.sqlBroker.commit(cur)

	async def addDM(self, message):
		if await self.checkDM(message.author.id, message.guild.id):
			await message.channel.send("You are already in my list of people to DM")
			return

		cur = await self.sqlBroker.connect()
		stmt = "INSERT INTO dms(serverid, clientid) values(%s, %s)"
		await cur.execute(stmt, (message.guild.id, message.author.id,))
		if cur.lastrowid != None:
			await self.sqlBroker.commit(cur)
			await message.channel.send("Added " + message.author.name + " to my DM list!")
		else:
			await self.sqlBroker.rollback(cur)
			await message.channel.send("Something went wrong!")

	async def removeDM(self, message):
		if not await self.checkDM(message.author.id, message.guild.id):
			await message.channel.send("You aren't in my list of people to DM")
			return

		cur = await self.sqlBroker.connect()
		stmt = "DELETE FROM dms WHERE serverid = %s AND clientid = %s"
		await cur.execute(stmt, (message.guild.id, str(message.author.id),))
		if self.cursor.lastrowid != None:
			await self.sqlBroker.commit(cur)
			await message.channel.send("Removed " + message.author.name + " from my DM list!")
		else:
			await self.sqlBroker.rollback(cur)
			await message.channel.send("Something went wrong!")
