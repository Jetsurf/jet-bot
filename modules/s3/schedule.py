import discord
import asyncio
import aiohttp
import time
import json
import requests
import dateutil.parser
import hashlib
import base64, traceback
import jelonzobot

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import apscheduler.triggers.cron
import apscheduler.triggers.interval

class S3Schedule():
	schedule_choices = [
		discord.OptionChoice('Turf War', 'TW'),
		discord.OptionChoice('Splatfest Open', 'SO'),
		discord.OptionChoice('Splatfest Pro', 'SP'),
		discord.OptionChoice('Anarchy Open', 'AO'),
		discord.OptionChoice('Anarchy Series', 'AS'),
		discord.OptionChoice('Challenge', 'CH'),
		discord.OptionChoice('X Battles', 'XB'),
		discord.OptionChoice('Salmon Run', 'SR'),
	]

	schedule_names = {
		'TW': 'Turf War',
		'SO': 'Splatfest Open',
		'SP': 'Splatfest Pro',
		'AO': 'Anarchy Open',
		'AS': 'Anarchy Series',
		'CH': 'Challenge',
		'SR': 'Salmon Run',
		'XB': 'X Battles',
	}

	schedule_types = {
		'TW': 'VERSUS',
		'SO': 'VERSUS',
		'SP': 'VERSUS',
		'AO': 'VERSUS',
		'AS': 'VERSUS',
		'CH': 'VERSUS',
		'XB': 'VERSUS',
		'SR': 'COOP',
	}

	def __init__(self, nsotoken, sqlBroker, cachemanager):
		self.nsotoken = nsotoken
		self.sqlBroker = sqlBroker
		self.updatetime = None
		self.image_cache_small = cachemanager.open("s3.maps.small")

		self.image_cache_sr_maps = cachemanager.open("s3.sr.maps")
		self.image_cache_sr_weapons = cachemanager.open("s3.sr.weapons")

		self.schedules = {}
		for k in self.schedule_names.keys():
			self.schedules[k] = []

		self.rotations = {}

		self.callbacks = {'COOP': [], 'VERSUS': []}

		# Schedule jobs
		self.scheduler = AsyncIOScheduler()
		self.scheduler.add_job(self.update, apscheduler.triggers.interval.IntervalTrigger(minutes = 60))
		self.scheduler.add_job(self.check_rotations, apscheduler.triggers.cron.CronTrigger(hour="*/1", minute='0', second='10', timezone='UTC'))
		#self.scheduler.add_job(self.check_rotations, apscheduler.triggers.cron.CronTrigger(hour="*/1", minute='*/1', second='10', timezone='UTC'))
		self.scheduler.start()

		# Do async startup
		asyncio.create_task(self.startup())

	async def startup(self):
		await self.sqlBroker.wait_for_startup()
		await self.load()
		await self.update()

	def on_versus_update(self, callback):
		self.callbacks['VERSUS'].append(callback)

	def on_coop_update(self, callback):
		self.callbacks['COOP'].append(callback)

	def run_callbacks(self, type):
		print(f"[S3Schedule] Running schedule rotation callbacks for: {type}")
		for cb in self.callbacks[type]:
			cb()

	def is_update_needed(self):
		if self.updatetime is None:
			return True

		if time.time() - self.updatetime > (30 * 60):  # At least 30 minutes
			return True

		return False

	def get_schedule(self, name, checktime = None, count = 1):
		schedule = self.schedules[name]

		if checktime == None:
			checktime = time.time()

		index = None
		for i in range(len(schedule)):
			if schedule[i]['endtime'] > checktime:
				index = i
				break

		if index is None:
			return []  # None found

		return schedule[index:index + count]

	# Sets the current rotations. Call once on startup.
	def set_initial_rotations(self, settime = None):
		if settime == None:
			settime = time.time()

		for k in self.schedules.keys():
			schedule = self.schedules[k]
			for i in range(len(schedule)):
				if (schedule[i]['starttime'] <= settime) and (schedule[i]['endtime'] >= settime):
					self.rotations[k] = schedule[i]['starttime']
					break

		print(f"[S3Schedule] set_initial_rotations(): initial rotations {self.rotations}")

	# Updates our notion of the current rotation and runs callbacks.
	def check_rotations(self, checktime = None):
		if checktime == None:
			checktime = time.time()

		# Check for rotation updates
		updates = []
		for k in self.schedules.keys():
			schedule = self.schedules[k]
			for i in range(len(schedule)):
				if (schedule[i]['starttime'] <= checktime) and (schedule[i]['endtime'] >= checktime):
					rotation = schedule[i]
					if (not k in self.rotations) or (rotation['starttime'] != self.rotations[k]):
						updates.append(k)
						self.rotations[k] = rotation['starttime']

		if len(updates) == 0:
			return

		print(f"[S3Schedule] check_rotations(): New rotations: {updates}")

		# Figure to rotation types to trigger callbacks for
		types = set()
		for u in updates:
			if u in self.schedule_types:
				types.add(self.schedule_types[u])

		# Run callbacks
		for t in types:
			self.run_callbacks(t)

	# Given 'vsStages' object, returns a list of maps
	def parse_maps(self, data):
		maps = []
		for vs in data:
			map = {}
			map['image']   = vs['image']['url']
			map['name']    = vs['name']
			map['stageid'] = base64.b64decode(vs['id']).decode("utf-8")
			maps.append(map)
		return maps

	# Given 'coopStage' object, returns the map
	def parse_salmon_map(self, data):
		map = {}
		map['image']   = data['image']['url']
		map['stageid'] = base64.b64decode(data['id']).decode("utf-8")
		map['name']    = data['name']
		return map

	def parse_salmon_weapons(self, weapon_data):
		weapons = []
		for w in weapon_data:
			weapon = {}
			weapon['name'] = w['name']
			weapon['image']  = w['image']['url']
			weapons.append(weapon)
		return weapons

	def parse_schedule_turf(self, settings, rec):
		rec['mode'] = settings['vsRule']['rule']
		rec['maps'] = self.parse_maps(settings['vsStages'])

	def parse_schedule_fest_open(self, settings, rec):
		settings = [ s for s in settings if s['festMode'] == 'REGULAR' ][0]
		rec['mode'] = settings['vsRule']['rule']
		rec['maps'] = self.parse_maps(settings['vsStages'])

	def parse_schedule_fest_pro(self, settings, rec):
		settings = [ s for s in settings if s['festMode'] == 'CHALLENGE' ][0]
		rec['mode'] = settings['vsRule']['rule']
		rec['maps'] = self.parse_maps(settings['vsStages'])

	def parse_schedule_anarchy_open(self, settings, rec):
		settings = [ s for s in settings if s['bankaraMode'] == 'OPEN' ][0]
		rec['mode'] = settings['vsRule']['rule']
		rec['maps'] = self.parse_maps(settings['vsStages'])

	def parse_schedule_anarchy_series(self, settings, rec):
		settings = [ s for s in settings if s['bankaraMode'] == 'CHALLENGE' ][0]
		rec['mode'] = settings['vsRule']['rule']
		rec['maps'] = self.parse_maps(settings['vsStages'])

	def parse_schedule_challenge(self, settings, rec):
		rec['mode'] = settings['vsRule']['rule']
		rec['maps'] = self.parse_maps(settings['vsStages'])
		rec['event'] = settings['leagueMatchEvent']

	def parse_schedule_x_battles(self, settings, rec):
		rec['mode'] = settings['vsRule']['rule']
		rec['maps'] = self.parse_maps(settings['vsStages'])

	def parse_versus_schedule(self, data, key, sub):
		if not data or not data.get('nodes'):
			return []  # Empty

		nodes = data.get('nodes')

		recs = []
		for node in nodes:
			if node.get(key) is None:
				continue  # Nothing scheduled in this timeslot

			rec = {}
			rec['type']      = 'VERSUS'
			rec['starttime'] = dateutil.parser.isoparse(node['startTime']).timestamp()
			rec['endtime']   = dateutil.parser.isoparse(node['endTime']).timestamp()
			sub(node[key], rec)
			recs.append(rec)

		return recs

	# These event ("challenge") records need a special parser because records can have multiple timeslots
	def parse_event_schedule(self, data):
		if not data or not data.get('nodes'):
			return []  # Empty

		nodes = data.get('nodes')

		recs = []
		for node in nodes:
			settings = node["leagueMatchSetting"]

			info = {}
			info['type'] = 'VERSUS'
			info['mode'] = settings['vsRule']['rule']
			info['desc'] = settings['leagueMatchEvent']['desc']
			info['maps'] = self.parse_maps(settings['vsStages'])

			for t in node['timePeriods']:
				rec = info.copy()
				rec['starttime'] = dateutil.parser.isoparse(t['startTime']).timestamp()
				rec['endtime']   = dateutil.parser.isoparse(t['endTime']).timestamp()
				recs.append(rec)

		return recs

	def parse_salmon_schedule(self, data):
		if not data or not data.get('nodes'):
			return []  # Empty

		nodes = data.get('nodes')

		recs = []
		for node in nodes:
			if node.get('setting') is None:
				continue  # Nothing scheduled in this timeslot

			rec = {}
			rec['type']      = 'COOP'
			rec['mode']      = node['setting']['__typename']
			rec['starttime'] = dateutil.parser.isoparse(node['startTime']).timestamp()
			rec['endtime']   = dateutil.parser.isoparse(node['endTime']).timestamp()
			rec['maps']      = [ self.parse_salmon_map(node['setting']['coopStage']) ]
			rec['weapons']   = self.parse_salmon_weapons(node['setting']['weapons'])
			recs.append(rec)

		return recs

	async def update(self):
		if not self.is_update_needed():
			return

		await self.sqlBroker.wait_for_startup()

		#nso = await self.nsotoken.get_bot_nso_client()
		#if not nso:
		#	return  # No bot account configured
		#elif not nso.is_logged_in():
		#	print("[S3Schedule] update(): Time to update but the bot account is not logged in")
		#	return

		print("[S3Schedule] update(): Updating schedule")
		#data = nso.s3.get_stage_schedule()
		#if data is None:
		#	print("[S3Schedule] update(): Failed to retrieve schedule")
		#	return

		jbot = jelonzobot.JelonzoBot()

		coop = await jbot.getCoopPhases()
		if coop:
			self.schedules['SR'] = jbot.xlatCoopPhases(coop)

		versus = await jbot.getVersusPhases()
		if versus:
			versus = jbot.xlatVersusPhases(versus)
			self.schedules['TW'] = versus['TW']
			self.schedules['SO'] = versus['SO']
			self.schedules['SP'] = versus['SP']
			self.schedules['AO'] = versus['AO']
			self.schedules['AS'] = versus['AS']
			self.schedules['XB'] = versus['XB']
			self.schedules['CH'] = versus['CH']

		#self.schedules['TW'] = self.parse_versus_schedule(data['data'].get('regularSchedules'), 'regularMatchSetting', self.parse_schedule_turf)
		#self.schedules['SO'] = self.parse_versus_schedule(data['data'].get('festSchedules'), 'festMatchSettings', self.parse_schedule_fest_open)
		#self.schedules['SP'] = self.parse_versus_schedule(data['data'].get('festSchedules'), 'festMatchSettings', self.parse_schedule_fest_pro)
		#self.schedules['AO'] = self.parse_versus_schedule(data['data'].get('bankaraSchedules'), 'bankaraMatchSettings', self.parse_schedule_anarchy_open)
		#self.schedules['AS'] = self.parse_versus_schedule(data['data'].get('bankaraSchedules'), 'bankaraMatchSettings', self.parse_schedule_anarchy_series)
		#self.schedules['XB'] = self.parse_versus_schedule(data['data'].get('xSchedules'), 'xMatchSetting', self.parse_schedule_x_battles)

		#self.schedules['CH'] = self.parse_event_schedule(data['data'].get('eventSchedules'))

		#self.schedules['SR'] = self.parse_salmon_schedule(data['data'].get('coopGroupingSchedule', {}).get('regularSchedules'))

		## If Big Run schedules are included, parse them and insert them into the regular SR schedule
		#if big_run_data := data['data'].get('coopGroupingSchedule', {}).get('bigRunSchedules'):
		#	big_run_schedule = self.parse_salmon_schedule(big_run_data)
		#	self.schedules['SR'] = sorted([*self.schedules['SR'], *big_run_schedule], key = lambda s: s['starttime'])

		self.updatetime = time.time()

		await self.save()

		await self.cache_images()

	async def save(self):
		async with self.sqlBroker.context() as sql:
			await sql.query("DELETE FROM s3_schedule_update")
			await sql.query("INSERT INTO s3_schedule_update (updatetime) VALUES (FROM_UNIXTIME(%s))", (self.updatetime,))

			for s in self.schedule_names.keys():
				await sql.query("DELETE FROM s3_schedule_periods WHERE (schedule = %s)", (s,))
				for rec in self.schedules[s]:
					await sql.query("INSERT INTO s3_schedule_periods (schedule, starttime, endtime, jsondata) VALUES (%s, FROM_UNIXTIME(%s), FROM_UNIXTIME(%s), %s)", (s, rec['starttime'], rec['endtime'], json.dumps(rec)))

	async def load(self):
		async with self.sqlBroker.context() as sql:
			updaterow = await sql.query_first("SELECT UNIX_TIMESTAMP(updatetime) AS updatetime FROM s3_schedule_update")

			schedules = {}
			rows = await sql.query("SELECT schedule, jsondata FROM s3_schedule_periods")
			for row in rows:
				if not row['schedule'] in schedules:
					schedules[row['schedule']] = []
				schedules[row['schedule']].append(json.loads(row['jsondata']))

			for s in self.schedule_names.keys():
				if not s in schedules:
					schedules[s] = []

			self.schedules = schedules
			self.updatetime = updaterow['updatetime'] if updaterow else None

			self.set_initial_rotations()

	async def cache_images(self):
		# PvP
		for k in ['TW', 'SO', 'SP', 'AO', 'AS', 'CH', 'XB']:

			for rec in self.schedules[k]:
				for map in rec['maps']:
					if (not map.get('stageid')) or (not map.get('image')):
						continue  # Missing required fields

					key = f"{map['stageid']}.png"
					if self.image_cache_small.is_fresh(key):
						continue  # Already fresh

					print(f"[S3Schedule] Caching map image stageid {map['stageid']} name '{map['name']}' image-url {map['image']}")
					await self.image_cache_small.add_url(key, map['image'])

		# Salmon run
		for k in ['SR']:
			for rec in self.schedules[k]:
				for map in rec['maps']:
					if (not map.get('stageid')) or (not map.get('image')):
						continue  # Missing required fields

					key = f"{map['stageid']}.png"
					if self.image_cache_sr_maps.is_fresh(key):
						continue  # Already fresh

					print(f"[S3Schedule] Caching SR map image stageid {map['stageid']} name '{map['name']}' image-url {map['image']}")
					await self.image_cache_sr_maps.add_url(key, map['image'])

				for weapon in rec.get('weapons', []):
					if (not weapon['name']) or (not weapon['image']):
						continue  # Missing required fields

					key = f"weapon-{hashlib.sha1(weapon['name'].encode('utf-8')).hexdigest()}.png"
					if self.image_cache_sr_weapons.is_fresh(key):
						continue  # Already fresh

					print(f"[S3Schedule] Caching SR weapon name '{weapon['name']}' key '{key}' image-url {weapon['image']}")
					await self.image_cache_sr_weapons.add_url(key, weapon['image'])
