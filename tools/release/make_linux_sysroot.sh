#!/usr/bin/env bash
# beautalks - radio programming software
# Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
#
# Builds the minimal Linux x86_64 "sysroot" that ./build.sh --release uses to
# cross-compile the GUI for Linux with Dado's pinned zig (from a Mac, or from
# any Linux box). zig supplies glibc itself; this adds only what sokol_app
# needs on top of it, taken from pinned Ubuntu 22.04 (jammy) release-pocket
# packages, each checked against its SHA-256:
#
#   usr/include/{X11,GL,KHR}               headers (libx11-dev, x11proto-dev,
#                                          libxi-dev, libxcursor-dev,
#                                          libxfixes-dev, libxext-dev, libgl-dev)
#   usr/lib/x86_64-linux-gnu/lib*.so       link targets: libX11, libXi,
#                                          libXcursor, libGL (glvnd)
#   LICENSES/<package>.copyright           each package's Debian copyright file
#
# All of it is MIT/X11-style licensed (X.Org, libglvnd, Khronos headers).
# Nothing here ends up inside beautalks: the program only records
# "NEEDED libX11.so.6" etc., resolved on the user's machine at run time.
#
# Output (deterministic: sorted, mtime 0, owner 0, gzip -n):
#   tools/release/linux-sysroot-x86_64-<SYSROOT_ID>.tar.gz  (+ .sha256)
#
# Needs: bash, curl, sha256sum (or shasum), tar, gzip, and dpkg-deb, or ar +
# a tar that reads zstd (jammy's data.tar is zstd). Run it on Linux:
#   tools/release/make_linux_sysroot.sh
# The owner does not need to run this: the tarball is committed, and
# build.sh only unpacks it.
set -euo pipefail

SYSROOT_ID="jammy-1"
MIRRORS=("http://archive.ubuntu.com/ubuntu" "http://old-releases.ubuntu.com/ubuntu")

# package  pool path  sha256   (Ubuntu 22.04 "jammy" release pocket, amd64)
PKGS=(
"libx11-dev     pool/main/libx/libx11/libx11-dev_1.7.5-1_amd64.deb                4b06bfd5ad9409ade5dd873ddd732d1c1f90aa1581e545c432a60303b08e980e"
"libx11-6       pool/main/libx/libx11/libx11-6_1.7.5-1_amd64.deb                  027e5e6c748c9a826125df013284caa78ca04213aba1967cd8c8067165e58020"
"x11proto-dev   pool/main/x/xorgproto/x11proto-dev_2021.5-1_all.deb               7cb2471a23ea50e197cec019d0596840b6ddd714e8deb75e427472e820e83548"
"libxi-dev      pool/main/libx/libxi/libxi-dev_1.8-1build1_amd64.deb              0de737897ef7238346e7d6bcd40286c1f414b455f74470e8da4bf95dd8c8553d"
"libxi6         pool/main/libx/libxi/libxi6_1.8-1build1_amd64.deb                 47662736cca4be456fd42a5f0a9d3bed8a5cfad4ee08b809a95dde6004daf275"
"libxcursor-dev pool/main/libx/libxcursor/libxcursor-dev_1.2.0-2build4_amd64.deb  7f45bdccf60c15056a08aaac5ce46a88f415ccb20a1b78d933fbc7138463a4a9"
"libxcursor1    pool/main/libx/libxcursor/libxcursor1_1.2.0-2build4_amd64.deb     4ea5fa73bc989f5b8cbeecfdb650e142920859837279d0a64891cb80aff9dfc8"
"libxfixes-dev  pool/main/libx/libxfixes/libxfixes-dev_6.0.0-1_amd64.deb          2504131bb60678e238dc6dc9af244793263ee245d420b0e43e8f0243b26de024"
"libxext-dev    pool/main/libx/libxext/libxext-dev_1.3.4-1build1_amd64.deb        3ecc871072ee30cdf166409b8e264c631b917f93bc340d54c0a47dec9cca2147"
"libgl-dev      pool/main/libg/libglvnd/libgl-dev_1.4.0-1_amd64.deb               6cda0891ca38204ab3a9a2a9279ecb99989ab100d6e48101306efce28f0759a2"
"libgl1         pool/main/libg/libglvnd/libgl1_1.4.0-1_amd64.deb                  4fb2bbff94bb1a59bbdb40041e7a8ab58db2a003a151f4055357af03f0b78666"
)
# link name -> versioned file in the packages above
LIBS=(libX11.so.6 libXi.so.6 libXcursor.so.1 libGL.so.1)

HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$HERE/linux-sysroot-x86_64-$SYSROOT_ID.tar.gz}"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/bt-sysroot.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

say() { printf '==> %s\n' "$*"; }
sha() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }

extract_deb() { # deb dest
    if command -v dpkg-deb >/dev/null; then dpkg-deb -x "$1" "$2"; return; fi
    local t; t="$(mktemp -d "$WORK/ar.XXXX")"
    (cd "$t" && ar x "$1")
    tar -xf "$t"/data.tar.* -C "$2"
}

ROOT="$WORK/root/linux-sysroot"
mkdir -p "$WORK/debs" "$WORK/x" "$ROOT/usr/include" "$ROOT/usr/lib/x86_64-linux-gnu" "$ROOT/LICENSES"
for line in "${PKGS[@]}"; do
    read -r name pool want <<<"$line"
    deb="$WORK/debs/$(basename "$pool")"
    ok=""
    for m in "${MIRRORS[@]}"; do
        if curl -fsSL --retry 2 -o "$deb" "$m/$pool"; then ok=1; break; fi
    done
    [ -n "$ok" ] || { echo "cannot download $pool" >&2; exit 1; }
    got="$(sha "$deb")"
    [ "$got" = "$want" ] || { echo "SHA-256 mismatch for $pool: $got (want $want)" >&2; exit 1; }
    say "$name ok"
    mkdir -p "$WORK/x/$name"
    extract_deb "$deb" "$WORK/x/$name"
    cp "$WORK/x/$name/usr/share/doc/$name/copyright" "$ROOT/LICENSES/$name.copyright"
    if [ -d "$WORK/x/$name/usr/include" ]; then
        cp -R "$WORK/x/$name/usr/include/." "$ROOT/usr/include/"
    fi
done
# Keep only what sokol_app includes (X11, GL, KHR); drop pkg-config etc.
for d in "$ROOT/usr/include"/*; do
    case "$(basename "$d")" in X11|GL|KHR) ;; *) rm -rf "$d" ;; esac
done
for so in "${LIBS[@]}"; do
    f="$(find "$WORK/x" -name "$so*" -type f | head -1)"
    [ -n "$f" ] || { echo "no $so in the packages" >&2; exit 1; }
    cp "$f" "$ROOT/usr/lib/x86_64-linux-gnu/$so"
    ln -sf "$so" "$ROOT/usr/lib/x86_64-linux-gnu/${so%%.so.*}.so"
done
cat > "$ROOT/README" <<EOF
beautalks Linux x86_64 cross-compile sysroot ($SYSROOT_ID), made by
tools/release/make_linux_sysroot.sh from pinned Ubuntu 22.04 packages:
$(for l in "${PKGS[@]}"; do read -r n p _ <<<"$l"; echo "  $(basename "$p")"; done)
Headers and link targets only (zig supplies glibc). Licences: LICENSES/.
Use: DADO_CFLAGS=-I<this>/usr/include DADO_LDFLAGS=-L<this>/usr/lib/x86_64-linux-gnu
EOF

# Deterministic tarball.
find "$ROOT" -exec touch -h -d @0 {} + 2>/dev/null || find "$ROOT" -exec touch -h -t 197001010000 {} +
( cd "$WORK/root" && LC_ALL=C find linux-sysroot -print | LC_ALL=C sort > "$WORK/list" )
if tar --version 2>/dev/null | grep -q GNU; then
    tar -C "$WORK/root" --owner=0 --group=0 --numeric-owner --mtime=@0 --no-recursion -cf "$WORK/s.tar" -T "$WORK/list"
else
    tar -C "$WORK/root" --uid 0 --gid 0 -n -cf "$WORK/s.tar" -T "$WORK/list"
fi
gzip -n -9 -c "$WORK/s.tar" > "$OUT"
sha "$OUT" | sed "s|\$|  $(basename "$OUT")|" > "$OUT.sha256"
say "wrote $OUT ($(wc -c < "$OUT" | tr -d ' ') bytes)"
cat "$OUT.sha256"
