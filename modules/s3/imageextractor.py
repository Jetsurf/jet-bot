from apscheduler.schedulers.asyncio import AsyncIOScheduler
import re
import requests
import asyncio
import cairosvg

MAX_AGE = 3600 * 24 * 90  # Cache for 90 days

IMAGES = [
	# Ranked modes
	{'cache': 's3.modes', 'key': 'SZ.png', 'size': [256, 256], 'pattern': r'^area\.[0-9a-f]+\.svg$'},
	{'cache': 's3.modes', 'key': 'TC.png', 'size': [256, 256], 'pattern': r'^yagura\.[0-9a-f]+\.svg$'},
	{'cache': 's3.modes', 'key': 'RM.png', 'size': [256, 256], 'pattern': r'^hoko\.[0-9a-f]+\.svg$'},
	{'cache': 's3.modes', 'key': 'CB.png', 'size': [256, 256], 'pattern': r'^asari\.[0-9a-f]+\.svg$'},
]

class S3ImageExtractor():
	def __init__(self, nsotoken, cachemanager):
		self.nsotoken     = nsotoken
		self.cachemanager = cachemanager
		self.caches       = {}

		self.scheduler = AsyncIOScheduler()
		self.scheduler.add_job(self.extract, 'interval', hours = 24)
		self.scheduler.start()

		self.create_caches()

		asyncio.create_task(self.extract())

	def create_caches(self):
		for rec in IMAGES:
			if not rec['cache'] in self.caches:
				self.caches[rec['cache']] = self.cachemanager.open(rec['cache'], MAX_AGE)

	async def extract(self):
		# Find records for uncached images
		uncached = []
		for rec in IMAGES:
			if not self.caches[rec['cache']].has(rec['key']):
				uncached.append(rec)

		if len(uncached) == 0:
			return  # Cache is already completely populated

		print(f"S3ImageExtractor(): There are uncached images. Let's try to extract...")

		nso = await self.nsotoken.get_bot_nso_client()
		if nso is None:
			return

		links = nso.s3.get_web_app_image_links()
		if links is None:
			print("get_web_app_image_links() failed")
			return

		for l in links:
			for rec in uncached:
				if re.match(rec['pattern'], l['filename']):
					await self.extract_svg_image(rec, l)
					break

	async def extract_svg_image(self, rec, link):
		print(f"S3ImageExtractor(): Grabbing SVG image: {link['url']}")

		# Grab the file
		res = requests.get(link['url'])
		if not res.ok:
			print(f"  Request failed: {res.status_code} {res.reason}")
			return

		# Convert to PNG
		bytes = cairosvg.svg2png(bytestring = res.content, output_width = rec['size'][0], output_height = rec['size'][1])

		# Save to cache
		self.caches[rec['cache']].add_bytes(rec['key'], bytes)
