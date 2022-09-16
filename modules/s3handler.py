import discord, asyncio
import mysqlhandler, nsotoken
import re, time, requests, random

#Image Editing
from PIL import Image, ImageFont, ImageDraw 
from io import BytesIO
import base64
import datetime
import dateutil.parser

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

		if starttime > now:
			whenstr = f"Starts at <t:{int(starttime.timestamp())}> (<t:{int(starttime.timestamp())}:R>)"
		elif endtime > now:
			whenstr = f"Ends at <t:{int(endtime.timestamp())}> (<t:{int(endtime.timestamp())}:R>)"
		else:
			whenstr = f"Ended at <t:{int(endtime.timestamp())}>>"

		embed = discord.Embed(colour=0x0004FF, description = whenstr)
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
		if len(historyGroups) == 0:
			embed.add_field(name = "History empty", value = "Go play some Salmon Run!")

		historyDetails = historyGroups[0]['historyDetails']['nodes']
		lastGameDetails = historyDetails[0]
		embed.title = f"Your Salmon Run rank"
		embed.add_field(name = "Rank", value = lastGameDetails['afterGrade']['name'])
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
	def createNamePlateImage(cls, playerJson, hostedUrl, webDir):
		imgResponse = requests.get(playerJson['data']['currentPlayer']['nameplate']['background']['image']['url'])
		npImage = Image.open(BytesIO(imgResponse.content)).convert("RGBA")
		
		s2FontSmall = ImageFont.truetype('/home/dbot/s2.otf', size=24)
		s2FontMed = ImageFont.truetype('/home/dbot/s2.otf', size=36)
		s1FontLarge = ImageFont.truetype('/home/dbot/s1.otf', size=64)

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
		imgUrl = f"{hostedUrl}/s3/nameplates/{imgName}"
		imgPath = f"{webDir}/s3/nameplates/{imgName}"

		npImage.save(imgPath, "PNG")
		return imgUrl

	@classmethod
	def createFitImage(self, statsjson, hostedUrl, webDir):
		gear = { 'weapon' : statsjson['data']['currentPlayer']['weapon'], 'head' : statsjson['data']['currentPlayer']['headGear'],
				'clothes' : statsjson['data']['currentPlayer']['clothingGear'], 'shoes' : statsjson['data']['currentPlayer']['shoesGear'] }
		MAXW, MAXH = 800, 250
		GHW = 200
		SUBHW = 50
		retImage = Image.new("RGBA", (MAXW, MAXH), (0, 0, 0, 0))
		retDraw = ImageDraw.Draw(retImage)
		i = 4
		for k, v in gear.items():
			res = requests.get(v['image']['url'])
			gimg = Image.open(BytesIO(res.content)).convert("RGBA")
			gimg.thumbnail((GHW, GHW), Image.ANTIALIAS)
			retImage.paste(gimg, (MAXW-(i*GHW), 0), gimg)
			if k == 'weapon':
				reqSub = requests.get(v['subWeapon']['image']['url'])
				reqSpec = requests.get(v['specialWeapon']['image']['url'])
				subImg = Image.open(BytesIO(reqSub.content)).convert("RGBA")
				subImg.thumbnail((SUBHW, SUBHW), Image.ANTIALIAS)
				specImg = Image.open(BytesIO(reqSpec.content)).convert("RGBA")
				specImg.thumbnail((SUBHW, SUBHW), Image.ANTIALIAS)
				center = (int(MAXW-(i*GHW) + (GHW/2)), GHW)
				retImage.paste(subImg, (center[0]-SUBHW, center[1]))
				retImage.paste(specImg, center)
			else:
				maReq = requests.get(v["primaryGearPower"]['image']['url'])
				maImg = Image.open(BytesIO(maReq.content)).convert("RGBA")
				maImg.thumbnail((SUBHW, SUBHW), Image.ANTIALIAS)
				retImage.paste(maImg, (MAXW-(i*GHW), GHW))
				j = 1
				for ability in v['additionalGearPowers']:
					abilReq = requests.get(ability['image']['url'])
					abilImg = Image.open(BytesIO(abilReq.content)).convert("RGBA")
					abilImg.thumbnail((SUBHW, SUBHW), Image.ANTIALIAS)
					retImage.paste(abilImg, (MAXW - (i * GHW) + (j*SUBHW),GHW))
					j+=1
			i-=1

		imgName = f"{statsjson['data']['currentPlayer']['name']}-{statsjson['data']['currentPlayer']['nameId']}.png"
		retImage.save(f"{webDir}/s3/fits/{imgName}", "PNG")
		return f"{hostedUrl}/s3/fits/{imgName}"	

class S3Handler():
	def __init__(self, client, mysqlHandler, nsotoken, splat3info, configData):
		self.client = client
		self.sqlBroker = mysqlHandler
		self.nsotoken = nsotoken
		self.splat3info = splat3info
		self.hostedUrl = configData.get('hosted_url')
		self.webDir = configData.get('web_dir')

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
			imgUrl = S3Utils.createNamePlateImage(statsfull, self.hostedUrl, self.webDir)
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

		url = S3Utils.createFitImage(statsfull, self.hostedUrl, self.webDir)
		await ctx.respond(f"{url}?{str(time.time() % 1)}")

	async def cmdFest(self, ctx):
		await ctx.defer()

		# TODO: Use bot owner account so user does not need /token
		nso = await self.nsotoken.get_nso_client(ctx.user.id)
		if not nso.is_logged_in():
			await ctx.respond("You don't have a NSO token set up! Run /token to get started.")
			return

		festinfo = nso.s3.get_splatfest_list()
		if festinfo is None:
			await ctx.respond(f"Failed to retrieve stats.")
			print(f"get_splatfest_list returned none for user {ctx.user.id}")
			return

		embed = S3Utils.createSplatfestEmbed(festinfo['data']['festRecords']['nodes'][0])
		await ctx.respond(embed = embed)
