#!/usr/bin/env python3
# beautalks - radio programming software
# Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
#
# Makes the platform icons from assets/brand/beautalks-icon.svg:
#   packaging/icons/beautalks-<N>.png   N = 16 32 48 64 128 256 512 1024
#   packaging/macos/beautalks.icns      PNG-based icns (macOS 10.7+), written
#                                       directly: no iconutil needed
#   packaging/windows/beautalks.ico     PNG-compressed ico (Vista+)
#
# The outputs are committed, so a release does not run this. Rerun it when the
# icon changes:  python3 tools/release/make_icons.py
# Rasterises with rsvg-convert (librsvg; `brew install librsvg` on a Mac) and,
# without it, scales the largest committed PNG with Pillow.
import io, os, shutil, struct, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SVG = os.path.join(ROOT, "assets", "brand", "beautalks-icon.svg")
PKG = os.path.join(ROOT, "packaging")
SIZES = [16, 32, 48, 64, 128, 256, 512, 1024]


def render(size):
    if shutil.which("rsvg-convert"):
        return subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), SVG],
                              check=True, stdout=subprocess.PIPE).stdout
    from PIL import Image  # fallback
    src = os.path.join(ROOT, "assets", "brand", "beautalks-icon-512.png")
    im = Image.open(src).convert("RGBA").resize((size, size), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True)
    return b.getvalue()


def icns(pngs):
    # type -> pixel size; the @2x types hold the doubled bitmap.
    types = [("icp4", 16), ("icp5", 32), ("ic11", 32), ("ic12", 64), ("ic07", 128),
             ("ic13", 256), ("ic08", 256), ("ic14", 512), ("ic09", 512), ("ic10", 1024)]
    body = b""
    for t, s in types:
        data = pngs[s]
        body += t.encode() + struct.pack(">I", len(data) + 8) + data
    return b"icns" + struct.pack(">I", len(body) + 8) + body


def ico(pngs):
    sizes = [16, 32, 48, 64, 128, 256]
    head = struct.pack("<HHH", 0, 1, len(sizes))
    off = 6 + 16 * len(sizes)
    dirs, blobs = b"", b""
    for s in sizes:
        data = pngs[s]
        dim = 0 if s >= 256 else s
        dirs += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), off)
        blobs += data
        off += len(data)
    return head + dirs + blobs


def main():
    pngs = {s: render(s) for s in SIZES}
    os.makedirs(os.path.join(PKG, "icons"), exist_ok=True)
    os.makedirs(os.path.join(PKG, "macos"), exist_ok=True)
    os.makedirs(os.path.join(PKG, "windows"), exist_ok=True)
    for s, data in pngs.items():
        with open(os.path.join(PKG, "icons", "beautalks-%d.png" % s), "wb") as f:
            f.write(data)
    with open(os.path.join(PKG, "macos", "beautalks.icns"), "wb") as f:
        f.write(icns(pngs))
    with open(os.path.join(PKG, "windows", "beautalks.ico"), "wb") as f:
        f.write(ico(pngs))
    print("icons written under", PKG)


if __name__ == "__main__":
    sys.exit(main())
