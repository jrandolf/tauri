#!/usr/bin/env bash
# On the box: scripts/run.sh SESSION VARIANT SCENARIO...   (SESSION: x11 | wayland)
#   RENDER=default (WebKit's default renderer) | nodmabuf (WEBKIT_DISABLE_DMABUF_RENDERER=1)
#   SCALE=2 sets GDK_SCALE=2 (X11 only)
#   BIN=plainviews runs the app built without the `unstable` feature (scripts/build-plain.sh); its results go to out/plain-VARIANT
# Results: out/VARIANT[-RENDER][-scale2]/SCENARIO-SESSION.{json,png,log}
set -u
H=$(cd "$(dirname "$0")/.." && pwd)
session=$1
variant=$2
shift 2
render=${RENDER:-default}
case $render in
  nodmabuf) export WEBKIT_DISABLE_DMABUF_RENDERER=1 ;;
  default) unset WEBKIT_DISABLE_DMABUF_RENDERER WEBKIT_DISABLE_COMPOSITING_MODE ;;
esac
suffix=""
[ "$render" != default ] && suffix="-$render"
if [ "${SCALE:-1}" != 1 ]; then
  export GDK_SCALE=$SCALE
  suffix="$suffix-scale$SCALE"
fi
bin=${BIN:-childviews}
prefix=""
[ "$bin" = plainviews ] && prefix="plain-"
export OUT=$H/out/$prefix$variant$suffix
export FINDBOX=$H/scripts/findbox.py
export DRAGSOURCE=$H/scripts/dragsource.py
mkdir -p "$OUT"
for scenario in "$@"; do
  echo "== $variant$suffix $session $scenario"
  timeout 150 "$H/scripts/session.sh" "$session" "$H/bin/$bin-$variant" "$scenario" >"$OUT/$scenario-$session.log" 2>&1
  code=$?
  # what GTK or the app complained about, apart from the noise of a headless session
  grep -E "panicked|CRITICAL|WARNING|watchdog|error" "$OUT/$scenario-$session.log" |
    grep -v -E "libEGL|MESA|dconf|GLib-GIO|libdecor|Fontconfig|Unable to load dnd" | sort | uniq -c | head -6
  echo "   exit $code"
done
