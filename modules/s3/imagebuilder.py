import re, time, requests, os, io

#Image Editing
from PIL import Image, ImageFont, ImageDraw 
from io import BytesIO
import base64
import datetime
import dateutil.parser

class S3ImageBuilder():
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
	def addCircleToImage(cls, image, HW, BUF):
		circleImg = Image.new("RGBA", (HW, HW), (255, 255, 255 ,0))
		circDraw = ImageDraw.Draw(circleImg)
		bounds = (0, 0, HW - 1, HW - 1)
		circDraw.ellipse(bounds, fill="black")
		circleImg.paste(image, (int(BUF/2), int(BUF/2)), image)
		return circleImg

	@classmethod
	def createGearCard(cls, gear):
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
		maImg = cls.addCircleToImage(maImg, MAHW, BUF)
		img.paste(maImg, (0, IMGW), maImg)

		for i, ability in enumerate(gear['additionalGearPowers']):
			abilReq = requests.get(ability['image']['url'])
			abilImg = Image.open(BytesIO(abilReq.content)).convert("RGBA")
			abilImg = abilImg.resize((SUBHW - BUF, SUBHW - BUF), Image.ANTIALIAS)
			abilImg = cls.addCircleToImage(abilImg, SUBHW, BUF)
			img.paste(abilImg, (MAHW + (i * SUBHW), IMGH - SUBHW), abilImg)

		return img

	@classmethod
	def createWeaponCard(cls, weapon):
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
		subImg = cls.addCircleToImage(subImg, SHW, BUF)
		specImg = cls.addCircleToImage(specImg, SHW, BUF)
		img.paste(subImg, (int(IMGW/2) - SHW, IMGW), subImg)
		img.paste(specImg, (int(IMGW/2), IMGW), specImg)

		return img

	@classmethod
	def createFitImage(cls, statsjson, fonts, configData):
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
				weaponCard = cls.createWeaponCard(v)
				retImage.paste(weaponCard, (0, TEXTBUF), weaponCard)
			else:
				retDraw.text((i * GHW + int(GHW / 2), 3), f"{v['name']}", TEXTCOLOR, font=s2FontSmall, anchor='mt')
				gearCard = cls.createGearCard(v)
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
