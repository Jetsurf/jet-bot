# Splatnet/Music Bot
Splatnet/Music bot was originally created in 2017 to be a music/soundclip playing bot. It 
has evolved into its primary purpose of fetching data about Splatoon 2 
maps/Splatnet to help discord servers to access this information 
quickly.

## Installation

If you don't care about self-hosting the bot, you can use the following link:

[![Discord Bots](https://discordbots.org/api/widget/542488723128844312.svg)](https://discordbots.org/bot/542488723128844312)

For self-hosting:
**WIKI TO COME**

Requires a bot token from the Discord Developer Portal and a Discord Team assigned to it for owner permissions.

Requires https://github.com/Pycord-Development/pycord discord python library to 
function as well as all dependencies for it. Needs to be installed from the master git branch (not automatically via pip) at this time.

Requires youtube-dl and ffmpeg for online video/music playback.

Soundclips are to be placed in a directory defined by discordbot.json.
 - It is assumed that the files are volume normalized. This is what is ran on the production files as a starting point:
   - `find . -name "*.mp3" -exec mp3gain -T -r -d -18dB {} \;`

Requires a mysql backend, configured in discordbot.json.

**OPTIONAL**: Have a https enabled (required) webserver local to the host running the bot stood up to host images provided in directory db-files. If not desired, leave web_dir and hosted_url blank, and the bot will disable the affected images.
 - The web_dir and hosted_url in the config needs to be set to the local root directory the web-server hosts from and the URL of the webserver providing the files. The production [URL](https://db-files.crmea.de) can be alternatively used in your config for hosted_url, but doing so will only break ACNH passport functionality.

## Configuration
An example configuration file is given at discordbot.json.example.
This file needs to be completed and moved to discordbot.json.

Soundsdir is a directory to place soundclips to play with the /voice playsound command.

You can also configure some settings at runtime with [admin commands](#admin-commands).

## Commands

NOTE: This bot is now using slash commands, message commands still work (run !help), but are deprecated and will go away once discord disables messaging for bots
The following sections list the different commands that are available.

### Admin commands

There are a few admin commands to configure the bot. To run these commands, you need the administrator role in your discord server. Can't DM the bot with any of these commands

 - `/admin playlist URL`: Add the given URL to the `/voice play random` playlist
 - `/admin dm add`: Subscribe to DMs on users leaving the server
 - `/admin dm remove`: Unsubscribe from DMs on users leaving the server
 - `/admin announcement set CHANNEL` : Sets a chat channel for announcements about restarts/new features from the devs
 - `/admin announcement get` : Gets the name of the channel that is set to receive announcements
 - `/admin announcement stop` : Disables announcements from the devs for the server
 - `/admin feed create` : Create (or change) feed for rotation updates (maps/sr/gear)
 - `/admin feed delete` : Deletes feed for a channel

### Music Commands

These commands cannot be used in DM's.

 - `/voice join CHANNEL` : Join a Voice Channel. If no channel is provided, joins the voice channel you are currently connected to.
 - `/voice play url URL` : Play/Queue Up a website to Play from URL
 - `/voice play search SOURCE SEARCH` : Searches SOURCE for SEARCH to play
 - `/voice play sound SOUND` : Plays a soundclip if in voice chat (get from `/voice sounds`)
 - `/voice play random NUM` : Plays a random url from my playlist.
 - `/voice currentsong` : Displays the currently playing Song/Video
 - `/voice queue` : Displays my current queue of songs to play
 - `/voice skip` : Stop a current playing video and play the next one
 - `/voice end` : Stops all music playback
 - `/voice volume` : Sets my voice volume for the current song (Youtube defaults to 7%, caps at 60% vol)
 - `/voice sounds` : List all possible sounds for `/voice play sound` to play
 
### Splatoon General Info Commands

 - `/maps current` : Displays the current Splatoon 2 Gamemodes/Maps
 - `/maps next NUM` : Displays the upcoming Splatoon 2 Gamemodes/Maps NUM rotations in the future (1-11)
 - `/maps currentsr` : Displays the current Splatoon 2 Salmon Run Map/Weapons
 - `/maps nextsr` : Displays the next Splatoon 2 Salmon Run Map/Weapons
 - `/maps random NUM` : Generates a list of random maps (1-10, NUM is optional for just 1 random map)
 - `/maps callout MAP` : Provides a map with callout locations
 - `/maps list` : Shows all Splatoon 2 maps w/ abbreviations
 - `/store currentgear` : Gets all of the current gear for sale on SplatNet
 - `/store dm add FLAG` : DM's you when a piece of gear with FLAG (Ability/Brand/Gear Name) appears in the SplatNet store. Can't DM the bot with this.
 - `/store dm list` : Shows you all FLAGS you are subscribed to for when gear with FLAG appears in the store. Can't DM the bot with this.
 - `/store dm remove FLAG` : Removes you from receiving DM's when a piece of gear with FLAG (Ability/Brand/Gear Name) appears in the SplatNet store. Can't DM the bot with this.
 - `/weapons random NUM` : Generates a list of random weapons (1-10), NUM is optional for just 1 random weapon)
 - `/weapons info WEAP` : Gets Sub/Special/Level/Points for special for WEAP
 - `/weapons sub SUB` : Gets all weapons with the subweapon SUB
 - `/weapons special SPECIAL` : Gets all weapons with the special SPECIAL
 - `/weapons list TYPE` : Gets all weapons of the type TYPE
 
### Splatoon 2 Splatnet Commands

The following commands require you to DM the bot with `!token` and follow the instructions. DM `!deletetoken` to remove all tokens from the bot.

 - `/stats battle NUM` : Gets stats from NUM last battle (1 is latest, upto 50)
 - `/stats rank` : Shows your ranks in the ranked gamemodes
 - `/stats multi` : Shows various stats from your gameplay
 - `/stats sr` : Shows various stats from Salmon Run
 - `/stats maps MAP` : Pulls stats for a specific map
 - `/store order ID/ITEM NAME` : `/store currentgear` provides an ID. Use either the ID or the name of an item on the store to order it
 - `/weapons stats WEAPON` : Pulls stats for a specific weapon

### Animal Crossing: New Horizons Commands
 - `/acnh passport` : Posts your passport for Animal Crossing: New Horizons

 ### Bot Info Commands
 
 - `/github` : Displays my github link
 - `/support` : Posts an invite link to my discord support guild

# License

[GPLv3](https://www.gnu.org/licenses/gpl-3.0.html)

