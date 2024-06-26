import discord, asyncio
import mysqlhandler
import json, time

from .imagebuilder import S3ImageBuilder
from .schedule import S3Schedule

from datetime import datetime, timezone, timedelta

class S3FeedHandler():
	def __init__(self, client, splat3info, mysqlHandler, schedule, cachemanager, fonts, store):
		self.client = client
		self.sqlBroker = mysqlHandler
		self.schedule = schedule
		self.cachemanager = cachemanager
		self.splat3info = splat3info
		self.fonts = fonts
		self.store = store
		self.initialized = False

		store.onUpdate(self.onStoreUpdate)

		schedule.on_versus_update(self.onVersusMapUpdate)
		schedule.on_coop_update(self.onCoopMapUpdate)

	def onStoreUpdate(self, items):
		self.client.loop.create_task(self.doGearFeed([i['data'] for i in items]))

	def onVersusMapUpdate(self):
		self.client.loop.create_task(self.doMapFeed())

	def onCoopMapUpdate(self):
		self.client.loop.create_task(self.doSRFeed())

	def getFeedChannel(self, serverid, channelid):
		guild = self.client.get_guild(int(serverid))
		if guild is None:
			print(f"[S3FeedHandler] getFeedChannel(): Can't find server for serverid {serverid}")
			return None

		channel = guild.get_channel_or_thread(int(channelid))
		if channel is None:
			print(f"[S3FeedHandler] getFeedChannel(): Can't find channel for serverid {serverid} channelid {channelid}")
			return None

		return channel

	async def sendFeedMessage(self, serverid, channelid, file = None, embed = None):
		channel = self.getFeedChannel(serverid, channelid)
		if channel is None:
			print(f"[S3FeedHandler] Can't retrieve channel - Deleting feeds for serverid {serverid} channelid {channelid}.")
			async with self.sqlBroker.context() as sql:
				await sql.query("DELETE FROM s3_feeds WHERE (serverid = %s) AND (channelid = %s)", (serverid, channelid))
			return

		try:
			await channel.send(file = file, embed = embed)
		except discord.Forbidden:
			print(f"[S3FeedHandler] 403 - Deleting feeds for serverid {serverid} channelid {channelid}")
			async with self.sqlBroker.context() as sql:
				await sql.query("DELETE FROM s3_feeds WHERE (serverid = %s) AND (channelid = %s)", (serverid, channelid))
			return

	async def doMapFeed(self):
		# Pull each schedule for the current time
		now = time.time()
		schedules = {}
		for t in ['TW', 'SO', 'SP', 'AO', 'AS', 'XB']:
			schedules[t] = self.schedule.get_schedule(t, count = 2)

		# Gather all the known time windows
		timewindows = {}
		for t in ['TW', 'SO', 'SP', 'AO', 'AS', 'XB']:
			for r in schedules[t]:
				timewindows[r['starttime']] = {'starttime': r['starttime'], 'endtime': r['endtime']}

		# Order the time windows
		timewindows = list(timewindows.values())
		timewindows.sort(key = lambda w: w['starttime'])
		if len(timewindows) == 0:
			print("[S3FeedHandler] Missed map rotation")
			return

		# Find the start of the following time window
		nexttime = None
		if len(timewindows) > 1:
			nexttime = timewindows[1]['starttime']

		# Pick the earliest time window to report on
		timewindows = timewindows[0:1]

		# Filter the schedules to those matching the time window(s)
		for t in ['TW', 'SO', 'SP', 'AO', 'AS', 'XB']:
			schedules[t] = [s for s in schedules[t] if (s['starttime'] in [w['starttime'] for w in timewindows])]

		image_io = S3ImageBuilder.createScheduleImage(timewindows, schedules, self.fonts, self.cachemanager, self.splat3info)
		embed = discord.Embed(colour=0x0004FF)
		embed.title = "Current Splatoon 3 multiplayer map rotation"

		embed.description = f"Started <t:{int(timewindows[0]['starttime'])}:t>."
		if nexttime:
			embed.description += f" Next <t:{int(nexttime)}:R>.\n"

		async with self.sqlBroker.context() as sql:
			map_feeds = await sql.query("SELECT * from s3_feeds WHERE (maps = 1)")

		print(f"[S3FeedHandler] Doing {len(map_feeds)} S3 map feeds")

		for feed in map_feeds:
			img = discord.File(image_io, filename = "maps-feed.png", description = "Current S3 multiplayer schedule")
			embed.set_image(url = "attachment://maps-feed.png")
			image_io.seek(0)

			await self.sendFeedMessage(feed['serverid'], feed['channelid'], file = img, embed = embed)

	async def doSRFeed(self):
		sched = self.schedule.get_schedule('SR', count = 2)
		image_io = S3ImageBuilder.createSRScheduleImage(sched, self.fonts, self.cachemanager)
		embed = discord.Embed(colour=0x0004FF)
		embed.title = "Current Splatoon 3 Salmon Run rotation"

		embed.description = f"Started <t:{int(sched[0]['starttime'])}:t>."
		if len(sched) > 1:
			embed.description += f" Next <t:{int(sched[1]['starttime'])}:R>."

		async with self.sqlBroker.context() as sql:
			sr_feeds = await sql.query("SELECT * from s3_feeds WHERE (sr = 1)")

		print(f"[S3FeedHandler] Doing {len(sr_feeds)} S3 Salmon Run feeds")

		for feed in sr_feeds:
			img = discord.File(image_io, filename = "sr-feed.png", description = "Current S3 Salmon Run schedule")
			embed.set_image(url = "attachment://sr-feed.png")
			image_io.seek(0)

			await self.sendFeedMessage(feed['serverid'], feed['channelid'], file = img, embed = embed)

	async def doGearFeed(self, items):
		embed = discord.Embed(colour=0x0004FF)
		embed.title = "New gear in the Splatoon 3 Splatnet store"

		image_io = S3ImageBuilder.createFeedGearCard(items, self.fonts)

		embed = discord.Embed(colour=0x0004FF)
		embed.title = "New gear in Splatoon 3 Splatnet store"

		async with self.sqlBroker.context() as sql:
			gear_feeds = await sql.query("SELECT * from s3_feeds WHERE (gear = 1)")

		print(f"[S3FeedHandler] Doing {len(gear_feeds)} gear feeds")

		for feed in gear_feeds:
			img = discord.File(image_io, filename = "gear-feed.png", description = "New gear posted to Splatoon 3 Splatnet")
			embed.set_image(url = "attachment://gear-feed.png")
			image_io.seek(0)

			await self.sendFeedMessage(feed['serverid'], feed['channelid'], file = img, embed = embed)

	async def getFeed(self, serverid, channelid):
		async with self.sqlBroker.context() as sql:
			row = await sql.query_first("SELECT * FROM s3_feeds WHERE (serverid = %s) AND (channelid = %s)", (serverid, channelid))
			if row is None:
				return None

			feed = {'serverid': row['serverid'], 'channelid': row['channelid'], 'flags': {'maps': bool(row['maps']), 'sr': bool(row['sr']), 'gear': bool(row['gear'])}}
			return feed

	async def createFeed(self, serverid, channelid, flags):
		async with self.sqlBroker.context() as sql:
			await sql.query("REPLACE INTO s3_feeds (serverid, channelid, maps, sr, gear) VALUES (%s, %s, %s, %s, %s)", (serverid, channelid, int(flags['maps']), int(flags['sr']), int(flags['gear'])))
		return

	async def deleteFeed(self, serverid, channelid):
		async with self.sqlBroker.context() as sql:
			await sql.query("DELETE FROM s3_feeds WHERE (serverid = %s) AND (channelid = %s)", (serverid, channelid))
		return

	async def removeServer(self, serverid):
		async with self.sqlBroker.context() as sql:
			await sql.query("DELETE FROM s3_feeds WHERE (serverid = %s)", (serverid,))
		return
