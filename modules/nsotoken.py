from __future__ import print_function
import mysqlhandler, nsohandler
import requests, json, re, sys, uuid, time
import os, base64, hashlib, random, string
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import googleplay

class Nsotoken():
	def __init__(self, client, mysqlhandler):
		self.client = client
		self.session = requests.Session()
		self.sqlBroker = mysqlhandler
		self.scheduler = AsyncIOScheduler()
		self.scheduler.add_job(self.updateAppVersion, 'cron', hour="3", minute='0', second='35')

	async def ensureAppVersionTable(self, cur):
		await cur.execute("SHOW TABLES LIKE 'nso_app_version'")
		row = await cur.fetchone()
		await self.sqlBroker.c_commit(cur)
		if row == None:
			await cur.execute("CREATE TABLE nso_app_version (version VARCHAR(32) NOT NULL, updatetime DATETIME NOT NULL)")
			await self.sqlBroker.c_commit(cur)

	async def getAppVersion(self):
		cur = await self.sqlBroker.connect()
		await self.ensureAppVersionTable(cur)

		await cur.execute("SELECT version, UNIX_TIMESTAMP(updatetime) AS updatetime FROM nso_app_version")
		row = await cur.fetchone()
		await self.sqlBroker.commit(cur)

		if row:
			return {'version': row[0], 'updatetime': row[1]}

		return None

	async def updateAppVersion(self):
		oldInfo = await self.getAppVersion()
		if oldInfo != None:
			age = time.time() - oldInfo['updatetime']
			if age < 3600:
				print("Skipping NSO version check -- cached data is recent")
				return

		gp = googleplay.GooglePlay()
		newVersion = gp.getAppVersion("com.nintendo.znca")
		if newVersion == None:
			print(f"Couldn't retrieve NSO app version?")
			return

		cur = await self.sqlBroker.connect()

		if (oldInfo == None) or (oldInfo['version'] != newVersion):
			# Version was updated
			await cur.execute("DELETE FROM nso_app_version")
			await cur.execute("INSERT INTO nso_app_version (version, updatetime) VALUES (%s, NOW())", (newVersion,))
			print(f"Updated NSO version: {oldInfo['version'] if oldInfo else '(none)'} -> {newVersion}")
		else:
			# No version change, so just bump the timestamp
			await cur.execute("UPDATE nso_app_version SET updatetime = NOW()")

		await self.sqlBroker.commit(cur)
		return

	async def checkDuplicate(self, id, cur):
		stmt = "SELECT COUNT(*) FROM tokens WHERE clientid = %s"
		await cur.execute(stmt, (str(id),))
		count = await cur.fetchone()
		if count[0] > 0:
			return True
		else:
			return False

	async def delete_tokens(self, ctx):
		cur = await self.sqlBroker.connect()
		print("Deleting token")
		stmt = "DELETE FROM tokens WHERE clientid = %s"
		input = (ctx.user.id,)
		await cur.execute(stmt, input)
		if cur.lastrowid != None:
			await self.sqlBroker.commit(cur)
			await ctx.send("Tokens deleted!")
		else:
			await self.sqlBroker.rollback(cur)
			await ctx.send("Something went wrong! If you want to report this, join my support discord and let the devs know what you were doing!")

	async def addToken(self, ctx, token, session_token):
		now = datetime.now()
		formatted_date = now.strftime('%Y-%m-%d %H:%M:%S')

		ac_g = token.get('ac_g')
		ac_p = token.get('ac_p')
		ac_b = token.get('ac_b')
		s2 = token.get('s2')

		cur = await self.sqlBroker.connect()

		if await self.checkDuplicate(str(ctx.user.id), cur):
			if ac_g != None:
				stmt = "UPDATE tokens SET gtoken = %s, park_session = %s, ac_bearer = %s, session_token = %s, iksm_time = %s WHERE clientid = %s"
				input = (str(ac_g), str(ac_p), str(ac_b), str(session_token), formatted_date, str(ctx.user.id),)
			elif s2 != None:
				print("Updating S2 token + " + s2)
				stmt = "UPDATE tokens SET token = %s, session_token = %s, iksm_time = %s WHERE clientid = %s"
				input = (str(s2), str(session_token), formatted_date, str(ctx.user.id),)
		else:
			stmt = "INSERT INTO tokens (clientid, session_time, session_token) VALUES(%s, %s, %s)"
			input = (str(ctx.user.id), formatted_date, str(session_token),)

		await cur.execute(stmt, input)
		if cur.lastrowid != None:
			await self.sqlBroker.commit(cur)
			return True
		else:
			await self.sqlBroker.rollback(cur)
			return False

	async def get_iksm_token_mysql(self, userid):
		cur = await self.sqlBroker.connect()
		stmt = "SELECT token FROM tokens WHERE clientid = %s"
		await cur.execute(stmt, (str(userid),))
		session_token = await cur.fetchall()
		await self.sqlBroker.commit(cur)
		if len(session_token) == 0:
			return None
		return session_token[0][0]

	async def get_ac_mysql(self, userid):
		cur = await self.sqlBroker.connect()
		stmt = "SELECT gtoken, park_session, ac_bearer FROM tokens WHERE clientid = %s"
		await cur.execute(stmt, (str(userid),))
		session_token = await cur.fetchall()
		await self.sqlBroker.commit(cur)
		if len(session_token) == 0:
			return None

		return session_token[0]

	async def get_session_token_mysql(self, userid):
		cur = await self.sqlBroker.connect()
		stmt = "SELECT session_token FROM tokens WHERE clientid = %s"
		await cur.execute(stmt, (str(userid),))
		session_token = await cur.fetchall()
		await self.sqlBroker.commit(cur)
		if len(session_token) == 0:
			return None
		return session_token[0][0]

	async def login(self, ctx, flag=-1):
		cur = await self.sqlBroker.connect()
		dupe = await self.checkDuplicate(ctx.user.id, cur)
		await self.sqlBroker.close(cur)

		if dupe:
			await ctx.send("You already have a token setup with me, if you need to refresh your token (due to an issue), DM me !deletetoken to perform this again.")
			return

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

		await ctx.send(f"Navigate to this URL in your browser: {post_login}")
		await ctx.send("Log in, right click the \"Select this person\" button, copy the link address, and paste it back to me or 'stop' to cancel.")
		await ctx.send("https://db-files.crmea.de/images/bot/nsohowto.png")

		while True:
			def check(m):
				return m.author == ctx.user and m.channel == ctx.channel

			accounturl = await self.client.wait_for('message', check=check)
			accounturl = accounturl.content

			if 'stop' in accounturl.lower():
				await ctx.send("Ok, stopping the token setup")
				return
			elif 'npf71b963c1b7b6d119' not in accounturl:
				await ctx.send("Invalid URL, please copy the link in \"Select this person\" (or stop to cancel).")
			else:
				break

		await ctx.channel.trigger_typing()
		session_token_code = re.search('session_token_code=(.*)&', accounturl)
		if session_token_code == None:
			print(f"Issue with account url: {str(accounturl)}")
			await ctx.send("Error in account url. Issue is logged, but you can report this in my support guild")
			return

		session_token_code = await self.get_session_token(session_token_code.group(0)[19:-1], auth_code_verifier)

		if session_token_code == None:
			await ctx.send("Something went wrong! Make sure you are also using the latest link I gave you to sign in. If so, join my support discord and report that something broke!")
			return
		else:
			success = await self.addToken(ctx, {}, session_token_code)

		if success and flag == -1:
			await ctx.send("Token added, NSO commands will now work! You shouldn't need to run this command again.")
		elif success and flag == 1:
			await ctx.send("Token added! Ordering...")
		else:
			await ctx.send("Something went wrong! Join my support discord and report that something broke!")

	def get_hash(self, id_token, timestamp):
		version = '1.5.13'
		api_app_head = { 'User-Agent': f"splatnet2statink/{version}" }
		api_body = { 'naIdToken': id_token, 'timestamp': timestamp }
		r = requests.post("https://elifessler.com/s2s/api/gen2", headers=api_app_head, data=api_body)
		print(f"S2API RESPONSE: {r.status_code} {r.reason}")

		if r.status_code == 429:
			print("stat.ink: RATE LIMITED")
			return 429
		elif r.status_code != 200:
			print(f"ERROR IN stat.ink CALL {r.status_code} {r.reason}: {r.text}")
			return None
		else:
			return json.loads(r.text)["hash"]

	async def do_iksm_refresh(self, ctx, game='s2'):
		await ctx.defer()
		session_token = await self.get_session_token_mysql(ctx.user.id)
		keys = await self.setup_nso(session_token, game)

		if keys == 404 or keys == 429:
			await ctx.respond("Temporary issue with NSO logins. Please try again in a few minutes")
			return None
		if keys == None:
			await ctx.respond("Error getting token, I have logged this for my owners")
			return None

		await self.addToken(ctx, keys, session_token)

		if game == 's2':
			return keys['s2']
		else:
			return keys

	async def do_ac_refresh(self, ctx):
		return await self.do_iksm_refresh(ctx, 'ac')

	async def get_session_token(self, session_token_code, auth_code_verifier):
		nsoAppInfo = await self.getAppVersion()
		if nsoAppInfo == None:
			print("get_session_token(): No known NSO app version")
			return None
		nsoAppVer = nsoAppInfo['version']

		head = {
			'User-Agent':      f'OnlineLounge/{nsoAppVer} NASDKAPI Android',
			'Accept-Language': 'en-US',
			'Accept':          'application/json',
			'Content-Type':    'application/x-www-form-urlencoded',
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
		if r.status_code != 200:
			print(f"ERROR IN SESSION TOKEN {r.status_code} {r.reason}: {str(r.text)}")
			return None
		else:
			return json.loads(r.text)["session_token"]

	def call_flapg(self, id_token, guid, timestamp, login):
		api_app_head = {
			'x-token': id_token,
			'x-time':  str(timestamp),
			'x-guid':  guid,
			'x-hash':  str(self.get_hash(id_token, timestamp)),
			'x-ver':   '3',
			'x-iid':   login
		}
		r = requests.get("https://flapg.com/ika2/api/login?public", headers=api_app_head)
		print(f"FLAPG API RESPONSE: {r.status_code} {r.reason}")
		if r.status_code == 404:
			print("ISSUE WITH FLAPG - 404")
			return 404
		elif r.status_code != 200:
			print(f"ERROR IN FLAPGAPI: {r.status_code} {r.reason} : {r.text}")
			return None
		else:
			return json.loads(r.text)["result"]

	async def setup_nso(self, session_token, game='s2'):
		nsoAppInfo = await self.getAppVersion()
		if nsoAppInfo == None:
			print("setup_nso(): No known NSO app version")
			return None
		nsoAppVer = nsoAppInfo['version']

		timestamp = int(time.time())
		guid = str(uuid.uuid4())

		head = {
			'Host': 'accounts.nintendo.com',
			'Accept-Encoding': 'gzip',
			'Content-Type': 'application/json; charset=utf-8',
			'Accept-Language': 'en-US',
			'Accept': 'application/json',
			'Connection': 'Keep-Alive',
			'User-Agent': f'OnlineLounge/{nsoAppVer} NASDKAPI Android'
		}
		body = {
			'client_id': '71b963c1b7b6d119',
			'session_token': session_token,
			'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer-session-token'
		}

		r = requests.post("https://accounts.nintendo.com/connect/1.0.0/api/token", headers=head, json=body)
		id_response = json.loads(r.text)
		if r.status_code != 200:
			print(f"NSO ERROR IN API TOKEN {r.status_code} {r.reason}: {str(id_response)}")
			return

		head = {
			'User-Agent': f'OnlineLounge/{nsoAppVer} NASDKAPI Android',
			'Accept-Language': 'en-US',
			'Accept': 'application/json',
			'Authorization': 'Bearer ' + id_response["access_token"],
			'Host': 'api.accounts.nintendo.com',
			'Connection': 'Keep-Alive',
			'Accept-Encoding': 'gzip'
		}

		r = requests.get("https://api.accounts.nintendo.com/2.0.0/users/me", headers=head)
		user_info = json.loads(r.text)
		if r.status_code != 200:
			print(f"NSO ERROR IN USER LOGIN {r.response} {r.reason}: {str(user_info)}")
			return

		head = {
			'Host': 'api-lp1.znc.srv.nintendo.net',
			'Accept-Language': 'en-US',
			'User-Agent': f'com.nintendo.znca/{nsoAppVer} (Android/7.1.2)',
			'Accept': 'application/json',
			'X-ProductVersion': nsoAppVer,
			'Content-Type': 'application/json; charset=utf-8',
			'Connection': 'Keep-Alive',
			'Authorization': 'Bearer',
			'X-Platform': 'Android',
			'Accept-Encoding': 'gzip'
		}

		idToken = id_response["access_token"]
		flapg_nso = self.call_flapg(idToken, guid, timestamp, "nso")

		if flapg_nso == 404 or flapg_nso == 429:
			return flapg_nso
		elif flapg_nso == None:
			print("ERROR IN FLAPGAPI NSO CALL")
			return None

		parameter = {
			'f':          flapg_nso["f"],
			'naIdToken':  flapg_nso["p1"],
			'timestamp':  flapg_nso["p2"],
			'requestId':  flapg_nso["p3"],
			'naCountry': user_info["country"],
			'naBirthday': user_info["birthday"],
			'language': user_info["language"]
		}
		body = {}
		body["parameter"] = parameter

		r = requests.post("https://api-lp1.znc.srv.nintendo.net/v1/Account/Login", headers=head, json=body)
		splatoon_token = json.loads(r.text)
		if r.status_code != 200:
			print(f"NSO ERROR IN LOGIN {r.status_code} {r.reason}: {str(splatoon_token)}")
			return None

		try:
			idToken = splatoon_token["result"]["webApiServerCredential"]["accessToken"]
		except Exception as e:
			print("YO! ORDER LIKELY EXPLODED. HERES THE JSON NINTENO SENT:")
			print(str(splatoon_token))
			print("HERES THE EXCEPTION:")
			print(str(e))
			#Cross fingers this will shed light on this stupid bug
			return None

		flapg_app = self.call_flapg(idToken, guid, timestamp, "app")
		if flapg_app == None:
			print("ERROR IN FLAPGAPI APP CALL")
			return None

		head = {
			'Host': 'api-lp1.znc.srv.nintendo.net',
			'User-Agent': f'com.nintendo.znca/{nsoAppVer} (Android/7.1.2)',
			'Accept': 'application/json',
			'X-ProductVersion': nsoAppVer,
			'Content-Type': 'application/json; charset=utf-8',
			'Connection': 'Keep-Alive',
			'Authorization': f'Bearer {splatoon_token["result"]["webApiServerCredential"]["accessToken"]}',
			'X-Platform': 'Android',
			'Accept-Encoding': 'gzip'
		}
		parameter = {
			'f':					flapg_app["f"],
			'registrationToken':	flapg_app["p1"],
			'timestamp':			flapg_app["p2"],
			'requestId':			flapg_app["p3"]
		}

		if game == 'ac':
			parameter['id'] = 4953919198265344
		else:
			parameter['id'] = 5741031244955648

		body = {}
		body["parameter"] = parameter

		r = requests.post("https://api-lp1.znc.srv.nintendo.net/v2/Game/GetWebServiceToken", headers=head, json=body)
		token = json.loads(r.text)
		if r.status_code != 200:
			print(f"NSO ERROR IN GETWEBSERVICETOKEN {r.status_code} {r.reason}: {str(token)}")
			return None

		head = {
			'Host': 'placeholder',
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

		keys = {}
		if game == 'ac':
			head['Host'] = 'web.sd.lp1.acbaa.srv.nintendo.net'
			r = requests.get("https://web.sd.lp1.acbaa.srv.nintendo.net/?lang=en-US&na_country=US&na_lang=en-US", headers=head)
			if r.cookies['_gtoken'] == None:
				print(f"ERROR IN GETTING AC _GTOKEN: {str(r.text)}")
				return None
			else:
				print("Got a AC token, getting park_session")
				gtoken = r.cookies["_gtoken"]

				r = requests.get('https://web.sd.lp1.acbaa.srv.nintendo.net/api/sd/v1/users', headers=head, cookies=dict(_gtoken=gtoken))
				thejson = json.loads(r.text)
				if thejson['users']:
					head['Referer'] = "https://web.sd.lp1.acbaa.srv.nintendo.net/?lang=en-US&na_country=US&na_lang=en-US"
					r = requests.post("https://web.sd.lp1.acbaa.srv.nintendo.net/api/sd/v1/auth_token", headers=head, data=dict(userId=thejson['users'][0]['id']), cookies=dict(_gtoken=gtoken))
					bearer = json.loads(r.text)
					if r.cookies['_park_session'] == None or 'token' not in bearer:
						print("ERROR GETTING AC _PARK_SESSION/BEARER")
						return None
					else:
						keys['ac_g'] = gtoken
						keys['ac_p'] = r.cookies['_park_session']
						keys['ac_b'] = bearer['token']
						print("Got AC _park_session and bearer!")
				else:
					return None
		else:
			head['Host'] = 'app.splatoon2.nintendo.net'
			r = requests.get("https://app.splatoon2.nintendo.net/?lang=en-US", headers=head)
			if r.status_code != 200:
				print(f"ERROR IN GETTING IKSM {r.status_code} {r.reason}: {str(r.text)}")
				return None
			else:
				print("Got a S2 token!")
				keys['s2'] = r.cookies["iksm_session"]

		return keys
