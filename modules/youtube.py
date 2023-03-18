import json
import re
import aiohttp
import urllib
import bs4

class Youtube():
	def __init__(self):
		self.http_client = None

	def __del__(self):
		if self.http_client:
			asyncio.create_task(self.http_client.close())

	def get_client(self):
		if self.http_client is None:
			self.http_client = aiohttp.ClientSession()

		return self.http_client

	def get_yt_meta(self, soup):
		details = {}

		meta = soup.find_all("meta")
		for m in meta:
			if "itemprop" in m.attrs:
				if m.attrs['itemprop'] == "name":
					details['title'] = m.attrs['content']
				elif m.attrs['itemprop'] == "duration":
					details['duration'] = self.decode_duration(m.attrs['content'])
				elif m.attrs['itemprop'] == "videoId":
					details['videoId'] = m.attrs['content']
		return details

	def get_yt_json(self, soup):
		scripts = soup.find_all("script")
		for s in scripts:
			text = s.string
			if text is None:
				continue
			if (re.search(r'var ytInitialData =', text)):
				text = re.sub(r'^\s*var ytInitialData\s*=\s*', '', text)  # Slice off leading JS
				text = re.sub(r';\s*$', '', text)  # Slice off trailing semicolon
				return text
		return None

	# Given a duration string like "PT4M49S", returns integer seconds.
	# https://en.wikipedia.org/wiki/ISO_8601#Durations
	def decode_duration(self, duration):
		seconds = 0
		if match := re.search(r'([0-9]+)S', duration):
			seconds = int(match[1])

		minutes = 0
		if match := re.search(r'([0-9]+)M', duration):
			minutes = int(match[1])

		hours = 0
		if match := re.search(r'([0-9]+)H', duration):
			hours = int(match[1])

		return (hours * 60 * 60) + (minutes * 60) + seconds

	def decode_vidlist(self, vidlist):
		vids = []
		for e in vidlist:
			if not e.get('itemSectionRenderer'):
				continue  # Section does not contain videos
			contents = e['itemSectionRenderer']['contents']
			for result in contents:
				r = result.get('videoRenderer')
				if r:
					if r.get('upcomingEventData'):
						continue  # Scheduled upcoming video
					vid = {}
					vid['title'] = ' '.join(list(map(lambda e: e.get("text"), r['title']['runs'])))
					vid['videoId'] = r['videoId']
					if r.get('lengthText'):
						vid['length'] = r['lengthText']['simpleText']
					vids.append(vid)
		return vids

	async def search(self, query):
		urlquery = urllib.parse.quote(query)
		urlquery.replace("%20", "+")
		url = f"https://youtube.com/results?search_query={urlquery}"

		client = self.get_client()
		response = await client.get(url)
		if not response.ok:
			print(f"[Youtube] Search for '{urlquery}' gave an error: {response.status_code} {response.reason} url '{response.url}'")
			return None

		source = await response.text()
		soup = bs4.BeautifulSoup(source,'html5lib')
		response_json = self.get_yt_json(soup)
		if not response_json:
			print(f"[Youtube] Could not find response JSON for query '{urlquery}'")
			return None

		data = json.loads(response_json)
		try:
			vidlist = data['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents']
		except KeyError:
			print(f"[Youtube] Could not find vidlist in search response")
			return None

		try:
			vids = self.decode_vidlist(vidlist)
		except Exception as e:
			print("--- Exception decoding Youtube vidlist ---")
			print(traceback.format_exc())
			print(f"Vidlist was: {repr(vidlist)}")
			print(f"Search was: {query}")
			raise

		return vids

	async def get_details(self, url):
		if not re.match(r'^https?://(?:www[.])?youtube[.]com/', url):
			return None

		client = self.get_client()
		response = await client.get(url)
		if not response.ok:
			print(f"[Youtube] Get details from '{url}' gave an error: {response.status_code} {response.reason} url '{response.url}'")
			return None

		source = await response.text()
		soup = bs4.BeautifulSoup(source,'html5lib')

		details = self.get_yt_meta(soup)
		return details
