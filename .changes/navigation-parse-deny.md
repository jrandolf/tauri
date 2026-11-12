---
"tauri-runtime-wry": patch:bug
---

A navigation to an address that does not parse as a URL is refused. It was allowed before, and the navigation handler was not called.
