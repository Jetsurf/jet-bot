import mysql.connector
from mysql.connector.cursor import MySQLCursorPrepared
import discord
import asyncio
import mysqlinfo

class serverUtils():
	def __init__(self, client, id, mysqlinfo):
		self.client = client
		self.mysqlinfo = mysqlinfo
		self.server = id

	def connect(self):
		theDB = mysql.connector.connect(host=self.mysqlinfo.host, user=self.mysqlinfo.user, password=self.mysqlinfo.pw, database=self.mysqlinfo.db)
		cursor = theDB.cursor(cursor_class=MySQLCursorPrepared)
		return theDB, cursor

	def disconnect(self, db, cursor):
		cursor.close()
		db.close()

	def checkDM(self, clientid):
		theDB, cursor = self.connect()
		stmt = "SELECT COUNT(*) FROM dms WHERE serverid = %s AND clientid = %s"
		cursor.execute(stmt, (self.server, str(clientid),))
		count = cursor.fetchone()
		self.disconnect(theDB, cursor)

		if count[0] > 0:
			return True
		else:
			return False

	async def report_cmd_totals(self, message):
		embed = discord.Embed(colour=0x00FFF3)
		embed.title = "Command Totals"
		print("TBD")

	def increment_cmd(self, cmd):
		valid_commands = [ "join", "play", "playrandom", "currentsong", "queue", "stop", "skip", "volume", "sounds", "currentmaps", "nextmaps",
							 "currentsr", "nextsr", "splatnetgear", "leavevoice", "storedm", "rank", "stats", "srstats", "order", "github", "help" ]

		if cmd not in valid_commands:
			return

		theDB, cursor = self.connect()
		stmt = "INSERT INTO commandcounts (serverid, command, count) VALUES (%s, %s, 1) ON DUPLICATE KEY UPDATE count = count + 1;"
		cursor.execute(stmt, (self.server, cmd))
		theDB.commit()
		self.disconnect(theDB, cursor)

	async def addDM(self, message):
		theDB, cursor = self.connect()
		if self.checkDM(message.author.id):
			await message.channel.send("You are already in my list of people to DM")
			return
		stmt = "INSERT INTO dms(serverid, clientid) values(%s, %s)"
		cursor.execute(stmt, (self.server, str(message.author.id),))
		if cursor.lastrowid != None:
			theDB.commit()
			await message.channel.send("Added " + message.author.name + " to my DM list!")
		else:
			await message.channel.send("Something went wrong!")
		self.disconnect(theDB, cursor)

	async def removeDM(self, message):
		theDB, cursor = self.connect()

		if not self.checkDM(message.author.id):
			await message.channel.send("You aren't in my list of people to DM")
			return

		stmt = "DELETE FROM dms WHERE serverid = %s AND clientid = %s"
		cursor.execute(stmt, (self.server, str(message.author.id),))
		if cursor.lastrowid != None:
			theDB.commit()
			await message.channel.send("Removed " + message.author.name + " from my DM list!")
		else:
			await message.channel.send("Something went wrong!")
		self.disconnect(theDB, cursor)
