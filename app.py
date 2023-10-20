"""The example Mpris player app"""
from typing import TypedDict, Optional
from urllib.parse import urlparse, parse_qs

from gi.repository import Gtk, GObject


class Track(TypedDict):
    uri: str
    artist: str | None
    track: str | None


class Playlist(TypedDict):
    name: str
    tracks: list[Track]


class PlayerApp(Gtk.Application):
    def __init__(self, *args, **kwargs):
        from mpris_demo import Mpris
        from window import PlayerWindow

        self.window = PlayerWindow(self)
        self.mpris = Mpris(self)

        self._state: str = "stopped"
        self._current_track: Optional[Track] = None
        self._tracklist: list[Track] = []
        self._playlists: list[Playlist] = []

        super().__init__(
            application_id="de.capypara.ExampleForTemplate", *args, **kwargs
        )

    def do_activate(self) -> None:
        self.mpris.start()
        self.window.set_application(self)
        self.window.present()

    @GObject.Property(type=str)
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value

    @GObject.Property(type=object)
    def current_track(self):
        return self._current_track

    @current_track.setter
    def current_track(self, value):
        self._current_track = value

    @GObject.Property(type=object)
    def tracklist(self):
        return self._tracklist

    @tracklist.setter
    def tracklist(self, value):
        self._tracklist = value

    @GObject.Property(type=object)
    def playlists(self):
        return self._playlists

    @playlists.setter
    def playlists(self, value):
        self._playlists = value

    def play(self):
        self.state = "playing"

    def pause(self):
        self.state = "paused"

    def play_pause(self):
        if self.state == "playing":
            self.state = "paused"
        else:
            self.state = "playing"

    def stop(self):
        self.state = "stopped"

    def next(self):
        current_track_idx = self.find_current_track_in_tracklist()
        if current_track_idx is None:
            current_track_idx = -1
        self.switch_track(current_track_idx + 1)

    def prev(self):
        current_track_idx = self.find_current_track_in_tracklist()
        if current_track_idx is None:
            current_track_idx = 1
        self.switch_track(current_track_idx - 1)

    def switch_track(self, track_id):
        if track_id >= len(self.tracklist):
            return
        self.current_track = self.tracklist[track_id]

    def switch_track_by_uri(self, track_uri):
        self.current_track = self.parse_track_uri(track_uri)

    @staticmethod
    def parse_track_uri(track_uri) -> Track:
        o = urlparse(track_uri)
        assert o.scheme == "dummy"
        track = None
        artist = None
        if o.query != "":
            query = parse_qs(o.query)
            track = query.get("track", [None])[0]
            artist = query.get("artist", [None])[0]

        return {"uri": track_uri, "artist": artist, "track": track}

    @GObject.Signal(arg_types=(int,))
    def seek(self, pos):
        return pos

    def find_current_track_in_tracklist(self):
        if self._current_track is None:
            return None
        for i, track in enumerate(self._tracklist):
            if track["uri"] == self._current_track["uri"]:
                return i
        return None
