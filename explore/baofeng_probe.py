#!/usr/bin/env python3
"""
Read-only exploration of a Baofeng UV-5R-family radio over its programming cable.
It NEVER writes channel memory to the radio; it only does the identify handshake
and (optionally) downloads the memory image to a file.

Protocol (as used by CHIRP's uv5r driver):
  9600 baud 8N1.
  1. Send a 7-byte "magic" one byte at a time (~10 ms apart). Radio replies 0x06 (ACK).
  2. Send 0x02. Radio replies with an ident: 8 (or 12) bytes, starts 0xAA, ends 0xDD.
  3. Send 0x06. Radio replies 0x06.  -> radio is now in programming mode (screen may blank).
  4. Read blocks: send 'S' + addr(2 bytes BE) + len(1). Radio replies 'X' + addr + len + data.
     Then we send 0x06 and the radio replies 0x06.
  Main memory: 0x0000-0x1800 (channels at 0x0000, 16 bytes each, names at 0x1000).
  Aux block:   0x1EC0-0x2000 (firmware version string, etc).

Usage:
  python3 -m pip install --user pyserial
  python3 explore/baofeng_probe.py                       # auto-pick port, identify only
  python3 explore/baofeng_probe.py --port /dev/cu.usbserial-XXXX
  python3 explore/baofeng_probe.py --dump radio.img      # also download memory image
"""
import argparse, glob, struct, sys, time

try:
    import serial
except ImportError:
    sys.exit("pyserial missing: python3 -m pip install --user pyserial")

MAGICS = {
    "UV-5R (BFB291+ / most common)": b"\x50\xBB\xFF\x20\x12\x07\x25",
    "UV-5R (original)":              b"\x50\xBB\xFF\x01\x25\x98\x4D",
    "UV-82":                         b"\x50\xBB\xFF\x20\x13\x01\x05",
    "UV-6":                          b"\x50\xBB\xFF\x20\x12\x08\x23",
    "UV-5G / GT-5R":                 b"\x50\xBB\xFF\x20\x12\x06\x25",
    "UV-A58 / GT-3":                 b"\x50\xBB\xFF\x20\x14\x04\x13",
    "F-11":                          b"\x50\xBB\xFF\x13\xA1\x11\xDD",
}

def hexs(b): return " ".join(f"{x:02X}" for x in b) if b else "(nothing)"

def pick_port():
    ports = [p for p in sorted(glob.glob("/dev/cu.*"))
             if "bluetooth" not in p.lower() and "debug" not in p.lower()]
    if not ports:
        sys.exit("No /dev/cu.* serial port found. Is the cable driver installed? Run explore/find_cable.sh")
    print("Candidate ports:", ", ".join(ports))
    return ports[0]

def open_port(path):
    s = serial.Serial(path, 9600, bytesize=8, parity="N", stopbits=1, timeout=1)
    # Some cables power the radio-side circuitry from DTR/RTS.
    s.dtr = True; s.rts = True
    time.sleep(0.1)
    s.reset_input_buffer()
    return s

def try_ident(s, name, magic):
    print(f"\n-- trying magic for {name}: {hexs(magic)}")
    s.reset_input_buffer()
    for byte in magic:
        s.write(bytes([byte])); time.sleep(0.01)
    ack = s.read(1)
    print(f"   ack after magic: {hexs(ack)}")
    if ack != b"\x06":
        return None
    s.write(b"\x02")
    ident = b""
    for _ in range(12):
        c = s.read(1)
        if not c: break
        ident += c
        if c == b"\xDD": break
    print(f"   ident ({len(ident)} bytes): {hexs(ident)}  ascii={ident!r}")
    s.write(b"\x06")
    ack2 = s.read(1)
    print(f"   ack after ident: {hexs(ack2)}")
    if ack2 != b"\x06":
        print("   (no final ack - handshake incomplete)")
        return None
    return ident

