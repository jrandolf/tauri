Pictures and numbers for a Tauri pull request: child webviews on Linux, in a container that clips and gives them their room.

- Tauri branch: `fix/linux-child-webviews` (`56eee7e9f`), on `dev` `66b29d1b0`.
- wry branch: `fix/linux-reparent-position` (`b24dae77a`), on wry `dev` `8d287db`.
- Before: tauri-apps/tauri#15704 as it is (its three commits on the same `dev`, with the wry branch that it pins).
- System: Ubuntu 24.04 arm64, GTK 3.24.41, WebKitGTK 2.52.6, `unstable` on. X11 is Xvfb. Wayland is Weston 13 (the `x11` backend, in Xvfb, so
  that `xdotool` can move the pointer and turn the wheel).
- The pictures use `WEBKIT_DISABLE_DMABUF_RENDERER=1`. With the default renderer of WebKitGTK, a reparented webview draws nothing and a webview that
  reaches past the edge of the window loses its top rows, in Xvfb, with or without the change. The numbers do not depend on the renderer.

| picture | what it shows |
|---|---|
| `p1-menu-bar.png` | The window's webview in a 600x400 window with a menu bar (X11): 600x400 in a room of 600x375, then 600x375. |
| `p2-menu-bar-wheel.png` | After five turns of the mouse wheel: the webviews moved up 25 px, then nothing moved. |
| `p3-child-past-bottom-wheel.png` | A child at (40, 320) 300x400 in an 800x600 window, after five turns of the wheel: up 120 px, then clipped and still. |
| `p4-wayland-window-webview.png` | The window's webview in an 800x600 window on Wayland: 852x689 in a room of 800x600, then 800x600. |
| `p5-wayland-multiwebview.png` | The four children of `examples/multiwebview` on Wayland: 426x345 each, then 400x300. |
| `p6-reparent.png` | `Webview::reparent` of a child that was at (60, 60): it is at (0, 0) in the new window, then at (60, 60). |

`results.md` has every number: the three problems, and the regressions I looked for (the window shrinks, `set_bounds` holds, clicks, file drops,
the time to the size of the room, a relayout loop at rest, scale factor 2).

`harness/` has the test app (`app/`), the scripts that build and run it under Xvfb and Weston (`scripts/`), and the probes of GTK containers
(`explore/`). `harness/README.md` says how to run them.
