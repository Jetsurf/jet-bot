import mysql.connector
from mysql.connector.cursor import MySQLCursorPrepared
import discord
import asyncio
import mysqlinfo

class Punish():
	def __init__(self, client, id, mysqlinfo):
		self.client = client
		self.theDB = mysql.connector.connect(host=mysqlinfo.host, user=mysqlinfo.user, password=mysqlinfo.pw, database=mysqlinfo.db)
		self.server = id
		self.cursor = self.theDB.cursor(cursor_class=MySQLCursorPrepared)

	async def getSquelches(self, message, all=0):
		stmt = 'SELECT * FROM squelch WHERE serverid = %s'
		theString = ''
		if all == 0:
			stmt = stmt + ' AND expireddate > NOW()'

		self.cursor.execute(stmt, (self.server,))
		records = self.cursor.fetchall()

		for row in records:
			user = discord.utils.find(lambda m : m.id == str(row[1]), message.channel.server.members)
			admin = discord.utils.find(lambda m : m.id == str(row[2]), message.channel.server.members)
			theString = theString + "User: " + user.name + " squelched by " + admin.name + " on " + str(row[3]) + " expiring " + str(row[4]) + '\n'
			
		await self.client.send_message(message.channel, theString)

	def getMutes(self):
		print("TBD")

	async def doSquelch(self, message):
		try:
			theUser = message.mentions[0]
			if theUser.server_permissions.administrator:
				await self.client.send_message(message.channel, "Cannot squelch " + theUser.name + " as they are an admin!")
				return

			if self.checkSquelch(theUser):
				await self.client.send_message(message.channel, theUser.name + " is already squelched!")
			else:	
				stmt = "INSERT INTO squelch(serverid, userid, adminid, addeddate, expireddate, reason) VALUES(%s, %s, %s, NOW(), NOW() + INTERVAL %s HOUR, %s)"
				input = (self.server, theUser.id, message.author.id, message.content.split(' ')[3], message.content.split(' ', 4)[4],)
				self.cursor.execute(stmt, input)
				if self.cursor.lastrowid != None:
					self.theDB.commit()
					await self.client.send_message(message.channel, theUser.name + " has been squelched for " + message.content.split(' ')[3] + " hours")
				else:
					await self.client.send_message(message.channel, "Something went wrong!")
		except Exception as e:
			await self.client.send_message(message.channel, "You didn't do something right, proper command is !admin squelch @user TIME REASON: Error is " + str(e))

	async def removeSquelch(self, message):
		try:
			theUser = message.mentions[0]
			if not self.checkSquelch(theUser):
				await client.send_message(message.channel, "User " + theUser.name + " isn't squelched")
			else:
				stmt = "UPDATE squelch SET expireddate = NOW() WHERE serverid = %s AND userid = %s AND expireddate > NOW()"
				self.cursor.execute(stmt, (self.server, theUser.id,))
				if self.cursor.lastrowid != None:
					await self.client.send_message(message.channel, "User " + theUser.name + " has been unsquelched")
					self.theDB.commit()
				else:
					await self.client.send_message(message.channel, "Something went wrong!")

		except Exception as e:
			await self.client.send_message(message.channel, "You didn't do something right, proper command is !admin unsquelch @user: Error is " + str(e))	

	def checkDM(self, clientid):
		stmt = "SELECT COUNT(*) FROM dms WHERE serverid = %s AND clientid = %s"
		self.cursor.execute(stmt, (self.server, clientid,))
		count = self.cursor.fetchone()

		if count[0] > 0:
			return True
		else:
			return False

	async def addDM(self, message):
		if self.checkDM(message.author.id):
			await self.client.send_message(message.channel, "You are already in my list of people to DM")
			return
		stmt = "INSERT INTO dms(serverid, clientid) values(%s, %s)"
		self.cursor.execute(stmt, (self.server, message.author.id,))
		if self.cursor.lastrowid != None:
			self.theDB.commit()
			await self.client.send_message(message.channel, "Added " + message.author.name + " to my DM list!")
		else:
			await self.client.send_message(message.channel, "Something went wrong!")

	async def removeDM(self, message):
		if not self.checkDM(message.author.id):
			await self.client.send_message(message.channel, "You aren't in my list of people to DM")
			return
		stmt = "DELETE FROM dms WHERE serverid = %s AND clientid = %s"
		self.cursor.execute(stmt, (self.server, message.author.id,))
		if self.cursor.lastrowid != None:
			self.theDB.commit()
			await self.client.send_message(message.channel, "Removed " + message.author.name + " from my DM list!")
		else:
			await self.client.send_message(message.channel, "Something went wrong!")

	def doMute(self):
		print("TBD")

	def checkSquelch(self, theUser):
		stmt = "SELECT COUNT(*) FROM squelch WHERE serverid = %s AND userid = %s AND expireddate > NOW()"
		self.cursor.execute(stmt, (self.server, theUser.id,))
		count = self.cursor.fetchone()

		if count[0] > 0:
			return True
		else:
			return False

	def checkMute(self):
		print("TBD")