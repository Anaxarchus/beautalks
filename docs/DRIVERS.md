<!--
beautalks - radio programming software
Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
-->
# Drivers: scripted engines, the driver bundle, and "Update drivers"

beautalks keeps **protocol drivers as DadoScript mods**. A driver is compiled to JavaScript
(`dadoc --emit=mod`) and loaded by path while the app runs, so drivers can be fixed or added by a
GitHub release and the **Update drivers** button, with no rebuild of the app. A **model** is still
an INI file (`models/*.ini`). Every release ships the INIs in the same bundle.

```
drivers/                       in the repo
  engines/<name>.dados         driver source (GPLv3, ships in the bundle for transparency)
  engines/<name>.js            what dadoc --emit=mod wrote from it (what the app loads)
  manifest.json                record of the last bundle built (written by release.py)
  release.py                   builds the bundle + release assets
models/*.ini                   model definitions (owned by the radio core; bundled as-is)
driverhost/                    Dado side: loads a driver mod, hands it a Link, calls it
updater/                       fetch -> verify -> install -> activate / rollback
```

## 0. Owner decisions (2026-11-08)

1. **Every GitHub release carries the driver bundle.** `drivers/release.py --upload` attaches
   it (`gh release upload <tag> ... --clobber`; `--create` makes the release first). The updater
   reads `releases/latest`, so a release without the bundle would make "Update drivers" fail
   (safely, keeping the active set).
2. **No manifest signing for now.** Section 5's signing design stays as future work only.
3. **Data dir** as proposed: OS config dir + `/beautalks` (`~/Library/Application Support/
   beautalks` on macOS, `~/.config/beautalks` on Linux).
4. **Updated engines override built-ins**, with fallback: if the downloaded engine fails to load
   (does not compile, wrong driver API, hangs while loading), the app uses the shipped set and
   then the built-in engine, and says why (`driverhost.choose_engine`, section 2).
5. Repo: `Anaxarchus/beautalks` (updater default, overridable).

## 1. Spike result: drivers as mods work

Proven in `spikes/modspike` (host) + `spikes/modspike_drivers` (mods). The production version is
in `driverhost/`, tested against the owner's real UV-5RM backup. The spike's `harden.js` is the
first version and is superseded by `driverhost/harden.js`.

How it works:

* Dado cannot call `Script.load` itself. A **script class compiled into the app**
  (`driverhost/loader.dados`) calls `Script.load(path, Link(), model)`. Dado holds the loader
  through a VM handle (`#script_vm`, `#script_new`) and calls its methods (`identify`,
  `download`, `upload`).
* `Link` (`driverhost/link.dados`) is a script class whose methods call Dado functions
  (`dh_write`, `dh_read`, ... in `driverhost.dado`). A driver receives a Link instance as an
  `any` and calls `link.write(bytes)` and `link.read(n, timeout_ms)`.
* **Bytes cross as `[]byte`.** A script `[]byte` passes into a Dado `[]u8` parameter, and a Dado
  `ref []u8` result comes back as `[]byte`. Each crossing makes a copy. `[]int` to `[]i64` also
  works, but `[]byte` is typed and keeps values modulo 256.
* **Speed is not a concern.** A 33,664-byte download in 0x40 blocks makes 526 round trips
  through Link and Dado. It took 22 to 39 ms in the spike, against about 3 s of serial time at
  115200 baud. Loading a mod takes 2 to 4 ms.
* **Errors keep their code and trace.**
  * A Dado function the script calls that fails with `fail 1` reaches the driver as an `Error`,
    and an uncaught one reaches Dado as `try ... else code:` with code 1.
  * A driver's `fail Error("...", 8)` reaches Dado as code 8.
  * `#script_error()` gives the text with a full trace, for example
    `at modspike_drivers/fake17.dados:16:5 (main.Fake17.identify)`.
  * Drivers fail with `radio.LinkError` numbers (2 NO_ANSWER, 3 BAD_REPLY, 4 REFUSED,
    7 BAD_MODEL, 8 IMAGE_SIZE).
* **Model INI: yes.** The host reads the INI with `core:cfg` and flattens it to
  `{"section.key": value}`. Dado maps cross to script maps, so the driver gets `model` as a
  `{string: string}` (for example `model.get("link.magics", "")`).
