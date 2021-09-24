# Meant to mimic the API of InteractionContext:
# https://github.com/Pycord-Development/pycord/blob/master/discord/app/context.py

class MessageContext:
	def __init__(self, message):
		self.message = message

	@property
	def channel(self):
		return self.message.channel

	@property
	def channel(self):
		return self.message.channel.id

	@property
	def guild(self):
		return self.message.channel.guild

#	@property
#	def message(self):
#        	return self.message

	@property
	def user(self):
		return self.message.author

	@property
	def respond(self):
		return self.message.channel.send

	@property
	def send(self):
		return self.message.channel.send

