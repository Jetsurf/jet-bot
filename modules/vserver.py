import discord, asyncio, subprocess
import queue, sys
import requests, urllib, urllib.request, copy
import youtube_dl, traceback
import mysqlhandler
import json, re, os
import youtube
from bs4 import BeautifulSoup
from random import randint
from subprocess import call
from discord.ui import *
from discord.enums import ComponentType, InputTextStyle

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

class PlayList():
	def __init__(self, ctx, sqlBroker):
		self.sqlBroker = sqlBroker
		self.page      = 1
		self.ctx       = ctx
		self.shown     = False
		self.yt = youtube.Youtube()

	async def generateEmbed(self):
		embed = discord.Embed(colour=0x3FFF33)
		embed.title = "Playlist Management"
		embed.add_field(name="Instructions", value="Playlists are for /voice play random #.\nAdd to add a video to the playlist.\nRemove to delete from playlist.\n Next/Prev to change pages.\nBold denotes youtube playlist\n  - Number at end is # of videos in list", inline=False)

		self.list = await self.getEntries()
		listlen = len(self.list)

		if listlen == 0:
			embed.add_field(name = "Playlist is empty!", value = "Add some video links!", inline = False)
			return embed

		liststring = ""
		for i, entry in enumerate(self.list[((self.page - 1) * 10):(min(listlen, self.page * 10))], 1):
			url = entry['url']
			duration = entry['duration']
			videocount = entry['videocount']
			title = entry['title']

			if videocount is not None:
				pl = True
			else:
				pl = False

			if title == None:
				if pl:
					liststring += f"**{i + ((self.page - 1) * 10)} - {url}**\n"
				else:
					liststring += f"{i + ((self.page - 1) * 10)} - {url}\n"
			else:
				if pl:
					liststring += f"**{i + ((self.page - 1) * 10)} - [{title}]({url}) - {videocount}**\n"
				else:
					h = int(duration / 3600)
					rem = duration % 3600
					m = int(rem / 60)
					rem = rem % 60
					s = int(rem)
					time = f"{h}:{m:02}:{s:02}" if h > 0 else f"{m}:{s:02}"

					liststring += f"{i + ((self.page - 1) * 10)} - [{title}]({url}) - {time}\n"

		embed.add_field(name=f"Video List (Page {self.page}/{-(listlen // -10)})", value = liststring, inline=False)

		return embed

	async def show(self):
		embed = await self.generateEmbed()

		if self.shown:
			await self.ctx.interaction.edit_original_response(embeds = [embed], view = PlayListView(self, self.page * 10, len(self.list)))
		else:
			await self.ctx.respond(embeds = [embed], view = PlayListView(self, self.page * 10, len(self.list)), ephemeral = True)

		self.shown = True

	async def hide(self):
		if self.shown:
			await self.ctx.interaction.delete_original_response()

	async def hasUrl(self, url):
		row = None
		ytlink = self.yt.url_info(url)

		async with self.sqlBroker.context() as sql:
			if ytlink is None:
				data = await YTDLSource.get_info(url)
				if data is not None:
					row = await sql.query_first("SELECT * FROM playlist WHERE serverid = %s AND url = %s", (self.ctx.guild.id, url))
			else:
				row = await sql.query_first("SELECT * FROM playlist WHERE serverid = %s AND url = %s", (self.ctx.guild.id, ytlink['url']))

		return (not row is None)

	async def getEntries(self):
		async with self.sqlBroker.context() as sql:
			return await sql.query("SELECT url, title, duration, videocount FROM playlist WHERE (serverid = %s)", self.ctx.guild.id)

	async def addEntry(self, url):
		link = self.yt.url_info(url)

		if link is not None and link['type'] == youtube.UrlType.PLAYLIST:
			print(f"Adding playlist URL: {url}")
			link = await self.yt.get_playlist_details(url)
		elif link is not None and link['type'] == youtube.UrlType.VIDEO:
			url = link['url']
			print(f"Adding video URL: {url}")
			link = await self.yt.get_video_details(url)
		else:
			try:
				link = await YTDLSource.get_info(url)
			except Exception as e:
				print(f"Exception: {e}")
				print(f"Failed to add video {url} to playlist")
				return False

		if link is None:
			return False

		async with self.sqlBroker.context() as sql:
			if link['type'] == youtube.UrlType.VIDEO:
				await sql.query("INSERT INTO playlist (serverid, url, duration, title) VALUES (%s, %s, %s, LEFT(%s, 100))", (self.ctx.guild.id, link['url'], link.get('duration'), link['title'], ))
			elif link['type'] == youtube.UrlType.PLAYLIST:
				await sql.query("INSERT INTO playlist (serverid, url, videocount, title) VALUES (%s, %s, %s, LEFT(%s, 100))", (self.ctx.guild.id, link['url'], link['title'], link['videocount'], ))

		self.list.append(link['url'])
		await self.show()
		return True

	async def deleteEntryByIndex(self, i):
		if (i < 0) or (i > len(self.list)):
			return  # Out of range

		entry = self.list.pop(i)
		async with self.sqlBroker.context() as sql:
			await sql.query("DELETE FROM playlist WHERE (serverid = %s) AND (url = %s)", (self.ctx.guild.id, entry['url']))

		await self.checkPageAfterDelete()
		await self.show()

	async def deleteEntryByUrl(self, url):
		ytlink = self.yt.url_info(url)

		async with self.sqlBroker.context() as sql:
			if ytlink['type'] == youtube.UrlType.UNKNOWN:
				await sql.query("DELETE FROM playlist WHERE (serverid = %s) AND (url = %s)", (self.ctx.guild.id, url))
			else:
				await sql.query("DELETE FROM playlist WHERE (serverid = %s) AND (url = %s)", (self.ctx.guild.id, ytlink['url']))

		await self.checkPageAfterDelete()
		await self.show()

	async def checkPageAfterDelete(self):
		#Decrement page if we deleted videos
		if self.page * 10 >= len(await self.getEntries()) + 10:
			self.page-=1

	async def advancePage(self):
		self.page+=1
		await self.show()

	async def retreatPage(self):
		self.page-=1
		await self.show()

