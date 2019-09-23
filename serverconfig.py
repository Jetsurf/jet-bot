import json
import mysql.connector
from mysql.connector.cursor import MySQLCursorPrepared

class ServerConfig():
	def __init__(self, mysqlinfo):
		self.db        = None
		self.mysqlinfo = mysqlinfo

	def connect(self):
		if self.db == None:
			self.db = mysql.connector.connect(host=self.mysqlinfo.host, user=self.mysqlinfo.user, password=self.mysqlinfo.pw, database=self.mysqlinfo.db)
			self.db.autocommit = True
		self.db.ping(True, 2, 1)
		cursor = self.db.cursor(cursor_class=MySQLCursorPrepared)
		return cursor

	def getConfig(self, cursor, serverid):
		cursor.execute("SELECT config FROM server_config WHERE (serverid = %s)", (serverid,))
		row = cursor.fetchone()
		cursor.close()
		if row == None:
			return {}  # Blank config
		return json.loads(row[0].decode("utf-8"))

	def setConfig(self, cursor, serverid, config):
		jsonconfig = json.dumps(config)
		cursor.execute("REPLACE INTO server_config (serverid, config) VALUES (%s, %s)", (serverid, jsonconfig))
		cursor.close()

	def getConfigValue(self, serverid, path):
		cursor = self.connect()
		value = self.getConfig(cursor, serverid)
		path = path.split(".")
		for p in path:
			if not p in value:
				return None  # No such key
			value = value[p]
		return value

	def setConfigValue(self, serverid, path, new):
		cursor = self.connect()
		config = self.getConfig(cursor, serverid)
		value = config
		path = path.split(".")
		for p in path[0:len(path) - 1]:
			print(p + "\t" + str(type(value[p])))
			if not p in value:
				value[p] = {}  # Autovivify
			elif not isinstance(value[p], dict):
				value[p] = {}  # Overwrite scalar with dict
			value = value[p]
		value[path[-1]] = new
		self.setConfig(cursor, serverid, config)
		cursor.execute("COMMIT")
		return

	def removeConfigValue(self, serverid, path):
		cursor = self.connect()
		cursor.execute("START TRANSACTION")
		config = self.getConfig(cursor, serverid)
		value = config
		path = path.split(".")
		for p in path[0:len(path) - 1]:
			if not p in value:
				cursor.execute("ROLLBACK")
				return	# Non-existant parent element in path
			elif not isinstance(value[p], dict):
				cursor.execute("ROLLBACK")
				return  # Parent element in path is not dict
			value = value[p]
		del value[path[-1]]
		self.setConfig(cursor, serverid, config)
		cursor.execute("COMMIT")
		return
