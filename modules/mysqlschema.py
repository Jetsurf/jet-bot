import asyncio

class MysqlSchema():
	def __init__(self, mysqlhandler):
		self.sqlBroker = mysqlhandler

	async def update(self):
		print("Checking DB schema...")

		cur = await self.sqlBroker.connect()

		if not await self.sqlBroker.hasTable(cur, 'nso_app_version'):
			print("Creating table 'nso_app_version'...")
			await cur.execute("CREATE TABLE nso_app_version (version VARCHAR(32) NOT NULL, updatetime DATETIME NOT NULL)")
			await self.sqlBroker.c_commit(cur)

		if not await self.sqlBroker.hasTable(cur, 'commandcounts'):
			print("Creating table 'commandcounts'...")
			await cur.execute(
			"""
			CREATE TABLE commandcounts
			(
			serverid bigint NOT NULL,
			command varchar(32) NOT NULL,
			count int NOT NULL DEFAULT '0',
			PRIMARY KEY (serverid, command)
			) ENGINE=InnoDB
			"""
			)
			await self.sqlBroker.c_commit(cur)

		if not await self.sqlBroker.hasTable(cur, 'server_config'):
			print("Creating table 'server_config'...")
			await cur.execute(
			"""
			CREATE TABLE server_config
			(
			serverid bigint unsigned NOT NULL,
			config text,
			PRIMARY KEY (`serverid`)
			) ENGINE=InnoDB
			"""
			)
			await self.sqlBroker.c_commit(cur)

		if await self.sqlBroker.hasTable(cur, 'blacklist'):
			print("Removing table 'blacklist'...")
			await cur.execute("DROP TABLE blacklist")
			await self.sqlBroker.c_commit(cur)

		return
