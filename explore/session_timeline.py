#!/usr/bin/env python3
"""Read-only timeline for a UV-5RM after a programming session ends.
Session 1: ident + F/M/SEND + one block read. Then every ~1.5 s for up to
60 s: first a harmless read probe (R 00 00 40) to see if the session is
still open; if not, a fresh ident. Stops at the first accepted ident and
prints when each state was seen. Never sends a write command."""
import serial, sys, time
PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/cu.usbserial-140"
IDENT = b"PROGRAMBFNORMALU"
MAGICS = [(b"F", 16), (b"M", 15),
          (b"SEND\x21\x05\x0D\x01\x01\x01\x04\x11\x08\x05\x0D\x0D\x01\x11\x0F\x09\x12\x09\x10\x04\x00", 1)]
def hx(b): return " ".join(f"{x:02X}" for x in b[:24]) + (" ..." if len(b) > 24 else "") if b else "-"
def listen(s, secs):
    end, got = time.time() + secs, b""
    while time.time() < end: got += s.read(64)
    return got
s = serial.Serial(PORT, 115200, timeout=0.1); s.dtr = s.rts = True; time.sleep(0.2)
s.reset_input_buffer(); s.write(IDENT); a = listen(s, 1.0)
if a[:1] != b"\x06":
    sys.exit(f"session 1 ident failed ({hx(a)}): power-cycle the radio and run again")
for m, n in MAGICS: s.write(m); s.read(n)
s.write(b"R\x00\x00\x40"); s.read(0x44)
t0 = time.time()
print(f"session 1 open and idle from t=0")
while time.time() - t0 < 60:
    time.sleep(1.5)
    t = time.time() - t0
    s.reset_input_buffer(); s.write(b"R\x00\x00\x40"); r = listen(s, 0.4)
    if r[:4] == b"R\x00\x00\x40":
        print(f"t={t:5.1f}s  read probe -> session STILL OPEN ({len(r)} bytes)")
        continue
    s.reset_input_buffer(); s.write(IDENT); a = listen(s, 0.8)
    print(f"t={t:5.1f}s  read probe -> {hx(r)} | ident -> {hx(a)}")
    if a[:1] == b"\x06":
        print(f"==> new ident ACCEPTED at t={t:.1f}s")
        break
s.close()
print("done - power-cycle the radio")
