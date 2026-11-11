# Tests that fail without the fix

Each test was run on the final commit, and then with one part of the fix taken out. A test that does not fail without its fix is not a test of it.
The runs are under Xvfb (X11) and Weston 13 (Wayland), Ubuntu 24.04 arm64, GTK 3.24.41. The tests need a display and do nothing without one.

## wry, `webview_in_a_gtk_fixed_keeps_its_bounds` (`jrandolf/wry` `b24dae77a`)

`harness/scripts/wry-test.sh`. The four changes: `set_bounds` with `size_allocate` only (before fix 1), `reparent` to (0, 0) (before fix 3), a flag that is set when the
webview is created in a `gtk::Fixed` (before fix 3), and the check for the exact type name `GtkFixed` (before fix 4).

```
== wry test and its mutants
== all fixes
-- x11
test webkitgtk::tests::webview_in_a_gtk_fixed_keeps_its_bounds ... ok
test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 8 filtered out; finished in 1.61s
-- wayland
test webkitgtk::tests::webview_in_a_gtk_fixed_keeps_its_bounds ... ok
test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 8 filtered out; finished in 1.74s
-- without a display
test webkitgtk::tests::webview_in_a_gtk_fixed_keeps_its_bounds ... ok
test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 8 filtered out; finished in 0.00s
== set_bounds with size_allocate only
-- x11
test webkitgtk::tests::webview_in_a_gtk_fixed_keeps_its_bounds ... FAILED
thread 'webkitgtk::tests::webview_in_a_gtk_fixed_keeps_its_bounds' panicked at src/webkitgtk/mod.rs:1484:5:
  left: (10, 20, 300, 200)
 right: (40, 50, 120, 90)
test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 8 filtered out; finished in 0.39s
-- wayland
test webkitgtk::tests::webview_in_a_gtk_fixed_keeps_its_bounds ... FAILED
thread 'webkitgtk::tests::webview_in_a_gtk_fixed_keeps_its_bounds' panicked at src/webkitgtk/mod.rs:1484:5:
  left: (10, 20, 300, 200)
 right: (40, 50, 120, 90)
test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 8 filtered out; finished in 0.43s
== reparent to (0, 0)
-- x11
test webkitgtk::tests::webview_in_a_gtk_fixed_keeps_its_bounds ... FAILED
thread 'webkitgtk::tests::webview_in_a_gtk_fixed_keeps_its_bounds' panicked at src/webkitgtk/mod.rs:1491:5:
  left: (0, 0, 120, 90)
 right: (40, 50, 120, 90)
test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 8 filtered out; finished in 0.70s
-- wayland
test webkitgtk::tests::webview_in_a_gtk_fixed_keeps_its_bounds ... FAILED
thread 'webkitgtk::tests::webview_in_a_gtk_fixed_keeps_its_bounds' panicked at src/webkitgtk/mod.rs:1491:5:
  left: (0, 0, 120, 90)
 right: (40, 50, 120, 90)
test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 8 filtered out; finished in 0.73s
== flag set at creation
-- x11
test webkitgtk::tests::webview_in_a_gtk_fixed_keeps_its_bounds ... FAILED
thread 'webkitgtk::tests::webview_in_a_gtk_fixed_keeps_its_bounds' panicked at src/webkitgtk/mod.rs:1501:5:
  left: (0, 0, 0, 0)
 right: (5, 6, 70, 80)
test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 8 filtered out; finished in 1.00s
-- wayland
test webkitgtk::tests::webview_in_a_gtk_fixed_keeps_its_bounds ... FAILED
thread 'webkitgtk::tests::webview_in_a_gtk_fixed_keeps_its_bounds' panicked at src/webkitgtk/mod.rs:1501:5:
  left: (0, 0, 0, 0)
 right: (5, 6, 70, 80)
test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 8 filtered out; finished in 1.07s
== exact type name GtkFixed
-- x11
test webkitgtk::tests::webview_in_a_gtk_fixed_keeps_its_bounds ... FAILED
thread 'webkitgtk::tests::webview_in_a_gtk_fixed_keeps_its_bounds' panicked at src/webkitgtk/mod.rs:1510:5:
  left: (0, 0, 0, 0)
 right: (10, 20, 300, 200)
test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 8 filtered out; finished in 1.31s
-- wayland
test webkitgtk::tests::webview_in_a_gtk_fixed_keeps_its_bounds ... FAILED
thread 'webkitgtk::tests::webview_in_a_gtk_fixed_keeps_its_bounds' panicked at src/webkitgtk/mod.rs:1510:5:
  left: (0, 0, 0, 0)
 right: (10, 20, 300, 200)
test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 8 filtered out; finished in 1.41s
```

## tauri-runtime-wry, `container_asks_for_no_room_and_gives_its_webviews_the_room_in_one_layout_pass` (`18aec2a65`)

`harness/scripts/mutate-test.sh`. The two changes: no zero size request in the container (the window cannot shrink below its webview), and the room that
reaches the webviews from an idle callback (one frame late).

```
== unchanged
test window::linux::tests::container_asks_for_no_room_and_gives_its_webviews_the_room_in_one_layout_pass ... ok
test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.65s
test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
== without the zero size request (window cannot shrink)
test window::linux::tests::container_asks_for_no_room_and_gives_its_webviews_the_room_in_one_layout_pass ... FAILED
thread 'window::linux::tests::container_asks_for_no_room_and_gives_its_webviews_the_room_in_one_layout_pass' panicked at crates/tauri-runtime-wry/src/window/linux.rs:195:
assertion `left == right` failed
  left: (800, 600)
 right: (300, 200)
test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.35s
error: test failed, to rerun pass `-p tauri-runtime-wry --lib`
== with the room one frame late (idle callback)
test window::linux::tests::container_asks_for_no_room_and_gives_its_webviews_the_room_in_one_layout_pass ... FAILED
thread 'window::linux::tests::container_asks_for_no_room_and_gives_its_webviews_the_room_in_one_layout_pass' panicked at crates/tauri-runtime-wry/src/window/linux.rs:228:
assertion `left == right` failed
  left: (300, 200)
 right: (500, 400)
test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.65s
error: test failed, to rerun pass `-p tauri-runtime-wry --lib`
```
