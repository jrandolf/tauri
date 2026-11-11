// A small Tauri app that builds the window layouts of tauri#15704's problems, measures what GTK gives
// each webview, and writes the numbers and screenshots to $OUT. Linux only. Run it inside
// scripts/session.sh (Xvfb or Weston) with the scenario name as the argument.

use std::{
  fs,
  path::{Path, PathBuf},
  process::Command,
  sync::{
    Arc, Mutex,
    atomic::{AtomicUsize, Ordering},
    mpsc,
  },
  thread,
  time::Duration,
};

#[cfg(feature = "unstable")]
use tauri::webview::WebviewBuilder;
use gtk::prelude::*;
use serde_json::{Value, json};
use tauri::{
  AppHandle, DragDropEvent, LogicalPosition, LogicalSize, Manager, WebviewEvent, WebviewUrl,
  WebviewWindowBuilder,
  menu::{Menu, MenuItem, Submenu},
};
#[cfg(feature = "unstable")]
use tauri::window::WindowBuilder;

// The border color of each page: `findbox.py` finds the page in a screenshot by it.
static DROPS: Mutex<Vec<(String, Arc<AtomicUsize>)>> = Mutex::new(Vec::new());

fn count_drops(webview: &tauri::Webview) {
  let counter = Arc::new(AtomicUsize::new(0));
  DROPS
    .lock()
    .unwrap()
    .push((webview.label().to_string(), counter.clone()));
  webview.on_webview_event(move |event| {
    if let WebviewEvent::DragDrop(DragDropEvent::Drop { .. }) = event {
      counter.fetch_add(1, Ordering::SeqCst);
    }
  });
}

fn drops() -> Value {
  let mut m = serde_json::Map::new();
  for (label, n) in DROPS.lock().unwrap().iter() {
    m.insert(label.clone(), json!(n.load(Ordering::SeqCst)));
  }
  Value::Object(m)
}

const MAIN: &str = "d946ef";
const SOURCE: &str = "ff0000";
const BLUE: &str = "2563eb";
const GREEN: &str = "16a34a";
const ORANGE: &str = "d97706";
const PURPLE: &str = "9333ea";

