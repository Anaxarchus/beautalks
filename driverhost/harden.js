// beautalks - radio programming software
// Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
//
// Runs once per driver VM, from Loader.init, before Script.load evaluates any
// driver code (its top level included). Shuts two doors QuickJS leaves open:
//
// 1. Code from a string (eval, Function and the async/generator function
//    constructors). Such code is not named "mod:...", so the engine's import
//    resolver would let it import Dado bindings ("dado:<pkg>") and the
//    loader ("dados:host").
// 2. Error.prepareStackTrace (QuickJS-ng's V8-style hook): its CallSite
//    objects answer getFunction() for every frame, so a driver could pick
//    up the host's own functions on the stack -- dados:host's `load`,
//    `__dados_load`, Loader's constructor and init. The accessor is replaced
//    by one that is always undefined and ignores writes, and cannot be
//    redefined; stacks stay plain strings.
//
// Every property is made non-writable and non-configurable, so a driver
// cannot undo any of it. Covered by driverhost/sandbox_test.dado.
let done = false;

function seal(obj, name, value) {
    Object.defineProperty(obj, name, { value: value, writable: false, configurable: false, enumerable: false });
}

export function lockdown() {
    if (done) return 0;
    done = true;
    const ctors = [
        Function,
        Object.getPrototypeOf(async function () {}).constructor,
        Object.getPrototypeOf(function* () {}).constructor,
        Object.getPrototypeOf(async function* () {}).constructor,
    ];
    for (const C of ctors) seal(C.prototype, "constructor", undefined);
    seal(globalThis, "eval", undefined);
    seal(globalThis, "Function", undefined);
    Object.defineProperty(Error, "prepareStackTrace", {
        get() { return undefined; },
        set(v) { },
        configurable: false,
        enumerable: false,
    });
    // the host's failure hook: a driver must not swap how failures are told
    if (typeof globalThis.__dados_failure === "function") seal(globalThis, "__dados_failure", globalThis.__dados_failure);
    return ctors.length;
}
