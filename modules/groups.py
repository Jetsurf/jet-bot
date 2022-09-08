import discord, re, sys, time, asyncio, aiomysql, json
from discord.enums import ComponentType, InputTextStyle
from apscheduler.schedulers.asyncio import AsyncIOScheduler

serverGroups = {}
serverChannels = {}

scheduler = AsyncIOScheduler()

client      = None
sqlBroker   = None
friendCodes = None

class Group:
	def __init__(self, startTime, duration, playerCount, gameType, guildid, creator):
		self.groupid     = None
		self.startTime   = startTime
		self.duration    = duration
		self.playerCount = playerCount
		self.gameType    = gameType
		self.guildid     = guildid
		self.creator     = creator
		self.messageTime = None  # Time of last embed update
		self.message     = None
		self.friendCodes = {}  # Maps member ids to friend codes
		self.members     = []  # discord.Member objects for each user

	async def findFriendCode(self, user):
		self.friendCodes[user.id] = await friendCodes.getFriendCode(user.id)

	async def addMember(self, user):
		if not self.hasMember(user):
			self.members.append(user)

		await GroupDB.saveGroup(self)

	async def removeMember(self, user):
		self.members = [x for x in self.members if x.id != user.id]

		await GroupDB.saveGroup(self)

	def hasMember(self, user):
		return user.id in [x.id for x in self.members]

	def memberCount(self):
		return len(self.members)

	async def disband(self):
		groups = serverGroups.get(self.guildid, [])
		serverGroups[self.guildid] = [x for x in groups if x is not self]

		self.members = []

		if self.message:
			await self.message.delete()

		await GroupDB.deleteGroup(self)

	async def updateMessage(self):
		channel = GroupUtils.getServerChannel(self.guildid)

		if len(self.members):
			lines = []
			for m in self.members:
				line = discord.utils.escape_markdown(m.name)

				if m.id == self.creator.id:
					line += " \U0001F451"  # Crown for group owner

				fc = self.friendCodes.get(m.id)
				if not fc is None:
					line += f" \u2023 SW-{fc}"

				lines.append(line)

			memberList = "\n".join(lines)
		else:
			memberList = "(empty)"

		if time.time() < self.startTime:
			color = discord.Colour.yellow()
			title = "Game '%s' starting at <t:%d> (<t:%d:R>)" % (discord.utils.escape_markdown(self.gameType), self.startTime, self.startTime)
		else:
			color = discord.Colour.green()
			title = "Game '%s' open until <t:%d>" % (discord.utils.escape_markdown(self.gameType), self.startTime + self.duration)

		embed = discord.Embed(title = title, color = color)
		embed.add_field(name = f"{self.memberCount()} player{'s' if (len(self.members) != 1) else ''}", value = memberList)
		embed.set_footer(text = f"Wants {self.playerCount} players for {int(self.duration / 60)} minutes")

		if (self.message is None) and channel:
			self.message = await channel.send(embeds = [embed], view = GroupView(self))
		else:
			self.message = await self.message.edit(embeds = [embed], view = GroupView(self))

		self.messageTime = time.time()

		await GroupDB.saveGroup(self)  # Update the message id (can it actually change?)

	def getMessageLink(self):
		if self.message is None:
			return None
		else:
			return self.message.jump_url

