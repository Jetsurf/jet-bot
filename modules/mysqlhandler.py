import asyncio
import aiomysql

class mysqlHandler():
	def __init__(self, host, user, pw, db):
		self.host = host
		self.user = user
		self.pw = pw
		self.db = db
		self.pool = None
		self.cons = {}

	async def startUp(self):
		self.pool = await aiomysql.create_pool(host=self.host, port=3306, user=self.user, password=self.pw, db=self.db)
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