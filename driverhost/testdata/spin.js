// beautalks - radio programming software
// Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
//
// TEST FIXTURE: drivers that never return. identify() spins without touching
// the link; download() spins inside a catch-all so a polite stop is swallowed
// (the watchdog must force it); upload() talks to the link forever, which
// keeps the idle watchdog fed until the whole-call cap trips.
export class Spin {
    constructor(link, model) { this.link = link; }
    api() { return 1; }
    identify() { for (;;) {} }
    download() { for (;;) { try { for (;;) {} } catch (e) { } } }
    upload(image) { for (;;) { this.link.sleep(5); } }
}
