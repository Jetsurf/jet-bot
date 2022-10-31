import discord
import asyncio
import mysqlhandler
import os
import code
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class HelpDropDown(discord.ui.Select):

	def __init__(self, helpdir):
		helpopts = []
		self.helpdir = helpdir
		with os.scandir(helpdir) as iter:
			for dirent in iter:
				if dirent.is_file() and dirent.name.endswith('-slash.txt'):
					val = dirent.path  
					theFile = self.readHelpFile(val)		
					opt = discord.SelectOption(label=theFile['label'], description=theFile['desc'], value=val)
					helpopts.append(opt)
		
		super().__init__(
			placeholder="Help Menu",
			min_values=1,
			max_values=1,
			options=helpopts,
		)

	def readHelpFile(self, file):
		toReturn = {}
		toReturn["fileData"] = []

		with open(file, "r") as f:
			lines = f.readlines()

		for line in lines:
			if line.startswith('**'):
				toReturn['desc'] = line.replace('**', '')
			elif line.startswith('*'):
				toReturn['label'] = line.replace('*', '')
			else:
				toReturn['fileData'].append(line)
		return toReturn

	async def callback(self, interaction: discord.Interaction):
		theFile = self.readHelpFile(self.values[0])

		embed = discord.Embed(colour=0x2AE5B8)
		embed.title = theFile['label']
		name = theFile['desc']
		text = ""
		page = 2

		for line in theFile['fileData']:
			if len(text + line) > 1024:
				embed.add_field(name=name, value=text, inline=False)
				name = f"Page {str(page)}"
				page += 1
				text = line
			else:
				text += line

		embed.add_field(name=name, value=text, inline=False)

		await interaction.response.edit_message(view=self.view, embed=embed)

class HelpMenuView(discord.ui.View):
	def __init__(self, helpdir):
		super().__init__()
		self.add_item(HelpDropDown(helpdir))

class serverUtils():
	def __init__(self, client, mysqlhandler, serverconfig, helpfldr):
		self.sqlBroker = mysqlhandler
		self.helpfldr = helpfldr
		self.serverConfig = serverconfig
		self.client = client
		self.statusnum = 1
		self.scheduler = AsyncIOScheduler()
		self.scheduler.add_job(self.changeStatus, 'cron', minute='*/5', timezone='UTC') 
		self.scheduler.start()

	async def deleteFeed(self, ctx, bypass=False):
		cur = await self.sqlBroker.connect()
		stmt = "SELECT * FROM feeds WHERE serverid = %s AND channelid = %s"
		await cur.execute(stmt, (ctx.guild.id, ctx.channel.id,))
		chan = await cur.fetchone()

		#TODO: Need to improve this w/ confirmation to delete
		if chan != None:
			if bypass:
				stmt = "DELETE FROM feeds WHERE serverid = %s AND channelid = %s"
				await cur.execute(stmt, (ctx.guild.id, ctx.channel.id,))
				if cur.lastrowid != None:
					await self.sqlBroker.commit(cur)
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

		if chan != None and args[3] == True:
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
		status = [ "Check /help for cmd info.",
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

	#TODO: Readd cmd report. Old one is way to dumb, new data will help determine how it's presented

	async def contextIncrementCmd(self, ctx):
		try:
			cur = await self.sqlBroker.connect()
			stmt = "INSERT INTO commandcounts (serverid, command, count) VALUES (%s, %s, 1) ON DUPLICATE KEY UPDATE count = count + 1;"
			if ctx.guild == None:
				await cur.execute(stmt, ('0', ctx.command.qualified_name,))
			else:
				await cur.execute(stmt, (ctx.guild.id, ctx.command.qualified_name,))
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

