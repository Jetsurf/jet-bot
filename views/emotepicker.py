import sys, discord
sys.path.append('../modules')
import mysqlhandler

class DropDown(discord.ui.Select):
	def __init__(self, emoteSelect):
		self.val = emoteSelect
		self.choice = ""

	async def initOpts(self, ctx, msg):
		options = []

		for emote in await ctx.guild.fetch_emojis():
			if emote.is_usable():
				options.append(discord.SelectOption(label=emote.name, description=emote.name, emoji=emote)) #f"<:{emote.name}:{str(emote.id)}>"))

		super().__init__(placeholder=msg, options=options, custom_id=self.val)

	async def callback(self, interaction: discord.Interaction):
		self.choice = self.values[0]

class confirm(discord.ui.Button):
	def __init__(self):
		super().__init__(style=discord.ButtonStyle.green, label='Confirm')

	async def callback(self, interaction: discord.Interaction):
		for opt in self.view.opts:
			if opt.choice == "":
				await interaction.response.send_message("Please provide a choice for each option", ephemeral=True)
				return

		string = ""
		choices = {}
		for opt in self.view.opts:
			for emote in await interaction.guild.fetch_emojis():
				if opt.choice == emote.name:
					break

			string+=f'{opt.val} : <:{emote.name}:{emote.id}>\n'
			choices[opt.val] = f"<:{emote.name}:{emote.id}>"
		
		cur = await self.view.sqlBroker.connect()
		await cur.execute("REPLACE INTO emotes (myid, turfwar, ranked, league) VALUES(%s, %s, %s, %s)", (self.view.client.user.id, choices['turfwar'], choices['ranked'], choices['league'],))
		await self.view.sqlBroker.commit(cur)
		await interaction.response.edit_message(content=f"Choices:\n{string}", view=None)
		self.view.stop()

class EmotePicker(discord.ui.View):
	def __init__(self, client, mysqlHandler):
		self.opts = []
		self.client = client
		self.sqlBroker = mysqlHandler
		self.picks = [ 'turfwar', 'ranked', 'league' ]
		super().__init__()
	
	async def init_options(self, ctx):
		for pick in self.picks:
			opt = DropDown(pick)
			await opt.initOpts(ctx, f'Select emote for {pick}')
			self.opts.append(opt)
			self.add_item(opt)

		but = confirm()
		self.add_item(but)