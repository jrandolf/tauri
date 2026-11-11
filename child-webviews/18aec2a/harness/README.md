# Harness for the child webviews of Tauri on Linux

It measures what GTK does with the webviews of a Tauri window, before and after the change, on a Linux box, under X11 (Xvfb) and Wayland
(Weston 13). It was run on Ubuntu 24.04 arm64 (GTK 3.24.41, WebKitGTK 2.52.6) with Rust 1.90, on a cloud VM. A Mac made the trees (`git archive`), the
pictures and the macOS checks.

## What it tests

`app/` is a small Tauri app (`examples/childviews` of each tree, a workspace member). It takes a scenario name and writes
`out/VARIANT/SCENARIO-SESSION.{json,png,log}`. The JSON holds, per checkpoint, the GTK widget tree of every window (type, allocation, place in the
window, scroll adjustments, the title of each page, which carries its size and its clicks) and what `Webview::bounds` and `Window::inner_size`
say. The pictures are screenshots of the whole display. The feature `unstable` is on by default. `scripts/build-plain.sh` builds the app without it.

| scenario | what it builds | what it checks |
|---|---|---|
| `menu` | `WebviewWindowBuilder` 600x400 with a menu bar | problem 1 and 2 on X11; shrink and grow |
| `plain` | `WebviewWindowBuilder` 800x600 | problem 1 and 2 on Wayland; shrink and grow |
| `past` | window 800x600, a page that fills it, and a child at (40, 320) 300x400 | problem 2; a click on the child |
| `multi` | the four children of `examples/multiwebview` | problem 1 for children; grow and shrink |
| `reparent` | child at (60, 60) 240x160 in window `a`, moved to window `b` | problem 3 |
| `click` | a page and two children | each click reaches the page under the pointer |
| `bounds` | a child at (100, 100) | `set_position`, `set_size`, `set_bounds`, a window that grows |
| `menuhide` | menu bar hidden and shown, children that resize | the room changes, the window does not |
| `edge` | a child over the menu bar | a click on the menu bar is not taken by the child |
| `dnd`, `dndchild` | a file dragged from a GTK window onto the page, and onto a child | drop events |
| `latency` | six `Window::set_size` calls | milliseconds until the webview has the size of its room |
| `idle` | two webviews that auto-resize, the window resizes twice, then 5 s at rest | CPU of the app, layout passes, allocations of the room: a relayout loop shows here |
| `close` | a child is closed, the window resizes and is destroyed | no crash |

## Variants

`scripts/sync.sh` fills `vendor/` from git commits, never from a working tree. It reads the Tauri clone and the wry clone (`TAURI`, `WRY`).

| variant | commit | what it is |
|---|---|---|
| `base` | `66b29d1b0` | upstream `dev` before tauri#15704 |
| `pr` | branch `pr-15704-on-dev`, made by `sync.sh` | the three commits of #15704 (`46f3a2d26`, `1baf7c24e`, `b23bb22f0`, fetched from `refs/pull/15704/head`) cherry-picked onto `66b29d1b0`, so that it is compared on the same `dev`; its `Cargo.toml` pins `tauri-apps/wry` `fix/gtk-fixed-bounds` (`4d8526e`) |
| `after` | `69fc9c594`, branch `fix/linux-child-webviews` of `jrandolf/tauri` | this change, with `jrandolf/wry` `fix/linux-reparent-position` `b24dae77` |
| `backport` | `9341158ca`, branch `fix/linux-child-webviews-v2.12.5` | the same three commits on the tag `tauri-v2.12.5` |
| `old` | `f16fe7f8c` | an older branch for tauri#10420: an overlay with a box and a `gtk::Fixed`, with wry `4f9fb76` patched in |
| `sizes` | `c5ae4bd3b` | #15704 and a change that sizes the webviews from the room of its scrolled window, on v2.12.5 (wry `1e01aff`, Lucas's commit on the tag `wry-v0.57.1`) |

## Run it again

The scripts run on any Ubuntu 24.04 machine. `scripts/setup-box.sh` installs what the display sessions need (Xvfb, Weston 13, xdotool, ImageMagick, Pillow).
`scripts/sync.sh` runs where the two clones are (`TAURI`, `WRY`; `upstream` is the Tauri repository) and writes `vendor/`. Copy this folder, with `vendor/`, to the Linux machine
and run the rest there. The commands, with `box run` for a cloud VM that the folder is copied to before each run:

```sh
scripts/sync.sh base pr after old sizes backport wry wry-dev    # vendor/ from the commits
box run NAME -- bash scripts/setup-box.sh                        # once: packages for the display sessions
box run NAME --pull out -- bash scripts/final3.sh                # build, checks, every measurement: about 30 minutes
python3 -I scripts/report.py out > results.md                    # the tables
python3 -I scripts/report.py out -scale2 >> results.md           # scale factor 2
python3 -I scripts/figures.py figures                            # the pictures
```

Smaller steps: `scripts/build.sh VARIANT...`, then `scripts/run.sh SESSION VARIANT SCENARIO...` (SESSION is `x11` or `wayland`;
`RENDER=nodmabuf` sets `WEBKIT_DISABLE_DMABUF_RENDERER=1`, which the pictures use: with the default renderer of WebKitGTK a reparented webview draws nothing and a webview
that reaches past the edge of the window loses its top rows, in Xvfb, with every variant; `SCALE=2` sets `GDK_SCALE=2`; `BIN=plainviews` runs the build without `unstable`).
`scripts/session.sh x11|wayland COMMAND...` runs a command inside Xvfb, or inside Weston 13 nested in Xvfb so that `xdotool` input reaches it. It stops what it started, by PID.

## Other checks

- `scripts/wry-test.sh`: the wry test of `gtk::Fixed` bounds, under Xvfb and Weston, and the three mutants of wry that it must fail on.
- `scripts/mutate-test.sh`: the same for the GTK test of the webview container in `tauri-runtime-wry`.
- `scripts/wry-checks.sh` and `checks/linux-checks.sh`: wry's and Tauri's fmt, clippy and tests on Linux (`final3.sh` runs them).
- `checks/mac-checks.sh`: the macOS checks and the Windows target of `tauri-runtime-wry`, as Tauri's workflows run them. It runs on a Mac with the clone of Tauri (`HEAVY` can prefix each cargo run).
- `explore/`: the probes that chose the container: `containers.py` (GTK containers and what they do with a webview), `frames.py` (frames until a child has the size
  of its room), `handler.py` (does a size request from a `size-allocate` handler hold).
