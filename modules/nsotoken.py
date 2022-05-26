from __future__ import print_function
import asyncio
import pynso
from pynso.nso_api import NSO_API
from pynso.imink import IMink
from pynso.nso_api_s2 import NSO_API_S2
import mysqlhandler, nsohandler, discord
import requests, json, re, sys, uuid, time
import os, base64, hashlib, random, string
from discord.ui import *
from discord.enums import ComponentType, InputTextStyle
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import googleplay
from typing import Optional
#TODO: Clean up these imports, this file is going to be mess

class tokenMenuView(discord.ui.View):
	def __init__(self, nsotoken, hostedurl):
		super().__init__()
		self.nsoTokens = nsotoken
		self.hostedurl = hostedurl

	async def init(self, ctx):
		self.ctx = ctx
		self.isDupe = await self.nsoTokens.checkSessionPresent(ctx)
		cancel = discord.ui.Button(label="Close", style=discord.ButtonStyle.red)
		cancel.callback = self.cancelButton
		self.add_item(cancel)

		if not self.isDupe:
			login = self.nsoTokens.loginUrl()
			self.auth_code_verifier = login['auth_code_verifier']
			self.add_item(discord.ui.Button(label="Sign In Link", url=login['url']))
			urlBut = discord.ui.Button(label="Submit URL")
			urlBut.callback = self.sendModal
			self.add_item(urlBut)
		else:
			delbut = discord.ui.Button(label="Delete Tokens")
			delbut.callback = self.deleteTokens
			self.add_item(delbut)

	async def deleteTokens(self, interaction: discord.Interaction):
		if await self.nsoTokens.deleteTokens(interaction):
			await interaction.response.edit_message(content='Tokens Deleted. To set them up again, run /token again.', embed=None, view=None)
		else:
			await interaction.response.edit_message(content='Tokens failed to delete, try again shortly or join my support guild.')
		self.stop()

	async def cancelButton(self, interaction: discord.Interaction):
		await interaction.response.edit_message(content="Closing", embed=None, view=None)
		self.stop()

	async def sendModal(self, interaction: discord.Interaction):
		self.disabled = True
		modal = tokenHandler(self.nsoTokens, self.auth_code_verifier, title="Nintendo NSO Token Setup")
		await interaction.response.send_modal(modal=modal)
		await modal.wait()
		self.clear_items()
		self.stop()

class tokenHandler(Modal):
	def __init__(self, nsoTokens,  auth_code_verifier, *args, **kwargs):
		self.nsoTokens = nsoTokens
		self.auth_code_verifier = auth_code_verifier
		super().__init__(*args, **kwargs)
		self.title="Nintendo NSO Token Setup"
		self.add_item(InputText(label="Requested Link from Nintendo", style=discord.InputTextStyle.long, placeholder="npf71b963c1b7b6d119://"))
		
	async def callback(self, interaction: discord.Interaction):
		session_token_code = re.search('session_token_code=([^&]*)&', self.children[0].value)

		if session_token_code is not None and await self.nsoTokens.postLogin(interaction, self.children[0].value, self.auth_code_verifier):
			await interaction.response.send_message("Token Added, run /token again to remove them from me. You can dismiss the first message now.", ephemeral=True)
			self.stop()
		else:
			await interaction.response.send_message("Token Failed to Add. Rerun /token again, and you can dismiss the first message now.", ephemeral=True)
			self.stop()						

