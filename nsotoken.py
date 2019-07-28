from __future__ import print_function
import requests, json, re, sys
import os, base64, hashlib, random, string
import uuid, time
import nsohandler

class Nsotoken():
	def __init__(self, client, nsohandler):
		self.client = client
		self.session = requests.Session()
		self.nsohandler = nsohandler

	async def login(self, message):
		auth_state = base64.urlsafe_b64encode(os.urandom(36))
		auth_code_verifier = base64.urlsafe_b64encode(os.urandom(32))
		auth_cv_hash = hashlib.sha256()
		auth_cv_hash.update(auth_code_verifier.replace(b"=", b""))
		auth_code_challenge = base64.urlsafe_b64encode(auth_cv_hash.digest())
		head = {
			'Host':                      'accounts.nintendo.com',
			'Connection':                'keep-alive',
			'Cache-Control':             'max-age=0',
			'Upgrade-Insecure-Requests': '1',
			'User-Agent':                'Mozilla/5.0 (Linux; Android 7.1.2; Pixel Build/NJH47D; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/59.0.3071.125 Mobile Safari/537.36',
			'Accept':                    'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8n',
			'DNT':                       '1',
			'Accept-Encoding':           'gzip,deflate,br',
		}
		body = {
			'state':                                auth_state,
			'redirect_uri':                         'npf71b963c1b7b6d119://auth',
			'client_id':                            '71b963c1b7b6d119',
			'scope':                                'openid user user.birthday user.mii user.screenName',
			'response_type':                        'session_token_code',
			'session_token_code_challenge':         auth_code_challenge.replace(b"=", b""),
			'session_token_code_challenge_method': 'S256',
			'theme':                               'login_form'
		}
		r = self.session.get('https://accounts.nintendo.com/connect/1.0.0/authorize', headers=head, params=body)

		post_login = r.history[0].url

		#await self.client.send_message(message.channel, "Sorry, this functionality is currently broken, see https://github.com/frozenpandaman/splatnet2statink/issues/79 for further info")
		#return

		await self.client.send_message(message.channel, "Navigate to this URL in your browser: " + post_login)
		await self.client.send_message(message.channel, "Log in, right click the \"Select this person\" button, copy the link address, and paste it back to me")

		while True:
			accounturl = await self.client.wait_for_message(author=message.author, channel=message.channel)
			accounturl = accounturl.content
			if 'npf71b963c1b7b6d119' not in accounturl:
				await self.client.send_message(message.channel, "Invalid URL, please copy the link in \"Select this person\"")
			else:
				break

		session_token_code = re.search('session_token_code=(.*)&', accounturl)
		session_token_code = self.get_session_token(session_token_code.group(0)[19:-1], auth_code_verifier)
		thetoken = self.get_cookie(session_token_code)
		await self.nsohandler.addToken(message, str(thetoken))

	def get_hash(self, id_token, timestamp):
		version = '1.5.1'
		api_app_head = { 'User-Agent': "splatnet2statink/{}".format(version) }
		api_body = { 'naIdToken': id_token, 'timestamp': timestamp }
		api_response = requests.post("https://elifessler.com/s2s/api/gen2", headers=api_app_head, data=api_body)
		return json.loads(api_response.text)["hash"]

	def get_session_token(self, session_token_code, auth_code_verifier):
		head = {
			'User-Agent':      'OnlineLounge/1.5.0 NASDKAPI Android',
			'Accept-Language': 'en-US',
			'Accept':          'application/json',
			'Content-Type':    'application/x-www-form-urlencoded',
			'Content-Length':  '540',
			'Host':            'accounts.nintendo.com',
			'Connection':      'Keep-Alive',
			'Accept-Encoding': 'gzip'
		}
		body = {
			'client_id':                   '71b963c1b7b6d119',
			'session_token_code':          session_token_code,
			'session_token_code_verifier': auth_code_verifier.replace(b"=", b"")
		}

		r = self.session.post('https://accounts.nintendo.com/connect/1.0.0/api/session_token', headers=head, data=body)
		return json.loads(r.text)["session_token"]

	def call_flapg(self, id_token, guid, timestamp):
		api_app_head = {
			'x-token': id_token,
			'x-time':  str(timestamp),
			'x-guid':  guid,
			'x-hash':  self.get_hash(id_token, timestamp),
			'x-ver':   '2',
			'x-iid':   ''.join([random.choice(string.ascii_letters + string.digits) for n in range(8)])
		}
		api_response = requests.get("https://flapg.com/ika2/api/login", headers=api_app_head)
		f = json.loads(api_response.text)
		return f

	def get_cookie(self, session_token):
		timestamp = int(time.time())
		guid = str(uuid.uuid4())

		head = {
			'Host': 'accounts.nintendo.com',
			'Accept-Encoding': 'gzip',
			'Content-Type': 'application/json; charset=utf-8',
			'Accept-Language': 'en-US',
			'Content-Length': '437',
			'Accept': 'application/json',
			'Connection': 'Keep-Alive',
			'User-Agent': 'OnlineLounge/1.5.0 NASDKAPI Android'
		}
		body = {
			'client_id': '71b963c1b7b6d119',
			'session_token': session_token,
			'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer-session-token'
		}

		r = requests.post("https://accounts.nintendo.com/connect/1.0.0/api/token", headers=head, json=body)
		id_response = json.loads(r.text)
		head = {
			'User-Agent': 'OnlineLounge/1.5.0 NASDKAPI Android',
			'Accept-Language': 'en-US',
			'Accept': 'application/json',
			'Authorization': 'Bearer ' + id_response["access_token"],
			'Host': 'api.accounts.nintendo.com',
			'Connection': 'Keep-Alive',
			'Accept-Encoding': 'gzip'
		}

		r = requests.get("https://api.accounts.nintendo.com/2.0.0/users/me", headers=head)
		user_info = json.loads(r.text)
		head = {
			'Host': 'api-lp1.znc.srv.nintendo.net',
			'Accept-Language': 'en-US',
			'User-Agent': 'com.nintendo.znca/1.5.0 (Android/7.1.2)',
			'Accept': 'application/json',
			'X-ProductVersion': '1.5.0',
			'Content-Type': 'application/json; charset=utf-8',
			'Connection': 'Keep-Alive',
			'Authorization': 'Bearer',
			'Content-Length': '1036',
			'X-Platform': 'Android',
			'Accept-Encoding': 'gzip'
		}

		idToken = id_response["id_token"]
		flapg_response = self.call_flapg(idToken, guid, timestamp)
		flapg_nso = flapg_response["login_nso"]
		flapg_app = flapg_response["login_app"]
		
		parameter = {
			'f':          flapg_nso["f"],
			'naIdToken':  flapg_nso["p1"],
			'timestamp':  flapg_nso["p2"],
			'requestId':  flapg_nso["p3"],
			'naIdToken': idToken,
			'naCountry': user_info["country"],
			'naBirthday': user_info["birthday"],
			'language': user_info["language"],
			'requestId': guid,
			'timestamp': timestamp
		}
		body = {}
		body["parameter"] = parameter

		r = requests.post("https://api-lp1.znc.srv.nintendo.net/v1/Account/Login", headers=head, json=body)
		splatoon_token = json.loads(r.text)
		
		head = {
			'Host': 'api-lp1.znc.srv.nintendo.net',
			'User-Agent': 'com.nintendo.znca/1.5.0 (Android/7.1.2)',
			'Accept': 'application/json',
			'X-ProductVersion': '1.5.0',
			'Content-Type': 'application/json; charset=utf-8',
			'Connection': 'Keep-Alive',
			'Authorization': 'Bearer ' + splatoon_token["result"]["webApiServerCredential"]["accessToken"],
			'Content-Length': '37',
			'X-Platform': 'Android',
			'Accept-Encoding': 'gzip'
		}
		parameter = {
			'id': 5741031244955648,
			'f':                 flapg_app["f"],
			'registrationToken': flapg_app["p1"],
			'timestamp':         flapg_app["p2"],
			'requestId':         flapg_app["p3"]
		}

		body = {}
		body["parameter"] = parameter

		r = requests.post("https://api-lp1.znc.srv.nintendo.net/v2/Game/GetWebServiceToken", headers=head, json=body)
		token = json.loads(r.text)

		print(str(token))
		head = {
			'Host': 'app.splatoon2.nintendo.net',
			'X-IsAppAnalyticsOptedIn': 'false',
			'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
			'Accept-Encoding': 'gzip,deflate',
			'X-GameWebToken': token["result"]["accessToken"],
			'Accept-Language': 'en-US',
			'X-IsAnalyticsOptedIn': 'false',
			'Connection': 'keep-alive',
			'DNT': '0',
			'User-Agent': 'Mozilla/5.0 (Linux; Android 7.1.2; Pixel Build/NJH47D; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/59.0.3071.125 Mobile Safari/537.36',
			'X-Requested-With': 'com.nintendo.znca'
		}

		r = requests.get("https://app.splatoon2.nintendo.net/?lang=en-US", headers=head)
		print("Got a token!")
		return r.cookies["iksm_session"]