import discord, re, sys, time
from discord.enums import ComponentType, InputTextStyle
from apscheduler.schedulers.asyncio import AsyncIOScheduler

serverGroups = {}
serverChannels = {}

scheduler = AsyncIOScheduler()

class Group:
	def __init__(self, startTime, duration, playerCount, gameType, guild_id, creator):
		self.startTime   = startTime
		self.duration    = duration
		self.playerCount = playerCount
		self.gameType    = gameType
		self.guild_id    = guild_id
		self.creator     = creator
		self.message     = None
		self.members     = []  # discord.Member objects for each user

	def addMember(self, user):
		if not self.hasMember(user):
			self.members.append(user)

	def removeMember(self, user):
		self.members = [x for x in self.members if x.id != user.id]

	def hasMember(self, user):
		return user.id in [x.id for x in self.members]

	def memberCount(self):
		return len(self.members)

	async def disband(self):
		groups = serverGroups.get(self.guild_id, [])
		serverGroups[self.guild_id] = [x for x in groups if x is not self]

		self.members = []

		if self.message:
			await self.message.delete()

	async def updateMessage(self):
		channel = GroupUtils.getServerChannel(self.guild_id)

		if len(self.members):
			memberList = "\n".join([discord.utils.escape_markdown(x.name) for x in self.members])
		else:
			memberList = "(empty)"

		if time.time() < self.startTime:
			title = "Game '%s' starting at <t:%d> (<t:%d:R>)" % (discord.utils.escape_markdown(self.gameType), self.startTime, self.startTime)
		else:
			title = "Game '%s' open until <t:%d>" % (discord.utils.escape_markdown(self.gameType), self.startTime + self.duration)

		embed = discord.Embed(title = title)
		embed.add_field(name = f"{self.memberCount()} player{'s' if (len(self.members) != 1) else ''}", value = memberList)
		embed.set_footer(text = f"Wants {self.playerCount} players for {int(self.duration / 60)} minutes")

		if (self.message is None) and channel:
			self.message = await channel.send(embeds = [embed], view = GroupView(self))
		else:
			self.message = await self.message.edit(embeds = [embed], view = GroupView(self))

	def getMessageLink(self):
		if self.message is None:
			return None
		else:
			return self.message.jump_url


class CreateGroupModal(discord.ui.Modal):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		startTime   = discord.ui.InputText(custom_id = 'startTime',   label = "Starting in how long (blank for ASAP)",       style = discord.InputTextStyle.short, placeholder = "MM or HH:MM", min_length = 1, max_length = 5, required = False, row = 1)
		duration    = discord.ui.InputText(custom_id = 'duration',    label = "How long to keep the group open after start", style = discord.InputTextStyle.short, placeholder = "MM or HH:MM", min_length = 1, max_length = 5, row = 2)
		playerCount = discord.ui.InputText(custom_id = 'playerCount', label = "Players wanted",                              style = discord.InputTextStyle.short, min_length = 1, max_length = 2, value = "4", row = 3)
		gameType    = discord.ui.InputText(custom_id = 'gameType',    label = "Game type",                                   style = discord.InputTextStyle.short, min_length = 1, max_length = 64, placeholder = "S3 league", row = 4)
		self.add_item(startTime)
		self.add_item(duration)
		self.add_item(playerCount)
		self.add_item(gameType)

	async def callback(self, interaction: discord.Interaction):
		await GroupCmds.handleCreateGroupModal(interaction, self.children)

class GroupView(discord.ui.View):
	def __init__(self, group):
		super().__init__()
		self.group = group

	@discord.ui.button(label = "Join", style=discord.ButtonStyle.primary, emoji = "\u2795")
	async def joinCallback(self, button, interaction):
		print(f"Joined - {interaction.user.name}")
		if self.group.hasMember(interaction.user):
			await interaction.response.send_message("You're already in that group", ephemeral = True)
		else:
			self.group.addMember(interaction.user)
			await self.group.updateMessage()
			#await interaction.response.send_message("You joined!", ephemeral = True)
			await interaction.response.send_message("User %s joined group '%s'!" % (discord.utils.escape_markdown(interaction.user.name), discord.utils.escape_markdown(self.group.gameType)), delete_after = 3)

	@discord.ui.button(label = "Leave", style=discord.ButtonStyle.secondary, emoji = "\u2796")
	async def leaveCallback(self, button, interaction):
		print(f"Left - {interaction.user.name}")
		if not self.group.hasMember(interaction.user):
			await interaction.response.send_message("You're not in that group", ephemeral = True)
		else:
			self.group.removeMember(interaction.user)
			await self.group.updateMessage()
			#await interaction.response.send_message("You left!", ephemeral = True)

			if self.group.memberCount() > 0:
				await interaction.response.send_message("User %s left group '%s'!" % (discord.utils.escape_markdown(interaction.user.name), discord.utils.escape_markdown(self.group.gameType)), delete_after = 3)
			else:
				await interaction.response.send_message("User %s left group '%s'! All members are gone, so group is disbanded." % (discord.utils.escape_markdown(interaction.user.name), discord.utils.escape_markdown(self.group.gameType)), delete_after = 3)
				await self.group.disband()

