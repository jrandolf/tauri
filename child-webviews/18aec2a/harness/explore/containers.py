#!/usr/bin/env python3
"""Probes how GTK 3 containers lay out absolutely placed WebKit webviews, the way wry does it:
put(webview, x, y) and set_size_request(width, height).

usage: containers.py VARIANT SCENARIO
  VARIANT   scrolled-fixed  GtkFixed in a GtkScrolledWindow with the external policy (tauri#15704)
            fixed           GtkFixed in the vbox
            layout-fixed    GtkFixed in a GtkLayout in the vbox
            layout          the webviews in a GtkLayout in the vbox
  SCENARIO  menu     600x400 window with a menu bar, a 600x400 webview at (0, 0)
            past     800x600 window, a webview 800x600 at (0, 0) and one 300x400 at (40, 320)
            shrink   800x600 window with a 800x600 webview, shrunk to 300x200
            negative 600x400 window with a menu bar, a 300x200 webview at (40, -50)
Prints one JSON object per measurement. Run it inside scripts/session.sh.
"""
import json
import os
import subprocess
import sys
import time

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import GLib, Gdk, Gtk, WebKit2  # noqa: E402

PAGE = (
    '<body style="margin:0;background:{bg};font:14px sans-serif;color:#fff">'
    '<div id=t style="padding:4px"></div><script>'
    "function f(){document.getElementById('t').textContent='{name} '+innerWidth+'x'+innerHeight}"
    "f();addEventListener('resize',f)</script>"
)

variant, scenario = sys.argv[1], sys.argv[2]
out_dir = os.environ.get("OUT", "/tmp")


def pump(seconds):
    end = time.time() + seconds
    while time.time() < end:
        while Gtk.events_pending():
            Gtk.main_iteration()
        time.sleep(0.02)


def emit(**kw):
    kw.update(variant=variant, scenario=scenario, session=os.environ.get("SESSION_MODE"))
    print(json.dumps(kw), flush=True)


def webview(name, bg):
    wv = WebKit2.WebView()
    wv.load_html(PAGE.replace("{bg}", bg).replace("{name}", name), None)
    return wv


def alloc(w):
    a = w.get_allocation()
    return [a.x, a.y, a.width, a.height]


def in_toplevel(w, win):
    r = w.translate_coordinates(win, 0, 0)
    return list(r) if r else None


win = Gtk.Window()
win.set_title("containers")
vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
win.add(vbox)

has_menu = scenario in ("menu", "negative")
if has_menu:
    bar = Gtk.MenuBar()
    for label in ("File", "Edit"):
        bar.append(Gtk.MenuItem(label=label))
    vbox.pack_start(bar, False, False, 0)

if variant == "scrolled-fixed":
    fixed = Gtk.Fixed()
    outer = Gtk.ScrolledWindow()
    outer.set_policy(Gtk.PolicyType.EXTERNAL, Gtk.PolicyType.EXTERNAL)
    outer.add(fixed)
    inner = fixed
elif variant == "fixed":
    fixed = Gtk.Fixed()
    outer = inner = fixed
elif variant == "layout-fixed":
    outer = Gtk.Layout()
    fixed = Gtk.Fixed()
    outer.put(fixed, 0, 0)
    inner = fixed
elif variant == "layout":
    outer = inner = Gtk.Layout()
elif variant == "layout-big":
    outer = inner = Gtk.Layout()
    outer.set_size(4000, 4000)
elif variant == "layout-fixed-big":
    outer = Gtk.Layout()
    outer.set_size(4000, 4000)
    fixed = Gtk.Fixed()
    outer.put(fixed, 0, 0)
    inner = fixed
elif variant == "overlay-fixed":
    outer = Gtk.Overlay()
    outer.add(Gtk.Box())
    fixed = Gtk.Fixed()
    outer.add_overlay(fixed)
    outer.set_overlay_pass_through(fixed, True)
    inner = fixed
else:
    raise SystemExit("unknown variant")
vbox.pack_start(outer, True, True, 0)

