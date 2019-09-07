import re
import mysql.connector
from mysql.connector.cursor import MySQLCursorPrepared

class CommandParser():
	def __init__(self):
		self.myid      = None
		self.db        = None
		self.prefixes  = None
		self.mysqlinfo = None

	def setUserid(self, myid):
		self.myid = myid

	def setMysqlInfo(self, mysqlinfo):
		self.mysqlinfo = mysqlinfo

	def connect(self):
		if self.db == None:
			self.db = mysql.connector.connect(host=self.mysqlinfo.host, user=self.mysqlinfo.user, password=self.mysqlinfo.pw, database=self.mysqlinfo.db)
			self.db.autocommit = True
		self.db.ping(True, 2, 1)
		cursor = self.db.cursor(cursor_class=MySQLCursorPrepared)
		return cursor

	def loadPrefixes(self):
		cursor = self.connect()
		cursor.execute("SELECT * FROM command_prefixes")
		print("Loading command prefixes...")
		self.prefixes = {}
		for row in cursor:
			self.prefixes[row[0]] = row[1].decode("utf-8")
		cursor.close()

	def setPrefix(self, serverid, prefix):
		self.prefixes[serverid] = prefix
		cursor = self.connect()
		cursor.execute("REPLACE INTO command_prefixes (serverid, prefix) VALUES (%s, %s)", (serverid, prefix))
		print(cursor.fetchwarnings())
		cursor.close()

	def getPrefix(self, serverid):
		if self.prefixes == None:
			self.loadPrefixes()
		if serverid in self.prefixes:
			return self.prefixes[serverid]
		return '!'

	def parse(self, serverid, message):
		prefix = self.getPrefix(serverid)

		# Validate command prefix or mention
		if message[0] == prefix:
			pos = 1
		elif (self.myid != None) and (message[0:2] == "<@"):
			pos = message.find(" ")
			if pos == -1:
				return None  # No space in message

			mentionid = message[2:pos - 1]
			if not mentionid.isdigit():
				return None  # Mention userid not numeric
			elif int(mentionid) != self.myid:
				return None  # Mention of a different user

			pos += 1
		else:
			return None

		# Split command into words at runs of spaces
		words = re.split(r" +", message[pos:])

		# First word is command, rest are args
		command = words[0].lower()
		args = words[1:]

		return { 'cmd': command, 'args': args }
