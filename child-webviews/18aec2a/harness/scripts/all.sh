#!/usr/bin/env bash
# On the box: every scenario of a variant under X11 and Wayland, default renderer and without DMABUF.
# usage: scripts/all.sh VARIANT [SCENARIO...]
H=$(cd "$(dirname "$0")/.." && pwd)
variant=$1
shift
scenarios=${*:-menu plain past multi reparent}
for render in default nodmabuf; do
  for session in x11 wayland; do
    RENDER=$render "$H/scripts/run.sh" $session "$variant" $scenarios
  done
done
