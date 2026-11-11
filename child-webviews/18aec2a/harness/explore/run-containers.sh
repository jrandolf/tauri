#!/usr/bin/env bash
# usage: run-containers.sh SESSION [VARIANT...]  (SESSION: x11 | wayland)
set -u
cd "$(dirname "$0")/.."
session=$1
shift
variants=${*:-scrolled-fixed fixed layout-fixed layout}
export OUT=$PWD/out/containers
mkdir -p "$OUT"
for variant in $variants; do
  for scenario in menu past shrink negative; do
    timeout 120 scripts/session.sh "$session" python3 explore/containers.py "$variant" "$scenario" 2>&1 | grep -v -E "^(Gtk-WARNING|libEGL|MESA|\(.*\): (Gtk|GLib|WebKit)-)" | tee -a "$OUT/containers-$session.jsonl"
  done
done
