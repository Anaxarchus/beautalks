#!/usr/bin/env python3
# beautalks - radio programming software
# Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
#
# A pty radio emulator: impersonates a UV-17Pro-family or UV-5R-family radio
# serving a memory image, so download/upload/detect run end to end without
# hardware. Protocol constants (idents, magics, scramble key, regions) come
# from a beautalks model definition (models/*.ini).
#
#   python3 tools/emu.py --model models/uv-5rm.ini --image testdata/uv5rm_backup.img \
#       --dump /tmp/after.img --port-file /tmp/emu.port
#
# Prints "PORT <path>" on stdout (and writes the path to --port-file), then
# serves until SIGTERM/SIGINT. Every accepted write updates the in-memory
# image; --dump writes it out after each write and on exit.
#
# Behaviour notes (match CHIRP's expectations and the owner's hardware):
#  * uv17pro: "PROGRAM...U" -> 06; 'F' -> 16 bytes; 'M' -> model reply;
#    'SEND...' (25 bytes) -> 06; 'R' a a 40 -> header + scrambled data;
#    'W' a a 40 + data -> 06. Unknown bytes before an ident are ignored
#    (e.g. 9600-baud UV-5R magics during detection).
#  * uv5r: magic -> 06; 02 -> 8-byte ident; 06 -> 06; 'S' a a n -> [06 unless
#    first after ident] + 'X' a a n + data; our 06 acks are swallowed;
#    'X' a a n + data -> 06. A wrong magic gets no answer.

import argparse
import configparser
import os
import select
import signal
import sys
import tty

ACK = b"\x06"


def parse_bytes(spec):
    spec = spec.strip()
    if spec.startswith("hex:"):
        return bytes.fromhex(spec[4:])
    return spec.encode()


def parse_magics(text):
    out = []
    for w in text.split():
        head, _, rest = w.partition("/")
        out.append((parse_bytes(head), int(rest, 0) if rest else 1))
    return out


def crypt(key, data):
    if not key:
        return bytes(data)
    out = bytearray(data)
    for i, b in enumerate(data):
        k = key[i % 4]
        if k != 0x20 and b not in (0, 0xFF) and b != k and b != (k ^ 0xFF):
            out[i] = b ^ k
    return bytes(out)


