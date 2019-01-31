# Jetbot
Jetbot was originally created to be a music/soundclip playing bot. It 
has evolved into its primary purpose of fetching data about Splatoon 2 
maps/splatnet to help discord servers to access this information 
quickly.
# NOTE
This bot is still hardcoded with a few things in place, this will be 
resolved in due time.
## Installation
Requires https://github.com/Rapptz/discord.py discord python library to 
function. Requires youtube-dl and ffmpeg for Youtube playback Soundclips 
are to be placed in a directory defined by discordbot.json Likely more 
dependencies needed to be listed later
## Use
Complete the discordbot.json config file with the necessary fields. 
Currently implemented commands are as follows:
>!joinvoice CHANNELNAME : Join a Voice Channel, must be exact 
>Upper/Lower case !playyt URL OR search : Play/Queue Up a Youtube Video 
>to Play from URL or YT search !playRandom : Plays a random YT Video 
>from my playlist !currentsong : Displays the currently playing 
>Song/Video !play : Resume the current paused YT video !pause : Pause 
>the currently playing YT video !stop : Stop a current playing video and 
>play the next one !volume : Sets my global voice volume (Youtube 
>defaults to 7%, caps at 50% vol) !sounds : List all possible sounds, 
>prepend ! to play !restart : Restarts me if I get stuck !currentmaps : 
>Displays the current Splatoon 2 Gamemodes/Maps !nextmaps : Displays the 
>upcoming Splatoon 2 Gamemodes/Maps (!nextnextmaps displays 2 map 
>rotations from now, etc) !currentsr : Displays the current Splatoon 2 
>Salmon Run Map/Weapons !nextsr : Displays the next Splatoon 2 Salmon 
>Run Map/Weapons !splatnetgear : Gets all of the current gear for sale 
>on SplatNet
The following command requires 3 roles to be in place. Americas - Europe 
- Japan/Asia
>!us OR !eu OR !jp : Show what region you hail from (Americas, Europe, 
>and Japan/Asia respectfully)
This command will be corrected to allow configuration of roles at a later date
