import json

class ServerConfig():
	def __init__(self, mysqlhandler):
		self.db        = None
		self.sqlBroker = mysqlhandler

	async def getConfig(self, sql, serverid):
		row = await sql.query_first("SELECT config FROM server_config WHERE (serverid = %s)", (serverid,))
		if row == None:
			return {}  # Blank config
		return json.loads(row['config'])

	async def setConfig(self, sql, serverid, config):
		jsonconfig = json.dumps(config)
		await sql.query("REPLACE INTO server_config (serverid, config) VALUES (%s, %s)", (serverid, jsonconfig))

	async def getConfigValue(self, serverid, path):
		async with self.sqlBroker.context() as sql:
			config = await self.getConfig(sql, serverid)

		value = config
		path = path.split(".")
		for p in path:
			if not p in value:
				return None  # No such key
			value = value[p]
		return value

	async def setConfigValue(self, serverid, path, new):
		async with self.sqlBroker.context() as sql:
			config = await self.getConfig(sql, serverid)

			value = config
			path = path.split(".")
			for p in path[0:len(path) - 1]:
				if not p in value:
					value[p] = {}  # Autovivify
				elif not isinstance(value[p], dict):
					value[p] = {}  # Overwrite scalar with dict
				value = value[p]
			value[path[-1]] = new

			await self.setConfig(sql, serverid, config)

		return

	async def removeConfigValue(self, serverid, path):
		async with self.sqlBroker.context() as sql:
			config = await self.getConfig(sql, serverid)

			value = config
			path = path.split(".")
			for p in path[0:len(path) - 1]:
				if not p in value:
					return	# Non-existant parent element in path
				elif not isinstance(value[p], dict):
					return  # Parent element in path is not dict
				value = value[p]

			if path[-1] in value:
				del value[path[-1]]
				await self.setConfig(sql, serverid, config)

		return
