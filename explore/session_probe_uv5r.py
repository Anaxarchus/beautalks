#!/usr/bin/env python3
"""Read-only: does a UV-5R-family radio stay in a programming session after a
download? Session 1 = magic, ident, two block reads (CHIRP order). Then tries
a fresh magic immediately, after 0.5 s, after 3 s, and after reopening."""
import serial, struct, sys, time
PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/cu.usbserial-140"
MAGIC = b"\x50\xBB\xFF\x20\x12\x07\x25"
def hx(b): return " ".join(f"{x:02X}" for x in b) if b else "(nothing)"
def listen(s, secs):
    end, got = time.time() + secs, b""
    while time.time() < end: got += s.read(64)
    return got
def magic(s):
    s.reset_input_buffer()
    for c in MAGIC: s.write(bytes([c])); time.sleep(0.01)
def session(s, label):
    magic(s); r = listen(s, 1.0)
    print(f"{label}: magic -> {hx(r[:40])}{' ...' if len(r) > 40 else ''}  ({len(r)} bytes)")
    if r[:1] != b"\x06": return False
    s.write(b"\x02"); ident = listen(s, 0.5); print(f"   ident -> {hx(ident)}")
    s.write(b"\x06"); print(f"   ack -> {hx(s.read(1))}")
    for i, addr in enumerate((0x1E80, 0x1EC0)):
        s.write(struct.pack(">BHB", ord("S"), addr, 0x40))
        r = listen(s, 0.6); print(f"   S {addr:04X} -> {len(r)} bytes, starts {hx(r[:5])}")
        s.write(b"\x06"); time.sleep(0.05)
    return True
s = serial.Serial(PORT, 9600, timeout=0.2); s.dtr = s.rts = True; time.sleep(0.2)
print("== session 1 (power-cycle the radio before running this)"); session(s, "S1")
print("== immediately"); session(s, "S2a")
print("== after 0.5 s"); time.sleep(0.5); session(s, "S2b")
print("== after 3 s"); time.sleep(3.0); session(s, "S2c")
s.close()
s = serial.Serial(PORT, 9600, timeout=0.2); s.dtr = s.rts = True; time.sleep(0.2)
print("== reopened"); session(s, "S3"); s.close()
print("done - power-cycle the radio")
