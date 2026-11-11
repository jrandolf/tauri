#!/usr/bin/env python3
"""How many frames after a window resize has the child the size of the room?
usage: frames.py layout-idle | subclass | packed"""
import sys
import time

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, GObject, Gtk  # noqa: E402

mode = sys.argv[1]


class RoomFixed(Gtk.Fixed):
    __gtype_name__ = "RoomFixed"

    def do_get_preferred_width(self):
        return 0, 0

    def do_get_preferred_height(self):
        return 0, 0

    def do_size_allocate(self, a):
        for c in self.get_children():
            c.set_size_request(a.width, a.height)
        Gtk.Fixed.do_size_allocate(self, a)


win = Gtk.Window()
win.set_default_size(400, 300)
vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
win.add(vbox)
child = Gtk.DrawingArea()
if mode == "layout-idle":
    layout = Gtk.Layout()
    fixed = Gtk.Fixed()
    layout.put(fixed, 0, 0)
    vbox.pack_start(layout, True, True, 0)
    fixed.put(child, 0, 0)
    room = layout
    layout.connect("size-allocate", lambda l, a: GLib.idle_add(lambda: child.set_size_request(room.get_allocation().width, room.get_allocation().height)))
elif mode == "subclass":
    fixed = RoomFixed()
    vbox.pack_start(fixed, True, True, 0)
    fixed.put(child, 0, 0)
    room = fixed
elif mode == "layout-direct":
    layout = Gtk.Layout()
    vbox.pack_start(layout, True, True, 0)
    layout.put(child, 0, 0)
    room = layout
    layout.connect("size-allocate", lambda l, a: child.set_size_request(a.width, a.height))
elif mode == "fixed-handler":
    fixed = Gtk.Fixed()
    vbox.pack_start(fixed, True, True, 0)
    fixed.put(child, 0, 0)
    room = fixed
    fixed.connect("size-allocate", lambda l, a: child.set_size_request(a.width, a.height))
elif mode == "packed":
    vbox.pack_start(child, True, True, 0)
    room = child
child.set_size_request(10, 10) if mode != "packed" else None
win.show_all()


def pump(seconds):
    end = time.time() + seconds
    while time.time() < end:
        while Gtk.events_pending():
            Gtk.main_iteration()
        time.sleep(0.005)


pump(1.0)
clock = win.get_frame_clock()
frames = []


def painted(clock):
    r, c = room.get_allocation(), child.get_allocation()
    frames.append(((r.width, r.height), (c.width, c.height)))


clock.connect("after-paint", painted)
for size in ((600, 450), (300, 200), (500, 350)):
    frames.clear()
    win.resize(*size)
    pump(0.5)
    first_match = next((i for i, (r, c) in enumerate(frames) if r == c and r != (0, 0) and r[0] == size[0]), None)
    print(mode, "resize to", size, "painted frames until the child matches the room:", None if first_match is None else first_match + 1, "of", len(frames), "frames:", frames[:4])
