#!/usr/bin/env python3
"""Read-only: what does a UV-5RM answer when a second programming session
starts without a power-cycle? Opens session 1 (ident + magics + one block
read), then tries the ident again several ways and prints raw replies."""
import serial, struct, sys, time
PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/cu.usbserial-140"
IDENT = b"PROGRAMBFNORMALU"
MAGICS = [(b"F", 16), (b"M", 15),
          (b"SEND\x21\x05\x0D\x01\x01\x01\x04\x11\x08\x05\x0D\x0D\x01\x11\x0F\x09\x12\x09\x10\x04\x00", 1)]
def hx(b): return " ".join(f"{x:02X}" for x in b) if b else "(nothing)"
def listen(s, secs):
    end, got = time.time() + secs, b""
    while time.time() < end: got += s.read(64)
    return got
def session(s, label):
    s.reset_input_buffer(); s.write(IDENT); r = listen(s, 1.0)
    print(f"{label}: ident -> {hx(r)}  {r[:40]!r}")
    if r[:1] != b"\x06": return False
    for m, n in MAGICS:
        s.write(m); r = s.read(n); print(f"   {m[:4]!r} -> {hx(r)}")
    s.write(b"R\x00\x00\x40"); r = s.read(0x44); print(f"   R 0000 -> {len(r)} bytes")
    return True
s = serial.Serial(PORT, 115200, timeout=0.2); s.dtr = s.rts = True; time.sleep(0.2)
print("== session 1 (power-cycle the radio before running this)")
session(s, "S1")
print("== session 2 immediately, same port open")
session(s, "S2a")
print("== retry after 0.5 s")
time.sleep(0.5); session(s, "S2b")
print("== retry after 2 s")
time.sleep(2.0); session(s, "S2c")
s.close()
print("== reopen the port, try again")
s = serial.Serial(PORT, 115200, timeout=0.2); s.dtr = s.rts = True; time.sleep(0.2)
session(s, "S3")
s.close()
print("done - power-cycle the radio")
