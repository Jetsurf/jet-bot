import discord, asyncio
import mysqlhandler, nsotoken
import time, requests
import gameinfo.splat3

splat3info = gameinfo.splat3.Splat3()

class S3Handler():
	def __init__(self, client, mysqlHandler, nsotoken, configData):
		self.client = client
		self.sqlBroker = mysqlHandler
		self.nsotoken = nsotoken
		self.hostedUrl = configData.get('hosted_url')
		self.webDir = configData.get('web_dir')

	async def cmdWeaponInfo(self, ctx, name):
		match = splat3info.weapons.matchItems(name)
		if not match.isValid():
			await ctx.respond(f"Can't find weapon: {match.errorMessage()}", ephemeral = True)
			return

		weapon = match.get()
		await ctx.respond(f"Weapon '{weapon.name()}' has subweapon '{weapon.sub().name()}' and special '{weapon.special().name()}'.")
		return
