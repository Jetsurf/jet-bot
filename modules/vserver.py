import discord, asyncio, subprocess
import queue, sys
import requests, urllib, urllib.request, copy
import youtube_dl, traceback
import mysqlhandler
import json, re, os
from bs4 import BeautifulSoup
from random import randint
from subprocess import call

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': 1,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.07):
        super().__init__(source, volume)

        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.yturl = data.get('webpage_url')
        self.duration = data.get('duration')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options, before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'), data=data)

class voiceServer():
	def __init__(self, client, mysqlhandler, id, soundsDir):
		self.client = client
		self.server = id
		self.vclient = None
		self.ytQueue = queue.Queue()
		self.source = None
		self.soundsDir = soundsDir
		self.sqlBroker = mysqlhandler

	async def joinVoiceChannel(self, ctx, args):
		id = 0
		channel = None

		if ctx.user.voice != None:
			channel = ctx.user.voice.channel

		if isinstance(args, (discord.VoiceChannel, tuple)) or len(args) > 0:
			if not isinstance(args, (discord.VoiceChannel, tuple)):
				channelName = str(' '.join(args[0:]))
				server = ctx.guild
				for channel in server.voice_channels:
					if channel.name == channelName:
						id = channel.id
						break
			else:
				id = args.id
				channel = args

			if id != 0:
				if self.vclient != None:
					#Make sure on_voice_state_update doesn't interfere
					tmpvclient = self.vclient
					self.vclient = None
					await tmpvclient.disconnect()

				#Lets *ACTUALLY* check to see if we're connected
				temp = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
				if temp != None:
					print(f"VSERVER: Caught trying to connect to voice channel in guild {str(ctx.guild.id)}... disconnecting first....")
					await temp.disconnect()

				self.vclient = await channel.connect()
				await ctx.respond(f"Joined voice channel: {channel.name}")
			else:
				await ctx.respond(f"I could not join channel {str(channelName)}")
		elif channel != None:
			if self.vclient != None:
				tmpvclient = self.vclient
				self.vclient = None
				await tmpvclient.disconnect()
				
			if ctx.guild.voice_client != None:
				print("DEBUG: Got vclient as none and server voice client present... disconnecting")
				await ctx.guild.voice_client.disconnect()

			self.vclient = await channel.connect()
			await ctx.respond(f"Joined voice channel {channel.name}")
		else:
			await ctx.respond("Cannot join a channel, either be in a channel or specify which channel to join")

	async def playSound(self, command):
		command = command.replace("../", "")
		if self.source != None or self.vclient == None:
			return

		try:
			source = discord.FFmpegPCMAudio(f"{self.soundsDir}/{command}.mp3")
			source = discord.PCMVolumeTransformer(source)
		except:
			return

		try:
			self.vclient.play(source)
		except:
			return

	def soundExists(self, sound):
		path = f"{self.soundsDir}/{sound}.mp3"
		return os.path.exists(path)

	async def stop(self, ctx):
		if self.source != None:
			self.vclient.stop()
			await ctx.respond("Stopped the currently playing video.")
		else:
			await ctx.respond("Can't stop when I'm not playing anything.")

	async def printQueue(self, ctx):
		theQueue = self.ytQueue.queue
		embed = discord.Embed(colour=0xFF0F00)
		embed.title = "Current Queue"

		if not theQueue:
			embed.add_field(name='Queue is empty', value='🤷', inline=False)

		for i in range(len(theQueue)):
			song = theQueue[i]
			name = song.title
			url = song.yturl
			duration = song.duration
			minutes = int(duration / 60)
			seconds = duration % 60
			embed.add_field(name=name, value=f"Duration - {str(minutes)} Minutes {str(seconds)} Seconds\nURL - {str(url)}", inline=False)

		await ctx.respond(embed=embed)

	def end(self):
		self.ytQueue = queue.Queue()
		self.vclient.stop()
		self.source = None

	def play(self):
		if self.source == None and self.ytQueue.qsize() == 1:
			source = self.ytQueue.get()
			self.vclient.play(source, after=self.playNext)
			self.source = source

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

	def get_yt_json(self, soup):
		scripts = soup.find_all("script")
		for s in scripts:
			text = s.string
			if text == None:
				continue
			if (re.search(r'var ytInitialData =', text)):
				text = re.sub(r'^\s*var ytInitialData\s*=\s*', '', text)  # Slice off leading JS
				text = re.sub(r';\s*$', '', text)  # Slice off trailing semicolon
				return text
		return None

	def playNext(self, e):
		if self.ytQueue.empty():
			self.source = None
		else:
			self.source = self.ytQueue.get()
			self.vclient.play(self.source, after=self.playNext)

	async def setupPlay(self, ctx, args):
		if len(args) == 0:
			return

		if self.vclient == None:
			await ctx.respond("Not connected to voice")
			return

		await ctx.defer()

		if args[0].startswith('https://') or args[0].startswith('http://'):
			try:
				tempPlayer = await YTDLSource.from_url(args[0])
				self.ytQueue.put(tempPlayer)
				self.play()
				await ctx.respond(f"Playing video: {args[0]}")
			except Exception as e:
				print(f"Failure to play youtube DL link... {args[0]}")
				traceback.print_exception(*sys.exc_info())
				await ctx.respond(f"Sorry, I can't play that, you can report the following in my support discord: {str(e)}")
		else:
			try:
				if 'youtube' in args[0]:
					query = urllib.request.pathname2url(' '.join(args[1:]))
					url = f"https://youtube.com/results?search_query={query}".replace('%20', '+')

					source = requests.get(url).text
					soup = BeautifulSoup(source,'html5lib')
					theJson = self.get_yt_json(soup)
					data = json.loads(theJson)
					vidlist = data['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents']

					try:
						vids = self.decode_vidlist(vidlist)
					except Exception as e:
						print("--- Exception decoding Youtube vidlist ---")
						print(traceback.format_exc())
						print(f"Vidlist was: {vidlist}")
						print(f"Search was: {query}")
						raise

					if len(vids) == 0:
						await ctx.respond("No videos found")
						return
					theURL = f"https://youtube.com/watch?v={vids[0]['videoId']}"
				elif 'soundcloud' in args[0]:
					query = ' '.join(args[1:])
					url = f"https://soundcloud.com/search/sounds?q={query}"
					response = requests.get(url)
					soup = BeautifulSoup(response.text, "html5lib")
					song = soup.find("h2")
					song = song.a.get("href")
					theURL = f"https://soundcloud.com{song}"
				else:
					await ctx.respond("Don't know where to search, try !play youtube SEARCH or !play soundcloud SEARCH")
					return

				tempPlayer = await YTDLSource.from_url(theURL)
				if self.ytQueue.empty() and self.source == None:
					await ctx.respond(f"Playing : {theURL}")
				else:
					await ctx.respond(f"Queued : {theURL}")
				print("Playing: " + theURL)
				self.ytQueue.put(tempPlayer)
				self.play()
			except Exception as e:
				print(traceback.format_exc())
				await ctx.respond(f"Sorry, I can't play that, you can report the following in my support discord: {str(e)}")

	async def listCheck(self, theURL):
		cur = await self.sqlBroker.connect()

		stmt = f"SELECT COUNT(*) FROM playlist WHERE serverid = %s AND url = %s"
		await cur.execute(stmt, (self.server, theURL,))
		count = await cur.fetchone()
		await self.sqlBroker.commit(cur)
		if count[0] > 0:
			return True
		else:
			return False

	async def listAdd(self, ctx, toAdd):
		cur = await self.sqlBroker.connect()

		stmt = f"INSERT INTO playlist (serverid, url) VALUES(%s, %s)"
		input = (self.server, toAdd,)
		await cur.execute(stmt, input)
		if cur.lastrowid != None:
			await self.sqlBroker.commit(cur)
			return True
		else:
			await self.sqlBroker.rollback(cur)
			return False

	async def playRandom(self, ctx, numToQueue):
		cur = await self.sqlBroker.connect()
		toPlay = []
		tempPlayer = None
		stmt = "SELECT url FROM playlist WHERE serverid = %s"
		await cur.execute(stmt, (self.server,))
		x = await cur.fetchall()
		await self.sqlBroker.close(cur)
		response = ""

		if len(x) == 0:
			await ctx.respond("You have nothing added to your playlist, use /admin playlist URL to add songs!")
			return
		if numToQueue <= 0:
			await ctx.respond("Num of songs to play must be greater than 0.")
			return

		await ctx.defer()
		print("Playing random")
		numToQueue = min(numToQueue, len(x))
		for y in range(numToQueue):
			while 1:
				numToPlay = randint(1, len(x))
				if numToPlay in toPlay:
					continue
				else:
					toPlay.append(numToPlay)
					break
			try:
				tempPlayer = await YTDLSource.from_url(x[numToPlay - 1][0])
			except Exception as e:
				print(f"ERROR: Failure on song {x[numToPlay - 1][0]} {str(e)}")
				traceback.print_exception(*sys.exc_info())
				continue

			self.ytQueue.put(tempPlayer)
			if self.source == None and self.vclient != None:
				response = f"Playing : {x[toPlay[0] - 1][0]}\n"
				self.play()

		if numToQueue > 1 and self.source == None:
			response = response + f"Also queued {str(numToQueue)} more song(s) from my playlist"
		elif numToQueue > 1:
			response = response + f"Added {str(numToQueue - 1)} more song(s) to the queue from my playlist"

		await ctx.respond(response)

	async def addGuildList(self, ctx, args):
		if len(set(args)) == 0:
			if self.source.yturl != None and await self.listCheck(self.source.yturl):
				if await self.listAdd(ctx, args[0]):
					await ctx.respond(f"Added URL: {self.source.yturl} to the playlist")
				else:
					await ctx.respond(f"Error adding to the playlist")
			else:
				await ctx.respond("I'm not playing anything")
		else:
			if 'https' in args[0] and not await self.listCheck(args[0]):
				if await self.listAdd(ctx, args[0]):
					await ctx.respond(f"Added URL: {args[0]} to the playlist")
				else:
					await ctx.respond(f"Error adding to the playlist")
			elif 'https' not in args[0]:
				await ctx.respond("I need a proper url to add")
			else:
				await ctx.respond(f"URL: {args[0]} is already in my playlist")

	def createSoundsEmbed(self):
		global configData
		embed = discord.Embed(colour=0xEB4034)
		embed.title = "Current Sounds"

		if not self.soundsDir:
			embed.add_field(name="Sorry", value="Sounds not configured on this instance of bot", inline=False)
			return embed

		# Gather files with mp3 extension in sounds dir
		sounds = []
		with os.scandir(self.soundsDir) as iter:
			for dirent in iter:
				if dirent.is_file() and dirent.name.endswith('.mp3'):
					filename = dirent.name.rsplit(".", 1)[0]  # Remove extension
					sounds.append(filename)
		sounds.sort()

		# Create string chunks, each of <= 1024 characters
		chunks = [""]
		for s in sounds:
			l = len(chunks[-1])
			next = f"{', ' if l else ''}{s}"
			if l + len(next) > 1024:
				chunks.append(s)
			else:
				chunks[-1] = chunks[-1] + next

		# Add embed field for each chunk
		for i in range(len(chunks)):
			embed.add_field(name=f"Sounds {i}", value=chunks[i], inline=False)

		return embed
