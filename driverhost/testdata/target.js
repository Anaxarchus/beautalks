// beautalks - radio programming software
// Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
//
// TEST FIXTURE: a module the hostile fixtures try to import. If any import of
// it resolves, the sandbox leaked.
export const pwned = 1;
export class Target { constructor(l, m) {} api() { return 1; } }
