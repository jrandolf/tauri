#!/usr/bin/env bash
# On the box: wry's own checks (its clippy-fmt and test workflows) on Linux for the wry commit in vendor/wry,
# and the same clippy on vendor/wry-dev (the commit that the branch is based on), to tell what is new.
# `cargo clippy --all-targets` does not compile on dev either: the gtk_opengl example does not build here,
# so the examples that build are named.
set -u
H=$(cd "$(dirname "$0")/.." && pwd)
export CARGO_TARGET_DIR=$H/target-wry CARGO_HTTP_MULTIPLEXING=false
rustup toolchain install stable --profile minimal -c clippy -c rustfmt >/dev/null 2>&1
clippy() {
  (cd "$H/vendor/$1" && cargo +stable clippy --lib --tests --example gtk_multiwebview --example reparent --example simple --example multiwebview 2>&1 |
    grep -E "^(warning|error)" | grep -v "generated\|waiting for" | sort | uniq -c | sort -rn)
}
echo "== cargo +stable fmt --all -- --check"
(cd "$H/vendor/wry" && cargo +stable fmt --all -- --check 2>&1 | grep -v "^Warning: can't set" | head -20; echo "exit ${PIPESTATUS[0]}")
echo "== clippy, the branch"
clippy wry
echo "== clippy, upstream dev"
clippy wry-dev
cd "$H/vendor/wry"
step() {
  echo "=== $*"
  "$@" >"$H/wry-step.log" 2>&1
  echo "--- exit $?"
  grep -E "^(error)|test result|panicked" "$H/wry-step.log" | head -8
}
# build.yml: the two feature sets, on Linux
step cargo build --no-default-features --features os-webview
step cargo build --all-features --lib
step cargo test --lib --features linux-body --no-default-features --features os-webview
step cargo test --lib --features linux-body --all-features
echo "=== the test of the bounds, under Xvfb and Weston"
for s in x11 wayland; do "$H/scripts/session.sh" $s cargo test --lib --features linux-body webkitgtk 2>&1 | grep -E "^test |test result: .* [1-9][0-9]* passed"; done