* Mods load by absolute path as well as relative, so the app can load from its data directory.
* Failures at load time, such as a missing file, a module that does not compile, an import, or
  `init` throwing, come back as code 70 with a clear message. The host reports them as
  `E_LOAD` (21). A driver whose `api()` is not 1 is refused with `E_API` (20).

## 2. Driver API 1

A driver mod is one class:

```
void init(any link, {string: string} model)
int api()                    // must answer 1
string identify()            // handshake; answers the radio's replies as text
[]byte download()            // the whole image (does its own handshake)
void upload([]byte image)    // writes it (does its own handshake)
```

`link` (driverhost/link.dados):

| method | meaning |
|---|---|
| `write([]byte)` | send every byte |
| `read(n, timeout_ms) -> []byte` | up to n bytes, whatever arrived in time (empty = timeout) |
| `read_exact(n, timeout_ms) -> []byte` | exactly n, or fail 2 (nothing came) / 3 (too few) |
| `read_byte(timeout_ms) -> int` | one byte, or -1 |
| `sleep(ms)` / `discard()` | pause (at most 10 s) / drop unread input |
| `log(msg)` / `progress(done, total)` | diagnostics / progress bar |

A mod cannot import anything, not even a shared helper library. Each engine therefore carries
its own helpers (hex parsing, scramble). Shared helpers could later be handed in as a third
`init` argument. Classes cannot hold `const` yet, so failure codes are written as fields.

Engine lookup when a model says `engine = X`:
`driverhost.choose_engine([active_dir, shipped_dir], "X", model_ini, has_builtin)`.
1. It tries `<active>/engines/X.js` (the updated set), then `<shipped>/engines/X.js` (the
   set inside the app), taking the first that loads and answers `api() == 1`.
2. Otherwise it answers BUILTIN, and the app uses its compiled engine X.
3. `Choice.why` lists every engine passed over and why: the load error, the wrong API, or a
   watchdog stop at load. The app logs it.

With no built-in engine and nothing loadable, it fails `E_NO_ENGINE`. Engine names must be
`[A-Za-z0-9_-]`. A release can therefore hot-fix a built-in engine, but a bad download cannot
brick a model. `driverhost/fallback_test.dado` tests a broken file, the wrong API, a hang at
load, the shipped set first, no built-in, and a path-like name. The updater accepts a model whose
engine is built in (`Config.builtin_engines`, default `uv17pro uv5r`).

### Watchdog

Every driver call (`identify`, `download`, `upload`) and every load runs under a watchdog thread.
A load counts because it runs the module's top-level code and `init`. The watchdog calls
`#script_stop(vm, 200)` when either limit is reached:
* the driver has not touched the link for `idle_ms` (default 5 s). Each write, read, sleep and
  progress report resets this, and a read or sleep also adds its own wait.
* the whole call has run for `call_ms` (default 10 min).

Change both with `driverhost.set_limits`. What a stop does:
* It is polite first, so the script meets an `Error` and its `finally` blocks run. After 200 ms
  it is forced.
* From the moment the watchdog trips, every Link call fails at once. QuickJS checks for an
  interrupt only every so many operations, so a loop that mostly waits in Dado would otherwise
  take seconds to stop. Before this fix, the busy-loop test took 16.9 s.
* The call fails `E_TIMEOUT` (23) with a clear message, for example "the driver did nothing on
  the link for 5000 ms and was stopped". The `Driver` is dead afterwards: close it and load
  again.

`driverhost/watchdog_test.dado` covers:

| case | stopped after |
|---|---|
| idle spin | about 305 ms (300 ms limit) |
| spin that catches the polite stop | about 504 ms (forced) |
| loop that keeps the link busy | about 1503 ms (1500 ms cap) |
| top-level code that never finishes | about 307 ms |

It also checks that a stopped driver refuses further calls, and that drivers load and run
normally afterwards.

The safety rules in HANDOFF are enforced by the host, not by drivers: `tested = write`, a backup
before writing, and verify after writing. A driver's `upload` is reached only after those checks
pass.

`drivers/engines/uv17pro.dados` is a complete port of the UV-17Pro family:
* handshake, magics, scramble and regions, all read from the model INI
* download, and upload (upload is untested on hardware)