fn page(name: &str, color: &str, fill: &str) -> WebviewUrl {
  let html = format!(
    r#"<!doctype html><meta charset=utf-8><style>
html,body{{margin:0;height:100%}}
body{{box-sizing:border-box;border:3px solid #{color};background:#{fill};color:#fff;font:14px sans-serif;
background-image:linear-gradient(#0001 1px,transparent 1px),linear-gradient(90deg,#0001 1px,transparent 1px);
background-size:50px 50px}}
#t{{position:fixed;right:8px;bottom:8px;background:#111;padding:4px 8px;border-radius:4px}}
#n{{position:fixed;left:10px;top:8px;color:#222;font-weight:bold}}
</style><body><div id=n>{name}</div><div id=t></div><script>
var c=0;function f(){{var s=innerWidth+'x'+innerHeight;document.getElementById('t').textContent=s;document.title='{name} '+s+' clicks='+c}}
f();addEventListener('resize',f);addEventListener('click',function(){{c++;f()}})</script>"#
  );
  WebviewUrl::External(
    format!(
      "data:text/html;charset=utf-8,{}",
      urlencoding::encode(&html)
    )
    .parse()
    .unwrap(),
  )
}

fn main_page(name: &str) -> WebviewUrl {
  page(name, MAIN, "e8eef7")
}

fn solid(name: &str, color: &str) -> WebviewUrl {
  page(name, color, color)
}

fn menu(app: &AppHandle) -> tauri::Result<Menu<tauri::Wry>> {
  let item = MenuItem::with_id(app, "noop", "Noop", true, None::<&str>)?;
  let file = Submenu::with_items(app, "File", true, &[&item])?;
  let edit = Submenu::with_items(app, "Edit", true, &[&item])?;
  Menu::with_items(app, &[&file, &edit])
}

fn widget_tree(widget: &gtk::Widget, top: &gtk::Widget, depth: usize, out: &mut Vec<Value>) {
  let a = widget.allocation();
  let mut v = json!({
    "type": widget.type_().name(),
    "depth": depth,
    "alloc": [a.x(), a.y(), a.width(), a.height()],
    "in_toplevel": widget.translate_coordinates(top, 0, 0).map(|(x, y)| [x, y]),
    "mapped": widget.is_mapped(),
  });
  if let Some(sw) = widget.downcast_ref::<gtk::ScrolledWindow>() {
    let (vadj, hadj) = (sw.vadjustment(), sw.hadjustment());
    v["scroll"] = json!({
      "v": [vadj.value(), vadj.upper(), vadj.page_size()],
      "h": [hadj.value(), hadj.upper(), hadj.page_size()],
    });
  }
  if let Some(wv) = widget.downcast_ref::<webkit2gtk::WebView>() {
    use webkit2gtk::WebViewExt;
    v["title"] = json!(wv.title().map(|t| t.to_string()));
    v["size_request"] = json!(widget.size_request());
  }
  out.push(v);
  if let Some(c) = widget.downcast_ref::<gtk::Container>() {
    for child in c.children() {
      widget_tree(&child, top, depth + 1, out);
    }
  }
}

fn dump_gtk() -> Value {
  let mut windows = vec![];
  for top in gtk::Window::list_toplevels() {
    let Ok(win) = top.downcast::<gtk::Window>() else {
      continue;
    };
    if !win.is_visible() {
      continue;
    }
    let mut tree = vec![];
    widget_tree(win.upcast_ref(), win.upcast_ref(), 0, &mut tree);
    let (w, h) = win.size();
    let min = win.preferred_size().0;
    windows.push(json!({
      "title": win.title().map(|t| t.to_string()),
      "size": [w, h],
      "min_size": [min.width, min.height],
      "tree": tree,
    }));
  }
  json!(windows)
}

/// The room of the first webview in the first window, and whether the webview has its size.
fn room_state() -> Value {
  for top in gtk::Window::list_toplevels() {
    let Ok(win) = top.downcast::<gtk::Window>() else {
      continue;
    };
    let mut tree = vec![];
    widget_tree(win.upcast_ref(), win.upcast_ref(), 0, &mut tree);
    let webview = tree.iter().find(|n| n["type"] == "WebKitWebView");
    let room = tree
      .iter()
      .find(|n| n["type"] == "GtkScrolledWindow" || n["type"] == "GtkLayout")
      .or(webview);
    if let (Some(webview), Some(room)) = (webview, room) {
      let w = &webview["alloc"];
      let r = &room["alloc"];
      return json!({
        "webview": [w[2], w[3]],
        "room": [r[2], r[3]],
        "match": w[2] == r[2] && w[3] == r[3],
      });
    }
  }
  Value::Null
}

#[cfg(not(feature = "unstable"))]
fn tauri_state(app: &AppHandle) -> Value {
  // without `unstable` there are no children: a window and its webview
  let mut windows = vec![];
  for (label, w) in app.webview_windows() {
    let sf = w.scale_factor().unwrap_or(1.0);
    let inner = w.inner_size().map(|s| s.to_logical::<f64>(sf)).ok();
    windows.push(json!({ "label": label, "scale_factor": sf, "inner_size": inner.map(|s| [s.width, s.height]), "webviews": [] }));
  }
  json!(windows)
}

#[cfg(feature = "unstable")]
fn tauri_state(app: &AppHandle) -> Value {
  let mut windows = vec![];
  for (label, w) in app.windows() {
    let sf = w.scale_factor().unwrap_or(1.0);
    let inner = w.inner_size().map(|s| s.to_logical::<f64>(sf)).ok();
    let outer = w.outer_size().map(|s| s.to_logical::<f64>(sf)).ok();
    let mut webviews = vec![];
    for wv in w.webviews() {
      let bounds = wv.bounds().ok().map(|b| {
        let p = b.position.to_logical::<f64>(sf);
        let s = b.size.to_logical::<f64>(sf);
        [p.x, p.y, s.width, s.height]
      });
      webviews.push(json!({ "label": wv.label(), "bounds": bounds }));
    }
    windows.push(json!({
      "label": label,
      "scale_factor": sf,
      "inner_size": inner.map(|s| [s.width, s.height]),
      "outer_size": outer.map(|s| [s.width, s.height]),
      "webviews": webviews,
    }));
  }
  json!(windows)
}

struct Driver {
  app: AppHandle,
  out: PathBuf,
  scenario: String,
  session: String,
  records: Vec<Value>,
}

impl Driver {
  fn on_main<T: Send + 'static>(&self, f: impl FnOnce() -> T + Send + 'static) -> T {
    let (tx, rx) = mpsc::channel();
    self
      .app
      .run_on_main_thread(move || {
        let _ = tx.send(f());
      })
      .expect("run on main thread");
    rx.recv_timeout(Duration::from_secs(20))
      .expect("main thread answered")
  }

  fn measure(&mut self, tag: &str) {
    let gtk = self.on_main(dump_gtk);
    let tauri = tauri_state(&self.app);
    self
      .records
      .push(json!({ "tag": tag, "gtk": gtk, "tauri": tauri }));
  }

  fn shot(&self, name: &str) -> PathBuf {
    let path = self
      .out
      .join(format!("{}-{}-{}.png", self.scenario, self.session, name));
    let status = Command::new("import")
      .args(["-window", "root"])
      .arg(&path)
      .status()
      .expect("import runs");
    assert!(status.success(), "screenshot failed");
    path
  }

  /// The bounding box of the visible part of a page, from its border color in a screenshot.
  fn find(&self, image: &Path, color: &str) -> Option<[i64; 4]> {
    let script = std::env::var("FINDBOX").expect("FINDBOX is set");
    let out = Command::new("python3")
      .arg("-I")
      .arg(script)
      .arg(image)
      .arg(color)
      .output()
      .expect("findbox runs");
    let text = String::from_utf8_lossy(&out.stdout);
    let nums: Vec<i64> = text
      .split_whitespace()
      .filter_map(|n| n.parse().ok())
      .collect();
    (nums.len() == 4).then(|| [nums[0], nums[1], nums[2], nums[3]])
  }

  fn point(&mut self, x: i64, y: i64) {
    let _ = Command::new("xdotool")
      .args(["mousemove", &x.to_string(), &y.to_string()])
      .status();
    thread::sleep(Duration::from_millis(400));
  }

  fn click(&mut self, button: u32, times: u32) {
    let _ = Command::new("xdotool")
      .args([
        "click",
        "--repeat",
        &times.to_string(),
        "--delay",
        "100",
        &button.to_string(),
      ])
      .status();
    thread::sleep(Duration::from_millis(1200));
  }

  /// Moves the pointer to the middle of the page with this border color and turns the wheel.
  fn wheel_over(&mut self, shot: &Path, color: &str, clicks: u32) -> Option<[i64; 4]> {
    let b = self.find(shot, color)?;
    self.point(b[0] + b[2] / 2, b[1] + b[3] / 2);
    self.click(5, clicks);
    Some(b)
  }

  fn click_on(&mut self, shot: &Path, color: &str) -> Option<[i64; 4]> {
    let b = self.find(shot, color)?;
    self.point(b[0] + b[2] / 2, b[1] + b[3] / 2);
    self.click(1, 1);
    Some(b)
  }

  fn start_drag_source(&self) -> std::process::Child {
    let script = std::env::var("DRAGSOURCE").expect("DRAGSOURCE is set");
    Command::new("python3")
      .arg("-I")
      .arg(script)
      .arg(self.out.join("drop-me.txt"))
      .spawn()
      .expect("drag source starts")
  }

  fn stop_drag_source(&self, mut source: std::process::Child) {
    let _ = source.kill();
    let _ = source.wait();
  }

  /// Drags with the left button from a point to a point, in steps, as a person does.
  fn drag(&mut self, from: (i64, i64), to: (i64, i64)) {
    let run = |args: &[&str]| {
      let _ = Command::new("xdotool").args(args).status();
    };
    run(&["mousemove", &from.0.to_string(), &from.1.to_string()]);
    thread::sleep(Duration::from_millis(300));
    run(&["mousedown", "1"]);
    thread::sleep(Duration::from_millis(300));
    for i in 1..=10 {
      let x = from.0 + (to.0 - from.0) * i / 10;
      let y = from.1 + (to.1 - from.1) * i / 10;
      run(&["mousemove", &x.to_string(), &y.to_string()]);
      thread::sleep(Duration::from_millis(80));
    }
    thread::sleep(Duration::from_millis(400));
    run(&["mouseup", "1"]);
    thread::sleep(Duration::from_millis(1200));
  }

  fn finish(&mut self) {
    let file = self
      .out
      .join(format!("{}-{}.json", self.scenario, self.session));
    let doc = json!({ "scenario": self.scenario, "session": self.session, "records": self.records });
    fs::write(&file, serde_json::to_string_pretty(&doc).unwrap()).unwrap();
    println!("wrote {}", file.display());
    self.app.exit(0);
  }
}

