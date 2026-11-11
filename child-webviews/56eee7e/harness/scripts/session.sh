#!/usr/bin/env bash
# Runs a command inside a display session on the Linux box.
#   session.sh x11     COMMAND...   under Xvfb (X11), no window manager
#   session.sh wayland COMMAND...   under Weston 13 (Wayland), nested in Xvfb so that xdotool input reaches it
#   session.sh wayland-headless COMMAND...   under headless Weston (no input devices)
# Exports DISPLAY (the Xvfb), and for Wayland WAYLAND_DISPLAY, GDK_BACKEND=wayland and XDG_RUNTIME_DIR.
# Stops what it started, by PID.
set -u
mode=$1
shift
size=${SESSION_SIZE:-1400x1000}
pids=()
cleanup() {
  for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null; done
  for pid in "${pids[@]}"; do wait "$pid" 2>/dev/null; done
  [ -n "${XDG_RUNTIME_DIR:-}" ] && [ -n "${SESSION_TMP:-}" ] && rm -rf "$SESSION_TMP"
}
trap cleanup EXIT
SESSION_TMP=$(mktemp -d)
export XDG_RUNTIME_DIR=$SESSION_TMP/run
mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"
export NO_AT_BRIDGE=1
export LIBGL_ALWAYS_SOFTWARE=1

start_xvfb() {
  # pick a free display number; sessions that start together take turns
  exec 9>/tmp/session-xvfb.lock
  flock 9
  for n in $(seq 90 130); do
    if [ ! -e /tmp/.X11-unix/X$n ] && [ ! -e /tmp/.X$n-lock ]; then
      Xvfb :$n -screen 0 ${size}x24 -nolisten tcp >"$SESSION_TMP/xvfb.log" 2>&1 &
      pids+=($!)
      export DISPLAY=:$n
      break
    fi
  done
  for _ in $(seq 1 50); do
    if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
      flock -u 9
      return 0
    fi
    sleep 0.1
  done
  echo "session: Xvfb did not start" >&2
  cat "$SESSION_TMP/xvfb.log" >&2
  exit 1
}

case "$mode" in
  x11)
    export GDK_BACKEND=x11
    start_xvfb
    ;;
  wayland | wayland-headless)
    start_xvfb
    export WAYLAND_DISPLAY=wl-session
    if [ "$mode" = wayland ]; then
      weston --backend=x11-backend.so --renderer=pixman --width=${size%x*} --height=${size#*x} \
        --socket=$WAYLAND_DISPLAY --no-config --log="$SESSION_TMP/weston.log" >"$SESSION_TMP/weston.out" 2>&1 &
    else
      weston --backend=headless-backend.so --renderer=pixman --width=${size%x*} --height=${size#*x} \
        --socket=$WAYLAND_DISPLAY --no-config --debug --log="$SESSION_TMP/weston.log" >"$SESSION_TMP/weston.out" 2>&1 &
    fi
    pids+=($!)
    for _ in $(seq 1 50); do
      [ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ] && break
      sleep 0.1
    done
    if [ ! -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]; then
      echo "session: Weston did not start" >&2
      cat "$SESSION_TMP/weston.log" "$SESSION_TMP/weston.out" >&2
      exit 1
    fi
    export GDK_BACKEND=wayland
    ;;
  *)
    echo "usage: session.sh x11|wayland|wayland-headless COMMAND..." >&2
    exit 2
    ;;
esac
export SESSION_MODE=$mode
"$@"
code=$?
exit $code
