// beautalks - radio programming software
// Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
//
// TEST FIXTURE: a hand-written hostile driver. identify() answers "SAFE" when
// every door it tries is shut, else "ESCAPED:" and what opened.
export class Hostile {
    constructor(link, model) { this.link = link; }
    api() { return 1; }
    identify() {
        const open = [];
        const tryit = (name, f) => { try { const v = f(); if (v !== undefined && v !== null) open.push(name); } catch (e) { } };
        for (const n of ["std", "os", "require", "process", "fetch", "XMLHttpRequest", "eval", "Function"]) {
            if (typeof globalThis[n] !== "undefined") open.push("global " + n);
        }
        tryit("eval-call", () => (0, eval)("1"));
        tryit("arrow-ctor", () => (() => 0).constructor);
        tryit("async-ctor", () => (async () => 0).constructor);
        tryit("gen-ctor", () => (function* () {}).constructor);
        tryit("asyncgen-ctor", () => (async function* () {}).constructor);
        tryit("Reflect-ctor", () => Reflect.getPrototypeOf(() => 0).constructor);
        return open.length === 0 ? "SAFE" : "ESCAPED:" + open.join(",");
    }
    download() { return []; }
    upload(image) { }
}
