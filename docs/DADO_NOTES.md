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
