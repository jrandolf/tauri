#!/usr/bin/env bash
# On the box, after scripts/final3.sh: what shows of the clipped child for every variant (without DMABUF), and the wry test with its mutants.
set -u
H=$(cd "$(dirname "$0")/.." && pwd)
cd "$H"
export CARGO_HTTP_MULTIPLEXING=false
echo "== past, without DMABUF, every variant"
for v in base pr old sizes after; do RENDER=nodmabuf scripts/run.sh x11 $v past; done
echo "== wry test and its mutants"
bash scripts/wry-test.sh 2>&1 | grep -E "^==|^-- |^test |test result|panicked|left:|right:"
echo "== done"
