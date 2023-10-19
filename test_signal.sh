#!/usr/bin/env sh
set -xe
# ./test_get.sh org.mpris.MediaPlayer2.Player
exec dbus-monitor "type='signal',sender='org.mpris.MediaPlayer2.ExampleForTemplate',interface='$1'"
