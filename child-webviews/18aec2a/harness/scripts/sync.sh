#!/usr/bin/env bash
# On the Mac: fills vendor/ from git commits (git archive, never a working tree), so that `box run`
# carries exactly what the commits hold. Each Tauri tree gets the test app as examples/childviews,
# a workspace member. Nothing else of a tree is changed, except where it says so.
#
#   base    upstream dev before #15704:                       BASE_REV  (66b29d1b0)
#   pr      #15704: its three commits (46f3a2d26, 1baf7c24e, b23bb22f0) cherry-picked onto BASE_REV, so that it
#           is compared on the same dev (the merge commit of the PR is left out); made here as the branch
#           PR_REV of the Tauri clone. Its Cargo.toml pins tauri-apps/wry fix/gtk-fixed-bounds (4d8526e)
#   after   this branch, with its own pin of the wry fork     AFTER_REV (the last commit)
#   old     the older overlay branch for #10420               OLD_REV   (f16fe7f8c), with wry
#           (its Cargo.toml has no wry pin: wry-old is patched in)  OLD_WRY_REV (4f9fb76)
#   sloper  the desktop's pin: c5ae4bd on v2.12.5             SLOPER_REV (c5ae4bd), which pins
#           jrandolf/wry sloper/v0.57.1-linux-child-bounds in its Cargo.lock
#   backport the commits of `after` on the tag tauri-v2.12.5      BACKPORT_REV (branch fix/linux-child-webviews-v2.12.5)
#   wry     the wry clone at WRY_REV, for the wry test and checks
#   wry-dev the wry commit that the branch is based on
set -euo pipefail
H=$(cd "$(dirname "$0")/.." && pwd)
TAURI=${TAURI:-/Volumes/External/Sources/tauri-child-webviews}
WRY=${WRY:-/Volumes/External/Sources/wry-child-webviews}
BASE_REV=${BASE_REV:-66b29d1b0}
PR_REV=${PR_REV:-pr-15704-on-dev}
AFTER_REV=${AFTER_REV:-fix/linux-child-webviews}
OLD_REV=${OLD_REV:-f16fe7f8c}
OLD_WRY_REV=${OLD_WRY_REV:-4f9fb76}
SLOPER_REV=${SLOPER_REV:-c5ae4bd3b81a87c3258b52031e9d6e0c8c903846}
WRY_REV=${WRY_REV:-fix/linux-reparent-position}
WRY_BASE=${WRY_BASE:-upstream/dev}
only=${*:-base pr after}

add_app() {
  local tree=$1
  mkdir -p "$tree/examples/childviews"
  rsync -a --delete "$H/app/" "$tree/examples/childviews/"
  python3 - "$tree/Cargo.toml" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
if '"examples/childviews"' not in s:
    s = s.replace('members = [\n', 'members = [\n  "examples/childviews",\n', 1)
open(p, "w").write(s)
PY
}

# the box refuses to pack what looks like a secret: the fixtures of the updater and the signer are test keys
extract() { # repo rev dest
  rm -rf "$3"
  mkdir -p "$3"
  git -C "$1" archive "$2" | tar -x -C "$3"
  rm -rf "$3/.docker" "$3/.github" "$3/audits"
  find "$3" \( -name '*.key' -o -name '*.pem' -o -name '.env*' \) -type f -delete
}

# the three commits of #15704 on BASE_REV, as the branch PR_REV of the Tauri clone, unless it is there
ensure_pr_branch() {
  git -C "$TAURI" rev-parse --verify -q "$PR_REV^{commit}" >/dev/null && return 0
  git -C "$TAURI" fetch -q upstream pull/15704/head:pr-15704
  local tree="$H/.pr-tree"
  rm -rf "$tree"
  git -C "$TAURI" worktree add -q --detach "$tree" "$BASE_REV"
  git -C "$tree" -c user.name=harness -c user.email=harness@example.invalid -c commit.gpgsign=false \
    cherry-pick 46f3a2d26d5b1a0db29b50772b0b249bf83611c8 1baf7c24e3743f69e37db6c9ccf7bb65acef0ff9 b23bb22f007a728e44cf3e8f35d193cd9b084bbb >/dev/null
  git -C "$TAURI" branch -f "$PR_REV" "$(git -C "$tree" rev-parse HEAD)"
  git -C "$TAURI" worktree remove --force "$tree"
}

for v in $only; do
  case $v in
    app) # the test app only, in the trees that are already there
      for t in base pr after old sloper backport; do [ -d "$H/vendor/$t" ] && add_app "$H/vendor/$t"; done ;;
    base) extract "$TAURI" "$BASE_REV" "$H/vendor/base"; add_app "$H/vendor/base" ;;
    pr) ensure_pr_branch; extract "$TAURI" "$PR_REV" "$H/vendor/pr"; add_app "$H/vendor/pr" ;;
    after) extract "$TAURI" "$AFTER_REV" "$H/vendor/after"; add_app "$H/vendor/after" ;;
    sloper) extract "$TAURI" "$SLOPER_REV" "$H/vendor/sloper"; add_app "$H/vendor/sloper" ;;
    backport) extract "$TAURI" "${BACKPORT_REV:-fix/linux-child-webviews-v2.12.5}" "$H/vendor/backport"; add_app "$H/vendor/backport" ;;
    old)
      extract "$TAURI" "$OLD_REV" "$H/vendor/old"
      extract "$WRY" "$OLD_WRY_REV" "$H/vendor/wry-old"
      add_app "$H/vendor/old"
      python3 - "$H/vendor/old/Cargo.toml" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
s = s.replace('[patch.crates-io]\n', '[patch.crates-io]\nwry = { path = "../wry-old" }\n', 1)
open(p, "w").write(s)
PY
      ;;
    wry) extract "$WRY" "$WRY_REV" "$H/vendor/wry" ;;
    wry-dev) extract "$WRY" "$WRY_BASE" "$H/vendor/wry-dev" ;;
  esac
done
echo "synced: $only"
for v in $only; do
  case $v in
    base) git -C "$TAURI" rev-parse --short=9 "$BASE_REV" | sed "s/^/  base   /" ;;
    pr) git -C "$TAURI" rev-parse --short=9 "$PR_REV" | sed "s/^/  pr     /" ;;
    after) git -C "$TAURI" rev-parse --short=9 "$AFTER_REV" | sed "s/^/  after  /" ;;
    sloper) git -C "$TAURI" rev-parse --short=9 "$SLOPER_REV" | sed "s/^/  sloper /" ;;
    old) git -C "$TAURI" rev-parse --short=9 "$OLD_REV" | sed "s/^/  old    /" ;;
    wry) git -C "$WRY" rev-parse --short=9 "$WRY_REV" | sed "s/^/  wry    /" ;;
  esac
done
