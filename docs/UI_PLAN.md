# beautalks: UI/UX plan (for owner review)

Status: **proposal**. Nothing here is built yet. Concepts are offered with tradeoffs so
Anaxarchus can choose before code is written. Sizes are in **cells** (app:ui is a monospace
cell grid). The main mockups are drawn at 120 cells wide, which is roughly a 1440x900 window
at a 12x25 px cell.

**Words used here** (owner's naming):
- **Profile**: a *model-independent* channel list ("Family Alaska", "Fishing trip"). It is
  the thing you edit, keep and move between radios. It has positions, not radio slots.
- **Model definition**: the per-radio-model INI in `models/` (band limits, slots, name length,
  power levels, `tested = …`). It was called "profile" in `HANDOFF.md`.
- **Radio image**: the raw memory of one radio model (a read, a backup, or what will be
  written). It is bound to one model.
- **Channel library**: curated read-only CSV sets (FRS, GMRS, MURS, NOAA incl. Alaska
  transmitters, marine, interop, ham calling + Alaska repeaters, aviation, Alaska state),
  each entry with a licence note. Another agent is building it. You copy entries from it into
  profiles.
- **Diagnostics**: the engine's per-channel results when it fits a profile onto a model.
  ✖ **error** = the channel is skipped; ! **warning** = it is changed to fit; i **info** = advisory.

Sources read: `HANDOFF.md`; `dado/collections/app/ui/` (UIS_FOR_DUMMIES.md, OUTLINE.md and the
file headers of ui, layout, widgets_*, modal, theme, chrome, pixels and edit_columns);
`app/input/input.dado` (modifiers, drag-and-drop); `core/jobs`, `core/threads`.

---

## 0. Design principles

1. **The profile is the main object; a radio is where it goes.** Anaxarchus thinks "my family's
   channels" and "put them on that radio". He does not think "UV-5RE slot 14". The UI is
   organised around profiles. Radios, images and backups support them.
2. **Never ask "which model?" first.** Plug in and press one key. The app says what it found
   and why. Asking is the fallback when detection is ambiguous, and then only with evidence.
3. **Reading is always safe; writing is earned.** Reading works for every model definition.
   Writing is visibly locked unless the model definition is `tested = write`, the radio on
   the cable is re-identified as the right model, and a fresh backup exists.
4. **Show what the radio will actually get, before it gets it.** Every profile-to-radio move
   goes through a preview that lists every skipped and changed channel and lets you fix them
   in place.
5. **Inform, never police.** Licence and service information (FRS, GMRS, ham, MURS, marine,
   Part 90, aviation, …) is shown as a *neutral, grey informational hint*. It is never a
   block, never red, never a confirm prompt and never counted as a problem. The **only hard
   checks** are what the radio physically cannot store or do: a frequency outside the model's
   band limits, a name too long for the model, an invalid tone code, or a mode the model lacks
   (e.g. AM).
6. **No file dialogs needed.** app:ui has none. The app keeps its own **Library** folder
   (profiles, backups, images, CSVs) and shows it inside the app. Import is drag-and-drop
   onto the window (app:input already delivers `Drop` events with paths) or a typed path.
7. **Keyboard first, mouse welcome.** Every action has a key, and every key hint on screen
   can also be clicked.
8. **Speak ham *and* FRS.** Duplex + offset by default (what repeater users expect). Raw
   RX/TX is one key away (what FRS/GMRS split entries and CSVs actually are).

---

## 1. Core user flows

### 1.1 Connect and detect
```
plug cable ─► app notices a new serial port (polls the port list about every 1 s while idle)
           ─► status: "New port cu.usbserial-140. Turn the radio on, then press F5 (Detect)"
F5 Detect ─► try UV-5R magics @9600 ─► try PROGRAM… idents @115200   (order from HANDOFF)
           ─► 1 match ............ identity panel fills in; Read / Apply become the next keys
           ─► >1 match ........... "Which radio is this?" with evidence (§3.6)
           ─► reply, no match .... "Unknown radio" with the raw reply; offer Teach (§1.10)
           ─► no reply ........... checklist error (§3.5)
```
- Auto-detect on plug-in is optional (Q4). Probing sends bytes to whatever is on the port,
  so the default is to notice the port and wait for F5, with a setting for auto-detect.
- If exactly one serial port looks like a programming cable (CH340/PL2303/CP210x by name),
  it is pre-selected. Several ports bring up a small picker. Zero ports bring up driver and
  permission help.
- The app remembers `ident → model choice`, so an ambiguous radio asks only once.

### 1.2 Read (and back up)
- F3 Read shows a progress dialog (§3.4). Cancel is always safe during a read.
- A successful read is **always saved** as a backup:
  `Library/backups/UV-5RM/2026-11-08_1402.img` plus a sidecar with model, ident, port and
  app version. This happens on every read, not only before writes. It is cheap insurance,
  and it gives you history for free.
- The read opens as a **radio image** tab ("UV-5RM radio 14:02"), with the same grid as a
  profile but in radio slots. The obvious next step is shown in the status line:
  **"Save as profile"** (Ctrl+Shift+S).

### 1.3 Profiles: create, edit, save
**Create** a profile from any of these:
- **From a radio** (after a read, or from any backup): channels go into the profile in slot
  order, empties dropped, with each slot number remembered as a "preferred position".
- **From channel library sets** (§1.4): "New profile from library…" with sets ticked.
- **From CSV** (ours or CHIRP's), by drag-and-drop or a typed path.
- **Blank** or **Duplicate** of an existing profile ("Fishing trip" from "Family Alaska").

**Edit** in the grid (§3.1). A profile channel is a superset of what radios hold:
- Name (up to ~16 chars) and an optional **Short name** used on radios whose names are
  shorter (Q5 offers alternatives).
- RX, duplex/offset (or TX), TX tone, RX tone, power as **Hi / Mid / Lo** (abstract; mapped
  to the nearest level per radio), mode FM / NFM / AM, scan, BCL, and advanced fields
  (PTT-ID, scramble, …) that only some models honour.
- Read-only provenance: "from set Ham rpt: AK", plus the library's licence note.

**Fits column** (the key idea that makes profiles first-class): a profile has a list of
**targets**, the models it is usually put on (learnt from past applies, editable). Each row
shows one badge per target, e.g. `✓ !  ✖` for UV-5RM, UV-5RE and UV-17Pro. You see while
editing that "Anchorage Tower won't go on the UV-5RE", without opening a preview. The
header shows totals per target, and clicking a target opens its preview.

**Save**: Ctrl+S writes `Library/profiles/<name>.csv` (our CSV plus the extra columns:
short name, notes, preferred position, source). A plain CSV keeps profiles hand-editable,
diffable and easy to share.

### 1.4 Channel library: browse and add
Ctrl+L opens it from any profile (or it shows in the Concept B sidebar):
```
╭─ Add from channel library → profile "Family Alaska" ─────────────────────────────────────────────────────────────────╮
│ Filter: [ alaska wx_______ ]       Fits: (•) any  ( ) UV-5RE  ( ) all targets       Show info notes [x]              │
│──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────│
│ Sets                        │    Name                 RX MHz     TX MHz     Tone      Mode  Licence / note           │
│ ▸ FRS (22)                  │ [x] WX Anchorage         162.55000  —          ·         NFM   NOAA, receive only      │
│ ▸ GMRS + repeater pairs (30)│ [x] WX Homer             162.40000  —          ·         NFM   NOAA, receive only      │
│ ▸ MURS (5)                  │ [ ] WX Kodiak            162.55000  —          ·         NFM   NOAA, receive only      │
│ ▾ NOAA Weather (7 + AK 52)  │ [ ] WX Seward            162.47500  —          ·         NFM   NOAA, receive only      │
│     ● Alaska transmitters   │ [x] WX Valdez            162.52500  —          ·         NFM   NOAA, receive only      │
│ ▸ Marine VHF (57)           │ [ ] WX Fairbanks         162.55000  —          ·         NFM   NOAA, receive only      │
│ ▸ Interop / mutual aid (12) │ [ ] WX Juneau            162.47500  —          ·         NFM   NOAA, receive only      │
│ ▸ Ham calling freqs (6)     │                                                                                        │
│ ▸ Ham repeaters: Alaska (84)│                                                                                        │
│ ▸ Aviation (AK, 40)         │                                                                                        │
│ ▸ Alaska state (18)         │                                                                                        │
│──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────│
│ 3 selected · 3 new · 0 already in profile          Insert: (•) at end  ( ) after row 24  ( ) replace selection       │
│ Space tick · ^A all in set · / filter · Enter Add 3 channels · Esc Close                                             │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```
- Left: sets as a tree (sets → sub-sets like "Alaska transmitters"). Right: entries with
  tick boxes, the frequency summary, and the **licence/service note in neutral grey**. Notes
  are information only and never stop you ticking anything. "Show info notes" hides them
  entirely for people who don't want them.
- Filter matches names, frequencies (`162.55`), places (`homer`) and notes (`marine`).
- **Fits** filter: dims entries a chosen target model can't take (e.g. aviation AM on a
  UV-5RE). They are dimmed, not hidden, so the library never looks smaller than it is.
- Already-in-profile entries are marked (same frequency, tones and mode) to avoid duplicates.
  Adding keeps the library's long name, suggests a short name, and records the source set.
- Insert at end / after the cursor row / replacing selected rows.
- A whole set can be added with one key (Ctrl+A on the set). "New profile from library" is
  this same dialog with the destination set to a new profile.

### 1.5 Apply a profile to a radio or model (the preview)
F7 "Apply to…" from a profile (or "Apply profile…" from a radio tab). Pick the target: the
radio on the cable (auto-detected), or any model (to produce an image/CSV without a
radio). The engine fits the profile and the **preview** opens:
```
╭─ Apply profile "Family Alaska" → Baofeng UV-5RE  (128 slots · names 7 · power H/L · 136–174, 400–520 · no AM) ───────╮
│ Placement:  start at slot [ 0  ]    ( ) keep positions  (•) pack in order    (•) overwrite  ( ) fill empty slots only│
│ Result:  48 channels → 46 written · 3 changed · 2 skipped · 9 info        Show: [ All ]  Problems  Skipped  Changed  │
│──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────│
│ Slot     Name    RX MHz    Dup Offset  TX t  RX t  Pw Mod Diagnostics                                                │
│    0     GMRS 1  462.5625              ·     ·     H  FM                                                             │
│   14  i  GMRS15R 462.5500  +   5.0     141.3 141.3 H  FM  short name used (name is 11 chars)                         │
│   22  i  WX ANC  162.5500  off         ·     ·     –  NFM short name used                                            │
│   29  !  Marine  156.8000              ·     ·     H  FM  name cut to 7: "Marine 16" → "Marine"  (same as slot 30)   │
│   30  !  Marine  157.1000              ·     ·     H  FM  name cut to 7: "Marine 22A" → "Marine" (same as slot 29)   │
│   35  i  KL7AA   146.9400  −   0.6     103.5 ·     H  FM  short name used                                            │
│    –  ✖  ANC TWR 118.3000              ·     ·     –  AM  SKIPPED: 118.3 MHz is outside this radio's bands; no AM    │
│    –  ✖  MRI     126.0000              ·     ·     –  AM  SKIPPED: 126.0 MHz is outside this radio's bands; no AM    │
│   37  !  2M CALL 146.5200              ·     ·     H  FM  power Mid → H (nearest; radio has H/L)                     │
│   38  i  AK MA   155.1600              ·     ·     L  NFM info: Part 90 channel (advisory only)                      │
│  46+     ·                                                slots 46–127 left empty                                    │
│──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────│
│ Slot 29 · fix here → Short name for "Marine 16": [ MAR 16_ ]   saved to the profile, used on every short-name radio  │
│                                                                                                                      │
│  Enter  Continue: check radio, back up, review, write    S  Save as UV-5RE image/CSV    F8  Next problem    Esc  Back│
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```
**Reading it:**
- **Header**: the target's limits in one line, so every diagnostic makes sense at a glance.
- **Placement** (re-runs the engine on change): *start slot*; *keep positions* (each
  channel goes in its profile position/preferred slot; collisions and overflow become
  diagnostics) vs *pack in order*; *overwrite* (radio's other channels erased) vs *fill
  empty slots only* (existing channels kept; the slot column then shows which existing
  channels are kept, dimmed).
- **Summary**: `48 → 46 written · 3 changed · 2 skipped · 9 info`. Each count is clickable
  and sets the filter.
- **Per-row badge** column: ✖ red (skipped; the row is dimmed with slot `–`), ! amber
  (changed; **the changed cell itself is highlighted** and the Diagnostics column says what
  changed from what), i grey (info; never coloured as a problem). Rows with no diagnostics
  have no badge.
- **Filter**: All / Problems (✖ and !) / Skipped / Changed. F8 / Shift+F8 jump to the next or
  previous problem. Info rows are excluded from "Problems".
- **Fix inline**: the cursor can go into the Name, Short, Pwr, Mode, tone and frequency cells
  of the preview. An edit is **an edit to the profile** (so it fixes every future apply);
  the engine re-runs and the badges update immediately. The bottom strip offers the most
  likely fix for the focused diagnostic (for a cut name, a short-name field pre-filled with
  a suggested abbreviation; for a duplicate name after cutting, it says so). Alt+Enter on a
  fix applies it "for this model only" if Q5 chooses per-model overrides.
- Skipped channels can't be "forced". The radio can't hold them. The preview just keeps
  them visible so nothing disappears silently.

**Then:** Enter goes into the write flow (§1.6) when a radio is connected and the model is
writable. Otherwise **S** saves a radio image/CSV for that model to the Library. For an
untested model the Enter label itself says why writing isn't offered.

### 1.6 Write (re-identify, backup, review, verify)
```
Enter from preview (or F4 on a radio image tab)
 ├─ model locked (not tested=write)? ─► explanation, no way past from this screen (§3.3)
 ├─ any ✖ left?  fine: skipped channels are simply not written (already listed in the preview)
 ├─ re-identify the radio on the cable ─► must be the previewed model, or stop
 ├─ fresh backup: read the radio now (fast on 5RE, ~10 s on 5RM) → Library/backups
 ├─ Review: what changes ON THIS RADIO, i.e. radio-now vs after-write (§3.3). This is a
 │   different question from the preview's "what changed from the profile"
 ├─ Enter "Write 46 channels"
 ├─ write with progress; cancelling mid-write warns first (§3.4)
 └─ verify: read back and compare the written ranges
      ├─ match ─► "Written and verified · backup <file>"; target remembered on the profile
      └─ mismatch/failure ─► recovery screen (§3.5): write again, or restore the backup
```

### 1.7 One profile → several radios
"Program several radios…" (from a profile, Ctrl+Shift+F7) is a production-line mode for
doing the family's radios in one sitting:
```
╭─ Program several radios with "Family Alaska" ────────────────────────────────────────────────────────────────────────╮
│ Each radio: detect → back up → preview (once per model) → write → verify.   Plug in the next radio when told.        │
│──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────│
│  #  Radio                 Model      Preview         Backup                    Write     Verify    Result            │
│  1  cu.usbserial-140      UV-5RM     ✓ approved      11-08 15:02 ✓             ✓         ✓         done 46 ch        │
│  2  cu.usbserial-140      UV-5RM     ✓ (same model)  11-08 15:05 ✓             ✓         ✓         done 46 ch        │
│  3  cu.usbserial-140      UV-5RE     ? new model     11-08 15:09 ✓             waiting                Enter: preview │
│  4  (plug in next radio)                                                                                             │
│                                                                                                                      │
│ Approved previews this session:  UV-5RM (46 written, 2 skipped)       Re-preview a model if the profile changes: yes │
│                                                                                                                      │
│   Enter  Continue      N  Next radio (skip this one)      L  Show log      Esc  Stop after this radio                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```
- Each radio: plug in, detect, automatic backup, **preview once per model per session**
  (approve the UV-5RM preview once, and the next UV-5RMs go straight to write, still with
  their own backup and verify), write, verify, then "unplug, plug in the next one".
- A changed profile, or different placement settings, invalidates approvals.
- A radio of a new model stops the line at the preview. A locked model is recorded as
  "skipped: model not writable" and the line moves on.
- A per-session log (saved to `Library/logs/`) lists each radio, ident, backup file and
  result. It answers "did I do Grandpa's radio already?"
- Concept B also shows, on each profile, its **targets with last-applied dates** and a
  stale marker ("Family Alaska changed since UV-5RE was programmed on 11-02").

### 1.8 Import / export
- Profiles are CSV already. Ctrl+E exports the current tab (profile or radio image) as CSV,
  or as CHIRP CSV later. The toast shows the path with **Copy path** and **Show folder**
  (macOS `open -R`, Linux `xdg-open`: one shell call, no dialog widget needed).
- Import: drag `.csv`/`.img` onto the window, or Ctrl+O and type/paste a path (a line edit
  with Tab completion). A CSV becomes a profile and an `.img` becomes a radio image tab.
- Rows copy and paste through the clipboard as CSV text (Ctrl+C/V), to and from
  spreadsheets and between tabs. A paste into a radio image tab runs the same diagnostics
  as a preview, shown as a small summary with "Show details".

### 1.9 Backups and history
- The Library shows Backups grouped by model, then date (newest first), with channel count
  and short ident.
- Opening a backup gives a read-only radio image tab. From there: **Save as profile**,
  **Restore to radio** (the write flow with this image, review included) and **Compare
  with…** (any two images of one model, or a profile vs a radio, using the review view).
- Retention: keep everything (files are 6–34 KB). Q6 asks where the Library lives.

### 1.10 Unknown radio: "teach me this model"
1. Detection got a reply that nothing matches (or nothing at all after trying everything).
2. The screen shows what was tried, each reply in hex + ASCII, and the nearest known family
   by score ("ident starts AA 30 like the UV-5R family").
3. Options:
   - **Save probe report** to `Library/probes/<date>.txt`, to hand to whoever writes model
     definitions. Always available.
   - **Try reading as <closest family>**: read-only, into a radio image tab flagged
     `UNVERIFIED LAYOUT`, with a plausibility score ("38 of 40 channels look valid: in-band
     freqs, valid tones, printable names"). If the score looks plausible, **Save as
     profile** works as usual, which rescues the channels even from an unsupported radio.
   - **Create model definition from this**: copies the closest family's INI to
     `Library/models/<name>.ini` with the observed ident and `tested = untested`. It is
     read-only by construction.
4. The app never offers to write here. Promoting a model to `tested = write` happens outside
   the GUI (Q2).

---

## 2. Three layout concepts for the main window

Parts shared by all three:
- **Grid**: one custom widget used for profiles (positions, Name+Short, Fits column), radio
  images (slots, model's name limit, Svc info) and the apply preview (slots, badges,
  diagnostics). The column sets differ; keys and editing are the same everywhere.
- **Radio identity**: model, how it was detected, port/baud, capability summary, and the
  write badge.
- **Inspector**: all fields of the focused channel in words, its fit per target, and its
  info note.
- **Key bar**: a bottom row of clickable key hints. It doubles as the buttons, since app:ui
  has no button widget yet.
- **Status line**: connection, last action, problem counts (errors and warnings only, never
  info), unsaved marker.

### Concept A: "Spreadsheet + inspector" (one tab at a time)
The window shows one thing: a profile, a radio image or a preview. The radio panel appears
when a radio is connected. Shown here with a radio image open:
```
╭─ Radio ──────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ ● Baofeng UV-5RM   detected by model reply "5RH"   cu.usbserial-140 @115200   1000 slots · names 12 · power H/M/L    │
│   VHF 136–174  UHF 400–520      ▐ UNTESTED · READ-ONLY ▌      read 14:02 · backup saved      showing: radio contents │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Channels ─────────────────────────────────────────────────────────────────────────╮╭─ Channel 23 ───────────────────╮
│   #  Name         RX MHz     Dup Offset     TX     RX     Pwr Mode Sc Info         ││ Name      GMRS15R              │
│                                               tone   tone                          ││ RX        462.55000 MHz        │
│   1  GMRS 1       462.56250                 ·      ·      H   FM   ✓  GMRS         ││ Duplex    +  (repeater)        │
│   2  GMRS 2       462.58750                 ·      ·      H   FM   ✓  GMRS         ││ Offset    5.00000 MHz          │
│   3  SIMPLEX      446.00000  spl 446.01250  ·      ·      H   FM   ✓  ham      !   ││ TX        467.55000 MHz        │
│   8  FRS 8        467.56250                 ·      ·      L   NFM  ✓  FRS          ││ TX tone   141.3 Hz CTCSS       │
│  15  GMRS 15      462.55000                 ·      ·      H   FM   ✓  GMRS         ││ RX tone   141.3 Hz CTCSS       │
│  23 ●GMRS15R      462.55000  +   5.00000    141.3  141.3  H   FM   ✓  GMRS rpt     ││           (CHIRP: "TSQL")      │
│  24  GMRS16R      462.57500  +   5.00000    141.3  141.3  H   FM   ✓  GMRS rpt     ││ Power     High                 │
│  30  MURS 1       151.82000                 ·      ·      H   NFM  ✓  MURS         ││ Mode      FM (wide)            │
│  36  WX ANCH      162.55000  off            ·      ·      –   NFM     NOAA rx      ││ Scan yes  BCL no               │
│  40  KL7AA RPT    146.94000  −   0.60000    103.5  ·      H   FM   ✓  ham rpt      ││ PTT-ID off  S-code 0           │
│  41  2M CALL      146.52000                 ·      ·      L   FM   ✓  ham          ││                                │
│  42  70CM RPT     444.10000  +   5.00000    D023N  D023N  H   FM   ✓  ham rpt      ││ ── Fits this radio ──────      │
│  43  ·                                                                             ││ ✓ in band (UHF 400–520)        │
│  44  ·                                                                             ││ ✓ name 7 of 12                 │
│  45  ·                                                                             ││                                │
│  46  ·                                                                             ││ ── Info (advisory) ──────      │
│  47  ·                                                                             ││ GMRS repeater pair. GMRS       │
│  48  ·                                                                             ││ needs an FCC licence (US)      │
│  49  ·                                                                             ││                                │
│  50  ·                                                                             ││                                │
│                                                                      23 / 1000     │╰────────────────────────────────╯
╰────────────────────────────────────────────────────────────────────────────────────╯
 ! ch 3: TX is 12.5 kHz above RX (446.0000 → 446.0125). Typo? F2 edit · ^I ignore              1 warning · 0 errors
 F1 Help  F2 Edit  F3 Read  F4 Write(locked)  F5 Detect  F6 RX/TX  F7 Apply profile  ^L Library  ^⇧S Save as profile
```
With a profile open, the radio panel shrinks to one line ("Radio: UV-5RM on
cu.usbserial-140 · F7 apply this profile to it"), and the grid shows the profile columns
(see the Concept B mockup).
- **Pros**: simplest mental model; widest grid; least to build beyond the grid itself; the
  inspector explains tones, duplex and licence notes in plain words.
- **Cons**: Library, channel library and backups are dialogs, which makes them less
  discoverable. Comparing a profile with a radio means switching back and forth. Batch
  programming is a dialog on top of everything else.

### Concept B: "Workbench" (Library sidebar + tabs)
```
                         Family Alaska ● × │ UV-5RM radio 14:02 × │ Apply → UV-5RE ×
╭─ Library ────────────╮╭──────────────────────────────────────────────────────────────────────────────────────────────╮
│ ▾ On the cable       ││ PROFILE "Family Alaska" · 48 ch · any model     Fits = 5RM 5RE 17Pro:  ✓   !2 ✖2   ✓         │
│   ● UV-5RM  usb-140  ││──────────────────────────────────────────────────────────────────────────────────────────────│
│ ▾ Profiles           ││ Pos Name             Short   RX MHz    Dup Offset  TX t  RX t  Pw Mod Fits  Info             │
│   ● Family Alaska  48││   1 GMRS 1                   462.5625              ·     ·     Hi FM  ✓ ✓ ✓ GMRS             │
│     Fishing trip   22││   2 GMRS 2                   462.5875              ·     ·     Hi FM  ✓ ✓ ✓ GMRS             │
│     Hunting camp   16││   8 FRS 8                    467.5625              ·     ·     Lo NFM ✓ ✓ ✓ FRS              │
│ ▸ Channel library 14 ││  15 GMRS 15 RPT      GMRS15R 462.5500  +   5.0     141.3 141.3 Hi FM  ✓ ✓ ✓ GMRS rpt         │
│ ▾ Backups            ││  23 WX Anchorage     WX ANC  162.5500  off         ·     ·     –  NFM ✓ ✓ ✓ NOAA rx          │
│   ▾ UV-5RM           ││  24 WX Homer         WX HOMR 162.4000  off         ·     ·     –  NFM ✓ ✓ ✓ NOAA rx          │
│      11-08 14:02  22 ││  30 Marine 16                156.8000              ·     ·     Hi FM  ✓ ! ✓ marine           │
│      11-02 09:13  22 ││  31 Marine 22A               157.1000              ·     ·     Hi FM  ✓ ! ✓ marine           │
│   ▸ UV-5RE (3)       ││  36 KL7AA Anchorage  KL7AA   146.9400  −   0.6     103.5 ·     Hi FM  ✓ ✓ ✓ ham rpt          │
│ ▸ CSV files (2)      ││  40 Anchorage Tower  ANC TWR 118.3000              ·     ·     –  AM  ✓ ✖ ✓ aviation         │
│ ▸ Model defs (24)    ││  41 Merrill Field    MRI     126.0000              ·     ·     –  AM  ✓ ✖ ✓ aviation         │
│                      ││  42 AK Mutual Aid    AK MA   155.1600              ·     ·     Lo NFM ✓ ✓ ✓ Part 90          │
│                      ││  43 ·                                                                                        │
│                      ││                                                                                              │
│                      ││                                                                                              │
│                      ││                                                                                              │
│                      ││                                                                                              │
│                      ││                                                                                              │
│                      ││                                                                                              │
│                      ││                                                                                              │
│                      ││                                                                                              │
│                      ││                                                                                              │
│                      ││──────────────────────────────────────────────────────────────────────────────────────────────│
│                      ││ 36 KL7AA Anchorage → TX 146.3400 · TX tone 103.5 · Hi · FM · scan · from set "Ham rpt: AK"   │
│                      ││ Short name is used on radios whose names are too short.   Info: ham repeater, licence needed.│
╰──────────────────────╯╰──────────────────────────────────────────────────────────────────────────────────────────────╯
 Profile OK · on UV-5RE: 2 skipped, 2 changed (F7 to preview)                                            ● unsaved
 F1 Help  F2 Edit  F3 Read  F5 Detect  F7 Apply to…  F9 Library  ^L Add from library  ^Tab Next tab  ^P Commands
```
- The sidebar puts **Profiles first**, then the radio on the cable, the channel library,
  backups, CSV files and model definitions. Double-click (or Enter) opens a tab. Dragging
  a profile onto "On the cable" means apply.
- Tabs hold profiles, radio images and previews side by side ("Apply → UV-5RE" is a tab, so
  you can flip between the profile and its preview while fixing things).
- The Fits column and the target summary make "will it fit my radios?" visible all the time.
- **Pros**: matches Anaxarchus's real situation (several radios, a few profiles, lots of
  backups); everything is on screen, so the missing file dialog is never felt; the channel
  library sits one click from the profile; batch mode and target history have a natural
  home.
- **Cons**: the most to build (sidebar tree source, tab state, cross-tab paste); the grid is
  ~24 cols narrower (the profile grid drops the Scn/BCL columns to the inspector strip);
  busier for a first-time user. F9 hides the sidebar (a split box with a hidden child gives
  the other all the room), which gives back Concept A's width.

### Concept C: "Guided steps" (a wizard around the profile)
A step strip on top: **① Profile ─ ② Radio ─ ③ Preview & fix ─ ④ Write & verify**. Each step
is a full page. ① is a profile picker with "edit" (the grid page) and "new from radio /
library". ③ is the preview mockup above at full size.
```
  ① Profile ─────────── ② Radio ─────────── ③ Preview & fix ─────────── ④ Write & verify
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ╭───────────────────────────────────────────────────────────────────────────────────────────╮
  │  Profile     ✓ Family Alaska · 48 channels · last changed today 13:55                     │
  │                                                                                           │
  │  Cable       ✓ cu.usbserial-140 (CH340 USB-serial)                                        │
  │  Radio       ✓ Baofeng UV-5RE · detected by ident AA 30 76 04 · firmware HN5RV011         │
  │  Model       uv-5re.ini · 128 slots · names up to 7 · power High/Low · no AM              │
  │  Writing     ✓ tested on this model (example, once tested)                                │
  │  Last time   this profile went on a UV-5RE on 11-02 (profile changed since)               │
  ╰───────────────────────────────────────────────────────────────────────────────────────────╯

     Enter  Preview Family Alaska on this radio      R  Read this radio first      Esc  Back
```
- **Pros**: very hard to get lost; backup, preview and verify are part of the path rather
  than options; good for once-a-season use and for family members.
- **Cons**: slow for someone doing many radios or many edits; reading and keeping backups
  of a radio without a profile is a side path; two UIs (wizard and editor) to keep consistent.

### 2.4 Grid columns

**Profile grid** (Concept B mockup): `Pos 4 · Name 16 · Short 7 · RX 9 · Dup 3 · Offset 7 ·
TX tone 5 · RX tone 5 · Pwr 2 (Hi/Md/Lo) · Mode 3 · Fits 2 per target · Info rest`.

**Radio image grid** (Concept A mockup): `# 4 (radio numbering: UV-5R 0-based, 5RM 1-based;
● = edited) · Name = model's limit (chars past it shown dim) · RX 10 · Dup 3 · Offset 10 ·
TX tone 6 · RX tone 6 · Pwr (model's levels) · Mode · Scan · Info`.

**Preview grid** (preview mockup): `Slot · Badge · result values · Diagnostics`.

**Duplex/offset vs raw RX/TX.** Ham-style (Dup + Offset) is the default, because repeaters
are where costly mistakes happen and "+5 MHz" shows intent. **F6** switches to raw
**RX | TX**. Storage is always RX + TX. `spl` is what any non-standard pair shows as (the
a 12.5 kHz mismatch shows as `spl 446.01250` with a soft "typo?" hint, and it is never
auto-fixed). Choosing `+`/`−` with an empty offset fills the band default (2m 0.6, 70cm 5.0,
GMRS 5.0), pre-selected so typing replaces it.

**Tones: three ways to show them (Q1).**
1. **TX tone / RX tone pair** (shown, recommended). Matches hardware and our CSV 1:1, with
   one rule ("tone I send / tone I need to hear"). The inspector adds the CHIRP name
   (Tone, TSQL, DTCS, Cross) for CHIRP veterans.
2. **CHIRP style** `Mode | Tone | ToneSq | DTCS | Pol | Cross`: familiar, but six columns and
   the confusion Anaxarchus already disliked.
3. **One "Squelch" summary column** (`T 100.0`, `TSQ 141.3`, `D023N`, `100.0/D023N`) edited
   through a picker: the narrowest, but slower to type and hides what is stored.

**Empty slots** (radio images) show `·` dimmed. The grid is virtualised, so 1000 rows cost
nothing. Ctrl+H hides empties.

---

## 3. Interaction details

### 3.1 Keyboard-first grid editing (all grids)
| key | action |
|---|---|
| arrows, PgUp/PgDn, Home/End, Ctrl+Home/End | move the cell cursor |
| type a printable char | start editing, replacing the value (spreadsheet style) |
| Enter or F2 | edit, keeping the value; Enter again commits and moves **down** |
| Tab / Shift+Tab | commit and move right/left (wraps to the next row) |
| Esc | cancel the edit |
| Space | toggle/cycle choice cells (Dup, Pwr, Mode, Scan, BCL) |
| Ctrl+Space | picker for the cell (tones, power, dup), filtered as you type |
| Del | clear the cell; on `#`/`Pos` or a row selection, delete channel(s) (undoable) |
| Shift+arrows | extend a row selection |
| Ctrl+Z / Ctrl+Shift+Z (Cmd on macOS) | undo/redo per tab, one step per commit |
| Ctrl+C / X / V | rows as CSV text; a paste runs diagnostics for the tab's model |
| Ctrl+D | duplicate the row |
| Alt+Up/Down | move rows up/down |
| Insert | insert an empty row (profile) or open a gap (radio image; warns if the last slot is used) |
| Ctrl+F | find by name/freq/note; F8 / Shift+F8 next/previous problem |
| Ctrl+L | channel library (insert at the cursor) |
| Ctrl+P | command palette: every action, searchable, with its key shown |

The grid parses input as you type and shows the normalised value before you commit:
- Frequency: `146.52`, or kHz (`146520`). Off-step values are kept, with a hint showing the
  value the radio will store.
- `147.255+` in RX sets Dup `+` with the band-default offset; `146.94-` likewise.
- Tones: `100`, `t100`, `d23`, `D023`, `023n`, `d23i`, `off`, `-`. A non-standard CTCSS value
  (`100.2`) can't be committed, and the nearest standard value is offered.

Mouse: click selects a cell, double-click edits, clicking a choice cell cycles it, the wheel
scrolls, dragging over `#` selects rows. Right-click opens the command palette pre-filtered
to row actions (there is no context-menu widget; the palette serves as one).

### 3.2 Validation: physical limits hard, licences informational
| check | where | level | shown as |
|---|---|---|---|
| tone not a valid CTCSS/DCS code | everywhere | **can't commit** | nearest valid offered |
| frequency outside the model's bands | radio image, preview | **error** (✖; skipped on apply) | cell red; reason in words |
| mode the model lacks (AM) | radio image, preview | **error** (✖) | "UV-5RE has no AM" |
| name longer than the model allows | radio image: can't type past it; preview | **warning** (! changed) | shows the cut name; offers a short name |
| more channels than slots / slot collision | preview | **error** (✖ skipped) | "no free slot (128 used)" |
| power level not on the model | preview, paste | **warning** (! mapped) | "Mid → H (nearest)" |
| tone/mode/feature the model lacks (e.g. cross-mode) | preview | **warning** (! changed) | shows the replacement |
| off the radio's tuning step | all | warning | shows the stored value |
| odd split (TX within 50 kHz of RX, not equal) | all | data-entry hint `!` "typo?" | never auto-fixed |
| licence/service note (FRS/GMRS/ham/MURS/marine/Part 90/aviation/NOAA receive-only) | all | **info**, grey | Info column + inspector; never in counts, never a prompt, never in the write review |
| duplicate entry | profile | info | `i` |

- A profile has no model of its own, so it can't have band errors. Its "will it fit"
  answers are the per-target Fits badges.
- **Errors never block Save or Write**: a ✖ channel is simply not written, and the preview
  already listed it. Nothing about licences ever blocks anything.
- TX on a receive-only service (NOAA, aviation) is *not* an error. The radio can store it.
  The library adds such entries with TX off, and the inspector shows a grey note if TX is
  turned on.
- Ctrl+I hides a hint on one channel (stored with the profile), so deliberate data stops
  nagging.

### 3.3 Write safety in the UI
**Badge** in the radio panel, always visible: `▐ TESTED · WRITE OK ▌` (green),
`▐ UNTESTED · READ-ONLY ▌` (amber), `▐ UNVERIFIED LAYOUT ▌` (red; taught models). On a locked
model the key bar shows `F4 Write(locked)` dimmed. Pressing it explains rather than errors:
"Writing to UV-5RM hasn't been verified on real hardware yet. You can read, edit, preview,
and save an image or CSV."

**Review** (after the preview, before writing): what changes *on this radio*:
```
╭─ Write to UV-5RE on cu.usbserial-140 ──────────────────────────────────────────────────────╮
│  Radio re-identified: UV-5RE ✓ (AA 30 76 04 …)     Backup: 2026-11-08_1531_UV-5RE.img ✓    │
│  On this radio: 31 channels unchanged · 12 new · 3 changed · 4 erased (overwrite mode)     │
│                                                                                            │
│   Slot  Change     On radio now                     After write                            │
│     14  new        ·                                GMRS15R 462.5500 +5.0 141.3/141.3 H    │
│     20  RX tone    ·                                67.0                                   │
│     31  name       MURS1                            MURS 1                                 │
│     40  erased     W1XYZ R 146.9400 −0.6 100.0 H    ·                                      │
│      …  (12 more, ↓ to scroll)                                                             │
│                                                                                            │
│  3 channels were changed on the radio since your last read (keypad edits) and are in       │
│  this list.                                                                                │
│                                                                                            │
│           Enter  Write 46 channels         Esc  Back to preview                            │
╰────────────────────────────────────────────────────────────────────────────────────────────╯
```
- Per-field diff for changed slots; whole rows for new and erased ones.
- If more than 10 channels would be erased, focus starts on "Back" (a cheap guard against a
  mass wipe); otherwise it starts on "Write".
- Diagnostics and licence info are *not* repeated here. This screen answers one question:
  "what happens to this radio's memory".

### 3.4 Progress
Serial work runs on a worker (core:jobs/threads). The UI polls a channel each frame and
calls `request_frame` while busy.
```
╭─ Reading UV-5RM ─────────────────────────────────────────╮
│  ███████████████████████████░░░░░░░░░░░░░░░░░░  58%      │
│  block 0x4C00 of 0x8380 · 8.1 KB/s · about 4 s left      │
│  channels found so far: 22                               │
│                                                          │
│                    Esc  Cancel (safe)                    │
╰──────────────────────────────────────────────────────────╯
```
- A write shows three phases on one bar: `Backup ▸ Write ▸ Verify`, with the current phase
  bold.
- Esc during a write asks "Stopping now leaves the radio half-written. Finish (Enter) / Stop
  anyway (S)?" rather than refusing silently.
- No reply for >2 s: the line becomes "Waiting for radio… check the cable is pushed fully
  in", before the hard timeout turns it into an error.

### 3.5 Error states
Each error shows what happened (one line), likely causes (an ordered checklist) and the
next key. Raw details (bytes, errno) are behind a "Details" toggle and in the log.

| situation | message and actions |
|---|---|
| no serial ports | "No programming cable found." Cable plugged in? Driver (macOS CH340; Linux built in)? F5 retry. |
| permission (Linux) | "Can't open /dev/ttyUSB0: permission denied." Shows `sudo usermod -aG dialout $USER` with Copy, and "then log out and back in". |
| port busy | "Another program is using the port (CHIRP?)." |
| no reply | "The radio didn't answer." Radio on? **Plug pushed fully in (it clicks twice)?** Volume up? Not in FM-broadcast mode? F5 retry · "Try all models slowly". |
| reply, unknown | → Teach flow (§1.10). |
| wrong model for write | "The radio on the cable is a UV-5RM, but this preview is for a UV-5RE." Actions: preview for UV-5RM (one key), or cancel. Writing never proceeds. |
| cable pulled mid-read | "Read stopped at 58%." Nothing saved except the log. Retry. |
| cable pulled mid-write | Full recovery panel (amber): "The radio may have a mix of old and new channels. Your backup is safe: <file>. 1) Reconnect and switch the radio off and on. 2) F4 write again (recommended), or R to restore the backup." The panel stays until one of those succeeds or you dismiss it explicitly. |
| verify mismatch | "Written, but 2 blocks read back differently." Shows the channels; write again / restore backup. |

### 3.6 Ambiguous auto-detect
Reading works the same for every candidate in a family, so the ambiguity only matters for
band limits, power levels and writing. The dialog shows evidence, not just names:
```
╭─ Which radio is this? ──────────────────────────────────────────────────────╮
│  It answered like the UV-5R family (ident AA 30 76 04 00 05 20 DD).         │
│                                                                             │
│  ▸ Baofeng UV-5R / UV-5RE   ident + firmware HN5RV011 match     best match  │
│    Baofeng BF-F8HP          ident matches; 3 power levels                   │
│    Baofeng UV-82            ident matches; firmware usually BFB…            │
│                                                                             │
│  Reading works the same for all of them. The choice sets band limits, power │
│  levels and writing. You can change it later in the radio panel.            │
│  [x] Remember for this radio                                                │
│                                                                             │
│            Enter  Use UV-5R / UV-5RE          Esc  Cancel                   │
╰─────────────────────────────────────────────────────────────────────────────╯
```
The list is a flat, filterable tree_view with the best match pre-selected.

---

## 4. Recommendation, first milestone, open questions

### Recommendation: **Concept B ("Workbench"), built in Concept A's order**
Profiles, the channel library, backups and several radios are Anaxarchus's real working set,
and B keeps them on screen. That also covers for the missing file dialog. Build it so the
first releases *are* Concept A: one tab, sidebar hidden (a split box with the left pane
collapsed). The sidebar and tabs come later without redesigning the grid. From Concept C,
take the **mandatory preview → review → verify path** and the friendly checklists for
errors.

Grid defaults: Dup+Offset with F6 for raw RX/TX; tones as a TX/RX pair (tone option 1);
profile names Name + Short (Q5).

### Milestone 1: "Read, keep, make it a profile" (no writing)
1. Window: radio panel, the grid widget in read-only form (virtualised, cell cursor, column
   sets, F6), status line, clickable key bar.
2. Detect (F5): port picker, ambiguous-candidates dialog, no-reply/permission errors.
3. Read (F3) on a worker with progress; automatic backup to the Library.
4. **Save as profile** from a read or a backup → `Library/profiles/*.csv`; open a profile
   or backup from a simple Library list dialog, or by drag-and-drop.
5. Export CSV.
6. Tested against `tools/emu.py` (the pty emulator), plus headless app:ui tests
   (`ui.update` + `ui.dispatch`) for grid keys.

Why this first: it already solves "never lose a radio's programming" and "keep my channels
independent of the radio", carries no write risk, and builds the biggest custom widget in
its simpler read-only form.

**M2: edit profiles**: inline editing, parsing, undo, copy/paste, Ctrl+L channel library,
Fits column. **M3: apply preview**: diagnostics from the engine, placement options,
filters, inline fixes, save image/CSV for any model. **M4: write**: re-identify, backup,
review, verify, recovery; UV-5RE first once its upload is ported and hardware-tested.
**M5: Workbench and batch**: sidebar, tabs, targets/stale markers, several radios per
session. **M6: teach a model**, compare any two.

### Open questions for Anaxarchus (only those that change the design)
- **Q1 Tones**: a TX tone/RX tone pair (recommended), CHIRP-style Mode/Tone/DTCS columns,
  or one "Squelch" column with a picker?
- **Q2 Who unlocks writing?** Only the developer setting `tested = write` (recommended), or
  an in-app "write anyway" for untested models, for when you want to test new models
  yourself from the GUI?
- **Q3 Workbench or single tab?** Do you often have two radios or profiles open at once? If
  rarely, Concept A is enough, and the tab/sidebar work can be saved.
- **Q4 Auto-detect on plug-in**, or wait for F5? (Auto is smoother; manual never sends bytes
  you didn't ask for.)
- **Q5 Fitting names**: one optional **Short name** per channel (recommended: simple, and
  covers 7- vs 12-char radios), **per-model overrides** (exact, but more UI), or **automatic
  abbreviation only** (no extra column, less control)?
- **Q6 Library location**: `~/Documents/beautalks` (visible; easy to back up and sync) or the
  hidden app-data folder?
- **Q7 Profile power**: abstract Hi/Mid/Lo mapped per radio (recommended), or watts?
- **Q8 Batch approval**: is "approve the preview once per model per session" right, or should
  every radio show its preview?

---

## 5. Feasibility against app:ui

### What exists and covers us
| need | app:ui piece | notes |
|---|---|---|
| window layout | `vbox`, `hbox`, `grid_box`, `margin_box`, `center_box`, `stack`+`set_anchor` | integer-cell layout |
| bordered panes | `panel` (themed `StyleBox`, focus-lit border) | radio panel, inspector |
| collapsible sidebar | `hsplit_box`/`vsplit_box`; hiding a child collapses it | Concept B (F9) |
| tabs | `tab_bar` (modified mark, close requests, overflow scroll) | profiles/images/previews |
| Library & channel-library sets | `tree_view` over a source: virtualised, chevrons, folder/file icons, keys, activate | sidebar, set tree |
| pickers / palette | `tree_view` flat + `tree_set_detail` + `tree_set_focus_proxy` + `line_edit_set_key_target` | the filtered-list pattern the IDE palette uses; tones, models, ports, commands |
| modal dialogs | `dialog`, modal stack, focus restore, `outside_pressed` | progress, review, errors, detect, library |
| text input | `line_edit` (undo, clipboard, placeholder, submitted/cancelled) | filters, path entry, inline fix field |
| read-only text | `text_view`; read-only `text_edit` with styles | logs, probe reports, help |
| status line | `label_set_status` | |
| custom widgets | `register_kind` + hooks, `create_owned` | grid, key bar, meter, tick list |
| pixel drawing | ink API, `draw_icon`, `pixel_box` | progress bar, badges |
| mouse | click, double-click timing, wheel/trackpad, capture/drag, cursors | |
| keyboard | key codes + `Text` events; modifiers include **Super (Cmd)** | Cmd on macOS, Ctrl on Linux |
| files without dialogs | `app:input` `Drop` event + `dropped_path` (copy it; ring of 16) | import |
| clipboard | text edit / `app:graphical` clipboard | rows as CSV; verify access from a custom widget |
| background work | `core:jobs` / `core:threads`, results through a channel; `ui.request_frame()` | serial off the UI thread |
| headless tests | `ui.update(rect)` + `ui.dispatch(event)` | grid behaviour without a window |
| theme | `theme_default`/`theme_set`; only a dark theme today | badge colours painted by our widgets |

### Gaps and rough effort
| gap | approach | effort |
|---|---|---|
| **Editable grid** (no Table widget yet; OUTLINE plans one) | custom kind: virtualised rows from a source (as tree_view does), pluggable column sets (profile / image / preview), cell cursor, row selection, per-cell colours and badges, header, whole-row scrolling. Inline edit: the grid owns a small edit buffer for the active cell (simplest), or a `line_edit` anchored over the cell in a `stack` (clipboard/undo for free, more plumbing). | **Large**: ~1200–1800 lines; M1's read-only part is about half |
| Buttons | **key bar** kind (clickable `F7 Apply…` spans, dimmed/locked state) + `Enter/Esc` hint rows | Small (~150) |
| Tick boxes / radio choices | grid ✓ cells; `[x]`/`(•)` spans in a small custom kind for dialogs (library, placement) | Small (~120) |
| Progress bar | custom kind with ink rects or `█░` cells | Small (~80) |
| Drop-down | picker dialog instead (pattern exists) | Small–medium (~200) |
| File dialogs | none: Library + drag-and-drop + typed path with Tab completion; "Show folder" via `open`/`xdg-open` | Medium (~250) |
| Toasts | `popup` in a `stack` anchored bottom-right, hidden by a timer | Small |
| Context menu | command palette pre-filtered | Small (reuses the picker) |
| Review diff | reuse the grid with a "before/after" column set | Medium |
| Light theme | author a second `Theme` | Small–medium, later |
| Port hot-plug | poll the port list from a timer | Small |
| Glyphs (`●✓✖▐▌−·`, box drawing) | check the default font's coverage; ASCII fallback (`*`, `x`, `!`, `[ ]`, `-`) | Check early |

Engine dependency: the preview needs the fit engine to return **structured** diagnostics
(channel, slot or `none`, severity, field, old value, new value, reason code + message), so
the UI can highlight the changed cell and offer a matching fix. Please make sure the engine
API has this shape rather than only message strings.

Spikes worth doing before M1:
1. **Serial on a worker thread** plus `request_frame` while idle frames are skipped: the UI
   stays live during a 10 s read, and the worker can own the fd.
2. **Font glyph coverage** for the symbols above.
3. **Clipboard** access from a custom widget.
4. **Window size**: 120×36 needs ~1440×900 at the default cell size. The smallest layout to
   support is ~100×30 (the inspector folds into a 2-line strip as in the Concept B mockup).

---

## Decisions (owner, 2026-11-08)

| Question | Decision |
|---|---|
| Main window | **Concept B (Workbench), built A-first**: early releases single-tab, sidebar/tabs added later without regridding. Safety path from C. |
| Tones in the grid | **TX tone / RX tone pair** of columns. |
| Untested models | **Write anyway, with warning**: an explicit in-app confirmation naming the risk; backup-before-write and read-back verify remain mandatory and cannot be skipped. Models marked `tested = write` skip the extra confirmation. |
| Plug-in | **Auto-detect when a cable appears.** Guard: only probe new USB-serial ports whose USB IDs are known programming-cable chips (CH340/CH341 1A86:7523/5523, PL2303 067B:2303, FTDI 0403:6001/6015, CP210x 10C4:EA60); other new ports show "Detect?" instead of being probed. Never probe a port mid-transfer. |

Defaults adopted for the remaining open questions (owner may override): Short-name column for
name fitting; Library at `~/Documents/beautalks`; profile power as abstract High/Medium/Low;
batch preview approved once per model per session.

### Added requirement (owner, 2026-11-08): remembered radios

The app keeps a registry of every radio it has talked to (model, identifying replies, firmware,
nickname, cable/port, last seen, last backup). Detection tries remembered radios first —
most recent on the same cable first — and only falls back to a full scan when none answer.
UI: a "Radios" group in the Library sidebar (nickname · model · last seen · last backup), rename
inline, "Forget"; the radio panel shows the nickname when a remembered radio is detected
("● Truck radio — Baofeng UV-5RM · seen 3 times").

---

## Decision (owner, 2026-11-08): native sokol app with Material-style polish — supersedes the cell-grid layouts

The terminal-style app:ui front end was rejected (audience: non-technical users) and dropped.
A web engine was also ruled out. The app is a **native sokol application** drawn with Dado's
app:draw/app:font (Metal on macOS), with a beautalks widget toolkit that gives it the feel of
a polished Material Design web app: rounded surfaces, soft elevation shadows, Inter type,
Material Symbols icons, motion, light and dark themes. The flows, safety rules, diagnostics
design and decisions above still apply; the ASCII layouts and key bar are obsolete.

### Added requirement (owner, 2026-11-08): built-in guided verification of untested hardware

A model that isn't tested for writing gets a guided **"Verify this radio"** procedure instead of
a bare warning:
1. Explain + consent (model, firmware/identifying reply, "we write back an identical copy",
   backup kept).
2. Read + automatic backup; show the channels so the user recognises their radio.
3. Safe write of the **identical image** (backup → write → read back), byte-for-byte compare.
4. Physical check: "Power-cycle the radio. Does it start normally and show the same channels?"
5. Yes → marked tested. Failure or No → guided restore from the backup + a saved report.

"Tested" is recorded **locally only** (owner decision), in the data dir, keyed by model id **plus
the radio's identifying fingerprint** (UV-5R ident/firmware tag, UV-17Pro F/M replies), so one
verified firmware doesn't vouch for another. The UI shows e.g. "Verified on this computer:
UV-5R · firmware HN5RV011". Shipped `tested = write` definitions still count as tested.
No results are sent anywhere.
