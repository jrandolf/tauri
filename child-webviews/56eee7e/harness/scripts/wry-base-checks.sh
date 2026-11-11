#!/usr/bin/env bash
# On the box: the same clippy on a clean copy of the wry commit that the branch is based on.
set -u
H=$(cd "$(dirname "$0")/.." && pwd)
export CARGO_TARGET_DIR=$H/target-wry CARGO_HTTP_MULTIPLEXING=false
cd "$H/vendor/wry-dev"
cargo clippy --lib --tests --examples --features linux-body -- -D warnings 2>&1 | grep -E "^(warning|error)" -A4 | grep -v "v2_42" | head -40
echo "exit ${PIPESTATUS[0]}"
