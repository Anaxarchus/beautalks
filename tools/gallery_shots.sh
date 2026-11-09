#!/bin/bash
# beautalks - radio programming software
# Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
#
# Screenshots of the btui component gallery into docs/screens-native/.
# Needs an X server big enough for 2x (Xvfb :98 -screen 0 3000x1900x24),
# xdotool and ImageMagick's `import`, and a build:
#   dado build gallery -o build/gallery && DISPLAY=:98 tools/gallery_shots.sh
set -u
cd "$(dirname "$0")/.."
OUT=docs/screens-native
mkdir -p "$OUT"
: "${DISPLAY:=:98}"
export DISPLAY

# shot NAME [gallery args...]
#   env: HOVER="x y", KEYS="k1 k2", SCALE=2, SIZE="w h", SCROLLX=n (shift+wheel)
shot() {
  local name=$1; shift
  pkill -x gallery 2>/dev/null; sleep 0.3
  (BTUI_SCALE=${SCALE:-} ./build/gallery --light "$@" > build/shot.log 2>&1 &)
  sleep "${WAIT:-2.5}"
  local wid
  wid=$(xdotool search --name 'btui gallery' | head -1)
  if [ -n "${SIZE:-}" ]; then xdotool windowsize "$wid" $SIZE; sleep 1; fi
  if [ -n "${HOVER:-}" ]; then xdotool mousemove --window "$wid" $HOVER; sleep "${HOVERWAIT:-1.4}"; fi
  if [ -n "${SCROLLX:-}" ]; then for i in $(seq 1 "$SCROLLX"); do xdotool keydown shift click 5 keyup shift; sleep 0.05; done; sleep 1; fi
  if [ -n "${KEYS:-}" ]; then for k in $KEYS; do xdotool key --window "$wid" "$k" 2>/dev/null; sleep 0.15; done; sleep 0.6; fi
  import -window "$wid" "$OUT/$name"
  echo "$OUT/$name"
  pkill -x gallery 2>/dev/null
}

shot 01-channels-light.png
shot 02-channels-dark.png --dark
HOVER="440 442" shot 03-channels-error-tooltip.png
shot 03b-channels-error-keyboard.png --cursor-error
shot 04-channels-edit-dropdown.png --edit
shot 05-channels-write-dialog.png --dialog
shot 06-channels-snackbar-dark.png --dark --snackbar
shot 07-channels-1000-slots.png --rows1000 --scroll 1100
SIZE="1100 760" HOVER="700 500" SCROLLX=7 shot 08-channels-narrow-frozen.png --scroll 0
shot 09-components-light.png --page components
shot 10-components-dark.png --page components --dark
shot 11-components-lists-cards.png --page components --scroll 560
shot 12-components-lists-cards-dark.png --page components --scroll 560 --dark
HOVER="248 284" shot 13-tooltip.png --page components
KEYS="Tab Tab Tab Tab Tab Tab Tab Tab Tab Tab" shot 14-focus-ring.png --page components
shot 15-forms-light.png --page forms
shot 16-forms-dark.png --page forms --dark
shot 17-forms-menu.png --page forms --menu
shot 18-forms-dialog-dark.png --page forms --dialog --dark
SCALE=2 WAIT=4 shot 19-channels-2x.png
SCALE=2 WAIT=4 shot 20-components-2x-dark.png --page components --dark
