import discord

class DropDown(discord.ui.Select):
	def __init__(self, emoteSelect):
		self.val = emoteSelect
		self.choice = ""

	async def initOpts(self, ctx, msg):
		options = []

		for emote in await ctx.guild.fetch_emojis():
			if emote.is_usable():
				options.append(discord.SelectOption(label=emote.name, description=emote.name, emoji=emote)) #f"<:{emote.name}:{str(emote.id)}>"))

		super().__init__(placeholder=msg, min_values=1, max_values=1, options=options, custom_id=self.val)

	async def callback(self, interaction: discord.Interaction):
		self.choice = self.values[0]

class confirm(discord.ui.Button):
	def __init__(self):
		super().__init__(style=discord.ButtonStyle.green, label='Confirm')


	async def callback(self, interaction: discord.Interaction):
		choices = 0
		for opt in self.view.opts:
			if opt.choice != "":
				choices+=1
		if choices != len(self.view.picks):
			await interaction.response.send_message("Please provide a choice for each option", ephemeral=True)
			return

		string = ""
		for opt in self.view.opts:
			for emote in await interaction.guild.fetch_emojis():
				if opt.choice == emote.name:
					break

			string+=f'{opt.val} : <:{emote.name}:{emote.id}>\n'

		await interaction.response.edit_message(content=f"Choices:\n{string}", view=None)
		self.view.stop()

class EmotePicker(discord.ui.View):
	def __init__(self):
		self.opts = []
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