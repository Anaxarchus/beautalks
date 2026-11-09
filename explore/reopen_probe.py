#!/usr/bin/env python3
"""Read-only: does closing/reopening the serial port break an open UV-5RM
programming session? Usage: reopen_probe.py PORT default|keeplines
  default   - normal close (macOS drops DTR/RTS on close: HUPCL)
  keeplines - clear HUPCL so DTR/RTS stay up across close/reopen
Sends only idents and read commands (R ...); never a write."""
import serial, sys, termios, time
PORT, MODE = sys.argv[1], sys.argv[2]
IDENT = b"PROGRAMBFNORMALU"
MAGICS = [(b"F", 16), (b"M", 15),
          (b"SEND\x21\x05\x0D\x01\x01\x01\x04\x11\x08\x05\x0D\x0D\x01\x11\x0F\x09\x12\x09\x10\x04\x00", 1)]
def hx(b): return " ".join(f"{x:02X}" for x in b[:24]) + (" ..." if len(b) > 24 else "") if b else "-"
def listen(s, secs):
    end, got = time.time() + secs, b""
    while time.time() < end: got += s.read(64)
    return got
def opened():
    s = serial.Serial(PORT, 115200, timeout=0.1)
    if MODE == "keeplines":
        a = termios.tcgetattr(s.fd); a[2] &= ~termios.HUPCL
        termios.tcsetattr(s.fd, termios.TCSANOW, a)
    s.dtr = s.rts = True; time.sleep(0.2); s.reset_input_buffer()
    return s
def probe(s, label):
    s.reset_input_buffer(); s.write(b"R\x00\x00\x40"); r = listen(s, 0.6)
    state = "SESSION OPEN" if r[:4] == b"R\x00\x00\x40" and len(r) >= 0x44 else "no session reply"
    print(f"{label}: read probe -> {state}  [{len(r)} bytes: {hx(r)}]")
    return state == "SESSION OPEN"
s = opened()
s.write(IDENT); a = listen(s, 1.0)
if a[:1] != b"\x06": sys.exit(f"ident failed ({hx(a)}): power-cycle the radio first")
for m, n in MAGICS: s.write(m); s.read(n)
probe(s, "before close")
s.close(); time.sleep(0.5)
s = opened()
ok = probe(s, "after reopen")
if not ok:
    time.sleep(2); ok = probe(s, "after reopen +2s")
if not ok:
    s.reset_input_buffer(); s.write(IDENT); a = listen(s, 1.0)
    print(f"ident after reopen -> {hx(a)}")
s.close()
print("done - power-cycle the radio")
