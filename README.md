# Splatnet/Music Bot
Splatnet/Music bot was originally created to be a music/soundclip playing bot. It 
has evolved into its primary purpose of fetching data about Splatoon 2 
maps/Splatnet to help discord servers to access this information 
quickly.

## Installation

If you don't care about self-hosting the bot, you can use the following link:

[![Discord Bots](https://discordbots.org/api/widget/542488723128844312.svg)](https://discordbots.org/bot/542488723128844312)

For self-hosting:

Requires a bot token from the Discord Developer Portal

Requires https://github.com/Rapptz/discord.py discord python library to 
function (Version >= 1.5 needed) as well as all dependencies for it.

Requires youtube-dl and ffmpeg for online video/music playback.

Soundclips are to be placed in a directory defined by discordbot.json.

Requires a mysql backend, configured in discordbot.json.

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
 - `!admin dm add`: Subscribe to DMs on users leaving the server
 - `!admin dm remove`: Unsubscribe from DMs on users leaving the server
 - `!admin prefix CHAR`: Change the command prefix character to CHAR
 - `!admin announcement set CHANNEL` : Sets a chat channel for announcements about restarts/new features from the devs
 - `!admin announcement get` : Gets the name of the channel that is set to receive announcements
 - `!admin announcement stop` : Disables announcements from the devs for the server
 - `!admin feed` : Create (or change) feed for rotation updates (maps/sr/gear)
 - `!admin feed delete` : Deletes feed for a channel

### Music Commands

 - `!join CHANNELNAME` : Join a Voice Channel, must be exact Upper/Lower case. If no name is provided, join the voice chat you
   are currently connected to.
 - `!play URL` : Play/Queue Up a website to Play from URL
 - `!play SOURCE SEARCH` : Searches SOURCE for SEARCH to play (Supports Youtube/Soundcloud)
 - `!playrandom #` : Plays a random url from my playlist. Optional #, queues # videos to play
 - `!currentsong` : Displays the currently playing Song/Video
 - `!queue` : Displays my current queue of songs to play
 - `!skip` : Stop a current playing video and play the next one
 - `!stop` OR `!end` : Stops all music playback
 - `!volume` : Sets my global voice volume (Youtube defaults to 7%, caps at 60% vol)
 - `!sounds` : List all possible sounds, prepend ! to play
 
### Splatoon General Info Commands

 - `!currentmaps` : Displays the current Splatoon 2 Gamemodes/Maps
 - `!nextmaps` : Displays the upcoming Splatoon 2 Gamemodes/Maps (!nextnextmaps displays 2 map rotations from now, etc)
 - `!currentsr` : Displays the current Splatoon 2 Salmon Run Map/Weapons
 - `!nextsr` : Displays the next Splatoon 2 Salmon Run Map/Weapons
 - `!splatnetgear` : Gets all of the current gear for sale on SplatNet
 - `!storedm` ABILITY/GEAR/BRAND : DM's you when a piece of gear with ABILITY, made by BRAND, or is item GEAR (supports all items in the game) appears in the store. Suggests when using partial terms. Can't DM the bot with this
 - `!map random NUM` : Generates a list of random maps (1-10, NUM is optional for just 1 random map)
 - `!map callout MAP` : Provides a map with callout locations
 - `!weapon random NUM` : Generates a list of random weapons (1-10, NUM is optional for just 1 random weapon)
 - `!weapon info WEAP` : Gets Sub/Special/Level/Points for special for WEAP
 - `!weapon sub SUB` : Gets all weapons with the subweapon SUB
 - `!weapon special SPECIAL` : Gets all weapons with the special SPECIAL
 
### Splatoon 2 Splatnet Commands

The following commands require you to DM the bot with !token and follow the instructions. DM !deletetoken to remove all tokens from the bot.

 - `!rank` : Shows your ranks in the ranked gamemodes
 - `!stats` : Shows various stats from your gameplay
 - `!srstats` : Shows various stats from Salmon Run
 - `!order ID/ITEM NAME` : !splatnetgear provides an ID. Use either the ID or the name of an item on the store to order it
 - `!map stats` MAP : Pulls stats for a specific map
 - `!battle last` : Gets stats from the last battle you played
 - `!battle num NUM` : Gets stats from NUM last battle (1 is last, upto 50)
 - `!weapon stats` WEAPON : Pulls stats for a specific weapon

 ### Bot Info Commands
 
 - `!github` : Displays my github link
 - `!support` : Posts an invite link to my discord support guild

# License

[GPLv3](https://www.gnu.org/licenses/gpl-3.0.html)

