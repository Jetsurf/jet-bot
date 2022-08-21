# Splatnet/Music Bot
Splatnet/Music bot was originally created in 2017 to be a music/soundclip playing bot. It 
has evolved into its primary purpose of fetching info from Nintendo Switch Online 

- Splatoon 2: Rotation info, Splatnet gameplay stats, ordering gear and notifications of specific gear arriving in the store
- Animal Crossing New Horizons: Passports
- Splatoon 3 Support is planned

## Installation

If you don't care about self-hosting the bot, you can use the following link:

[![Discord Bots](https://top.gg/api/widget/542488723128844312.svg)](https://top.gg/bot/542488723128844312)

For self-hosting:
[See Here](https://github.com/Jetsurf/jet-bot/wiki)

## NOTE

DM'ing the bot with !token and giving it the link it requests pulls your account sesion token from Nintendo to grant it access to game specific data. It is identical to logging into the NSO App on your phone.
The game specific tokens are ONLY used to access your Splatoon 2 stats and ACNH passports to post within Discord and order gear for you. The account session token is used to refresh game tokens if they expire. They are used for nothing else.
Feel free to look over [modules/nsotoken.py](https://github.com/Jetsurf/jet-bot/blob/master/modules/nsotoken.py) to audit the handling of keys yourself.

## Commands

NOTE: This bot is now using slash commands, message commands still work (run !help), but are deprecated and will go away once discord disables message content access for bots
The following sections list the different commands that are available.

### Admin commands

There are a few admin commands to configure the bot. To run these commands, you need the administrator permission in your discord server. Can't DM the bot with any of these commands

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
 - `/acnh getemotes` : Gets all available emotes to use with `/acnh emote`
 - `/acnh emote` : Makes your character in ACNH perform an emote. Must be connected to the internet with your game
 - `/acnh message` : Makes your character in ACNH say a message. Must be connected to the internet with your game

 ### Bot Info Commands
 
 - `/github` : Displays my github link
 - `/support` : Posts an invite link to my discord support guild

# License

[GPLv3](https://www.gnu.org/licenses/gpl-3.0.html)