class Radio:
    def __init__(self, args, ini):
        self.args = args
        self.ini = ini
        self.family = ini.get("model", "engine")
        self.image = bytearray(open(args.image, "rb").read())
        self.buf = bytearray()
        self.state = "idle"
        self.writes = 0
        link = ini["link"]
        self.magics = parse_magics(link.get("magics", ""))
        if self.family == "uv17pro":
            self.idents = [parse_bytes(w) for w in link.get("ident", "").split()]
            key = link.get("key", "none").strip()
            self.key = b"" if key in ("", "none") else parse_bytes(key)
            self.regions = []
            off = 0
            for w in link.get("regions", "").split():
                a, l = w.split("+")
                self.regions.append((int(a, 0), int(l, 0), off))
                off += int(l, 0)
            self.f_reply = bytes.fromhex(args.f_reply)
            mr = args.m_reply if args.m_reply is not None else "5RH     +L00000"
            self.m_reply = mr.encode()
        else:
            self.ident = bytes.fromhex(args.ident) if args.ident else bytes(self.image[:8])
            self.aux = link.get("aux", "yes") != "no"
            self.first = True

    # ── address maps ──
    def uv17_off(self, addr, n):
        for a, l, off in self.regions:
            if a <= addr and addr + n <= a + l:
                return off + (addr - a)
        return None

    def uv5r_off(self, addr, n):
        if 0 <= addr and addr + n <= 0x1800:
            return 8 + addr
        if self.aux and 0x1EC0 <= addr and addr + n <= 0x2000:
            return 0x1808 + (addr - 0x1EC0)
        return None

    def dump(self):
        if self.args.dump:
            with open(self.args.dump + ".tmp", "wb") as f:
                f.write(self.image)
            os.replace(self.args.dump + ".tmp", self.args.dump)

    # ── byte stream ──
    def need(self, n):
        return len(self.buf) >= n

    def take(self, n):
        out = bytes(self.buf[:n])
        del self.buf[:n]
        return out

    def feed(self, data, send):
        self.buf += data
        progress = True
        while progress and self.buf:
            progress = getattr(self, "step_" + self.family)(send)

    def idle_match(self, candidates, send, on_match):
        for c in candidates:
            i = self.buf.find(c)
            if i >= 0:
                del self.buf[:i + len(c)]
                on_match(c)
                return True
        # keep only a tail long enough to still match
        keep = max(len(c) for c in candidates) if candidates else 0
        if len(self.buf) > keep:
            del self.buf[:len(self.buf) - keep]
        return False

    def step_uv17pro(self, send):
        if self.state == "idle":
            def matched(_):
                send(ACK)
                self.state = "program"
            return self.idle_match(self.idents, send, matched)
        b = self.buf[0]
        if b == 0x46:  # F
            self.take(1)
            send(self.f_reply)
            return True
        if b == 0x4D:  # M
            self.take(1)
            want = 15
            for m, n in self.magics:
                if m == b"M":
                    want = n
            send(self.m_reply[:want])
            return True
        if b == 0x53:  # SEND...
            if not self.need(25):
                return False
            self.take(25)
            send(ACK)
            return True
        if b == 0x52:  # R
            if not self.need(4):
                return False
            hdr = self.take(4)
            addr = (hdr[1] << 8) | hdr[2]
            n = hdr[3]
            off = self.uv17_off(addr, n)
            data = bytes(self.image[off:off + n]) if off is not None else b"\xff" * n
            send(hdr + crypt(self.key, data))
            return True
        if b == 0x57:  # W
            if not self.need(4):
                return False
            n = self.buf[3]
            if not self.need(4 + n):
                return False
            frame = self.take(4 + n)
            addr = (frame[1] << 8) | frame[2]
            off = self.uv17_off(addr, n)
            if off is None:
                send(b"\x15")
                return True
            self.image[off:off + n] = crypt(self.key, frame[4:])
            self.writes += 1
            self.dump()
            send(ACK)
            return True
        # anything else: back to idle (a new ident may follow)
        self.state = "idle"
        return True

    def step_uv5r(self, send):
        if self.state == "idle":
            def matched(_):
                send(ACK)
                self.state = "ident"
            return self.idle_match([m for m, _ in self.magics], send, matched)
        b = self.buf[0]
        if self.state == "ident":
            self.take(1)
            if b == 0x02:
                send(self.ident)
                self.state = "ack"
            else:
                self.state = "idle"
            return True
        if self.state == "ack":
            self.take(1)
            if b == 0x06:
                send(ACK)
                self.state = "clone"
                self.first = True
            else:
                self.state = "idle"
            return True
        # clone
        if b == 0x06:
            self.take(1)
            return True
        if b == 0x53:  # S
            if not self.need(4):
                return False
            hdr = self.take(4)
            addr = (hdr[1] << 8) | hdr[2]
            n = hdr[3]
            off = self.uv5r_off(addr, n)
            data = bytes(self.image[off:off + n]) if off is not None else b"\xff" * n
            out = b"" if self.first else ACK
            self.first = False
            send(out + b"X" + hdr[1:4] + data)
            return True
        if b == 0x58:  # X
            if not self.need(4):
                return False
            n = self.buf[3]
            if not self.need(4 + n):
                return False
            frame = self.take(4 + n)
            addr = (frame[1] << 8) | frame[2]
            off = self.uv5r_off(addr, n)
            if off is None:
                send(b"\x15")
                return True
            self.image[off:off + n] = frame[4:]
            self.writes += 1
            self.dump()
            send(ACK)
            return True
        self.state = "idle"
        return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True, help="models/*.ini to impersonate")
    ap.add_argument("--image", required=True, help="memory image to serve")
    ap.add_argument("--dump", help="write the (possibly updated) image here")
    ap.add_argument("--port-file", help="write the pty path here")
    ap.add_argument("--m-reply", help="uv17pro 'M' reply text (default: the owner's 5RM)")
    ap.add_argument("--f-reply", default="0136017404000520020002608084" "8A94",
                    help="uv17pro 'F' reply, hex")
    ap.add_argument("--ident", help="uv5r ident reply, hex (default: image[0:8])")
    ap.add_argument("--log", action="store_true", help="log traffic to stderr")
    args = ap.parse_args()

    ini = configparser.ConfigParser(interpolation=None, comment_prefixes=(";", "#"),
                                    inline_comment_prefixes=None)
    ini.read(args.model)
    radio = Radio(args, ini)

    master, slave = os.openpty()
    tty.setraw(slave)
    path = os.ttyname(slave)
    if args.port_file:
        with open(args.port_file + ".tmp", "w") as f:
            f.write(path)
        os.replace(args.port_file + ".tmp", args.port_file)
    print("PORT", path, flush=True)

    running = [True]

    def stop(*_):
        running[0] = False
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    def send(data):
        if args.log:
            sys.stderr.write("<- %s\n" % data.hex())
        os.write(master, data)

    while running[0]:
        try:
            r, _, _ = select.select([master], [], [], 0.2)
        except InterruptedError:
            continue
        if not r:
            continue
        try:
            data = os.read(master, 4096)
        except OSError:
            continue
        if args.log:
            sys.stderr.write("-> %s\n" % data.hex())
        radio.feed(data, send)
    radio.dump()
    os.close(slave)
    os.close(master)


if __name__ == "__main__":
    main()