`dado test driverhost` runs it against an in-memory UV-5RM that serves `testdata/uv5rm.img`
scrambled, as the radio sends it. The test checks:
* the download matches the backup byte for byte
* the upload round-trips
* a short image is refused with code 8
* a silent radio fails with code 2
* the sandbox cases in section 5

## 3. The bundle and the manifest

Drivers come **only from tagged GitHub releases**. Every release, whether an app release or a
drivers-only release, carries the bundle as **flat release assets**:

* `drivers-manifest.json`
* one asset per file: `engines.uv17pro.js`, `engines.uv17pro.dados`, `models.uv-5rm.ini`, ...

`drivers-manifest.json` (format 1):

```json
{
  "format": 1,
  "driver_api": 1,
  "min_app": "0.1.0",
  "release": "v0.2.0",
  "serial": 202611081200,
  "created": "2026-11-08T12:00:00Z",
  "files": [
    {"path": "engines/uv17pro.js", "asset": "engines.uv17pro.js",
     "sha256": "<64 lowercase hex>", "size": 14185},
    {"path": "models/uv-5rm.ini", "asset": "models.uv-5rm.ini", "sha256": "...", "size": 1290}
  ]
}
```

The updater refuses the whole manifest unless all of these hold:
* `format` is 1.
* The release tag and every asset name match `[A-Za-z0-9._-]` and do not start with `.`.
* Each path is one of `engines/<name>.js`, `engines/<name>.dados`, `models/<name>.ini`,
  `README.md` or `LICENSE`. No `..` and no other directory is allowed.
* Each sha256 is 64 lowercase hex digits, and each size is at least 0.
* No path or asset appears twice.
* There are at most 1000 files.

Size limits: 4 MiB per file and 256 KiB for the manifest, both enforced by curl.

### Versioning and compatibility

| field | rule |
|---|---|
| `driver_api` | must be within the app's `[API_MIN, API_MAX]` (both 1 today). Add an API version only for a breaking change to the Link or driver contract. An app can support a range of versions. |
| `min_app` | the app must be at least this version (`a.b.c`, a `-suffix` is ignored) |
| `serial` | must be higher than the active set's serial (defaults to UTC `yyyymmddHHMM`). A lower serial is refused, which stops replays of old bundles. `allow_downgrade` overrides this. |
| per engine | `api()` is checked again at load time |

If the check fails, the app keeps its current drivers and the message says
"update the app".

### Making a release

```
python3 drivers/release.py --release v0.2.0 --out dist/assets --upload [--create]
```

`release.py` compiles the engines with dadoc and attaches the assets with `gh`. Every release
must run it, including app releases. It also rewrites `drivers/manifest.json`. Commit it as the record of what was shipped.

A GitHub Actions job could run the same two steps on a tag push. That would need dadoc on the
runner. Alternatively, commit the `.js` files and use `--no-compile`.

## 4. The updater

`updater.update_drivers(Config) -> Report` (or `update_drivers_with(c, progress)`), and
`updater.rollback(Config) -> Report`. A Report holds:
* `status`: UP_TO_DATE, INSTALLED, ROLLED_BACK or FAILED
* `stage`: where it stopped
* `message`
* `release`: the active release, and `previous`: the one kept for rollback
* `files` and `bytes`

`describe(r)` gives one line. `updater/tool` is a small CLI for manual use:
`dado run updater/tool -- update|rollback|where`.

Config defaults:
* `owner = Anaxarchus`, `repo = beautalks`
* `tag = ""` means the latest release
* `proto = "=https"`, `max_time_s = 60`
* `data_dir`: the OS config dir plus `/beautalks`. On macOS that is
  `~/Library/Application Support/beautalks`; on Linux, `~/.config/beautalks`.

Flow:
1. GET `https://github.com/<owner>/<repo>/releases/latest/download/drivers-manifest.json`, or
   `.../releases/download/<tag>/...` when pinned. GitHub redirects this to its asset CDN.
   * This avoids `api.github.com`: no rate limit of 60 requests per hour, and no API JSON to
     parse.
   * If the latest release has no bundle, the result is a 404 and the active set is kept.
2. Validate the manifest and check compatibility, as in section 3.
3. Fetch each file from `.../releases/download/<manifest.release>/<asset>`. The URL is **pinned
   to the tag the manifest names**, so a release published during the update cannot mix two
   bundles. Each file goes into `<data>/drivers/staging/incoming.<pid>/<path>` and must match
   its size and SHA-256 exactly. Any mismatch deletes the staging directory, and nothing is
   activated or executed.
