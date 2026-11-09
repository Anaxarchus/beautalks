#!/usr/bin/env python3
# beautalks - radio programming software
# Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
"""Icon and brand rasters for the btui toolkit (ui/).

Material Symbols (Apache-2.0, Google; npm package @material-symbols/svg-400,
style "rounded") are rasterised with rsvg-convert into one alpha atlas per
display scale. Every icon is drawn at 18, 20 and 24 dp, outlined and filled,
so the app never scales an icon bitmap at 1x or 2x.

Writes into assets/icons/:
    icons@1x.png / icons@2x.png   the atlas, for people (black on transparent)
    icons@1x.bta / icons@2x.bta   the same alpha, for the app (see below)
    icons@1x.csv / icons@2x.csv   name,fill,size_dp,x,y,w,h  (pixels)
    LICENSE-material-symbols.txt
and the brand images into assets/brand/ (RGBA .bta + .png):
    wordmark[-dark]@{1,2}x   the wordmark at 28 dp tall
    appicon@{1,2}x           the app icon at 40 dp

.bta is "BTA1" u32 width u32 height u32 channels, then rows top-down (no
padding). It exists because the app has no PNG decoder.

    python3 tools/make_icons.py --symbols <node_modules/@material-symbols/svg-400>
Needs: rsvg-convert (librsvg2-bin) and Pillow.
"""
import argparse
import io
import os
import struct
import subprocess
import sys

from PIL import Image

ICONS = """
radio usb cable sync download upload save edit delete add search check_circle error
warning info settings history folder star tune close more_vert arrow_back chevron_right
chevron_left light_mode dark_mode library_books swap_horiz verified lock help refresh
wifi_tethering check arrow_drop_down arrow_upward arrow_downward
keyboard_arrow_down keyboard_arrow_up menu filter_list content_copy content_paste undo redo home widgets cancel remove
open_in_new backup settings_backup_restore schedule bolt notifications person palette visibility
unfold_more drag_indicator sell table_rows edit_note playlist_add description
upload_file folder_open cell_tower sensors signal_cellular_alt keyboard
check_box check_box_outline_blank radio_button_checked radio_button_unchecked
lock_open block contrast list format_list_numbered inventory_2 devices
priority_high sell label wifi
""".split()

SIZES = [18, 20, 24]
SCALES = [1, 2]
PAD = 1
ATLAS_W = {1: 512, 2: 1024}


def rsvg(path, w, h):
    png = subprocess.run(["rsvg-convert", "-w", str(w), "-h", str(h), path],
                         check=True, capture_output=True).stdout
    return Image.open(io.BytesIO(png)).convert("RGBA")


def write_bta(path, img, channels):
    w, h = img.size
    with open(path, "wb") as f:
        f.write(b"BTA1")
        f.write(struct.pack("<III", w, h, channels))
        if channels == 1:
            f.write(img.tobytes())
        else:
            f.write(img.convert("RGBA").tobytes())


def pack(items, width):
    """Shelf packer: items are (key, w, h); answers {key: (x, y)} and height."""
    items = sorted(items, key=lambda t: (-t[2], t[0]))
    x = y = shelf = 0
    out = {}
    for key, w, h in items:
        if x + w + PAD > width:
            x = 0
            y += shelf + PAD
            shelf = 0
        out[key] = (x + PAD, y + PAD)
        x += w + PAD
        shelf = max(shelf, h)
    return out, y + shelf + 2 * PAD


def icons(symbols, outdir):
    style = os.path.join(symbols, "rounded")
    missing = [n for n in ICONS if not os.path.exists(os.path.join(style, n + ".svg"))]
    if missing:
        sys.exit("missing symbols: " + " ".join(missing))
    for scale in SCALES:
        cells = []
        bitmaps = {}
        for name in ICONS:
            for fill in (0, 1):
                svg = os.path.join(style, name + ("-fill" if fill else "") + ".svg")
                for dp in SIZES:
                    px = dp * scale
                    alpha = rsvg(svg, px, px).getchannel("A")
                    bitmaps[(name, fill, dp)] = alpha
                    cells.append(((name, fill, dp), px, px))
        pos, height = pack(cells, ATLAS_W[scale])
        atlas = Image.new("L", (ATLAS_W[scale], height), 0)
        rows = []
        for key, (x, y) in pos.items():
            atlas.paste(bitmaps[key], (x, y))
            name, fill, dp = key
            rows.append(f"{name},{fill},{dp},{x},{y},{dp * scale},{dp * scale}")
        base = os.path.join(outdir, f"icons@{scale}x")
        write_bta(base + ".bta", atlas, 1)
        show = Image.new("RGBA", atlas.size, (0, 0, 0, 0))
        show.putalpha(atlas)
        show.save(base + ".png")
        with open(base + ".csv", "w") as f:
            f.write("name,fill,size_dp,x,y,w,h\n")
            f.write("\n".join(sorted(rows)) + "\n")
        print(f"{base}: {len(rows)} icons, {atlas.size[0]}x{atlas.size[1]}")
    lic = os.path.join(symbols, "LICENSE")
    with open(os.path.join(outdir, "LICENSE-material-symbols.txt"), "w") as f:
        f.write("Material Symbols (style: rounded, weight 400), from the npm package\n"
                "@material-symbols/svg-400. Copyright Google LLC. Apache License 2.0.\n"
                "Rasterised into icons@1x/@2x by tools/make_icons.py.\n\n")
        f.write(open(lic).read())


def brand(branddir):
    jobs = [("beautalks-wordmark.svg", "wordmark", 28),
            ("beautalks-wordmark-dark.svg", "wordmark-dark", 28),
            ("beautalks-icon.svg", "appicon", 40)]
    for svg, name, dp in jobs:
        path = os.path.join(branddir, svg)
        with open(path) as f:
            head = f.read(400)
        vb = head.split('viewBox="')[1].split('"')[0].split()
        vw, vh = float(vb[2]), float(vb[3])
        for scale in SCALES:
            h = dp * scale
            w = round(vw * h / vh)
            img = rsvg(path, w, h)
            base = os.path.join(branddir, f"{name}@{scale}x")
            write_bta(base + ".bta", img, 4)
            img.save(base + ".png")
            print(f"{base}: {w}x{h}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", required=True, help="path to @material-symbols/svg-400")
    ap.add_argument("--root", default=os.path.join(os.path.dirname(__file__), ".."))
    a = ap.parse_args()
    icons(a.symbols, os.path.join(a.root, "assets", "icons"))
    brand(os.path.join(a.root, "assets", "brand"))


if __name__ == "__main__":
    main()
