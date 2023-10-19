#!/usr/bin/env sh
set -xe
# ./test_method.sh org.mpris.MediaPlayer2 Quit
exec dbus-send --print-reply \
  --dest=org.mpris.MediaPlayer2.ExampleForTemplate \
  /org/mpris/MediaPlayer2 \
  "$1.$2"
