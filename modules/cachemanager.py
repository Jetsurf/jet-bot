import re, os, time

class Cache():
	def __init__(self, manager, path, maxage):
		self.manager = manager
		self.path    = path
		self.maxage  = maxage
		os.makedirs(self.path, exist_ok = True)

	def key_path(self, key):
		if not CacheManager.key_name_valid(key):
			raise Exception("Invalid key name")

		path = f"{self.path}/{key}"
		return path

	def remove(self, key):
		path = self.key_path(key)

		try:
			os.unlink(path)
		except:
			print("Cache.remove(): Could not unlink '{path}'")

	def has(self, key):
		age = self.get_age(key)
		if age is None:
			return False  # Does not exist
		elif age > self.maxage:
			return False  # Past max age

		return True

	def get_io(self, key):
		age = self.get_age(key)
		if age is None:
			return None  # Does not exist
		elif age > self.maxage:
			return None  # Past max age

		path = self.key_path(key)
		try:
			io = open(path, "rb")
		except:
			return None

		return io

	def get_age(self, key):
		path = self.key_path(key)
		try:
			s = os.stat(path)
		except:
			return None

		return time.time() - s.st_mtime

	def create_file_exclusive(self, path):
		try:
			file = open(path, "xb")  # Exclusive mode to prevent races
		except FileExistsError:
			# Already exists. Unlink the old one and retry
			os.unlink(path)
			try:
				file = open(path, "xb")
			except FileExistsError:
				return None

		return file

	def add_io(self, key, io):
		path = self.key_path(key)
		tmppath = path + ".part"

		file = self.create_file_exclusive(tmppath)
		if file is None:
			return  # Couldn't create file

		while (buf := f.read(8192)) != '':
			file.write(buf)

		file.close()
		os.rename(tmppath, path)

	# Takes a requests.Response object. It's best to create it using stream = True:
	# response = requests.get(url, stream=True)
	def add_http_response(self, key, response):
		if not response.ok:
			print(f"Tried to cache unsuccessful HTTP response: {response.status_code} {response.reason} url '{response.url}'")
			return

		path = self.key_path(key)
		tmppath = path + ".part"

		file = self.create_file_exclusive(tmppath)
		if file is None:
			return  # Couldn't create file

		for buf in response.iter_content(chunk_size = None):
			file.write(buf)

		file.close()
		os.rename(tmppath, path)

	# Takes a byte string object.
	def add_bytes(self, key, bytes):
		path = self.key_path(key)
		tmppath = path + ".part"

		file = self.create_file_exclusive(tmppath)
		if file is None:
			return  # Couldn't create file

		file.write(bytes)
		file.close()
		os.rename(tmppath, path)

class CacheManager():
	@classmethod
	def cache_name_part_valid(cls, part):
		return not re.match(r'^[-A-Za-z0-9]{0,32}$', part, flags = re.IGNORECASE) is None

	# Key name must not start with period
	@classmethod
	def key_name_valid(cls, name):
		return not re.match(r'^[A-Z0-9][-.A-Z0-9]*$', name, flags = re.IGNORECASE) is None

	def __init__(self, path):
		self.path = path
		os.makedirs(self.path, exist_ok = True)

	def cache_name_to_path(self, cachename):
		parts = cachename.split(".")
		for p in parts:
			if not CacheManager.cache_name_part_valid(p):
				raise Exception("Invalid cache name")

		return "%s/%s/" % (self.path, "/".join(parts))

	def open(self, name, maxage):
		path = self.cache_name_to_path(name)
		return Cache(self, path, maxage)
