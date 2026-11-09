#!/usr/bin/env python3
# beautalks - radio programming software
# Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
#
# Builds the synthetic test images from scratch:
#   testdata/uv5rm.img  33664 bytes  UV-17Pro family (UV-5RM), descrambled
#   testdata/uv5re.img   6472 bytes  UV-5R family (8-byte ident + 0x1800 main + 0x140 aux)
#
# Structurally faithful (sizes, record layouts, ident, firmware tag at the
# real offsets) but holding only PUBLIC channels: FRS, GMRS, MURS, NOAA,
# national calling frequencies, a generic repeater pair, airband guard.
# Settings areas are synthesized (no bytes copied from any real radio).
#
#   python3 tools/make_fixtures.py testdata
#
# The tests assert the values listed here; change both together.

import os
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "testdata"

DCS = sorted([23, 25, 26, 31, 32, 36, 43, 47, 51, 53, 54, 65, 71, 72, 73, 74, 114, 115, 116, 122,
              125, 131, 132, 134, 143, 145, 152, 155, 156, 162, 165, 172, 174, 205, 212, 223, 225,
              226, 243, 244, 245, 246, 251, 252, 255, 261, 263, 265, 266, 271, 274, 306, 311, 315,
              325, 331, 332, 343, 346, 351, 356, 364, 365, 371, 411, 412, 413, 423, 431, 432, 445,
              446, 452, 454, 455, 462, 464, 465, 466, 503, 506, 516, 523, 526, 532, 546, 565, 606,
              612, 624, 627, 631, 632, 645, 654, 662, 664, 703, 712, 723, 731, 732, 734, 743, 754])


