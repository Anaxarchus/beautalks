#!/bin/bash
# beautalks - radio programming software
# Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
#
# Screenshots of every screen of the desktop app into docs/screens-app/,
# against the pty emulator (tools/emu.py). Needs an X server (Xvfb :97
# -screen 0 3000x1900x24), xdotool, ImageMagick `import`, python3, and
#   dado build app -o build/beautalks-app   (build/beautalks is the CLI)
# Usage: DISPLAY=:97 tools/app_shots.sh [names...]
set -u
cd "$(dirname "$0")/.."
OUT=docs/screens-app
mkdir -p "$OUT" build/shots
: "${DISPLAY:=:97}"
export DISPLAY

# A fresh emulator for every shot: a killed app can leave a session open.
EMU_MODEL=""; EMU_IMAGE=""
start_emu() {  # model.ini image.img
  EMU_MODEL=$1; EMU_IMAGE=$2
  pkill -f "port-file build/shots/emu.port" 2>/dev/null; sleep 0.3
  rm -f build/shots/emu.port
  (python3 tools/emu.py --model "$1" --image "$2" --port-file build/shots/emu.port --session-timeout 2 ${EMU_EXTRA:-} > build/shots/emu.log 2>&1 &)
  for _ in $(seq 1 50); do [ -s build/shots/emu.port ] && break; sleep 0.1; done
  PORT=$(cat build/shots/emu.port)
}

# shot FILE SHOTNAME WAIT [extra args]: WAIT is the most seconds to wait for
# the app's "SHOT READY" (it drives itself there; detection can be slow).
shot() {
  local file=$1 name=$2 wait=$3; shift 3
  pkill -x beautalks-app 2>/dev/null; sleep 0.3
  start_emu "$EMU_MODEL" "$EMU_IMAGE"
  rm -rf build/shots/lib/profiles   # each shot makes its own profile
  (./build/beautalks-app --port "$PORT" --data build/shots/data --library build/shots/lib \
     --models "${MODELS:-models}" --no-watch --light --shot "$name" "$@" > build/shots/app.log 2>&1 &)
  for _ in $(seq 1 $((wait * 4))); do grep -q "SHOT READY" build/shots/app.log && break; sleep 0.25; done
  grep -q "SHOT READY" build/shots/app.log || echo "$name: not ready after ${wait}s" >&2
  sleep 0.5
  local wid
  wid=$(xdotool search --name '^beautalks$' | head -1)
  if [ -z "$wid" ]; then echo "no window for $name" >&2; cat build/shots/app.log >&2; return; fi
  if [ -n "${HOVER:-}" ]; then xdotool mousemove --window "$wid" $HOVER; sleep 1.5; fi
  import -window "$wid" "$OUT/$file"
  echo "$OUT/$file"
  pkill -x beautalks-app 2>/dev/null
}

rm -rf build/shots/data build/shots/lib
start_emu models/uv-5rm.ini testdata/uv5rm.img
shot 01-radio-plug-in.png radio 20
shot 01b-radio-mac-waiting.png radio-mac 20
shot 01c-radio-mac-other-ports.png radio-mac-other 20
EMU_EXTRA="--reply-delay 600" shot 02-detecting.png detecting 30   # slowed: detection is quick now
shot 03-identity.png identity 90
shot 04-which-radio.png which 90
EMU_EXTRA="--drop-first 100000000" shot 05-error-no-answer.png error 90
shot 06-channels.png channels 90
shot 07-channels-dark.png channels 90 --dark
shot 08-channels-error-footer.png channels-error 90
shot 09-tone-picker.png tone 90
shot 10-write-review.png review 90
shot 12-write-confirm.png confirm 90
shot 13-writing.png writing 90
shot 14-write-done.png result 90
shot 15-profiles.png profiles 90
shot 16-library.png library 90
shot 17-apply-preview.png apply 90
shot 18-apply-preview-dark.png apply 90 --dark
shot 17b-apply-keep-positions.png apply-keep 90
shot 19-radios.png radios 20
shot 20-backups.png backups 20
shot 21-settings.png settings 20
shot 22-settings-dark.png settings 20 --dark
# an untested model: a models copy with the UV-5R family marked read-only
rm -rf build/shots/models && cp -r models build/shots/models
sed -i 's/^tested = write/tested = read/' build/shots/models/uv-5r.ini
start_emu build/shots/models/uv-5r.ini testdata/uv5re.img
MODELS=build/shots/models shot 11-write-untested.png untested 90
MODELS=build/shots/models shot 23-verify-intro.png verify 90
MODELS=build/shots/models shot 24-verify-channels.png verify-channels 90
MODELS=build/shots/models shot 25-verify-power.png verify-power 90
MODELS=build/shots/models shot 26-verify-pass.png verify-pass 90
pkill -f "port-file build/shots/emu.port" 2>/dev/null
