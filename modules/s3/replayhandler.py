import discord
from .imagebuilder import S3ImageBuilder
from .embedbuilder import S3EmbedBuilder
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class replayView(discord.ui.View):
	def __init__(self, nsoToken, replay):
		super().__init__()
		self.nsoToken = nsoToken
		self.replay = replay
		self.replayCode = replay['replayCode']
		url = "https://s.nintendo.com/av5ja-lp1/znca/game/4834290508791808?p=%2Freplay%3Fcode%3D"
		self.formattedCode = '-'.join(self.replayCode[i:i+4] for i in range(0, len(self.replayCode), 4))
		self.add_item(discord.ui.Button(label="NSO App Link", url=url + self.formattedCode))
		dlButton = discord.ui.Button(label="Download to NSO")
		dlButton.callback = self.dlButton
		self.add_item(dlButton)

	async def dlButton(self, interaction: discord.Interaction):
		nso = await self.nsoToken.get_nso_client(interaction.user.id)
		if not nso.is_logged_in():
			await interaction.response.send_message("You aren't setup for NSO commands! Run /token to get started", ephemeral=True)
			return
		
		ret = nso.s3.download_replay_from_code(self.replay['id'])
		#2nd Check may not be needed, { "data": { "replay": null } } is returned on invalid codes
		if ret is None or 'reserveReplayDownload' not in ret['data']:
			await interaction.response.send_message("Something went wrong", ephemeral=True)
		else:
			await interaction.response.send_message(f"{interaction.user.display_name} - added replay {self.formattedCode} for viewing in-game.")

class S3ReplayHandler():

	def __init__(self, ctx, nsoToken, handlers, cacheManager, fonts):
		self.ctx = ctx
		self.nsoToken = nsoToken
		self.cacheManager = cacheManager
		self.fonts = fonts
		self.endtime = (datetime.now() + timedelta(minutes=120))
		self.user = None
		self.initialized = False
		self.seenReplays = []
		self.handlers = handlers
		self.scheduler = AsyncIOScheduler(timezone='UTC')

	async def GetInitialReplays(self, ctx):
		self.user = ctx.author
		self.channel = ctx.channel
		nso = await self.nsoToken.get_nso_client(ctx.user.id)
		replays = nso.s3.get_replay_list()

		for replay in replays['data']['replays']['nodes']:
			print(f"Found replay ID for {ctx.user.id} : {replay['id']} {replay['historyDetail']['playedTime']}")
			self.seenReplays.append(replay['id'])

		#1 minute here only for testing
		self.scheduler.add_job(self.GetFeedUpdates, next_run_time=(datetime.now() + timedelta(minutes=5)))

		print(f"Starting S3 Replay Watch for user {self.ctx.user.id}")
		self.scheduler.start()

	async def GetFeedUpdates(self):
		print(f"Doing replay run for {self.ctx.user.id}")

		nso = await self.nsoToken.get_nso_client(self.ctx.user.id)
		refresh = nso.s3.get_replay_refresh_list()
		for replay in refresh['data']['replays']['nodes']:
			if replay['id'] in self.seenReplays:
				continue
			else:
				print(f"Got replay {replay['replayCode']}")
				file = None
				playerJson = { 'data' : { 'currentPlayer' : replay['historyDetail']['player'] } }
				embed = S3EmbedBuilder.createReplayEmbed(replay)
				file = None
				if nameplate_io := S3ImageBuilder.getNamePlateImageIO(playerJson, self.fonts, self.cacheManager):
					file = discord.File(nameplate_io, filename = "nameplate.png", description = "Nameplate")
					embed.set_thumbnail(url=f"attachment://nameplate.png")

				self.seenReplays.append(replay['id'])

				await self.ctx.channel.send(embed = embed, file = file, view = replayView(self.nsoToken, replay))

		#Keep at 5?
		timetorun = (datetime.now() + timedelta(minutes=5))

		if timetorun > self.endtime:
			print(f"Last replay run for {self.user.id}")
			self.handlers.pop(self.ctx.user.id, None)
		else:
			self.scheduler.add_job(self.GetFeedUpdates, next_run_time=timetorun)
