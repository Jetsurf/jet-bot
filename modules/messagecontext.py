# Meant to mimic the API of InteractionContext:
# https://github.com/Pycord-Development/pycord/blob/master/discord/app/context.py

class MessageContext:
	def __init__(self, message):
		self.message = message

	@property
	def channel(self):
		return self.message.channel

	@property
	def guild(self):
		return self.message.channel.guild

	@property
	def content(self):
        	return self.message.content

	@property
	def user(self):
		return self.message.author

	@property
	def respond(self):
		return self.message.channel.send

	@property
	def send(self):
		return self.message.channel.send

	@property
	def defer(self):
		return self.message.channel.trigger_typing
