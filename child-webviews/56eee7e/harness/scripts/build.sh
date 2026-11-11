#!/usr/bin/env bash
# On the box: builds the test app of each variant into bin/childviews-VARIANT.
set -euo pipefail
H=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$H/bin"
export CARGO_TARGET_DIR=$H/target
export CARGO_TERM_COLOR=never
for v in ${*:-base pr after}; do
  echo "== build $v"
  (cd "$H/vendor/$v" && cargo build -p childviews 2>&1 | tail -${TAIL:-40})
  cp "$CARGO_TARGET_DIR/debug/childviews" "$H/bin/childviews-$v"
done
