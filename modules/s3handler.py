import discord, asyncio
import mysqlhandler, nsotoken
import json, sys, re, time, requests, random, hashlib, os, io
import s3.storedm
import s3.schedule

from apscheduler.schedulers.asyncio import AsyncIOScheduler

#Image Editing
from PIL import Image, ImageFont, ImageDraw 
from io import BytesIO
from os.path import exists
import base64
import datetime
import dateutil.parser

class S3Utils():
	@classmethod
	def createBattleDetailsImage(cls, details, weapon_thumbnail_cache, font_broker):
		typeNames = {"BANKARA": "Anarchy", "FEST": "Splatfest", "X": "X Rank", "LEAGUE": "League", "PRIVATE": "Private Battle"}
		anarchyTypeNames = {"OPEN": "Open", "CHALLENGE": "Series"}
		festTypeNames = {"NORMAL": "Normal", "DECUPLE": "10x", "DRAGON": "100x", "DOUBLE_DRAGON": "333x"}
		judgementNames = {"WIN": "Victory", "LOSE": "Defeat", "EXEMPTED_LOSE": "Early disconnect with no penalty", "DEEMED_LOSE": "Loss due to early disconnect", "DRAW": "No contest"}
		modeNames = {"TURF_WAR": "Turf War", "GOAL": "Rainmaker", "LOFT": "Tower Control", "CLAM": "Clam Blitz", "AREA": "Splat Zones"}

		playerName = details['data']['vsHistoryDetail']['player']['name']
		type = details['data']['vsHistoryDetail']['vsMode']['mode']
		mode = details['data']['vsHistoryDetail']['vsRule']['rule']
		map = details['data']['vsHistoryDetail']['vsStage']['name']
		judgement = details['data']['vsHistoryDetail']['judgement']
		playerId = details['data']['vsHistoryDetail']['player']['id']
		duration = details['data']['vsHistoryDetail']['duration']

		anarchy_type = None
		if (type == 'BANKARA') and (details['data']['vsHistoryDetail'].get('bankaraMatch')):
			anarchy_type = details['data']['vsHistoryDetail']['bankaraMatch'].get('mode')

		fest_type = None
		if (type == 'FEST') and (details['data']['vsHistoryDetail'].get('festMatch')):
			fest_type = details['data']['vsHistoryDetail']['festMatch'].get('dragonMatchType')

		# Gather all teams
		all_teams = [details['data']['vsHistoryDetail']['myTeam'], *details['data']['vsHistoryDetail']['otherTeams']]

		# Cache weapon thumbnails
		for t in all_teams:
			for p in t['players']:
				if (weapon := p.get('weapon')) and (weapon.get('image2dThumbnail')):
					key = base64.b64decode(weapon['id']).decode("utf-8") + ".png"
					url = weapon['image2dThumbnail']['url']
					if weapon_thumbnail_cache.has(key):
						continue  # Already cached

					print(f"Caching weapon thumbnail key '{key}' image-url {url}")
					response = requests.get(url, stream=True)
					weapon_thumbnail_cache.add_http_response(key, response)

		fonts = {}
		fonts['s2'] = font_broker.truetype("s2.otf", size=24)
		fonts['s1'] = font_broker.truetype("s1.otf", size=24)

		myTeam = details['data']['vsHistoryDetail']['myTeam']
		otherTeams = details['data']['vsHistoryDetail']['otherTeams']

		text_color = (255, 255, 255)

		image = Image.new('RGB', (500, 600), (0, 0, 0))
		draw = ImageDraw.Draw(image)

		yposition = 5

		# Game type
		if anarchy_type:
			text = f"{typeNames.get(type, type)} \u2022 {anarchyTypeNames.get(anarchy_type, anarchy_type)}"
		elif fest_type:
			text = f"{typeNames.get(type, type)} \u2022 {festTypeNames.get(fest_type, fest_type)}"
		else:
			text = f"{typeNames.get(type, type)}"
		draw.text((image.width / 2, yposition), text, text_color, font = fonts['s1'], anchor='mt')
		bbox = draw.textbbox((image.width / 2, yposition), text, font = fonts['s1'], anchor='mt')
		yposition = bbox[3]

		# Mode and map
		text = f"{modeNames.get(mode, mode)} \u2022 {map}"
		draw.text((image.width / 2, yposition), text, text_color, font = fonts['s1'], anchor='mt')
		bbox = draw.textbbox((image.width / 2, yposition), text, font = fonts['s1'], anchor='mt')
		yposition = bbox[3]

		# Score bar
		if not myTeam['result'] is None:  # May be null if game was a draw
			if mode == 'TURF_WAR':
				ratios = [*[t['result'].get('paintRatio', 0) for t in all_teams]]
				labels = [("%0.1f" % (r)) for r in ratios]
				print(repr(ratios))
			else:
				#scores = [myTeam['result'].get('score', 0), *[t['result'].get('score', 0) for t in otherTeams]]
				scores = [*[t['result'].get('score', 0) for t in all_teams]]
				labels = [str(s) for s in scores]
				total = sum(scores)
				if total == 0:
					ratios = [0 for s in scores]
				else:
					ratios = [(s / total) for s in scores]

			if len(all_teams) == 3:
				positions = [5, int(image.width / 2), image.width - 5]
				anchors = ['lt', 'mt', 'rt']
			else:
				positions = [5, image.width - 5]
				anchors = ['lt', 'rt']

			colors = [(int(t['color']['r'] * 255), int(t['color']['g'] * 255), int(t['color']['b'] * 255)) for t in all_teams]
			widths = [int((r * image.width) + 0.5) for r in ratios]

			x = 0
			for i in range(len(all_teams)):
				draw.rectangle([(x, yposition), (x + widths[i], yposition + 24)], fill = colors[i])
				x += widths[i]

				draw.text((positions[i] + 1, yposition + 1), labels[i], (0, 0, 0), font = fonts['s1'], anchor = anchors[i])
				draw.text((positions[i], yposition), labels[i], (255, 255, 255), font = fonts['s1'], anchor = anchors[i])

			yposition += fonts['s1'].size

		# Outcome
		text = f"{judgementNames.get(judgement, judgement)}"
		draw.text((image.width / 2, yposition), text, font = fonts['s1'], anchor = 'mt')
		bbox = draw.textbbox((image.width / 2, yposition), text, font = fonts['s1'], anchor = 'mt')
		yposition = bbox[3]

		if judgement == 'WIN':
			yposition = cls.createBattleDetailsImageTeam(image, draw, yposition, "My Team", fonts, weapon_thumbnail_cache, myTeam)
			for t in otherTeams:
				yposition = cls.createBattleDetailsImageTeam(image, draw, yposition, "Opposing Team", fonts, weapon_thumbnail_cache, t)
		else:
			for t in otherTeams:
				yposition = cls.createBattleDetailsImageTeam(image, draw, yposition, "Opposing Team", fonts, weapon_thumbnail_cache, t)
			yposition = cls.createBattleDetailsImageTeam(image, draw, yposition, "My Team", fonts, weapon_thumbnail_cache, myTeam)

		font_name = fonts['s1'].getname()[0]
		if (font_name == 'Splatoon1') or (font_name == 'Splatoon2'):
			text = "\uE063 %d:%02d" % (int(duration / 60), duration % 60)  # Use clock symbol from PUA
		else:
			text = "Duration %d:%02d" % (int(duration / 60), duration % 60)
		draw.text((image.width / 2, yposition), text, font = fonts['s1'], anchor = 'mt')
		bbox = draw.textbbox((image.width / 2, yposition), text, font = fonts['s1'], anchor = 'mt')
		yposition = bbox[3]

		# Crop to used height
		image = image.crop((0, 0, image.width, yposition))

		image_io = io.BytesIO()
		image.save(image_io, 'PNG')
		image_io.seek(0)
		return image_io

	@classmethod
	def createBattleDetailsImageTeam(cls, image, draw, yposition, name, fonts, weapon_thumbnail_cache, team):
		margin = 5
		titleheight = 40
		rowheight = 30
		thumbnail_size = 28
		height = titleheight + (len(team['players']) * rowheight) + (margin * 2)

		rect = [(margin, yposition), (image.width - margin, yposition + height)]
		color = (int(team['color']['r'] * 255), int(team['color']['g'] * 255), int(team['color']['b'] * 255))
		draw.rounded_rectangle(rect, 7, color)

		yposition += margin

		draw.text((margin * 2 + 1, yposition + 1), name, fill = (0, 0, 0), font = fonts['s2'], anchor = 'lt')
		draw.text((margin * 2, yposition), name, font = fonts['s2'], anchor = 'lt')

		draw.text((int(image.width * 0.60) + 1, yposition + 1), "paint", fill = (0, 0, 0), font = fonts['s2'], anchor = 'rt')
		draw.text((int(image.width * 0.60), yposition), "paint", font = fonts['s2'], anchor = 'rt')

		draw.text((image.width - (margin * 2) + 1, yposition + 1), "K+A(A)/D/S", fill = (0, 0, 0), font = fonts['s2'], anchor = 'rt')
		draw.text((image.width - (margin * 2), yposition), "K+A(A)/D/S", font = fonts['s2'], anchor = 'rt')

		draw.line([margin * 2, yposition + titleheight - 8, image.width - margin * 2, yposition + titleheight - 8], fill = (255, 255, 255), width = 3)
		yposition += titleheight

		stats = []
		for p in team['players']:
			result = p['result']
			weapon = p['weapon']

			# Add arrow indicator for player
			if p.get('isMyself'):
				draw.text((margin * 2, yposition + int(rowheight / 2) - 1), "\u2192", font = fonts['s1'], anchor = 'lm')

			# Add weapon thumbnail
			weapon_key = base64.b64decode(weapon['id']).decode("utf-8") + ".png"
			if thumbnail_io := weapon_thumbnail_cache.get_io(weapon_key):
				thumbnail_image = Image.open(thumbnail_io).convert("RGBA")
				thumbnail_image.thumbnail((thumbnail_size, thumbnail_size), Image.ANTIALIAS)
				draw.ellipse([margin * 2 + thumbnail_size, yposition, margin * 2 + thumbnail_size * 2, yposition + thumbnail_size], fill = (0,0,0))
				image.paste(thumbnail_image, (margin * 2 + thumbnail_size, yposition), thumbnail_image)

			pos = (margin * 3 + thumbnail_size * 2, yposition)
			draw.text((pos[0] + 1, pos[1] + 1), p['name'], fill = (0, 0, 0), font = fonts['s2'], anchor = 'lt')
			draw.text(pos, p['name'], font = fonts['s2'], anchor = 'lt')

			pos = (int(image.width * 0.60), yposition)
			draw.text((pos[0] + 1, pos[1] + 1), f"{p['paint']}p", fill = (0, 0, 0), font = fonts['s2'], anchor = 'rt')
			draw.text(pos, f"{p['paint']}p", font = fonts['s2'], anchor = 'rt')

			pos = (int(image.width - (margin * 2)), yposition)
			if result is None:
				stats = '(disconnect)'
			else:
				stats = "%d(%d)/%d/%d" % (result['kill'], result['assist'], result['death'], result['special'])
			draw.text((pos[0] + 1, pos[1] + 1), stats, fill = (0, 0, 0), font = fonts['s2'], anchor = 'rt')
			draw.text(pos, stats, font = fonts['s2'], anchor = 'rt')

			yposition += rowheight

		yposition += margin * 2

		return yposition

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
		draw.line([(0, TEXTH), (MAXW, TEXTH)], fill='black', width=3) #Don't know if lines are going to be good
		for i, gear in enumerate(gearJson['pickupBrand']['brandGears']):
			draw.text((i * CARDW + int(CARDW/2), TEXTH), gear['gear']['name'], TEXTCOLOR, font=s2FontSmall, anchor='mt')
			draw.text((i * CARDW + int(CARDW/2), TEXTH * 2), f"Price: {gear['price']}", TEXTCOLOR, font=s2FontSmall, anchor="mt")
			gearImg = self.createGearCard(gear['gear'])
			img.paste(gearImg, (i * CARDW, TEXTH*3), gearImg)

		#Normal gear rotation
		draw.text((int(MAXW/2), CARDH + (TEXTH*3)), "Normal gear on sale", TEXTCOLOR, font=s2FontSmall, anchor="mt")
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
		embed.set_image(url=url)
		embed.set_footer("To order gear, run `/s3 order")
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
		self.schedule = s3.schedule.S3Schedule(nsotoken, mysqlHandler, cachemanager)
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

		weapon_thumbnail_cache = self.cachemanager.open("s3.weapons.small-2d", (3600 * 24 * 90))  # Cache for 90 days

		image_io = S3Utils.createBattleDetailsImage(details, weapon_thumbnail_cache, self.fonts)
		await ctx.respond(file = discord.File(image_io, filename = "battle.png", description = "Battle details"))

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

		image_io = S3Utils.createFitImage(statsfull, self.fonts, self.configData)
		await ctx.respond(file = discord.File(image_io, filename = "fit.png", description = "Fit image"))

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
			await ctx.respond("I can't fetch the current store listing, please try again later")

	async def cmdS3StoreOrder(self, ctx, item, override):
		await ctx.defer()

		nso = await self.nsotoken.get_nso_client(ctx.user.id)
		if not nso.is_logged_in():
			await ctx.respond("You don't have a NSO token setup! Run /token to get started.")
			return

		match = self.splat3info.gear.matchItem(item)
		if match.isValid():
			store = nso.s3.get_store_items()
			if store == None:
				await ctx.respond("Something went wrong!")
				return

			theItem = None
			for item in store['data']['gesotown']['limitedGears']:
				if item['gear']['name'] == match.get().name():
					theItem = item
					break

			if theItem == None:
				for item in store['data']['gesotown']['pickupBrand']['brandGears']:
					if item['gear']['name'] == match.get().name():
						theItem = item
						break

			if theItem == None:
				await ctx.respond(f"{match.get().name()} isn't in the store right now.")
				return
			else:
				ret = nso.s3.do_store_order(theItem['id'], override)
				if ret['data']['orderGesotownGear']['userErrors'] == None:
					#createStoreEmbed(self, gear, brand, title, configData):
					brand = self.splat3info.brands.getItemByName(theItem['gear']['brand']['name'])
					await ctx.respond(embed = S3Utils.createStoreEmbed(theItem, brand, "Ordered! Talk to Murch in game to get it!", self.configData))
				elif ret['data']['orderGesotownGear']['userErrors'][0]['code'] == "GESOTOWN_ALREADY_ORDERED":
					await ctx.respond("You already have an item on order! If you still want to order this, run this command again with Override set to True.")
				else:
					await ctx.respond("Something went wrong.")

				return
		else:
			if len(match.items) < 1:
				await ctx.respond(f"Can't find any gear with the name {item}")
				return
			else:
				embed = discord.Embed(colour=0xF9FC5F)
				embed.title = "Did you mean?"
				embed.add_field(name="Gear", value=", ".join(map(lambda item: item.name(), match.items)), inline=False)
				await ctx.respond(embed = embed)
				return

	async def cmdWeaponStats(self, ctx, weapon):
		await ctx.defer()

		nso = await self.nsotoken.get_nso_client(ctx.user.id)
		if not nso.is_logged_in():
			await ctx.respond("You don't have a NSO token setup! Run /token to get started.")
			return

		match = self.splat3info.weapons.matchItem(weapon)
		if match.isValid():
			weapons = nso.s3.get_weapons_stats()
			if weapons == None:
				await ctx.respond("Something went wrong!")
				return

			theWeapon = None
			for node in weapons['data']['weaponRecords']['nodes']:
				if match.get().name() == node['name']:
					theWeapon = node
					break

			if theWeapon == None:
				await ctx.respond(f"It looks like you haven't used {match.get().name()} yet. Go try it out!")
				return
			else:
				embed = discord.Embed(colour=0xF9FC5F)
				embed.title = f"{theWeapon['name']} Stats"
				img = S3Utils.createWeaponCard(theWeapon)
				#embed.set_thumbnail(discord.File(img, filename = "weapon.png", description = "Weapon image"))
				embed.add_field(name = "Turf Inked", value = f"{theWeapon['stats']['paint']}", inline = True)
				embed.add_field(name = "Freshness", value = f"{theWeapon['stats']['vibes']}", inline = True)
				embed.add_field(name = "Wins", value = f"{theWeapon['stats']['win']}", inline = True)
				embed.add_field(name = "Level", value = f"{theWeapon['stats']['level']}", inline = True)
				embed.add_field(name = "EXP till next level", value = f"{theWeapon['stats']['paint']}", inline = True)

				await ctx.respond(embed = embed)
		else:
			if len(match.items) < 1:
				await ctx.respond(f"Can't find any gear with the name {weapon}")
				return
			else:
				embed = discord.Embed(colour=0xF9FC5F)
				embed.title = "Did you mean?"
				embed.add_field(name="Weapon", value=", ".join(map(lambda item: item.name(), match.items)), inline=False)
				await ctx.respond(embed = embed)
				return
