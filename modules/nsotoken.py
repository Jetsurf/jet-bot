from __future__ import print_function
import asyncio

#PyNSO Specific
import pynso
from pynso.nso_api import NSO_API
from pynso.imink import IMink
from pynso.nso_api_s2 import NSO_API_S2

import mysqlhandler, discord
import requests, json, re, sys, uuid, time
import os, base64, hashlib, random, string
from discord.ui import *
from discord.enums import ComponentType, InputTextStyle
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from itunes_app_scraper.scraper import AppStoreScraper
from typing import Optional

class tokenMenuView(discord.ui.View):
	def __init__(self, nsotoken, hostedurl):
		super().__init__()
		self.nsotoken = nsotoken
		self.hostedurl = hostedurl

	async def init(self, ctx):
		self.ctx = ctx
		self.nso = await self.nsotoken.get_nso_client(ctx.user.id)
		self.isDupe = self.nso.is_logged_in()
		cancel = discord.ui.Button(label="Close", style=discord.ButtonStyle.red)
		cancel.callback = self.cancelButton
		self.add_item(cancel)

		if not self.isDupe:
			login = self.nso.get_login_challenge_url()
			self.add_item(discord.ui.Button(label="Sign In Link", url=login))
			urlBut = discord.ui.Button(label="Submit URL")
			urlBut.callback = self.sendModal
			self.add_item(urlBut)
		else:
			delbut = discord.ui.Button(label="Delete Tokens")
			delbut.callback = self.deleteTokens
			self.add_item(delbut)

	async def deleteTokens(self, interaction: discord.Interaction):
		if await self.nsotoken.deleteTokens(interaction):
			await interaction.response.edit_message(content='Tokens Deleted. To set them up again, run /token again.', embed=None, view=None)
		else:
			await interaction.response.edit_message(content='Tokens failed to delete, try again shortly or join my support guild.')
		self.stop()

	async def cancelButton(self, interaction: discord.Interaction):
		await interaction.response.edit_message(content="Closing", embed=None, view=None)
		self.stop()

	async def sendModal(self, interaction: discord.Interaction):
		self.disabled = True
		modal = tokenHandler(self.nso, title="Nintendo NSO Token Setup")
		await interaction.response.send_modal(modal=modal)
		await modal.wait()
		self.clear_items()
		self.stop()

class tokenHandler(Modal):
	def __init__(self, nso, *args, **kwargs):
		self.nso = nso
		self.title="Nintendo NSO Token Setup"
		super().__init__(*args, **kwargs)
		self.add_item(InputText(label="Requested Link from Nintendo", style=discord.InputTextStyle.long, placeholder="npf71b963c1b7b6d119://"))
		
	async def callback(self, interaction: discord.Interaction):
		if self.nso.complete_login_challenge(self.children[0].value):
			await interaction.response.send_message("Token Added, run /token again to remove them from me. You can dismiss the first message now.", ephemeral=True)
			self.stop()
		else:
			await interaction.response.send_message("Token Failed to Add. Rerun /token again, and you can dismiss the first message now.", ephemeral=True)
			self.stop()

class Nsotoken():
	def __init__(self, client, config, mysqlhandler, stringCrypt, friendCodes):
		self.client = client
		self.config = config
		self.session = requests.Session()
		self.sqlBroker = mysqlhandler
		self.stringCrypt = stringCrypt
		self.friendCodes = friendCodes
		self.imink = IMink("Jet-bot/1.0.0 (discord=jetsurf#8514)")  # TODO: Figure out bot owner automatically
		self.nso_clients = {}

		# Set up scheduled tasks
		self.scheduler = AsyncIOScheduler()
		self.scheduler.add_job(self.updateAppVersion, 'interval', hours = 24)
		self.scheduler.add_job(self.nso_client_cleanup, 'interval', minutes = 5)
		self.scheduler.start()

	async def migrate_tokens_if_needed(self):
		cur = await self.sqlBroker.connect()

		if not await self.sqlBroker.hasTable(cur, 'tokens'):
			return  # No such table

		await cur.execute("SELECT clientid, session_token FROM tokens")
		rows = await cur.fetchall()

		for row in rows:
			clientid = row[0]
			session_token_ciphertext = row[1]

			print(f"MIGRATE user {clientid}")

			client = await self.get_nso_client(clientid)
			if client.is_logged_in():
				print("  Already has new-style tokens, not migrating...")
				continue

			session_token = self.stringCrypt.decryptString(session_token_ciphertext)
			client.set_session_token(session_token)
			await self.nso_client_save_keys(clientid)

		await cur.execute("DROP TABLE tokens")

	# Returns NSO client for the bot account, or None if there was a problem.
	async def get_bot_nso_client(self):
		if not self.config.get('nso_userid'):
			print("No nso_userid configured, can't get bot NSO client")
			return None

		nso = await self.get_nso_client(self.config['nso_userid'])
		if not nso.is_logged_in():
			print("Someone wants to use the bot NSO client, but it's not logged in!")
			# TODO: Warn bot owners?
			# Don't return None because we want to be able to give
			#  different messages if it's set up and not working
			#  or not set up.

		return nso

	# Given a userid, returns an NSO client for that user.
	async def get_nso_client(self, userid):
		userid = int(userid)

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

		# Register callback for when keys change
		nso.on_keys_update(self.nso_client_keys_updated)

		self.nso_clients[userid] = nso
		return nso

	async def remove_nso_client(self, userid):
		userid = int(userid)

		# Record friend code from client object before deletion
		client = self.nso_clients[userid]
		if not client is None:
			fc = client.get_cached_friend_code()
			if not fc is None:
				await self.friendCodes.setFriendCode(userid, fc)

		# Remove it
		del self.nso_clients[userid]

	async def nso_client_cleanup(self):
		for userid in list(self.nso_clients):
			client = self.nso_clients[userid]
			idle_seconds = client.get_idle_seconds()
			if idle_seconds > (4 * 3600):
				print(f"NSO client for {userid} not used for {int(idle_seconds)} seconds. Deleting.")
				await self.remove_nso_client(userid)

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

		scraper = AppStoreScraper()
		nsogp = scraper.get_app_details(1234806557, country='us') #iOS App ID

		newVersion = nsogp['version']
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

	async def deleteTokens(self, interaction):
		cur = await self.sqlBroker.connect()
		print("Deleting token and nso client")
		stmt = "DELETE FROM nso_client_keys WHERE (clientid = %s)"
		instmt = (interaction.user.id,)
		await cur.execute(stmt, instmt)
		if cur.lastrowid != None:
			await self.sqlBroker.commit(cur)
			#Delete the nso object, as we destroyed tokens
			del self.nso_clients[interaction.user.id]
			return True
		else:
			await self.sqlBroker.rollback(cur)
			return False
			
