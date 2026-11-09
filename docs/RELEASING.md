<!--
beautalks - radio programming software
Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
-->
# Building and releasing beautalks

One script, `./build.sh`, at the repo root, does both everyday builds and releases. A release is
made on the Mac mini: it builds macOS natively, cross-compiles Windows and Linux with Dado's
pinned zig, packages all three, and publishes one GitHub release with everything attached,
including the driver bundle that **Update drivers** reads.

```
./build.sh                         dev build of the app for this machine  -> build/beautalks-app
./build.sh cli                     dev build of the CLI                  -> build/beautalks
./build.sh test [PKG...]           dado test (default: radio cli driverhost updater ui)
./build.sh --target linux          cross-build the app for Linux x86_64   -> build/linux-x64/beautalks-app
./build.sh --target windows cli    cross-build a package for Windows      -> build/windows-x64/beautalks.exe
./build.sh --release --dry-run     build + package everything into dist/<version>/, publish nothing
./build.sh --release               ... and tag, push the tag, create the GitHub release
```

`./build.sh --help` lists the options. The GUI is `app/` (dev build: `build/beautalks-app`;
`./build.sh cli` builds the CLI as `build/beautalks`). `BEAUTALKS_GUI_PKG=gallery` builds the
component gallery instead, for dev builds and dry runs only: a real release refuses anything but
`app/`. `build-mac.sh` is replaced by plain `./build.sh` on the Mac, which uses the same Apple
clang flags. Every build, dev and release, gets `-D updater.APP_VERSION=<VERSION>`, so `VERSION`
is the only place the version is written.

## 1. One-time setup on the Mac

1. Xcode command line tools (Apple clang, `git`, `python3`, `lipo`, `ditto`, `hdiutil`, `plutil`):
   `xcode-select --install`
2. Dado 1.0.0-rc.9 installed (`~/dado`, `dado` on `PATH`). `dado doctor` should be all `ok`.
3. GitHub CLI: `brew install gh`, then `gh auth login` (GitHub.com, HTTPS, log in with a
   browser). `gh auth status` must say you are logged in with the `repo` scope.
4. `git remote -v` shows `origin` as `github.com/Anaxarchus/beautalks`, and your git
   `user.name`/`user.email` are set (the release tag is an annotated tag).

The first cross build of each platform takes a few minutes longer: zig builds its MinGW and glibc
support libraries once, and Dado's driver builds the script engine (QuickJS-ng) once per target.
That step clones QuickJS-ng from GitHub, so the first run needs the network. Later builds hit the
caches.

## 2. Making a release

1. Set the version in `VERSION` (it reaches the programs as `-D updater.APP_VERSION=...`: what
   `beautalks-cli version` prints and the driver updater compares against `min_app`). Commit,
   and push your branch.
2. Rehearse: `./build.sh --release --dry-run`. Everything lands in `dist/<version>/`:
   `assets/` (exactly what will be uploaded), `RELEASE_NOTES.md`, `logs/`, `stage/` (unpacked
   packages). Open `stage/mac/beautalks.app` and read the notes.
3. Release: `./build.sh --release` (or `./build.sh --release 0.1.0`; the argument must match
   `VERSION`). It asks you to type the version before it tags anything (`--yes` skips that).

What `--release` does, step by step (each step is printed as `==> [n] ...`, and each command's
output goes to `dist/<version>/logs/`, with its tail printed if it fails):

1. **Preflight.** Refuses if the version is not `MAJOR.MINOR.PATCH[-suffix]`, if `VERSION`
   disagrees with it, if the GUI package is not `app/`, if there is no `LICENSE`, if tracked files have uncommitted changes, if tag `v<version>`
   exists locally or on `origin`, if a release with that tag exists, or if `gh` is not logged in.
   `--dry-run` turns these into warnings and never needs `gh`.
2. **Tests.** `./build.sh test` for `radio cli driverhost updater ui` (with the Apple-silicon
   workaround of section 7 when needed); any failure stops the release.
   `--skip-tests` skips them (the notes are not changed by that, so do not publish untested).
