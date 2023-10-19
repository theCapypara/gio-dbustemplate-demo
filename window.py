"""The actual example media player window. Not really too important for the actual D-Bus example."""
from __future__ import annotations

from copy import deepcopy
from functools import wraps
from traceback import print_exc
from typing import TYPE_CHECKING, cast

import strictyaml
from gi.repository import Gtk, GLib

if TYPE_CHECKING:
    from mpris_demo import PlayerApp


def try_parse(lbl_name):
    def deco(func):
        @wraps(func)
        def wrapper(self, *args):
            lbl = getattr(self, lbl_name)
            try:
                func(self, *args)
                lbl.set_text("OK")
            except Exception:
                print_exc()
                lbl.set_text("ERR")

        return wrapper

    return deco


@Gtk.Template(filename="window.ui")
class PlayerWindow(Gtk.Window):
    __gtype_name__ = "PlayerWindow"

    tracklist_buff = cast(Gtk.TextBuffer, Gtk.Template.Child())
    playlists_buff = cast(Gtk.TextBuffer, Gtk.Template.Child())
    seeker = cast(Gtk.Scale, Gtk.Template.Child())
    current_track_lbl = cast(Gtk.Label, Gtk.Template.Child())
    state = cast(Gtk.Label, Gtk.Template.Child())
    parse_state_tracklist = cast(Gtk.Label, Gtk.Template.Child())
    parse_state_playlists = cast(Gtk.Label, Gtk.Template.Child())
    switch_track_id = cast(Gtk.Entry, Gtk.Template.Child())

    _suppress_textbuffer: bool
    _suppress_seek: bool

    def __init__(self, app: PlayerApp, *args):
        super().__init__(*args)
        self.app = app

        self._suppress_seek = False
        self._suppress_textbuffer = False

    @Gtk.Template.Callback()
    def on_realize(self, *args):
        self.app.connect("notify::state", self.on_app_state_notify)
        self.app.connect("notify::current-track", self.on_app_current_track_notify)
        self.app.connect("notify::tracklist", self.on_app_tracklist_notify)
        self.app.connect("notify::playlists", self.on_app_playlists_notify)
        self.app.connect("seek", self.on_app_seek)

        self.on_playlists_changed()
        self.on_tracklist_changed()
        self.on_stop_clicked()

        self.on_submit_switch_track_id_clicked()
        GLib.timeout_add_seconds(1, self.on_second_passed)

    def on_second_passed(self):
        if self.app.get_property("state") == "playing":
            self._suppress_seek = True
            self.seeker.set_value(self.seeker.get_value() + 1)
            self._suppress_seek = False
        return True

    @Gtk.Template.Callback()
    @try_parse("parse_state_tracklist")
    def on_tracklist_changed(self, *args):
        if self._suppress_textbuffer:
            return
        tracks = [
            self.app.parse_track_uri(x)
            for x in self.tracklist_buff.get_text(
                self.tracklist_buff.get_start_iter(),
                self.tracklist_buff.get_end_iter(),
                False,
            ).splitlines()
        ]
        self.app.tracklist = tracks

    @Gtk.Template.Callback()
    @try_parse("parse_state_playlists")
    def on_playlists_changed(self, *args):
        if self._suppress_textbuffer:
            return
        playlists_text = self.playlists_buff.get_text(
            self.playlists_buff.get_start_iter(),
            self.playlists_buff.get_end_iter(),
            False,
        )
        playlists = strictyaml.load(playlists_text).data
        assert isinstance(playlists, list)
        for playlist in playlists:
            assert isinstance(playlist, dict)
            assert "name" in playlist
            assert isinstance(playlist["name"], str)
            assert "tracks" in playlist
            assert isinstance(playlist["tracks"], list)
            tracks = []
            for track in playlist["tracks"]:
                assert isinstance(track, str)
                tracks.append(self.app.parse_track_uri(track))
            playlist["tracks"] = tracks
        self.app.playlists = playlists

    @Gtk.Template.Callback()
    def on_seeker_change_value(self, _range, _scroll, value):
        if not self._suppress_seek:
            self.app.seek(int(value))

    @Gtk.Template.Callback()
    def on_play_pause_clicked(self, *args):
        self.app.play_pause()

    @Gtk.Template.Callback()
    def on_stop_clicked(self, *args):
        self.app.stop()

    @Gtk.Template.Callback()
    def on_next_clicked(self, *args):
        self.app.next()

    @Gtk.Template.Callback()
    def on_prev_clicked(self, *args):
        self.app.prev()

    @Gtk.Template.Callback()
    def on_submit_switch_track_id_clicked(self, *args):
        try:
            track_id = int(self.switch_track_id.get_text())
        except ValueError:
            return
        self.app.switch_track(track_id)

    def on_app_state_notify(self, *args):
        self.state.set_text(self.app.state.capitalize())

    def on_app_current_track_notify(self, *args):
        self.current_track_lbl.set_text(
            f"{self.app.current_track['uri']}\nA-T: {self.app.current_track['artist']} - {self.app.current_track['track']}"
        )

    def on_app_tracklist_notify(self, *args):
        # we delay this, since we may still be in a user action
        def delayed():
            uris = [x["uri"] for x in self.app.tracklist]
            self._suppress_textbuffer = True
            self.tracklist_buff.set_text("\n".join(uris) + "\n")
            self._suppress_textbuffer = False

        GLib.idle_add(delayed)

    def on_app_playlists_notify(self, *args):
        # we delay this, since we may still be in a user action
        def delayed():
            self._suppress_textbuffer = True
            playlists = deepcopy(self.app.playlists)
            for playlist in playlists:
                tracks_strs = []
                for track in playlist["tracks"]:
                    tracks_strs.append(track["uri"])
                playlist["tracks"] = tracks_strs
            self.playlists_buff.set_text(
                strictyaml.as_document(playlists).as_yaml() + "\n"
            )
            self._suppress_textbuffer = False

        GLib.idle_add(delayed)

    def on_app_seek(self, app, value: int):
        self._suppress_seek = True
        self.seeker.set_value(value)
        self._suppress_seek = False
