import mysql.connector
from mysql.connector.cursor import MySQLCursorPrepared
import discord
import asyncio
import mysqlinfo

class Punish():
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

	async def getSquelches(self, message, all=0):
		theDB, cursor = self.connect()
		embed = discord.Embed(0xE52D2A)
		stmt = 'SELECT * FROM squelch WHERE serverid = %s'
		if all == 0:
			embed.title = 'Current Squelches'
			stmt = stmt + ' AND expireddate > NOW()'
		else: 
			embed.title = 'All Squelches'
		
		cursor.execute(stmt, (self.server,))
		records = cursor.fetchall()
		self.disconnect(theDB, cursor)

		for row in records:
			user = discord.utils.find(lambda m : m.id == str(row[1]), message.channel.server.members)
			admin = discord.utils.find(lambda m : m.id == str(row[2]), message.channel.server.members)
			embed.add_field(name= "User: " + user.name, value=" squelched by " + admin.name + " on " + str(row[3]) + " expiring " + str(row[4]), inline=False)
		
		await self.client.send_message(message.channel, theString)

	def getMutes(self):
		print("TBD")

	async def doSquelch(self, message):
		try:
			theDB, cursor = self.connect()
			theUser = message.mentions[0]
			if theUser.server_permissions.administrator:
				await self.client.send_message(message.channel, "Cannot squelch " + theUser.name + " as they are an admin!")
				return

			if self.checkSquelch(theUser):
				await self.client.send_message(message.channel, theUser.name + " is already squelched!")
			else:	
				stmt = "INSERT INTO squelch(serverid, userid, adminid, addeddate, expireddate, reason) VALUES(%s, %s, %s, NOW(), NOW() + INTERVAL %s HOUR, %s)"
				input = (self.server, theUser.id, message.author.id, message.content.split(' ')[3], message.content.split(' ', 4)[4],)
				cursor.execute(stmt, input)
				if cursor.lastrowid != None:
					theDB.commit()
					await self.client.send_message(message.channel, theUser.name + " has been squelched for " + message.content.split(' ')[3] + " hours")
				else:
					await self.client.send_message(message.channel, "Something went wrong!")
			self.disconnect(theDB, cursor)
		except Exception as e:
			await self.client.send_message(message.channel, "You didn't do something right, proper command is !admin squelch @user TIME REASON: Error is " + str(e))

	async def removeSquelch(self, message):
		try:
			theDB, cursor = self.connect()
			theUser = message.mentions[0]
			if not self.checkSquelch(theUser):
				await client.send_message(message.channel, "User " + theUser.name + " isn't squelched")
			else:
				stmt = "UPDATE squelch SET expireddate = NOW() WHERE serverid = %s AND userid = %s AND expireddate > NOW()"
				cursor.execute(stmt, (self.server, theUser.id,))
				if cursor.lastrowid != None:
					await self.client.send_message(message.channel, "User " + theUser.name + " has been unsquelched")
					theDB.commit()
				else:
					await self.client.send_message(message.channel, "Something went wrong!")
			self.disconnect(theDB, cursor)
		except Exception as e:
			await self.client.send_message(message.channel, "You didn't do something right, proper command is !admin unsquelch @user: Error is " + str(e))	

	def checkDM(self, clientid):
		theDB, cursor = self.connect()
		stmt = "SELECT COUNT(*) FROM dms WHERE serverid = %s AND clientid = %s"
		cursor.execute(stmt, (self.server, clientid,))
		count = cursor.fetchone()
		self.disconnect(theDB, cursor)

		if count[0] > 0:
			return True
		else:
			return False

	async def addDM(self, message):
		theDB, cursor = self.connect()
		if self.checkDM(message.author.id):
			await self.client.send_message(message.channel, "You are already in my list of people to DM")
			return
		stmt = "INSERT INTO dms(serverid, clientid) values(%s, %s)"
		cursor.execute(stmt, (self.server, message.author.id,))
		if cursor.lastrowid != None:
			theDB.commit()
			await self.client.send_message(message.channel, "Added " + message.author.name + " to my DM list!")
		else:
			await self.client.send_message(message.channel, "Something went wrong!")
		self.disconnect(theDB, cursor)

	async def removeDM(self, message):
		theDB, cursor = self.connect()

		if not self.checkDM(message.author.id):
			await self.client.send_message(message.channel, "You aren't in my list of people to DM")
			return

		stmt = "DELETE FROM dms WHERE serverid = %s AND clientid = %s"
		cursor.execute(stmt, (self.server, message.author.id,))
		if cursor.lastrowid != None:
			theDB.commit()
			await self.client.send_message(message.channel, "Removed " + message.author.name + " from my DM list!")
		else:
			await self.client.send_message(message.channel, "Something went wrong!")
		self.disconnect(theDB, cursor)

	def doMute(self):
		print("TBD")

	def checkSquelch(self, theUser):
		theDB, cursor= self.connect()
		stmt = "SELECT COUNT(*) FROM squelch WHERE serverid = %s AND userid = %s AND expireddate > NOW()"
		cursor.execute(stmt, (self.server, theUser.id,))
		count = cursor.fetchone()
		self.disconnect(theDB, cursor)

		if count[0] > 0:
			return True
		else:
			return False

	def checkMute(self):
		print("TBD")