class PlayListView(discord.ui.View):
	def __init__(self, playlist, index, numUrls):
		super().__init__()
		self.playlist = playlist
		self.numUrls = numUrls
		self.index = index

		if self.numUrls > 10 and self.index <= self.numUrls:
			self.get_item("next").disabled = False

		if numUrls > 10 and self.index - 10 > 1:
			self.get_item("prev").disabled = False

	@discord.ui.button(label = "Done!", style=discord.ButtonStyle.primary)
	async def doneCallback(self, button, interaction):
		await interaction.response.defer()
		await self.playlist.hide()
		self.stop()

	@discord.ui.button(label = "Add", style=discord.ButtonStyle.secondary, emoji = "\u2795")
	async def addCallback(self, button, interaction):
		modal = PlayListAddModal(self.playlist, title="Add a URL to playlist")
		await interaction.response.send_modal(modal = modal)

	@discord.ui.button(label = "Remove", style=discord.ButtonStyle.red, emoji = "\u2796")
	async def removeCallback(self, button, interaction):
		modal = PlayListDeleteModal(self.playlist, title="Delete entry from playlist")
		await interaction.response.send_modal(modal=modal)

	@discord.ui.button(label = "Previous", style = discord.ButtonStyle.secondary, emoji = "\u2B05", disabled = True, custom_id="prev")
	async def prevCallback(self, button, interaction):
		await self.playlist.retreatPage()
		await interaction.response.defer(invisible=True)

	@discord.ui.button(label = "Next", style = discord.ButtonStyle.secondary, emoji = "\u27A1", disabled = True, custom_id="next")
	async def nextCallback(self, button, interaction):
		await self.playlist.advancePage()
		await interaction.response.defer(invisible=True)