class GroupUtils:
	@classmethod
	def gatherModalValues(cls, children):
		values = {}
		for c in children:
			values[c.custom_id] = c.value
		return values

	@classmethod
	def parseMinutes(cls, text):
		# Try HH:MM
		match1 = re.match("^([0-9]{1,2}):([0-9]{1,2})$", text)
		if match1:
			return int(match1.groups()[0] * 60) + int(match1.groups()[1])

		# Try MMM
		match2 = re.match("^[0-9]{1,3}$", text)
		if match2:
			return int(text)

		# Not understood
		return None

	@classmethod
	def getServerChannel(cls, guild_id):
		return serverChannels.get(guild_id)

class Groups:
	@classmethod
	def findGroupWithMember(cls, guild_id, user):
		groups = serverGroups.get(guild_id, [])
		for g in groups:
			if g.hasMember(user):
				return g
		return None

	@classmethod
	def findGroupWithCreator(cls, guild_id, user):
		groups = serverGroups.get(guild_id, [])
		for g in groups:
			if g.creator.id == user.id:
				return g
		return None

	@classmethod
	async def expire(cls):
		now = int(time.time())
		for guild_id in serverGroups.keys():
			groups = serverGroups[guild_id]
			for g in groups:
				if g.startTime + g.duration < now:
					print(f"Expiring group '{g.gameType}'")
					await g.disband()

class GroupCmds:
	def __init__(self):
		pass

	@classmethod
	async def handleCreateGroupModal(cls, interaction, children):
		values = GroupUtils.gatherModalValues(children)
		print(repr(values))

		if len(values['startTime']) == 0:
			values['startTime'] = '0'

		startMinutes = GroupUtils.parseMinutes(values['startTime'])
		if startMinutes == None:
			await interaction.response.send_message(content = f"I could not understand your start time of `{values['startTime']}`. Try HH:MM or MM format.", allowed_mentions = discord.AllowedMentions.none(), ephemeral = True, delete_after = 10)
			return

		durationMinutes = GroupUtils.parseMinutes(values['duration'])
		if durationMinutes == None:
			await interaction.response.send_message(content = f"I could not understand your duration of `{values['duration']}`. Try HH:MM or MM format.", allowed_mentions = discord.AllowedMentions.none(), ephemeral = True)
			return
		if durationMinutes > (12 * 60):
			await interaction.response.send_message(content = f"Sorry, maximum duration is 12 hours", ephemeral = True)
			return

		startTime = int(time.time()) + (startMinutes * 60)
		g = Group(startTime, durationMinutes * 60, values['playerCount'], values['gameType'], interaction.guild_id, interaction.user)
		if not serverGroups.get(interaction.guild_id):
			serverGroups[interaction.guild_id] = []
		serverGroups[interaction.guild_id].append(g)

		g.addMember(interaction.user)
		await g.updateMessage()

		link = g.getMessageLink()
		responseText = "Okay, created a new group for '%s'." % (discord.utils.escape_markdown(g.gameType))
		if link:
			responseText += f" You can find it here: {link}"
		await interaction.response.send_message(content = responseText, ephemeral = True, delete_after = 3)

	@classmethod
	async def showGroups(cls, ctx):
		groups = serverGroups.get(ctx.guild_id, [])
		for g in groups:
			await g.updateMessage()
			#await interaction.response.send_message(embeds = [embed], view = GroupView(g))
			#await interaction.response.send_message(view = GroupView(g))
		#await interaction.response.defer()
		#await ctx.defer(invisible = True)
		#await ctx.response.send_message(content = "Okay, showed the groups", ephemeral = True, delete_after = 5)
		#await ctx.respond("Okay, showed the groups", ephemeral = True, delete_after = 3)
		interaction = await ctx.respond("Okay, showed the groups", ephemeral = True)
		await interaction.delete_original_message(delay = 3)

	@classmethod
	async def create(cls, ctx):
		if not ctx.guild_id:
			await ctx.respond("You can only use this command on a server, not in a DM.", ephemeral = True)
		elif Groups.findGroupWithCreator(ctx.guild_id, ctx.user):
			await ctx.respond("You have already created a group. You can use `/group disband` to disband the old one.", ephemeral = True)
		elif GroupUtils.getServerChannel(ctx.guild_id) is None:
			await ctx.respond("There is no group channel defined for this server. Try `group channel` to set one.", ephemeral = True)
		else:
			await ctx.send_modal(CreateGroupModal(title = "Create a group"))

	@classmethod
	async def disband(cls, ctx):
		if not ctx.guild_id:
			await ctx.respond("You can only use this command on a server, not in a DM.")
			return

		g = Groups.findGroupWithCreator(ctx.guild_id, ctx.user)
		if not g:
			await ctx.respond("You haven't created any group to disband.")
		else:
			await g.disband()
			await ctx.respond("Disbanded your group '%s'." % (discord.utils.escape_markdown(g.gameType)))

	@classmethod
	async def channel(cls, ctx, channel):
		if not ctx.guild_id:
			await ctx.respond("You can only use this command on a server, not in a DM.", ephemeral = True)
		serverChannels[ctx.guild_id] = channel
		await ctx.respond("Okay, set groups channel to '%s'" % (discord.utils.escape_markdown(channel.name)), ephemeral = True)

scheduler.add_job(Groups.expire, 'cron', minute='*', timezone='UTC')
scheduler.start()
