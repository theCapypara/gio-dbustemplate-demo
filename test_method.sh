#!/usr/bin/env sh
set -xe
# ./test_method.sh org.mpris.MediaPlayer2 Quit
iface=$1
method=$2
shift
shift
exec dbus-send --print-reply \
  --dest=org.mpris.MediaPlayer2.ExampleForTemplate \
  /org/mpris/MediaPlayer2 \
  "$iface.$method" $@
