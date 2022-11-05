import os
import time
import PIL
from PIL import ImageFont

class Fonts:
	fallback = "DejaVuSansCondensed.ttf"
	cachesize = 8

	def __init__(self, path):
		if path[-1] != '/':
			path += '/'

		self.path  = path
		self.cache = {}

	def truetype(self, name, size = 10):
		path = self.path + name
		if not os.path.exists(path):
			name = Fonts.fallback
			path = self.path + name

		cachekey = f"{name}:{size}"
		if cachekey in self.cache:
			self.cache[cachekey]['lastusetime'] = time.time()
			return self.cache[cachekey]['font']

		font = PIL.ImageFont.truetype(path, size = size)
		self.cache[cachekey] = {"lastusetime": time.time(), "font": font}

		self.shrink_cache()

		return font

	def shrink_cache(self):
		if len(self.cache) <= Fonts.cachesize:
			return  # Already small enough

		# Find the least-recently-used cache entry
		oldest = None
		for k in self.cache.keys():
			if (oldest is None) or (self.cache[k]['lastusetime'] < self.cache[oldest]['lastusetime']):
				oldest = k

		print(f"Removing entry '{oldest}' from font cache")
		del self.cache[oldest]