class GroupDB:
	@classmethod
	async def saveGroup(cls, group):
		memberjson = json.dumps([x.id for x in group.members])
		sqltime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(group.startTime))
		messageid = group.message.id if group.message else None

		cur = await sqlBroker.connect()

		if group.groupid is None:
			await cur.execute("INSERT INTO group_games (guildid, ownerid, starttime, duration, playercount, gametype, members, messageid) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", (group.guildid, group.creator.id, sqltime, group.duration, group.playerCount, group.gameType, memberjson, messageid))
			group.groupid = cur.lastrowid
		else:
			await cur.execute("UPDATE group_games SET starttime = %s, duration = %s, playercount = %s, gametype = %s, members = %s, messageid = %s WHERE (groupid = %s)", (sqltime, group.duration, group.playerCount, group.gameType, memberjson, messageid, group.groupid))
		await sqlBroker.commit(cur)

	@classmethod
	async def loadGroups(cls):
		cur = await sqlBroker.connect(aiomysql.DictCursor)
		await cur.execute("SELECT * FROM group_games")
		rows = await cur.fetchall()
		for row in rows:
			print(repr(row))

			channel = GroupUtils.getServerChannel(int(row['guildid']))

			#startTime = time.mktime(time.strptime(row['starttime'], '%Y-%m-%d %H:%M:%S'))
			startTime = row['starttime'].timestamp()
			creator = client.get_user(row['ownerid'])
			duration = int(row['duration'])
			playerCount = int(row['playercount'])

			if creator is None:
				print(f"loadGroups(): Can't find group owner by id {row['ownerid']}, discarding group with id {row['groupid']}")
				await cur.execute("DELETE FROM group_games WHERE (groupid = %s)", (row['groupid'],))
				continue

			memberids = json.loads(row['members'])
			members = [client.get_user(id) for id in memberids]
			members = [x for x in members if not (x is None)]

			message = (await channel.fetch_message(row['messageid'])) if row['messageid'] else None

			print(repr(row), repr(members), repr(message))
			g = Group(startTime, duration, playerCount, row['gametype'], int(row['guildid']), creator)
			g.groupid   = int(row['groupid'])
			g.message   = message
			g.members   = members

			for m in members:
				await g.findFriendCode(m)

			await g.updateMessage()

			if g.memberCount == 0:
				await g.disband()

		await sqlBroker.commit(cur)

	@classmethod
	async def deleteGroup(cls, group):
		if group.groupid is None:
			return
		cur = await sqlBroker.connect()
		await cur.execute("DELETE FROM group_games WHERE (groupid = %s)", (group.groupid,))
		await sqlBroker.commit(cur)

class GroupSettingsModal(discord.ui.Modal):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		startTime   = discord.ui.InputText(custom_id = 'startTime',   label = "Starting in how long (blank for ASAP)",       style = discord.InputTextStyle.short, placeholder = "MM or HH:MM", min_length = 1, max_length = 5, required = False, row = 1)
		duration    = discord.ui.InputText(custom_id = 'duration',    label = "How long to keep the group open after start", style = discord.InputTextStyle.short, placeholder = "MM or HH:MM", min_length = 1, max_length = 5, row = 2)
		playerCount = discord.ui.InputText(custom_id = 'playerCount', label = "Players wanted (including you)",                       style = discord.InputTextStyle.short, min_length = 1, max_length = 2, value = "4", row = 3)
		gameType    = discord.ui.InputText(custom_id = 'gameType',    label = "Game type",                                   style = discord.InputTextStyle.short, min_length = 1, max_length = 64, placeholder = "S3 league", row = 4)

		self.add_item(startTime)
		self.add_item(duration)
		self.add_item(playerCount)
		self.add_item(gameType)

		self.callbackHandler = None

	def setFields(self, values):
		GroupUtils.scatterModalValues(self.children, values)

	def getFields(self):
		values = GroupUtils.gatherModalValues(self.children)

		if len(values['startTime']) == 0:
			values['startTime'] = '0'

		return values

	def checkFieldError(self):
		values = self.getFields()

		startMinutes = GroupUtils.parseMinutes(values['startTime'])
		if startMinutes == None:
			return f"I could not understand your start time of `{values['startTime']}`. Try HH:MM or MM format."

		durationMinutes = GroupUtils.parseMinutes(values['duration'])
		if durationMinutes == None:
			return "I could not understand your duration of `{values['duration']}`. Try HH:MM or MM format."
		elif durationMinutes > (12 * 60):
			return f"Sorry, maximum duration is 12 hours"

		return None

	def setCallbackHandler(self, cbh):
		self.callbackHandler = cbh

	async def callback(self, interaction: discord.Interaction):
		error = self.checkFieldError()
		if error:
			await interaction.response.send_message(content = error, allowed_mentions = discord.AllowedMentions.none(), ephemeral = True, delete_after = 10)
			return

		if self.callbackHandler is None:
			return
		elif asyncio.iscoroutinefunction(self.callbackHandler):
			await self.callbackHandler(interaction, self)
		else:
			self.callbackHandler(interaction, self)

