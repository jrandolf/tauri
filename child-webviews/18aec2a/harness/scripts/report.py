#!/usr/bin/env python3
"""The numbers of the pull request, as Markdown, from the measurements in out/.

usage: report.py [OUTDIR [SUFFIX]]      (default: out) writes the tables to stdout. SUFFIX picks the runs of a
directory name such as pr-scale2 (GDK_SCALE=2): `report.py out -scale2`.

Each column is a variant of the Tauri tree (scripts/sync.sh): base, pr (#15704), old, sloper, after.
A cell reads "-" where the run was not made.
"""
import json
import os
import re
import sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(H, "out")
SUFFIX = sys.argv[2] if len(sys.argv) > 2 else ""  # e.g. -scale2: the runs with GDK_SCALE=2
VARIANTS = [
    ("base", "dev"),
    ("pr", "#15704"),
    ("old", "overlay branch"),
    ("sloper", "desktop pin"),
    ("after", "this branch"),
]
ROOMS = ("GtkScrolledWindow", "GtkLayout", "TauriWebviewContainer", "GtkOverlay")


def load(variant, scenario, session, suffix=None):
    path = os.path.join(OUT, variant + (SUFFIX if suffix is None else suffix), f"{scenario}-{session}.json")
    return json.load(open(path)) if os.path.exists(path) else None


def rec(doc, tag):
    return next((r for r in doc["records"] if r["tag"] == tag), None) if doc else None


def webviews(r):
    """{page: (width, height, x in the window, y in the window)} of the webviews of the first window that has any."""
    out = {}
    for w in r["gtk"]:
        found = {}
        for n in w["tree"]:
            if n["type"] == "WebKitWebView":
                found[n["title"].split()[0]] = (*n["alloc"][2:], *n["in_toplevel"])
        if found:
            return found
    return out


def room(r):
    """The size of the container that holds the webviews: what GTK gives them."""
    for w in r["gtk"]:
        for n in w["tree"]:
            if n["type"] in ROOMS:
                return tuple(n["alloc"][2:])
    return None


def window(r):
    for w in r["gtk"]:
        if any(n["type"] == "WebKitWebView" for n in w["tree"]):
            return tuple(w["size"]), tuple(w["min_size"])
    return None


def size(t):
    return "-" if t is None else f"{t[0]}x{t[1]}"


def table(title, rows, note=None):
    print(f"\n#### {title}\n")
    if note:
        print(note + "\n")
    print("| | " + " | ".join(f"{v} ({label})" for v, label in VARIANTS) + " |")
    print("|---|" + "---|" * len(VARIANTS))
    for label, cells in rows:
        print(f"| {label} | " + " | ".join(cells) + " |")


def cells(fn):
    out = []
    for v, _ in VARIANTS:
        try:
            out.append(fn(v) or "-")
        except (KeyError, IndexError, TypeError, ValueError, StopIteration):
            out.append("-")
    return out


def view_in_room(scenario, session, tag, page="main"):
    def fn(v):
        r = rec(load(v, scenario, session), tag)
        if not r:
            return None
        wv = webviews(r)
        rm = room(r) or wv[page][:2]  # base has no container: the room is the packed webview
        return f"{size(wv[page][:2])} in {size(rm)}"

    return cells(fn)


def wheel(scenario, session, page):
    def fn(v):
        doc = load(v, scenario, session)
        a, b = rec(doc, "settled"), rec(doc, "after-wheel")
        if not (a and b):
            return None
        return f"{webviews(a)[page][3] - webviews(b)[page][3]} px"

    return cells(fn)


def page_sizes(scenario, session, tag, pages):
    def fn(v):
        r = rec(load(v, scenario, session), tag)
        if not r:
            return None
        wv = webviews(r)
        return ", ".join(f"{p} {size(wv[p][:2])}" for p in pages)

    return cells(fn)


def where(scenario, session, tag, page):
    def fn(v):
        r = rec(load(v, scenario, session), tag)
        if not r:
            return None
        w = webviews(r)[page]
        return f"({w[2]}, {w[3]}) {w[0]}x{w[1]}"

    return cells(fn)


