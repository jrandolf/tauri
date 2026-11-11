#!/usr/bin/env python3
"""A window that is the source of a file drag: dragging its label offers one file. For drop tests."""
import os
import sys

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gtk  # noqa: E402

path = sys.argv[1]
open(path, "a").close()
css = Gtk.CssProvider()
css.load_from_data(b"window, box, label { background: #ff0000; color: white; font: bold 16px sans-serif; }")
Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
win = Gtk.Window()
win.set_decorated(False)
win.set_default_size(240, 120)
if os.environ.get("GDK_BACKEND") == "x11":
    win.move(1100, 100)
box = Gtk.EventBox()
box.add(Gtk.Label(label="drag me"))
win.add(box)
target = Gtk.TargetEntry.new("text/uri-list", 0, 0)
box.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, [target], Gdk.DragAction.COPY)
box.connect("drag-data-get", lambda w, ctx, data, info, time: data.set_uris(["file://" + path]))
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
