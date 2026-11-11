#!/usr/bin/env bash
# On the box, the last session: everything that depends on the final commits.
#   checks   wry's and Tauri's checks on Linux
#   matrix   every scenario for `after`, X11 and Wayland, both renderers, and scale 2
#   timing   idle and latency, one at a time
#   plain    the default build (no `unstable`), base and after
#   headless the sizes under Weston with its headless backend
#   backport the backport on v2.12.5
set -u
H=$(cd "$(dirname "$0")/.." && pwd)
cd "$H"
export CARGO_HTTP_MULTIPLEXING=false
echo "== build"; TAIL=3 bash scripts/build.sh base pr after old sizes backport 2>&1 | grep -E "^==|^error|Finished"
echo "== build without unstable"; bash scripts/build-plain.sh base after 2>&1 | grep -E "^==|^error|Finished"
echo "== wry checks"; bash scripts/wry-checks.sh 2>&1
echo "== tauri checks"; bash checks/linux-checks.sh 2>&1
echo "== matrix for after"
SCENARIOS="menu plain past multi reparent click bounds menuhide edge dnd dndchild close"
rm -rf out/after out/after-nodmabuf out/after-scale2
mkdir -p out
( for s in x11 wayland; do RENDER=default scripts/run.sh $s after $SCENARIOS; done ) >out/stream-after.log 2>&1 &
sleep 4
( for s in x11 wayland; do RENDER=nodmabuf scripts/run.sh $s after $SCENARIOS; done ) >out/stream-after-nodmabuf.log 2>&1 &
wait
SCALE=2 scripts/run.sh x11 after menu plain past multi reparent >out/stream-scale2-after.log 2>&1
echo "== timing: idle and latency, one at a time"
for v in base pr old sizes after; do scripts/run.sh x11 $v idle latency; done
echo "== default build, no unstable"
for v in base after; do for s in x11 wayland; do BIN=plainviews scripts/run.sh $s $v menu plain latency; done; done
echo "== sizes under headless Weston"
for v in pr after; do scripts/run.sh wayland-headless $v plain multi; done
echo "== backport on v2.12.5"
for s in x11 wayland; do scripts/run.sh $s backport menu plain past multi reparent bounds; done
echo "== done"
