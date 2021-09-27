# Splatnet/Music Bot
Splatnet/Music bot was originally created in 2017 to be a music/soundclip playing bot. It 
has evolved into its primary purpose of fetching data about Splatoon 2 
maps/Splatnet to help discord servers to access this information 
quickly.

## Installation

If you don't care about self-hosting the bot, you can use the following link:

[![Discord Bots](https://discordbots.org/api/widget/542488723128844312.svg)](https://discordbots.org/bot/542488723128844312)

For self-hosting:

Requires a bot token from the Discord Developer Portal

Requires https://github.com/Pycord-Development/pycord discord python library to 
function (needs branch feature/slash) as well as all dependencies for it.

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

NOTE: This bot is now using slash commands, message commands still work, but are deprecated and will go away once discord disables messaging for bots
The following sections list the different commands that are available.

### Admin commands

There are a few admin commands to configure the bot. To run these commands, you need the administrator role in your discord server.

 - `/admin playlist URL`: Add the given URL to the `/voice playrandom` playlist
 - `/admin blacklist URL`: Prevent the video at the URL from ever being played
 - `/admin dm add`: Subscribe to DMs on users leaving the server
 - `/admin dm remove`: Unsubscribe from DMs on users leaving the server
 - `/admin announcement set CHANNEL` : Sets a chat channel for announcements about restarts/new features from the devs
 - `/admin announcement get` : Gets the name of the channel that is set to receive announcements
 - `/admin announcement stop` : Disables announcements from the devs for the server
 - `/admin feed create` : Create (or change) feed for rotation updates (maps/sr/gear)
 - `/admin feed delete` : Deletes feed for a channel

### Music Commands

 - `/voice join CHANNEL` : Join a Voice Channel. If no channel is provided, joins the voice channel you are connected to
   are currently connected to.
 - `/voice play url URL` : Play/Queue Up a website to Play from URL
 - `/voice play search SOURCE SEARCH` : Searches SOURCE for SEARCH to play
 - `/voice playrandom NUM` : Plays a random url from my playlist.
 - `/voice currentvid` : Displays the currently playing Song/Video
 - `/voice queue` : Displays my current queue of songs to play
 - `/voice skip` : Stop a current playing video and play the next one
 - `/voice end` : Stops all music playback
 - `/voice volume` : Sets my global voice volume (Youtube defaults to 7%, caps at 60% vol)
 - `/voice sounds` : List all possible sounds, prepend ! to play
 
### Splatoon General Info Commands

 - `/splatnetgear` : Gets all of the current gear for sale on SplatNet
 - `/storedm ability ABILITY` : DM's you when a piece of gear with ABILITY appears in the store. Can't DM the bot with this.
 - `/storedm brand BRAND` : DM's you when a piece of gear made by BRAND appears in the store. Can't DM the bot with this.
 - `/storedm brand GEAR` : DM's you when a piece of GEAR (supports all items in the game) appears in the store. Can't DM the bot with this.
 - `/maps current` : Displays the current Splatoon 2 Gamemodes/Maps
 - `/maps next` : Displays the upcoming Splatoon 2 Gamemodes/Maps (!nextnextmaps displays 2 map rotations from now, etc)
 - `/maps currentsr` : Displays the current Splatoon 2 Salmon Run Map/Weapons
 - `/maps nextsr` : Displays the next Splatoon 2 Salmon Run Map/Weapons
 - `/maps random NUM` : Generates a list of random maps (1-10, NUM is optional for just 1 random map)
 - `/maps callout MAP` : Provides a map with callout locations
 - `/maps list` : Shows all Splatoon 2 maps w/ abbreviations
 - `/weapons random NUM` : Generates a list of random weapons (1-10, NUM is optional for just 1 random weapon)
 - `/weapons info WEAP` : Gets Sub/Special/Level/Points for special for WEAP
 - `/weapons sub SUB` : Gets all weapons with the subweapon SUB
 - `/weapons special SPECIAL` : Gets all weapons with the special SPECIAL
 - `/weapons list TYPE` : Gets all weapons of the type TYPE
 
### Splatoon 2 Splatnet Commands

The following commands require you to DM the bot with !token and follow the instructions. DM !deletetoken to remove all tokens from the bot.

 - `/rank` : Shows your ranks in the ranked gamemodes
 - `/stats` : Shows various stats from your gameplay
 - `/srstats` : Shows various stats from Salmon Run
 - `/order ID/ITEM NAME` : !splatnetgear provides an ID. Use either the ID or the name of an item on the store to order it
 - `/battle last` : Gets stats from the last battle you played
 - `/battle num NUM` : Gets stats from NUM last battle (1 is last, upto 50)
 - `/weapons stats WEAPON` : Pulls stats for a specific weapon
 - `/maps stats MAP` : Pulls stats for a specific map

 ### Bot Info Commands
 
 - `/github` : Displays my github link
 - `/support` : Posts an invite link to my discord support guild

# License

[GPLv3](https://www.gnu.org/licenses/gpl-3.0.html)

