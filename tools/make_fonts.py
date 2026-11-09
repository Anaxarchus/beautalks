#!/usr/bin/env python3
# beautalks - radio programming software
# Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
"""Font sidecars for the btui toolkit (ui/).

stb_truetype rasterises Inter's CFF outlines fine, but it cannot read Inter 4's
kerning (GPOS PairPos wrapped in Extension lookups) and it does no GSUB, so it
cannot reach the tabular figures (`tnum`) the channel table needs. This script
resolves both with fontTools at build time and writes a small binary sidecar
next to each font:

    <font>.btk  =  "BTK1" u32 npairs u32 nsubs
                   npairs x (u16 left_gid, u16 right_gid, i16 value_font_units)
                   nsubs  x (u16 from_gid, u16 to_gid)            # tnum

Kerning is resolved for every pair of glyphs whose code points are in COVER
(Latin-1, Latin Extended-A, general punctuation, arrows and a few symbols).

    python3 tools/make_fonts.py assets/fonts/Inter-Regular.otf ...
"""
import struct
import sys

from fontTools.ttLib import TTFont

COVER = list(range(0x20, 0x7F)) + list(range(0xA0, 0x180)) + list(range(0x2010, 0x2070)) + \
    [0x2190, 0x2191, 0x2192, 0x2193, 0x2212, 0x2713, 0x2715, 0x2116, 0x2122, 0x25CF]


def lookups_for(table, tag):
    idx = set()
    for fr in table.FeatureList.FeatureRecord:
        if fr.FeatureTag == tag:
            idx.update(fr.Feature.LookupListIndex)
    out = []
    for i in sorted(idx):
        lk = table.LookupList.Lookup[i]
        for st in lk.SubTable:
            t = lk.LookupType
            if t == 9 or t == 7:  # Extension (GPOS 9 / GSUB 7)
                t = st.ExtensionLookupType
                st = st.ExtSubTable
            out.append((t, st))
    return out


def value_x(vr):
    if vr is None:
        return 0
    return getattr(vr, "XAdvance", 0) or 0


def pair_value(subtables, left, right):
    for t, st in subtables:
        if t != 2:
            continue
        cov = st.Coverage.glyphs
        if left not in cov:
            continue
        if st.Format == 1:
            ps = st.PairSet[cov.index(left)]
            for rec in ps.PairValueRecord:
                if rec.SecondGlyph == right:
                    return value_x(rec.Value1)
        else:
            c1 = st.ClassDef1.classDefs.get(left, 0)
            c2 = st.ClassDef2.classDefs.get(right, 0)
            rec = st.Class1Record[c1].Class2Record[c2]
            v = value_x(rec.Value1)
            if v != 0:
                return v
            # a zero in a class table does not stop later subtables
    return 0


def main(paths):
    for path in paths:
        f = TTFont(path)
        order = f.getGlyphOrder()
        gid = {n: i for i, n in enumerate(order)}
        cmap = f.getBestCmap()
        names = sorted({cmap[cp] for cp in COVER if cp in cmap})
        kern = lookups_for(f["GPOS"].table, "kern")
        pairs = []
        for a in names:
            for b in names:
                v = pair_value(kern, a, b)
                if v != 0:
                    pairs.append((gid[a], gid[b], v))
        subs = []
        for t, st in lookups_for(f["GSUB"].table, "tnum"):
            if t == 1:
                for src, dst in st.mapping.items():
                    subs.append((gid[src], gid[dst]))
        with open(path + ".btk", "wb") as out:
            out.write(b"BTK1")
            out.write(struct.pack("<II", len(pairs), len(subs)))
            for l, r, v in pairs:
                out.write(struct.pack("<HHh", l, r, v))
            for a, b in subs:
                out.write(struct.pack("<HH", a, b))
        print(f"{path}.btk: {len(pairs)} kerning pairs, {len(subs)} tnum substitutions")


if __name__ == "__main__":
    main(sys.argv[1:])
