#!/usr/bin/env python3
# beautalks - radio programming software
# Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
#
# Packaging helpers for ./build.sh --release. Standard library only, so it runs
# with the python3 that comes with Xcode's command line tools.
#
#   package.py fill TEMPLATE OUT KEY=VALUE...    replace @KEY@ in a template
#   package.py archive zip|tar.gz SRC_DIR OUT    deterministic archive of SRC_DIR
#                                                (top folder = SRC_DIR's name)
#   package.py sums DIR                          DIR/SHA256SUMS over every file in DIR
#   package.py notes --version V --tag T ...     the release notes (Markdown)
#   package.py readme linux|windows|macos V OUT  the README.txt inside a package
import argparse, datetime, glob, gzip, hashlib, io, os, re, stat, sys, tarfile, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EPOCH = 315532800  # 1980-01-01, the earliest time a zip can hold


def mtime():
    # SOURCE_DATE_EPOCH (build.sh sets it to the commit time) keeps archives reproducible.
    return int(os.environ.get("SOURCE_DATE_EPOCH", EPOCH))


def cmd_fill(a):
    with open(a.template, encoding="utf-8") as f:
        text = f.read()
    for kv in a.pairs:
        k, _, v = kv.partition("=")
        text = text.replace("@" + k + "@", v)
    left = re.findall(r"@[A-Z_]+@", text)
    if left:
        sys.exit("fill: %s still has %s" % (a.template, ", ".join(sorted(set(left)))))
    with open(a.out, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def walk(src):
    base = os.path.basename(os.path.normpath(src))
    out = [(src, base)]
    for dirpath, dirnames, filenames in os.walk(src, followlinks=False):
        dirnames.sort()
        rel = os.path.relpath(dirpath, os.path.dirname(os.path.normpath(src)))
        for d in list(dirnames):
            p = os.path.join(dirpath, d)
            out.append((p, os.path.join(rel, d)))
        for n in sorted(filenames):
            if n in (".DS_Store",) or n.startswith("._"):
                continue
            out.append((os.path.join(dirpath, n), os.path.join(rel, n)))
    return sorted(out, key=lambda t: t[1])


def cmd_archive(a):
    t = mtime()
    entries = walk(a.src)
    if a.format == "zip":
        with zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for path, arc in entries:
                arc = arc.replace(os.sep, "/")
                st = os.lstat(path)
                stamp = datetime.datetime.fromtimestamp(max(t, EPOCH), datetime.timezone.utc).timetuple()[:6]
                zi = zipfile.ZipInfo(arc + ("/" if stat.S_ISDIR(st.st_mode) else ""), stamp)
                zi.create_system = 3  # unix: keep the mode bits
                if stat.S_ISDIR(st.st_mode):
                    zi.external_attr = (0o40755 << 16) | 0x10
                    z.writestr(zi, b"")
                elif stat.S_ISLNK(st.st_mode):
                    sys.exit("archive: a zip here holds no symlinks: " + path)
                else:
                    mode = 0o755 if st.st_mode & 0o111 else 0o644
                    zi.external_attr = (0o100000 | mode) << 16
                    zi.compress_type = zipfile.ZIP_DEFLATED
                    with open(path, "rb") as f:
                        z.writestr(zi, f.read())
    else:
        raw = io.BytesIO()
        with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tar:
            for path, arc in entries:
                ti = tar.gettarinfo(path, arcname=arc.replace(os.sep, "/"))
                ti.uid = ti.gid = 0
                ti.uname = ti.gname = ""
                ti.mtime = t
                if ti.isreg():
                    ti.mode = 0o755 if ti.mode & 0o111 else 0o644
                    with open(path, "rb") as f:
                        tar.addfile(ti, f)
                else:
                    if ti.isdir():
                        ti.mode = 0o755
                    tar.addfile(ti)
        with open(a.out, "wb") as f:
            with gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=t, compresslevel=9) as g:
                g.write(raw.getvalue())
    print("%s (%d bytes)" % (a.out, os.path.getsize(a.out)))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_sums(a):
    names = sorted(n for n in os.listdir(a.dir) if n != "SHA256SUMS" and os.path.isfile(os.path.join(a.dir, n)))
    with open(os.path.join(a.dir, "SHA256SUMS"), "w", newline="\n") as f:
        for n in names:
            f.write("%s  %s\n" % (sha256(os.path.join(a.dir, n)), n))
    print("SHA256SUMS: %d files" % len(names))


def ini_value(text, section, key):
    sec = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            sec = s[1:-1].strip()
        elif sec == section and "=" in s and not s.startswith((";", "#")):
            k, _, v = s.partition("=")
            if k.strip() == key:
                return v.strip()
    return ""


