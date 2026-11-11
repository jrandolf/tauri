#!/usr/bin/env python3
"""Builds the pictures of the pull requests from the screenshots of out/: each one puts the window
of tauri#15704 (variant `pr`) next to the window of the new branch (variant `after`).
usage: figures.py OUTDIR"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(H, "figures")
os.makedirs(OUT, exist_ok=True)
FONT = None
for path in ("/System/Library/Fonts/Helvetica.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
    if os.path.exists(path):
        FONT = ImageFont.truetype(path, 17)
        break
FONT = FONT or ImageFont.load_default()


def findbox(path, color):
    r = subprocess.run([sys.executable, "-I", os.path.join(H, "scripts", "findbox.py"), path, color], capture_output=True, text=True)
    nums = r.stdout.split()
    return tuple(int(n) for n in nums) if len(nums) == 4 else None


def crop_box(session, shot, size, color):
    """The window in a screenshot: at the corner on X11; on Wayland from the top left corner of a page that fills it."""
    if session == "x11":
        return (0, 0, size[0], size[1])
    x, y, _, _ = findbox(shot, color)
    return (max(x - 30, 0), max(y - 50, 0), x + size[0] + 30, y + size[1] + 40)


def panel(path, box, caption):
    img = Image.open(path).convert("RGB").crop(box)
    bar = 30
    out = Image.new("RGB", (img.width, img.height + bar), "white")
    ImageDraw.Draw(out).text((6, 5), caption, fill="black", font=FONT)
    out.paste(img, (0, bar))
    return out


def side_by_side(name, panels):
    gap = 24
    width = sum(p.width for p in panels) + gap * (len(panels) - 1)
    height = max(p.height for p in panels)
    sheet = Image.new("RGB", (width, height), "white")
    x = 0
    for p in panels:
        sheet.paste(p, (x, 0))
        x += p.width + gap
    sheet.save(os.path.join(OUT, name + ".png"), optimize=True)
    print("wrote", name, sheet.size)


def shots(variant, scenario, session, name):
    return os.path.join(H, "out", variant, f"{scenario}-{session}-{name}.png")


def figure(name, scenario, session, shot_name, before_caption, after_caption, size, render="", color="d946ef"):
    before = shots("pr" + render, scenario, session, shot_name)
    after = shots("after" + render, scenario, session, shot_name)
    box = crop_box(session, after, size, color)
    side_by_side(name, [panel(before, box, before_caption), panel(after, box, after_caption)])



if __name__ == "__main__":
    spec = json.load(open(os.path.join(H, "scripts", "figures.json")))
    for f in spec:
        figure(**f)
