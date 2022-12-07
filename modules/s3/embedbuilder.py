import discord, asyncio
import re, time, requests, hashlib, os

from s3.imagebuilder import S3ImageBuilder

import base64
import datetime
import dateutil.parser

class S3EmbedBuilder():
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
		historyDetails = historyGroups[0]['historyDetails']['nodes']
		lastGameDetails = historyDetails[0]
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
	def createStoreEmbed(self, gear, brand, title):
		embed = discord.Embed(colour=0xF9FC5F)

		embed.title = title
		embed.add_field(name = "Brand", value = gear['gear']['brand']['name'], inline = True)
		embed.add_field(name = "Gear Name", value = gear['gear']['name'], inline = True)
		embed.add_field(name = "Type", value = gear['gear']['__typename'].replace("Gear", ""), inline = True)
		embed.add_field(name = "Main Ability", value = gear['gear']['primaryGearPower']['name'], inline = True)
		embed.add_field(name = "Sub Slots", value = len(gear['gear']['additionalGearPowers']), inline = True)
		embed.add_field(name = "Common Ability", value = brand.commonAbility().name(), inline = True)
		embed.add_field(name = "Price", value = gear['price'], inline = True)

		return embed