4. Every `models/*.ini` must name an engine that the bundle carries or the app has built in.
5. Rename the staging directory to `sets/<release>`, point `previous` at the old active set,
   then point `active` at the new set. Each link is a new symlink renamed over the old one,
   which is atomic under rename(2). Other sets are pruned. The app loads only from `active`.

curl is run as an argv array through `core:os/proc` `exec`, never through a shell:

```
curl -q --fail --silent --show-error --location --proto =https --proto-redir =https
     --max-time 60 --max-filesize <size> --retry 2 --user-agent beautalks-driver-updater
     --stderr <dest>.curl-err --output <dest> <url>
```

* `-q` makes curl ignore `~/.curlrc`.
* Every value placed in a URL has passed the `safe_name` check first.
* `--proto` can be changed only through Config, which tests use. The app never exposes it.

Rollback: `rollback()` swaps `active` and `previous`, and calling it again rolls forward. A failed
update never touches `active`.

Tests: `dado test updater`, all passing under ASan and UBSan. They run against fake releases that
`release.py --github-layout` builds:
* file:// tests:
  * a fresh install, then a second run that reports up to date
  * a tampered engine is rejected, the old set stays active, and staging is empty
  * a newer release installs and keeps the old one as `previous`
  * rollback, then roll forward
  * an older serial is refused
  * driver API 2 is refused
  * a manifest with a `../` path is refused
  * a pinned tag that does not exist fails at the manifest; a pinned tag that is already active
    reports up to date
  * `--proto =https` refuses a `file://` URL
* `python3 -m http.server` on 127.0.0.1 tests:
  * an install
  * a tampered model is rejected

Against the real repo, which has no releases yet, the tool fails safely:

```
FAILED (fetch manifest): ... curl exit 22: ... 404 (https://github.com/Anaxarchus/beautalks/releases/latest/download/drivers-manifest.json)
```

## 5. Security model

**Trust root:** HTTPS to github.com and its asset CDN, through the system curl and the system CA
store. On top of that:
* the manifest hashes, which bind every file to the manifest fetched over that channel
* serial monotonicity, which stops a replay of an older bundle

Whoever can publish a release on the repo can ship drivers. Protect the repo with 2FA, branch
and tag protection, and a minimum of maintainers.

**Driver sandbox (defense in depth).**

What a driver mod can reach:
* only the `link` and `model` its loader hands it
* the runtime blocks static `import` of Dado bindings, JavaScript and packages at load
  (the test checks this)
* the engine is QuickJS without its std or os modules, so there is no `std`, `os`, `fetch`,
  `require` or `process`

**Finding from the spike:** the import block covers only modules whose name starts with
`mod:`.
* Code compiled from a string, `(0, eval)("import('dado:main')")` or `new Function(...)`, has
  another module name, so the resolver lets it import:
  * `dado:<pkg>`: **every Dado function that any compiled-in script calls**
  * `dados:host`: load any `.js` file
  * `dados:mods`
* The spike's hostile mod did exactly that.

Mitigation, implemented in `driverhost/harden.js` and called by the loader before any mod loads:
* make `eval` and `Function` undefined
* make the `constructor` of the Function, AsyncFunction, GeneratorFunction and
  AsyncGeneratorFunction prototypes non-writable `undefined`

**Second finding (QA follow-up):** QuickJS-ng has V8's `Error.prepareStackTrace`, and its
CallSite objects answer `getFunction()` for every frame.
* A mod's top-level code runs inside `Script.load`. Setting the hook there and creating an
  `Error` handed it the host's own functions: `load` (dados:host), `__dados_load`, and
  `Loader`'s `init` and constructor.
* At call time it got `Loader.identify`.

The lockdown now also replaces `Error.prepareStackTrace` with a non-configurable accessor that
is always `undefined` and ignores writes, so stacks stay strings. It also seals
`globalThis.__dados_failure`, the host's failure hook. Every sealed property is non-writable and
non-configurable, so a driver cannot undo the lockdown.

