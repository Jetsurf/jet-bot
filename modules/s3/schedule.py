import discord
import asyncio
import time
import requests
import dateutil.parser
import hashlib
import base64

from apscheduler.schedulers.asyncio import AsyncIOScheduler

class S3Schedule():
	schedule_choices = [
		discord.OptionChoice('Turf War', 'TW'),
		discord.OptionChoice('Splatfest', 'SF'),
		discord.OptionChoice('Anarchy Open', 'AO'),
		discord.OptionChoice('Anarchy Series', 'AS'),
	]

	schedule_properties = {
		'TW': 'turf_war_schedule',
		'SF': 'splatfest_schedule',
		'AO': 'anarchy_open_schedule',
		'AS': 'anarchy_series_schedule',
	}

	schedule_names = {
		'TW': 'Turf War',
		'SF': 'Splatfest',
		'AO': 'Anarchy Open',
		'AS': 'Anarchy Series',
	}

	def __init__(self, nsotoken, sqlBroker, cachemanager):
		self.nsotoken = nsotoken
		self.sqlBroker = sqlBroker
		self.updatetime = None
		self.image_cache_small = cachemanager.open("s3.maps.small", (3600 * 24 * 90))  # Cache for 90 days

		self.image_cache_sr_maps = cachemanager.open("s3.sr.maps", (3600 * 24 * 90))  # Cache for 90 days
		self.image_cache_sr_weapons = cachemanager.open("s3.sr.weapons", (3600 * 24 * 90))  # Cache for 90 days

		self.turf_war_schedule       = []
		self.splatfest_schedule      = []
		self.anarchy_open_schedule   = []
		self.anarchy_series_schedule = []

		self.salmon_run_schedule     = []

		# Schedule updates every hour
		self.scheduler = AsyncIOScheduler()
		self.scheduler.add_job(self.update, 'interval', minutes = 60)
		self.scheduler.start()

		# Update shortly after bot startup
		asyncio.create_task(self.update())

	def is_update_needed(self):
		if self.updatetime is None:
			return True

		if time.time() - self.updatetime > (30 * 60):  # At least 30 minutes
			return True

		return False

	def get_schedule(self, name, checktime = None, count = 1):
		property = self.schedule_properties[name]
		schedule = getattr(self, self.schedule_properties[name])

		if checktime == None:
			checktime = time.time()

		index = None
		for i in range(len(schedule)):
			if schedule[i]['starttime'] < checktime:
				index = i
				break

		if index is None:
			return []  # None found

		return schedule[index:index + count]

#	def get_turf_schedule(self, checktime = None, count = 1):
#		return self.get_schedule('TW', *kwargs)
#
#	def get_fest_schedule(self, checktime = None, count = 1):
#		return self.get_schedule('SF', *kwargs)
#
#	def get_anarchy_open_schedule(self, checktime = None, count = 1):
#		return self.get_schedule('AO', *kwargs)
#
#	def get_anarchy_series_schedule(self, checktime = None, count = 1):
#		return self.get_schedule('AS', *kwargs)

	# Given 'vsStages' object, returns a list of maps
	def parse_maps(self, data):
		maps = []
		for vs in data:
			map = {}
			map['image']   = vs['image']['url']
			map['name']    = vs['name']
			map['stageid'] = vs['vsStageId']  # TODO: Use base64 of 'id' field instead?
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
		rec['mode'] = settings['vsRule']['name']
		rec['maps'] = self.parse_maps(settings['vsStages'])

	def parse_schedule_fest(self, settings, rec):
		rec['mode'] = settings['vsRule']['name']
		rec['maps'] = self.parse_maps(settings['vsStages'])

	def parse_schedule_anarchy_open(self, settings, rec):
		settings = [ s for s in settings if s['mode'] == 'OPEN' ][0]
		rec['mode'] = settings['vsRule']['name']
		rec['maps'] = self.parse_maps(settings['vsStages'])

	def parse_schedule_anarchy_series(self, settings, rec):
		settings = [ s for s in settings if s['mode'] == 'CHALLENGE' ][0]
		rec['mode'] = settings['vsRule']['name']
		rec['maps'] = self.parse_maps(settings['vsStages'])

	def parse_schedule(self, data, key, sub):
		if not data or not data.get('nodes'):
			return []  # Empty

		nodes = data.get('nodes')

		recs = []
		for node in nodes:
			if node[key] is None:
				continue  # Nothing scheduled in this timeslot

			rec = {}
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

		self.turf_war_schedule       = self.parse_schedule(data['data'].get('regularSchedules'), 'regularMatchSetting', self.parse_schedule_turf)
		self.splatfest_schedule      = self.parse_schedule(data['data'].get('festSchedules'), 'festMatchSetting', self.parse_schedule_fest)
		self.anarchy_open_schedule   = self.parse_schedule(data['data'].get('bankaraSchedules'), 'bankaraMatchSettings', self.parse_schedule_anarchy_open)
		self.anarchy_series_schedule = self.parse_schedule(data['data'].get('bankaraSchedules'), 'bankaraMatchSettings', self.parse_schedule_anarchy_series)

		self.salmon_run_schedule = self.parse_salmon_schedule(data['data'].get('coopGroupingSchedule', {}).get('regularSchedules'))

		self.cache_images()

		self.updatetime = time.time()

	def cache_images(self):
		# PvP
		for rec in [*self.turf_war_schedule, *self.splatfest_schedule, *self.anarchy_open_schedule, *self.anarchy_series_schedule]:
			for map in rec['maps']:
				if (not map['stageid']) or (not map['image']):
					continue  # Missing required fields

				key = f"stage-{map['stageid']}.png"
				if self.image_cache_small.has(key):
					continue  # Already cached

				print(f"Caching map image stageid {map['stageid']} name '{map['name']}' image-url {map['image']}")
				response = requests.get(map['image'], stream=True)
				self.image_cache_small.add_http_response(key, response)


		# Salmon run
		for rec in self.salmon_run_schedule:
			for map in rec['maps']:
				if (not map['stageid']) or (not map['image']):
					continue  # Missing required fields

				key = f"{map['stageid']}.png"
				if self.image_cache_sr_maps.has(key):
					continue  # Already cached

				print(f"Caching SR map image stageid {map['stageid']} name '{map['name']}' image-url {map['image']}")
				response = requests.get(map['image'], stream=True)
				self.image_cache_salmon_maps.add_http_response(key, response)

			for weapon in rec['weapons']:
				if (not weapon['name']) or (not weapon['image']):
					continue  # Missing required fields

				key = f"weapon-{hashlib.sha1(weapon['name'].encode('utf-8')).hexdigest()}.png"
				if self.image_cache_sr_weapons.has(key):
					continue  # Already cached

				print(f"Caching SR weapon name '{weapon['name']}' key '{key}' image-url {weapon['image']}")
				response = requests.get(weapon['image'], stream=True)
				self.image_cache_sr_weapons.add_http_response(key, response)