if scenario == "menu":
    win.set_default_size(600, 400)
    children = {"w0": (0, 0, 600, 400, "#2563eb")}
elif scenario == "past":
    win.set_default_size(800, 600)
    children = {"w0": (0, 0, 800, 600, "#475569"), "w1": (40, 320, 300, 400, "#2563eb")}
elif scenario == "shrink":
    win.set_default_size(800, 600)
    children = {"w0": (0, 0, 800, 600, "#475569")}
elif scenario == "negative":
    win.set_default_size(600, 400)
    children = {"w0": (0, 0, 600, 375, "#475569"), "w1": (40, -50, 300, 200, "#dc2626")}
else:
    raise SystemExit("unknown scenario")

views = {}
for name, (x, y, w, h, bg) in children.items():
    wv = webview(name, bg)
    wv.set_size_request(w, h)
    inner.put(wv, x, y)
    views[name] = wv
win.show_all()
win.connect("destroy", Gtk.main_quit)
pump(2.5)


def snapshot(tag):
    data = {
        "tag": tag,
        "window": list(win.get_size()),
        "window_min": [win.get_preferred_size()[0].width, win.get_preferred_size()[0].height],
        "outer": alloc(outer),
        "inner": alloc(inner),
        "children": {n: {"alloc": alloc(v), "in_toplevel": in_toplevel(v, win)} for n, v in views.items()},
    }
    if variant == "scrolled-fixed":
        v, h = outer.get_vadjustment(), outer.get_hadjustment()
        data["scroll"] = {
            "v": [v.get_value(), v.get_lower(), v.get_upper(), v.get_page_size()],
            "h": [h.get_value(), h.get_lower(), h.get_upper(), h.get_page_size()],
        }
    emit(**data)


def shot(name):
    path = os.path.join(out_dir, f"{variant}-{scenario}-{os.environ.get('SESSION_MODE')}-{name}.png")
    subprocess.run(["import", "-window", "root", path], check=False)
    return path


def find_origin():
    """The toplevel's position in the X screen: the pointer position that GTK reports inside it."""
    gw = win.get_window()
    seat = Gdk.Display.get_default().get_default_seat()
    pointer = seat.get_pointer()
    for y in range(20, 700, 40):
        for x in range(20, 1000, 40):
            subprocess.run(["xdotool", "mousemove", str(x), str(y)], check=False)
            pump(0.08)
            w, px, py, _ = gw.get_device_position(pointer)
            if w is not None and (px, py) != (0, 0):
                return x - px, y - py
    return None


snapshot("start")
start_png = shot("start")
here = os.path.dirname(os.path.abspath(__file__))
rects = {}
for name, (x, y, w, h, bg) in children.items():
    r = subprocess.run(["python3", os.path.join(here, "..", "scripts", "findbox.py"), start_png, bg.lstrip("#")], capture_output=True, text=True)
    rects[name] = r.stdout.strip()
emit(tag="visible", rects=rects)
if os.environ.get("NOSCAN"):
    origin = None
else:
    origin = (0, 0) if os.environ.get("SESSION_MODE") == "x11" else find_origin()
emit(tag="origin", origin=origin)

if scenario in ("menu", "past") and origin is not None:
    target = "w1" if scenario == "past" else "w0"
    x, y = in_toplevel(views[target], win)
    px, py = origin[0] + x + 30, origin[1] + y + 30
    subprocess.run(["xdotool", "mousemove", str(px), str(py)], check=False)
    pump(0.3)
    subprocess.run(["xdotool", "click", "--repeat", "5", "--delay", "80", "5"], check=False)
    pump(1.0)
    snapshot("after-wheel")
    shot("after-wheel")

if scenario == "past":
    views["w1"].grab_focus()
    pump(0.5)
    snapshot("after-focus")

if scenario == "shrink":
    win.resize(300, 200)
    pump(1.0)
    snapshot("after-shrink")
    shot("after-shrink")

if scenario == "negative":
    shot("negative")

win.destroy()
