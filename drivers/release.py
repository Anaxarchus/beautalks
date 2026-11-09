#!/usr/bin/env python3
# beautalks - radio programming software
# Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
#
# Builds the driver bundle for a GitHub release (see docs/DRIVERS.md):
#   * compiles drivers/engines/*.dados to .js with `dadoc --emit=mod`
#   * collects engines/*.js, engines/*.dados and models/*.ini
#   * writes drivers/manifest.json (committed: the record of the last bundle)
#     and, in --out, the flat release assets: drivers-manifest.json plus one
#     asset per file (engines.uv17pro.js, models.uv-5rm.ini, ...)
#
#   python3 drivers/release.py --release v0.2.0 --out dist/release-assets --upload
#
# Owner decision: EVERY GitHub release carries the driver bundle (the updater
# reads releases/latest). --upload attaches the assets to the release with
# `gh release upload <tag> ... --clobber` (create the release first, or pass
# --create to run `gh release create <tag>` when it does not exist yet).
#
# --github-layout BASE also lays the assets out as GitHub serves them
# (BASE/download/<tag>/<asset> and BASE/latest/download/<asset>), for tests
# against a file:// or http://127.0.0.1 fake.
import argparse, datetime, hashlib, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SAFE = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9._-]{0,99}$")
DRIVER_API = 1


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True, help="the release tag the assets are attached to")
    ap.add_argument("--serial", type=int, default=int(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M")),
                    help="monotonic bundle number (default: UTC yyyymmddHHMM)")
    ap.add_argument("--min-app", default="0.1.0")
    ap.add_argument("--driver-api", type=int, default=DRIVER_API)
    ap.add_argument("--engines", default=os.path.join(HERE, "engines"))
    ap.add_argument("--models", default=os.path.join(ROOT, "models"))
    ap.add_argument("--dadoc", default=os.environ.get("DADOC", "dadoc"))
    ap.add_argument("--no-compile", action="store_true", help="use the committed .js as they are")
    ap.add_argument("--out", required=True, help="directory for the flat release assets")
    ap.add_argument("--github-layout", help="also lay assets out as GitHub serves them, under this dir")
    ap.add_argument("--upload", action="store_true", help="attach the assets to the GitHub release with gh")
    ap.add_argument("--create", action="store_true", help="with --upload: create the release if it does not exist")
    ap.add_argument("--repo", default="Anaxarchus/beautalks", help="OWNER/REPO for --upload")
    ap.add_argument("--no-repo-manifest", action="store_true", help="do not rewrite drivers/manifest.json")
    a = ap.parse_args()
    if not SAFE.match(a.release):
        sys.exit("release tag must match " + SAFE.pattern)

    engines = sorted(f for f in os.listdir(a.engines) if f.endswith(".dados"))
    if not a.no_compile:
        for f in engines:
            src = os.path.join(a.engines, f)
            dst = src[:-len(".dados")] + ".js"
            subprocess.run([a.dadoc, "--emit=mod", src, "-o", dst], check=True)

    files = []  # (install path, source path)
    for f in sorted(os.listdir(a.engines)):
        if f.endswith(".js") or f.endswith(".dados"):
            files.append(("engines/" + f, os.path.join(a.engines, f)))
    for f in sorted(os.listdir(a.models)):
        if f.endswith(".ini"):
            files.append(("models/" + f, os.path.join(a.models, f)))

    os.makedirs(a.out, exist_ok=True)
    entries = []
    for rel, src in files:
        asset = rel.replace("/", ".")
        if not SAFE.match(os.path.basename(rel)) or not SAFE.match(asset):
            sys.exit("unsafe file name: " + rel)
        shutil.copyfile(src, os.path.join(a.out, asset))
        entries.append({"path": rel, "asset": asset, "sha256": sha256(src), "size": os.path.getsize(src)})

    manifest = {
        "format": 1,
        "driver_api": a.driver_api,
        "min_app": a.min_app,
        "release": a.release,
        "serial": a.serial,
        "created": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0, tzinfo=None).isoformat() + "Z",
        "files": entries,
    }
    text = json.dumps(manifest, indent=2) + "\n"
    with open(os.path.join(a.out, "drivers-manifest.json"), "w") as f:
        f.write(text)
    if not a.no_repo_manifest:
        with open(os.path.join(HERE, "manifest.json"), "w") as f:
            f.write(text)

    if a.github_layout:
        for d in (os.path.join(a.github_layout, "download", a.release),
                  os.path.join(a.github_layout, "latest", "download")):
            os.makedirs(d, exist_ok=True)
            for name in os.listdir(a.out):
                shutil.copyfile(os.path.join(a.out, name), os.path.join(d, name))
    print("bundle %s serial %d: %d files" % (a.release, a.serial, len(entries)))

    if a.upload:
        assets = sorted(os.path.join(a.out, n) for n in os.listdir(a.out))
        exists = subprocess.run(["gh", "release", "view", a.release, "--repo", a.repo],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        if not exists:
            if not a.create:
                sys.exit("release %s does not exist on %s (pass --create)" % (a.release, a.repo))
            subprocess.run(["gh", "release", "create", a.release, "--repo", a.repo,
                            "--title", a.release, "--notes", "beautalks " + a.release], check=True)
        subprocess.run(["gh", "release", "upload", a.release, "--repo", a.repo, "--clobber"] + assets, check=True)
        print("attached %d assets to %s %s" % (len(assets), a.repo, a.release))


if __name__ == "__main__":
    main()