def reparent(session):
    def fn(v):
        r = rec(load(v, "reparent", session), "reparent-bounds")
        m = re.search(r"x: ([-0-9.]+), y: ([-0-9.]+)", r["after"])
        return f"({float(m.group(1)):g}, {float(m.group(2)):g})"

    return cells(fn)


def api_bounds(scenario, session, tag, page):
    def fn(v):
        r = rec(load(v, scenario, session), tag)
        b = next(w for w in r["tauri"] if w["label"] == "main")
        x, y, w_, h = next(x["bounds"] for x in b["webviews"] if x["label"] == page)
        return f"({x:g}, {y:g}) {w_:g}x{h:g}"

    return cells(fn)


def clicks(session):
    def fn(v):
        r = rec(load(v, "click", session), "after-click-d946ef")
        counts = {}
        for w in r["gtk"]:
            for n in w["tree"]:
                if n["type"] == "WebKitWebView":
                    m = re.search(r"clicks=(\d+)", n["title"])
                    counts[n["title"].split()[0]] = int(m.group(1))
        return ", ".join(f"{k} {counts[k]}" for k in ("blue", "green", "main"))

    return cells(fn)


def drops(scenario, session, tag):
    def fn(v):
        r = rec(load(v, scenario, session), tag)
        a, b = r["drops-before"], r["drops-after"]
        return ", ".join(f"{k} +{b[k] - a[k]}" for k in sorted(b))

    return cells(fn)


def visible(scenario, session, shot, color, suffix=""):
    """The part of a page that shows in a screenshot, from its color: x, y, width, height, as the display has it."""
    import subprocess

    def fn(v):
        path = os.path.join(OUT, v + suffix, f"{scenario}-{session}-{shot}.png")
        if not os.path.exists(path):
            return None
        r = subprocess.run([sys.executable, "-I", os.path.join(H, "scripts", "findbox.py"), path, color], capture_output=True, text=True)
        n = r.stdout.split()
        return "{}x{} at ({}, {})".format(n[2], n[3], n[0], n[1]) if len(n) == 4 else "none"

    return cells(fn)


def latency():
    def fn(v):
        r = rec(load(v, "latency", "x11"), "latency")["results"]
        return "/".join(str(x["ms"]) for x in r[:6]) + " ms"

    return cells(fn)


def idle(session):
    def fn(v):
        r = rec(load(v, "idle", session), "idle-cpu")
        return "{:.1f} % of a core, {} layout passes, {} allocations of the room".format(
            r["percent_of_one_core"], r.get("layouts", "?"), r.get("allocations", "?")
        )

    return cells(fn)


def shrinks(scenario, session, tag):
    def fn(v):
        r = rec(load(v, scenario, session), tag)
        win, minimum = window(r)
        return f"window {size(win)}, its minimum {size(minimum)}"

    return cells(fn)


def scale2():
    table(
        "Scale factor 2 (`GDK_SCALE=2`, X11): the same sizes, in logical pixels",
        [
            ("the window's webview, 600x400 window, menu bar", view_in_room("menu", "x11", "settled")),
            ("the window's webview, the window grows to 900x700", view_in_room("menu", "x11", "grown-900x700")),
            ("the four children of `examples/multiwebview`", page_sizes("multi", "x11", "settled", ["main1", "main4"])),
            ("five turns of the wheel over the window's webview, menu bar", wheel("menu", "x11", "main")),
            ("five turns of the wheel, child at (40, 320) 300x400", wheel("past", "x11", "child")),
            ("`Webview::reparent` of the child that was at (60, 60)", reparent("x11")),
        ],
    )


def shape(doc):
    """What a run says, apart from noise: per checkpoint, the webviews of each window (page, size, place in the window),
    the room, and what `Webview::bounds` returns."""
    out = {}
    for r in doc["records"]:
        if "gtk" not in r:
            out[r["tag"]] = {k: v for k, v in r.items() if k != "tag"}
            continue
        windows = []
        for w in r["gtk"]:
            views = sorted(
                (n["title"].split()[0], tuple(n["alloc"]), tuple(n["in_toplevel"]))
                for n in w["tree"]
                if n["type"] == "WebKitWebView"
            )
            rooms = [tuple(n["alloc"]) for n in w["tree"] if n["type"] in ROOMS]
            windows.append((tuple(views), tuple(rooms), tuple(w["size"])))
        tauri = {w["label"]: {x["label"]: x["bounds"] for x in w["webviews"]} for w in r["tauri"]}
        out[r["tag"]] = {"windows": sorted(windows), "tauri": tauri}
    return out


