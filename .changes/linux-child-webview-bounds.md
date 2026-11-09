---
"tauri-runtime-wry": patch:bug
---

On Linux, child webviews added with `Window::add_child` are placed at their bounds over the window's webview, instead of being packed into the window's box below it.
