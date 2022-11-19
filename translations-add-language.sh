#!/bin/bash

if [ $# -eq 0 ]; then
	echo "Usage: $0 <language>"
	echo "The language should be a code with an underscore in the middle, like fr_FR"
	exit 1
fi

lang="$1"

[ ! -d share/locale/"$lang" ] && mkdir -p share/locale/"$lang"/LC_MESSAGES/
msginit -i share/locale/jet-bot.po --no-translator --locale="$lang" -o share/locale/"$lang"/LC_MESSAGES/jet-bot.po
