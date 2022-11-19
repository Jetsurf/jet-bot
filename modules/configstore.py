import json

class ConfigStore():
	def __init__(self, mysqlhandler, table_name, key_name):
		self.sql        = mysqlhandler
		self.table_name = table_name
		self.key_name   = key_name

	async def getConfig(self, cursor, key):
		await cursor.execute(f"SELECT config FROM `{self.table_name}` WHERE (`{self.key_name}` = %s)", (key,))
		row = await cursor.fetchone()
		if row == None:
			return {}  # Blank config
		return json.loads(row[0])

	async def setConfig(self, cursor, key, config):
		jsonconfig = json.dumps(config)
		await cursor.execute(f"REPLACE INTO `{self.table_name}` (`{self.key_name}`, config) VALUES (%s, %s)", (key, jsonconfig))

	async def getConfigValue(self, key, path):
		cursor = await self.sql.connect()
		value = await self.getConfig(cursor, key)
		await self.sql.commit(cursor)
		path = path.split(".")
		for p in path:
			if not p in value:
				return None  # No such key
			value = value[p]
		return value

	async def setConfigValue(self, key, path, new):
		cursor = await self.sql.connect()
		config = await self.getConfig(cursor, key)
		value = config
		path = path.split(".")
		for p in path[0:len(path) - 1]:
			if not p in value:
				value[p] = {}  # Autovivify
			elif not isinstance(value[p], dict):
				value[p] = {}  # Overwrite scalar with dict
			value = value[p]
		value[path[-1]] = new
		await self.setConfig(cursor, key, config)
		await self.sql.commit(cursor)
		return

	async def removeConfigValue(self, key, path):
		cursor = await self.sql.connect()
		config = await self.getConfig(cursor, key)
		value = config
		path = path.split(".")
		for p in path[0:len(path) - 1]:
			if not p in value:
				await self.sql.rollback(cursor)
				return	# Non-existant parent element in path
			elif not isinstance(value[p], dict):
				await self.sql.rollback(cursor)
				return  # Parent element in path is not dict
			value = value[p]
		if path[-1] in value:
			del value[path[-1]]
		await self.setConfig(cursor, key, config)
		await self.sql.commit(cursor)
		return

class UserConfig(ConfigStore):
        def __init__(self, mysqlhandler):
                super().__init__(mysqlhandler, 'user_config', 'userid')

class ServerConfig(ConfigStore):
        def __init__(self, mysqlhandler):
                super().__init__(mysqlhandler, 'server_config', 'serverid')
