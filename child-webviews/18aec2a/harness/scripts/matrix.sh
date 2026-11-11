#!/usr/bin/env bash
# On the box: every measurement of the pull request, from the binaries in bin/.
#   stage 1: the scenarios that do not time anything, four variants at once
#   stage 2: latency and idle, one at a time, so that they time the app and not the box
#   stage 3: GDK_SCALE=2 on X11
# usage: bash scripts/matrix.sh
set -u
H=$(cd "$(dirname "$0")/.." && pwd)
cd "$H"
SCENARIOS="menu plain past multi reparent click bounds menuhide edge dnd dndchild close"
rm -rf out
mkdir -p out
echo "stage 1 $(date -u +%T)"
stream() { # variant renders...
  local v=$1
  shift
  for render in "$@"; do
    for session in x11 wayland; do
      RENDER=$render scripts/run.sh $session $v $SCENARIOS
    done
  done
}
stream after default nodmabuf >out/stream-after.log 2>&1 &
sleep 4
stream pr default nodmabuf >out/stream-pr.log 2>&1 &
sleep 4
stream base default >out/stream-base.log 2>&1 &
sleep 4
{ stream old default; stream sizes default; } >out/stream-old-sizes.log 2>&1 &
wait
echo "stage 2 $(date -u +%T)"
for v in base pr old sizes after; do
  scripts/run.sh x11 $v latency idle >>out/stream-timing.log 2>&1
done
echo "stage 3 $(date -u +%T)"
for v in pr after; do
  SCALE=2 scripts/run.sh x11 $v menu plain past multi reparent >>out/stream-scale2.log 2>&1
done
echo "done $(date -u +%T)"
