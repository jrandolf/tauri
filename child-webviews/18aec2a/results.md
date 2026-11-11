### Results

Ubuntu 24.04 arm64, GTK 3.24.41, WebKitGTK 2.52.6, Xvfb (X11) and Weston 13 (Wayland), `unstable` on.
Sizes and places are the GTK allocations of the webviews, in logical pixels.

#### Problem 1: the window's own webview, and its room

| | base (dev) | pr (#15704) | old (overlay branch) | sloper (desktop pin) | after (this branch) |
|---|---|---|---|---|---|
| X11, 600x400 window, menu bar | 600x375 in 600x375 | 600x400 in 600x375 | 600x375 in 600x375 | 600x375 in 600x375 | 600x375 in 600x375 |
| X11, the window shrinks to 320x240 | 320x215 in 320x215 | 320x240 in 320x215 | 320x215 in 320x215 | 320x215 in 320x215 | 320x215 in 320x215 |
| X11, the window grows to 900x700 | 900x675 in 900x675 | 900x700 in 900x675 | 900x675 in 900x675 | 900x675 in 900x675 | 900x675 in 900x675 |
| Wayland, 800x600 window | 800x600 in 800x600 | 852x689 in 800x600 | 800x600 in 800x600 | 800x600 in 800x600 | 800x600 in 800x600 |
| Wayland, the window grows to 900x700 | 900x700 in 900x700 | 952x789 in 900x700 | 900x700 in 900x700 | 900x700 in 900x700 | 900x700 in 900x700 |

#### Problem 1: children that resize with the window (the layout of `examples/multiwebview`, 800x600)

The room is 800x600 on X11 and on Wayland, so each child should be 400x300.

| | base (dev) | pr (#15704) | old (overlay branch) | sloper (desktop pin) | after (this branch) |
|---|---|---|---|---|---|
| X11, the four children | main1 800x150, main2 800x150, main3 800x150, main4 800x150 | main1 400x300, main2 400x300, main3 400x300, main4 400x300 | main1 400x300, main2 400x300, main3 400x300, main4 400x300 | main1 400x300, main2 400x300, main3 400x300, main4 400x300 | main1 400x300, main2 400x300, main3 400x300, main4 400x300 |
| Wayland, the four children | main1 800x150, main2 800x150, main3 800x150, main4 800x150 | main1 426x345, main2 426x345, main3 426x345, main4 426x345 | main1 426x345, main2 426x345, main3 426x345, main4 426x345 | main1 400x300, main2 400x300, main3 400x300, main4 400x300 | main1 400x300, main2 400x300, main3 400x300, main4 400x300 |
| Wayland, the window grows to 1000x700 | main1 1000x175, main4 1000x175 | main1 526x395, main4 526x395 | main1 526x395, main4 526x395 | main1 500x350, main4 500x350 | main1 500x350, main4 500x350 |
| Wayland, the window shrinks to 400x300 | main1 400x75, main4 400x75 | main1 226x195, main4 226x195 | main1 226x195, main4 226x195 | main1 200x150, main4 200x150 | main1 200x150, main4 200x150 |

#### Problem 2: how far five turns of the mouse wheel move the webviews

| | base (dev) | pr (#15704) | old (overlay branch) | sloper (desktop pin) | after (this branch) |
|---|---|---|---|---|---|
| X11, menu bar, the window's webview | 0 px | 25 px | 0 px | 0 px | 0 px |
| Wayland, the window's webview | 0 px | 89 px | 0 px | 0 px | 0 px |
| X11, child at (40, 320) 300x400 in an 800x600 window | 0 px | 120 px | 0 px | 120 px | 0 px |
| Wayland, the same child | 0 px | 120 px | 0 px | 120 px | 0 px |

#### Problem 3: where `Webview::reparent` puts a child that was at (60, 60)

| | base (dev) | pr (#15704) | old (overlay branch) | sloper (desktop pin) | after (this branch) |
|---|---|---|---|---|---|
| X11 | (0, 0) | (0, 0) | (60, 60) | (0, 0) | (60, 60) |
| Wayland | (0, 0) | (0, 0) | (60, 60) | (0, 0) | (60, 60) |

#### Regression: the window shrinks below the size of its webviews

The minimum is what GTK asks for. A window can shrink to it and no further.

| | base (dev) | pr (#15704) | old (overlay branch) | sloper (desktop pin) | after (this branch) |
|---|---|---|---|---|---|
| X11, 800x600 window with a 800x600 webview, set to 320x240 | window 320x240, its minimum 0x0 | window 320x240, its minimum 0x0 | window 320x240, its minimum 0x0 | window 320x240, its minimum 0x0 | window 320x240, its minimum 0x0 |
| X11, menu bar, set to 320x240 | window 320x240, its minimum 80x25 | window 320x240, its minimum 80x25 | window 320x240, its minimum 80x25 | window 320x240, its minimum 80x25 | window 320x240, its minimum 80x25 |
| Wayland, 800x600 window, set to 320x240 | window 320x240, its minimum 174x89 | window 320x240, its minimum 174x89 | window 320x240, its minimum 174x89 | window 320x240, its minimum 174x89 | window 320x240, its minimum 174x89 |

#### Placement: `set_position`, `set_size`, `set_bounds` and a window that grows (child at (100, 100) 200x150)

Each cell is what `Webview::bounds` returns. The GTK allocation of the webview is the same in each run where the layout holds.

| | base (dev) | pr (#15704) | old (overlay branch) | sloper (desktop pin) | after (this branch) |
|---|---|---|---|---|---|
| X11, `set_position` then `set_size` at once | (0, 0) 800x300 | (300, 200) 240x180 | (300, 200) 240x180 | (300, 200) 240x180 | (300, 200) 240x180 |
| X11, `set_size` then `set_position` at once | (0, 0) 800x300 | (50, 60) 150x100 | (50, 60) 150x100 | (50, 60) 150x100 | (50, 60) 150x100 |
| X11, `set_bounds` | (0, 0) 800x300 | (10, 20) 320x210 | (10, 20) 320x210 | (10, 20) 320x210 | (10, 20) 320x210 |
| X11, the window grows to 1000x700 | (0, 0) 1000x350 | (10, 20) 320x210 | (10, 20) 320x210 | (10, 20) 320x210 | (10, 20) 320x210 |
| Wayland, `set_bounds` | (0, 0) 800x300 | (10, 20) 320x210 | (10, 20) 320x210 | (10, 20) 320x210 | (10, 20) 320x210 |

#### Where GTK puts a child (child at (40, 320) 300x400 in an 800x600 window)

| | base (dev) | pr (#15704) | old (overlay branch) | sloper (desktop pin) | after (this branch) |
|---|---|---|---|---|---|
| X11 | (0, 300) 800x300 | (40, 320) 300x400 | (40, 320) 300x400 | (40, 320) 300x400 | (40, 320) 300x400 |
| Wayland | (26, 360) 800x300 | (66, 380) 300x400 | (66, 380) 300x400 | (66, 380) 300x400 | (66, 380) 300x400 |

#### What shows of that child: it reaches past the bottom edge of the window, so 280 of its 400 rows should show

The window is at the top left corner of the display on X11. These runs have `WEBKIT_DISABLE_DMABUF_RENDERER=1`: the default renderer of WebKitGTK does not draw the top rows of a webview that reaches past the edge of the window, with every variant, in Xvfb.

| | base (dev) | pr (#15704) | old (overlay branch) | sloper (desktop pin) | after (this branch) |
|---|---|---|---|---|---|
| X11, in the screenshot | 800x300 at (0, 300) | 300x280 at (40, 320) | 300x280 at (40, 320) | 300x280 at (40, 320) | 300x280 at (40, 320) |

#### Clicks: one click on each of blue, green and the window's webview (counts of clicks per page)

| | base (dev) | pr (#15704) | old (overlay branch) | sloper (desktop pin) | after (this branch) |
|---|---|---|---|---|---|
| X11 | blue 1, green 1, main 1 | blue 1, green 1, main 1 | blue 1, green 1, main 1 | blue 1, green 1, main 1 | blue 1, green 1, main 1 |
| Wayland | blue 1, green 1, main 1 | blue 1, green 1, main 1 | blue 1, green 1, main 1 | blue 1, green 1, main 1 | blue 1, green 1, main 1 |

#### Drops of a file, dragged from another window

A cell shows the drop events that each page got. Each row should show +1 for the page under the pointer. On `dev` the child is stacked below the window's webview, so the point beside the child is on the child.

| | base (dev) | pr (#15704) | old (overlay branch) | sloper (desktop pin) | after (this branch) |
|---|---|---|---|---|---|
| X11, no child, on the window's webview | main +1 | main +1 | main +0 | main +1 | main +1 |
| X11, child, on the child | child +1, main +0 | child +1, main +0 | child +1, main +0 | child +1, main +0 | child +1, main +0 |
| X11, child, on the window's webview beside the child | child +1, main +0 | child +0, main +1 | child +0, main +0 | child +0, main +1 | child +0, main +1 |
| Wayland, no child, on the window's webview | main +1 | main +1 | main +0 | main +1 | main +1 |
| Wayland, child, on the child | child +1, main +0 | child +1, main +0 | child +1, main +0 | child +1, main +0 | child +1, main +0 |
| Wayland, child, on the window's webview beside the child | child +1, main +0 | child +0, main +1 | child +0, main +0 | child +0, main +1 | child +0, main +1 |

#### Time until the window's webview has the size of its room after `Window::set_size` (X11, six sizes)

| | base (dev) | pr (#15704) | old (overlay branch) | sloper (desktop pin) | after (this branch) |
|---|---|---|---|---|---|
| milliseconds | 5/5/5/5/5/5 ms | 21/5/5/5/5/5 ms | 5/5/5/5/5/5 ms | 21/32/36/31/32/34 ms | 5/5/5/5/5/5 ms |

#### At rest for 5 s, after the window resized twice, a window with two webviews that auto-resize: CPU of the app, layout passes of GTK, and allocations of the widget that holds the webviews

| | base (dev) | pr (#15704) | old (overlay branch) | sloper (desktop pin) | after (this branch) |
|---|---|---|---|---|---|
| X11 | 0.0 % of a core, 0 layout passes, 0 allocations of the room | 0.0 % of a core, 0 layout passes, 0 allocations of the room | 0.0 % of a core, 0 layout passes, 0 allocations of the room | 2.4 % of a core, 300 layout passes, 300 allocations of the room | 0.0 % of a core, 0 layout passes, 0 allocations of the room |
| Wayland | 0.0 % of a core, 0 layout passes, 0 allocations of the room | 0.0 % of a core, 0 layout passes, 0 allocations of the room | 0.0 % of a core, 0 layout passes, 0 allocations of the room | 12.2 % of a core, 300 layout passes, 300 allocations of the room | 0.0 % of a core, 0 layout passes, 0 allocations of the room |

#### The menu bar hides and shows (X11, 800x600 window, a webview and a child that resize with it)

The webviews that resize with the window should have the size of the room. With #15704 they do not follow it.

| | base (dev) | pr (#15704) | old (overlay branch) | sloper (desktop pin) | after (this branch) |
|---|---|---|---|---|---|
| menu bar shown | room -, window's webview 800x288, half child 800x287 | room 800x575, window's webview 800x575, half child 400x288 | room 800x575, window's webview 800x575, half child 400x288 | room 800x575, window's webview 800x551, half child 400x276 | room 800x575, window's webview 800x575, half child 400x288 |
| menu bar hidden: the room is 25 px higher, the window is the same | room -, window's webview 800x300, half child 800x300 | room 800x600, window's webview 800x575, half child 400x288 | room 800x600, window's webview 800x575, half child 400x288 | room 800x600, window's webview 800x575, half child 400x288 | room 800x600, window's webview 800x600, half child 400x301 |
| menu bar shown again | room -, window's webview 800x288, half child 800x287 | room 800x575, window's webview 800x575, half child 400x288 | room 800x575, window's webview 800x575, half child 400x288 | room 800x575, window's webview 800x551, half child 400x276 | room 800x575, window's webview 800x575, half child 400x288 |

#### A child that reaches over the menu bar (child at (5, -60) 100x200): a click on the menu bar

| | base (dev) | pr (#15704) | old (overlay branch) | sloper (desktop pin) | after (this branch) |
|---|---|---|---|---|---|
| X11 | menu opened, child got 0 clicks | menu opened, child got 0 clicks | menu opened, child got 0 clicks | menu opened, child got 0 clicks | menu opened, child got 0 clicks |
| Wayland | menu opened, child got 0 clicks | menu did not open, child got 1 click | menu did not open, child got 1 click | menu opened, child got 0 clicks | menu opened, child got 0 clicks |

#### The backport on v2.12.5 gives the same numbers as the branch on `dev`

| scenario | X11 | Wayland |
|---|---|---|
| menu | same, 4 checkpoints | same, 4 checkpoints |
| plain | same, 4 checkpoints | same, 4 checkpoints |
| past | same, 3 checkpoints | same, 3 checkpoints |
| multi | same, 3 checkpoints | same, 3 checkpoints |
| reparent | same, 3 checkpoints | same, 3 checkpoints |
| bounds | same, 5 checkpoints | same, 5 checkpoints |

### Results with a scale factor of 2


#### Scale factor 2 (`GDK_SCALE=2`, X11): the same sizes, in logical pixels

| | base (dev) | pr (#15704) | old (overlay branch) | sloper (desktop pin) | after (this branch) |
|---|---|---|---|---|---|
| the window's webview, 600x400 window, menu bar | - | 600x400 in 600x375 | - | - | 600x375 in 600x375 |
| the window's webview, the window grows to 900x700 | - | 900x700 in 900x675 | - | - | 900x675 in 900x675 |
| the four children of `examples/multiwebview` | - | main1 400x300, main4 400x300 | - | - | main1 400x300, main4 400x300 |
| five turns of the wheel over the window's webview, menu bar | - | 25 px | - | - | 0 px |
| five turns of the wheel, child at (40, 320) 300x400 | - | 120 px | - | - | 0 px |
| `Webview::reparent` of the child that was at (60, 60) | - | (0, 0) | - | - | (60, 60) |
