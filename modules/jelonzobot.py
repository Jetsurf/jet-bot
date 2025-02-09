import urllib
import aiohttp
import asyncio
import time
import dateutil.parser
import re

class JelonzoBot:
	HOST = "splatoon.oatmealdome.me"

	COOP_STAGES =	{
		1:   {"stageid": "CoopStage-1", "name": "Spawning Grounds"},
    2:   {"stageid": "CoopStage-2", "name": "Sockeye Station"},
    4:   {"stageid": "CoopStage-4", "name": "Salmonid Smokeyard"},
    6:   {"stageid": "CoopStage-6", "name": "Marooner's Bay"},
    7:   {"stageid": "CoopStage-7", "name": "Gone Fission Hydroplant"},
    8:   {"stageid": "CoopStage-8", "name": "Jammin' Salmon Junction"},
    9:   {"stageid": "CoopStage-9", "name": "Bonerattle Arena"},
    100: {"stageid": "CoopStage-100", "name": "Wahoo World"},
    102: {"stageid": "CoopStage-102", "name": "Inkblot Art Academy"},
    103: {"stageid": "CoopStage-103", "name": "Undertow Spillway"},
    104: {"stageid": "CoopStage-104", "name": "Um'ami Ruins"},
    105: {"stageid": "CoopStage-105", "name": "Barnacle & Dime"},
    106: {"stageid": "CoopStage-106", "name": "Eeltail Alley"},
    107: {"stageid": "CoopStage-107", "name": "Grand Splatlands Bowl"},
	}

	VERSUS_STAGES = {
		1:  {"stageid": "VsStage-1", "name": "Scorch Gorge"},
		2:  {"stageid": "VsStage-2", "name": "Eeltail Alley"},
		3:  {"stageid": "VsStage-3", "name": "Hagglefish Market"},
		4:  {"stageid": "VsStage-4", "name": "Undertow Spillway"},
		5:  {"stageid": "VsStage-5", "name": "Um'ami Ruins"},
		6:  {"stageid": "VsStage-6", "name": "Mincemeat Metalworks"},
		7:  {"stageid": "VsStage-7", "name": "Brinewater Springs"},
		8:  {"stageid": "VsStage-8", "name": "Barnacle & Dime"},
		9:  {"stageid": "VsStage-9", "name": "Flounder Heights"},
		10: {"stageid": "VsStage-10", "name": "Hammerhead Bridge"},
		11: {"stageid": "VsStage-11", "name": "Museum d'Alfonsino"},
		12: {"stageid": "VsStage-12", "name": "Mahi-Mahi Resort"},
		13: {"stageid": "VsStage-13", "name": "Inkblot Art Academy"},
		14: {"stageid": "VsStage-14", "name": "Sturgeon Shipyard"},
		15: {"stageid": "VsStage-15", "name": "MakoMart"},
		16: {"stageid": "VsStage-16", "name": "Wahoo World"},
		17: {"stageid": "VsStage-17", "name": "Humpback Pump Track"},
		18: {"stageid": "VsStage-18", "name": "Manta Maria"},
		19: {"stageid": "VsStage-19", "name": "Crableg Capital"},
		20: {"stageid": "VsStage-20", "name": "Shipshape Cargo Co."},
		21: {"stageid": "VsStage-21", "name": "Robo ROM-en"},
		22: {"stageid": "VsStage-22", "name": "Bluefin Depot"},
		23: {"stageid": "VsStage-23", "name": "Marlin Airport"},
		24: {"stageid": "VsStage-24", "name": "Lemuria Hub"},
		25: {"stageid": "VsStage-25", "name": "Grand Splatlands Bowl"},
	}

	MODES = {
		'Paint': {"mode": "TURF_WAR"},
		'Area':  {"mode": "AREA"},
		'Clam':  {"mode": "CLAM"},
		'Lift':  {"mode": "LOFT"},
		'Goal':  {"mode": "GOAL"},
	}

	def __init__(self):
		self.rateLimit = {"remainingRequests": 1, "resetTime": time.time()}
		self.httpClient = aiohttp.ClientSession()
		self.queue = []
		self.worker = None

	def __del__(self):
		if self.worker is not None:
			self.worker.cancel()

		if self.httpClient:
			asyncio.create_task(self.httpClient.close())

	def constructUrl(self, path, args):
		url = "https://" + JelonzoBot.HOST + path

		delim = "?"
		for key in args:
			url += delim + urllib.parse.quote_plus(key) + "=" + urllib.parse.quote_plus(str(args[key]))
			delim = "&"

		return url

	def updateRateLimit(self, headers):
		remainingRequests = headers.get("x-rate-limit-remaining")
		if (remainingRequests is not None) and (re.match("^([0-9]+)$", remainingRequests)):
			self.rateLimit["remainingRequests"] = int(remainingRequests)

		resetTime = headers.get("x-rate-limit-reset")
		if resetTime is not None:
			self.rateLimit["resetTime"] = dateutil.parser.isoparse(resetTime).timestamp()

		print(self.rateLimit)
		return

	async def waitForRateLimit(self):
		if self.rateLimit["remainingRequests"] > 0:
			return

		now = time.time()
		resetTime = self.rateLimit["resetTime"]
		if resetTime is None:
			await asyncio.sleep(5)  # Unknown wait time?
			return
		elif resetTime < now:
			return	# We have already reached the reset time

	  # Wait until the reset time
		waitTime = resetTime - now
		print(f"Jelonzobot.waitForRateLimit(): Waiting {waitTime} due to rate limit...")
		await asyncio.sleep(waitTime)
		return

	async def doRequest(self, url):
		print(f"Performing request: {url}")

		headers = {'accept': 'application/json', 'user-agent': 'jet-bot/1.0 (discord:jetsurf#8514)'}
		response = await self.httpClient.get(url)

		self.updateRateLimit(response.headers)

		if response.status != 200:
			raise Exception("Jelonzobot.doRequest(): Unexpected HTTP status code: {response.status}")

		data = await response.json()
		return data

	async def processJobs(self):
		# Process each item from the queue
		while len(self.queue):
			await self.waitForRateLimit()

			job = self.queue.pop(0)

			url = self.constructUrl(job["path"], job["args"])

			try:
				result = await self.doRequest(url)
			except Exception as e:
				print(f"Jelonzobot.processJobs(): Exception during HTTP request: {e}")
				job["future"].set_exception(e)
				return

			if result:
				job["future"].set_result(result)
			else:
				job["future"].set_exception("Request failed")

		# All done
		self.worker = None
		return

	async def enqueue(self, job, loop = None):
		# Create a Future to hold the eventual result of the job
		loop = loop or asyncio.get_event_loop()
		future = loop.create_future()
		job["future"] = future

		# Add job to the queue
		self.queue.append(job)

		# Start a worker to process jobs from the queue, if necessary
		if self.worker is None:
			self.worker = asyncio.create_task(self.processJobs())

		return future

	async def getCoopPhases(self, count = 5):
		job = {"path": "/api/v1/three/coop/phases", "args": {"count": count}}
		future = await self.enqueue(job)
		result = await asyncio.wait_for(future, None)
		return result

	async def getVersusPhases(self, count = 5):
		job = {"path": "/api/v1/three/versus/phases", "args": {"count": count}}
		future = await self.enqueue(job)
		result = await asyncio.wait_for(future, None)
		return result

	def xlatCoopPhases(self, input):
		output = []

		for i in input["Normal"]:
			rot = {}
			rot["type"] = "COOP"
			rot["mode"] = "CoopNormalSetting"
			rot["starttime"] = dateutil.parser.isoparse(i["startTime"]).timestamp()
			rot["endtime"] = dateutil.parser.isoparse(i["endTime"]).timestamp()
			rot["maps"] = [ self.COOP_STAGES.get(i["stage"]) ]
			output.append(rot)

		for i in input["BigRun"]:
			rot = {}
			rot["type"] = "COOP"
			rot["mode"] = "CoopBigRunSetting"
			rot["starttime"] = dateutil.parser.isoparse(i["startTime"]).timestamp()
			rot["endtime"] = dateutil.parser.isoparse(i["endTime"]).timestamp()
			rot["maps"] = [ self.COOP_STAGES.get(i["stage"]) ]
			output.append(rot)

		output = sorted(output, key = lambda s: s['starttime'])

		return output

	def xlatVersusPhases(self, input):
		output = {"TW": [], "SO": [], "SP": [], "AO": [], "AS": [], "XB": [], "CH": []}

		# Pull in normal data
		for i in input.get('normal', []):
			starttime = dateutil.parser.isoparse(i["startTime"]).timestamp()
			endtime = dateutil.parser.isoparse(i["endTime"]).timestamp()
			if "Regular" in i:
				maps = [ self.VERSUS_STAGES.get(x) for x in i["Regular"]["stages"] ]
				rot = {"type": "VERSUS", "mode": "TURF_WAR", "starttime": starttime, "endtime": endtime, "maps": maps}
				output["TW"].append(rot)
			if ("BankaraOpen" in i) and (i["BankaraOpen"]["rule"] != 'None'):
				maps = [ self.VERSUS_STAGES.get(x) for x in i["BankaraOpen"]["stages"] ]
				rot = {"type": "VERSUS", "mode": self.MODES[i["BankaraOpen"]["rule"]]["mode"], "starttime": starttime, "endtime": endtime, "maps": maps}
				output["AO"].append(rot)
			if ("Bankara" in i) and (i["Bankara"]["rule"] != 'None'):
				maps = [ self.VERSUS_STAGES.get(x) for x in i["Bankara"]["stages"] ]
				rot = {"type": "VERSUS", "mode": self.MODES[i["Bankara"]["rule"]]["mode"], "starttime": starttime, "endtime": endtime, "maps": maps}
				output["AS"].append(rot)
			if ("X" in i) and (i["X"]["rule"] != 'None'):
				maps = [ self.VERSUS_STAGES.get(x) for x in i["X"]["stages"] ]
				rot = {"type": "VERSUS", "mode": self.MODES[i["X"]["rule"]]["mode"], "starttime": starttime, "endtime": endtime, "maps": maps}
				output["XB"].append(rot)
			if ("League" in i) and (i["League"]["rule"] != 'None'):
				maps = [ self.VERSUS_STAGES.get(x) for x in i["League"]["stages"] ]
				rot = {"type": "VERSUS", "mode": self.MODES[i["League"]["rule"]]["mode"], "starttime": starttime, "endtime": endtime, "maps": maps}
				output["CH"].append(rot)

		# Pull splatfest data
		if (fests := input.get('fest')) and len(fests.keys()):
			fest = fests[list(fests.keys())[0]]
			for f in fest:
				starttime = dateutil.parser.isoparse(f["startTime"]).timestamp()
				endtime = dateutil.parser.isoparse(f["endTime"]).timestamp()
				if "FestRegular" in f:
					maps = [ self.VERSUS_STAGES.get(x) for x in f["FestRegular"]["stages"] ]
					rot = {"type": "VERSUS", "mode": "TURF_WAR", "starttime": starttime, "endtime": endtime, "maps": maps}
					output["SO"].append(rot)
				if "FestChallenge" in f:
					maps = [ self.VERSUS_STAGES.get(x) for x in f["FestChallenge"]["stages"] ]
					rot = {"type": "VERSUS", "mode": "TURF_WAR", "starttime": starttime, "endtime": endtime, "maps": maps}
					output["SP"].append(rot)

		# Sort each schedule by starting time
		for schedule in output:
			output[schedule] = sorted(output[schedule], key = lambda s: s['starttime'])

		return output
