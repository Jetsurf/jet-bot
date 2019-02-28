# Jetbot
Jetbot was originally created to be a music/soundclip playing bot. It 
has evolved into its primary purpose of fetching data about Splatoon 2 
maps/splatnet to help discord servers to access this information 
quickly.

# NOTE
This bot still has some hardcoded things in place, most have been
resolved, but the !us/jp/eu role commands are not.

## Installation
Requires https://github.com/Rapptz/discord.py discord python library to 
function.

Requires youtube-dl and ffmpeg for online video/music playback.

Soundclips are to be placed in a directory defined by discordbot.json.

Likely more dependencies needed to be listed later.

## Configuration
An example configuration file is given at discordbot.json.example.
This file needs to be completed and moved to discordbot.json.

Soundsdir is a directory to place soundclips to play with the !file
command.

There are two admin commands to configure the bot:
 - !admin playlist URL
 - !admin blacklist URL

Run the command with a URL to either add it to the !playrandom playlist or prevent the video at the URL from ever being played.

The following admin commands are used for chat squelching (voice mute to come soon)

 - !admin squelch @user hours reason
 - !admin unsquelch @user
 - !admin squelch current
 - !admin squelch log
 
The squelch current command gives a list of all users currently squelched by the bot, squelch log provides a detailed log
of what users are actively or ever were squeleched.

To run these commands, you need the administrator role in your discord server.

## Use
Complete the discordbot.json config file with the necessary fields. 
Currently implemented commands are as follows:
 - !joinvoice OR !join CHANNELNAME : Join a Voice Channel, must be exact
   Upper/Lower case or if no name is provided, join the voice chat you
   are currently connected to.
 - !play URL : Play/Queue Up a website to Play from URL
 - !play SOURCE SEARCH : Searches SOURCE for SEARCH to play (Supports
   Youtube/Soundcloud)
 - !playrandom # : Plays a random url from my playlist. Optional #,
   queues # videos to play
 - !currentsong : Displays the currently playing Song/Video
 - !stop OR !skip : Stop a current playing video and play the next one
 - !volume : Sets my global voice volume (Youtube defaults to 7%, caps
   at 60% vol)
 - !sounds : List all possible sounds, prepend ! to play
 - !currentmaps : Displays the current Splatoon 2 Gamemodes/Maps
 - !nextmaps : Displays the upcoming Splatoon 2 Gamemodes/Maps
   (!nextnextmaps displays 2 map rotations from now, etc)
 - !currentsr : Displays the current Splatoon 2 Salmon Run Map/Weapons
 - !nextsr : Displays the next Splatoon 2 Salmon Run Map/Weapons
 - !splatnetgear : Gets all of the current gear for sale on SplatNet
 - !github : Displays my github link

The following command requires 3 roles to be in place. Americas - Europe - 
Japan/Asia

 - !us OR !eu OR !jp : Show what region you hail from (Americas, Europe,
   and Japan/Asia respectfully)

This command will be corrected to allow configuration of roles at a later date
