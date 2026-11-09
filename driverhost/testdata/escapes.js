// beautalks - radio programming software
// Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
//
// TEST FIXTURE: other ways out of the sandbox. identify() answers "SAFE", or
// "OPEN:" and every door that opened.
export class Escapes {
    constructor(link, model) { this.link = link; }
    api() { return 1; }
    identify() {
        const open = [];
        for (const n of ["setTimeout", "setInterval", "setImmediate", "Worker", "ShadowRealm", "WebAssembly",
                         "std", "os", "scriptArgs", "require", "process", "fetch", "XMLHttpRequest",
                         "Deno", "Bun", "eval", "Function", "importScripts", "load", "evalScript"]) {
            if (typeof globalThis[n] !== "undefined") open.push("global:" + n);
        }
        for (const k of Object.keys(import.meta)) open.push("import.meta." + k);
        for (const s of Object.getOwnPropertySymbols(globalThis)) if (s !== Symbol.toStringTag) open.push("symbol:" + String(s));
        if (typeof Symbol.for("dados") !== "symbol") open.push("Symbol.for");
        try { globalThis.__dados_failure = () => 0; if (globalThis.__dados_failure.length === 0) open.push("swap __dados_failure"); } catch (e) { }
        try { Object.defineProperty(Error, "prepareStackTrace", { value: (e, cs) => cs }); open.push("redefine prepareStackTrace"); } catch (e) { }
        // Error.prepareStackTrace: callsites of the host's frames (Loader, Link)
        try {
            Error.prepareStackTrace = (e, cs) => cs;
            const cs = new Error("x").stack;
            Error.prepareStackTrace = undefined;
            if (Array.isArray(cs)) {
                const fns = cs.filter((c) => typeof c.getFunction() === "function");
                if (fns.length) open.push("callsite-functions:" + fns.map((c) => c.getFunctionName()).join("|"));
            }
        } catch (e) { }
        try {
            const o = {};
            Error.captureStackTrace(o);
            if (typeof o.stack !== "string" && o.stack !== undefined) open.push("captureStackTrace");
        } catch (e) { }
        // undo the lockdown
        const tries = [
            ["define eval", () => Object.defineProperty(globalThis, "eval", { value: () => 1 })],
            ["assign eval", () => { globalThis.eval = () => 1; if (typeof globalThis.eval === "function") throw 0; }],
            ["delete Function", () => { if (delete globalThis.Function && typeof globalThis.Function !== "undefined") throw 0; }],
            ["define Function.prototype.constructor", () => Object.defineProperty(Object.getPrototypeOf(() => 0), "constructor", { value: Object })],
            ["Reflect.defineProperty", () => { if (Reflect.defineProperty(Object.getPrototypeOf(() => 0), "constructor", { value: Object })) throw 0; else throw 1; }],
            ["setPrototypeOf trick", () => { const f = () => 0; Object.setPrototypeOf(f, {}); if (typeof f.constructor === "function" && f.constructor !== Object) throw 0; else throw 1; }],
        ];
        for (const [name, f] of tries) {
            try { f(); open.push("undo:" + name); } catch (e) { if (e === 0) open.push("undo:" + name); }
        }
        const after = [() => (0, globalThis.eval)("1"), () => (() => 0).constructor("return 1"),
                       () => (async () => 0).constructor("return 1")];
        for (const f of after) { try { f(); open.push("code-from-string-after-undo"); } catch (e) { } }
        return open.length ? "OPEN:" + open.join(",") : "SAFE";
    }
    download() { return []; }
    upload(image) { }
}