3. **Driver bundle.** `drivers/release.py --release v<version> --no-repo-manifest` compiles the
   engines with `dadoc` and writes `drivers-manifest.json` plus one asset per file. If the freshly
   compiled `drivers/engines/*.js` differ from the committed ones, the release stops: commit them
   first, so the tag holds exactly what ships. (`--no-repo-manifest`: the release does not dirty
   `drivers/manifest.json`; the uploaded `drivers-manifest.json` is the record.)
4. **macOS.** `arm64` and `x86_64` builds with Apple clang (`MACOSX_DEPLOYMENT_TARGET=14.0`), joined
   with `lipo` into a universal binary. If the Intel half fails it ships Apple silicon only, says
   so in the warnings and in the release notes (`--mac-arch arm64` skips the attempt). Then
   `beautalks-cli version` must print `beautalks <version>`. Then `beautalks.app`, zipped with `ditto -c -k --keepParent`, and a `.dmg` with an Applications
   link (`--no-dmg` skips it).
5. **Windows x64.** The app and the CLI, both required, cross-built with zig
   (`DADO_TARGET=x86_64-w64-mingw32`, D3D11); the app as a GUI program (no console window) with
   the icon and version information (`zig rc`). Where Wine is installed (Linux), `beautalks-cli.exe
   version` is checked too. Zipped.
6. **Linux x64.** Cross-built with zig (`ZIG_TARGET=x86_64-linux-gnu`) against the committed
   sysroot (section 4); on a Linux host `beautalks-cli version` is checked. Packed as `.tar.gz`.
7. **Notes and checksums.** `dist/<version>/RELEASE_NOTES.md` (version, the models verified on
   hardware read from `models/*.ini`, how to open unsigned apps on each platform, licences) and
   `SHA256SUMS` over every asset.
8. **Publish.** `git tag -a v<version>` at the built commit, `git push origin refs/tags/v<version>`
   (never forced), `gh release create --draft --verify-tag` with **every** asset, a check that the
   draft holds them all, then `gh release edit --draft=false --latest`. The release only becomes
   visible (and `releases/latest`, which the driver updater reads) once it is complete. A version
   with a suffix (`0.2.0-rc.1`) is published as a pre-release, which `releases/latest` skips.

If something fails after the tag is pushed, the script prints the exact `gh` commands that finish
the job. Nothing is ever force-pushed or deleted on GitHub by the script.

### The release assets

| asset | contents |
|---|---|
| `beautalks-<v>-macos-universal.zip` (or `-arm64`) | `beautalks.app` |
| `beautalks-<v>-macos-universal.dmg` | the same app, with an Applications link |
| `beautalks-<v>-windows-x64.zip` | `beautalks.exe`, `beautalks-cli.exe`, `assets\ models\ drivers\ data\`, `LICENSE.txt`, `README.txt` |
| `beautalks-<v>-linux-x64.tar.gz` | `beautalks` + `beautalks-cli` launchers, `bin/`, `assets/ models/ drivers/ data/`, `beautalks.desktop`, `beautalks.png`, `install-desktop-entry.sh`, `LICENSE`, `README.txt` |
| `drivers-manifest.json`, `engines.*`, `models.*` | the driver bundle (docs/DRIVERS.md) |
| `SHA256SUMS` | SHA-256 of every other asset |

Inside the app bundle:

```
beautalks.app/Contents/
  Info.plist           io.github.anaxarchus.beautalks, version, LSMinimumSystemVersion 14.0,
                       NSHighResolutionCapable (packaging/macos/Info.plist.in)
  MacOS/beautalks      the GUI;  MacOS/beautalks-cli  the CLI
  Resources/beautalks.icns
  Resources/assets/    fonts, icons, brand  (found by ui/ as <exe>/../Resources/assets)
  Resources/models/  Resources/drivers/  Resources/data/  Resources/LICENSE
