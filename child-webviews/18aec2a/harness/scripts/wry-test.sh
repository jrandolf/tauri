#!/usr/bin/env bash
# On the box: the wry test of the gtk::Fixed bounds, and that it fails without each of the fixes.
# Without a display it does nothing, so each run is under Xvfb and under Weston.
set -u
H=$(cd "$(dirname "$0")/.." && pwd)
export CARGO_TARGET_DIR=$H/target-wry CARGO_HTTP_MULTIPLEXING=false
cd "$H/vendor/wry"
run() {
  echo "== $1"
  for session in x11 wayland; do
    echo "-- $session"
    "$H/scripts/session.sh" $session cargo test --features linux-body --lib webkitgtk 2>&1 |
      grep -E "^test |panicked|assertion|left:|right:|^error|test result" | head -8
  done
}
run "all fixes"
echo "-- without a display"
(unset DISPLAY WAYLAND_DISPLAY; cargo test --features linux-body --lib webkitgtk 2>&1 | grep -E "^test |test result")
cp src/webkitgtk/mod.rs /tmp/wry-mod.orig
mutant() {
  cp /tmp/wry-mod.orig src/webkitgtk/mod.rs
  python3 - "$1" "$2" "$3" <<'PY'
import sys
p = "src/webkitgtk/mod.rs"
s = open(p).read()
old, new = sys.argv[2], sys.argv[3]
assert old in s, old
open(p, "w").write(s.replace(old, new, 1))
PY
  run "$1"
}
# 1. set_bounds only allocates the webview, as before the fix
mutant "set_bounds with size_allocate only" \
  "      self.webview.set_size_request(width, height);
      fixed.move_(&self.webview, x, y);" \
  "      let _ = &fixed;
      self.webview.size_allocate(&gtk::Allocation::new(x, y, width, height));"
# 2. reparent puts the webview at (0, 0)
mutant "reparent to (0, 0)" ".put(&self.webview, x, y);" ".put(&self.webview, 0, 0);"
# 3. a flag that is set when the webview is created in a gtk::Fixed, as before the fixes
cp /tmp/wry-mod.orig src/webkitgtk/mod.rs
python3 - <<'PY'
p = "src/webkitgtk/mod.rs"
s = open(p).read()
s = s.replace("      fixed.put(webview, x, y);\n    } else {", "      fixed.put(webview, x, y);\n      unsafe { webview.set_data(\"in-fixed\", true) };\n    } else {", 1)
s = s.replace("    if let Some(fixed) = self.fixed_parent() {\n      // let the GtkFixed lay", "    if let (Some(fixed), Some(_)) = (self.fixed_parent(), unsafe { self.webview.data::<bool>(\"in-fixed\") }) {\n      // let the GtkFixed lay", 1)
open(p, "w").write(s)
PY
run "flag set at creation"
# 4. the exact type name
mutant "exact type name GtkFixed" \
  "    } else if let Some(fixed) = container.dynamic_cast_ref::<gtk::Fixed>() {
      let scale_factor" \
  "    } else if let (true, Some(fixed)) = (container.type_().name() == \"GtkFixed\", container.dynamic_cast_ref::<gtk::Fixed>()) {
      let scale_factor"
cp /tmp/wry-mod.orig src/webkitgtk/mod.rs
