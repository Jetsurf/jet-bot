import re
import mysql.connector
from mysql.connector.cursor import MySQLCursorPrepared

class CommandParser():
	def __init__(self, mysqlinfo, serverConfig, myid):
		self.myid         = myid
		self.db           = None
		self.prefixes     = None
		self.serverConfig = serverConfig
		self.mysqlinfo    = mysqlinfo

	def loadPrefixes(self):
		cursor = self.connect()
		cursor.execute("SELECT * FROM command_prefixes")
		print("Loading command prefixes...")
		self.prefixes = {}
		for row in cursor:
			self.prefixes[row[0]] = row[1].decode("utf-8")
		cursor.close()

	def setPrefix(self, serverid, prefix):
		self.serverConfig.setConfigValue(serverid, 'commandparser.prefix', prefix)

	def getPrefix(self, serverid):
		prefix = self.serverConfig.getConfigValue(serverid, 'commandparser.prefix')
		if prefix == None:
			return '!'
		return prefix

	def parse(self, serverid, message):
		# Ignore zero-length messages. This can happen if there is no text but attached pictures.
		if len(message) == 0:
			return None

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
