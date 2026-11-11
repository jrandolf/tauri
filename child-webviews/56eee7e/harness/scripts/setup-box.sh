#!/usr/bin/env bash
# On the box, once: the packages that the display sessions and the checks need.
set -euo pipefail
sudo -n env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq xdotool imagemagick x11-utils python3-pil fonts-dejavu-core xvfb weston >/dev/null
which xdotool import xwininfo weston Xvfb
python3 -c "import PIL; print('PIL', PIL.__version__)"
