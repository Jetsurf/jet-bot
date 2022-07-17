from bs4 import BeautifulSoup
import requests
import re

# TODO: This is an ugly hack. Look into using: https://github.com/JoMingyu/google-play-scraper
class GooglePlay():
	def getAppVersion(self, packageName):
		params = {'id': packageName, 'hl' : 'en_US'}
		headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:92.0) Gecko/20100101 Firefox/92.0'}
		response = requests.get('https://play.google.com/store/apps/details', params = params, headers = headers)
		if response.status_code != requests.codes.ok:
			print(f"getAppVersion(): Retrieving '{response.url}' got status code {response.status_code}")
			return None

		return self.getAppVersionFromHtml(response.text)

	def getAppVersionFromHtml(self, html):
		soup = BeautifulSoup(html, 'html5lib')
		scripts = soup.find_all(self.filterScriptElement)

		for s in scripts:
			match = re.search(r'\[\[\["([0-9]+([.][0-9]+)*)"', s.string)
			if match:
				return match[1]

		return None

	def filterScriptElement(self, tag):
		return (tag.name == 'script') and (tag.string != None) and ("AF_initDataCallback" in tag.string)
