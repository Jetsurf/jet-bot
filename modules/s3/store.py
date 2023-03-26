import discord
import asyncio
import mysqlhandler
import nsotoken
import json
import time
import re
import base64
import dateutil.parser

from apscheduler.schedulers.asyncio import AsyncIOScheduler

class S3Store():
	def __init__(self, nsoToken, splat3info, mysqlHandler):
		self.sqlBroker = mysqlHandler
		self.nsoToken = nsoToken
		self.splat3info = splat3info

		self.items = []

		self.scheduler = AsyncIOScheduler()
		self.scheduler.add_job(self.checkStoreItems, 'cron', hour="*/1", minute='0', second='15', timezone='UTC')
		#self.scheduler.add_job(self.checkStoreItems, 'cron', hour="*", minute='*/15', second='15', timezone='UTC')
		self.scheduler.start()

		# Do async startup
		asyncio.create_task(self.loadStoreItems())

	async def loadStoreItems(self):
		async with self.sqlBroker.context() as sql:
			rows = await sql.query("SELECT * FROM s3_store_items")

		items = []
		for row in rows:
			item = {}
			item['saleid']    = row['saleid']
			item['name']      = row['name']
			item['dailydrop'] = (row['dailydrop'] == "Y")
			item['brandid']   = int(row['brandid'])
			item['price']     = int(row['price'])
			item['endtime']   = row['endtime'].timestamp()
			item['data']      = json.loads(row['jsondata'])

			items.append(item)

		#print(f"loaded: {repr(items)}")
		self.items = items

	async def addStoreItem(self, item):
		# Add to DB
		sqlendtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(item['endtime']))
		async with self.sqlBroker.context() as sql:
			await sql.query("INSERT INTO s3_store_items (saleid, name, dailydrop, brandid, price, endtime, jsondata) VALUES (%s, %s, %s, %s, %s, %s, %s)", (item['saleid'], item['name'], 'Y' if item['dailydrop'] else 'N', item['brandid'], item['price'], sqlendtime, json.dumps(item['data'])))

		# Add to list
		self.items.append(item)

	async def removeStoreItem(self, item):
		# Remove from DB
		async with self.sqlBroker.context() as sql:
			await sql.query("DELETE FROM s3_store_items WHERE (saleid = %s)", (item['saleid'], ))

		# Remove from list
		self.items = [i for i in self.items if i['saleid'] != item['saleid']]

	# Given a base64-encoded brand id string, returns the brand number.
	def decodeBrandId(self, encoded):
		decoded = base64.b64decode(encoded).decode("utf-8")  # Decodes to a string like "Brand-16"
		if match := re.search(r'-([0-9]+)$', decoded):
			return int(match[1])

		return None

	def decodeStoreItem(self, itemdata, dailydrop = False):
		item = {}
		item['saleid'] = itemdata['id']
		item['name'] = itemdata['gear']['name']
		item['dailydrop'] = dailydrop
		item['brandid'] = self.decodeBrandId(itemdata['gear']['brand']['id'])
		item['price'] = int(itemdata['price'])
		item['endtime'] = dateutil.parser.isoparse(itemdata['saleEndTime']).timestamp()
		item['data'] = itemdata
		return item

	def findInventoryChanges(self, items):
		results = {'new': [], 'old': []}

		# Find items that are new
		for item in items:
			if not item['saleid'] in [i['saleid'] for i in self.items]:
				results['new'].append(item)

		# Find items that are old
		for item in self.items:
			if not item['saleid'] in [i['saleid'] for i in items]:
				results['old'].append(item)

		return results

	async def checkStoreItems(self):
		nso = await self.nsoToken.get_bot_nso_client()
		if not nso:
			return  # No bot account configured

		print("[S3Store] Checking store items...")
		if not nso.is_logged_in():
			print("[S3Store] Time to refresh store cache, but the bot account is not logged in")
			return

		storedata = nso.s3.get_store_items()
		if storedata is None:
			print("[S3Store] Failure on store cache refresh. Trying again...")
			await asyncio.sleep(3)  # Give it a bit to try again...
			storedata = nso.s3.get_store_items()  # Done 2nd time for 9403 errors w/ token generation
			if storedata is None:
				print("[S3Store] Failed to update store inventory!")
				return

		items = []

		# Pull regular items
		for itemdata in storedata['data']['gesotown']['limitedGears']:
			items.append(self.decodeStoreItem(itemdata))

		# Pull "daily drop" items
		for itemdata in storedata['data']['gesotown']['pickupBrand']['brandGears']:
			items.append(self.decodeStoreItem(itemdata, dailydrop = True))

		# Figure out which items changed
		changes = self.findInventoryChanges(items)

		# Remove old items
		for item in changes['old']:
			print(f"[S3Store] Removing old item '{item['name']}'")
			await self.removeStoreItem(item)

		# Add new items
		for item in changes['new']:
			print(f"[S3Store] Adding new item '{item['name']}'")
			await self.addStoreItem(item)

		return
