#!/usr/bin/env bash
# beautalks - radio programming software
# Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
#
# The one build script (docs/RELEASING.md has the whole story).
#
#   ./build.sh [PKG] [-o OUT]          dev build of PKG (default: the GUI) for this machine
#   ./build.sh --target linux|windows [PKG] [-o OUT]
#                                      cross-build PKG with Dado's pinned zig (release tier)
#   ./build.sh --release [VERSION]     build every platform, package, tag, push and publish
#                                      the GitHub release (run it on the Mac)
#       --dry-run         build and package into dist/<version>/ only: no tag, no push,
#                         no upload (also allowed with a dirty tree)
#       --skip-tests      do not run `dado test` first
#       --targets LIST    comma list of mac,windows,linux (default: all three on a Mac,
#                         windows,linux elsewhere; a real release wants all three)
#       --mac-arch A      universal (default: arm64 + x86_64, falling back to arm64 with a
#                         warning if the Intel half does not build) or arm64
#       --no-dmg          skip the macOS disk image (the zip is always made)
#       --yes             do not ask before tagging and publishing
#
# Environment: BEAUTALKS_GUI_PKG (default below), BEAUTALKS_REPO (owner/repo),
# BEAUTALKS_MIN_MACOS (default 11.0), BEAUTALKS_MAC_DADO_FLAGS (e.g. --no-lto),
# ZIG (the pinned zig, found from `dado` otherwise).
#
# Bash 3.2 (macOS's /bin/bash) compatible on purpose.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# ── settings ──────────────────────────────────────────────────────────────────
# The desktop program (BEAUTALKS_GUI_PKG overrides it for experiments; a
# release refuses anything but app/).
GUI_PKG="${BEAUTALKS_GUI_PKG:-app}"
CLI_PKG="cli"
TEST_PKGS="radio cli driverhost updater ui"
REPO="${BEAUTALKS_REPO:-Anaxarchus/beautalks}"
MIN_MACOS="${BEAUTALKS_MIN_MACOS:-11.0}"
SYSROOT_ID="jammy-1"
SYSROOT_TGZ="$ROOT/tools/release/linux-sysroot-x86_64-$SYSROOT_ID.tar.gz"
WIN_DADO_TARGET="x86_64-w64-mingw32"
LIN_DADO_TARGET="x86_64-pc-linux-gnu"
# zig's target for Linux. No glibc suffix (x86_64-linux-gnu.2.31): zig cc
# -dumpmachine rejects one, and the script engine's build asks it. The default
# glibc floor of the pinned zig gives binaries that need glibc 2.29.
LIN_ZIG_TARGET="x86_64-linux-gnu"
PY="${PYTHON:-python3}"
# Extra `dado build` flags for the macOS release builds, e.g. --no-lto if Apple
# clang's link-time optimisation gives trouble (BEAUTALKS_MAC_DADO_FLAGS).
MAC_DADO_FLAGS="${BEAUTALKS_MAC_DADO_FLAGS:-}"
# Where beautalks.exe sits inside the Windows zip: "" is the top of the folder
# (radio.find_shipped looks beside the program). "bin" would put it in bin\.
WIN_BIN=""

HOST="$(uname -s)"
STEP=0
WARNINGS=""

