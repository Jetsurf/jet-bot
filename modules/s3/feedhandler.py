import discord, asyncio
import mysqlhandler
import json, time

from .imagebuilder import S3ImageBuilder
from .schedule import S3Schedule

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone, timedelta

class S3FeedHandler():
	def __init__(self, client, splat3info, mysqlHandler, schedule, cachemanager, fonts, storedm):
		self.client = client
		self.sqlBroker = mysqlHandler
		self.schedule = schedule
		self.storedm = storedm
		self.cachemanager = cachemanager
		self.splat3info = splat3info
		self.fonts = fonts
		self.initialized = False
		self.scheduler = AsyncIOScheduler(timezone='UTC')
		self.scheduler.add_job(self.doMapFeed, 'cron', hour="*/2", minute='0', second='25', timezone='UTC')
		self.scheduler.add_job(self.doGearFeed, 'cron', hour="*/4", minute='0', second='25', timezone='UTC')
		asyncio.create_task(self.scheduleSRFeed())

	async def scheduleSRFeed(self):
		while self.schedule.get_schedule('SR') == []:
			await asyncio.sleep(1)

		sched = self.schedule.get_schedule('SR')
		#(datetime.now() + timedelta(minutes=1)).timestamp())
		runtime = datetime.fromtimestamp(int(sched[0]['endtime']) + 20)
		print(f"Scheduling SR feed run at {runtime}")
		self.scheduler.add_job(self.doSRFeed, 'date', next_run_time=runtime)

		if not self.initialized:
			self.scheduler.start()
			self.initialized = True

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

		cur = await self.sqlBroker.connect()
		await cur.execute("SELECT * from s3feeds WHERE (maps = 1)")
		map_feeds = await cur.fetchall()
		
		print(f"Doing {len(map_feeds)} S3 map feeds")

		for id in range(len(map_feeds)):
			img = discord.File(image_io, filename = "maps-feed.png", description = "Current S3 multiplayer schedule")
			embed.set_image(url = "attachment://maps-feed.png")
			image_io.seek(0)

			channel = self.client.get_guild(int(map_feeds[id][0])).get_channel(int(map_feeds[id][1]))
			if channel != None:
				await channel.send(file = img, embed = embed)
			else:
				print(f"Deleting feed for channel {map_feeds[id][1]}")
				await cur.execute("DELETE FROM s3feeds WHERE channelid = %s", (map_feeds[id][1],))

		await self.sqlBroker.commit(cur)

	async def doSRFeed(self):
		await self.scheduleSRFeed() # Setup next run

		sched = self.schedule.get_schedule('SR', count = 2)
		image_io = S3ImageBuilder.createSRScheduleImage(sched, self.fonts, self.cachemanager)
		embed = discord.Embed(colour=0x0004FF)
		embed.title = "Current Splatoon 3 Salmon Run rotation"


		cur = await self.sqlBroker.connect()
		await cur.execute("SELECT * from s3feeds WHERE sr = 1")
		srFeeds = await cur.fetchall()

		print(f"Doing {len(srFeeds)} S3 Salmon Run feeds")

		for id in range(len(srFeeds)):
			img = discord.File(image_io, filename = "sr-feed.png", description = "Current S3 Salmon Run schedule")
			embed.set_image(url = "attachment://sr-feed.png")
			image_io.seek(0)

			channel = self.client.get_guild(int(srFeeds[id][0])).get_channel(int(srFeeds[id][1]))
			if channel != None:
				await channel.send(file = img, embed = embed)
			else:
				print(f"Deleting feed for channel {srFeeds[id][1]}")
				await cur.execute("DELETE FROM s3feeds WHERE channelid = %s", (srFeeds[id][1],))

		await self.sqlBroker.commit(cur)

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
		
		cur = await self.sqlBroker.connect()
		await cur.execute("SELECT * FROM s3feeds WHERE gear = 1")
		gearFeeds = await cur.fetchall()

		print(f"Doing {len(gearFeeds)} S3 gear feeds")

		for id in range(len(gearFeeds)):
			img = discord.File(image_io, filename = "gear-feed.png", description = "New gear posted to Splatoon 3 Splatnet")
			embed.set_image(url = "attachment://gear-feed.png")			
			image_io.seek(0)

			channel = self.client.get_guild(int(gearFeeds[id][0])).get_channel(int(gearFeeds[id][1]))
			if channel != None:
				await channel.send(file = img, embed = embed)
			else:
				print(f"Deleting feed for channel {gearFeeds[id][1]}")
				await cur.execute("DELETE FROM s3feeds WHERE channelid = %s", (gearFeeds[id][1],))

		await self.sqlBroker.commit(cur)
		return

