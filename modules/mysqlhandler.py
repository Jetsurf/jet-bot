import asyncio
import aiomysql
import traceback
import pdb
import re

class mysqlHandler():
	def __init__(self, host, user, pw, db):
		self.__host = host
		self.__user = user
		self.__pw = pw
		self.__db = db
		self.pool = None
		self.cons = {}
		self.traces = {}

	# On bot startup, the mysql connection may not be ready yet. We can
	#  use this to wait for it.
	async def wait_for_startup(self):
		for i in range(10):
			if self.pool is None:
				await asyncio.sleep(1)

		return self.pool is not None

	async def startUp(self):
		self.pool = await aiomysql.create_pool(host=self.__host, port=3306, user=self.__user, password=self.__pw, db=self.__db, maxsize=25)
		print("MYSQL: Created connection pool")

	def context(self, *args):
		return MysqlContext(self, *args)

	def getDatabaseName(self):
		return self.__db

	def escapeTableName(self, name):
		if not re.fullmatch(r'^[a-z_][a-z0-9_]*$', name, re.IGNORECASE):
			raise Exception("Invalid characters in table name")

		return f"`{name}`"

	async def connect(self, *args):
		con = await self.pool.acquire()
		cur = await con.cursor(*args)
		self.traces[hash(cur)] = traceback.format_stack()[:-1]
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
		for con in self.cons:
			print(f"DEBUG: {str(con)} + {''.join(self.traces[hash(con)])}")
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

class MysqlContext():
	def __init__(self, broker, *args):
		if len(args) == 0:
			args = [aiomysql.DictCursor]

		self.broker = broker
		self.args   = args
		self.valid  = False
		self.cur    = None

	async def __aenter__(self):
		#print(f"Entering SQL context {repr(self)}")
		self.cur = await self.broker.connect(*self.args)
		self.valid = True
		return self

	async def __aexit__(self, exc_type, exc_value, exc_tb):
		if exc_type is None:
			if self.valid:
				#print(f"Leaving SQL context normally {repr(self)}")
				await self.broker.commit(self.cur)
			else:
				print(f"Leaving SQL context after rollback {repr(self)}")
				await self.broker.close(self.cur)
		else:
			print(f"Leaving SQL context due to exception {repr(self)}")
			self.valid = False
			await self.broker.rollback(self.cur)
			return False  # Allow exception to propagate

	@property
	def lastrowid(self):
		return self.cur.lastrowid

	async def commit(self):
		await self.broker.c_commit(self.cur)

	async def rollback(self):
		self.valid = False
		await self.broker.c_rollback(self.cur)

	# Convenience method for executing a query and returning all rows
	async def query(self, stmt, args = ()):
		if not self.valid:
			raise Exception("Attempt to call query() on invalid SQL context")

		await self.cur.execute(stmt, args)
		rows = await self.cur.fetchall()
		return rows

	# Convenience method for executing a query and returning the first row
	async def query_first(self, stmt, args = ()):
		if not self.valid:
			raise Exception("Attempt to call query_first() on invalid SQL context")

		await self.cur.execute(stmt, args)
		row = await self.cur.fetchone()
		return row