# ── output ────────────────────────────────────────────────────────────────────
step() { STEP=$((STEP + 1)); printf '\n==> [%d] %s\n' "$STEP" "$*"; }
info() { printf '    %s\n' "$*"; }
warn() { printf '    WARNING: %s\n' "$*" >&2; WARNINGS="$WARNINGS
  - $*"; }
die()  { printf '\nERROR: %s\n' "$*" >&2; exit 1; }
show() { printf '    $'; printf ' %q' "$@"; printf '\n'; }

# run LOG CMD...: print the command, send its output to LOG, show the tail on failure.
run() {
    local log=$1; shift
    show "$@"
    if "$@" >"$log" 2>&1; then return 0; fi
    printf '    ---- last lines of %s ----\n' "$log" >&2
    tail -n 25 "$log" | sed 's/^/    | /' >&2
    return 1
}

realpath_py() { "$PY" -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$1"; }
sha256_of() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }

# ── the toolchain ─────────────────────────────────────────────────────────────
need() { command -v "$1" >/dev/null 2>&1 || die "$1 is not on PATH. $2"; }

# Dado's install directory (holds dadoc and zig/<version>/zig), from `dado` on PATH.
dado_home() {
    local d; d="$(realpath_py "$(command -v dado)")"
    d="$(dirname "$(dirname "$d")")"
    printf '%s' "$d"
}
find_zig() {
    if [ -n "${ZIG:-}" ]; then printf '%s' "$ZIG"; return; fi
    local z
    for z in "$(dado_home)"/zig/*/zig; do
        if [ -x "$z" ]; then printf '%s' "$z"; return; fi
    done
    command -v zig 2>/dev/null || true
}
find_dadoc() {
    if [ -x "$(dado_home)/dadoc" ]; then printf '%s' "$(dado_home)/dadoc"; return; fi
    command -v dadoc 2>/dev/null || true
}

# A directory put first on PATH for cross builds:
#  * `brew` that answers nothing: the Dado driver adds Homebrew's -I/-L to
#    every build when brew is on PATH, cross builds too (rc.9), and macOS
#    headers or dylibs must never reach a Linux or Windows build;
#  * `zig`, the pinned one: the script engine's build (tools/quickjs/build.sh)
#    indexes its archive with `zig ar` only when zig is on PATH, and Apple's
#    ar cannot index ELF or COFF objects;
#  * `sha256sum`, if missing, from shasum (the engine build's cache key).
make_shims() {
    local dir=$1 zig
    mkdir -p "$dir"
    printf '#!/bin/sh\nexit 1\n' > "$dir/brew"
    chmod +x "$dir/brew"
    zig="$(find_zig)"
    [ -n "$zig" ] || die "cannot find Dado's pinned zig (looked in $(dado_home)/zig/*/zig). Set ZIG=/path/to/zig."
    ln -sf "$zig" "$dir/zig"
    if ! command -v sha256sum >/dev/null 2>&1; then
        printf '#!/bin/sh\nexec shasum -a 256 "$@"\n' > "$dir/sha256sum"
        chmod +x "$dir/sha256sum"
    fi
}

# The Linux sysroot (tools/release/make_linux_sysroot.sh), unpacked once into build/.
linux_sysroot() {
    local dest="$ROOT/build/linux-sysroot-$SYSROOT_ID"
    if [ ! -f "$dest/linux-sysroot/README" ]; then
        [ -f "$SYSROOT_TGZ" ] || die "missing $SYSROOT_TGZ (make it with tools/release/make_linux_sysroot.sh on Linux)"
        local want got
        want="$(cut -d' ' -f1 < "$SYSROOT_TGZ.sha256")"
        got="$(sha256_of "$SYSROOT_TGZ")"
        [ "$want" = "$got" ] || die "$SYSROOT_TGZ does not match its .sha256 ($got)"
        rm -rf "$dest"; mkdir -p "$dest"
        tar -xzf "$SYSROOT_TGZ" -C "$dest"
    fi
    printf '%s' "$dest/linux-sysroot"
}

# `-D updater.APP_VERSION=<version>`: the version the programs report
# (`beautalks-cli version`) and the driver updater compares with min_app.
# Unquoted: quotes would become part of the string.
BUILD_VERSION=""
version_define() {
    local v="${BUILD_VERSION:-}"
    [ -n "$v" ] || v="$(tr -d ' \t\r\n' < "$ROOT/VERSION" 2>/dev/null || true)"
    [ -z "$v" ] || printf '%s' "-D updater.APP_VERSION=$v"
}

# check_version LABEL CMD...: CMD must print "beautalks <BUILD_VERSION>".
check_version() {
    local label=$1 got; shift
    got="$("$@" version 2>/dev/null | tr -d '\r' | head -1 || true)"
    if [ "$got" = "beautalks $BUILD_VERSION" ]; then info "$label: '$got'"
    else die "$label reports '$got', expected 'beautalks $BUILD_VERSION'"; fi
}

# ── builds ────────────────────────────────────────────────────────────────────
# Each: PKG OUT LOG [extra]. Every one names its own DADO_CFLAGS/LDFLAGS/TARGET
# so nothing from the caller's environment leaks across platforms.