```

Nothing but the standard entries sits in `Contents/`, so the bundle can be signed later as it is.

Packaging inputs live in `packaging/`: `macos/Info.plist.in`, `macos/beautalks.icns`,
`windows/beautalks.ico`, `windows/beautalks.rc.in`, `linux/beautalks.desktop.in`,
`linux/install-desktop-entry.sh`, `icons/beautalks-<N>.png`. The icons are made from
`assets/brand/beautalks-icon.svg` by `python3 tools/release/make_icons.py` (rsvg-convert, or
Pillow) and committed; it writes the `.icns` and `.ico` itself, so no `iconutil` is needed.

## 3. Checking the macOS build (things only the Mac can verify)

Run once after the first `./build.sh --release --dry-run` on the Mac, before the first real
release. `V` is the version.

```sh
./build.sh test driverhost   # first line says whether the MAX_ALIGN patch applied; must pass 4/4
V=$(cat VERSION); D=dist/$V
lipo -archs $D/stage/mac/beautalks.app/Contents/MacOS/beautalks       # arm64 x86_64 (or arm64)
lipo -archs $D/stage/mac/beautalks.app/Contents/MacOS/beautalks-cli
plutil -p $D/stage/mac/beautalks.app/Contents/Info.plist | head -20
otool -L $D/stage/mac/beautalks.app/Contents/MacOS/beautalks           # only /System and /usr/lib
vtool -show-build $D/stage/mac/beautalks.app/Contents/MacOS/beautalks | grep minos   # 14.0
open $D/stage/mac/beautalks.app            # window opens, fonts and icons drawn, the Dock icon is purple "b"
$D/stage/mac/beautalks.app/Contents/MacOS/beautalks-cli models | head -3   # models found from any directory
cd /tmp && unzip -q -o ~/dev/Dado/beautalks/$D/assets/beautalks-$V-macos-*.zip && open beautalks.app; cd -
hdiutil attach $D/assets/beautalks-$V-macos-*.dmg     # Finder window with the app and Applications
arch -x86_64 $D/stage/mac/beautalks.app/Contents/MacOS/beautalks-cli models | head -1   # Intel half (Rosetta)
```

To see the first-run experience of a user, quarantine a copy:
`xattr -w com.apple.quarantine "0081;$(printf %x $(date +%s));Safari;" /tmp/beautalks.app`
and open it: Gatekeeper must offer the **Open Anyway** path described in the release notes.
Report anything that differs; the macOS steps were written without a Mac to run them on.

## 4. Cross-compiling: how Windows and Linux are built from the Mac

Both use Dado's pinned zig (`~/dado/zig/0.16.0/zig`) as the C compiler, so the same commands
work on the Mac and on Linux (and were run on Linux to test them):

| | Windows x64 | Linux x64 |
|---|---|---|
| `DADO_TARGET` | `x86_64-w64-mingw32` | `x86_64-pc-linux-gnu` |
| `ZIG_TARGET` | (unset: derived) | `x86_64-linux-gnu` |
| `DADO_CFLAGS` | (empty) | `-I<sysroot>/usr/include` |
| `DADO_LDFLAGS` | `beautalks.res -Wl,--subsystem,windows` (GUI) | `-L<sysroot>/usr/lib/x86_64-linux-gnu -s` |
| graphics | D3D11 (sokol) | OpenGL 3.3 core over GLX (sokol) |
| runs on | Windows 10/11 x64 | glibc 2.29+ with libX11, libXi, libXcursor, libGL |

`build.sh` also puts a shim directory first on `PATH` for these builds (`dist/<v>/.shims`):

* a `brew` that answers nothing, because the rc.9 driver adds `brew --prefix`'s `-I`/`-L` to
  **every** build, cross builds included, and macOS headers must not reach a Linux or Windows
  compile;
* `zig` pointing at the pinned zig, because the script engine's build (`tools/quickjs/build.sh`
  in the Dado install) indexes its archive with `zig ar` only when `zig` is on `PATH`; Apple's
  `ar` cannot index ELF or COFF objects;
* `sha256sum` (from `shasum`) when the Mac has none, for the same script's cache key.

`ZIG_TARGET` has no glibc suffix (`x86_64-linux-gnu.2.31`): `zig cc -dumpmachine` rejects it, and
the script engine's build asks for it. The pinned zig's default glibc floor gives binaries that
need glibc 2.29 (checked with `objdump -T`: the newest symbol version is `GLIBC_2.29`).

### The Linux sysroot

`tools/release/linux-sysroot-x86_64-jammy-1.tar.gz` (1,413,722 bytes, committed, with its
`.sha256`) holds only what sokol_app needs on top of zig's own glibc:

* headers: `X11/` (libx11-dev, x11proto-dev, libxi-dev, libxcursor-dev, libxfixes-dev,
  libxext-dev), `GL/` and `KHR/` (libgl-dev);
* link targets: `libX11.so.6`, `libXi.so.6`, `libXcursor.so.1`, `libGL.so.1` (glvnd) and their
  `lib*.so` links;
* `LICENSES/`: each package's Debian copyright file. Everything is MIT/X11-style (X.Org,
  libglvnd, Khronos). None of it is copied into beautalks: the binary only records
  `NEEDED libX11.so.6` etc., resolved on the user's machine.

It is made by `tools/release/make_linux_sysroot.sh` from eleven Ubuntu 22.04 (jammy)
release-pocket packages pinned by version and SHA-256 (downloaded from archive.ubuntu.com, falling
back to old-releases.ubuntu.com). The tarball is deterministic: two runs gave the same SHA-256
(`5167cc9d…97b4d2`). Rerun it on Linux (it needs `dpkg-deb`, or `ar` and a zstd-capable `tar`)
only to change the package set; bump `SYSROOT_ID` in both scripts when you do. `build.sh` checks
the `.sha256` and unpacks it once into `build/linux-sysroot-<id>/`.

Tested: the packaged Linux build (from `./build.sh --release --dry-run` on Ubuntu 24.04) runs
under Xvfb with Mesa, started from `/` through a symlink to the `beautalks` launcher, and finds
its fonts, icons and channel data (`docs/screens-release/linux-x64-app-radio.png`); `beautalks-cli models`
finds the models from any directory; `ldd` resolves everything from stock packages.

### Windows status

* The app and the CLI both cross-build (the CLI with `serial/`'s Win32 backend), and both are
  required: a failure stops the release. The app runs under Wine 9 (D3D11 through wined3d):
  `docs/screens-release/windows-x64-wine-app.png`.
* `beautalks.exe` is a GUI-subsystem program (no console window) with the icon and a version tab;
  `beautalks-cli.exe` is a console program.
* The script engine (QuickJS-ng) cross-builds with zig's MinGW (the Dado README's "cannot be
  built on Windows" is about a Windows host).
* Not yet tried: a real Windows machine, and a radio on a Windows COM port.

## 5. Where a package's files are found at run time

`ui/` (assets) and `radio.find_shipped(dir)` (models, drivers, data; used by `app/`, `cli/` and
`engines/`) look, first wins, in `$BEAUTALKS_<DIR>`, `./<dir>`, `<exe>/<dir>`, `<exe>/../<dir>`,
`<exe>/../Resources/<dir>`. So:

| package | program | its folders |
|---|---|---|
| Windows zip | `beautalks.exe` at the top | beside it (`<exe>/<dir>`) |
| Linux tar | `bin/beautalks` (run through the `./beautalks` launcher) | `<exe>/../<dir>` |
| macOS bundle | `Contents/MacOS/beautalks` | `Contents/Resources/<dir>` |

User data stays in `$BEAUTALKS_HOME`, else the OS config dir + `/beautalks`.

## 6. Code changes needed in other packages

Done since the first version of this file: `radio.find_shipped`, `APP_VERSION` as an `@const`,
the Win32 serial backend, `LICENSE`, `.gitignore` for `/dist/`. Nothing else is required by the
release tooling.

## 7. Dado issues worked around here (worth reporting upstream)

* **Apple silicon: `#heap` refuses `mem.MAX_ALIGN`.** `core:mem` declares `MAX_ALIGN = 16`, but
  the C runtime's `#heap` refuses alignments above `DADO_MAX_ALIGN`, which is 8 on Apple arm64
  (`long double` is a `double` there). Every `#heap` request at `MAX_ALIGN` returns NULL, which
  breaks core:script (`dado test driverhost` fails 0/4 on the Mac). On an Apple arm64 host,
  `build.sh` compiles and runs a 10-line probe (in `build/.dado-align-probe/`) at the start of
  each dev build, `./build.sh test` and release. If the heap refuses, it copies the collections
  (`dado where`) once to `build/.dado-collections-patched/<dado version>-<hash of mem.dado>/`,
  replaces the `MAX_ALIGN` line with
  `when #OS == #DARWIN && #ARCH == #AARCH64: const u64 MAX_ALIGN = 8` / `else: ... = 16`, and
  sets `DADO_COLLECTIONS` to it for the host builds and tests only (the macOS release build,
  both slices, as the `when` gives the Intel slice 16). Windows and Linux cross builds keep the
  stock collections. It prints one line saying which way it went. Use `./build.sh test`, not
  bare `dado test`, on the Mac. Checked here: core:mem, core:script, core:mem/{arena,slab,bump,gc,libc},
  core:runtime and app/cli/driverhost/radio/updater/ui all `dado check` with the patch for
  `aarch64-apple-darwin` and for Linux; the emitted C asks for 8 on `aarch64-apple-darwin` and
  16 on every other target; `dado test driverhost` passes against the patched tree.
  `BEAUTALKS_FORCE_ALIGN_PATCH=1` forces the patch on any host (for testing). **Removing it:**
  when a Dado release fixes the runtime, the probe passes and nothing is patched; then delete
  the block "the Apple-silicon alignment workaround" (and `host_dado`/`run_tests`' use of it)
  from `build.sh` and `rm -rf build/.dado-collections-patched build/.dado-align-probe`.

* macOS: `-x objective-c` from sokol's `flags` clause is repeated on the link line before the
  objects; worked around with `DADO_CFLAGS="-x none -ObjC"` and Apple clang.
* Homebrew's `-I`/`-L` are added to cross builds (the `brew` shim).
* `tools/quickjs/build.sh` picks `ar` unless `zig` is on `PATH`, which breaks a cross archive
  on macOS (the `zig` shim), and uses `sha256sum` (the `sha256sum` shim).
* `ZIG_TARGET` with a glibc version (`x86_64-linux-gnu.2.31`) breaks the engine build
  (`zig cc -dumpmachine`).
* zig writes a `.pdb` beside a Windows `-o`; it is not packaged.

## 8. Troubleshooting

* **A step failed**: its log is in `dist/<v>/logs/` (the last 25 lines are printed). Fix, commit,
  and run `./build.sh --release` again: nothing was tagged unless step "publish" was reached.
* **The macOS release build fails but `./build.sh` (dev) works**: the release tier adds `-O2`
  and link-time optimisation. Try `BEAUTALKS_MAC_DADO_FLAGS=--no-lto ./build.sh --release --dry-run`.
* **Only the Intel half fails**: the release goes out Apple-silicon-only and says so; or pass
  `--mac-arch arm64` to skip the attempt.
* **Spaces in the checkout path** break the cross builds (`DADO_CFLAGS`/`DADO_LDFLAGS` are
  split on spaces by the Dado driver). `~/dev/Dado/beautalks` is fine.

## 9. Testing a Linux or Windows build without the hardware

On any Linux box (this is how the release tooling was tested):

```sh
./build.sh --release --dry-run --targets windows,linux
tar xzf dist/<v>/assets/beautalks-<v>-linux-x64.tar.gz -C /tmp
Xvfb :91 -screen 0 1600x1000x24 &  DISPLAY=:91 /tmp/beautalks-<v>-linux-x64/beautalks
# Windows: unzip, then  DISPLAY=:91 wine beautalks.exe   (apt install wine64)
```
