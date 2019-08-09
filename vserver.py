import discord
import queue
import asyncio
import sys
import requests
import urllib
import urllib.request
import mysql.connector
import copy
import youtube_dl
from mysql.connector.cursor import MySQLCursorPrepared
from bs4 import BeautifulSoup
from random import randint

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'playlistend' : '5'
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
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class voiceServer():
	def __init__(self, client, mysqlinfo, id, soundsDir):
		self.client = client
		self.server = id
		self.vclient = None
		self.ytQueue = queue.Queue()
		self.source = None
		self.soundsDir = soundsDir
		self.mysqlinfo = mysqlinfo

	def connect(self):
		theDB = mysql.connector.connect(host=self.mysqlinfo.host, user=self.mysqlinfo.user, password=self.mysqlinfo.pw, database=self.mysqlinfo.db)
		cursor = theDB.cursor(cursor_class=MySQLCursorPrepared)
		return theDB, cursor

	def disconnect(self, db, cursor):
		cursor.close()
		db.close()

	async def joinVoiceChannel(self, channelName, message):
		id = 0
		channel = None
		
		if message.author.voice.channel != None:
			channel = message.author.voice.channel

		if len(message.content) > 6:
			server = message.guild
			for channel in server.voice_channels:
				if channel.name == channelName:
					id = channel.id
					break
			if id is not 0:
				if self.vclient != None:
					await self.vclient.disconnect()
				self.vclient = await channel.connect()
			else:
				await message.channel.send("I could not join channel " + str(channelName))
		elif channel != None:
			if self.vclient != None:
				await self.vclient.disconnect()
			self.vclient = await channel.connect()
		else:
			await message.channel.send("Cannot join a channel, either be in a channel or specify which channel to join")

	async def playWTF(self, message):
		if self.vclient != None and self.source == None:
			source = discord.FFmpegPCMAudio(self.soundsDir + '/wtfboom.mp3')
			souce = discord.PCMVolumeTransformer(source)
			source.volume = .5
			self.vclient.play(source)

	async def playSound(self, command, message):
		if self.source != None:
			return
		
		source = discord.FFmpegPCMAudio(self.soundsDir + '/' + command[1:] + '.mp3')
		source = discord.PCMVolumeTransformer(source)

		if '!wtfboom' in command or '!johncena' in command or '!ohmygod' in command or "!leeroy" in command:
			source.volume = .1
		elif '!whosaidthat' in command or '!chrishansen' in command or '!sotasty' in command:
			source.volume = .4
		else:
			source.volume = .25

		self.vclient.play(source)

	async def stop(self, message):
		if self.source != None:
			self.vclient.stop()
		else:
			await message.channel.send("I'm not playing anything right now")

	async def printQueue(self, message):
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
			embed.add_field(name=name, value="Duration - " + str(minutes) + " Minutes " + str(seconds) + " Seconds\nURL - " + str(url), inline=False)

		await message.channel.send(embed=embed)

	def end(self):
		self.ytQueue = queue.Queue()
		self.vclient.stop()
		self.source = None

	def play(self):
		if self.source == None and self.ytQueue.qsize() == 1:
			source = self.ytQueue.get()
			self.vclient.play(source, after=self.playNext)
			self.source = source

	def playNext(self, e):
		if self.ytQueue.empty():
			self.source = None
		else:
			self.source = self.ytQueue.get()
			self.vclient.play(self.source, after=self.playNext)

	async def setupPlay(self, message):
		if 'https://' in message.content:
			if self.listCheck(1, message.content.split(' ')[1]):
				print(message.author.name + " tried to play a blacklisted video")
				await message.channel.send("Sorry, I can't play that")
				return
			try:
				tempPlayer = await YTDLSource.from_url(message.content.split(' ')[1])
				self.ytQueue.put(tempPlayer)
				self.play()
				await message.add_reaction('👍')
			except Exception as e:
				print(str(e))
				await message.channel.send("Sorry, I can't play that, give this info to jetsurf: " + str(e))
		else:
			try:
				if 'youtube' in message.content.lower():
					query = urllib.request.pathname2url(' '.join(message.content.split()[2:]))
					url = "https://youtube.com/results?search_query=" + query
					response = urllib.request.urlopen(url)
					html = response.read()
					soup = BeautifulSoup(html, "lxml")
					vid =  soup.find_all(attrs={'class':'yt-uix-tile-link'})
					if 'googleadservices' in vid[0]['href']:
						theURL = 'https://youtube.com' + vid[1]['href']
					else:	
						theURL = "https://youtube.com" + vid[0]['href']
				elif 'soundcloud' in message.content.lower():
					query = ' '.join(message.content.split()[2:])
					url = "https://soundcloud.com/search/sounds?q=" + query
					response = requests.get(url)
					soup = BeautifulSoup(response.text, "lxml")
					song = soup.find("h2")
					song = song.a.get("href")
					theURL = "https://soundcloud.com" + song
				else:
					await message.channel.send("Don't know where to search, try !play youtube SEARCH or !play soundcloud SEARCH")
					return
				if self.listCheck(1, theURL):
					print(message.author.name + " tried to play a blacklisted video")
					await message.channel.send("Sorry, I can't play that")
					return

				if self.ytQueue.empty() and self.source == None:
					await message.channel.send("Playing : " + theURL)
				else:
					await message.channel.send("Queued : " + theURL)
				print("Playing: " + theURL)
				tempPlayer = await YTDLSource.from_url(theURL)
				self.ytQueue.put(tempPlayer)
				self.play()
			except Exception as e:
				print(str(e))
				await message.channel.send("Sorry, I can't play that, give this info to jetsurf: " + str(e))

	def listCheck(self, theList, theURL):
		theDB, cursor = self.connect()
		stmt = "SELECT COUNT(*) FROM "

		if theList == 0:
			stmt = stmt + "playlist "
		else:
			stmt = stmt + "blacklist "

		stmt = stmt + "WHERE serverid = %s AND url = %s"
		cursor.execute(stmt, (self.server, theURL,))
		count = cursor.fetchone()
		self.disconnect(theDB, cursor)
		if count[0] > 0:
			return True
		else:
			return False

	async def listAdd(self, theList, toAdd, message):
		theDB, cursor = self.connect()
		stmt = "INSERT INTO "

		if theList == 0:
			stmt = stmt + "playlist "
		else:
			stmt = stmt + "blacklist "

		stmt = stmt + "(serverid, url) VALUES(%s, %s)"
		input = (self.server, toAdd,)
		cursor.execute(stmt, input)
		if cursor.lastrowid != None:
			theDB.commit()
			self.disconnect(theDB, cursor)
		else:
			await self.client.send_message(message.channel, "Something went wrong!")

	async def playRandom(self, message, numToQueue):
		theDB, cursor = self.connect()
		toPlay = []
		tempPlayer = None
		stmt = "SELECT url FROM playlist WHERE serverid = %s"
		cursor.execute(stmt, (self.server,))
		x = cursor.fetchall()
		self.disconnect(theDB, cursor)

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
				tempPlayer = await YTDLSource.from_url(x[numToPlay - 1][0].decode('utf-8'))
			except Exception as e:
				print("ERROR: Failure on song " + x[numToPlay - 1][0].decode('utf-8') + " " + str(e))
				sys.stdout.flush()
				continue

			self.ytQueue.put(tempPlayer)

			if self.source == None and self.vclient != None:
				await message.channel.send("Playing : " + x[toPlay[0] - 1][0].decode('utf-8'))
			self.play()
		if numToQueue > 1:
			await message.channel.send("Also queued " + str(numToQueue - 1) + " more song(s) from my playlist")

	async def addPlaylist(self, message):
		toAdd = ''
		if 'https' in message.content:
			toAdd = message.content.split(' ', 2)[2]
		elif self.ytPlayer != None:
			toAdd = self.ytPlayer.url
		else:
			await self.client.send_message(message.channel, 'Im not playing anything, pass me a url to add to the playlist')
			return
		
		if not self.listCheck(0, toAdd):
			await self.listAdd(0, toAdd, message)
			await self.client.add_reaction(message, '👍')
		else:
			await self.client.send_message(message.channel, 'That is already in my playlist!')

	async def addBlacklist(self, message):
		toAdd = ''
		if 'https' in message.content:
			toAdd = message.content.split(' ', 2)[2]
		elif self.ytPlayer != None:
			toAdd = self.ytplayer.url
		else:
			await self.client.send_message(message.channel, 'Im not playing anything, pass me a url to add to the playlist')
			return
		
		if not self.listCheck(1, toAdd):
			await self.listAdd(1, toAdd, message)
			await self.client.add_reaction(message, '👍')
		else:
			await self.client.send_message(message.channel, 'That is already in my blacklist!')
