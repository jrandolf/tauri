#!/usr/bin/env bash
# On the box: the checks of Tauri's workflows for the crates that the branch changes, on Linux, for the tree in vendor/after
# (a git archive of the branch, with the test app added as a workspace member, which these checks do not touch).
# Clippy and rustfmt are the stable ones, as lint-rust.yml and fmt.yml use; tests and checks use Rust 1.90, as test-core.yml does.
# usage: bash checks/linux-checks.sh   (from the harness folder)
set -u
H=$(cd "$(dirname "$0")/.." && pwd)
export CARGO_TARGET_DIR=$H/target-checks CARGO_HTTP_MULTIPLEXING=false
rustup toolchain install stable --profile minimal -c clippy -c rustfmt >/dev/null 2>&1
cd "$H/vendor/after"
step() {
  echo "=== $*"
  "$@" >"$H/checks.step" 2>&1
  echo "--- exit $?"
  grep -E "^(warning|error)" "$H/checks.step" | grep -v "generated\|waiting for\|missing .\[lints\]" | sort | uniq -c | sort -rn | head -12
  tail -2 "$H/checks.step"
}
step cargo +stable clippy -p tauri-runtime-wry -p tauri --all-targets --all-features -- -D warnings
step cargo +stable clippy -p tauri-runtime-wry --no-default-features -- -D warnings
step cargo +stable clippy -p tauri-runtime-wry --no-default-features --features x11 -- -D warnings
step cargo check -p tauri-runtime-wry --no-default-features
step cargo check -p tauri-runtime-wry --no-default-features --features unstable
step cargo test -p tauri-runtime-wry --no-default-features
step cargo test -p tauri-runtime-wry --all-features
echo "=== the GTK test under Xvfb and Weston"
for s in x11 wayland; do "$H/scripts/session.sh" $s cargo test -p tauri-runtime-wry --all-features -- --nocapture 2>&1 | grep -E "^test |test result: .* [1-9][0-9]* passed|skipped"; done
step cargo test -p tauri --all-features --lib
step cargo test -p tauri --no-default-features --features wry --lib
echo "=== cargo +stable fmt, of the crates that the branch changes"
cargo +stable fmt -p tauri-runtime-wry -- --check 2>&1 | grep -v "^Warning: can't set" | head -20
echo "--- exit ${PIPESTATUS[0]}"
