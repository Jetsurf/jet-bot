import json
import re
import asyncio
import aiohttp
import urllib
import urllib.parse
import bs4

from enum import Enum

class UrlType(Enum):
	UNKNOWN = 0
	VIDEO = 1
	PLAYLIST = 2

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

	def url_info(self, url):
		parsed = urllib.parse.urlparse(url)
		if not parsed.hostname is None:
			if parsed.hostname == 'youtu.be':
				if match := re.match(r'/([-_A-Z0-9]{11})', parsed.path, re.IGNORECASE):
					return {'type': UrlType.VIDEO, 'videoId': match[1], 'url': f"https://youtu.be/{match[1]}"}
				return None
			elif re.match(r'^(?:[^.]+\.)?youtube(?:kids)?[.]com', parsed.hostname, re.IGNORECASE):
				args = urllib.parse.parse_qs(parsed.query)
				if (parsed.path == '/watch') and ('v' in args):
					return {'type': UrlType.VIDEO, 'videoId': args['v'][0], 'url': f"https://youtu.be/{args['v'][0]}"}
				elif (parsed.path == '/playlist') and ('list' in args):
					return {'type': UrlType.PLAYLIST, 'listId': args['list'][0], 'url': f"https://youtube.com/playlist?list={args['list'][0]}"}

		# Fallbacks in case of invalid URL syntax
		if match := re.search(r'youtu\.be/([-_A-Z0-9]{11})', url, re.IGNORECASE):
			return {'type': UrlType.VIDEO, 'videoId': match[1], 'url': f"https://youtu.be/{match[1]}"}
		elif match := re.search(r'youtube(?:kids)?\.com/watch\?v=([-_A-Z0-9]{11})', url, re.IGNORECASE):
			return {'type': UrlType.VIDEO, 'videoId': match[1], 'url': f"https://youtu.be/{match[1]}"}
		elif match := re.search(r'youtube(?:kids)?\.com/playlist\?list=([-_A-Z0-9]{13,})', url, re.IGNORECASE):
			return {'type': UrlType.PLAYLIST, 'listId': match[1], 'url': f"https://youtube.com/playlist?list={match[1]}"}

		return None  # Not a known Youtube URL

	def get_video_meta(self, soup):
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

	def get_playlist_meta(self, soup):
		details = {}

		meta = soup.find_all("meta")
		for m in meta:
			if "name" in m.attrs:
				if m.attrs['name'] == "title":
					details['title'] = m.attrs['content']

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
			print(f"[Youtube] Search for '{urlquery}' gave an error: {response.status} {response.reason} url '{response.url}'")
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

	async def get_video_details(self, url):
		url_info = self.url_info(url)
		if url_info is None:
			return None  # Couldn't understand URL
		elif url_info['type'] != UrlType.VIDEO:
			return None  # Not a video

		client = self.get_client()
		response = await client.get(url_info['url'])
		if not response.ok:
			print(f"[Youtube] Get video details from '{url}' gave an error: {response.status} {response.reason} url '{response.url}'")
			return None

		source = await response.text()
		soup = bs4.BeautifulSoup(source,'html5lib')

		details = self.get_video_meta(soup)
		details['url'] = url_info['url']  # Add canonicalized URL to details
		return details

	# Tries to grab playlist details from Youtube.
	# Note that Youtube only returns the first 100 videos in the inital
	#  response. If there are more videos than this, you'll only get
	#  the first 100.
	async def get_playlist_details(self, url):
		url_info = self.url_info(url)
		if url_info is None:
			return None  # Couldn't understand URL
		elif url_info['type'] != UrlType.PLAYLIST:
			return None  # Not a playlist

		client = self.get_client()
		response = await client.get(url_info['url'])
		if not response.ok:
			print(f"[Youtube] Get playlist details from '{url}' gave an error: {response.status} {response.reason} url '{response.url}'")
			return None

		source = await response.text()
		soup = bs4.BeautifulSoup(source,'html5lib')

		#details = self.get_playlist_meta(soup)
		response_json = self.get_yt_json(soup)
		if not response_json:
			print(f"[Youtube] Could not find response JSON for query '{urlquery}'")
			return None

		data = json.loads(response_json)

		details = {}
		details['url']        = url_info['url']
		details['listId']     = url_info['listId']
		details['title']      = data['header']['playlistHeaderRenderer']['title']['simpleText']
		details['videoCount'] = int(data['header']['playlistHeaderRenderer']['numVideosText']['runs'][0]['text'])

		try:
			contents = data['contents']['twoColumnBrowseResultsRenderer']['tabs'][0]['tabRenderer']['content']['sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents'][0]['playlistVideoListRenderer']['contents']
		except KeyError:
                        print(f"[Youtube] Could not find playlist contents in JSON")
                        return None

		videos = []
		for c in contents:
			if not "playlistVideoRenderer" in c:
				continue  # Not a video?
			elif not c['playlistVideoRenderer']['isPlayable']:
				continue  # Unplayable

			video = {}
			video['title']    = ' '.join(list(map(lambda e: e.get("text"), c['playlistVideoRenderer']['title']['runs'])))
			video['duration'] = int(c['playlistVideoRenderer']['lengthSeconds'])
			video['videoId']  = c['playlistVideoRenderer']['videoId']
			videos.append(video)

		details['videos'] = videos
		return details