def models_by_status():
    write, read, untested = [], [], []
    for p in sorted(glob.glob(os.path.join(ROOT, "models", "*.ini"))):
        with open(p, encoding="utf-8") as f:
            t = f.read()
        name = (ini_value(t, "model", "vendor") + " " + ini_value(t, "model", "name")).strip()
        status = ini_value(t, "model", "tested")
        notes = ini_value(t, "model", "notes")
        if status == "write" and notes:
            name = "%s: %s" % (name, notes)
        (write if status == "write" else read if status == "read" else untested).append(name)
    return write, read, untested


UNSIGNED_HEAD = """\
### Opening the app (these builds are not signed yet)

beautalks is not yet signed with an Apple or Microsoft certificate, so your system warns
the first time you open it. Check the download against `SHA256SUMS` first if you like
(`shasum -a 256 -c SHA256SUMS --ignore-missing` on macOS and Linux,
`Get-FileHash <file>` in PowerShell).
"""

UNSIGNED_MAC = """
**macOS** (Apple silicon{intel}; macOS {min_macos} or later)
1. Unzip `{mac_zip}` and drag **beautalks.app** to Applications{dmg_hint}.
2. Open it once with **right-click (or Control-click) on beautalks.app → Open → Open**.
3. On macOS 15 Sequoia and later that menu no longer offers Open: double-click the app,
   close the warning, then go to **System Settings → Privacy & Security**, scroll to
   *Security*, click **Open Anyway** next to "beautalks was blocked", and confirm.
4. If macOS says the app "is damaged and can't be opened", the download quarantine is
   the cause, not the app: run `xattr -dr com.apple.quarantine /Applications/beautalks.app`
   in Terminal, then open it again.

The command-line tool is inside the bundle:
`/Applications/beautalks.app/Contents/MacOS/beautalks-cli --help`.
"""

UNSIGNED_WIN = """
**Windows** (64-bit Windows 10 or 11)
1. Right-click `{win_zip}` → **Extract All…** (do not run it from inside the zip).
2. In the extracted folder, double-click **{win_exe}**.
3. If SmartScreen says "Windows protected your PC", click **More info → Run anyway**.
"""

UNSIGNED_LIN = """
**Linux** (x86_64, X11 or XWayland, glibc 2.29 or later: Ubuntu 20.04+, Debian 11+, Fedora 31+)
1. `tar xzf {lin_tar}` and run `./beautalks-{version}-linux-x64/beautalks`
   (if the executable bit got lost: `chmod +x beautalks-*/beautalks beautalks-*/bin/*`).
2. It needs the X11 and OpenGL libraries most desktops already have:
   Debian/Ubuntu `sudo apt install libx11-6 libxi6 libxcursor1 libgl1`,
   Fedora `sudo dnf install libX11 libXi libXcursor mesa-libGL`.
3. `./install-desktop-entry.sh` (inside the folder) adds beautalks to your application menu.
4. Serial cables: add yourself to the `dialout` group (`sudo usermod -aG dialout $USER`,
   then log out and in) so beautalks can open `/dev/ttyUSB*`.
"""


