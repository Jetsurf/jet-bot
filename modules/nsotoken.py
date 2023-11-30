from __future__ import print_function
import asyncio

# nso-api specific
import nso_api
from nso_api.nso_api import NSO_API
from nso_api.imink import IMink
from nso_api.nso_api_s2 import NSO_API_S2

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
		if await self.nsotoken.deleteTokens(interaction.user.id):
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
		print(f"Nsotoken: Using NSO-API version {NSO_API.get_version()}")
		self.client = client
		self.config = config
		self.sqlBroker = mysqlhandler
		self.stringCrypt = stringCrypt
		self.friendCodes = friendCodes
		self.f_provider = IMink("Jet-bot/1.0.0 (discord=jetsurf#8514)")  # TODO: Figure out bot owner automatically
		self.nso_clients = {}
		self.init_complete = False

		# Set up scheduled tasks
		self.scheduler = AsyncIOScheduler()
		self.scheduler.add_job(self.nso_client_cleanup, 'interval', minutes = 5)
		self.scheduler.start()

		# Do async init
		asyncio.create_task(self.async_init())

	async def async_init(self):
		global_data = await self.nso_load_global_data()
		NSO_API.load_global_data(global_data)
		self.init_complete = True

	# Wait for the class's async_init to complete.
	async def wait_for_init(self):
		for i in range(5):
			if self.init_complete:
				return
			await asyncio.sleep(1)

	# Returns NSO client for the bot account, or None if there was a problem.
	async def get_bot_nso_client(self):
		if not self.config.get('nso_userid'):
			print("No nso_userid configured, can't get bot NSO client")
			return None

		# Wait for async init
		await self.wait_for_init()

		# Might get called before SQL has connected, so await connection
		await self.sqlBroker.wait_for_startup()

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
		# Wait for async init
		await self.wait_for_init()

		userid = int(userid)

		# If we already have a client for this user, just return it
		if self.nso_clients.get(userid):
			return self.nso_clients[userid]

		# Construct a new one for this user
		nso = NSO_API(self.f_provider, userid)
		
		# If we have keys, load them into the client
		keys = await self.nso_client_load_keys(userid)
		if keys:
			nso.load_user_data(keys)

		# Register callback for when user data changes
		nso.on_user_data_update(self.nso_user_data_updated)

		# Register callback for when global data changes
		nso.on_global_data_update(self.nso_global_data_updated)

		self.nso_clients[userid] = nso
		print(f"NSO App ver: {nso.app.get_version()}")
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

	# This is a callback which is called by nso-api when a client object's
	#  keys change.
	def nso_user_data_updated(self, nso, userid):
		# This callback is not async, so we use asyncio.create_task() to schedule an async call
		asyncio.create_task(self.nso_client_save_keys(userid))

	# This is a callback which is called by nso-api when global data has
	#  changed.
	def nso_global_data_updated(self, data):
		# This callback is not async, so we use asyncio.create_task() to schedule an async call
		asyncio.create_task(self.nso_save_global_data(data))

	async def nso_client_save_keys(self, userid):
		if not self.nso_clients.get(userid):
			return  # No client for this user

		keys = self.nso_clients[userid].get_user_data()
		plaintext = json.dumps(keys)
		ciphertext = self.stringCrypt.encryptString(plaintext)
		#print(f"nso_client_save_keys: {plaintext} -> {ciphertext}")

		async with self.sqlBroker.context() as sql:
			await sql.query("DELETE FROM nso_client_keys WHERE (clientid = %s)", (userid,))
			await sql.query("INSERT INTO nso_client_keys (clientid, updatetime, jsonkeys) VALUES (%s, NOW(), %s)", (userid, ciphertext))

		return

	async def nso_client_load_keys(self, userid):
		async with self.sqlBroker.context() as sql:
			row = await sql.query_first("SELECT jsonkeys FROM nso_client_keys WHERE (clientid = %s) LIMIT 1", (userid,))

		if (row == None) or (row['jsonkeys'] == None):
			return None  # No keys

		ciphertext = row['jsonkeys']
		plaintext = self.stringCrypt.decryptString(ciphertext)
		#print(f"getGameKeys: {ciphertext} -> {plaintext}")
		keys = json.loads(plaintext)
		return keys

	async def nso_save_global_data(self, data):
		jsondata = json.dumps(data)

		async with self.sqlBroker.context() as sql:
			await sql.query("DELETE FROM nso_global_data")
			await sql.query("INSERT INTO nso_global_data (updatetime, jsondata) VALUES (NOW(), %s)", (jsondata,))

		return

	async def nso_load_global_data(self):
		await self.sqlBroker.wait_for_startup()

		async with self.sqlBroker.context() as sql:
			row = await sql.query_first("SELECT jsondata FROM nso_global_data LIMIT 1")

		if (row == None) or (row['jsondata'] == None):
			return None  # No stored data

		return json.loads(row['jsondata'])

	async def deleteTokens(self, userid):
		print(f"Deleting token and nso client for {userid}")
		async with self.sqlBroker.context() as sql:
			await sql.query("DELETE FROM nso_client_keys WHERE (clientid = %s)", (userid,))

		del self.nso_clients[userid]
		return True