def read_block(s, addr, size=0x40, first=False):
    # CHIRP uv5r.py: radio ACKs (0x06) every request except the first, BEFORE the
    # 'X' header; we ACK each block after reading it.
    cmd = struct.pack(">BHB", ord("S"), addr, size)
    s.write(cmd)
    if not first:
        ack = s.read(1)
        if ack != b"\x06":
            raise IOError(f"no ack before block 0x{addr:04X}: {hexs(ack)}")
    hdr = s.read(4)
    if len(hdr) != 4 or hdr[0] != ord("X") or hdr[1:] != cmd[1:]:
        raise IOError(f"bad header at 0x{addr:04X}: {hexs(hdr)}")
    data = s.read(size)
    if len(data) != size:
        raise IOError(f"short read at 0x{addr:04X}: got {len(data)} bytes")
    s.write(b"\x06")
    time.sleep(0.05)
    return data

def bcd_freq(b4):
    # Little-endian BCD, units of 10 Hz -> MHz string
    digits = "".join(f"{x:02X}" for x in reversed(b4))
    if not digits.isdigit(): return None
    return f"{int(digits)/100000:.5f}"

def summarize(img):
    print("\n== Channels found (index: RX MHz / TX MHz / name) ==")
    for i in range(128):
        rec = img[i*16:(i+1)*16]
        if rec[:4] == b"\xFF"*4: continue
        rx, tx = bcd_freq(rec[0:4]), bcd_freq(rec[4:8])
        name_raw = img[0x1000 + i*16:0x1000 + i*16 + 7] if len(img) > 0x1000 + i*16 + 7 else b""
        name = name_raw.split(b"\xFF")[0].decode("ascii", "replace").strip()
        print(f"  {i:3d}: {rx} / {tx}  {name}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port")
    ap.add_argument("--dump", help="file to save the downloaded memory image")
    a = ap.parse_args()

    port = a.port or pick_port()
    print(f"Using {port}. Radio should be ON, cable pushed in fully (it clicks twice), volume up.")
    s = open_port(port)
    ident = None
    for name, magic in MAGICS.items():
        ident = try_ident(s, name, magic)
        if ident is not None:
            print(f"\n*** Radio answered as: {name} ***")
            break
        time.sleep(1.5)  # radio needs a pause before it will accept another attempt
    if ident is None:
        print("\nNo handshake. Check: radio on, cable fully seated, correct port, driver OK.")
        print("Tip: power-cycle the radio between runs.")
        return 1
    if not a.dump:
        print("\nIdentify OK. Re-run with --dump radio.img to download memory (read-only).")
        return 0
    # Same order as CHIRP: firmware/aux probe first (new radios return bad aux
    # data otherwise), then main memory, then aux memory.
    try:
        read_block(s, 0x1E80, 0x40, first=True)
        b1 = read_block(s, 0x1EC0)
        b2 = read_block(s, 0x1FC0)
        version = b1[48:62]
        dropped = b2[15:16] == b"\xFF"
        print(f"Firmware: {version!r}  dropped-byte quirk: {dropped}")
        main = bytearray()
        for addr in range(0x0000, 0x1800, 0x40):
            main += read_block(s, addr)
            print(f"\r   read 0x{addr:04X}", end="", flush=True)
        aux = bytearray()
        for addr in range(0x1EC0, 0x1FC0, 0x40):
            aux += read_block(s, addr)
        step = 0x10 if dropped else 0x40
        for addr in range(0x1FC0, 0x2000, step):
            aux += read_block(s, addr, step)
        print()
    except IOError as e:
        print(f"\nRead failed: {e}")
        return 1
    img = bytes(ident[:8]) + bytes(main) + bytes(aux)   # CHIRP's image layout
    with open(a.dump, "wb") as f:
        f.write(img)
    print(f"Saved {len(img)} bytes to {a.dump} (8-byte ident + 0x1800 main + 0x140 aux)")
    summarize(main)
    print("\nPower-cycle the radio to leave programming mode.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
