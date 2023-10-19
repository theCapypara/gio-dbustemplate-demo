#!/usr/bin/env sh
set -xe
# ./test_get.sh org.mpris.MediaPlayer2 CanQuit
exec dbus-send --print-reply \
  --dest=org.mpris.MediaPlayer2.ExampleForTemplate \
  /org/mpris/MediaPlayer2 \
  org.freedesktop.DBus.Properties.Get \
  string:"$1" \
  string:"$2"
