# Example for Gio.DBusTemplate

This is an example for an implementation for "Gio.DBusTemplate" for PyGObject.

See merge request: -link here-

Run `main.py` for an example "music player" that implements MPRIS2 using "Gio.DBusTemplate" 
(it doesn't actually play music).

The implementation of "Gio.DBusTemplate" is in "gdbus_ext.py". 

The demo app is a bit yanky, it's really just to show that Mpris2 works. To edit the playlists on the right, the best
thing to do is to copy the YAML out, edit it and then copy it back in.

The Mpris2 implementation is not necessarily fully correct. The version/subset of MPRIS in this demo is the same that
is used by GNOME Music.

The `test_*.sh` scripts are provided to send D-Bus commands or monitor signals. But any mpris client can be used.
