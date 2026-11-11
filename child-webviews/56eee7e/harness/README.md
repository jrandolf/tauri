# Harness for the child webviews of Tauri on Linux

A small Tauri app (`app/`, a workspace member of a Tauri tree as `examples/childviews`) takes a scenario name and writes the GTK widget tree of every
window, what `Webview::bounds` says, and screenshots. `scripts/session.sh x11|wayland COMMAND` runs a command in Xvfb, or in Weston 13 nested in Xvfb so
that `xdotool` can move the pointer and turn the wheel. `scripts/run.sh SESSION VARIANT SCENARIO...` runs scenarios, `scripts/report.py` prints the tables
of `results.md`, `scripts/figures.py` builds the pictures. `explore/` holds the probes that chose the container: `containers.py` (what GTK containers do with
a webview), `frames.py` (frames until a child has the size of its room), `handler.py` (does a size request from a `size-allocate` handler hold).

The variants are Tauri trees that `scripts/sync.sh` extracts from git commits with `git archive`, and adds the app to:

| variant | what it is |
|---|---|
| `base` | upstream `dev` `66b29d1b0`, before tauri#15704 |
| `pr` | tauri#15704 as it is: its three commits on that `dev`, with the wry branch that it pins (`tauri-apps/wry` `fix/gtk-fixed-bounds`) |
| `after` | `jrandolf/tauri` `fix/linux-child-webviews` `56eee7e9f`, with `jrandolf/wry` `fix/linux-reparent-position` `b24dae77a` |
| `old` | an older branch for tauri#10420 (`f16fe7f8c`): an overlay with a box and a `gtk::Fixed` |
| `sloper` | tauri#15704 and a fix for sizes (`c5ae4bd3b`) on v2.12.5: what one downstream app pins |

The scenarios are in `app/src/main.rs` (`build` makes the windows, `drive` measures). The numbers come from Ubuntu 24.04 arm64 with GTK 3.24.41 and
WebKitGTK 2.52.6. Build with Rust 1.90, the `rust-toolchain.toml` of a Tauri tree.
