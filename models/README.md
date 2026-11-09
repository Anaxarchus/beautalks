<!-- beautalks - radio programming software
     Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later. -->
# Model definitions

One INI file per radio model. A model in a known family (engine `uv17pro` or
`uv5r`) is just a file here; no recompile. The app loads them from a
configurable directory (`--models DIR`, `$BEAUTALKS_MODELS`, `./models`, or
`<program>/../models`), so an updated drivers/models folder can override these.

The files are generated from CHIRP constants by `tools/gen_models.py`
(`python3 tools/gen_models.py models`); edit the generator, not the INI, or the
next run overwrites your change.

## Keys

| section | key | meaning |
|---|---|---|
| model | vendor, name, aliases | display name; `aliases` (comma list) also match `--model` |
| model | engine | `uv17pro` or `uv5r` |
| model | tested | `untested`, `read` (download confirmed on hardware) or `write`. Writes need `write` or the user's explicit override; backup + verify always run |
| model | source | the CHIRP class it comes from |
| link | baud, block | serial speed, block size |
| link | ident | uv17pro: space-separated `PROGRAM...U` idents (tried in order) |
| link | magics | space-separated `hex:..[/replylen]`; uv17pro: sent after the ident; uv5r: the ident magics tried in order |
| link | key | uv17pro scramble key `hex:434F2037` ("CO 7") or `none` |
| link | regions | uv17pro: `addr+len ...`, concatenated into the image |
| link | aux, orig_check, basetype | uv5r: aux block present; how CHIRP's `_is_orig` decides (`bfb`/`never`); `_basetype` words (`_` = space) |
| detect | model_reply | uv17pro: text inside the 'M' reply that confirms this model |
| detect | ident_reply | uv5r: hex prefix of the 8-byte ident that confirms this model |
| channels | count, first, start, stride, empty_at, empty_byte, blank | channel array; `blank` is the new-channel template |
| channels | rx, tx, rx_tone, tx_tone, power, wide / narrow, scan, bcl, name | field specs: `<off> lbcd <n>`, `<off> tone_bf`, `<off> bits <bit> <width>`, `<off> text <n> [table <addr> <stride>]`; `narrow` = a bit that is set for NFM |
| channels | powers, watts | power level names in stored order; watts for display |
| channels | rx_bands, tx_bands, am_bands | hardware limits in MHz (`136-174 400-520`); `am_bands` = where the radio receives AM |
| channels | modes, charset | `FM,NFM[,AM]`; characters a name may use |

## Models

UV-17Pro family (CHIRP `baofeng_uv17Pro.py`): UV-5RM (`tested = read`), UV-17Pro,
UV-21ProV2, UV-25, UV-17ProGPS, GM-30 Plus, GM-30 Pro, GM-21, UV-32, UV-21ProGPS,
UV-28Plus, MaxTalker P15, MaxTalker MT-5RM, K5-Plus, UV-5RM Plus, GM-5RH, UV-5G Plus,
UV-17R-Plus, UV-5RH, BF-F8HP-PRO, K6, UV-5R Mini, UV-5G Mini.

UV-5R family (CHIRP `uv5r.py`): UV-5R (+ aliases UV-5RE, UV-5X, RT5R, RT5RV, RT5,
RH5R, UV-5R EX, A-5R; `tested = read`), UV-5G Pro, F-11, UV-82, UV-82X3, UV-6,
KT-980HP, BF-F8HP (+ its aliases), UV-82HP, UV-5RX3, GT-5R, UV-5G.

Every registered class of both CHIRP files is covered. Not carried over (no
model skipped, but these CHIRP behaviours are not in the generic layout):

- **AM** is not a stored bit: as in CHIRP, a channel whose receive frequency is
  in `am_bands` is AM. `apply` changes the mode accordingly and says so.
- **UV-5R 220 MHz radios**: CHIRP picks the 220 or the UHF band from the image's
  band byte; the definition lists 130-176, 220-260 and 400-520 together (CHIRP's
  no-image list). The upload guard (220 image vs non-220 radio) is ported.
- **GMRS models** (GM-30 Plus/Pro, GM-21, UV-5G Mini, GT-5R): CHIRP's software
  restrictions on GMRS interstitials and fixed channels are not enforced
  (owner: beautalks does not police frequencies). GT-5R's hardware TX range
  (144-148 / 420-450) is in `tx_bands`. UV-5G Mini channels 1-30 are fixed in
  the radio; editing them is not yet blocked.
- **Per-channel extras** (PTT-ID, S-code, scramble, FHSS, sqmode) are not
  exposed, but encode is read-modify-write so they are kept as they are.
- **BLE upload** block size (UV-5R Mini over Bluetooth) is not supported.
- Only the owner's UV-5RM 'M' reply (`5RH`) is known; other uv17pro models
  sharing an ident rank by `tested`, so detection lists them all.
