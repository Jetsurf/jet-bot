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

	async def getCurrentSquelches(self, message):
		stmt = 'SELECT * FROM squelch WHERE serverid = %s AND expireddate > NOW()'
		self.cursor.execute(stmt, (self.server,))
		records = self.cursor.fetchall()

		for row in records:
			user = discord.utils.find(lambda m : m.id == str(row[1]), message.channel.server.members)
			admin = discord.utils.find(lambda m : m.id == str(row[2]), message.channel.server.members)
			print("User " + str(user) + " admin " + str(admin))

			await self.client.send_message(message.channel, "User: " + user.name + " squelched by " + admin.name + " on " + str(row[3]) + " expiring " + str(row[4]))

	def getMutes(self):
		print("TBD")

	async def doSquelch(self, message):
		try:
			theUser = message.mentions[0]
			if self.checkSquelch(theUser):
				await self.client.send_message(message.channel, theUser.name + " is already squelched!")
			else:	
				stmt = "INSERT INTO squelch(serverid, userid, adminid, addeddate, expireddate, reason) VALUES(%s, %s, %s, NOW(), NOW() + INTERVAL %s HOUR, %s)"
				input = (self.server, theUser.id, message.author.id, message.content.split(' ')[3], message.content.split(' ', 4)[4],)
				self.cursor.execute(stmt, input)
				if self.cursor.lastrowid != None:
					self.theDB.commit()
					await self.client.send_message(message.channel, str(input))
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