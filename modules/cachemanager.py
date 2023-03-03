import re, os, time
import asyncio
import aiohttp
import io

DEFAULT_MAX_AGE = 3600 * 24 * 90  # 90 days

class Cache():
	def __init__(self, manager, path, max_age):
		self.manager     = manager
		self.path        = path
		self.max_age     = max_age or DEFAULT_MAX_AGE
		self.fresh_age   = int(self.max_age * 0.9)
		self.http_client = None
		os.makedirs(self.path, exist_ok = True)

	def __del__(self):
		if self.http_client:
			asyncio.create_task(self.http_client.close())

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
		elif age > self.max_age:
			return False  # Past max age

		return True

	def is_fresh(self, key):
		age = self.get_age(key)
		if age is None:
			return False  # Does not exist
		elif age > self.fresh_age:
			return False  # Past freshness age

		return True

	def get_io(self, key):
		age = self.get_age(key)
		if age is None:
			return None  # Does not exist
		elif age > self.max_age:
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

		while buf := io.read(8192):
			file.write(buf)

		file.close()
		os.rename(tmppath, path)

	# Takes a PIL.Image and caches it.
	# Returns an io object containing the image data.
	def add_image(self, key, image, format = 'PNG'):
		image_io = io.BytesIO()
		image.save(image_io, format)
		image_io.seek(0)

		self.add_io(key, image_io)
		image_io.seek(0)

		return image_io

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

	# Takes an aiohttp.ClientResponse object.
	async def add_http_response_async(self, key, response):
		if not response.ok:
			print(f"Tried to cache unsuccessful HTTP response: {response.status_code} {response.reason} url '{response.url}'")
			return

		path = self.key_path(key)
		tmppath = path + ".part"

		file = self.create_file_exclusive(tmppath)
		if file is None:
			return  # Couldn't create file

		async for buf in response.content.iter_chunked(4096):
			file.write(buf)

		file.close()
		os.rename(tmppath, path)

	async def add_url(self, key, url):
		if self.http_client is None:
			self.http_client = aiohttp.ClientSession()

		response = await self.http_client.get(url)
		await self.add_http_response_async(key, response)

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
		return not re.match(r'^[A-Z0-9][-_.A-Z0-9]*$', name, flags = re.IGNORECASE) is None

	def __init__(self, path):
		self.path = path
		os.makedirs(self.path, exist_ok = True)

	def cache_name_to_path(self, cachename):
		parts = cachename.split(".")
		for p in parts:
			if not CacheManager.cache_name_part_valid(p):
				raise Exception("Invalid cache name")

		return "%s/%s/" % (self.path, "/".join(parts))

	def open(self, name, max_age = None):
		path = self.cache_name_to_path(name)
		return Cache(self, path, max_age)
