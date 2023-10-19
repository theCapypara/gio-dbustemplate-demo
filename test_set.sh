#!/usr/bin/env sh
set -xe
# ./test_get.sh org.mpris.MediaPlayer2 Fullscreen boolean:true
exec dbus-send --print-reply \
  --dest=org.mpris.MediaPlayer2.ExampleForTemplate \
  /org/mpris/MediaPlayer2 \
  org.freedesktop.DBus.Properties.Set \
  string:"$1" \
  string:"$2" \
  "variant:$3"
