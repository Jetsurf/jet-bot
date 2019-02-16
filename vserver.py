import discord
import queue
import asyncio
import sys
import requests
from bs4 import BeautifulSoup
from random import randint

class voiceServer():

	#soundsDir
	#playlist
	#blacklist

	def __init__(self, client, id, soundsDir, playlist, blacklist):
		self.client = client
		self.ID = id
		self.vclient = None
		self.ytQueue = queue.Queue()
		self.ytPlayer = None
		self.player = None
		self.soundsDir = soundsDir
		self.blacklist = blacklist
		self.playlist = playlist

	async def joinVoiceChannel(self, channelName, message):
		id = 0

		print(self.vclient)
		if self.vclient != None:
			await self.vclient.disconnect()

		server = message.server
		for channel in server.channels:
			if channel.name == channelName:
				id = channel.id
				break
		if id != 0:
			self.vclient = await self.client.join_voice_channel(self.client.get_channel(id))
		else:
			await self.client.send_message(message.channel, "I could not join channel " + str(channelName))

	async def playSound(self, command, message):
		if self.ytPlayer == None:
			if self.player != None:
				self.player.stop()

			self.player = self.vclient.create_ffmpeg_player(self.soundsDir + '/' + command[1:] + '.mp3')

			if '!wtfboom' in command or '!johncena' in command or '!ohmygod' in command or "!leeroy" in command:
				self.player.volume = .1
			elif '!whosaidthat' in command or '!chrishansen' in command:
				self.player.volume = .4
			else:
				self.player.volume = .25

			self.player.start()

	async def stop(self, message):
		if self.ytPlayer != None:
			self.ytPlayer.stop()
		else:
			await self.client.send_message(message.channel, "I'm not playing anything right now")

	def play(self):
		if self.ytPlayer == None and self.ytQueue.qsize() == 1:
			self.ytPlayer = self.ytQueue.get()
			self.ytPlayer.volume = .07
			self.ytPlayer.start()

	def playNext(self):
		if self.ytQueue.empty():
			self.ytPlayer = None
		else:
			self.ytPlayer = self.ytQueue.get()
			self.ytPlayer.volume = .07
			self.ytPlayer.start()

	async def setupPlay(self, message):
		if self.player != None:
			self.player.stop()
		if 'https://' in message.content:
			if self.listCheck(self.blacklist, message.content.split(' ')[1]):
				print(message.author.name + " tried to play a blacklisted video")
				await self.client.send_message(message.channel, "Sorry, I can't play that")
				return
			try:
				tempytplayer = await self.vclient.create_ytdl_player(message.content.split(' ')[1], after=self.playNext)
				tempytplayer.after = self.playNext
				self.ytQueue.put(tempytplayer)
				self.play()
				await self.client.add_reaction(message, '👍')
			except Exception as e:
				print(str(e))
				await self.client.send_message(message.channel, "Sorry, I can't play that, give this info to jetsurf: " + str(e))
		else:
			try:
				if 'youtube' in message.content:
					query = urllib.request.pathname2url(' '.join(message.content.split()[2:]))
					url = "https://youtube.com/results?search_query=" + query
					response = urllib.request.urlopen(url)
					html = response.read()
					soup = BeautifulSoup(html, "lxml")
					vid =  soup.find(attrs={'class':'yt-uix-tile-link'})
					theURL = "https://youtube.com" + vid['href']
				elif 'soundcloud' in message.content:
					query = ' '.join(message.content.split()[2:])
					url = "https://soundcloud.com/search/sounds?q=" + query
					response = requests.get(url)
					soup = BeautifulSoup(response.text, "lxml")
					song = soup.find("h2")
					song = song.a.get("href")
					theURL = "https://soundcloud.com" + song
				else:
					await self.client.send_message(message.channel, "Don't know where to search, try !play youtube SEARCH or !play soundcloud SEARCH")
					return

					if listCheck(self.blacklist, theURL):
						print(message.author.name + " tried to play a blacklisted video")
						await self.client.send_message(message.channel, "Sorry, I can't play that")
						return

				if self.ytQueue.empty() and self.ytPlayer == None:
					await self.client.send_message(message.channel, "Playing : " + theURL)
				else:
					await self.client.send_message(message.channel, "Queued : " + theURL)
				print("Playing: " + theURL)
				tempytplayer = await self.vclient.create_ytdl_player(theURL)
				tempytplayer.after = self.playNext
				self.ytQueue.put(tempytplayer)
				self.play()
			except Exception as e:
				print(str(e))
				await self.client.send_message(message.channel, "Sorry, I can't play that, give this info to jetsurf: " + str(e))

	def listCheck(self, theFile, theURL):
		flag = False

		with open(theFile, 'r') as f:
			for line in f:
				if theURL in line:
					flag = True
					break
		f.close()
		return flag

	def listAdd(theFile, toAdd):
		list = open(theFile, 'a')
		list.write('\n' + toAdd)
		list.flush()
		list.close()

	async def playRandom(self, message, numToQueue):
		x = []
		toPlay = []
		tempytplayer = None

		with open(self.playlist, 'r') as f:
			for line in f:
				x.append(line)

		numToQueue = min(numToQueue, len(x))
		for y in range(numToQueue):
			while 1:
				numToPlay = randint(1, len(x))
				if numToPlay in toPlay:
					continue
				else:
					toPlay.append(numToPlay)
					print("I am going to play track " + str(numToPlay) + " " + x[numToPlay - 1])
					break

			tempytplayer = await self.vclient.create_ytdl_player(x[numToPlay - 1])
			tempytplayer.after = self.playNext
			self.ytQueue.put(tempytplayer)

			if self.ytPlayer == None and self.vclient != None:
				await self.client.send_message(message.channel, "Playing : " + x[toPlay[0] - 1])
			if y == 1:
				print("I am queueing song " + str(numToPlay) + " " + x[numToPlay - 1])
			self.play()
		if numToQueue > 1:
			await self.client.send_message(message.channel, "Also queued " + str(numToQueue - 1) + " more song(s) from my playlist")