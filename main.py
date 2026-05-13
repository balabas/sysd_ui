#!/usr/bin/env python3
from __future__ import annotations

import logging
import os
import sys

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import Gio

from ui.main_window import MainWindow


logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)


class SysdApp(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id="com.local.sysd_ui",
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )
        self.window = MainWindow()

    def do_activate(self) -> None:
        if self.window.window is None:
            self.window.build(self)
        self.window.window.present()


def main() -> None:
    logging.getLogger("sysd_ui").info("pid=%s argv=%s", os.getpid(), sys.argv)
    app = SysdApp()
    app.run([])


if __name__ == "__main__":
    main()