fn settle() {
  thread::sleep(Duration::from_millis(3000));
}

fn build(app: &mut tauri::App, scenario: &str) -> tauri::Result<()> {
  let handle = app.handle().clone();
  match scenario {
    // problem 1: the window's own webview below a menu bar
    "menu" => {
      WebviewWindowBuilder::new(app, "main", main_page("main"))
        .inner_size(600., 400.)
        .menu(menu(&handle)?)
        .build()?;
    }
    // the window's own webview, no menu bar
    "plain" => {
      WebviewWindowBuilder::new(app, "main", main_page("main"))
        .inner_size(800., 600.)
        .build()?;
    }
    // problem 2: a child past the bottom edge of the window
    #[cfg(feature = "unstable")]
    "past" => {
      let w = WindowBuilder::new(app, "main").inner_size(800., 600.).build()?;
      w.add_child(
        WebviewBuilder::new("main", main_page("main")).auto_resize(),
        LogicalPosition::new(0., 0.),
        LogicalSize::new(800., 600.),
      )?;
      w.add_child(
        WebviewBuilder::new("child", solid("child", BLUE)),
        LogicalPosition::new(40., 320.),
        LogicalSize::new(300., 400.),
      )?;
    }
    // the layout of examples/multiwebview
    #[cfg(feature = "unstable")]
    "multi" => {
      let (width, height) = (800., 600.);
      let w = WindowBuilder::new(app, "main")
        .inner_size(width, height)
        .build()?;
      for (i, (color, x, y)) in [
        (BLUE, 0., 0.),
        (GREEN, width / 2., 0.),
        (ORANGE, 0., height / 2.),
        (PURPLE, width / 2., height / 2.),
      ]
      .into_iter()
      .enumerate()
      {
        w.add_child(
          WebviewBuilder::new(format!("main{}", i + 1), solid(&format!("main{}", i + 1), color))
            .auto_resize(),
          LogicalPosition::new(x, y),
          LogicalSize::new(width / 2., height / 2.),
        )?;
      }
    }
    // a file dropped on the window's webview, with and without a child over it
    #[cfg(feature = "unstable")]
    "dnd" | "dndchild" => {
      let main = WebviewWindowBuilder::new(app, "main", main_page("main"))
        .inner_size(800., 600.)
        .build()?;
      count_drops(&main.as_ref().clone());
      if scenario == "dndchild" {
        let child = main.as_ref().window().add_child(
          WebviewBuilder::new("child", solid("child", BLUE)),
          LogicalPosition::new(200., 100.),
          LogicalSize::new(400., 300.),
        )?;
        count_drops(&child);
      }
    }
    // clicks reach the webview under the pointer
    #[cfg(feature = "unstable")]
    "click" => {
      let w = WindowBuilder::new(app, "main").inner_size(800., 600.).build()?;
      w.add_child(
        WebviewBuilder::new("main", main_page("main")).auto_resize(),
        LogicalPosition::new(0., 0.),
        LogicalSize::new(800., 600.),
      )?;
      w.add_child(
        WebviewBuilder::new("blue", solid("blue", BLUE)),
        LogicalPosition::new(50., 50.),
        LogicalSize::new(300., 200.),
      )?;
      w.add_child(
        WebviewBuilder::new("green", solid("green", GREEN)),
        LogicalPosition::new(400., 300.),
        LogicalSize::new(300., 200.),
      )?;
    }
    // Webview::set_position, set_size and set_bounds, in each order
    #[cfg(feature = "unstable")]
    "bounds" => {
      let w = WindowBuilder::new(app, "main").inner_size(800., 600.).build()?;
      w.add_child(
        WebviewBuilder::new("main", main_page("main")).auto_resize(),
        LogicalPosition::new(0., 0.),
        LogicalSize::new(800., 600.),
      )?;
      w.add_child(
        WebviewBuilder::new("child", solid("child", BLUE)),
        LogicalPosition::new(100., 100.),
        LogicalSize::new(200., 150.),
      )?;
    }
    // a child that reaches over the menu bar must not take the clicks of the menu bar
    #[cfg(feature = "unstable")]
    "edge" => {
      let w = WindowBuilder::new(app, "main")
        .inner_size(600., 400.)
        .menu(menu(&handle)?)
        .build()?;
      w.add_child(
        WebviewBuilder::new("main", main_page("main")).auto_resize(),
        LogicalPosition::new(0., 0.),
        LogicalSize::new(600., 375.),
      )?;
      w.add_child(
        WebviewBuilder::new("over", solid("over", BLUE)),
        LogicalPosition::new(5., -60.),
        LogicalSize::new(100., 200.),
      )?;
    }
    // the menu bar hides and shows: the room changes, the window does not
    #[cfg(feature = "unstable")]
    "menuhide" => {
      let w = WindowBuilder::new(app, "main")
        .inner_size(800., 600.)
        .menu(menu(&handle)?)
        .build()?;
      w.add_child(
        WebviewBuilder::new("main", main_page("main")).auto_resize(),
        LogicalPosition::new(0., 0.),
        LogicalSize::new(800., 575.),
      )?;
      w.add_child(
        WebviewBuilder::new("half", solid("half", BLUE)).auto_resize(),
        LogicalPosition::new(400., 287.),
        LogicalSize::new(400., 288.),
      )?;
    }
    // a window with a child at rest must not lay out again and again
    #[cfg(feature = "unstable")]
    "idle" => {
      let w = WindowBuilder::new(app, "main").inner_size(800., 600.).build()?;
      w.add_child(
        WebviewBuilder::new("main", main_page("main")).auto_resize(),
        LogicalPosition::new(0., 0.),
        LogicalSize::new(800., 600.),
      )?;
      w.add_child(
        WebviewBuilder::new("half", solid("half", BLUE)).auto_resize(),
        LogicalPosition::new(400., 300.),
        LogicalSize::new(400., 300.),
      )?;
    }
    // closing a child and then the window
    #[cfg(feature = "unstable")]
    "close" => {
      let w = WindowBuilder::new(app, "main").inner_size(800., 600.).build()?;
      w.add_child(
        WebviewBuilder::new("main", main_page("main")).auto_resize(),
        LogicalPosition::new(0., 0.),
        LogicalSize::new(800., 600.),
      )?;
      w.add_child(
        WebviewBuilder::new("child", solid("child", BLUE)).auto_resize(),
        LogicalPosition::new(400., 300.),
        LogicalSize::new(400., 300.),
      )?;
    }
    // how long after a resize the window's webview has the size of its room
    "latency" => {
      WebviewWindowBuilder::new(app, "main", main_page("main"))
        .inner_size(800., 600.)
        .build()?;
    }
    // problem 3: Webview::reparent
    #[cfg(feature = "unstable")]
    "reparent" => {
      let a = WindowBuilder::new(app, "a")
        .inner_size(500., 400.)
        .position(0., 0.)
        .build()?;
      a.add_child(
        WebviewBuilder::new("a", main_page("a")).auto_resize(),
        LogicalPosition::new(0., 0.),
        LogicalSize::new(500., 400.),
      )?;
      a.add_child(
        WebviewBuilder::new("child", solid("child", BLUE)),
        LogicalPosition::new(60., 60.),
        LogicalSize::new(240., 160.),
      )?;
      let b = WindowBuilder::new(app, "b")
        .inner_size(500., 400.)
        .position(520., 0.)
        .build()?;
      b.add_child(
        WebviewBuilder::new("b", main_page("b")).auto_resize(),
        LogicalPosition::new(0., 0.),
        LogicalSize::new(500., 400.),
      )?;
    }
    other => panic!("unknown scenario {other}"),
  }
  Ok(())
}

