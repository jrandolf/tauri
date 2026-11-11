#!/usr/bin/env bash
# On the Mac: the checks of Tauri's workflows for the crates that the branch changes, on macOS, and the Windows
# target by `cargo check` and `cargo clippy` (nothing links). Each cargo run takes a slot of heavy.sh.
# Log: checks/mac-checks.log
cd /Volumes/External/Sources/tauri-child-webviews || exit 1
export CARGO_BUILD_JOBS=4 CARGO_HTTP_MULTIPLEXING=false
# HEAVY can prefix each cargo run, for example with a script that limits the runs at once
HEAVY=${HEAVY:-nice -n 19}
LOG=${CHECKS_LOG:-/tmp/mac-checks.log}
: >"$LOG"
step() {
  echo "=== $*" | tee -a "$LOG"
  "$@" >>"$LOG.step" 2>&1
  echo "--- exit $?" | tee -a "$LOG"
  grep -E "^(warning|error)" "$LOG.step" | grep -v "generated\|waiting for" | sort | uniq -c | sort -rn | head -12 >>"$LOG"
  tail -3 "$LOG.step" >>"$LOG"
  : >"$LOG.step"
}
git log --format='HEAD %h %s' -1 >>"$LOG"
step $HEAVY cargo +1.90.0 check -p tauri-runtime-wry --all-features
step $HEAVY cargo +1.90.0 check -p tauri-runtime-wry --no-default-features
step $HEAVY cargo +1.90.0 test -p tauri-runtime-wry --all-features
step $HEAVY cargo +stable clippy -p tauri-runtime-wry -p tauri --all-targets --all-features -- -D warnings
step $HEAVY cargo +nightly check -p tauri-runtime-wry --all-features --target x86_64-pc-windows-msvc
# only the nightly toolchain has the Windows target here, and its clippy has a lint (redundant_clone) that the stable one of the workflows
# does not have and that fires in crates/tauri-utils/src/acl/schema.rs, so this one names the crate and does not deny warnings
step $HEAVY cargo +nightly clippy -p tauri-runtime-wry --all-targets --all-features --target x86_64-pc-windows-msvc
grep -c "tauri-runtime-wry/src" "$LOG.step" >/dev/null 2>&1 || true
echo "=== cargo +stable fmt --all -- --check" | tee -a "$LOG"
cargo +stable fmt --all -- --check 2>&1 | grep -v "^Warning: can't set" | head -20 >>"$LOG"
echo "--- exit ${PIPESTATUS[0]}" | tee -a "$LOG"
echo "DONE" >>"$LOG"
