import sys
import gi

gi.require_version("Gtk", "4.0")

from app import PlayerApp


if __name__ == "__main__":
    app = PlayerApp()
    exit(app.run(sys.argv))
