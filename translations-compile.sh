#!/bin/bash

for infile in share/locale/*/LC_MESSAGES/jet-bot.po; do
  outfile="${infile%%.po}.mo"
  msgfmt "$infile" -o "$outfile"
done
