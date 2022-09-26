import discord, asyncio
import mysqlhandler, nsotoken
import json, sys, re, time, requests, random

#Image Editing
from PIL import Image, ImageFont, ImageDraw 
from io import BytesIO
import base64
import datetime
import dateutil.parser

from apscheduler.schedulers.asyncio import AsyncIOScheduler

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
			description += f"Ended at <t:{int(endtime.timestamp())}>>\n"

		embed = discord.Embed(colour=0x0004FF, description = description)
		embed.title = splatfest['title']
		embed.set_image(url = splatfest['image']['url'])

		for t in splatfest['teams']:
			id = base64.b64decode(t['id']).decode("utf-8")
			which = re.sub('^.*:', '', id)
			embed.add_field(name = f'Team {which}', value = t['teamName'])

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
	def createNamePlateImage(cls, playerJson, configData):
		imgResponse = requests.get(playerJson['data']['currentPlayer']['nameplate']['background']['image']['url'])
		npImage = Image.open(BytesIO(imgResponse.content)).convert("RGBA")
		
		s2FontSmall = ImageFont.truetype(f"{configData['fonts_dir']}/s2.otf", size=24)
		s2FontMed = ImageFont.truetype(f"{configData['fonts_dir']}/s2.otf", size=36)
		s1FontLarge = ImageFont.truetype(f"{configData['fonts_dir']}/s1.otf", size=64)

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
		bounds = (0, 0, HW-2, HW-2)
		circDraw.ellipse(bounds, fill="black")
		circleImg.paste(image, (0 + int(BUF/2),0 + int(BUF/2)), image)
		return circleImg

	@classmethod
	def createFitImage(self, statsjson, configData):
		gear = { 'weapon' : statsjson['data']['currentPlayer']['weapon'], 'head' : statsjson['data']['currentPlayer']['headGear'],
				'clothes' : statsjson['data']['currentPlayer']['clothingGear'], 'shoes' : statsjson['data']['currentPlayer']['shoesGear'] }
		s2FontSmall = ImageFont.truetype(f"{configData['fonts_dir']}/s2.otf", size=24)
		MAXW, MAXH = 860, 294
		TEXTBUF = 24
		GHW = 220
		MAINHW = 70
		SUBHW = 50
		BUF = 5
		TEXTCOLOR = (0, 150, 150, 255)
		retImage = Image.new("RGBA", (MAXW, MAXH), (0, 0, 0, 0))
		retDraw = ImageDraw.Draw(retImage)
		i = 4
		for k, v in gear.items():
			res = requests.get(v['image']['url'])
			gimg = Image.open(BytesIO(res.content)).convert("RGBA")
			gimg.thumbnail((GHW, GHW), Image.ANTIALIAS)
			if k == 'weapon':
				retDraw.text((MAXW - (i * GHW) + int(GHW / 2), 0 + 3), f"{v['name']}", TEXTCOLOR, font=s2FontSmall, anchor='mt')
				retImage.paste(gimg, (MAXW - (i * GHW) + int((MAINHW - SUBHW) / 2), TEXTBUF), gimg)
				reqSub = requests.get(v['subWeapon']['image']['url'])
				reqSpec = requests.get(v['specialWeapon']['image']['url'])
				subImg = Image.open(BytesIO(reqSub.content)).convert("RGBA")
				subImg.thumbnail((SUBHW-BUF, SUBHW-BUF), Image.ANTIALIAS)
				specImg = Image.open(BytesIO(reqSpec.content)).convert("RGBA")
				specImg.thumbnail((SUBHW - BUF, SUBHW - BUF), Image.ANTIALIAS)
				center = (int(MAXW - (i * GHW) + (GHW / 2)), GHW + TEXTBUF)
				subImg = self.addCircleToImage(subImg, SUBHW, BUF)
				specImg = self.addCircleToImage(specImg, SUBHW, BUF)
				retImage.paste(subImg, (center[0]-SUBHW, center[1]), subImg)
				retImage.paste(specImg, center, specImg)
			else:
				retDraw.text((MAXW - (i * GHW) + int(GHW / 2) - (MAINHW - SUBHW), 0 + 3), f"{v['name']}", TEXTCOLOR, font=s2FontSmall, anchor='mt')
				retImage.paste(gimg, (MAXW - (i * GHW) - int((MAINHW - SUBHW) / 2), TEXTBUF), gimg)
				maReq = requests.get(v["primaryGearPower"]['image']['url'])
				maImg = Image.open(BytesIO(maReq.content)).convert("RGBA")
				maImg.thumbnail((MAINHW-BUF, MAINHW-BUF), Image.ANTIALIAS)
				maImg = self.addCircleToImage(maImg, MAINHW, BUF)
				retImage.paste(maImg, (MAXW - (i * GHW) - (MAINHW - SUBHW), GHW - (MAINHW - SUBHW) + TEXTBUF), maImg)
				j = 1
				for ability in v['additionalGearPowers']:
					abilReq = requests.get(ability['image']['url'])
					abilImg = Image.open(BytesIO(abilReq.content)).convert("RGBA")
					abilImg.thumbnail((SUBHW-BUF, SUBHW-BUF), Image.ANTIALIAS)
					abilImg = self.addCircleToImage(abilImg, SUBHW, BUF)
					retImage.paste(abilImg, (MAXW - (i * GHW) + (j * SUBHW),GHW + TEXTBUF), abilImg)
					j += 1
				retDraw.line([((MAXW - (i * GHW) - (MAINHW - SUBHW), 0)), ((MAXW - (i * GHW) - (MAINHW - SUBHW), MAXH))], fill="black", width=3)
			i -= 1

		retDraw.rectangle((0, 0, MAXW - 1, MAXH - 1), outline="black", width=3)
		imgName = f"{statsjson['data']['currentPlayer']['name']}-{statsjson['data']['currentPlayer']['nameId']}.png"
		retImage.save(f"{configData['web_dir']}/s3/fits/{imgName}", "PNG")
		return f"{configData['hosted_url']}/s3/fits/{imgName}"	

