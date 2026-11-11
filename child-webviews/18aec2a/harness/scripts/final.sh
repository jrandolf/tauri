#!/usr/bin/env bash
# On the box: what is left after scripts/matrix.sh: the app rebuilt, the click scenario again, the default build (no
# `unstable`), the backport on v2.12.5, the frame probes, and the Linux checks.
set -u
H=$(cd "$(dirname "$0")/.." && pwd)
cd "$H"
export CARGO_HTTP_MULTIPLEXING=false
echo "== build"; TAIL=3 bash scripts/build.sh base pr after old sloper backport 2>&1 | grep -E "^==|^error|Finished"
echo "== build without unstable"; bash scripts/build-plain.sh base after 2>&1 | grep -E "^==|^error|Finished"
echo "== click again"
for v in base pr old sloper after; do for s in x11 wayland; do scripts/run.sh $s $v click; done; done
for v in pr after; do for s in x11 wayland; do RENDER=nodmabuf scripts/run.sh $s $v click; done; done
echo "== backport on v2.12.5"
for s in x11 wayland; do scripts/run.sh $s backport menu plain past multi reparent bounds; done
echo "== default build, no unstable"
for v in base after; do for s in x11 wayland; do BIN=plainviews scripts/run.sh $s $v menu plain latency; done; done
echo "== frames until a child has the size of its room"
for m in packed layout-idle layout-direct fixed-handler subclass; do
  scripts/session.sh x11 python3 explore/frames.py $m 2>&1 | grep -E "^$m"
done
echo "== linux checks"
bash checks/linux-checks.sh 2>&1