def lbcd(hz):
    v = hz // 10
    out = bytearray()
    for _ in range(4):
        two = v % 100
        out.append(((two // 10) << 4) | (two % 10))
        v //= 100
    return bytes(out)


def tone(t):
    """None | 69.3 (CTCSS) | 'D023N' | 'D754I'"""
    if t is None:
        return 0
    if isinstance(t, str):
        code = int(t[1:4])
        idx = DCS.index(code)
        return idx + (0x6A if t.endswith("I") else 1)
    return int(round(t * 10))


def u16(v):
    return bytes([v & 0xFF, (v >> 8) & 0xFF])


def mhz(x):
    return int(round(x * 1000000))


# (name, rx MHz, tx MHz or None for TX off, rx tone, tx tone, power index, wide, scan, bcl)
FRS = []
for i, f in enumerate([462.5625, 462.5875, 462.6125, 462.6375, 462.6625, 462.6875, 462.7125], 1):
    FRS.append(("FRS %d" % i, f, f, None, None, 1, True, True, False))
for i, f in enumerate([467.5625, 467.5875, 467.6125, 467.6375, 467.6625, 467.6875, 467.7125], 8):
    FRS.append(("FRS %d" % i, f, f, None, None, 1, False, True, False))
for i, f in enumerate([462.550, 462.575, 462.600, 462.625, 462.650, 462.675, 462.700, 462.725], 15):
    FRS.append(("FRS %d" % i, f, f, None, None, 0, True, True, False))

MURS = [("MURS %d" % i, f, f, None, None, 0, i >= 4, True, False)
        for i, f in enumerate([151.820, 151.880, 151.940, 154.570, 154.600], 1)]
NOAA = [("WX%d" % i, f, None, None, None, 0, True, False, False)
        for i, f in enumerate([162.550, 162.400, 162.475, 162.425, 162.450, 162.500, 162.525], 1)]

# ── UV-5RM (UV-17Pro layout, 1000 x 32 bytes at 0, numbered 1..1000) ────────

def rm_record(name, rx, tx, rxt, txt, power, wide, scan, bcl, scode=0):
    r = bytearray(32)
    r[0:4] = lbcd(mhz(rx))
    r[4:8] = lbcd(mhz(tx)) if tx is not None else b"\xff" * 4
    r[8:10] = u16(tone(rxt))
    r[10:12] = u16(tone(txt))
    r[12] = scode
    r[13] = 0
    r[14] = power & 3
    r[15] = (0 if wide else 0x40) | (0x08 if bcl else 0) | (0x04 if scan else 0)
    r[16:20] = b"\xff" * 4
    nb = name.encode()[:12]
    r[20:32] = nb + b"\xff" * (12 - len(nb))
    return bytes(r)


def make_rm():
    img = bytearray(b"\xff" * 0x8380)
    ch = {}
    n = 1
    for c in FRS:                     # 1..22
        ch[n] = c
        n += 1
    # 23..27 GMRS repeater pairs (input +5 MHz) with CTCSS 141.3, High
    for i, f in enumerate([462.550, 462.575, 462.600, 462.625, 462.650], 15):
        ch[n] = ("GMRS%dR" % i, f, f + 5.0, 141.3, 141.3, 0, True, True, False)
        n += 1
    for c in MURS:                    # 28..32
        ch[n] = c
        n += 1
    for c in NOAA:                    # 33..39, receive only, scan off
        ch[n] = c
        n += 1
    ch[40] = ("2M CALL", 146.520, 146.520, None, None, 2, True, True, False)      # Medium
    ch[41] = ("70CM CALL", 446.000, 446.000, None, None, 1, True, True, False)    # Low
    ch[42] = ("2M RPT", 146.940, 146.340, None, 100.0, 0, True, True, True)       # -0.6, tone, BCL
    ch[43] = ("DCS N", 446.100, 446.100, "D023N", "D023N", 1, False, True, False)
    ch[44] = ("DCS I", 446.150, 446.150, "D754I", "D754I", 1, False, True, False)
    ch[45] = ("NOSCAN", 446.200, 446.200, 67.0, 67.0, 2, True, False, False)
    ch[46] = ("LONGNAME1234", 145.500, 145.500, None, None, 0, True, True, False)  # 12 chars
    ch[47] = ("AIR GUARD", 121.500, None, None, None, 0, True, True, False)        # AM airband
    ch[60] = ("GAP 60", 147.420, 147.420, 88.5, None, 1, False, True, False)        # after a gap
    ch[1000] = ("LAST", 440.000, 445.000, None, None, 0, True, True, False)
    for num, c in ch.items():
        img[(num - 1) * 32:(num - 1) * 32 + 32] = rm_record(*c)
    # deleted channels: first byte FF, stale bytes left behind
    for num in (48, 52, 61):
        r = bytearray(rm_record("OLD %d" % num, 146.000 + num / 100, 146.000 + num / 100, None, None, 0, True, True, False))
        r[0] = 0xFF
        img[(num - 1) * 32:(num - 1) * 32 + 32] = r
    # 0x8000.. VFO A/B, settings, ANI, PTT-ID, names: synthesized
    base = 0x8000
    vfo = bytearray(b"\x00" * 32)
    vfo[0:8] = bytes([1, 4, 6, 5, 2, 0, 0, 0])
    img[base:base + 32] = vfo
    vfo[0:8] = bytes([4, 4, 6, 0, 0, 0, 0, 0])
    img[base + 32:base + 64] = vfo
    img[base + 64:base + 128] = bytes([3, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0] * 4)
    for i in range(10):              # bank names: spaces as the radio keeps them
        img[0x8240 + 16 * i:0x8240 + 16 * i + 12] = b" " * 12
    return img, ch

# ── UV-5RE (UV-5R layout) ────────────────────────────────────────────────────

def re_record(rx, tx, rxt, txt, power, wide, scan, bcl, scode=0):
    r = bytearray(16)
    r[0:4] = lbcd(mhz(rx))
    r[4:8] = lbcd(mhz(tx)) if tx is not None else b"\xff" * 4
    r[8:10] = u16(tone(rxt))
    r[10:12] = u16(tone(txt))
    r[12] = scode & 0x0F
    r[13] = 0
    r[14] = power & 3
    r[15] = (0x40 if wide else 0) | (0x08 if bcl else 0) | (0x04 if scan else 0)
    return bytes(r)


def make_re():
    img = bytearray(b"\xff" * (8 + 0x1800 + 0x140))
    img[0:8] = bytes([0xAA, 0x30, 0x76, 0x04, 0x00, 0x05, 0x20, 0xDD])
    ch = {}
    n = 1
    for c in FRS[:14]:                # 1..14
        ch[n] = c
        n += 1
    for i, f in enumerate([462.550, 462.575, 462.600, 462.625, 462.650, 462.675, 462.700, 462.725], 15):
        ch[n] = ("GMRS%d" % i, f, f, 141.3, 141.3, 0, True, True, False)   # 15..22
        n += 1
    for c in MURS[:3]:                # 23..25
        ch[n] = c
        n += 1
    for c in NOAA:                    # 26..32
        ch[n] = c
        n += 1
    ch[33] = ("2M CALL", 146.520, 146.520, None, None, 0, True, True, False)
    ch[34] = ("70CMCAL", 446.000, 446.000, None, None, 1, True, True, False)   # 7 chars
    ch[35] = ("2M RPT", 146.940, 146.340, None, 100.0, 0, True, True, True)
    ch[36] = ("DCS N", 446.100, 446.100, "D023N", "D023N", 1, False, True, False)
    ch[37] = ("DCS I", 446.150, 446.150, "D754I", "D754I", 1, False, True, False)
    ch[38] = ("NOSCAN", 446.200, 446.200, 67.0, 67.0, 0, True, False, False)
    ch[40] = ("GAP 40", 147.420, 147.420, 88.5, None, 1, False, True, False)
    ch[127] = ("LAST", 440.000, 445.000, None, None, 0, True, True, False)
    for idx, c in ch.items():
        name, rest = c[0], c[1:]
        img[8 + idx * 16:8 + idx * 16 + 16] = re_record(*rest)
        nb = name.encode()[:7]
        img[0x1008 + idx * 16:0x1008 + idx * 16 + 16] = nb + b"\xff" * (16 - len(nb))
    # deleted: first byte FF with stale bytes (and a stale name)
    for idx in (39, 45):
        r = bytearray(re_record(146.000 + idx / 100, 146.000 + idx / 100, None, None, 0, True, True, False))
        r[0] = 0xFF
        img[8 + idx * 16:8 + idx * 16 + 16] = r
    # 0x0E28 settings (image offset 0x0E30): synthesized, CHIRP-default-like
    s = 0x0E28 + 8
    img[s:s + 0x50] = bytes([3, 5, 0, 1, 0, 0, 5, 0, 1, 3, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0,
                             0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0] * 2)
    # VFO A/B (0x0F10/0x0F30): 146.52 and 446.00 as digit bytes
    for at, digits in ((0x0F10 + 8, [1, 4, 6, 5, 2, 0, 0, 0]), (0x0F30 + 8, [4, 4, 6, 0, 0, 0, 0, 0])):
        img[at:at + 8] = bytes(digits)
        img[at + 8:at + 32] = b"\x00" * 24
    # power-on / firmware messages (main 0x1828 / 0x1838)
    img[0x1828 + 8:0x1828 + 8 + 14] = b"BEAUTALKTEST  "
    # aux block (radio 0x1EC0.., image 0x1808..): firmware tag at radio 0x1EF0
    aux = 0x1808
    img[aux:aux + 0x140] = b"\x00" * 0x140
    img[aux + 0x30:aux + 0x30 + 14] = b"HN5RV011" + b"\xff" * 6
    img[aux + 0x20:aux + 0x2E] = b"BEAUTALKTEST  "
    # squelch tables and band limits (synthetic values)
    img[aux + 0xA0:aux + 0xAA] = bytes(range(0x10, 0x1A))
    img[aux + 0xC0:aux + 0xCA] = bytes(range(0x20, 0x2A))
    img[aux + 0x100:aux + 0x10A] = bytes([0, 0x01, 0x36, 0x01, 0x74, 0, 0x04, 0x00, 0x05, 0x20])
    # radio 0x1FCF (image aux + 0x10F) must not be 0xFF (that is the dropped-byte sign)
    img[aux + 0x10F] = 0x00
    return img, ch


def main():
    os.makedirs(OUT, exist_ok=True)
    rm, _ = make_rm()
    re_, _ = make_re()
    assert len(rm) == 33664 and len(re_) == 6472
    with open(os.path.join(OUT, "uv5rm.img"), "wb") as f:
        f.write(rm)
    with open(os.path.join(OUT, "uv5re.img"), "wb") as f:
        f.write(re_)
    print("wrote", os.path.join(OUT, "uv5rm.img"), "and", os.path.join(OUT, "uv5re.img"))


if __name__ == "__main__":
    main()