def backport():
    """The commits of the branch on the tag v2.12.5 (`backport`) against the branch on dev (`after`), per scenario."""
    print("\n#### The backport on v2.12.5 gives the same numbers as the branch on `dev`\n")
    print("| scenario | X11 | Wayland |")
    print("|---|---|---|")
    for scenario in ("menu", "plain", "past", "multi", "reparent", "bounds"):
        cells = []
        for session in ("x11", "wayland"):
            a, b = load("after", scenario, session, ""), load("backport", scenario, session, "")
            if not (a and b):
                cells.append("-")
                continue
            sa, sb = shape(a), shape(b)
            diff = [t for t in sa if sa[t] != sb.get(t)]
            cells.append("same, {} checkpoints".format(len(sa)) if not diff else "differs at " + ", ".join(diff))
        print(f"| {scenario} | {cells[0]} | {cells[1]} |")


if __name__ == "__main__" and SUFFIX == "-scale2":
    print("### Results with a scale factor of 2\n")
    scale2()
elif __name__ == "__main__":
    print("### Results\n")
    print("Ubuntu 24.04 arm64, GTK 3.24.41, WebKitGTK 2.52.6, Xvfb (X11) and Weston 13 (Wayland), `unstable` on.")
    print("Sizes and places are the GTK allocations of the webviews, in logical pixels.")

    table(
        "Problem 1: the window's own webview, and its room",
        [
            ("X11, 600x400 window, menu bar", view_in_room("menu", "x11", "settled")),
            ("X11, the window shrinks to 320x240", view_in_room("menu", "x11", "shrunk-320x240")),
            ("X11, the window grows to 900x700", view_in_room("menu", "x11", "grown-900x700")),
            ("Wayland, 800x600 window", view_in_room("plain", "wayland", "settled")),
            ("Wayland, the window grows to 900x700", view_in_room("plain", "wayland", "grown-900x700")),
        ],
    )
    table(
        "Problem 1: children that resize with the window (the layout of `examples/multiwebview`, 800x600)",
        [
            ("X11, the four children", page_sizes("multi", "x11", "settled", ["main1", "main2", "main3", "main4"])),
            ("Wayland, the four children", page_sizes("multi", "wayland", "settled", ["main1", "main2", "main3", "main4"])),
            ("Wayland, the window grows to 1000x700", page_sizes("multi", "wayland", "grown-1000x700", ["main1", "main4"])),
            ("Wayland, the window shrinks to 400x300", page_sizes("multi", "wayland", "shrunk-400x300", ["main1", "main4"])),
        ],
        "The room is 800x600 on X11 and on Wayland, so each child should be 400x300.",
    )
    table(
        "Problem 2: how far five turns of the mouse wheel move the webviews",
        [
            ("X11, menu bar, the window's webview", wheel("menu", "x11", "main")),
            ("Wayland, the window's webview", wheel("plain", "wayland", "main")),
            ("X11, child at (40, 320) 300x400 in an 800x600 window", wheel("past", "x11", "child")),
            ("Wayland, the same child", wheel("past", "wayland", "child")),
        ],
    )
    table(
        "Problem 3: where `Webview::reparent` puts a child that was at (60, 60)",
        [("X11", reparent("x11")), ("Wayland", reparent("wayland"))],
    )
    table(
        "Regression: the window shrinks below the size of its webviews",
        [
            ("X11, 800x600 window with a 800x600 webview, set to 320x240", shrinks("plain", "x11", "shrunk-320x240")),
            ("X11, menu bar, set to 320x240", shrinks("menu", "x11", "shrunk-320x240")),
            ("Wayland, 800x600 window, set to 320x240", shrinks("plain", "wayland", "shrunk-320x240")),
        ],
        "The minimum is what GTK asks for. A window can shrink to it and no further.",
    )
    table(
        "Placement: `set_position`, `set_size`, `set_bounds` and a window that grows (child at (100, 100) 200x150)",
        [
            ("X11, `set_position` then `set_size` at once", api_bounds("bounds", "x11", "position-then-size", "child")),
            ("X11, `set_size` then `set_position` at once", api_bounds("bounds", "x11", "size-then-position", "child")),
            ("X11, `set_bounds`", api_bounds("bounds", "x11", "set-bounds", "child")),
            ("X11, the window grows to 1000x700", api_bounds("bounds", "x11", "window-grown", "child")),
            ("Wayland, `set_bounds`", api_bounds("bounds", "wayland", "set-bounds", "child")),
        ],
        "Each cell is what `Webview::bounds` returns. The GTK allocation of the webview is the same in each run where the layout holds.",
    )
    table(
        "Where GTK puts a child (child at (40, 320) 300x400 in an 800x600 window)",
        [("X11", where("past", "x11", "settled", "child")), ("Wayland", where("past", "wayland", "settled", "child"))],
    )
    table(
        "What shows of that child: it reaches past the bottom edge of the window, so 280 of its 400 rows should show",
        [("X11, in the screenshot", visible("past", "x11", "start", "2563eb", "-nodmabuf"))],
        "The window is at the top left corner of the display on X11. These runs have `WEBKIT_DISABLE_DMABUF_RENDERER=1`: the default renderer of WebKitGTK does not draw the top rows of a webview that reaches past the edge of the window, with every variant, in Xvfb.",
    )
    table(
        "Clicks: one click on each of blue, green and the window's webview (counts of clicks per page)",
        [("X11", clicks("x11")), ("Wayland", clicks("wayland"))],
    )
    table(
        "Drops of a file, dragged from another window",
        [
            ("X11, no child, on the window's webview", drops("dnd", "x11", "dnd-main-only")),
            ("X11, child, on the child", drops("dndchild", "x11", "dnd-over-child")),
            ("X11, child, on the window's webview beside the child", drops("dndchild", "x11", "dnd-main-beside-child")),
            ("Wayland, no child, on the window's webview", drops("dnd", "wayland", "dnd-main-only")),
            ("Wayland, child, on the child", drops("dndchild", "wayland", "dnd-over-child")),
            ("Wayland, child, on the window's webview beside the child", drops("dndchild", "wayland", "dnd-main-beside-child")),
        ],
        "A cell shows the drop events that each page got. Each row should show +1 for the page under the pointer. On `dev` the child is stacked below the window's webview, so the point beside the child is on the child.",
    )
    table(
        "Time until the window's webview has the size of its room after `Window::set_size` (X11, six sizes)",
        [("milliseconds", latency())],
    )
    table(
        "At rest for 5 s, after the window resized twice, a window with two webviews that auto-resize: CPU of the app, layout passes of GTK, and allocations of the widget that holds the webviews",
        [("X11", idle("x11")), ("Wayland", idle("wayland"))],
    )
    def edge(session):
        def fn(v):
            r = rec(load(v, "edge", session), "after-click-on-menu-bar")
            over = next(
                int(re.search(r"clicks=(\d+)", n["title"]).group(1))
                for w in r["gtk"]
                for n in w["tree"]
                if n["type"] == "WebKitWebView" and n["title"].startswith("over")
            )
            return "menu {}, child got {} click{}".format("opened" if len(r["gtk"]) > 1 else "did not open", over, "" if over == 1 else "s")

        return cells(fn)

    def menu_follows(tag):
        def fn(v):
            r = rec(load(v, "menuhide", "x11"), tag)
            wv = webviews(r)
            return "room {}, window's webview {}, half child {}".format(size(room(r)), size(wv["main"][:2]), size(wv["half"][:2]))

        return cells(fn)

    table(
        "The menu bar hides and shows (X11, 800x600 window, a webview and a child that resize with it)",
        [
            ("menu bar shown", menu_follows("settled")),
            ("menu bar hidden: the room is 25 px higher, the window is the same", menu_follows("menu-hidden")),
            ("menu bar shown again", menu_follows("menu-shown")),
        ],
        "The webviews that resize with the window should have the size of the room. With #15704 they do not follow it.",
    )
    table(
        "A child that reaches over the menu bar (child at (5, -60) 100x200): a click on the menu bar",
        [("X11", edge("x11")), ("Wayland", edge("wayland"))],
    )
    backport()