fn drive(d: &mut Driver) {
  settle();
  d.measure("settled");
  let start = d.shot("start");
  let session = d.session.clone();
  match d.scenario.as_str() {
    "menu" | "plain" => {
      // the wheel over the window's own webview
      d.wheel_over(&start, MAIN, 5);
      d.measure("after-wheel");
      d.shot("after-wheel");
      // the window shrinks and grows, and the webview follows the room
      let w = d.app.get_webview_window("main").unwrap();
      w.set_size(LogicalSize::new(320., 240.)).unwrap();
      thread::sleep(Duration::from_millis(1500));
      d.measure("shrunk-320x240");
      d.shot("shrunk");
      w.set_size(LogicalSize::new(900., 700.)).unwrap();
      thread::sleep(Duration::from_millis(1500));
      d.measure("grown-900x700");
      d.shot("grown");
    }
    #[cfg(feature = "unstable")]
    "past" => {
      d.click_on(&start, BLUE);
      d.measure("after-click");
      let shot = d.shot("after-click");
      d.wheel_over(&shot, BLUE, 5);
      d.measure("after-wheel");
      d.shot("after-wheel");
      let _ = session;
    }
    #[cfg(feature = "unstable")]
    "multi" => {
      let w = d.app.get_window("main").unwrap();
      w.set_size(LogicalSize::new(1000., 700.)).unwrap();
      thread::sleep(Duration::from_millis(1500));
      d.measure("grown-1000x700");
      d.shot("grown");
      w.set_size(LogicalSize::new(400., 300.)).unwrap();
      thread::sleep(Duration::from_millis(1500));
      d.measure("shrunk-400x300");
      d.shot("shrunk");
    }
    #[cfg(feature = "unstable")]
    "dnd" | "dndchild" => {
      let source = d.start_drag_source();
      thread::sleep(Duration::from_millis(2500));
      let shot = d.shot("with-source");
      let from = d.find(&shot, SOURCE).map(|b| (b[0] + b[2] / 2, b[1] + b[3] / 2));
      let main = d.find(&shot, MAIN);
      let child = d.find(&shot, BLUE);
      d.records.push(json!({"tag": "dnd-found", "source": from, "main": main, "child": child}));
      if let (Some(from), Some(main)) = (from, main) {
        let mut targets = vec![("main-only", (main[0] + 100, main[1] + 500))];
        if let Some(c) = child {
          targets.push(("over-child", (c[0] + c[2] / 2, c[1] + c[3] / 2)));
          targets.push(("main-beside-child", (main[0] + 700, main[1] + 500)));
        } else {
          targets.push(("main-center", (main[0] + 400, main[1] + 300)));
        }
        for (name, to) in targets {
          let before = drops();
          d.drag(from, to);
          d.records.push(json!({"tag": format!("dnd-{name}"), "target": to, "drops-before": before, "drops-after": drops()}));
        }
      }
      d.shot("after-drops");
      d.stop_drag_source(source);
    }
    #[cfg(feature = "unstable")]
    "idle" => {
      let cpu = || -> u64 {
        let stat = fs::read_to_string("/proc/self/stat").unwrap();
        let f: Vec<&str> = stat.rsplit(')').next().unwrap().split_whitespace().collect();
        f[11].parse::<u64>().unwrap() + f[12].parse::<u64>().unwrap()
      };
      // the ticks of this process, and of the whole process tree is not needed: the UI thread is in this one
      thread::sleep(Duration::from_millis(2000));
      let (a, t0) = (cpu(), std::time::Instant::now());
      thread::sleep(Duration::from_millis(5000));
      let (b, secs) = (cpu(), t0.elapsed().as_secs_f64());
      d.records.push(json!({
        "tag": "idle-cpu", "ticks": b - a, "seconds": secs, "percent_of_one_core": (b - a) as f64 / 100.0 / secs * 100.0,
      }));
    }
    #[cfg(feature = "unstable")]
    "click" => {
      for color in [BLUE, GREEN] {
        d.click_on(&start, color);
        d.measure(&format!("after-click-{color}"));
      }
      // the window's page fills the window under the children: click it near its bottom left corner
      if let Some(b) = d.find(&start, MAIN) {
        d.point(b[0] + 20, b[1] + b[3] - 20);
        d.click(1, 1);
      }
      d.measure(&format!("after-click-{MAIN}"));
      d.shot("after-clicks");
    }
    #[cfg(feature = "unstable")]
    "close" => {
      d.app.get_webview("child").unwrap().close().unwrap();
      thread::sleep(Duration::from_millis(1000));
      d.measure("child-closed");
      let w = d.app.get_window("main").unwrap();
      w.set_size(LogicalSize::new(500., 400.)).unwrap();
      thread::sleep(Duration::from_millis(1000));
      d.measure("window-resized");
      w.destroy().unwrap();
      thread::sleep(Duration::from_millis(1000));
    }
    #[cfg(feature = "unstable")]
    "bounds" => {
      let child = d.app.get_webview("child").unwrap();
      let sf = 1.0;
      let _ = sf;
      // set_position, then set_size at once
      child.set_position(LogicalPosition::new(300., 200.)).unwrap();
      child.set_size(LogicalSize::new(240., 180.)).unwrap();
      thread::sleep(Duration::from_millis(1500));
      d.measure("position-then-size");
      // set_size, then set_position at once
      child.set_size(LogicalSize::new(150., 100.)).unwrap();
      child.set_position(LogicalPosition::new(50., 60.)).unwrap();
      thread::sleep(Duration::from_millis(1500));
      d.measure("size-then-position");
      // set_bounds
      child
        .set_bounds(tauri::Rect {
          position: LogicalPosition::new(10., 20.).into(),
          size: LogicalSize::new(320., 210.).into(),
        })
        .unwrap();
      thread::sleep(Duration::from_millis(1500));
      d.measure("set-bounds");
      // the window grows: a child that does not resize with the window keeps its bounds
      let w = d.app.get_window("main").unwrap();
      w.set_size(LogicalSize::new(1000., 700.)).unwrap();
      thread::sleep(Duration::from_millis(1500));
      d.measure("window-grown");
      d.shot("window-grown");
    }
    #[cfg(feature = "unstable")]
    "edge" => {
      // the child is over the "File" item of the menu bar: a click there opens the menu
      if let Some(main) = d.find(&start, MAIN) {
        d.point(main[0] + 15, main[1] - 12);
        d.click(1, 1);
        d.measure("after-click-on-menu-bar");
        d.shot("after-click-on-menu-bar");
      }
    }
    #[cfg(feature = "unstable")]
    "menuhide" => {
      let w = d.app.get_window("main").unwrap();
      w.hide_menu().unwrap();
      thread::sleep(Duration::from_millis(1500));
      d.measure("menu-hidden");
      d.shot("menu-hidden");
      w.show_menu().unwrap();
      thread::sleep(Duration::from_millis(1500));
      d.measure("menu-shown");
    }
    "latency" => {
      let w = d.app.get_webview_window("main").unwrap();
      let mut results = vec![];
      for (i, size) in [(1000., 700.), (640., 480.), (900., 650.), (500., 400.), (1000., 700.), (700., 500.)]
        .into_iter()
        .enumerate()
      {
        let t0 = std::time::Instant::now();
        w.set_size(LogicalSize::new(size.0, size.1)).unwrap();
        let mut elapsed = None;
        let mut last = Value::Null;
        for _ in 0..300 {
          let state = d.on_main(room_state);
          last = state.clone();
          if state["match"] == json!(true) && state["room"] == json!([size.0 as i64, size.1 as i64]) {
            elapsed = Some(t0.elapsed().as_millis());
            break;
          }
          thread::sleep(Duration::from_millis(5));
        }
        results.push(json!({"i": i, "size": [size.0, size.1], "ms": elapsed, "last": last}));
        thread::sleep(Duration::from_millis(800));
      }
      d.records.push(json!({"tag": "latency", "results": results}));
    }
    #[cfg(feature = "unstable")]
    "reparent" => {
      let child = d.app.get_webview("child").unwrap();
      let b = d.app.get_window("b").unwrap();
      let before = child.bounds().unwrap();
      child.reparent(&b).unwrap();
      thread::sleep(Duration::from_millis(1500));
      let after = child.bounds().unwrap();
      d.records.push(json!({
        "tag": "reparent-bounds",
        "before": format!("{before:?}"),
        "after": format!("{after:?}"),
      }));
      d.measure("after-reparent");
      d.shot("after-reparent");
    }
    _ => {}
  }
  d.finish();
}

fn main() {
  let scenario = std::env::args().nth(1).expect("usage: childviews SCENARIO");
  let out = PathBuf::from(std::env::var("OUT").unwrap_or_else(|_| "out".into()));
  fs::create_dir_all(&out).unwrap();
  let session = std::env::var("SESSION_MODE").unwrap_or_else(|_| "unknown".into());
  let sc = scenario.clone();
  tauri::Builder::default()
    .setup(move |app| {
      build(app, &sc)?;
      let mut driver = Driver {
        app: app.handle().clone(),
        out,
        scenario: sc,
        session,
        records: vec![],
      };
      thread::spawn(move || drive(&mut driver));
      // a watchdog, so that a stuck run ends
      let handle = app.handle().clone();
      thread::spawn(move || {
        thread::sleep(Duration::from_secs(90));
        eprintln!("watchdog: the scenario did not finish");
        handle.exit(3);
      });
      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running the app");
}
