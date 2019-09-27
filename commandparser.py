import re
import mysql.connector
from mysql.connector.cursor import MySQLCursorPrepared

class CommandParser():

	def __init__(self, serverConfig, myid):
		self.myid         = myid
		self.db           = None
		self.prefixes     = {}
		self.serverConfig = serverConfig

	def setPrefix(self, serverid, prefix):
		self.prefixes[serverid] = prefix
		self.serverConfig.setConfigValue(serverid, 'commandparser.prefix', prefix)

	def getPrefix(self, serverid):
		if serverid in self.prefixes:
			return self.prefixes[serverid]

		prefix = self.serverConfig.getConfigValue(serverid, 'commandparser.prefix')
		if prefix == None:
			prefix = '!'
		self.prefixes[serverid] = prefix
		return prefix

	def parse(self, serverid, message):
		# Ignore zero-length messages. This can happen if there is no text but attached pictures.
		if len(message) == 0:
			return None

		prefix = self.getPrefix(serverid)
		prefixlen = len(prefix)

		# Validate command prefix or mention
		if (len(message) > prefixlen) and (message[0:prefixlen] == prefix):
			pos = prefixlen
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
