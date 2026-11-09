// beautalks - radio programming software
// Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
//
// TEST FIXTURE: a mod importing Dado bindings; must fail to load.
import { dh_write } from "dado:driverhost";
export class StaticImport { constructor(l, m) {} api() { return 1; } }
