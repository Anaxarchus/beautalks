#!/bin/sh
# beautalks - radio programming software
# Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
#
# Adds beautalks to your desktop's application menu (for this user only), pointing at
# this folder. Run it again after moving the folder; --remove takes the entry away.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICONS="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/256x256/apps"
if [ "${1:-}" = "--remove" ]; then
    rm -f "$APPS/beautalks.desktop" "$ICONS/beautalks.png"
    echo "removed the beautalks menu entry"
    exit 0
fi
mkdir -p "$APPS" "$ICONS"
cp "$HERE/beautalks.png" "$ICONS/beautalks.png"
sed -e "s|@EXEC@|\"$HERE/bin/beautalks\"|" -e "s|@ICON@|beautalks|" "$HERE/beautalks.desktop" > "$APPS/beautalks.desktop"
chmod 644 "$APPS/beautalks.desktop"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS" >/dev/null 2>&1 || true
echo "added beautalks to the application menu ($APPS/beautalks.desktop)"
