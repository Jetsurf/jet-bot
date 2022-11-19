#!/bin/bash -e

stringsfile=share/locale/jet-bot.po

xgettext --language=python -d 'jet-bot' --output="$stringsfile" --files-from=<(find . -iname '*.py')

sed -i 's/charset=CHARSET/charset=UTF-8/g' "$stringsfile"

for langfile in share/locale/*/LC_MESSAGES/jet-bot.po; do
  msgmerge "$langfile" "$stringsfile" > "${langfile}.new"
  mv "${langfile}.new" "$langfile"
done
