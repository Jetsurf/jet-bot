import os
import time
import PIL
from PIL import ImageFont

class Fonts:
	FALLBACK = "DejaVuSansCondensed.ttf"
	FONT_CACHE_SIZE = 16
	SIZE_CACHE_SIZE = 384

	def __init__(self, path):
		if path[-1] != '/':
			path += '/'

		self.path = path
		self.font_cache = {}
		self.size_cache = {}

	def truetype(self, name, size = 10):
		path = self.path + name
		if not os.path.exists(path):
			name = Fonts.FALLBACK
			path = self.path + name

		cachekey = f"{name}:{size}"
		if cachekey in self.font_cache:
			self.font_cache[cachekey]['lastusetime'] = time.time()
			return self.font_cache[cachekey]['font']

		font = PIL.ImageFont.truetype(path, size = size)
		self.font_cache[cachekey] = {"lastusetime": time.time(), "font": font}

		self.shrink_font_cache()

		return font

	# Returns a font sized appropriately to fit within the given maximum
	#  width.
	def truetype_for_width(self, name, max_size, max_width, string):
		size = self.size_for_width(self, name, max_size, max_width, string)
		return self.truetype(name, size)

	# Returns a font size such that the string when rendered fits within
	#  the given maximum width.
	def size_for_width(self, name, max_size, max_width, string):
		# We do a binary search for the largest font size up to the
		#  maximum that fits within the given space. For efficiency
		#  we check even-numbered sizes below the maximum size.
		#print(f"truetype_for_width(): name '{name}' max_size {max_size} string '{string}'")
		size = max_size
		best = None
		count = (size - 1).bit_length() - 1
		while (count >= 0) and (size > 0):
			#print(f"count {count} checking size {size}")
			width = self.check_string_width(name, size, string)
			if width <= max_width:
				if size == max_size:
					return max_size
				elif (best is None) or (size > best):
					best = size

				size = (size + (1 << count)) & -2
			else:
				size = (size - (1 << count)) & -2

			count = count - 1

		return best

	def check_string_width(self, name, size, string):
		cachekey = f"{name}:{size}:{string}"
		if cachekey in self.size_cache:
			self.size_cache[cachekey]['lastusetime'] = time.time()
			return self.size_cache[cachekey]['width']

		font = self.truetype(name, size)
		width = font.getlength(string)
		self.size_cache[cachekey] = {"lastusetime": time.time(), "width": width}

		self.shrink_size_cache()

		return width

	def shrink_cache(self, cache, max_size):
		if len(cache) <= max_size:
			return  # Already small enough

		# Find the least-recently-used cache entry
		oldest = None
		for k in cache.keys():
			if (oldest is None) or (cache[k]['lastusetime'] < cache[oldest]['lastusetime']):
				oldest = k

		if oldest is None:
			return  # No old entry?

		del cache[oldest]
		return oldest

	def shrink_font_cache(self):
		oldkey = self.shrink_cache(self.font_cache, Fonts.FONT_CACHE_SIZE)
		if oldkey:
			print(f"Fonts.shrink_font_cache(): Removed key '{oldkey}'")

	def shrink_size_cache(self):
		oldkey = self.shrink_cache(self.size_cache, Fonts.SIZE_CACHE_SIZE)
		if oldkey:
			print(f"Fonts.shrink_size_cache(): Removed key '{oldkey}'")