Tests, all passing:
* `driverhost/testdata/hostile.js` finds every door shut (`driverhost_test.dado`).
* `driverhost/sandbox_test.dado` tests dynamic `import()` written in the mod's own source (not
  through eval). `testdata/imports.js` starts imports of the following, all rejected:
  * `dado:driverhost`, `dado:main`, `dados:host`, `dados:mods`
  * `./target.js`, an absolute path, and a spoofed `mod:<abs>` name
  * package scripts `driverhost/Link` and `driverhost/Loader`
  * `js:harden.js`
* **How we know the job queue ran:** `identify()` #1 starts the imports and returns. `identify()`
  #2 reads the results. Two controls must have settled by then:
  * `import("dados:runtime")`, the one import a mod is allowed, must be "resolved"
  * a plain `Promise.resolve().then(...)` counter must be 1

  No import may still be "pending". If jobs did not run between calls, every import would be
  pending and the test fails. (QuickJS runs pending jobs as a call into the script returns.)
* The same fixture's **top-level** code checks that `eval` and `Function` are already
  `undefined` and that `prepareStackTrace` yields no functions. This proves `lockdown()` runs
  before any driver code: `Loader.init` calls it before `Script.load` evaluates the module.
* `testdata/escapes.js` finds none of the following:
  * timers (`setTimeout`, `setInterval`, `setImmediate`), `Worker`, `ShadowRealm`,
    `WebAssembly`
  * `std`, `os`, `scriptArgs`, `require`, `process`, `fetch`, `Deno`, `Bun`, `load`,
    `evalScript`
  * any `import.meta` keys, or host symbols on `globalThis`
  * CallSite functions, or a `captureStackTrace` leak

  Every attempt to undo the lockdown also fails: redefining or assigning `eval`, deleting
  `Function`, redefining `Function.prototype.constructor` or `prepareStackTrace`, and swapping
  `__dados_failure`. QuickJS has no second realm (no iframes, no ShadowRealm), so there is no
  fresh, unlocked `Function` to fetch. Each driver also runs in its own VM.

**Rules for the codebase** (because the bindings table is program-wide):
* No compiled-in script may call a Dado function that touches files, network or processes.
* The `dh_*` functions take no paths. They act only on the wire the host bound for the current
  call, and they fail when no call is in progress.

Not yet covered, and recommended:
* **Memory.** Give each driver VM a capped allocator: `#script_vm(alloc)` takes one.
* **Upstream.** Report the eval/Function resolver gap to Dado. The resolver should treat code
  evaluated inside a mod as the mod's own.

**Future work, not planned now (owner decision): a signed manifest** (minisign or signify, Ed25519):
* The maintainer holds an offline Ed25519 key. The app embeds the public key, or two keys, to
  allow rotation.
* (Future work; the owner decided against signing for now.) `release.py` signs `drivers-manifest.json` and publishes `drivers-manifest.json.minisig` as an
  extra asset.
* Before parsing, the updater fetches both files and verifies the signature in Dado. Ed25519
  verification is small (about 300 lines, or a vendored C file such as TweetNaCl or Monocypher's
  `crypto_ed25519_check`). Do not depend on a minisign binary, which is not installed on macOS or
  Linux by default.
* The signed manifest should also carry `serial` and `release`. It already does, so a replay or a
  release swap fails verification.
* A signature moves the trust root from "whoever can publish a GitHub release or compromise its
  delivery" to "whoever holds the key". It also allows mirrors.
* Key loss or rotation needs an app release.

## 6. Integration notes for the radio core

* `driverhost.Wire` has the same methods as `radio.Link`: `send`, `recv`, `sleep_ms`,
  `discard`. driverhost does not import `radio`, so the app needs a 10-line adapter
  `type ScriptWire using driverhost.Wire` that holds a `^` to the app's serial link and forwards.
  Alternatively, the core can declare its port type `using radio.Link, driverhost.Wire`.
* Failure codes: drivers use radio.LinkError numbers 1 to 8. The host adds 20 (wrong API),
  21 (load failed), 22 (no link bound), 23 (stopped by the watchdog) and 24 (no usable engine).
* A driver call keeps its wire in package storage for the length of the call, so the compiler
  requires the wire to outlive the caller's frame: allocate it with `#new`, or hold it at package
  level.
* The host must not hold an engine's progress callback beyond a call. driverhost reports progress
  through a `(fn, ctx)` pair shaped like `radio.Progress`.