def cmd_notes(a):
    write, read, untested = models_by_status()
    v = a.version
    lines = []
    lines.append("# beautalks %s\n" % v)
    lines.append("Released %s from commit `%s`.\n" % (datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"), a.commit))
    if a.gui_pkg != "app":
        lines.append("> **Preview build.** The desktop app is still being written; this release's window is "
                     "the component gallery (`%s/`), a mock of the interface with sample channels. "
                     "Radio programming is available through `beautalks-cli`.\n" % a.gui_pkg)
    lines.append("## Downloads\n")
    lines.append("| platform | file |\n|---|---|")
    for label, f in (("macOS", a.mac_zip), ("macOS (disk image)", a.mac_dmg), ("Windows x64", a.win_zip), ("Linux x64", a.lin_tar)):
        if f:
            lines.append("| %s | `%s` |" % (label, f))
    lines.append("| checksums | `SHA256SUMS` |")
    lines.append("| driver bundle | `drivers-manifest.json` + `engines.*` / `models.*` (read by *Update drivers*) |\n")
    if a.notes_extra:
        for n in a.notes_extra:
            lines.append("* " + n)
        lines.append("")
    lines.append("## Verified on real radios\n")
    if write:
        lines.append("Read, safe write (backup first, verify after) and read-back checked on hardware, "
                     "on macOS with a CH340 programming cable:\n")
        for n in write:
            lines.append("* **%s**" % n)
        lines.append("")
    if read:
        lines.append("Read checked on hardware (writing stays disabled): " + ", ".join(read) + ".\n")
    if untested:
        lines.append("%d more model definitions ship as **untested**: beautalks can read them. Before the first "
                     "write it offers a guided verification (an identical write-back, then you confirm the radio "
                     "still works), which marks that radio as tested on your computer; writing without it needs an "
                     "explicit risk confirmation. A backup is always taken first and every write is read back to "
                     "verify.\n" % len(untested))
    built = [n for n, f in (("macOS (native, Apple clang)", a.mac_zip), ("Windows", a.win_zip), ("Linux", a.lin_tar)) if f]
    lines.append("Built: %s. Windows and Linux are cross-compiled with Dado %s's pinned zig; "
                 "radios have so far been tested from macOS only.\n" % (", ".join(built), a.dado_version))
    lines.append(UNSIGNED_HEAD)
    if a.mac_zip:
        lines.append(UNSIGNED_MAC.format(
            intel=" and Intel" if a.mac_universal == "1" else "", min_macos=a.min_macos, mac_zip=a.mac_zip,
            dmg_hint=(" (or open `%s` and drag it to the Applications link)" % a.mac_dmg) if a.mac_dmg else ""))
    if a.win_zip:
        lines.append(UNSIGNED_WIN.format(win_zip=a.win_zip, win_exe=a.win_exe))
    if a.lin_tar:
        lines.append(UNSIGNED_LIN.format(lin_tar=a.lin_tar, version=v))
    lines.append("## Licences\n")
    lines.append("* beautalks: Copyright (C) 2026 Anaxarchus. Licensed under the **GNU GPL v3 or later**. "
                 "Source: https://github.com/Anaxarchus/beautalks (tag `%s`)." % a.tag)
    lines.append("* Radio protocol and memory-layout knowledge is ported from **CHIRP** "
                 "(https://chirpmyradio.com, GPLv3). Thank you to the CHIRP developers.")
    lines.append("* **Inter** typeface by Rasmus Andersson, SIL Open Font License 1.1 (`assets/fonts/OFL.txt`).")
    lines.append("* **Material Symbols** icons by Google, Apache License 2.0 "
                 "(`assets/icons/LICENSE-material-symbols.txt`).")
    lines.append("* Built with Dado (sokol, zlib licence; QuickJS-ng, MIT licence).")
    lines.append("")
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    print("release notes: " + a.out)


README = {
"linux": """beautalks {v} for Linux (x86_64)
Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.

Run:            ./beautalks            (the desktop app)
                ./beautalks-cli --help (the command-line tool)
Menu entry:     ./install-desktop-entry.sh   (./install-desktop-entry.sh --remove undoes it)
Needs:          X11 (or XWayland), OpenGL 3.3, glibc 2.29+, and the libraries
                libX11.so.6 libXi.so.6 libXcursor.so.1 libGL.so.1
                (Debian/Ubuntu: sudo apt install libx11-6 libxi6 libxcursor1 libgl1)
Serial cables:  sudo usermod -aG dialout $USER   (then log out and back in)

Keep the folder together: bin/ looks for assets/, models/, drivers/ and data/ beside it.
Your radios, backups and updated drivers live in ~/.config/beautalks.
Licences: LICENSE (GPLv3), assets/fonts/OFL.txt (Inter), assets/icons/LICENSE-material-symbols.txt.
""",
"windows": """beautalks {v} for Windows (64-bit)
Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.

Extract the whole zip first (right-click > Extract All), then double-click {exe}.
Command line: beautalks-cli.exe --help (in the same folder).
If SmartScreen says "Windows protected your PC": More info > Run anyway
(the app is not signed with a Microsoft certificate yet).

Keep the folder together: {exe} finds the assets, models, drivers and data
folders through its place in it.
Licences: LICENSE.txt (GPLv3), assets/fonts/OFL.txt (Inter), assets/icons/LICENSE-material-symbols.txt.
""",
}


def cmd_readme(a):
    text = README[a.platform].format(v=a.version, exe=a.exe)
    nl = "\r\n" if a.platform == "windows" else "\n"
    with open(a.out, "w", encoding="utf-8", newline="") as f:
        f.write(text.replace("\n", nl))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("fill"); p.add_argument("template"); p.add_argument("out"); p.add_argument("pairs", nargs="*")
    p = sub.add_parser("archive"); p.add_argument("format", choices=["zip", "tar.gz"]); p.add_argument("src"); p.add_argument("out")
    p = sub.add_parser("sums"); p.add_argument("dir")
    p = sub.add_parser("readme"); p.add_argument("platform", choices=["linux", "windows"]); p.add_argument("version"); p.add_argument("out"); p.add_argument("--exe", default="beautalks.exe")
    p = sub.add_parser("notes")
    for k in ("version", "tag", "commit", "out", "gui-pkg", "dado-version", "min-macos"):
        p.add_argument("--" + k, required=True)
    for k in ("mac-zip", "mac-dmg", "win-zip", "lin-tar", "mac-universal"):
        p.add_argument("--" + k, default="")
    for k in ("win-exe",):
        p.add_argument("--" + k, default="")
    p.add_argument("--note", dest="notes_extra", action="append", default=[])
    a = ap.parse_args()
    {"fill": cmd_fill, "archive": cmd_archive, "sums": cmd_sums, "notes": cmd_notes, "readme": cmd_readme}[a.cmd](a)


if __name__ == "__main__":
    main()
