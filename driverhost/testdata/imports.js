// beautalks - radio programming software
// Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
//
// TEST FIXTURE: dynamic import() written in the mod's own source, plus
// top-level probes run while the module is evaluated (inside Script.load).
// identify() #1 starts the imports and answers "started"; identify() #2
// answers one line per import: name=resolved|rejected|pending.
// Controls: import("dados:runtime") (the one module a mod may import) must
// resolve and a plain promise job must run, which proves the engine's job
// queue ran between the two calls; otherwise "pending" fails the test.
const atLoad = "eval:" + typeof globalThis.eval + " Function:" + typeof globalThis.Function +
    " ctor:" + typeof (function () {}).constructor;
let topCallsites = "none";
try {
    Error.prepareStackTrace = (e, cs) => cs;
    const cs = new Error("probe").stack;
    if (Array.isArray(cs)) {
        const fns = cs.filter((c) => typeof c.getFunction() === "function");
        topCallsites = fns.length ? "FUNCTIONS:" + fns.map((c) => c.getFunctionName()).join("|") : "callsites-without-functions";
    } else {
        topCallsites = "string";
    }
} catch (e) { topCallsites = "threw"; }

export class Imports {
    constructor(link, model) { this.model = model; this.results = null; this.jobs = 0; }
    api() { return 1; }
    identify() {
        if (this.results === null) {
            const abs = this.model.get("test.abs");
            const names = ["dados:runtime", "dado:driverhost", "dado:main", "dados:host", "dados:mods",
                "./target.js", abs, "driverhost/Link", "driverhost/Loader", "js:harden.js", "mod:" + abs];
            this.results = {};
            for (const n of names) {
                this.results[n] = "pending";
                try {
                    import(n).then(() => { this.results[n] = "resolved"; },
                                   () => { this.results[n] = "rejected"; });
                } catch (e) { this.results[n] = "rejected"; }
            }
            Promise.resolve().then(() => { this.jobs += 1; });
            return "started";
        }
        const lines = ["jobs=" + this.jobs, "atLoad=" + atLoad, "topCallsites=" + topCallsites];
        for (const k of Object.keys(this.results)) lines.push(k + "=" + this.results[k]);
        return lines.join("\n");
    }
    download() { return []; }
    upload(image) { }
}
