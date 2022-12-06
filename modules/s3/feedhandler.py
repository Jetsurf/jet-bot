import discord, asyncio
import mysqlhandler
import json, time

from .imagebuilder import S3ImageBuilder
from .schedule import S3Schedule

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone

class S3FeedHandler():
	def __init__(self, client, splat3info, mysqlHandler, schedule, cachemanager, fonts, storedm):
		self.client = client
		self.sqlBroker = mysqlHandler
		self.schedule = schedule
		self.storedm = storedm
		self.cachemanager = cachemanager
		self.splat3info = splat3info
		self.fonts = fonts
		self.scheduler = AsyncIOScheduler(timezone='UTC')
		self.debug = True

		self.scheduler.add_job(self.doMapFeed, 'cron', hour="*/2", minute='0', second='25', timezone='UTC')
		self.scheduler.add_job(self.doGearFeed, 'cron', hour="*/4", minute='0', second='25', timezone='UTC')
		asyncio.create_task(self.initSRSchedule())

	async def initSRSchedule(self):
		while self.schedule.get_schedule('SR') == []:
			await asyncio.sleep(1)

		sched = self.schedule.get_schedule('SR')
		runtime = datetime.fromtimestamp(int(sched[0]['endtime']) + 20)
		print(f"Scheduling SR feed run at {runtime}")
		self.scheduler.add_job(self.doSRFeed, 'date', next_run_time=runtime)
		self.scheduler.start()  

	async def doMapFeed(self):
		# Pull each schedule for the current time
		now = time.time()
		schedules = {}
		for t in ['TW', 'SF', 'AO', 'AS', 'XB']:
			schedules[t] = self.schedule.get_schedule(t)

		# Gather all the known time windows
		timewindows = {}
		for t in ['TW', 'SF', 'AO', 'AS', 'XB']:
			for r in schedules[t]:
				timewindows[r['starttime']] = {'starttime': r['starttime'], 'endtime': r['endtime']}

		# Pick the two earliest time windows
		timewindows = list(timewindows.values())
		timewindows.sort(key = lambda w: w['starttime'])
		timewindows = timewindows[0:2]

		if len(timewindows) == 0:
			print("Missed map rotation")
			return

		# Filter the schedules to those matching the two earliest time windows
		for t in ['TW', 'SF', 'AO', 'AS', 'XB']:
			schedules[t] = [s for s in schedules[t] if (r['starttime'] in [w['starttime'] for w in timewindows])]

		image_io = S3ImageBuilder.createScheduleImage(timewindows, schedules, self.fonts, self.cachemanager, self.splat3info)
		embed = discord.Embed(colour=0x0004FF)
		embed.title = "Current Splatoon 3 multiplayer map rotation"
		img = discord.File(image_io, filename = "maps-feed.png", description = "Current S3 multiplayer schedule")
		embed.set_image(url = "attachment://maps-feed.png")

		cur = await self.sqlBroker.connect()
		await cur.execute("SELECT * from s3feeds WHERE sr = 1")
		srFeeds = await cur.fetchall()
		await self.sqlBroker.close(cur)

		print(f"Doing {len(srFeeds)} S3 map feeds")

		for id in range(len(srFeeds)):
			channel = self.client.get_guild(int(srFeeds[id][0])).get_channel(int(srFeeds[id][1]))
			await channel.send(file = img, embed = embed)

	async def doSRFeed(self):
		if not self.debug:
			await self.initSchedule() # Setup next run

		sched = self.schedule.get_schedule('SR', count = 2)
		image_io = S3ImageBuilder.createSRScheduleImage(sched, self.fonts, self.cachemanager)
		embed = discord.Embed(colour=0x0004FF)
		embed.title = "Current Splatoon 3 Salmon Run rotation"
		img = discord.File(image_io, filename = "sr-feed.png", description = "Current S3 Salmon Run schedule")
		embed.set_image(url = "attachment://sr-feed.png")
		
		cur = await self.sqlBroker.connect()
		await cur.execute("SELECT * from s3feeds WHERE sr = 1")
		srFeeds = await cur.fetchall()
		await self.sqlBroker.close(cur)

		print(f"Doing {len(srFeeds)} S3 Salmon Run feeds")

		for id in range(len(srFeeds)):
			channel = self.client.get_guild(int(srFeeds[id][0])).get_channel(int(srFeeds[id][1]))
			await channel.send(file = img, embed = embed)

	async def doGearFeed(self):
		embed = discord.Embed(colour=0x0004FF)
		embed.title = "New gear in the Splatoon 3 Splatnet store"

		if self.storedm.storecache == None:
			print("Storecache is none...")
			return

		if datetime.now(timezone.utc).hour == 0:
			items = self.storedm.storecache['pickupBrand']['brandGears'] 
			items.append(self.storedm.storecache['limitedGears'][5])
			image_io = S3ImageBuilder.createFeedGearCard(items, self.fonts)
		else:
			items = [ self.storedm.storecache['limitedGears'][5] ]
			image_io = S3ImageBuilder.createFeedGearCard(items, self.fonts)

		embed = discord.Embed(colour=0x0004FF)
		embed.title = "New gear in Splatoon 3 Splatnet store"
		img = discord.File(image_io, filename = "gear-feed.png", description = "New gear posted to Splatoon 3 Splatnet")
		embed.set_image(url = "attachment://gear-feed.png")		

		cur = await self.sqlBroker.connect()
		await cur.execute("SELECT * FROM s3feeds WHERE gear = 1")
		gearFeeds = await cur.fetchall()
		await self.sqlBroker.close(cur)

		print(f"Doing {len(gearFeeds)} S3 gear feeds")

		for id in range(len(gearFeeds)):
			channel = self.client.get_guild(int(gearFeeds[id][0])).get_channel(int(gearFeeds[id][1]))
			await channel.send(file = img, embed = embed)
			
		return

