import asyncio

class MysqlSchema():
	def __init__(self, mysqlhandler):
		self.sqlBroker = mysqlhandler

	async def update(self):
		print("Checking DB schema...")

		cur = await self.sqlBroker.connect()

		if await self.sqlBroker.hasTable(cur, 'feeds') and not await self.sqlBroker.hasTable(cur, 's2_feeds'):
			print("Renaming table 'feeds' to 's2_feeds'...")
			await cur.execute("RENAME TABLE feeds TO s2_feeds")
			await self.sqlBroker.c_commit(cur)

		if await self.sqlBroker.hasTable(cur, 'storedms') and not await self.sqlBroker.hasTable(cur, 's2_storedms'):
			print("Renaming table 'storedms' to 's2_storedms'...")
			await cur.execute("RENAME TABLE storedms TO s2_storedms")
			await self.sqlBroker.c_commit(cur)

		if await self.sqlBroker.hasTable(cur, 'nso_app_version'):
			print("Removing table 'nso_app_version'...")
			await cur.execute("DROP TABLE nso_app_version")
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

		if not await self.sqlBroker.hasTable(cur, 's2_feeds'):
			print("Creating table 's2_feeds'...")
			await cur.execute(
			"""
			CREATE TABLE `s2_feeds` (
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

		if not await self.sqlBroker.hasTable(cur, 's3feeds'):
			print("Creating table 's3feeds'...")
			await cur.execute(
			"""
			CREATE TABLE `s3feeds` (
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

		if not await self.sqlBroker.hasKey(cur, 's2_feeds', 'serverid') or not await self.sqlBroker.hasKey(cur, 's2_feeds', 'channelid'):
			print("Updating keys on table 'feeds'...")
			await cur.execute("ALTER TABLE feeds MODIFY serverid BIGINT unsigned NOT NULL, MODIFY channelid BIGINT unsigned NOT NULL")
			await cur.execute("ALTER TABLE feeds ADD PRIMARY KEY (`serverid`, `channelid`)")
			await self.sqlBroker.c_commit(cur)

		if not await self.sqlBroker.hasTable(cur, 's2_storedms'):
			print("Creating table 's2_storedms'...")
			await cur.execute(
			"""
			CREATE TABLE `s2_storedms` (
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

		if not await self.sqlBroker.hasTable(cur, 'nso_client_keys'):
			print("Creating table 'nso_client_keys'...")
			await cur.execute(
			"""
			CREATE TABLE nso_client_keys (
			clientid   BIGINT UNSIGNED NOT NULL,
			updatetime DATETIME NOT NULL,
			jsonkeys   TEXT NULL,
			PRIMARY KEY(clientid)
			) ENGINE=InnoDB
			"""
			)
			await self.sqlBroker.c_commit(cur)

		if not await self.sqlBroker.hasTable(cur, 'nso_global_data'):
			print("Creating table 'nso_global_data'...")
			await cur.execute(
			"""
			CREATE TABLE nso_global_data
			(
			updatetime DATETIME NOT NULL,
			jsondata TEXT NULL
			) ENGINE = InnoDB
			"""
			)
			await self.sqlBroker.c_commit(cur)

		if not await self.sqlBroker.hasTable(cur, 'emotes'):
			print("Creating table 'emotes'...")
			await cur.execute(
			"""
			CREATE TABLE emotes (
			myid bigint unsigned NOT NULL,
			turfwar TEXT NOT NULL,
			ranked TEXT NOT NULL,
			league TEXT NOT NULL,
			badge100k TEXT NOT NULL,
			badge500k TEXT NOT NULL,
			badge1m TEXT NOT NULL,
			badge10m TEXT NOT NULL,
			PRIMARY KEY (`myid`)
			) ENGINE=InnoDB
			"""
			)
			await self.sqlBroker.c_commit(cur)

		if not await self.sqlBroker.hasTable(cur, 'friend_codes'):
			print("Creating table 'friend_codes'...")
			await cur.execute(
			"""
			CREATE TABLE friend_codes (
			userid                BIGINT UNSIGNED NOT NULL,
			updatetime            DATETIME NOT NULL,
			encrypted_friend_code TEXT NOT NULL,
			PRIMARY KEY(userid)
			) ENGINE=InnoDB
			"""
			)
			await self.sqlBroker.c_commit(cur)

		if not await self.sqlBroker.hasTable(cur, 'group_channels'):
			print("Creating table 'group_channels'...")
			await cur.execute(
			"""
			CREATE TABLE group_channels (
			guildid BIGINT UNSIGNED NOT NULL,
			channelid BIGINT UNSIGNED NOT NULL,
			PRIMARY KEY(guildid)
			) ENGINE = InnoDB
			"""
			)
			await self.sqlBroker.c_commit(cur)

		if not await self.sqlBroker.hasTable(cur, 'group_games'):
			print("Creating table 'group_games'...")
			await cur.execute(
			"""
			CREATE TABLE group_games (
			groupid     INT AUTO_INCREMENT NOT NULL,
			guildid     BIGINT UNSIGNED NOT NULL,
			ownerid     BIGINT UNSIGNED NOT NULL,
			messageid   BIGINT UNSIGNED NULL,
			starttime   DATETIME NOT NULL,
			duration    INT NOT NULL,
			playercount INT NOT NULL,
			gametype    VARCHAR(64) NOT NULL,
			members     TEXT NOT NULL,
			PRIMARY KEY(groupid)
			) ENGINE = InnoDB
			"""
			)
			await self.sqlBroker.c_commit(cur)

		if not await self.sqlBroker.hasTable(cur, 's3storedms'):
			print("Creating table 's3storedms'...")
			await cur.execute(
			"""
			CREATE TABLE s3storedms
			(
			serverid BIGINT unsigned NOT NULL,
			clientid BIGINT unsigned NOT NULL,
			dmtriggers TEXT,
			PRIMARY KEY (`clientid`)
			) ENGINE=InnoDB
			"""
			)
			await self.sqlBroker.c_commit(cur)

		if not await self.sqlBroker.hasTable(cur, 's3_schedule_update'):
			print("Creating table 's3_schedule_update'...")
			await cur.execute(
			"""
			CREATE TABLE s3_schedule_update
			(
			updatetime DATETIME NOT NULL
			) ENGINE = InnoDB
			"""
			)
			await self.sqlBroker.c_commit(cur)

		if not await self.sqlBroker.hasTable(cur, 's3_schedule_periods'):
			print("Creating table 's3_schedule_periods'...")
			await cur.execute(
			"""
			CREATE TABLE s3_schedule_periods
			(
			schedule  CHAR(2) NOT NULL,
			starttime DATETIME NOT NULL,
			endtime   DATETIME NOT NULL,
			jsondata  TEXT NULL,
			PRIMARY KEY(schedule, starttime)
			) ENGINE = InnoDB
			"""
			)
			await self.sqlBroker.c_commit(cur)

		await self.sqlBroker.close(cur)
		return