class Nsotoken():
	def __init__(self, client, mysqlhandler, hostedUrl, stringCrypt):
		self.client = client
		self.session = requests.Session()
		self.sqlBroker = mysqlhandler
		self.scheduler = AsyncIOScheduler()
		self.hostedUrl = hostedUrl
		self.stringCrypt = stringCrypt
		self.scheduler.add_job(self.updateAppVersion, 'cron', hour="3", minute='0', second='35', timezone='UTC')
		self.scheduler.add_job(self.nso_client_cleanup, 'cron', hour="0", minute='0', second='0', timezone='UTC')
		self.imink = IMink("Jet-bot/1.0.0 (discord=jetsurf#8514)")  # TODO: Figure out bot owner automatically
		self.nso_clients = {}

	# Given a userid, returns an NSO client for that user.
	async def get_nso_client(self, userid):
		# If we already have a client for this user, just return it
		if self.nso_clients.get(userid):
			return self.nso_clients[userid]

		# Construct a new one for this user
		nsoAppInfo = await self.getAppVersion()
		nso = NSO_API(nsoAppInfo['version'], self.imink, userid)

		# If we have keys, load them into the client
		keys = await self.nso_client_load_keys(userid)
		if keys:
			nso.set_keys(keys)
		elif await self.checkSessionPresent(userid):
			# As a fallback, try to pull in token from old key store
			session = await self.get_session_token_mysql(userid)
			nso.set_session_token(session)

		# Register callback for when keys change
		nso.on_keys_update(self.nso_client_keys_updated)

		self.nso_clients[userid] = nso
		return nso

	async def nso_client_cleanup(self):
		for userid in list(self.nso_clients):
			client = self.nso_clients[userid]
			idle_seconds = client.get_idle_seconds()
			if idle_seconds > (4 * 3600):
				print(f"NSO client for {userid} not used for {int(idle_seconds)} seconds. Deleting.")
				del self.nso_clients[userid]

	# This is a callback which is called by pynso when a client object's
	#  keys change.
	# This callback is not async, so we use asyncio.create_task to call
	#  an async method later that does the actual work.
	def nso_client_keys_updated(self, nso, userid):
		print(f"Time to save keys for user {userid}")
		asyncio.create_task(self.nso_client_save_keys(userid))

	async def nso_client_save_keys(self, userid):
		if not self.nso_clients.get(userid):
			return  # No client for this user

		keys = self.nso_clients[userid].get_keys()
		plaintext = json.dumps(keys)
		ciphertext = self.stringCrypt.encryptString(plaintext)
		#print(f"nso_client_save_keys: {plaintext} -> {ciphertext}")

		cur = await self.sqlBroker.connect()
		await cur.execute("DELETE FROM nso_client_keys WHERE (clientid = %s)", (userid,))
		await cur.execute("INSERT INTO nso_client_keys (clientid, updatetime, jsonkeys) VALUES (%s, NOW(), %s)", (userid, ciphertext))
		await self.sqlBroker.commit(cur)
		return

	async def nso_client_load_keys(self, userid):
		cur = await self.sqlBroker.connect()
		await cur.execute("SELECT jsonkeys FROM nso_client_keys WHERE (clientid = %s) LIMIT 1", (userid,))
		row = await cur.fetchone()
		await self.sqlBroker.commit(cur)

		if (row == None) or (row[0] == None):
			return None  # No keys

		ciphertext = row[0]
		plaintext = self.stringCrypt.decryptString(ciphertext)
		#print(f"getGameKeys: {ciphertext} -> {plaintext}")
		keys = json.loads(plaintext)
		return keys

	async def getAppVersion(self):
		cur = await self.sqlBroker.connect()

		await cur.execute("SELECT version, UNIX_TIMESTAMP(updatetime) AS updatetime FROM nso_app_version")
		row = await cur.fetchone()
		await self.sqlBroker.commit(cur)

		if row:
			return {'version': row[0], 'updatetime': row[1]}

		return None

	async def updateAppVersion(self):
		oldInfo = await self.getAppVersion()
		if oldInfo != None:
			age = time.time() - oldInfo['updatetime']
			if age < 3600:
				print("Skipping NSO version check -- cached data is recent")
				return

		gp = googleplay.GooglePlay()
		newVersion = gp.getAppVersion("com.nintendo.znca")
		if newVersion == None:
			print(f"Couldn't retrieve NSO app version?")
			return

		cur = await self.sqlBroker.connect()

		if (oldInfo == None) or (oldInfo['version'] != newVersion):
			# Version was updated
			await cur.execute("DELETE FROM nso_app_version")
			await cur.execute("INSERT INTO nso_app_version (version, updatetime) VALUES (%s, NOW())", (newVersion,))
			print(f"Updated NSO version: {oldInfo['version'] if oldInfo else '(none)'} -> {newVersion}")
		else:
			# No version change, so just bump the timestamp
			await cur.execute("UPDATE nso_app_version SET updatetime = NOW()")

		await self.sqlBroker.commit(cur)
		return

	async def getGameKeys(self, clientid):
		cur = await self.sqlBroker.connect()
		await cur.execute("SELECT game_keys FROM tokens WHERE (clientid = %s) LIMIT 1", (str(clientid),))
		row = await cur.fetchone()
		await self.sqlBroker.commit(cur)

		if (row == None) or (row[0] == None):
			return {}  # No keys

		ciphertext = row[0]
		plaintext = self.stringCrypt.decryptString(ciphertext)
		#print(f"getGameKeys: {ciphertext} -> {plaintext}")
		keys = json.loads(plaintext)
		return keys

	async def __checkDuplicate(self, id, cur):
		await cur.execute("SELECT COUNT(*) FROM tokens WHERE clientid = %s", (str(id),))
		count = await cur.fetchone()
		if count[0] > 0:
			return True
		else:
			return False

	async def checkSessionPresent(self, ctx):
		cur = await self.sqlBroker.connect()
		print(f"Class: {type(ctx)}")
		if not isinstance(ctx, discord.Member):
			print("Context call")
			ret = await self.__checkDuplicate(ctx.user.id, cur)
		else:
			print("Interaction call")
			ret = await self.__checkDuplicate(ctx.id, cur)
		await self.sqlBroker.close(cur)
		return ret

	async def deleteTokens(self, interaction):
		cur = await self.sqlBroker.connect()
		print("Deleting token")
		stmt = "DELETE FROM tokens WHERE clientid = %s"
		input = (interaction.user.id,)
		await cur.execute(stmt, input)
		if cur.lastrowid != None:
			await self.sqlBroker.commit(cur)
			return True
		else:
			await self.sqlBroker.rollback(cur)
			return False

	async def get_session_token_mysql(self, userid) -> Optional[str]:
		cur = await self.sqlBroker.connect()
		stmt = "SELECT session_token FROM tokens WHERE clientid = %s"
		await cur.execute(stmt, (str(userid),))
		ciphertext = await cur.fetchone()
		await self.sqlBroker.close(cur)
		if ciphertext == None:
			return None
		else:
			return self.stringCrypt.decryptString(ciphertext[0])
			