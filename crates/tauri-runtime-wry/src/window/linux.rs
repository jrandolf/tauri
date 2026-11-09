// Copyright 2019-2024 Tauri Programme within The Commons Conservancy
// SPDX-License-Identifier: Apache-2.0
// SPDX-License-Identifier: MIT

use gtk::prelude::*;
#[cfg(any(
  target_os = "linux",
  target_os = "dragonfly",
  target_os = "freebsd",
  target_os = "netbsd",
  target_os = "openbsd"
))]
use tao::platform::unix::WindowExtUnix;
use wry::WebViewExtUnix;

impl super::WindowExt for tao::window::Window {
  fn set_enabled(&self, enabled: bool) {
    self.gtk_window().set_sensitive(enabled);
  }

  fn is_enabled(&self) -> bool {
    self.gtk_window().is_sensitive()
  }

  fn center(&self) {
    if let Some(monitor) = self.current_monitor() {
      let window_size = self.outer_size();
      let new_pos = super::calculate_window_center_position(window_size, monitor);
      self.set_outer_position(new_pos);
    }
  }
}

/// Names the overlay that [`WebviewContainers`] adds to a window's default vbox.
const WEBVIEW_OVERLAY_NAME: &str = "tauri-webview-overlay";

/// The containers for a window's webviews, in its default vbox below the menu bar.
///
/// They are the main child and the overlay child of a [`gtk::Overlay`], so positioned webviews
/// are drawn over the filling ones. The overlay child lets input through where it has no webview.
pub struct WebviewContainers {
  /// Packs the webviews that fill the window.
  pub filling: gtk::Box,
  /// Puts webviews at their own bounds.
  pub positioned: gtk::Fixed,
}

impl WebviewContainers {
  /// Returns the containers in `vbox`, adding them the first time.
  pub fn get_or_create(vbox: &gtk::Box) -> Self {
    if let Some(containers) = vbox.children().into_iter().find_map(Self::from_overlay) {
      return containers;
    }

    let containers = Self {
      filling: gtk::Box::new(gtk::Orientation::Vertical, 0),
      positioned: gtk::Fixed::new(),
    };
    let overlay = gtk::Overlay::new();
    overlay.set_widget_name(WEBVIEW_OVERLAY_NAME);
    overlay.add(&containers.filling);
    overlay.add_overlay(&containers.positioned);
    overlay.set_overlay_pass_through(&containers.positioned, true);
    vbox.pack_start(&overlay, true, true, 0);
    overlay.show_all();
    containers
  }

  fn from_overlay(widget: gtk::Widget) -> Option<Self> {
    if widget.widget_name() != WEBVIEW_OVERLAY_NAME {
      return None;
    }
    let overlay = widget.downcast::<gtk::Overlay>().ok()?;
    Some(Self {
      filling: overlay.child()?.downcast().ok()?,
      positioned: overlay
        .children()
        .into_iter()
        .find_map(|child| child.downcast().ok())?,
    })
  }

  /// Moves `webview` to the window with `vbox`, into the same kind of container it is in now.
  pub fn reparent(webview: &wry::WebView, vbox: &gtk::Box) -> wry::Result<()> {
    let parent = webview.webview().parent();
    if parent
      .as_ref()
      .is_some_and(|parent| parent.is::<gtk::Fixed>())
    {
      // `gtk::Fixed::put` places it at the top left, so its bounds are set again.
      let bounds = webview.bounds()?;
      webview.reparent(&Self::get_or_create(vbox).positioned)?;
      webview.set_bounds(bounds)
    } else if parent
      .and_then(|parent| parent.parent())
      .is_some_and(|grandparent| grandparent.widget_name() == WEBVIEW_OVERLAY_NAME)
    {
      webview.reparent(&Self::get_or_create(vbox).filling)
    } else {
      webview.reparent(vbox)
    }
  }
}
