# Splatnet/Music Bot
Splatnet/Music bot was originally created to be a music/soundclip playing bot. It 
has evolved into its primary purpose of fetching data about Splatoon 2 
maps/Splatnet to help discord servers to access this information 
quickly.

## Installation
Requires https://github.com/Rapptz/discord.py discord python library to 
function (Version >= 1.0 needed).

Requires youtube-dl and ffmpeg for online video/music playback.

Soundclips are to be placed in a directory defined by discordbot.json.

Likely more dependencies needed to be listed later.

Alternatively, use the following link to join the bot to your server!

[![Discord Bots](https://discordbots.org/api/widget/542488723128844312.svg)](https://discordbots.org/bot/542488723128844312)

## Configuration
An example configuration file is given at discordbot.json.example.
This file needs to be completed and moved to discordbot.json.

Soundsdir is a directory to place soundclips to play with the !file
command.

You can also configure some settings at runtime with [admin commands](#admin-commands).

## Commands

The default command prefix is `!`. You can also send commands without the prefix by @mentioning the bot:
```@Splatnet/Music Bot nextmaps```

You can always run `!help` to get a list of the commands regardless of the prefix. Also, you can run
`!prefix`. 

The following sections list the different commands that are available.

### Admin commands

There are a few admin commands to configure the bot. To run these commands, you need the administrator role in your discord server.

 - `!admin playlist URL`: Add the given URL to the `!playrandom` playlist
 - `!admin blacklist URL`: Prevent the video at the URL from ever being played
 - `!admin dm add`: Subscribe to direct DMs on users leaving the server
 - `!admin dm remove`: Unsubscribe from direct DMs on users leaving the server
 - `!admin prefix CHAR`: Change the command prefix character to CHAR

### Music Commands

 - `!joinvoice` OR `!join CHANNELNAME` : Join a Voice Channel, must be exact
   Upper/Lower case or if no name is provided, join the voice chat you
   are currently connected to.
 - `!play URL` : Play/Queue Up a website to Play from URL
 - `!play SOURCE SEARCH` : Searches SOURCE for SEARCH to play (Supports
   Youtube/Soundcloud)
 - `!playrandom #` : Plays a random url from my playlist. Optional #,
   queues # videos to play
 - `!currentsong` : Displays the currently playing Song/Video
 - `!queue` : Displays my current queue of songs to play
 - `!stop` OR `!skip` : Stop a current playing video and play the next one
 - `!volume` : Sets my global voice volume (Youtube defaults to 7%, caps
   at 60% vol)
 - `!sounds` : List all possible sounds, prepend ! to play
 
### Splatoon General Info Commands

 - `!currentmaps` : Displays the current Splatoon 2 Gamemodes/Maps
 - `!nextmaps` : Displays the upcoming Splatoon 2 Gamemodes/Maps
   (!nextnextmaps displays 2 map rotations from now, etc)
 - `!currentsr` : Displays the current Splatoon 2 Salmon Run Map/Weapons
 - `!nextsr` : Displays the next Splatoon 2 Salmon Run Map/Weapons
 - `!splatnetgear` : Gets all of the current gear for sale on SplatNet
 - `!storedm` ABILITY : DM's you when a piece of gear with ABILITY appears in the store (only once, can't DM the bot with this)
 
### Splatoon 2 Splatnet Commands

The following commands require you to DM the bot with !token and follow the instructions. DM !deletetoken to remove all tokens from the bot.

 - `!rank` : Shows your ranks in the ranked gamemodes
 - `!stats` : Shows various stats from your gameplay
 - `!srstats` : Shows various stats from Salmon Run
 - `!order ID` : The !splatnetgear command gives you 'ID to buy' run this with that ID to
   place an order in the splatnet store

 ### Bot Info Commands
 
 - `!github` : Displays my github link
 - `!support` : Posts an invite link to my discord support guild

# License

[GPLv3](https://www.gnu.org/licenses/gpl-3.0.html)

