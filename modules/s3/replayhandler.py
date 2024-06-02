from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class S3ReplayHandler():

	def __init__(self, ctx, nso, handlers):
		self.ctx = ctx
		self.nso = nso
		self.endtime = (datetime.now() + timedelta(minutes=30))
		self.user = None
		self.initialized = False
		self.seenReplays = []
		self.handlers = handlers
		self.scheduler = AsyncIOScheduler(timezone='UTC')

	async def GetInitialReplays(self, ctx):
		self.user = ctx.author
		self.channel = ctx.channel
		replays = self.nso.s3.get_replay_list()

		for replay in replays['data']['replays']['nodes']:
			if replay['historyDetail']['id'] == "VnNIaXN0b3J5RGV0YWlsLXUtYXBvd2gzM3Q0a2o2a2gyYTNubW06OjIwMjQwNjAyVDAwMTQyMl9jYzhhMzllNC0wZTgxLTQ0MTctOGE1Yi01M2RjZmU2ZjE2ZWE=":
				continue
			else:
				print(f"Found replay ID: {replay['historyDetail']['id']} {replay['historyDetail']['playedTime']}")
				self.seenReplays.append(replay['historyDetail']['id'])

		self.scheduler.add_job(self.GetFeedUpdates, next_run_time=(datetime.now() + timedelta(minutes=5)))

		self.scheduler.start()

	async def GetFeedUpdates(self):
		print(f"Doing replay run for {self.ctx.user.id}")

		refresh = self.nso.s3.get_replay_refresh_list()
		for replay in refresh['data']['replays']['nodes']:
			if replay['historyDetail']['id'] in self.seenReplays:
				continue
			else:
				print(f"Got replay {replay['replayCode']}")
				await self.ctx.channel.send(f"Found a new replay code for {self.ctx.user.name} with replay code {'-'.join(replay['replayCode'][i:i+4] for i in range(0, len(replay['replayCode']), 4))}")
				self.seenReplays.append(replay['historyDetail']['id'])

		timetorun = (datetime.now() + timedelta(minutes=5))

		if timetorun > self.endtime:
			print(f"Last Run for {self.user.name}")
			self.handlers.pop(self.ctx.user.id, None)
		else:
			self.scheduler.add_job(self.GetFeedUpdates, next_run_time=timetorun)


