# Jetbot
Jetbot was originally created to be a music/soundclip playing bot. It 
has evolved into its primary purpose of fetching data about Splatoon 2 
maps/splatnet to help discord servers to access this information 
quickly.

# NOTE
This bot is still hardcoded with a few things in place, most have been
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

Also, discordbot.service will need to be played in
/etc/systemd/system/multi-user.target.wants/ for !restart to work.

Playlist/Blacklist files are simple .txt files. They are simply a
file containing the links to videos/songs to play with !playrandom
or to be blacklisted from being played. To start a file, create
a new file, paste one link in, and do not add a newline to the end of
the link.

Admins are contained in a JSON array and should have the discord ID of
all the users that you want to allow access to the admin commands.
(List of commands coming soon)

## Use
Complete the discordbot.json config file with the necessary fields. 
Currently implemented commands are as follows:
 - !joinvoice CHANNELNAME : Join a Voice Channel, must be exact
   Upper/Lower case
 - !play URL OR search : Play/Queue Up a video/song to Play from
   URL or YT search
 - !playrandom # : Plays a random YT Video from my playlist, optional #,
   queues # videos to play
 - !currentsong : Displays the currently playing Song/Video
 - !stop : Stop a current playing video and play the next one
 - !volume : Sets my global voice volume (Youtube defaults to 7%, caps
   at 50% vol)
 - !sounds : List all possible sounds, prepend ! to play
 - !restart : Restarts me if I get stuck
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
