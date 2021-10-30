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

		if not await self.sqlBroker.hasTable(cur, 'playlist'):
			print("Creating table 'playlist'...")
			await cur.execute(
			"""
			CREATE TABLE `playlist` (
  			`serverid` bigint unsigned NOT NULL,
  			`url` varchar(200) NOT NULL,
  			PRIMARY KEY (`serverid`)
			) ENGINE=InnoDB
			"""
			)
			await self.sqlBroker.c_commit(cur)

		if not await self.sqlBroker.hasTable(cur, 'dms'):
			print("Creating table 'dms'...")
			await cur.execute(
			"""
			CREATE TABLE `dms` (
  			`serverid` bigint unsigned NOT NULL,
  			`clientid` bigint unsigned NOT NULL,
  			PRIMARY KEY (`serverid`)
			) ENGINE=InnoDB
			"""
			)
			await self.sqlBroker.c_commit(cur)

		if not await self.sqlBroker.hasTable(cur, 'feeds'):
			print("Creating table 'feeds'...")
			await cur.execute(
			"""
			CREATE TABLE `feeds` (
			`serverid` bigint unsigned NOT NULL,
  			`channelid` bigint unsigned NOT NULL,
  			`maps` TINYINT NOT NULL,
  			`sr` TINYINT NOT NULL,
  			`gear` TINYINT NOT NULL,
  			PRIMARY KEY (`serverid`, `channelid`)
			) ENGINE=InnoDB
			"""
			)
			await self.sqlBroker.c_commit(cur)

		if not await self.sqlBroker.hasKey(cur, 'feeds', 'serverid') or not await self.sqlBroker.hasKey(cur, 'feeds', 'channelid'):
			print("Updating keys on table 'feeds'...")
			await cur.execute("ALTER TABLE feeds MODIFY serverid BIGINT unsigned NOT NULL, MODIFY channelid unsigned BIGINT NOT NULL")
			await cur.execute("ALTER TABLE feeds ADD PRIMARY KEY (`serverid`, `channelid`)")
			await self.sqlBroker.c_commit(cur)

		if not await self.sqlBroker.hasTable(cur, 'storedms'):
			print("Creating table 'storedms'...")
			await cur.execute(
			"""
			CREATE TABLE `storedms` (
  			`clientid` bigint unsigned NOT NULL,
  			`serverid` bigint unsigned NOT NULL,
  			`ability` varchar(25) COLLATE utf8mb4_general_ci DEFAULT NULL,
  			`brand` varchar(25) COLLATE utf8mb4_general_ci DEFAULT NULL,
  			`gearname` varchar(26) COLLATE utf8mb4_general_ci DEFAULT NULL,
  			KEY `clientid` (`clientid`)
			) ENGINE=InnoDB

			"""
			)
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
			PRIMARY KEY (`serverid`, `command`)
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

		if await self.sqlBroker.hasTable(cur, 'tokens') and not await self.sqlBroker.hasColumn(cur, 'tokens', 'game_keys'):
			if not await self.sqlBroker.hasTable(cur, 'tokens_migrate'):
				print("Renaming old-style 'tokens' table in preparation for migration...")
				await cur.execute("RENAME TABLE tokens TO tokens_migrate")
				await self.sqlBroker.c_commit(cur)

		if not await self.sqlBroker.hasTable(cur, 'tokens'):
			print("Creating table 'tokens'...")
			await cur.execute(
			"""
			CREATE TABLE tokens (
			clientid bigint unsigned NOT NULL,
			session_time datetime NOT NULL,
			session_token TEXT NOT NULL,
			game_keys TEXT NULL,
			game_keys_time DATETIME NULL,
			PRIMARY KEY(`clientid`)
			) ENGINE=InnoDB
			"""
			)
			await self.sqlBroker.c_commit(cur)

		if await self.sqlBroker.hasTable(cur, 'blacklist'):
			print("Removing table 'blacklist'...")
			await cur.execute("DROP TABLE blacklist")
			await self.sqlBroker.c_commit(cur)

		await self.sqlBroker.close(cur)
		return
