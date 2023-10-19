import base64

from gi.repository import Gtk, GObject, GLib

from app import PlayerApp, Track
from gdbus_ext import DBusTemplate


@DBusTemplate(filename="mpris.xml")
class Mpris(GObject.Object):
    def __init__(self, app: PlayerApp):
        self.app = app

    def start(self):
        self.app.connect("notify::state", self.on_app_state_notify)
        self.app.connect("notify::current-track", self.on_app_current_track_notify)
        self.app.connect("notify::tracklist", self.on_app_tracklist_notify)
        self.app.connect("notify::playlists", self.on_app_playlists_notify)
        self.app.connect("seek", self.on_app_seek)

        DBusTemplate.register_object(
            self.app.get_dbus_connection(),
            "org.mpris.MediaPlayer2.ExampleForTemplate",
            "/org/mpris/MediaPlayer2",
            self,
        )

    ## App signal handlers

    def on_app_state_notify(self, *args):
        DBusTemplate.properties_changed(
            self, "org.mpris.MediaPlayer2.Player", ("PlaybackStatus",)
        )

    def on_app_current_track_notify(self, *args):
        DBusTemplate.properties_changed(
            self, "org.mpris.MediaPlayer2.Player", ("Metadata",)
        )

    def on_app_tracklist_notify(self, *args):
        DBusTemplate.properties_changed(
            self, "org.mpris.MediaPlayer2.TrackList", ("Tracks",)
        )

    def on_app_playlists_notify(self, *args):
        DBusTemplate.properties_changed(
            self,
            "org.mpris.MediaPlayer2.Playlists",
            ("PlaylistCount", "ActivePlaylist"),
        )

    def on_app_seek(self, app, value: int):
        self.seeked(value)

    ### org.mpris.MediaPlayer2

    # name is usually optional and auto-generated, but in this case "raise" is a keyword in Python
    @DBusTemplate.Method(name="Raise")
    def _raise(self):
        self.__msg("got raise")

    # interface name is optional as long as there are no conflicts.
    @DBusTemplate.Method(interface="org.mpris.MediaPlayer2")
    def quit(self):
        self.__msg("got quit", lambda *args: self.app.quit())

    # This will refer to CanQuit.
    # SIGNATURES AND ANY TYPE HINTS ARE NOT ACTUALLY CHECKED BY DBusTemplate.
    @DBusTemplate.Property()
    def can_quit(self) -> bool:
        return True

    @DBusTemplate.Property()
    def fullscreen(self) -> bool:
        return self.app.window.is_fullscreen()

    @fullscreen.setter
    def fullscreen(self, value: bool):
        if value:
            self.app.window.fullscreen()
        else:
            self.app.window.unfullscreen()

    @DBusTemplate.Property()
    def can_raise(self) -> bool:
        return False

    @DBusTemplate.Property()
    def has_track_list(self) -> bool:
        return True

    @DBusTemplate.Property()
    def identity(self) -> str:
        return "Example Media Player for Gio.DBusTemplate"

    @DBusTemplate.Property()
    def desktop_entry(self) -> str:
        return ""

    @DBusTemplate.Property()
    def supported_uri_schemes(self) -> list[str]:
        return ["dummy"]

    @DBusTemplate.Property()
    def supported_mime_types(self) -> list[str]:
        return ["audio/mpeg", "audio/ogg", "audio/vnd.wav"]

    ### org.mpris.MediaPlayer2.Player

    @DBusTemplate.Method()
    def next(self):
        self.app.next()

    @DBusTemplate.Method()
    def previous(self):
        self.app.prev()

    @DBusTemplate.Method()
    def pause(self):
        self.app.pause()

    @DBusTemplate.Method()
    def play_pause(self):
        self.app.play_pause()

    @DBusTemplate.Method()
    def stop(self):
        self.app.stop()

    @DBusTemplate.Method()
    def play(self):
        self.app.play()

    @DBusTemplate.Method()
    def seek(self, offset: int):
        self.app.seek(offset)

    @DBusTemplate.Method()
    def set_position(self, track_id: str, position: int):
        self.app.switch_track_by_uri(self._track_path_to_uri(track_id))
        self.app.seek(position)

    @DBusTemplate.Method()
    def open_uri(self, uri: str):
        self.app.switch_track_by_uri(uri)

    @DBusTemplate.Signal()
    def seeked(self, position: int):
        pass
        # arguments can also be manipulated before emitting:
        # return position - 100

    @DBusTemplate.Property()
    def playback_status(self) -> str:
        return self.app.state.capitalize()

    @DBusTemplate.Property()
    def loop_status(self) -> str:
        # we don't implement this
        return "None"

    @loop_status.setter
    def loop_status(self, value: str):
        # we don't implement this, just pretend it worked.
        pass

    @DBusTemplate.Property()
    def rate(self) -> float:
        # we don't implement this
        return 1

    @rate.setter
    def rate(self, value: float):
        # we don't implement this, just pretend it worked.
        pass

    @DBusTemplate.Property()
    def shuffle(self) -> bool:
        # we don't implement this
        return False

    @shuffle.setter
    def shuffle(self, value: bool):
        # we don't implement this, just pretend it worked.
        pass

    @DBusTemplate.Property()
    def metadata(self) -> dict[str, GLib.Variant]:
        return self._get_track_metadata(self.app.current_track)

    @DBusTemplate.Property(emit_changed=False)
    def position(self) -> int:
        return int(self.app.window.seeker.get_value())

    @DBusTemplate.Property()
    def minimum_rate(self) -> float:
        return 1

    @DBusTemplate.Property()
    def maximum_rate(self) -> float:
        return 1

    @DBusTemplate.Property()
    def can_go_next(self) -> bool:
        return True

    @DBusTemplate.Property()
    def can_go_previous(self) -> bool:
        return True

    @DBusTemplate.Property()
    def can_play(self) -> bool:
        return True

    @DBusTemplate.Property()
    def can_pause(self) -> bool:
        return True

    @DBusTemplate.Property()
    def can_seek(self) -> bool:
        return True

    @DBusTemplate.Property(emit_changed=False)
    def can_control(self) -> bool:
        return True

    ### org.mpris.MediaPlayer2.TrackList

    @DBusTemplate.Method()
    def get_tracks_metadata(
        self, track_ids: list[str]
    ) -> list[dict[str, GLib.Variant]]:
        metadatas = []
        for track_path in track_ids:
            track_uri = self._track_path_to_uri(track_path)
            metadatas.append(
                self._get_track_metadata(self.app.parse_track_uri(track_uri))
            )
        return metadatas

    @DBusTemplate.Method()
    def add_track(self, uri: str, after_track: str, set_as_current: bool):
        tracks: list[Track] = list(self.app.tracklist)
        insert_pos = None
        for i, track in enumerate(tracks):
            if self._track_uri_to_path(track["uri"]) == after_track:
                insert_pos = i
                break
        if insert_pos is None:
            print("warning: insert_pos was None in add_track")
            insert_pos = len(tracks)

        tracks.insert(insert_pos, self.app.parse_track_uri(uri))
        self.app.tracklist = tracks

        if set_as_current:
            self.app.switch_track_by_uri(uri)

    @DBusTemplate.Method()
    def remove_track(self, track_id: str):
        remove_val = None
        tracks: list[Track] = list(self.app.tracklist)
        for i, track in enumerate(tracks):
            if self._track_uri_to_path(track["uri"]) == track_id:
                remove_val = track
                break
        if remove_val is not None:
            tracks.remove(remove_val)
            self.app.tracklist = tracks

    @DBusTemplate.Method()
    def go_to(self, track_id: str):
        val = None
        for i, track in enumerate(self.app.tracklist):
            if self._track_uri_to_path(track["uri"]) == track_id:
                val = track
                break
        if val is not None:
            self.app.switch_track_by_uri(val["uri"])

    @DBusTemplate.Signal()
    def track_list_replaced(self, tracks: list[str], current_track: str):
        # we don't fire this in this demo
        pass

    @DBusTemplate.Property(emit_with_value=False)
    def tracks(self) -> list[str]:
        return [self._track_uri_to_path(x["uri"]) for x in self.app.tracklist]

    @DBusTemplate.Property()
    def can_edit_tracks(self) -> bool:
        return True

    ### org.mpris.MediaPlayer2.Playlists

    @DBusTemplate.Method()
    def activate_playlist(self, playlist_id: str):
        playlist_index = self._playlist_path_to_id(playlist_id)
        if playlist_index < len(self.app.playlists):
            print(self.app.playlists[playlist_index])
            self.app.tracklist = self.app.playlists[playlist_index]["tracks"]
            self.app.switch_track(0)

    @DBusTemplate.Method()
    def get_playlists(
        self, index: int, max_count: int, order: str, reverse_order: bool
    ) -> list[tuple[str, str, str]]:
        # TODO
        raise NotImplementedError()

    @DBusTemplate.Signal()
    def playlist_changed(self, playlist: tuple[str, str, str]):
        # for this demo we don't emit this
        pass

    @DBusTemplate.Property()
    def playlist_count(self) -> int:
        return len(self.app.playlists)

    @DBusTemplate.Property()
    def orderings(self) -> list[str]:
        # for this demo we don't support this
        return ["default"]

    @DBusTemplate.Property()
    def active_playlist(self) -> tuple[bool, tuple[str, str, str]]:
        # for this demo we don't emit this
        return (
            False,
            ("/", "", ""),
        )

    ###

    def __msg(self, message, cb=None):
        if cb is None:
            cb = lambda *args: ...
        Gtk.AlertDialog(message=message, modal=True, buttons=["OK"]).choose(
            self.app.window, None, cb
        )

    @staticmethod
    def _track_path_to_uri(track_path):
        if not track_path.startswith("/de/capypara/ExampleForTemplate/TrackList/Track"):
            raise ValueError("invalid track path")
        track_id_b64 = track_path.replace(
            "/de/capypara/ExampleForTemplate/TrackList/Track", ""
        )
        return str(base64.b16decode(track_id_b64), "utf-8")

    @staticmethod
    def _track_uri_to_path(track_id):
        return f"/de/capypara/ExampleForTemplate/TrackList/Track{str(base64.b16encode(bytes(track_id, 'utf-8')), 'utf-8')}"

    @staticmethod
    def _playlist_path_to_id(playlist_path):
        if not playlist_path.startswith(
            "/de/capypara/ExampleForTemplate/Playlist/Playlist"
        ):
            raise ValueError("invalid playlist path")
        playlist_id = playlist_path.replace(
            "/de/capypara/ExampleForTemplate/Playlist/Playlist", ""
        )
        return int(playlist_id)

    @staticmethod
    def _playlist_id_to_path(playlist_id):
        return f"/de/capypara/ExampleForTemplate/Playlist/Playlist{playlist_id}"

    @classmethod
    def _get_track_metadata(cls, track: Track):
        title = "Unknown"
        if track["track"] is not None:
            title = track["track"]
        artist = "Unknown"
        if track["track"] is not None:
            artist = track["artist"]
        return {
            "mpris:trackid": GLib.Variant("o", cls._track_uri_to_path(track["uri"])),
            "xesam:url": GLib.Variant("s", track["uri"]),
            "xesam:title": GLib.Variant("s", title),
            "xesam:artist": GLib.Variant("as", [artist]),
        }