# macOS, Apple clang. -x none -ObjC: Dado rc.9 repeats sokol's `-x objective-c`
# on the link line before the objects, so clang reads them as source; `-x none`
# puts it back and -ObjC keeps the sources Objective-C (zig cc ignores -ObjC).
build_mac() { # PKG OUT LOG ARCH
    local pkg=$1 out=$2 log=$3 arch=$4 cflags="-x none -ObjC" ldflags="" tgt=""
    if [ "$arch" != "$(native_mac_arch)" ]; then
        cflags="$cflags -arch $arch"; ldflags="-arch $arch"; tgt="$arch-apple-darwin"
    fi
    run "$log" env -u ZIG_TARGET MACOSX_DEPLOYMENT_TARGET="$MIN_MACOS" \
        DADO_CFLAGS="$cflags" DADO_LDFLAGS="$ldflags" ${tgt:+DADO_TARGET=$tgt} \
        dado build "$pkg" --release --cc clang $MAC_DADO_FLAGS $(version_define) -o "$out"
}
native_mac_arch() {
    if [ "$(sysctl -n hw.optional.arm64 2>/dev/null || echo 0)" = 1 ]; then echo arm64; else echo x86_64; fi
}

build_windows() { # PKG OUT LOG SHIMS [LDFLAGS]
    local pkg=$1 out=$2 log=$3 shims=$4 ldflags=${5:-}
    run "$log" env -u ZIG_TARGET PATH="$shims:$PATH" DADO_TARGET="$WIN_DADO_TARGET" \
        DADO_CFLAGS="" DADO_LDFLAGS="$ldflags" \
        dado build "$pkg" --release $(version_define) -o "$out"
}

build_linux() { # PKG OUT LOG SHIMS
    local pkg=$1 out=$2 log=$3 shims=$4 sr
    sr="$(linux_sysroot)"
    run "$log" env PATH="$shims:$PATH" DADO_TARGET="$LIN_DADO_TARGET" ZIG_TARGET="$LIN_ZIG_TARGET" \
        DADO_CFLAGS="-I$sr/usr/include" DADO_LDFLAGS="-L$sr/usr/lib/x86_64-linux-gnu -s" \
        dado build "$pkg" --release $(version_define) -o "$out"
}

# beautalks.exe's resources (icon + version tab), compiled by `zig rc`.
windows_res() { # VERSION OUTDIR -> path of the .res, or nothing
    local v=$1 dir=$2 zig base commas
    zig="$(find_zig)"
    [ -n "$zig" ] || { warn "no zig: beautalks.exe gets no icon"; return 0; }
    mkdir -p "$dir"
    base="${v%%-*}"
    commas="$(printf '%s' "$base" | tr '.' ','),0"
    cp "$ROOT/packaging/windows/beautalks.ico" "$dir/"
    "$PY" "$ROOT/tools/release/package.py" fill "$ROOT/packaging/windows/beautalks.rc.in" "$dir/beautalks.rc" \
        "VERSION=$v" "VERSION_COMMAS=$commas"
    if (cd "$dir" && "$zig" rc /fo beautalks.res beautalks.rc) >"$dir/rc.log" 2>&1; then
        printf '%s' "$dir/beautalks.res"
    else
        warn "zig rc failed ($dir/rc.log): beautalks.exe gets no icon"
    fi
}

# ── dev mode ──────────────────────────────────────────────────────────────────
dev_build() {
    local target="" pkg="" out=""
    while [ $# -gt 0 ]; do
        case $1 in
            --target) target=$2; shift 2;;
            --target=*) target=${1#--target=}; shift;;
            -o) out=$2; shift 2;;
            -h|--help) awk 'NR >= 4 && /^#/ { sub(/^# ?/, ""); print; next } NR >= 4 { exit }' "$0"; exit 0;;
            -*) die "unknown option $1 (./build.sh --help)";;
            *) pkg=$1; shift;;
        esac
    done
    pkg="${pkg:-$GUI_PKG}"
    pkg="${pkg%/}"
    [ -d "$pkg" ] || die "no package $pkg"
    need dado "Install Dado (see docs/RELEASING.md)."
    local name; name="$(basename "$pkg")"
    # Dev names: the app is build/beautalks-app, the CLI build/beautalks.
    case $name in app) name=beautalks-app;; cli) name=beautalks;; esac
    case "$target" in
        "")
            out="${out:-build/$name}"
            mkdir -p "$(dirname "$out")"
            if [ "$HOST" = Darwin ]; then
                step "dev build of $pkg for macOS (Apple clang)"
                DADO_CFLAGS="-x none -ObjC ${DADO_CFLAGS:-}" exec dado build "$pkg" --cc clang $(version_define) -o "$out"
            fi
            step "dev build of $pkg for this machine"
            exec dado build "$pkg" $(version_define) -o "$out"
            ;;
        linux|windows)
            local shims="$ROOT/build/.release-shims" log
            make_shims "$shims"
            if [ "$target" = linux ]; then out="${out:-build/linux-x64/$name}"; else out="${out:-build/windows-x64/$name.exe}"; fi
            mkdir -p "$(dirname "$out")"
            log="$(dirname "$out")/$name.build.log"
            step "cross build of $pkg for $target -> $out"
            if [ "$target" = linux ]; then build_linux "$pkg" "$out" "$log" "$shims" || die "the build failed (log: $log)"
            else build_windows "$pkg" "$out" "$log" "$shims" || die "the build failed (log: $log)"; fi
            info "built $out (log: $log)"
            ;;
        *) die "--target is linux or windows (a dev build for this machine takes no --target)";;
    esac
}

