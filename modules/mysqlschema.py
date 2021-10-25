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

		if not await self.sqlBroker.hasTable(cur, 'tokens'):
			print("Creating table 'tokens'...")
			await cur.execute(
			"""
			CREATE TABLE tokens (
			clientid bigint(20) unsigned NOT NULL,
			session_time datetime NOT NULL,
			session_token TEXT NOT NULL,
			game_keys TEXT NULL,
			game_keys_time DATETIME NULL
			) ENGINE=InnoDB
			"""
			)
			await self.sqlBroker.c_commit(cur)

		if await self.sqlBroker.hasTable(cur, 'blacklist'):
			print("Removing table 'blacklist'...")
			await cur.execute("DROP TABLE blacklist")
			await self.sqlBroker.c_commit(cur)

		if not await self.sqlBroker.hasColumn(cur, 'tokens', 'game_keys'):
			print("Adding 'game_keys' and 'game_keys_time' columns to 'tokens' table...")
			await cur.execute("ALTER TABLE tokens ADD COLUMN game_keys TEXT NULL, ADD COLUMN game_keys_time DATETIME NULL");
			await self.sqlBroker.c_commit(cur)
			# TODO: Migrate existing keys

		return
