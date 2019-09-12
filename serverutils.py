import mysql.connector
from mysql.connector.cursor import MySQLCursorPrepared
import discord
import asyncio
import mysqlinfo

class serverUtils():
	def __init__(self, mysqlinfo):
		self.mysqlinfo = mysqlinfo
		self.valid_commands = [ "join", "play", "playrandom", "currentsong", "queue", "stop", "skip", "volume", "sounds", "currentmaps", "nextmaps",
							 "currentsr", "nextsr", "splatnetgear", "leavevoice", "storedm", "rank", "stats", "srstats", "order", "github", "help" ]
		self.theDB = mysql.connector.connect(host=self.mysqlinfo.host, user=self.mysqlinfo.user, password=self.mysqlinfo.pw, database=self.mysqlinfo.db)
		self.cursor = self.theDB.cursor(cursor_class=MySQLCursorPrepared)

	def checkDM(self, clientid, serverid):
		stmt = "SELECT COUNT(*) FROM dms WHERE serverid = %s AND clientid = %s"
		self.cursor.execute(stmt, (serverid, clientid,))
		count = self.cursor.fetchone()

		if count[0] > 0:
			return True
		else:
			return False

	async def report_cmd_totals(self, message):
		embed = discord.Embed(colour=0x00FFF3)
		embed.title = "Command Totals"
		print("TBD")

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
			await message.channel.send("Something went wrong!")