class GroupView(discord.ui.View):
	def __init__(self, group):
		# NOTE: For a view to be persistent, timeout must not be set,
		#  and all items must have a custom_id set.
		super().__init__()
		self.timeout = None
		self.group = group

	@discord.ui.button(label = "Join", style=discord.ButtonStyle.primary, custom_id = "joinButton", emoji = "\u2795")
	async def joinCallback(self, button, interaction):
		print(f"Joined - {interaction.user.name}")
		if self.group.hasMember(interaction.user):
			await interaction.response.send_message("You're already in that group", ephemeral = True)
		else:
			await self.group.addMember(interaction.user)
			await self.group.findFriendCode(interaction.user)
			await self.group.updateMessage()
			#await interaction.response.send_message("You joined!", ephemeral = True)
			await interaction.response.send_message("User %s joined group '%s'!" % (discord.utils.escape_markdown(interaction.user.name), discord.utils.escape_markdown(self.group.gameType)), delete_after = 3)

	@discord.ui.button(label = "Leave", style=discord.ButtonStyle.secondary, custom_id = "leaveButton", emoji = "\u2796")
	async def leaveCallback(self, button, interaction):
		print(f"Left - {interaction.user.name}")
		if not self.group.hasMember(interaction.user):
			await interaction.response.send_message("You're not in that group", ephemeral = True)
		else:
			await self.group.removeMember(interaction.user)
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
			values[c.custom_id] = c.value.strip()
		return values

	@classmethod
	def scatterModalValues(cls, children, values):
		for c in children:
			if not c.custom_id:
				continue
			v = values.get(c.custom_id)
			if v is None:
				continue
			c.value = str(v)

	@classmethod
	def parseMinutes(cls, text):
		# Try HH:MM
		match1 = re.match("^([0-9]{1,2}):([0-9]{1,2})$", text)
		if match1:
			return (int(match1.groups()[0]) * 60) + int(match1.groups()[1])

		# Try MMM
		match2 = re.match("^[0-9]{1,3}$", text)
		if match2:
			return int(text)

		# Not understood
		return None

	@classmethod
	def getServerChannel(cls, guildid):
		return serverChannels.get(guildid)

class Groups:
	@classmethod
	def findGroupWithMember(cls, guildid, user):
		groups = serverGroups.get(guildid, [])
		for g in groups:
			if g.hasMember(user):
				return g
		return None

	@classmethod
	def findGroupWithCreator(cls, guildid, user):
		groups = serverGroups.get(guildid, [])
		for g in groups:
			if g.creator.id == user.id:
				return g
		return None

	@classmethod
	async def update(cls):
		now = int(time.time())
		for guildid in serverGroups.keys():
			groups = serverGroups[guildid]
			for g in groups:
				if g.startTime + g.duration < now:
					print(f"Expiring group '{g.gameType}'")
					await g.disband()
				elif g.messageTime and (g.messageTime < (now - 55)):
					#print(f"Updating group message for '{g.gameType}'")
					await g.updateMessage()

	@classmethod
	async def setServerChannel(cls, guildid, channel):
		serverChannels[guildid] = channel
		cur = await sqlBroker.connect()
		await cur.execute("DELETE FROM group_channels WHERE (guildid = %s)", (guildid,))
		await cur.execute("INSERT INTO group_channels (guildid, channelid) VALUES (%s, %s)", (guildid, channel.id))
		await sqlBroker.commit(cur)

	@classmethod
	async def loadServerChannels(cls):
		cur = await sqlBroker.connect()
		await cur.execute("SELECT guildid, channelid FROM group_channels")
		rows = await cur.fetchall()
		await sqlBroker.commit(cur)
		for row in rows:
			(guildid, channelid) = row

			channel = client.get_channel(channelid)
			if channel is None:
				continue  # Channel was probably deleted

			#print(f"  Groups channel for guild {guildid} is '{channel.name}'")
			serverChannels[guildid] = channel

	@classmethod
	def setFriendObjects(cls, _client, _sqlBroker, _friendCodes):
		global client, sqlBroker, friendCodes
		client      = _client
		sqlBroker   = _sqlBroker
		friendCodes = _friendCodes

	@classmethod
	async def startup(cls):
		await cls.loadServerChannels()
		await GroupDB.loadGroups()

