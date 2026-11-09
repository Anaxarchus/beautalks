# beautalks — handoff notes (source of truth for agents)

beautalks is a radio (walkie-talkie) channel programmer written in **Dado** (dadolang), GPLv3,
porting protocol/layout knowledge from CHIRP (GPLv3). Owner: Anaxarchus. Target: macOS
(Mac mini, Apple silicon) first, Linux second.

## Goals (from the owner)
- Program channels on many radio models. "Ship as many as we can"; owner has many radios.
- **Auto-detect** the connected model (CHIRP makes you pick a model; that's a pain point).
- **Extensible**: a new model in a known family = a data file (INI profile in `models/`), no
  recompile. A genuinely new protocol = an engine (Dado) or later a DadoScript mod
  (`Script.load`, see dado docs/language.md ~line 3650).
- **Graphical UI** using Dado's `app:ui` (cell-grid UI over sokol). CLI too, for scripting/tests.
- Safety: never write to a radio unless the profile is `tested = write`; always back up the
  radio's current image before a write; verify after writing (read back + compare).

## Environment (cloud container — agents work here)
- Scratch root: `S=/tmp/claude-0/-home-claude/a05a8cd4-55ac-5cb3-a9b5-1513a2f56652/scratchpad`
- Toolchain: `export PATH=$S/dadoinst/bin:$S/bin:$PATH` then `dado check <pkg>`, `dado build`,
  `dado run`, `dado test`, `dado api core:x`, `dado doc core:x`, `dado explain ERRxxxx`.
  Read `$S/dado/AGENTS.md` first (the Dado primer — Dado is NOT Go/Python; see its table).
- Dado source/docs: `$S/dado` (collections/, docs/language.md, docs/reference.md).
- CHIRP source: `$S/chirp/src/chirp/drivers/` (uv5r.py, baofeng_uv17Pro.py, baofeng_common.py…).
- Project: `$S/beautalks` (this folder). The owner's real folder is on his Mac
  (`~/dev/Dado/beautalks`); the supervisor syncs files there. Do not touch the Mac.
- Real radio backups exist OUTSIDE the project for local cross-checks only (private data,
  never commit): `$S/uv5rm_backup.img` (UV-5RM, 33664 B), `$S/uv5re_backup.img` (UV-5RE, 6472 B).

## Confirmed on real hardware (cable: CH340, /dev/cu.usbserial-140)
### UV-17Pro family (owner's UV-5RM; CHIRP class BF5RM)
- 115200 8N1. Send `PROGRAMBFNORMALU` → `06`. Then magics in order, each answered with N bytes:
  `46` ('F') → 16 bytes (got `01 36 01 74 04 00 05 20 02 00 02 60 80 84 8A 94`);
  `4D` ('M') → 15 bytes (got ASCII `5RH     +L00000`);
  `53454E44 21050D010101041108050D0D01110F0912091004 00` ('SEND'+…) → 1 byte (`06`).
- Read: send `52 aH aL 40` → reply 4-byte header (`52 aH aL 40`) + 0x40 data. No acks.
- Write (CHIRP, not yet tried on hardware): `57 aH aL 40` + 0x40 scrambled data → reply `06`.
- Regions (radio addr+len): 0x0000+0x8040, 0x9000+0x40, 0xA000+0x2C0, 0xD000+0x40; image is
  their concatenation (0x8380 bytes).
- Scramble: XOR with 4-byte key `"CO 7"` (BF5RM; UV-5RM Plus uses `"C SL"`), skipping bytes
  equal to 0x00, 0xFF, key byte, key byte^0xFF, and key bytes equal to space. See `_crypt` in
  baofeng_uv17Pro.py. Same function both directions.
- Channels: 1000 × 32 bytes at image 0x0000, numbered 1..1000. Empty when byte 0 == 0xFF.
  Layout: rx lbcd[4] @0, tx lbcd[4] @4, rxtone u16le @8, txtone u16le @10, scode @12,
  pttid @13, byte14 bits0-1 = power (0 High,1 Low,2 Medium for 5RM), byte15: bit6 wide,
  bits5-4 sqmode, bit3 bcl, bit2 scan, bit0 fhss; @16..19 unknown; name text[12] @20 (FF pad).
  New channel template: 16×00 then 16×FF. Erased channel: 32×FF.
- The radios used for development belong to someone else: their images stay off the repo;
  tests use synthetic fixtures (tools/make_fixtures.py).

### UV-5R family (owner's UV-5RE; CHIRP uv5r.py class BaofengUV5R, firmware `HN5RV011`)
- 9600 8N1. Send magic `50 BB FF 20 12 07 25` one byte at a time, 10 ms apart → `06`;
  send `02` → ident 8 bytes `AA 30 76 04 00 05 20 DD` (read bytewise until DD, ≤12; 12-byte
  form is compacted per CHIRP); send `06` → `06`. Other magics in uv5r.py (UV-82, UV-6, …).
  A failed magic needs ~2 s pause before the next try.
- Read block: send `53 aH aL len`; for every request EXCEPT the first, radio first sends `06`;
  then header `58 aH aL len` + data; then WE send `06` and sleep 50 ms.
- Download order (CHIRP): 0x1E80 (first, discarded), 0x1EC0, 0x1FC0 (firmware = blk1[48:62];
  dropped-byte quirk if blk2[15]==0xFF), then main 0x0000..0x1800 step 0x40, then aux
  0x1EC0..0x1FC0 step 0x40 and 0x1FC0..0x2000 step 0x40 (or 0x10 if quirk).
  Image = ident(8) + main + aux.
- Upload is guarded in CHIRP (`_do_upload`, uv5r.py ~615): firmware/aux-area matching, only
  ranges (0x0008,0x0CF8),(0x0D08,0x0DF8),(0x0E08,0x1808) of main by default; write frame
  `58 aH aL len`+data → `06`. Port this logic faithfully before enabling writes.
- Channels: 128 × 16 bytes at image 0x0008, numbered 0..127; empty if byte0 == 0xFF.
  rx lbcd[4] @0, tx lbcd[4] @4 (tx FF*4 or 00*4 = TX off), rxtone u16le @8, txtone @10,
  byte12 bits0-3 scode, byte14 bits0-1 power (High, Low; tri-power models High, Low, Mid?
  check UV5R_POWER_LEVELS3), byte15: bit6 wide, bit3 bcl, bit2 scan, bits0-1 pttid.
  Names: table at image 0x1008, 16 bytes per channel, 7 chars, FF pad.
  New channel: 16×00. Erased: record 16×FF and name 16×FF.
- Never "fix" channel data automatically; odd pairs are shown, not changed.

### Tones (both families)
16-bit word: 0/0xFFFF off; ≥0x258 CTCSS in 0.1 Hz; 1..0x69 DCS index+1; ≥0x6A inverted DCS
index+0x6A, index into DCS_CODES (CHIRP DTCS_CODES + 645, sorted, 105 codes). Implemented in
`radio/codec.dado`.

## Code so far
- `serial/serial.dado` — termios serial port (open/close/write/read_into with timeout/
  discard_input/set_lines/pause). Used on hardware (CH340, macOS): settles 200 ms after open.
- `radio/codec.dado` — byte codecs + tones. Passes check.
- `radio/profile.dado` — INI model profiles + field-spec layouts. **Does not check yet**
  (LNT0613 pass-by-pointer lints, fs.Listing API misuse — see `dado api core:os/fs`).
- `explore/*.py` — the Python probes that worked on real hardware (reference behaviour).
  `explore/uv5rm_probe.py` and `explore/baofeng_probe.py` (fixed UV-5R block reads).

## Planned architecture
```
serial/      termios port
radio/       codec, profile (INI), channel (decode/encode via Layout), image I/O, csv
             engines: uv17pro.dado, uv5r.dado (each: identify, download, upload)
             detect.dado: try engines/idents in order (9600 UV-5R magics first, then 115200
             PROGRAM... idents — this order worked on the real 5RM), match replies against
             profiles' [detect] keys (model_reply = substring of 'M' reply; ident_reply = hex
             prefix of UV-5R ident), report candidates.
models/      *.ini — one per model (uv-5rm.ini, uv-5r.ini first; then the rest of both CHIRP
             families: UV-17Pro, UV-17ProGPS, UV-21Pro, F8HP Pro, K5-Plus, GM-5RH, UV-5R Mini,
             UV-82, UV-6, F-11, RT5, UV-5R EX, A-5R, UV-5G Pro … each `tested = untested`).
cli/         `beautalks` CLI: ports, detect, read -o x.img, channels x.img, export x.img -o
             x.csv, import x.img x.csv -o y.img, write x.img (refuses unless tested=write).
gui/         app:ui channel editor (see UI plan from the design agent).
tools/emu.py pty radio emulator for both families, serving a backup image, so the whole
             serial path is tested without hardware.
```
Profile INI keys used by profile.dado: [model] vendor,name,aliases,engine,tested,source;
[link] baud,ident,magics (space-separated `hex:XX/replylen`),key,block,regions
(`0x0000+0x8040 …`); [detect] model_reply, ident_reply; [channels] count,first,start,stride,
empty_at,empty_byte,blank(hex),rx,tx,rx_tone,tx_tone,power,wide,scan,bcl,name (field specs:
`<off> lbcd <n>` | `<off> tone_bf` | `<off> bits <bit> <width>` | `<off> text <n>
[table <addr> <stride>]`), powers (comma list).

## CSV (our own, simple; CHIRP CSV import later)
`number,name,rx_mhz,tx_mhz,rx_tone,tx_tone,power,mode,scan,bcl` — tone `""`|`69.3`|`D023N`|
`D023I`; tx_mhz empty = TX off; mode `FM`|`NFM`; scan/bcl `yes`/`no`.

## Hardware-verified writes (2026-11-08)
- UV-5RM (`models/uv-5rm.ini`, `tested = write`): read → safe write (backup, 526 W blocks all
  acked, verify) → read, back to back without power-cycling, all identical; the write and the
  second read reused the open programming session (0 idents). After a fresh power-on the radio
  ignored the first two idents and answered the third (~3.5 s): the ident retries
  (`radio.IDENT_TRIES` = 3, 500 ms apart, 1 s reply timeout) cover it, including detection's
  remembered fast path.
- UV-5RE (`models/uv-5r.ini`, `tested = write`; firmware HN5RV011): read → guarded safe write
  (6432 B, CHIRP default ranges) → read, identical; detection right after the write took one
  attempt, 7.3 s (waited out the ~6 s clone-session quiet time).
- Both radios worked normally afterwards. Session behaviour per family: `radio.session_info`.
