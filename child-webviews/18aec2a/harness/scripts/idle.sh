#!/usr/bin/env bash
# On the box: the idle scenario for every variant, one at a time, X11 and Wayland.
set -u
H=$(cd "$(dirname "$0")/.." && pwd)
cd "$H"
export CARGO_HTTP_MULTIPLEXING=false
TAIL=3 bash scripts/build.sh base pr after old sizes 2>&1 | grep -E "^==|^error|Finished"
for v in base pr old sizes after; do for s in x11 wayland; do scripts/run.sh $s $v idle; done; done
