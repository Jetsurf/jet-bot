import asyncio
import aiomysql

class mysqlHandler():
	def __init__(self, host, user, pw, db):
		self.__host = host
		self.__user = user
		self.__pw = pw
		self.__db = db
		self.pool = None
		self.cons = {}

	async def startUp(self):
		self.pool = await aiomysql.create_pool(host=self.__host, port=3306, user=self.__user, password=self.__pw, db=self.__db, maxsize=25)
		print("MYSQL: Created connection pool")

	async def connect(self):
		con = await self.pool.acquire()
		cur = await con.cursor()
		self.cons[hash(cur)] = con
		return cur

	async def c_commit(self, cur):
		await self.cons[hash(cur)].commit()

	async def c_rollback(self, cur):
		await self.cons[hash(cur)].rollback()

	async def commit(self, cur):
		await self.cons[hash(cur)].commit()
		await self.close(cur)

	async def rollback(self, cur):
		await self.cons[hash(cur)].rollback()
		await self.close(cur)

	def getColumnNames(self, cur):
		return [col[0] for col in cur.description]

	def rowToDict(self, colnames, row):
		return dict(zip(colnames, row))

	async def hasTable(self, cur, tablename):
		await cur.execute("SELECT 1 FROM information_schema.TABLES WHERE (TABLE_SCHEMA = %s) AND (TABLE_NAME = %s) LIMIT 1", (self.__db, tablename))
		row = await cur.fetchone()
		await self.c_commit(cur)
		if row == None:
			return False
		return True

	async def hasColumn(self, cur, tablename, columnname):
		await cur.execute("SELECT 1 FROM information_schema.COLUMNS WHERE (TABLE_SCHEMA = %s) AND (TABLE_NAME = %s) AND (COLUMN_NAME = %s) LIMIT 1", (self.__db, tablename, columnname))
		row = await cur.fetchone()
		await self.c_commit(cur)
		if row == None:
			return False
		return True

	async def hasKey(self, cur, tablename, keyname):
		await cur.execute("SELECT * FROM information_schema.STATISTICS WHERE (TABLE_SCHEMA = %s) AND (TABLE_NAME = %s) AND (COLUMN_NAME = %s)", (self.__db, tablename, keyname,))
		row = await cur.fetchone()
		await self.c_commit(cur)
		if row == None:
			return False
		return True

	async def printCons(self, message):
		await message.channel.send("MySQL Connections: " + str(self.cons))

	async def getConnection(self, cur):
		return self.cursors[hash(cur)]

	async def close(self, cur):
		con = self.cons[hash(cur)]
		await cur.close()
		self.pool.release(con)
		self.cons.pop(hash(cur))

	async def close_pool(self):
		self.pool.close()
		await self.pool.wait_closed()
		print("MYSQL: Closed Pool")