# ── release mode ──────────────────────────────────────────────────────────────
release() {
    local version="" dry=0 skip_tests=0 targets="" mac_arch=universal dmg=1 yes=0
    while [ $# -gt 0 ]; do
        case $1 in
            --dry-run) dry=1; shift;;
            --skip-tests) skip_tests=1; shift;;
            --targets) targets=$2; shift 2;;
            --targets=*) targets=${1#--targets=}; shift;;
            --mac-arch) mac_arch=$2; shift 2;;
            --no-dmg) dmg=0; shift;;
            --yes|-y) yes=1; shift;;
            -*) die "unknown option $1 (./build.sh --help)";;
            *) [ -z "$version" ] || die "two versions given: $version and $1"; version=$1; shift;;
        esac
    done
    if [ -z "$targets" ]; then
        if [ "$HOST" = Darwin ]; then targets="mac,windows,linux"; else targets="windows,linux"; fi
    fi
    local do_mac=0 do_win=0 do_lin=0 t
    for t in $(printf '%s' "$targets" | tr ',' ' '); do
        case $t in mac|macos) do_mac=1;; windows|win) do_win=1;; linux) do_lin=1;; *) die "unknown target $t";; esac
    done
    case $mac_arch in universal|arm64) ;; *) die "--mac-arch is universal or arm64";; esac

    # ── 1. preflight
    step "preflight"
    need dado "Install Dado 1.0.0-rc.9 (docs/RELEASING.md)."
    need git "Install Xcode's command line tools: xcode-select --install"
    need "$PY" "Install Xcode's command line tools (python3): xcode-select --install"
    [ -z "$version" ] && version="$(tr -d ' \t\r\n' < VERSION)"
    printf '%s' "$version" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$' \
        || die "version '$version' is not MAJOR.MINOR.PATCH[-suffix]"
    local tag="v$version" prerelease=0
    case $version in *-*) prerelease=1;; esac
    info "version $version, tag $tag, repo $REPO"
    info "targets: $targets   GUI package: $GUI_PKG   CLI package: $CLI_PKG"
    [ -d "$GUI_PKG" ] || die "GUI package $GUI_PKG/ does not exist"
    if [ "$GUI_PKG" != app ]; then
        [ "$dry" = 1 ] || die "a release ships app/, not $GUI_PKG/ (unset BEAUTALKS_GUI_PKG)"
        warn "the GUI is $GUI_PKG/, not app/ (allowed with --dry-run only)"
    fi
    if [ "$do_mac" = 1 ] && [ "$HOST" != Darwin ]; then
        die "the macOS build needs a Mac (Apple clang and SDK). Here, use --targets windows,linux"
    fi
    if [ "$dry" = 0 ] && { [ "$do_mac" = 0 ] || [ "$do_win" = 0 ] || [ "$do_lin" = 0 ]; }; then
        warn "publishing without every platform (targets: $targets)"
    fi
    local file_ver
    file_ver="$(tr -d ' \t\r\n' < VERSION)"
    [ "$file_ver" = "$version" ] || {
        if [ "$dry" = 1 ]; then warn "VERSION says $file_ver, building $version"; else die "VERSION says $file_ver but you asked for $version: edit VERSION and commit first"; fi; }
    git rev-parse --git-dir >/dev/null 2>&1 || die "not a git checkout"
    local commit dirty
    commit="$(git rev-parse HEAD)"
    dirty="$(git status --porcelain --untracked-files=no)"
    if [ -n "$dirty" ]; then
        if [ "$dry" = 1 ]; then warn "the tree has uncommitted changes (allowed with --dry-run)"
        else printf '%s\n' "$dirty" | sed 's/^/    /'; die "the git tree is dirty: commit or stash first"; fi
    fi
    local untracked
    untracked="$(git status --porcelain | grep '^??' | grep -v -e ' dist/' -e ' build/' || true)"
    [ -z "$untracked" ] || warn "untracked files (not in the release, not committed): $(printf '%s' "$untracked" | tr '\n' ' ')"
    if git rev-parse -q --verify "refs/tags/$tag" >/dev/null; then
        [ "$dry" = 1 ] && warn "tag $tag already exists locally" || die "tag $tag already exists locally"
    fi
    if [ "$dry" = 0 ]; then
        need gh "brew install gh, then: gh auth login"
        gh auth status >/dev/null 2>&1 || die "gh is not logged in: gh auth login"
        if [ -n "$(git ls-remote --tags origin "refs/tags/$tag" 2>/dev/null)" ]; then die "tag $tag already exists on origin"; fi
        if gh release view "$tag" --repo "$REPO" >/dev/null 2>&1; then die "a release $tag already exists on $REPO"; fi
        local url; url="$(git remote get-url origin 2>/dev/null || true)"
        case $url in *"$REPO"|*"$REPO.git") ;; *) warn "origin is $url, releases go to $REPO";; esac
        git fetch -q origin 2>/dev/null || warn "git fetch origin failed"
        if [ -z "$(git branch -r --contains HEAD 2>/dev/null)" ]; then
            warn "HEAD ($commit) is not on any pushed branch: the tag will carry it, but push your branch too"
        fi
    fi
    BUILD_VERSION="$version"
    info "programs built with $(version_define)"
    export SOURCE_DATE_EPOCH; SOURCE_DATE_EPOCH="$(git log -1 --format=%ct)"
    local dado_ver; dado_ver="$(dado --version 2>/dev/null | sed -n 's/^dadoc //p' | head -1)"
    info "dado: ${dado_ver:-unknown}   zig: $(find_zig)   commit: $commit"

    local DIST="$ROOT/dist/$version"
    local B="$DIST/build" STAGE="$DIST/stage" OUT="$DIST/assets" LOGS="$DIST/logs" SHIMS="$DIST/.shims"
    rm -rf "$DIST"
    mkdir -p "$B" "$STAGE" "$OUT" "$LOGS"
    make_shims "$SHIMS"
    info "output: $DIST"

    # ── 2. tests
    if [ "$skip_tests" = 1 ]; then
        step "tests skipped (--skip-tests)"
        warn "tests were skipped"
    else
        step "tests: dado test $TEST_PKGS"
        local p
        for p in $TEST_PKGS; do
            info "dado test $p"
            run "$LOGS/test-$p.log" dado test "$p" || die "dado test $p failed (log: $LOGS/test-$p.log)"
        done
    fi

    # ── 3. driver bundle (the same release carries it: docs/DRIVERS.md)
    step "driver bundle for $tag (drivers/release.py)"
    local dadoc compile_flag=""
    dadoc="$(find_dadoc)"
    if [ -z "$dadoc" ]; then warn "no dadoc: shipping the committed drivers/engines/*.js"; compile_flag="--no-compile"; fi
    if ! run "$LOGS/drivers.log" "$PY" drivers/release.py --release "$tag" --out "$B/drivers-assets" \
            --no-repo-manifest ${dadoc:+--dadoc "$dadoc"} $compile_flag; then
        [ -z "$compile_flag" ] || die "drivers/release.py failed"
        warn "compiling the engines failed: shipping drivers/engines/*.js as they are (--no-compile)"
        run "$LOGS/drivers.log" "$PY" drivers/release.py --release "$tag" --out "$B/drivers-assets" \
            --no-repo-manifest --no-compile || die "drivers/release.py --no-compile failed"
    fi
    if [ -n "$(git status --porcelain --untracked-files=no -- drivers)" ]; then
        local msg="dadoc compiled drivers/engines/*.js differently from what is committed"
        if [ "$dry" = 1 ]; then warn "$msg"; else
            git --no-pager diff --stat -- drivers | sed 's/^/    /'
            die "$msg: commit the new .js (the release must match its tag), then run again"; fi
    fi
    cp "$B/drivers-assets"/* "$OUT/"
    info "$(ls "$B/drivers-assets" | wc -l | tr -d ' ') bundle assets"

    # The data every package carries beside the program.
    local SHARE="$B/share"
    mkdir -p "$SHARE/drivers/engines"
    cp -R assets models data "$SHARE/"
    cp drivers/engines/*.js drivers/engines/*.dados "$SHARE/drivers/engines/"
    cp "$B/drivers-assets/drivers-manifest.json" "$SHARE/drivers/manifest.json"
    find "$SHARE" -name '.DS_Store' -exec rm -f {} + 2>/dev/null || true
    local license=""
    for license in LICENSE LICENSE.txt LICENSE.md COPYING; do [ -f "$license" ] && break; license=""; done
    [ -n "$license" ] || die "no LICENSE file at the repo root: every package must carry the GPLv3 text"

    local mac_zip="" mac_dmg="" win_zip="" lin_tar="" universal=0 notes_extra=""

    # ── 4. macOS
    if [ "$do_mac" = 1 ]; then
        step "macOS: build ($mac_arch, macOS $MIN_MACOS+)"
        local native; native="$(native_mac_arch)"
        [ "$native" = arm64 ] || warn "this Mac is not Apple silicon: the arm64 half is cross-built"
        local archs="arm64" a
        [ "$mac_arch" = universal ] && archs="arm64 x86_64"
        local built_archs=""
        for a in $archs; do
            mkdir -p "$B/mac-$a"
            info "$GUI_PKG for $a"
            if build_mac "$GUI_PKG" "$B/mac-$a/beautalks" "$LOGS/mac-$a-gui.log" "$a" \
               && { info "$CLI_PKG for $a"; build_mac "$CLI_PKG" "$B/mac-$a/beautalks-cli" "$LOGS/mac-$a-cli.log" "$a"; }; then
                built_archs="$built_archs $a"
            else
                [ "$a" = arm64 ] && die "the arm64 macOS build failed"
                warn "the x86_64 (Intel) macOS build failed: shipping Apple silicon only (see $LOGS/mac-$a-*.log)"
            fi
        done
        mkdir -p "$B/mac"
        local bin
        for bin in beautalks beautalks-cli; do
            if [ "$built_archs" = " arm64 x86_64" ]; then
                lipo -create -output "$B/mac/$bin" "$B/mac-arm64/$bin" "$B/mac-x86_64/$bin"
            else
                cp "$B/mac-arm64/$bin" "$B/mac/$bin"
            fi
        done
        local arch_label=arm64
        if [ "$built_archs" = " arm64 x86_64" ]; then universal=1; arch_label=universal; fi
        info "$(lipo -archs "$B/mac/beautalks" 2>/dev/null || file "$B/mac/beautalks")"
        check_version "macOS beautalks-cli version" "$B/mac/beautalks-cli"

        step "macOS: beautalks.app"
        local APP="$STAGE/mac/beautalks.app"
        mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
        "$PY" tools/release/package.py fill packaging/macos/Info.plist.in "$APP/Contents/Info.plist" \
            "VERSION=${version%%-*}" "BUILD=$version" "MIN_MACOS=$MIN_MACOS"
        plutil -lint "$APP/Contents/Info.plist" >/dev/null || die "Info.plist does not lint"
        printf 'APPL????' > "$APP/Contents/PkgInfo"
        cp "$B/mac/beautalks" "$B/mac/beautalks-cli" "$APP/Contents/MacOS/"
        cp packaging/macos/beautalks.icns "$APP/Contents/Resources/"
        cp -R "$SHARE"/assets "$SHARE"/models "$SHARE"/data "$SHARE"/drivers "$APP/Contents/Resources/"
        cp "$license" "$APP/Contents/Resources/LICENSE"
        xattr -cr "$APP" 2>/dev/null || true
        mac_zip="beautalks-$version-macos-$arch_label.zip"
        show ditto -c -k --keepParent "$APP" "$OUT/$mac_zip"
        ditto -c -k --keepParent "$APP" "$OUT/$mac_zip"
        if [ "$dmg" = 1 ]; then
            local DMGSRC="$STAGE/mac-dmg"
            mkdir -p "$DMGSRC"
            ditto "$APP" "$DMGSRC/beautalks.app"
            ln -s /Applications "$DMGSRC/Applications"
            mac_dmg="beautalks-$version-macos-$arch_label.dmg"
            if ! run "$LOGS/dmg.log" hdiutil create -volname "beautalks $version" -srcfolder "$DMGSRC" \
                    -ov -format UDZO "$OUT/$mac_dmg"; then
                warn "hdiutil failed: no disk image this time (the zip is complete)"; mac_dmg=""
            fi
        fi
        [ "$universal" = 1 ] || notes_extra="$notes_extra|The macOS build is for Apple silicon only this time."
    fi

    # ── 5. Windows
    if [ "$do_win" = 1 ]; then
        step "Windows x64: cross build with zig ($WIN_DADO_TARGET)"
        mkdir -p "$B/windows"
        local res; res="$(windows_res "$version" "$B/windows-res")"
        info "$GUI_PKG -> beautalks.exe (GUI subsystem${res:+, icon})"
        build_windows "$GUI_PKG" "$B/windows/beautalks.exe" "$LOGS/windows-gui.log" "$SHIMS" \
            "${res:+$res }-Wl,--subsystem,windows" || die "the Windows build of $GUI_PKG failed"
        info "$CLI_PKG -> beautalks-cli.exe"
        build_windows "$CLI_PKG" "$B/windows/beautalks-cli.exe" "$LOGS/windows-cli.log" "$SHIMS" \
            || die "the Windows build of $CLI_PKG failed"
        if command -v wine >/dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
            check_version "Windows beautalks-cli.exe version (Wine)" env WINEDEBUG=-all wine "$B/windows/beautalks-cli.exe"
        else
            info "(Windows beautalks-cli.exe version not checked: no Wine here)"
        fi
        step "Windows x64: package"
        # Flat by default (WIN_BIN=""): find_shipped looks beside the program.
        local W="$STAGE/windows/beautalks-$version-windows-x64" WB
        WB="$W${WIN_BIN:+/$WIN_BIN}"
        mkdir -p "$WB"
        cp "$B/windows/beautalks.exe" "$WB/"
        cp "$B/windows/beautalks-cli.exe" "$WB/"
        cp -R "$SHARE"/assets "$SHARE"/models "$SHARE"/data "$SHARE"/drivers "$W/"
        cp "$license" "$W/LICENSE.txt"
        "$PY" tools/release/package.py readme windows "$version" "$W/README.txt" --exe "${WIN_BIN:+$WIN_BIN\\}beautalks.exe"
        win_zip="beautalks-$version-windows-x64.zip"
        "$PY" tools/release/package.py archive zip "$W" "$OUT/$win_zip" | sed 's/^/    /'
    fi

    # ── 6. Linux
    if [ "$do_lin" = 1 ]; then
        step "Linux x64: cross build with zig ($LIN_ZIG_TARGET + sysroot $SYSROOT_ID)"
        mkdir -p "$B/linux"
        info "$GUI_PKG -> bin/beautalks"
        build_linux "$GUI_PKG" "$B/linux/beautalks" "$LOGS/linux-gui.log" "$SHIMS" || die "the Linux build of $GUI_PKG failed"
        info "$CLI_PKG -> bin/beautalks-cli"
        build_linux "$CLI_PKG" "$B/linux/beautalks-cli" "$LOGS/linux-cli.log" "$SHIMS" || die "the Linux build of $CLI_PKG failed"
        if [ "$HOST" = Linux ] && [ "$(uname -m)" = x86_64 ]; then
            check_version "Linux beautalks-cli version" "$B/linux/beautalks-cli"
        else
            info "(Linux beautalks-cli version not checked: not a Linux x86_64 host)"
        fi
        step "Linux x64: package"
        local L="$STAGE/linux/beautalks-$version-linux-x64"
        mkdir -p "$L/bin"
        cp "$B/linux/beautalks" "$B/linux/beautalks-cli" "$L/bin/"
        chmod 755 "$L/bin/beautalks" "$L/bin/beautalks-cli"
        cp -R "$SHARE"/assets "$SHARE"/models "$SHARE"/data "$SHARE"/drivers "$L/"
        local x
        for x in beautalks beautalks-cli; do
            printf '#!/bin/sh\n# Runs bin/%s from wherever this folder is (symlinks to this file work too).\nhere=$(dirname "$(readlink -f "$0")")\nexec "$here/bin/%s" "$@"\n' "$x" "$x" > "$L/$x"
            chmod 755 "$L/$x"
        done
        cp packaging/linux/beautalks.desktop.in "$L/beautalks.desktop"
        cp packaging/icons/beautalks-256.png "$L/beautalks.png"
        cp packaging/linux/install-desktop-entry.sh "$L/"
        chmod 755 "$L/install-desktop-entry.sh"
        cp "$license" "$L/LICENSE"
        "$PY" tools/release/package.py readme linux "$version" "$L/README.txt"
        lin_tar="beautalks-$version-linux-x64.tar.gz"
        "$PY" tools/release/package.py archive tar.gz "$L" "$OUT/$lin_tar" | sed 's/^/    /'
    fi

    # ── 7. notes and checksums
    step "release notes and SHA256SUMS"
    local -a note_args=()
    local IFS_SAVE=$IFS n
    IFS='|'
    for n in $notes_extra; do [ -z "$n" ] || note_args+=(--note "$n"); done
    IFS=$IFS_SAVE
    "$PY" tools/release/package.py notes --version "$version" --tag "$tag" --commit "${commit:0:12}" \
        --out "$DIST/RELEASE_NOTES.md" --gui-pkg "$GUI_PKG" --dado-version "${dado_ver:-1.0.0-rc.9}" \
        --min-macos "$MIN_MACOS" --mac-zip "$mac_zip" --mac-dmg "$mac_dmg" --win-zip "$win_zip" \
        --lin-tar "$lin_tar" --mac-universal "$universal" --win-exe "${WIN_BIN:+$WIN_BIN\\}beautalks.exe" ${note_args[@]+"${note_args[@]}"} | sed 's/^/    /'
    "$PY" tools/release/package.py sums "$OUT" | sed 's/^/    /'
    info "assets ($(ls "$OUT" | wc -l | tr -d ' ') files) in $OUT:"
    ls -l "$OUT" | grep -v -e '^total' -e ' engines\.' -e ' models\.' | awk '{printf "      %10s  %s\n", $5, $NF}'
    info "+ $(ls "$OUT" | grep -c -e '^engines\.' -e '^models\.') driver bundle files"

    if [ "$dry" = 1 ]; then
        step "dry run: nothing tagged, pushed or uploaded"
        info "everything is in $DIST (notes: $DIST/RELEASE_NOTES.md)"
        finish
        return 0
    fi

    # ── 8. tag, push, publish
    step "publish $tag to $REPO"
    info "this will: tag $tag at ${commit:0:12}, push the tag to origin, create the release"
    info "as a draft with all $(ls "$OUT" | wc -l | tr -d ' ') assets, then publish it"
    if [ "$yes" = 0 ]; then
        printf '    Type %s to go on, anything else stops: ' "$version"
        local answer=""; read -r answer || true
        [ "$answer" = "$version" ] || die "stopped before tagging (nothing was changed)"
    fi
    run "$LOGS/tag.log" git tag -a "$tag" -m "beautalks $version" "$commit" || die "git tag failed"
    run "$LOGS/push.log" git push origin "refs/tags/$tag" \
        || die "git push of $tag failed. The tag exists locally only: fix the problem and run 'git push origin refs/tags/$tag', or delete it with 'git tag -d $tag' and run ./build.sh --release again"
    local -a flags=(--repo "$REPO" --title "beautalks $version" --notes-file "$DIST/RELEASE_NOTES.md" --verify-tag --draft)
    [ "$prerelease" = 0 ] || flags+=(--prerelease)
    local -a files=()
    local f
    for f in "$OUT"/*; do files+=("$f"); done
    if ! run "$LOGS/release.log" gh release create "$tag" "${flags[@]}" "${files[@]}"; then
        die "gh release create failed; the tag $tag is pushed. Finish by hand:
    gh release upload $tag --repo $REPO --clobber $OUT/*
    gh release edit $tag --repo $REPO --draft=false
  (or, if no draft exists: gh release create $tag --repo $REPO --draft --verify-tag --notes-file $DIST/RELEASE_NOTES.md $OUT/*)"
    fi
    local n_up
    n_up="$(gh release view "$tag" --repo "$REPO" --json assets --jq '.assets | length')"
    [ "$n_up" = "${#files[@]}" ] || die "the draft has $n_up assets, expected ${#files[@]}: check it on GitHub, then: gh release edit $tag --repo $REPO --draft=false"
    local -a pub=(--draft=false)
    [ "$prerelease" = 1 ] || pub+=(--latest)
    run "$LOGS/publish.log" gh release edit "$tag" --repo "$REPO" "${pub[@]}" || die "publishing the draft failed: gh release edit $tag --repo $REPO --draft=false"
    info "published: https://github.com/$REPO/releases/tag/$tag"
    [ "$prerelease" = 0 ] || warn "$tag is a pre-release: GitHub's releases/latest (what Update drivers reads) still points at the last full release"
    finish
}

finish() {
    if [ -n "$WARNINGS" ]; then
        printf '\nwarnings:%s\n' "$WARNINGS"
    fi
    printf '\ndone.\n'
}

# ${1+"$@"}: bash 3.2 under set -u calls an empty "$@" unbound.
case "${1:-}" in
    --release) shift; release ${1+"$@"};;
    *) dev_build ${1+"$@"};;
esac
