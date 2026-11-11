#!/usr/bin/env python3
"""usage: summarize.py out/VARIANT/SCENARIO-SESSION.json ...  prints what GTK and Tauri say, per checkpoint."""
import json
import sys

KEEP = ("TauriWebviewContainer", "GtkScrolledWindow", "GtkViewport", "GtkFixed", "GtkLayout", "GtkOverlay", "WebKitWebView", "GtkBox", "GtkMenuBar")


def show(path):
    d = json.load(open(path))
    print(f"### {d['scenario']} {d['session']}")
    for r in d["records"]:
        if "gtk" not in r:
            print(f"  [{r['tag']}] " + ", ".join(f"{k}={v}" for k, v in r.items() if k != "tag"))
            continue
        print(f"  [{r['tag']}] toplevels={len(r['gtk'])}")
        for w in r["gtk"]:
            print(f"    window gtk_size={w['size']} min={w['min_size']}")
            for n in w["tree"]:
                if n["type"] in KEEP and n["depth"] > 0:
                    extra = ""
                    if "title" in n:
                        extra += f" title={n['title']!r} request={n['size_request']}"
                    if "scroll" in n:
                        extra += f" scroll={n['scroll']}"
                    print(f"      {'  ' * (n['depth'] - 1)}{n['type']} alloc={n['alloc']} in_toplevel={n['in_toplevel']}{extra}")
        for w in r["tauri"]:
            wv = {x["label"]: x["bounds"] for x in w["webviews"]}
            print(f"    tauri window {w['label']}: inner={w['inner_size']} outer={w['outer_size']} webview bounds={wv}")


for p in sys.argv[1:]:
    show(p)
