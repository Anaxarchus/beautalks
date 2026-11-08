#!/usr/bin/env python3
"""Read-only probe for the Baofeng UV-5RM (CHIRP model "5RM", UV-17Pro protocol).

Protocol, from CHIRP's baofeng_uv17Pro.py:
  115200 baud 8N1
  1. send b"PROGRAMBFNORMALU"            -> radio replies 0x06
  2. send b"F"                           -> 16 bytes (radio info)
  3. send b"M"                           -> 15 bytes
  4. send b"SEND" + 21 bytes             -> 1 byte
  5. read: b"R" + addr(2 BE) + len(1)    -> 4-byte header + 0x40 data bytes
     data is XOR-obfuscated with key b"CO 7" (UV-5RM Plus uses b"C SL")
  regions: 0x0000+0x8040, 0x9000+0x40, 0xA000+0x2C0, 0xD000+0x40
"""
import argparse, struct, sys, time
import serial

IDENT = b"PROGRAMBFNORMALU"
MAGICS_5RM = [(b"F", 16), (b"M", 15),
              (b"SEND\x21\x05\x0D\x01\x01\x01\x04\x11\x08\x05\x0D\x0D\x01\x11\x0F\x09\x12\x09\x10\x04\x00", 1)]
MAGICS_5RM_PLUS = [(b"F", 16), (b"M", 15),
              (b"SEND\x13\x0F\x0D\x13\x0E\x0E\x0E\x0D\x0A\x0E\x0E\x02\x0F\x08\x04\x11\x0C\x00\x0D\x0E\x00", 1)]
KEYS = {"5RM": b"CO 7", "5RM Plus": b"C SL"}
REGIONS = [(0x0000, 0x8040), (0x9000, 0x0040), (0xA000, 0x02C0), (0xD000, 0x0040)]

def hexs(b): return " ".join(f"{x:02X}" for x in b) if b else "(nothing)"

def crypt(key, buf):
    out, k = bytearray(), 0
    for b in buf:
        s = key[k]
        if s != 32 and b not in (0, 255, s, s ^ 255):
            b ^= s
        out.append(b); k = (k + 1) % 4
    return bytes(out)

def xfer(s, data, n, label):
    s.write(data)
    r = s.read(n)
    print(f"  {label:10s} sent {len(data):2d}B -> got {len(r):2d}/{n}: {hexs(r)}  {r!r}")
    return r

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/cu.usbserial-140")
    ap.add_argument("--plus", action="store_true", help="use UV-5RM Plus magic/key")
    ap.add_argument("--dump", help="save decrypted memory image here")
    a = ap.parse_args()
    variant = "5RM Plus" if a.plus else "5RM"
    magics = MAGICS_5RM_PLUS if a.plus else MAGICS_5RM

    s = serial.Serial(a.port, 115200, bytesize=8, parity="N", stopbits=1, timeout=1.5)
    s.dtr = True; s.rts = True
    time.sleep(0.2); s.reset_input_buffer()

    print(f"Talking to {a.port} as UV-{variant}")
    ack = xfer(s, IDENT, 1, "ident")
    if ack != b"\x06":
        print("\nNo 0x06 ack. Radio isn't hearing us (or isn't answering). See notes in chat.")
        return 1
    for m, n in magics:
        xfer(s, m, n, m[:4].decode(errors="replace"))
    print("Handshake complete - radio should be in programming mode.")

    if not a.dump:
        r = xfer(s, b"R" + struct.pack(">H", 0) + b"\x40", 0x44, "R 0x0000")
        if len(r) == 0x44:
            d = crypt(KEYS[variant], r[4:])
            print("  first 64 bytes decrypted:", hexs(d))
        print("\nRe-run with --dump radio.img to save the whole memory. Power-cycle the radio after.")
        return 0

    img = bytearray()
    for start, size in REGIONS:
        for addr in range(start, start + size, 0x40):
            s.write(b"R" + struct.pack(">H", addr) + b"\x40")
            r = s.read(0x44)
            if len(r) != 0x44:
                print(f"\nshort read at 0x{addr:04X}: {hexs(r)}"); break
            img += crypt(KEYS[variant], r[4:])
            print(f"\r  read 0x{addr:04X}", end="", flush=True)
    print()
    open(a.dump, "wb").write(bytes(img))
    print(f"Saved {len(img)} bytes to {a.dump} (CHIRP expects 0x8380 = {0x8380}). Power-cycle the radio.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