class GroupCmds:
	def __init__(self):
		pass

	@classmethod
	async def handleGroupModalCreate(cls, interaction, modal):
		values = modal.getFields()
		print(f"handleGroupModalCreate(): {repr(values)}")

		startMinutes = GroupUtils.parseMinutes(values['startTime'])
		durationMinutes = GroupUtils.parseMinutes(values['duration'])

		startTime = int(time.time()) + (startMinutes * 60)
		g = Group(startTime, durationMinutes * 60, values['playerCount'], values['gameType'], interaction.guild_id, interaction.user)
		if not serverGroups.get(interaction.guild_id):
			serverGroups[interaction.guild_id] = []
		serverGroups[interaction.guild_id].append(g)

		await g.addMember(interaction.user)
		await g.findFriendCode(interaction.user)
		await g.updateMessage()

		link = g.getMessageLink()
		responseText = "Okay, created a new group for '%s'." % (discord.utils.escape_markdown(g.gameType))
		if link:
			responseText += f" You can find it here: {link}"
		await interaction.response.send_message(content = responseText, ephemeral = True)

	@classmethod
	async def handleGroupModalEdit(cls, interaction, modal):
		values = modal.getFields()
		print(f"handleGroupModalEdit(): {repr(values)}")

		startMinutes = GroupUtils.parseMinutes(values['startTime'])
		durationMinutes = GroupUtils.parseMinutes(values['duration'])

		g = Groups.findGroupWithCreator(interaction.guild_id, interaction.user)

		g.startTime = int(time.time()) + (startMinutes * 60)
		g.duration = durationMinutes * 60
		g.playerCount = values['playerCount']
		g.gameType = values['gameType']

		await g.updateMessage()

		responseText = "Okay, edited your group for '%s'." % (discord.utils.escape_markdown(g.gameType))
		await interaction.response.send_message(content = responseText, ephemeral = True)

	#@classmethod
	#async def showGroups(cls, ctx):
	#	groups = serverGroups.get(ctx.guild_id, [])
	#	for g in groups:
	#		await g.updateMessage()
	#	interaction = await ctx.respond("Okay, showed the groups", ephemeral = True)

	@classmethod
	async def create(cls, ctx):
		if not ctx.guild_id:
			await ctx.respond("You can only use this command on a server, not in a DM.", ephemeral = True)
		elif Groups.findGroupWithCreator(ctx.guild_id, ctx.user):
			await ctx.respond("You have already created a group. You can use `/group disband` to disband the old one.", ephemeral = True)
		elif GroupUtils.getServerChannel(ctx.guild_id) is None:
			await ctx.respond("There is no group channel defined for this server. Try `group channel` to set one.", ephemeral = True)
		else:
			modal = GroupSettingsModal(title = "Create a group")
			modal.setCallbackHandler(cls.handleGroupModalCreate)
			await ctx.send_modal(modal)

	@classmethod
	async def edit(cls, ctx):
		if not ctx.guild_id:
			await ctx.respond("You can only use this command on a server, not in a DM.", ephemeral = True)

		g = Groups.findGroupWithCreator(ctx.guild_id, ctx.user)
		if not g:
			await ctx.respond("You haven't created a group. You can create one with `/group create`.", ephemeral = True)
		else:
			startMinutes = max(0, int((g.startTime - time.time()) / 60))

			modal = GroupSettingsModal(title = "Edit group")
			modal.setFields({"startTime": startMinutes, "duration": int(g.duration / 60), "playerCount": g.playerCount, "gameType": g.gameType})
			modal.setCallbackHandler(cls.handleGroupModalEdit)
			await ctx.send_modal(modal)

	@classmethod
	async def disband(cls, ctx):
		if not ctx.guild_id:
			await ctx.respond("You can only use this command on a server, not in a DM.")
			return

		g = Groups.findGroupWithCreator(ctx.guild_id, ctx.user)
		if not g:
			await ctx.respond("You haven't created any group to disband.", ephemeral = True)
		else:
			await g.disband()
			await ctx.respond("Okay, disbanded your group '%s'." % (discord.utils.escape_markdown(g.gameType)), ephemeral = True)

	@classmethod
	async def channel(cls, ctx, channel):
		if not ctx.guild_id:
			await ctx.respond("You can only use this command on a server, not in a DM.", ephemeral = True)
		await Groups.setServerChannel(ctx.guild_id, channel)
		await ctx.respond("Okay, set groups channel to '%s'" % (discord.utils.escape_markdown(channel.name)), ephemeral = True)

scheduler.add_job(Groups.update, 'cron', minute='*', timezone='UTC')
scheduler.start()
