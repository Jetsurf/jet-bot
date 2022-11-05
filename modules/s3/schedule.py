import discord
import asyncio
import time
import requests
import dateutil.parser

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

		self.turf_war_schedule       = []
		self.splatfest_schedule      = []
		self.anarchy_open_schedule   = []
		self.anarchy_series_schedule = []

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
			map['stageid'] = vs['vsStageId']
			maps.append(map)
		return maps

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

		self.cache_map_images()

		self.updatetime = time.time()

	def cache_map_images(self):
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

