import re

class CommandParser():
	def __init__(self):
		self.myid   = None

	def setUserid(self, myid):
		self.myid = myid

	def parse(self, prefix, message):
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
