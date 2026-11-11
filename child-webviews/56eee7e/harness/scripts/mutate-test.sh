#!/usr/bin/env bash
# On the box: shows that the GTK test of the webview container fails without each part of the fix.
# It edits a copy of vendor/after and runs the test under Xvfb. Run `scripts/sync.sh after` to undo.
set -u
H=$(cd "$(dirname "$0")/.." && pwd)
export CARGO_TARGET_DIR=$H/target-mutants CARGO_HTTP_MULTIPLEXING=false
rm -rf "$H/vendor/mutant" && cp -r "$H/vendor/after" "$H/vendor/mutant"
file=$H/vendor/mutant/crates/tauri-runtime-wry/src/window/linux.rs
run() {
  echo "== $1"
  (cd "$H/vendor/mutant" && "$H/scripts/session.sh" x11 cargo test -p tauri-runtime-wry --all-features 2>&1 |
    grep -E "^test |panicked|assertion|left:|right:|^error" | head -8)
}
run "unchanged"
# 1. the container asks for the room of its webviews, as a gtk::Fixed does
python3 - "$file" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
s = s.replace("""    fn preferred_width(&self) -> (i32, i32) {
      (0, 0)
    }

    fn preferred_height(&self) -> (i32, i32) {
      (0, 0)
    }
""", "")
open(p, "w").write(s)
PY
run "without the zero size request (window cannot shrink)"
cp "$H/vendor/after/crates/tauri-runtime-wry/src/window/linux.rs" "$file"
# 2. the room reaches the webviews one frame later, as from an idle callback
python3 - "$file" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
s = s.replace("""        on_room(room);
      }
      self.parent_size_allocate(allocation);""", """        let on_room = self.obj().clone();
        gtk::glib::idle_add_local_once(move || {
          if let Some(on_room) = &*on_room.imp().on_room.borrow() {
            on_room(room);
          }
        });
      }
      self.parent_size_allocate(allocation);""")
open(p, "w").write(s)
PY
run "with the room one frame late (idle callback)"
