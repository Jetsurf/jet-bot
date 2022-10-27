import discord, asyncio
import mysqlhandler, nsotoken
import json, sys, re, time, requests, random, hashlib, os, io
import s3.storedm

from apscheduler.schedulers.asyncio import AsyncIOScheduler

#Image Editing
from PIL import Image, ImageFont, ImageDraw 
from io import BytesIO
from os.path import exists
import base64
import datetime
import dateutil.parser

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
				if not response.ok:
					print(f"  Error reading map image: {response.status_code} {response.reason}")
					continue

				self.image_cache_small.add_http_response(key, response)

class S3Utils():
	@classmethod
	def createBattleDetailsEmbed(cls, details):
		embed = discord.Embed(colour=0x0004FF)
		playerName = details['data']['vsHistoryDetail']['player']['name']
		type = details['data']['vsHistoryDetail']['vsMode']['mode']
		mode = details['data']['vsHistoryDetail']['vsRule']['name']
		judgement = details['data']['vsHistoryDetail']['judgement']
		playerId = details['data']['vsHistoryDetail']['player']['id']


		typeNames = {"BANKARA": "Anarchy Battle", "FEST": "Splatfest", "X": "X", "LEAGUE": "League", "PRIVATE": "Private Battle"}
		judgementNames = {"WIN": "Win", "LOSS": "Loss", "DEEMED_LOSE": "Loss due to early disconnect", "DRAW": "Draw"}

		myTeam = details['data']['vsHistoryDetail']['myTeam']
		otherTeams = details['data']['vsHistoryDetail']['otherTeams']

		embed.title = f"Stats for {playerName}'s last battle - {typeNames.get(type, type)} - {mode} (Kills(Assists)/Deaths/Specials)"

		cls.createBattleDetailsTeamEmbed(embed, "My Team", myTeam)

		for t in otherTeams:
			cls.createBattleDetailsTeamEmbed(embed, "Opposing Team", t)

		embed.set_footer(text=f"Judgement {judgementNames.get(judgement, judgement)}")
		return embed

	@classmethod
	def createBattleDetailsTeamEmbed(cls, embed, name, team):
		stats = []
		for p in team['players']:
			result = p['result']

			if result is None:
				stats.append("%s \u2014 %s \u2014 (disconnect)" % (p['weapon']['name'], discord.utils.escape_markdown(p['name']),))
			else:
				stats.append("%s \u2014 %s \u2014 %d(%d)/%d/%d paint %d" % (p['weapon']['name'], discord.utils.escape_markdown(p['name']), result['kill'], result['assist'], result['death'], result['special'], p['paint']))
		embed.add_field(name = name, value = "\n".join(stats), inline = False)

	@classmethod
	def createSplatfestEmbed(cls, splatfest):
		now = datetime.datetime.now(datetime.timezone.utc)

		starttime = dateutil.parser.isoparse(splatfest['startTime'])
		endtime   = dateutil.parser.isoparse(splatfest['endTime'])

		state = splatfest.get('state')

		description = ""
		if state == 'FIRST_HALF':
			description += "Currently in first half.\n"
		elif state == 'SECOND_HALF':
			description += "Currently in second half.\n"

		if starttime > now:
			description += f"Starts at <t:{int(starttime.timestamp())}> (<t:{int(starttime.timestamp())}:R>)\n"
		elif endtime > now:
			description += f"Ends at <t:{int(endtime.timestamp())}> (<t:{int(endtime.timestamp())}:R>)\n"
		else:
			description += f"Ended at <t:{int(endtime.timestamp())}>\n"

		embed = discord.Embed(colour=0x0004FF, description = description)
		embed.title = splatfest['title']
		embed.set_image(url = splatfest['image']['url'])

		for t in splatfest['teams']:
			id = base64.b64decode(t['id']).decode("utf-8")
			which = re.sub('^.*:', '', id)
			winner = False
			if t.get('result'):
				winner = t['result'].get('isWinner', False)
			text = t['teamName']
			if winner:
				text += "\n**Winner!**"

			embed.add_field(name = f'Team {which}', value = text)

		return embed


	@classmethod
	def createSalmonRunResultsEmbed(cls, results):
		embed = discord.Embed(colour=0x0004FF)
		historyGroups = results['data']['coopResult']['historyGroups']['nodes']
		stats = results['data']['coopResult']
		pointCard = results['data']['coopResult']['pointCard']
		embed.title = f"{lastGameDetails['afterGrade']['name']} - {stats['regularGradePoint']}"
		embed.add_field(name = "Totals", value = f"Shifts Worked: {pointCard['playCount']}\nPower Eggs: {pointCard['deliverCount']}\nGolden Eggs: {pointCard['goldenDeliverCount']}\nTotal Points: {pointCard['totalPoint']}\nKing Salmonoid Kills: {pointCard['defeatBossCount']}", inline = True)
		embed.add_field(name = "Scales", value = f"Bronze: {stats['scale']['bronze']}\nSilver: {stats['scale']['silver']}\nGold:{stats['scale']['gold']}", inline = True)
		
		bossSeen = 0
		bossDowns = 0
		clears = 0
		pwrEggTotal = 0
		gldEggTotal = 0
		matches = 0
		for group in historyGroups:
			#Here for checking highest results
			for match in group['historyDetails']['nodes']:
				if match['bossResult'] != None:
					bossSeen += 1
					if match['bossResult']['hasDefeatBoss']:
						bossDowns += 1

				pwrEggTotal += match['myResult']['deliverCount']
				gldEggTotal += match['myResult']['goldenDeliverCount']
				if match['gradePointDiff'] == 'UP':
					clears += 1
				matches += 1

		#embed.add_field(name = f"Average Stats (Last {matches})", value = "STUFF", inline = True)
		embed.add_field(name = f"Total Stats (Last {matches})", value = f"King Salmonoids Seen: {bossSeen}\nKing Salmonids Clears: {bossDowns}\nGolden Eggs: {gldEggTotal}\nPower Eggs: {pwrEggTotal}", inline = True)

		return embed

	@classmethod
	def createGearSubsEmbed(cls, embed, gear):
		out = []
		out.append(f"Main: {gear['primaryGearPower']['name']}")
		for sub in gear['additionalGearPowers']:
			out.append(f"Sub: {sub['name']}")

		embed.add_field(name=f"{gear['__isGear'].replace('Gear', '')} - {gear['name']}", value="\n".join(out))

	@classmethod
	def createMultiplayerStatsEmbed(cls, statssimple, statsfull, species):
		embed = discord.Embed(colour=0x0004FF)
		name = statsfull['data']['currentPlayer']['name']
		id = statsfull['data']['currentPlayer']['nameId']
		shoes = statsfull['data']['currentPlayer']['shoesGear']
		clothes = statsfull['data']['currentPlayer']['clothingGear']
		head = statsfull['data']['currentPlayer']['headGear']
		weapon = statsfull['data']['currentPlayer']['weapon']
		byname = statsfull['data']['currentPlayer']['byname']
		usedWeaps = statsfull['data']['playHistory']['frequentlyUsedWeapons']
		paintpt = statsfull['data']['playHistory']['paintPointTotal']
		maxRank = statsfull['data']['playHistory']['udemaeMax']
		winCount = statsfull['data']['playHistory']['winCountTotal']
		totalBattle = statssimple['data']['playHistory']['battleNumTotal']
		species = species['data']['currentPlayer']['species']

		embed.title = f"Multiplayer stats for {name}#{id} - {species.title()}"
		percent = "{:.0f}".format(winCount/totalBattle * 100 if totalBattle > 0 else 0.0)
		embed.add_field(name="Stats", value=f"Title: {byname}\nTotal Turf Inked: {str(paintpt)}\nBattles (Total/Won/Percent) : {str(totalBattle)}/{str(winCount)}/{str(percent)}%\n")
		cls.createGearSubsEmbed(embed, head)
		cls.createGearSubsEmbed(embed, clothes)
		cls.createGearSubsEmbed(embed, shoes)

		return embed

	#Ensure you have 'hosted_url' AND 'web_dir' both set before calling this!
	@classmethod
	def createNamePlateImage(cls, playerJson, fonts, configData):
		imgResponse = requests.get(playerJson['data']['currentPlayer']['nameplate']['background']['image']['url'])
		npImage = Image.open(BytesIO(imgResponse.content)).convert("RGBA")
		
		s2FontSmall = fonts.truetype("s2.otf", size=24)
		s2FontMed = fonts.truetype("s2.otf", size=36)
		s1FontLarge = fonts.truetype("s1.otf", size=64)

		MAXW, MAXH = 700, 200
		size = (72, 72)
		i = 3 #Max badges is 3
		for badge in playerJson['data']['currentPlayer']['nameplate']['badges']:
			if badge is None:
				break
			else:	
				badgeRes = requests.get(badge['image']['url'])
				badgeImg = Image.open(BytesIO(badgeRes.content)).convert("RGBA")
				badgeImg.thumbnail(size, Image.ANTIALIAS)
				npImage.paste(badgeImg, (MAXW-(i*size[0]), MAXH-size[1]), badgeImg)
				i-=1

		imgEdit = ImageDraw.Draw(npImage)

		imgEdit.text((10,10), playerJson['data']['currentPlayer']['byname'], (255, 255, 255), font=s2FontMed, anchor='lt')
		imgEdit.text((10,175), f"#{playerJson['data']['currentPlayer']['nameId']}", (255, 255, 255), font=s2FontSmall, anchor='lt')
		imgEdit.text((MAXW/2, MAXH/2), playerJson['data']['currentPlayer']['name'], (255, 255, 255), font=s1FontLarge, anchor='mm')

		imgName = f"{playerJson['data']['currentPlayer']['name']}{playerJson['data']['currentPlayer']['nameId']}.png"
		imgUrl = f"{configData['hosted_url']}/s3/nameplates/{imgName}"
		imgPath = f"{configData['web_dir']}/s3/nameplates/{imgName}"

		npImage.save(imgPath, "PNG")
		return imgUrl

	@classmethod
	def addCircleToImage(self, image, HW, BUF):
		circleImg = Image.new("RGBA", (HW, HW), (255, 255, 255 ,0))
		circDraw = ImageDraw.Draw(circleImg)
		bounds = (0, 0, HW - 1, HW - 1)
		circDraw.ellipse(bounds, fill="black")
		circleImg.paste(image, (int(BUF/2), int(BUF/2)), image)
		return circleImg

	@classmethod
	def createGearCard(self, gear):
		IMGW, IMGH = 220, 290
		MAHW, SUBHW, BUF = 70, 50, 5
		img = Image.new("RGBA", (IMGW, IMGH), (0, 0, 0, 0))

		gearReq = requests.get(gear['image']['url'])
		gearImg = Image.open(BytesIO(gearReq.content)).convert("RGBA")
		gearImg = gearImg.resize((IMGW, IMGW), Image.ANTIALIAS)
		img.paste(gearImg, (0, 0), gearImg)

		maReq = requests.get(gear["primaryGearPower"]['image']['url'])
		maImg = Image.open(BytesIO(maReq.content)).convert("RGBA")
		maImg = maImg.resize((MAHW - BUF, MAHW - BUF), Image.ANTIALIAS)
		maImg = self.addCircleToImage(maImg, MAHW, BUF)
		img.paste(maImg, (0, IMGW), maImg)

		for i, ability in enumerate(gear['additionalGearPowers']):
			abilReq = requests.get(ability['image']['url'])
			abilImg = Image.open(BytesIO(abilReq.content)).convert("RGBA")
			abilImg = abilImg.resize((SUBHW - BUF, SUBHW - BUF), Image.ANTIALIAS)
			abilImg = self.addCircleToImage(abilImg, SUBHW, BUF)
			img.paste(abilImg, (MAHW + (i * SUBHW), IMGH - SUBHW), abilImg)

		return img

	@classmethod
	def createWeaponCard(self, weapon):
		IMGW, IMGH = 220, 290
		SHW, BUF = 70, 10
		img = Image.new("RGBA", (IMGW, IMGH), (0, 0, 0, 0))

		weapReq = requests.get(weapon['image']['url'])
		weapImg = Image.open(BytesIO(weapReq.content)).convert("RGBA")
		weapImg = weapImg.resize((IMGW, IMGW), Image.ANTIALIAS)
		img.paste(weapImg, (10, 0), weapImg)

		reqSub = requests.get(weapon['subWeapon']['image']['url'])
		reqSpec = requests.get(weapon['specialWeapon']['image']['url'])
		subImg = Image.open(BytesIO(reqSub.content)).convert("RGBA")
		specImg = Image.open(BytesIO(reqSpec.content)).convert("RGBA")
		subImg = subImg.resize((SHW - BUF, SHW - BUF), Image.ANTIALIAS)
		specImg = specImg.resize((SHW - BUF, SHW - BUF), Image.ANTIALIAS)
		subImg = self.addCircleToImage(subImg, SHW, BUF)
		specImg = self.addCircleToImage(specImg, SHW, BUF)
		img.paste(subImg, (int(IMGW/2) - SHW, IMGW), subImg)
		img.paste(specImg, (int(IMGW/2), IMGW), specImg)

		return img

	@classmethod
	def createFitImage(self, statsjson, fonts, configData):
		gear = { 'weapon' : statsjson['data']['currentPlayer']['weapon'], 'head' : statsjson['data']['currentPlayer']['headGear'],
				'clothes' : statsjson['data']['currentPlayer']['clothingGear'], 'shoes' : statsjson['data']['currentPlayer']['shoesGear'] }
		s2FontSmall = fonts.truetype("s2.otf", size=24)
		MAXW, MAXH = 880, 314
		TEXTBUF = 24
		GHW = 220
		TEXTCOLOR = (0, 150, 150, 255)
		retImage = Image.new("RGBA", (MAXW, MAXH), (0, 0, 0, 0))
		retDraw = ImageDraw.Draw(retImage)
		i = 0
		for k, v in gear.items():
			if k == 'weapon':
				retDraw.text((i * GHW + int(GHW / 2), 3), f"{v['name']}", TEXTCOLOR, font=s2FontSmall, anchor='mt')
				weaponCard = self.createWeaponCard(v)
				retImage.paste(weaponCard, (0, TEXTBUF), weaponCard)
			else:
				retDraw.text((i * GHW + int(GHW / 2), 3), f"{v['name']}", TEXTCOLOR, font=s2FontSmall, anchor='mt')
				gearCard = self.createGearCard(v)
				retImage.paste(gearCard, ((i * GHW), TEXTBUF), gearCard)
				retDraw.line([(i * GHW, 0), (i * GHW, MAXH)], fill="black", width=3)
			i += 1

		retDraw.rectangle((0, 0, MAXW - 1, MAXH - 1), outline="black", width=3)
		imgName = f"{statsjson['data']['currentPlayer']['name']}-{statsjson['data']['currentPlayer']['nameId']}.png"

		img = io.BytesIO()
		retImage.save(img, 'PNG')
		img.seek(0)
		return img

	@classmethod
	def createStoreEmbed(self, gear, brand, title, configData):
		embed = discord.Embed(colour=0xF9FC5F)
		imgHash = hashlib.sha224(f"{gear['id']}{gear['gear']['primaryGearPower']['name']}".encode()).hexdigest()
		if not os.path.exists(f"{configData['web_dir']}/s3/gearcards/{imgHash}.png"):
			self.createGearCard(gear['gear']).save(f"{configData['web_dir']}/s3/gearcards/{imgHash}.png")

		embed.set_thumbnail(url=f"{configData['hosted_url']}/s3/gearcards/{imgHash}.png")

		embed.title = title
		embed.add_field(name = "Brand", value = gear['gear']['brand']['name'], inline = True)
		embed.add_field(name = "Gear Name", value = gear['gear']['name'], inline = True)
		embed.add_field(name = "Type", value = gear['gear']['__typename'].replace("Gear", ""), inline = True)
		embed.add_field(name = "Main Ability", value = gear['gear']['primaryGearPower']['name'], inline = True)
		embed.add_field(name = "Sub Slots", value = len(gear['gear']['additionalGearPowers']), inline = True)
		embed.add_field(name = "Common Ability", value = brand.commonAbility().name(), inline = True)
		embed.add_field(name = "Price", value = gear['price'], inline = True)

		return embed

	@classmethod
	def createStoreCanvas(self, gearJson, fonts, configData):
		MAXW, MAXH = 660, 1062
		CARDW, CARDH = 220, 290
		TEXTH = 24
		TEXTCOLOR = (0, 150, 150, 255)
		s2FontSmall = fonts.truetype("s2.otf", size=TEXTH)
		img = Image.new("RGBA", (MAXW, MAXH), (0, 0, 0, 0))
		draw = ImageDraw.Draw(img)

		#Daily Drops
		draw.text((int(MAXW/2), 0), f"The Daily Drop: {gearJson['pickupBrand']['brand']['name']}", TEXTCOLOR, font=s2FontSmall, anchor="mt")
		#draw.line([(0, TEXTH), (MAXW, TEXTH)], fill='black', width=3) - Don't know if lines are going to be good
		for i, gear in enumerate(gearJson['pickupBrand']['brandGears']):
			draw.text((i * CARDW + int(CARDW/2), TEXTH), gear['gear']['name'], TEXTCOLOR, font=s2FontSmall, anchor='mt')
			draw.text((i * CARDW + int(CARDW/2), TEXTH * 2), f"Price: {gear['price']}", TEXTCOLOR, font=s2FontSmall, anchor="mt")
			gearImg = self.createGearCard(gear['gear'])
			img.paste(gearImg, (i * CARDW, TEXTH*3), gearImg)

		#draw.line([(0, CARDH + (TEXTH * 3)), (MAXW, CARDH + (TEXTH * 2))], fill="black", width=3)
		draw.text((int(MAXW/2), CARDH + (TEXTH*3)), "Normal gear on sale", TEXTCOLOR, font=s2FontSmall, anchor="mt")
		#draw.line([(0, CARDH + (TEXTH * 4)), (MAXW, CARDH + (TEXTH * 3))], fill="black", width=3)
		for i, gears in enumerate([gearJson['limitedGears'][i * 3:(i + 1) * 3] for i in range((len(gearJson['limitedGears']) + 3 - 1) // 3 )]):
			for j, gear in enumerate(gears):
				draw.text((j * CARDW + int(CARDW/2), (i+1) * CARDH + ((4+i) * TEXTH + i * TEXTH)), gear['gear']['name'], TEXTCOLOR, font=s2FontSmall, anchor="mt")
				draw.text((j * CARDW + int(CARDW/2), (i+1) * CARDH + ((5+i) * TEXTH + i * TEXTH)), f"Price: {gear['price']}", TEXTCOLOR, font=s2FontSmall, anchor="mt")
				gearImg = self.createGearCard(gear['gear'])
				img.paste(gearImg, (j * CARDW, (i+1) * CARDH + ((6+i) * TEXTH)), gearImg)

		img.save(f"{configData['web_dir']}/s3/store.png", "PNG")

		return f"{configData['hosted_url']}/s3/store.png?{str(time.time())}"

	@classmethod
	def createStoreListingEmbed(self, gearJson, fonts, configData):
		embed = discord.Embed(colour=0xF9FC5F)
		embed.title = "Splatoon 3 Splatnet Store Gear"
		url = S3Utils.createStoreCanvas(gearJson, fonts, configData)
		#print(f"URL: {url}")
		embed.set_image(url=url)
		return embed

class S3Handler():
	def __init__(self, client, mysqlHandler, nsotoken, splat3info, configData, fonts, cachemanager):
		self.client = client
		self.sqlBroker = mysqlHandler
		self.nsotoken = nsotoken
		self.splat3info = splat3info
		self.configData = configData
		self.hostedUrl = configData.get('hosted_url')
		self.webDir = configData.get('web_dir')
		self.schedule = S3Schedule(nsotoken, mysqlHandler, cachemanager)
		self.storedm = s3.storedm.S3StoreHandler(client, nsotoken, splat3info, mysqlHandler, configData)
		self.fonts = fonts
		self.cachemanager = cachemanager

	async def cmdWeaponInfo(self, ctx, name):
		match = self.splat3info.weapons.matchItem(name)
		if not match.isValid():
			await ctx.respond(f"Can't find weapon: {match.errorMessage()}", ephemeral = True)
			return

		weapon = match.get()
		await ctx.respond(f"Weapon '{weapon.name()}' has subweapon '{weapon.sub().name()}' and special '{weapon.special().name()}'.")
		return

	async def cmdWeaponSpecial(self, ctx, name):
		match = self.splat3info.specials.matchItem(name)
		if not match.isValid():
			await ctx.respond(f"Can't find special: {match.errorMessage()}", ephemeral = True)
			return

		special = match.get()
		weapons = self.splat3info.getWeaponsBySpecial(special)
		embed = discord.Embed(colour=0x0004FF)
		embed.title = f"Weapons with Special: {special.name()}"
		for w in weapons:
			embed.add_field(name=w.name(), value=f"Subweapon: {w.sub().name()}\nPts for Special: {str(w.specpts())}\nLevel To Purchase: {str(w.level())}", inline=True)
		await ctx.respond(embed=embed)

	async def cmdWeaponSub(self, ctx, name):
		match = self.splat3info.subweapons.matchItem(name)
		if not match.isValid():
			await ctx.respond(f"Can't find subweapon: {match.errorMessage()}", ephemeral = True)
			return

		subweapon = match.get()
		weapons = self.splat3info.getWeaponsBySubweapon(subweapon)
		embed = discord.Embed(colour=0x0004FF)
		embed.title = f"Weapons with Subweapon: {subweapon.name()}"
		for w in weapons:
			embed.add_field(name=w.name(), value=f"Special: {w.special().name()}\nPts for Special: {str(w.specpts())}\nLevel To Purchase: {str(w.level())}", inline=True)
		await ctx.respond(embed=embed)

	async def cmdWeaponRandom(self, ctx):
		weapon = self.splat3info.weapons.getRandomItem()
		await ctx.respond(f"Random weapon: **{weapon.name()}** (subweapon **{weapon.sub().name()}**/special **{weapon.special().name()}**)")

	async def cmdScrim(self, ctx, num, modelist):
		if (num < 0) or (num > 20):
			await ctx.respond("Please supply a number of battles between 1 and 20", ephemeral = True)
			return

		# Parse list of modes into objects
		modes = []
		modeNames = re.split("[,; ]", modelist)
		for mn in modeNames:
			match = self.splat3info.modes.matchItem(mn)
			if not match.isValid():
				await ctx.respond(f"Unknown mode: {match.errorMessage()}", ephemeral = True)
				return
			modes.append(match.get())

		# Generate list
		battles = []
		for i in range(num):
			map = self.splat3info.maps.getRandomItem()
			mode = random.choice(modes)
			battles.append(f"Game {i + 1}: {mode.name()} on {map.name()}")

		# Create embed
		embed = discord.Embed(colour=0x0004FF)
		embed.title = "Scrim battle list"
		embed.add_field(name = f"{num} battles", value = "\n".join(battles))

		await ctx.respond(embed=embed)

	async def cmdStatsBattle(self, ctx, battlenum):
		await ctx.defer()

		nso = await self.nsotoken.get_nso_client(ctx.user.id)
		if not nso.is_logged_in():
			await ctx.respond("You don't have a NSO token set up! Run /token to get started.")
			return

		histories = nso.s3.get_battle_history_list()
		if histories is None:
			await ctx.respond("Failed to retrieve battle history")
			return

		battles = histories['data']['latestBattleHistories']['historyGroups']['nodes'][0]['historyDetails']['nodes']
		if battlenum > len(battles):
			await ctx.respond(f"You asked for battle number {battlenum} but I only see {len(battles)} battles.")
			return

		battle = battles[battlenum - 1]
		details = nso.s3.get_battle_history_detail(battle['id'])
		if details is None:
			await ctx.respond("Failed to retrieve battle details")
			return

		embed = S3Utils.createBattleDetailsEmbed(details)
		await ctx.respond(embed=embed)

	async def cmdStats(self, ctx):
		await ctx.defer()

		nso = await self.nsotoken.get_nso_client(ctx.user.id)
		if not nso.is_logged_in():
			await ctx.respond("You don't have a NSO token setup! Run /token to get started.")
			return

		statssimple = nso.s3.get_player_stats_simple()
		if statssimple is None:
			await ctx.respond(f"Failed to retrieve stats.")
			print(f"cmdStats: get_player_stats returned none for user {ctx.user.id}")
			return

		statsfull = nso.s3.get_player_stats_full()

		species = nso.s3.get_species_cur_weapon()

		embed = S3Utils.createMultiplayerStatsEmbed(statssimple, statsfull, species)
		if self.webDir and self.hostedUrl:
			imgUrl = S3Utils.createNamePlateImage(statsfull, self.fonts, self.configData)
			embed.set_thumbnail(url=f"{imgUrl}?{str(time.time() % 1)}")

		await ctx.respond(embed = embed)

	async def cmdSRStats(self, ctx):
		await ctx.defer()

		nso = await self.nsotoken.get_nso_client(ctx.user.id)
		if not nso.is_logged_in():
			await ctx.respond("You don't have a NSO token setup! Run /token to get started.")
			return

		srstats = nso.s3.get_salmon_run_stats()
		if srstats is None:
			await ctx.respond(f"Failed to retrieve stats.")
			print(f"get_salmon_run_stats returned none for user {ctx.user.id}")
			return

		embed = S3Utils.createSalmonRunResultsEmbed(srstats)
		await ctx.respond(embed = embed)

	async def cmdFit(self, ctx):
		await ctx.defer()

		nso = await self.nsotoken.get_nso_client(ctx.user.id)
		if not nso.is_logged_in():
			await ctx.respond("You don't have a NSO token setup! Run /token to get started.")
			return

		statsfull = nso.s3.get_player_stats_full()
		if statsfull is None:
			await ctx.respond("Failed to retrieve stats.")
			print(f"cmdFit: get_player_stats_full returned none for {ctx.user.id}")
			return

		img = S3Utils.createFitImage(statsfull, self.fonts, self.configData)
		await ctx.respond(file = discord.File(img, filename = "fit.png", description = "Fit image"))

	async def cmdFest(self, ctx):
		await ctx.defer()

		nso = await self.nsotoken.get_bot_nso_client()
		if not nso:
			await ctx.respond("Sorry, this bot is not configured to allow this.")
			return
		if not nso.is_logged_in():
			await ctx.respond("Sorry, unavailable at this time.")
			return

		festinfo = nso.s3.get_splatfest_list()
		if festinfo is None:
			await ctx.respond(f"Failed to retrieve stats.")
			print(f"get_splatfest_list returned none for user {ctx.user.id}")
			return

		embed = S3Utils.createSplatfestEmbed(festinfo['data']['festRecords']['nodes'][0])
		await ctx.respond(embed = embed)

	async def cmdSchedule(self, ctx, which):
		await ctx.defer()

		name = self.schedule.schedule_names[which]

		sched = self.schedule.get_schedule(which, count = 2)
		if len(sched) == 0:
			await ctx.respond(f"That schedule is empty.", ephemeral = True)
			return

		now = time.time()

		embed = discord.Embed(colour=0x0004FF)
		embed.title = f"{name} Schedule"

		for rot in sched:
			title = rot['mode']

			if rot['endtime'] < now:
				title += f" \u2014 Ended"
			elif rot['starttime'] <= now and rot['endtime'] > now:
				title += f" \u2014 Started at <t:{int(rot['starttime'])}>"
			else:
				title += f" \u2014 Upcoming at <t:{int(rot['starttime'])}>"

			map_names = map(lambda m: m['name'], rot['maps'])

			text = "\n".join(map_names)

			embed.add_field(name = title, value = text, inline = False)

		await ctx.respond(embed = embed)

	async def cmdStoreList(self, ctx):
		if self.storedm.cacheState:
			await ctx.respond(embed=S3Utils.createStoreListingEmbed(self.storedm.storecache, self.fonts, self.configData))
		else:
			#TODO...
			await ctx.respond("Somethings up with NSO bruh, better look at that!")
