#!/usr/bin/env python3
"""Does a size request that a size-allocate handler sets lay the child out again?
usage: handler.py direct|idle"""
import sys
import time

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

mode = sys.argv[1]
win = Gtk.Window()
win.set_default_size(400, 300)
vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
win.add(vbox)
layout = Gtk.Layout()
fixed = Gtk.Fixed()
layout.put(fixed, 0, 0)
vbox.pack_start(layout, True, True, 0)
child = Gtk.DrawingArea()
child.set_size_request(10, 10)
fixed.put(child, 0, 0)
win.show_all()


def follow(*_):
    a = layout.get_allocation()
    child.set_size_request(a.width, a.height)


if mode == "direct":
    layout.connect("size-allocate", follow)
else:
    layout.connect("size-allocate", lambda *a: GLib.idle_add(follow))


def pump(seconds):
    end = time.time() + seconds
    while time.time() < end:
        while Gtk.events_pending():
            Gtk.main_iteration()
        time.sleep(0.01)


pump(1.0)
for size in ((600, 450), (300, 200), (500, 350)):
    win.resize(*size)
    pump(1.0)
    la = layout.get_allocation()
    ca = child.get_allocation()
    print(mode, "window", size, "layout", (la.width, la.height), "child", (ca.width, ca.height), "request", child.get_size_request())
