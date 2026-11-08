#!/usr/bin/env python3
"""Wider read-only probe: tries several baud rates, DTR/RTS settings and the
newer Baofeng 'PROGRAM...' handshakes (UV-5RM, UV-17Pro, UV-5R Mini, etc.).
Prints every byte that comes back. Power-cycle the radio before running."""
import sys, time, argparse
import serial

UV5R = [b"\x50\xBB\xFF\x20\x12\x07\x25", b"\x50\xBB\xFF\x01\x25\x98\x4D"]
ASCII_IDENTS = [b"PROGRAMBT80U", b"PROGRAMCOLORPROU", b"PROGRAMBFNORMALU",
                b"PROGRAMBF5RU", b"PROGRAM"]

def hexs(b): return " ".join(f"{x:02X}" for x in b) if b else "(nothing)"

def listen(s, secs):
    end, got = time.time() + secs, b""
    while time.time() < end:
        got += s.read(64)
    return got

def attempt(port, baud, dtr, payload, bytewise):
    with serial.Serial(port, baud, timeout=0.3) as s:
        s.dtr, s.rts = dtr, dtr
        time.sleep(0.2); s.reset_input_buffer()
        if bytewise:
            for c in payload: s.write(bytes([c])); time.sleep(0.01)
        else:
            s.write(payload)
        return listen(s, 1.0)

ap = argparse.ArgumentParser(); ap.add_argument("--port", default="/dev/cu.usbserial-140")
port = ap.parse_args().port

with serial.Serial(port, 9600, timeout=0.3) as s:
    print("Passive listen 2s at 9600 (press PTT or turn a knob now):", hexs(listen(s, 2)))

hits = []
for baud in (9600, 19200, 38400, 57600, 115200):
    for dtr in (True, False):
        tests = [(m, True) for m in UV5R] + [(m, False) for m in ASCII_IDENTS]
        for payload, bytewise in tests:
            r = attempt(port, baud, dtr, payload, bytewise)
            tag = f"baud={baud:6d} dtr/rts={'on ' if dtr else 'off'} send={payload[:16]!r}"
            print(f"{tag:70s} -> {hexs(r)}")
            if r: hits.append((tag, r))
            time.sleep(0.3)
print("\nResponses:" if hits else "\nNo bytes came back on any setting.")
for t, r in hits: print(" ", t, "->", hexs(r), r)
