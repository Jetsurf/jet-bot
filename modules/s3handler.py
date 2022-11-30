import discord, asyncio
import mysqlhandler, nsotoken
import json, sys, re, time, requests, random, hashlib, os, io
import sys
import traceback
import s3.storedm
import s3.schedule
import s3.imageextractor

from s3.imagebuilder import S3ImageBuilder
from s3.embedbuilder import S3EmbedBuilder
from s3.feedhandler import S3FeedHandler

from io import BytesIO
from os.path import exists
import base64
import datetime
import dateutil.parser

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
		self.feeds = s3.feedhandler.S3FeedHandler(client, mysqlHandler, self.schedule, cachemanager, fonts)
		self.imageextractor = s3.imageextractor.S3ImageExtractor(nsotoken, cachemanager)
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
		if battlenum < 1:
			await ctx.respond("The most recent battle is number 1.")
			return
		elif battlenum > len(battles):
			await ctx.respond(f"You asked for battle number {battlenum} but I only see {len(battles)} battles.")
			return

		battle = battles[battlenum - 1]
		details = nso.s3.get_battle_history_detail(battle['id'])
		if details is None:
			await ctx.respond("Failed to retrieve battle details")
			return

		weapon_thumbnail_cache = self.cachemanager.open("s3.weapons.small-2d")

		try:
			image_io = S3ImageBuilder.createBattleDetailsImage(details, weapon_thumbnail_cache, self.fonts)
		except:
			await ctx.respond("Could not render battle details! If problem persists, please complain (see /support).")
			sys.stderr.write(f"*** Could not render battle details!\n")
			traceback.print_exc(file = sys.stderr)
			sys.stderr.write(f"*** Battle JSON follows:\n{json.dumps(details)}\n")
			return

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

		embed = S3EmbedBuilder.createMultiplayerStatsEmbed(statssimple, statsfull, species)
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

		embed = S3EmbedBuilder.createSalmonRunResultsEmbed(srstats)
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

		embed = S3EmbedBuilder.createSplatfestEmbed(festinfo['data']['festRecords']['nodes'][0])
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
			mode = self.splat3info.getModeByInternalName(rot['mode'])
			title = mode.name() if mode else rot['mode']

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

	async def cmdSRMaps(self, ctx):
		await ctx.defer()

		sched = self.schedule.get_schedule('SR', count = 2)
		if len(sched) == 0:
			await ctx.respond(f"That schedule is empty.", ephemeral = True)

		image_io = S3ImageBuilder.createSRScheduleImage(sched, self.fonts, self.cachemanager)
		await ctx.respond(file = discord.File(image_io, filename = "sr-schedule.png", description = "Salmon Run schedule"))

	async def cmdStoreList(self, ctx):
		if self.storedm.cacheState:
			await ctx.respond(embed=S3EmbedBuilder.createStoreListingEmbed(self.storedm.storecache, self.fonts, self.configData))
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
					await ctx.respond(embed = S3EmbedBuilder.createStoreEmbed(theItem, brand, "Ordered! Talk to Murch in game to get it!", self.configData))
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
