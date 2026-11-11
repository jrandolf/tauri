#!/usr/bin/env python3
"""usage: findbox.py IMAGE RRGGBB  -> prints "x y width height" of the bounding box of the pixels of
exactly that color, or "none"."""
import sys

from PIL import Image

img = Image.open(sys.argv[1]).convert("RGB")
color = tuple(int(sys.argv[2][i : i + 2], 16) for i in (0, 2, 4))
mask = img.point(lambda v: 0)  # placeholder to keep PIL imported lazily
w, h = img.size
px = img.load()
xs0, ys0, xs1, ys1 = w, h, -1, -1
for y in range(h):
    row_hit = False
    for x in range(w):
        if px[x, y] == color:
            row_hit = True
            if x < xs0:
                xs0 = x
            if x > xs1:
                xs1 = x
    if row_hit:
        if y < ys0:
            ys0 = y
        ys1 = y
print("none" if xs1 < 0 else f"{xs0} {ys0} {xs1 - xs0 + 1} {ys1 - ys0 + 1}")
