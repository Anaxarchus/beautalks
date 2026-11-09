<!-- beautalks - radio programming software
     Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later. -->
# Dado notes (rc.9) — things that cost time

- Methods are written inside the `type` body (`void destroy(^self):`), never as
  `void T.destroy(...)` at top level.
- XOR is `~` (binary), not `^` (`^` is the pointer sigil).
- `#len(f())` is refused: bind the call's value to a name first.
- A declaring `try T x = f() else:` must leave the scope; to fall back, declare
  `x` first and write `try x = f() else: x = ...`.
- A one-slot type *is* its slot: `type SerialLink using Link: serial.Port port`
  is built with `SerialLink(p)`, not `SerialLink(port: p)`.
- A trait value is made by assignment only (`eng.link = link`), never
  `T(link)`. A trait as a parameter's whole type (`^Link link`) is a binder,
  instantiated per implementer; errors in it appear only when a caller
  instantiates it, so `dado check radio` can pass while `dado build cli` fails.
- Slices of a frame array: `arr[:]`; `string8(bytes[a..<b])` views bytes as text.
- A `"""` string starts on the next line and its closing `"""` (alone on its
  line) sets the margin.
- `switch` over an enum names every member (NONE included) plus `else`.
- `@test` must be the file's first line; test output on stdout is not shown, so
  put diagnostics into `#expect` messages. Tests run from the directory where
  `dado test` is called (the project root), so `testdata/...` and `models` are
  relative to it.
- A `[]u8` parameter does not take `^const []u8`; take `[]u8` (a view).
- `dado build cli -o build/beautalks` names the program; without `-o` it is `build/cli`.
- `==` between a `string8` and a `ref []char8` is refused, and `string8(ref)`
  too: bind it (`string8 v = owned`) and compare `v`.
- Aliasing two `ref` runs through a conditional (`ref []T l = a if p else b`)
  makes the checker think one may point into the other (WRN0803); use a view
  `[]T l = ...` instead.
- A trait whose methods are `E!T` with `E` declared in the trait's package
  (`LinkError!ref []u8 download(...)`) cannot be implemented from another
  package: the name `E` is resolved in the implementer's package (ERR0401 /
  ERR0536). Workaround: plain `!T` methods in the trait carrying the same
  numbers, translated with `try ... else code: fail LinkError(code)`.
- driverhost.download/upload keep the Wire in package storage while they
  run, so the checker refuses (ERR0826) a Wire or engine on the caller's
  frame. The CLI puts the ScriptEngine and a copy of the SerialLink on the
  heap (`#new`); the remaining WRN0803 about `defer #delete(se)` is the
  checker not seeing driverhost unbind before returning.
- A `foreign` block's header and `define`s matter even when the functions
  live in `@c_body`: switching serial's block from `termios.h` to `stdlib.h`
  (to build on Windows) made the POSIX build misbehave intermittently (pty
  reads lost in tests). Fix: one block per OS, `when #OS == #WINDOWS:`
  (`windows.h`) `else:` (`termios.h` + `_DEFAULT_SOURCE`/`_DARWIN_C_SOURCE`).
- `@const string8 X = "..."` is replaced by `-D pkg.X=text` with the text
  taken as is: `-D updater.APP_VERSION=0.2.0` gives "0.2.0"; quoting it
  (`"0.2.0"`) puts the quotes into the string.
- Tests that spawn tools/emu.py are killed by any `pkill -f emu.py` run at the
  same time (and that pkill also kills the shell whose command line holds
  "emu.py"). Don't run manual emulator sessions while `dado test` runs.