class s3OrderView(discord.ui.View):
	def __init__(self, s3handler, nsotoken, user):
		super().__init__()
		self.nsoToken = nsotoken
		self.s3Handler = s3handler
		self.user = user
		self.confirm = False
		self.timeout = 6900.0

	async def initView(self):
		orderBut = discord.ui.Button(label="Order Item")
		nso = await self.nsoToken.get_nso_client(self.user.id)
		if nso.is_logged_in():
			orderBut.callback = self.orderItem
		else:
			self.stop()
			return None
		self.add_item(orderBut)

	async def orderItem(self, interaction: discord.Interaction):
		if self.confirm:
			await self.nsoHandler.orderGearCommand(interaction, args=['5'], override=True)
			if self.user != None:
				self.clear_items()
				self.stop()
		else:
			await self.nsoHandler.orderGearCommand(interaction, args=['5'])
			self.confirm=True

class S3StoreHandler():
	def __init__(self, client, nsoToken, splat3info, mysqlHandler):
		self.client = client
		self.sqlBroker = mysqlHandler
		self.nsotoken = nsoToken
		self.splat3info = splat3info
		self.scheduler = AsyncIOScheduler()
		self.scheduler.add_job(self.doStoreRegularDM, 'cron', second="0")#hour="*/2", minute='1', timezone='UTC') 
		self.scheduler.add_job(self.doStoreDailyDropDM, 'cron', hour="0", minute='1', timezone='UTC')
		self.scheduler.add_job(self.cacheS3JSON, 'cron', hour="*/2", minute='0', second='15', timezone='UTC')
		self.storecache = None
		self.cacheState = False
		self.scheduler.start()

	##Trigger Keys: gearname brand mability
	#{ 'gearnames' : ['Gear One', "Two" ], 'brands': ['Toni-Kensa', 'Forge'], 'mabilities' : ['Ink Saver (Main)'] }

	def checkToDM(self, gear, triggers):
		brand = gear['brand']['name']
		mability = gear['primaryGearPower']['name']
		gearname = gear['name']

		for trigger in triggers.values():
			if brand in trigger:
				return True
			if mability in trigger:
				return True
			if gearname in trigger:
				return True
			
		return False

	async def doStoreDailyDropDM(self):
		return

	async def handleDM(self, user, gear):
		return

	async def doStoreRegularDM(self):
		if not self.cacheState:
			print("Cache was not updated... skipping this rotation...")
			return

		theGear = self.storecache['limitedGears'][5]['gear']
		brand = theGear['brand']['name']
		mability = theGear['primaryGearPower']['name']
		gearname = theGear['name']
		cur = await self.sqlBroker.connect()

		print(f"Doing S3 Store DM. Checking {gearname} Brand: {brand} Ability: {mability}")

		stmt = "SELECT * FROM s3storedms"
		await cur.execute(stmt)
		toDM = await cur.fetchall()
		await self.sqlBroker.close(cur)
		for id in range(len(toDM)):
			servid = toDM[id][0]
			memid = toDM[id][1]
			triggers = json.loads(toDM[id][2])
			server = self.client.get_guild(int(servid))

			await server.chunk()
			theMem = server.get_member(int(memid))
			if theMem is None:
				continue
			elif self.checkToDM(theGear, triggers):
				asyncio.ensure_future(self.handleDM(theMem, theGear))

	async def cacheS3JSON(self):
		print("Updating cached S3 json...")
		nso = await self.nsotoken.get_bot_nso_client()

		storejson = nso.s3.get_store_items()
		if storejson is None:
			print("Failure on store cache refresh. Trying again...")
			time.sleep(3) #Give it a bit to try again...
			storejson = nso.s3.get_store_items() #Done 2nd time for 9403 errors w/ token generation
			if storejson is None:
				print("Failed to update store cache for rotation")
				self.cacheState = False
				return

		print("Got store cache for this rotation")
		self.storecache = storejson['data']['gesotown']
		self.cacheState = True

class S3Handler():
	def __init__(self, client, mysqlHandler, nsotoken, splat3info, configData):
		self.client = client
		self.sqlBroker = mysqlHandler
		self.nsotoken = nsotoken
		self.splat3info = splat3info
		self.configData = configData
		self.hostedUrl = configData.get('hosted_url')
		self.webDir = configData.get('web_dir')
		self.storedm = S3StoreHandler(client, nsotoken, splat3info, mysqlHandler)

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

		histories = nso.s3.get_battle_histories()
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
			imgUrl = S3Utils.createNamePlateImage(statsfull, self.configData)
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

		url = S3Utils.createFitImage(statsfull, self.configData)
		await ctx.respond(f"{url}?{str(time.time() % 1)}")

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
