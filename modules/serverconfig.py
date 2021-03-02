import json

class ServerConfig():
	def __init__(self, mysqlhandler):
		self.db        = None
		self.sqlBroker = mysqlhandler

	async def getConfig(self, cursor, serverid):
		await cursor.execute("SELECT config FROM server_config WHERE (serverid = %s)", (serverid,))
		row = await cursor.fetchone()
		if row == None:
			return {}  # Blank config
		return json.loads(row[0])

	async def setConfig(self, cursor, serverid, config):
		jsonconfig = json.dumps(config)
		await cursor.execute("REPLACE INTO server_config (serverid, config) VALUES (%s, %s)", (serverid, jsonconfig))

	async def getConfigValue(self, serverid, path):
		cursor = await self.sqlBroker.connect()
		value = await self.getConfig(cursor, serverid)
		await self.sqlBroker.commit(cursor)
		path = path.split(".")
		for p in path:
			if not p in value:
				return None  # No such key
			value = value[p]
		return value

	async def setConfigValue(self, serverid, path, new):
		cursor = await self.sqlBroker.connect()
		config = await self.getConfig(cursor, serverid)
		value = config
		path = path.split(".")
		for p in path[0:len(path) - 1]:
			if not p in value:
				value[p] = {}  # Autovivify
			elif not isinstance(value[p], dict):
				value[p] = {}  # Overwrite scalar with dict
			value = value[p]
		value[path[-1]] = new
		await self.setConfig(cursor, serverid, config)
		await self.sqlBroker.commit(cursor)
		return

	async def removeConfigValue(self, serverid, path):
		cursor = await self.sqlBroker.connect()
		config = await self.getConfig(cursor, serverid)
		value = config
		path = path.split(".")
		for p in path[0:len(path) - 1]:
			if not p in value:
				await self.sqlBroker.rollback(cursor)
				return	# Non-existant parent element in path
			elif not isinstance(value[p], dict):
				await self.sqlBroker.rollback(cursor)
				return  # Parent element in path is not dict
			value = value[p]
		del value[path[-1]]
		await self.setConfig(cursor, serverid, config)
		await self.sqlBroker.commit(cursor)
		return
