import discord, asyncio
import mysqlhandler, nsotoken
import json, sys, re, time, requests, random, hashlib, os, io
import s3.storedm
import s3.schedule
from s3.imagebuilder import S3ImageBuilder

from io import BytesIO
from os.path import exists
import base64
import datetime
import dateutil.parser

class S3Utils():
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

	@classmethod
	def createStoreEmbed(self, gear, brand, title, configData):
		embed = discord.Embed(colour=0xF9FC5F)
		imgHash = hashlib.sha224(f"{gear['id']}{gear['gear']['primaryGearPower']['name']}".encode()).hexdigest()
		if not os.path.exists(f"{configData['web_dir']}/s3/gearcards/{imgHash}.png"):
			S3ImageBuilder.createGearCard(gear['gear']).save(f"{configData['web_dir']}/s3/gearcards/{imgHash}.png")

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
	def createStoreListingEmbed(self, gearJson, fonts, configData):
		embed = discord.Embed(colour=0xF9FC5F)
		embed.title = "Splatoon 3 Splatnet Store Gear"
		url = S3ImageBuilder.createStoreCanvas(gearJson, fonts, configData)
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

		image_io = S3ImageBuilder.createBattleDetailsImage(details, weapon_thumbnail_cache, self.fonts)
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
			imgUrl = S3ImageBuilder.createNamePlateImage(statsfull, self.fonts, self.configData)
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

		image_io = S3ImageBuilder.createFitImage(statsfull, self.fonts, self.configData)
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
			weapons = nso.s3.get_weapon_stats()
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
				img = S3ImageBuilder.createWeaponCard(theWeapon)
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