class PlayListAddModal(Modal):
	def __init__(self, playlist, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.playlist = playlist

		url_input = InputText(label="URL to add to the playlist", style=discord.InputTextStyle.short, placeholder="https://")

		self.add_item(url_input)

	async def addUrl(self, interaction, url):
		async with self.sqlBroker.context() as sql:
			chk = await sql.query("DELETE FROM playlist WHERE (serverid = %s) AND (url = %s)", (interaction.guild.id, url,))

	async def callback(self, interaction: discord.Interaction):
		url = self.children[0].value.strip()
		if not url.startswith('https://'):
			await interaction.response.send_message(content = "I need a valid https:// link to add.", ephemeral = True, delete_after = 5)
			return

		print(f"URL is: {url}")
		if await self.playlist.hasUrl(url):
			await interaction.response.send_message(content = "That URL is already on the playlist.", allowed_mentions = discord.AllowedMentions.none(), ephemeral = True, delete_after = 5)
			return

		if await self.playlist.addEntry(url):
			await interaction.response.send_message(f"Added <{url}>", ephemeral = True, delete_after = 5)
		else:
			await interaction.response.send_message(f"Failed to add <{url}>", ephemeral = True, delete_after = 5)

		return

class PlayListDeleteModal(Modal):
	def __init__(self, playlist, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.playlist = playlist

		self.add_item(InputText(label=f"Video number to delete (1-{len(self.playlist.list)}), or the url", style=discord.InputTextStyle.short, placeholder=f"1-{len(self.playlist.list)} OR https://"))

	async def callback(self, interaction: discord.Interaction):
		if 'https://' in self.children[0].value:
			if await self.playlist.hasUrl(self.children[0].value):
				await self.playlist.deleteEntryByUrl(self.children[0].value)
				await interaction.response.send_message(f"Removed url <{self.children[0].value}> from the playlist.", ephemeral = True, delete_after = 5)
				return
			else:
				await interaction.response.send_message(f"Couldn't find url <{self.children[0].value}> in the playlist.", ephemeral = True, delete_after = 5)
				return

		num = int(self.children[0].value)
		if (num > len(self.playlist.list)) or (num <= 0):
			await interaction.response.send_message(f"Num needs to be between 1 and {len(self.playlist.list)}", ephemeral=True, delete_after = 5)
			return

		await interaction.response.send_message(f"Okay, removed item {num}", ephemeral = True, delete_after = 5)
		await self.playlist.deleteEntryByIndex(num - 1)

class YTDLSource(discord.PCMVolumeTransformer):
	def __init__(self, source, *, data, volume=0.07):
		super().__init__(source, volume)

		self.data = data
		self.title = data.get('title')
		self.url = data.get('url')
		self.yturl = data.get('webpage_url')
		self.duration = data.get('duration')

	@classmethod
	async def get_info(cls, url, *, loop=None, stream=True):
		loop = loop or asyncio.get_event_loop()
		data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

		if data['extractor'] == 'generic' or data['extractor'] == 'youtube:search':
			return None

		##THIS ASSUMES VIDEO LINKS ONLY
		retData = { 'title' : data.get('title'),
					'url' : data.get('webpage_url'),
					'type' : youtube.UrlType.VIDEO,
					'duration' : data.get('duration')
				}

		return retData

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
		self.youtube = youtube.Youtube()
		self.sqlBroker = mysqlhandler

	@classmethod
	async def updatePlaylists(cls, sqlBroker):
		yt = youtube.Youtube()

		async with sqlBroker.context() as sql:
			rows = await sql.query("SELECT * FROM playlist WHERE (title IS NULL)")

		for r in rows:
			print(f"updatePlaylists(): entryid {r['entryid']} url '{r['url']}'")
			info = yt.url_info(r['url'])
			if info is None:
				#Check with youtube-dl to see if this is a valid non-youtube link
				data = await YTDLSource.get_info(r['url'])
				if data is not None:
					async with sqlBroker.context() as sql:
						await sql.query("UPDATE playlist SET url = %s, title = LEFT(%s, 100), duration = %s WHERE (entryid = %s)", (data['url'], data['title'], int(data['duration']), r['entryid'], ))

					print(f"  Added valid non-youtube url {data['title']} {data['duration']} {data['url']}")
					await asyncio.sleep(15)
					continue
				else:
					print(f"  Removing bad URL: {r['url']}")
					async with sqlBroker.context() as sql:
						await sql.query("DELETE FROM playlist WHERE entryid = %s", (r['entryid'],))
					continue

			await asyncio.sleep(15)  # Slow down so we don't hit Youtube too hard

			if info['type'] == youtube.UrlType.PLAYLIST:
				details = await yt.get_playlist_details(info['url'])
			else:
				details = await yt.get_video_details(info['url'])

			if details is None:
				print("  Couldn't get details")
				continue

			#print(f"  repr {repr(details)}")
			if info['type'] == youtube.UrlType.PLAYLIST:
				print(f"  Setting playlist details: url '{details['url']}' title '{details['title']}' videoCount {details['videoCount']}")
				async with sqlBroker.context() as sql:
					await sql.query("UPDATE playlist SET url = %s, title = LEFT(%s, 100), videocount = %s WHERE (entryid = %s)", (details['url'], details['title'], details['videoCount'], r['entryid'], ))
			elif details['playable']:
				print(f"  Setting video details: url '{details['url']}' title '{details['title']}' duration {details['duration']}")
				async with sqlBroker.context() as sql:
					await sql.query("UPDATE playlist SET url = %s, title = LEFT(%s, 100), duration = %s WHERE (entryid = %s)", (details['url'], details['title'], details['duration'], r['entryid'], ))
			else:
				print(f"  Removing unplayable video: {details.get('error', 'Unknown error')}")
				async with sqlBroker.context() as sql:
					await sql.query("DELETE FROM playlist WHERE (entryid = %s)", (r['entryid'], ))

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
					query = ' '.join(args[1:])
					vids = await self.youtube.search(query)

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
