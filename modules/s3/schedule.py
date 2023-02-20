import discord
import asyncio
import time
import json
import requests
import dateutil.parser
import hashlib
import base64, traceback

from apscheduler.schedulers.asyncio import AsyncIOScheduler

class S3Schedule():
	schedule_choices = [
		discord.OptionChoice('Turf War', 'TW'),
		discord.OptionChoice('Splatfest', 'SF'),
		discord.OptionChoice('Anarchy Open', 'AO'),
		discord.OptionChoice('Anarchy Series', 'AS'),
		discord.OptionChoice('X Battles', 'XB'),
		discord.OptionChoice('Salmon Run', 'SR'),
	]

	schedule_names = {
		'TW': 'Turf War',
		'SF': 'Splatfest',
		'AO': 'Anarchy Open',
		'AS': 'Anarchy Series',
		'SR': 'Salmon Run',
		'XB': 'X Battles',
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

		# Schedule updates every hour
		self.scheduler = AsyncIOScheduler()
		self.scheduler.add_job(self.update, 'interval', minutes = 60)
		self.scheduler.start()

		# Do async startup
		asyncio.create_task(self.startup())

	async def startup(self):
		await self.sqlBroker.wait_for_startup()
		await self.load()
		await self.update()

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

	def parse_schedule_fest(self, settings, rec):
		rec['mode'] = settings['vsRule']['rule']
		rec['maps'] = self.parse_maps(settings['vsStages'])

	def parse_schedule_anarchy_open(self, settings, rec):
		settings = [ s for s in settings if s['mode'] == 'OPEN' ][0]
		rec['mode'] = settings['vsRule']['rule']
		rec['maps'] = self.parse_maps(settings['vsStages'])

	def parse_schedule_anarchy_series(self, settings, rec):
		settings = [ s for s in settings if s['mode'] == 'CHALLENGE' ][0]
		rec['mode'] = settings['vsRule']['rule']
		rec['maps'] = self.parse_maps(settings['vsStages'])

	def parse_schedule_x_battles(self, settings, rec):
		rec['mode'] = settings['vsRule']['rule']
		rec['maps'] = self.parse_maps(settings['vsStages'])

	def parse_versus_schedule(self, data, key, sub):
		if not data or not data.get('nodes'):
			return []  # Empty

		nodes = data.get('nodes')

		recs = []
		for node in nodes:
			if node[key] is None:
				continue  # Nothing scheduled in this timeslot

			rec = {}
			rec['type']      = 'VERSUS'
			rec['starttime'] = dateutil.parser.isoparse(node['startTime']).timestamp()
			rec['endtime']   = dateutil.parser.isoparse(node['endTime']).timestamp()
			sub(node[key], rec)
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

		nso = await self.nsotoken.get_bot_nso_client()
		if not nso:
			return  # No bot account configured
		elif not nso.is_logged_in():
			print("S3Schedule.update(): Time to update but the bot account is not logged in")
			return

		print("S3Schedule.update(): Updating schedule")
		data = nso.s3.get_stage_schedule()
		if data is None:
			print("S3Schedule.update(): Failed to retrieve schedule")
			return

		self.schedules['TW'] = self.parse_versus_schedule(data['data'].get('regularSchedules'), 'regularMatchSetting', self.parse_schedule_turf)
		self.schedules['SF'] = self.parse_versus_schedule(data['data'].get('festSchedules'), 'festMatchSetting', self.parse_schedule_fest)
		self.schedules['AO'] = self.parse_versus_schedule(data['data'].get('bankaraSchedules'), 'bankaraMatchSettings', self.parse_schedule_anarchy_open)
		self.schedules['AS'] = self.parse_versus_schedule(data['data'].get('bankaraSchedules'), 'bankaraMatchSettings', self.parse_schedule_anarchy_series)
		self.schedules['XB'] = self.parse_versus_schedule(data['data'].get('xSchedules'), 'xMatchSetting', self.parse_schedule_x_battles)

		self.schedules['SR'] = self.parse_salmon_schedule(data['data'].get('coopGroupingSchedule', {}).get('regularSchedules'))

		# If Big Run schedules are included, parse them and insert them into the regular SR schedule
		if big_run_data := data['data'].get('coopGroupingSchedule', {}).get('bigRunSchedules'):
			big_run_schedule = self.parse_salmon_schedule(big_run_data)
			self.schedules['SR'] = sorted([*self.schedules['SR'], *big_run_schedule], key = lambda s: s['starttime'])

		self.updatetime = time.time()

		await self.save()

		self.cache_images()

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
			self.updatetime = updaterow['updatetime']

	def cache_images(self):
		# PvP
		for k in ['TW', 'SF', 'AO', 'AS', 'XB']:
			for rec in self.schedules[k]:
				for map in rec['maps']:
					if (not map['stageid']) or (not map['image']):
						continue  # Missing required fields

					key = f"{map['stageid']}.png"
					if self.image_cache_small.is_fresh(key):
						continue  # Already fresh

					print(f"Caching map image stageid {map['stageid']} name '{map['name']}' image-url {map['image']}")
					response = requests.get(map['image'], stream=True)
					self.image_cache_small.add_http_response(key, response)


		# Salmon run
		for k in ['SR']:
			for rec in self.schedules[k]:
				for map in rec['maps']:
					if (not map['stageid']) or (not map['image']):
						continue  # Missing required fields

					key = f"{map['stageid']}.png"
					if self.image_cache_sr_maps.is_fresh(key):
						continue  # Already fresh

					print(f"Caching SR map image stageid {map['stageid']} name '{map['name']}' image-url {map['image']}")
					response = requests.get(map['image'], stream=True)
					self.image_cache_sr_maps.add_http_response(key, response)

				for weapon in rec['weapons']:
					if (not weapon['name']) or (not weapon['image']):
						continue  # Missing required fields

					key = f"weapon-{hashlib.sha1(weapon['name'].encode('utf-8')).hexdigest()}.png"
					if self.image_cache_sr_weapons.is_fresh(key):
						continue  # Already fresh

					print(f"Caching SR weapon name '{weapon['name']}' key '{key}' image-url {weapon['image']}")
					response = requests.get(weapon['image'], stream=True)
					self.image_cache_sr_weapons.add_http_response(key, response)
