#!/usr/bin/env bash
# On the box: the test app without the `unstable` feature, as the default build of a Tauri app, into bin/plainviews-VARIANT.
set -euo pipefail
H=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$H/bin"
export CARGO_TARGET_DIR=$H/target-plain CARGO_TERM_COLOR=never CARGO_HTTP_MULTIPLEXING=false
for v in ${*:-base after}; do
  echo "== build $v without unstable"
  (cd "$H/vendor/$v" && cargo build -p childviews --no-default-features 2>&1 | grep -E "^error|Finished" -A8 | head -40)
  cp "$CARGO_TARGET_DIR/debug/childviews" "$H/bin/plainviews-$v"
done
