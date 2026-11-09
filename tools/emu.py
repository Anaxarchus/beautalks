#!/usr/bin/env python3
# beautalks - radio programming software
# Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
#
# A pty radio emulator: impersonates a UV-17Pro-family or UV-5R-family radio
# serving a memory image, so download/upload/detect run end to end without
# hardware. Protocol constants (idents, magics, scramble key, regions) come
# from a beautalks model definition (models/*.ini).
#
#   python3 tools/emu.py --model models/uv-5rm.ini --image testdata/uv5rm.img \
#       --dump /tmp/after.img --port-file /tmp/emu.port
#
# Prints "PORT <path>" on stdout (and writes the path to --port-file), then
# serves until SIGTERM/SIGINT. Every accepted write updates the in-memory
# image; --dump writes it out after each write and on exit.
#
# Sessions, as probed on the owner's radios:
#  * uv17pro (UV-5RM): after the ident the radio stays in its programming
#    session for the rest of the connection AND across reconnects until it
#    is power-cycled. Every byte is parsed as a command: R and W frames are
#    executed, anything else is ignored, and an ident is never accepted
#    mid-session ("PROGRAM..." holds `R O G R`, which it executes as a
#    read). --session-timeout SEC ends an idle session (unknown on the real
#    radio; default: never).
#  * uv5r (UV-5RE): after the magic + ident the radio is in clone mode; S
#    and X frames are executed, our 06 acks swallowed, other bytes (a new
#    magic included) silently ignored. The session ends after
#    --uv5r-timeout seconds without traffic (default 4; the real radio:
#    between ~2.5 and ~5.5 s).
# Power-cycle: SIGUSR1, or touching --power-file.
# Cable faults: --drop-first N drops the first N bytes after each open of
# the port, --drop-ms M drops what arrives in the first M ms after an open
# (a CH340 losing bytes right after open / line changes), --reply-delay MS
# delays every answer. An "open" is seen through pty packet mode: opening
# flushes both directions (TIOCPKT_FLUSHWRITE), which nothing else does.
# --capture FILE appends every received byte; --stats FILE keeps counters.
#
# Protocol details (match CHIRP's expectations and the owner's hardware):
#  * uv17pro: "PROGRAM...U" -> 06; 'F' -> 16 bytes; 'M' -> model reply;
#    'SEND...' (25 bytes) -> 06; 'R' a a 40 -> header + scrambled data;
#    'W' a a 40 + data -> 06. Bytes before an ident are ignored.
#  * uv5r: magic -> 06; 02 -> 8-byte ident; 06 -> 06; 'S' a a n -> [06 unless
#    first after ident] + 'X' a a n + data; 'X' a a n + data -> 06.
#    A wrong magic gets no answer.

import argparse
import configparser
import fcntl
import os
import struct
import termios
import select
import signal
import sys
import time
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
        self.family = ini.get("model", "engine")
        self.image = bytearray(open(args.image, "rb").read())
        self.buf = bytearray()
        self.state = "idle"
        self.counts = dict(idents_accepted=0, reads=0, writes=0, power_cycles=0)
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
            self.timeout = args.session_timeout
        else:
            self.ident = bytes.fromhex(args.ident) if args.ident else bytes(self.image[:8])
            self.aux = link.get("aux", "yes") != "no"
            self.first = True
            self.timeout = args.uv5r_timeout

    def log(self, msg):
        if self.args.log:
            sys.stderr.write(msg + "\n")

    def power_cycle(self):
        self.state = "idle"
        self.buf.clear()
        self.counts["power_cycles"] += 1
        self.log("power-cycled")
        self.write_stats()

    def idle_tick(self, idle_s):
        if self.timeout and self.state != "idle" and idle_s > self.timeout:
            self.log("session timed out")
            self.state = "idle"
            self.buf.clear()

    def write_stats(self):
        if self.args.stats:
            with open(self.args.stats + ".tmp", "w") as f:
                for k, v in sorted(self.counts.items()):
                    f.write("%s %d\n" % (k, v))
                f.write("state %s\n" % self.state)
            os.replace(self.args.stats + ".tmp", self.args.stats)

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
        self.write_stats()

    def idle_match(self, candidates, on_match):
        for c in candidates:
            i = self.buf.find(c)
            if i >= 0:
                del self.buf[:i + len(c)]
                on_match(c)
                return True
        keep = max(len(c) for c in candidates) if candidates else 0
        if len(self.buf) > keep:
            del self.buf[:len(self.buf) - keep]
        return False

    def read_frame(self, send, prefix=b""):
        hdr = self.take(4)
        addr = (hdr[1] << 8) | hdr[2]
        n = hdr[3]
        if self.family == "uv17pro":
            off = self.uv17_off(addr, n)
            data = bytes(self.image[off:off + n]) if off is not None else b"\xff" * n
            send(hdr + crypt(self.key, data))
        else:
            off = self.uv5r_off(addr, n)
            data = bytes(self.image[off:off + n]) if off is not None else b"\xff" * n
            send(prefix + b"X" + hdr[1:4] + data)
        self.counts["reads"] += 1

    def write_frame(self, send):
        n = self.buf[3]
        if not self.need(4 + n):
            return False
        frame = self.take(4 + n)
        addr = (frame[1] << 8) | frame[2]
        off = self.uv17_off(addr, n) if self.family == "uv17pro" else self.uv5r_off(addr, n)
        if off is None:
            send(b"\x15")
            return True
        payload = crypt(self.key, frame[4:]) if self.family == "uv17pro" else frame[4:]
        self.image[off:off + n] = payload
        self.counts["writes"] += 1
        self.dump()
        send(ACK)
        return True

    def step_uv17pro(self, send):
        if self.state == "idle":
            def matched(_):
                send(ACK)
                self.counts["idents_accepted"] += 1
                self.state = "program"
            return self.idle_match(self.idents, matched)
        b = self.buf[0]
        in_session = self.state == "session"
        if b == 0x46 and not in_session:  # F
            self.take(1)
            send(self.f_reply)
            return True
        if b == 0x4D and not in_session:  # M
            self.take(1)
            want = 15
            for m, n in self.magics:
                if m == b"M":
                    want = n
            send(self.m_reply[:want])
            return True
        if b == 0x53 and not in_session:  # SEND...
            if not self.need(25):
                return False
            self.take(25)
            send(ACK)
            self.state = "session"
            return True
        if b == 0x52:  # R
            if not self.need(4):
                return False
            self.read_frame(send)
            self.state = "session"
            return True
        if b == 0x57:  # W
            if not self.need(4):
                return False
            if not self.write_frame(send):
                return False
            self.state = "session"
            return True
        # the radio ignores what it cannot parse, and stays where it is
        self.take(1)
        return True

    def step_uv5r(self, send):
        if self.state == "idle":
            def matched(_):
                send(ACK)
                self.state = "ident"
            return self.idle_match([m for m, _ in self.magics], matched)
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
                self.counts["idents_accepted"] += 1
                self.state = "clone"
                self.first = True
            else:
                self.state = "idle"
            return True
        # clone: S and X executed, anything else (06 acks, a magic) ignored
        if b == 0x53:  # S
            if not self.need(4):
                return False
            prefix = b"" if self.first else ACK
            self.first = False
            self.read_frame(send, prefix)
            return True
        if b == 0x58:  # X
            if not self.need(4):
                return False
            return self.write_frame(send)
        self.take(1)
        return True


def main():
    ap = argparse.ArgumentParser(description="beautalks radio emulator")
    ap.add_argument("--model", required=True, help="models/*.ini to impersonate")
    ap.add_argument("--image", required=True, help="memory image to serve")
    ap.add_argument("--dump", help="write the (possibly updated) image here")
    ap.add_argument("--port-file", help="write the pty path here")
    ap.add_argument("--m-reply", help="uv17pro 'M' reply text (default: the owner's 5RM)")
    ap.add_argument("--f-reply", default="01360174040005200200026080848A94",
                    help="uv17pro 'F' reply, hex")
    ap.add_argument("--ident", help="uv5r ident reply, hex (default: image[0:8])")
    ap.add_argument("--session-timeout", type=float, default=0,
                    help="uv17pro: seconds of silence that end a session (0: never)")
    ap.add_argument("--uv5r-timeout", type=float, default=4.0,
                    help="uv5r: seconds of silence that end a clone session")
    ap.add_argument("--power-file", help="touching this file power-cycles the radio")
    ap.add_argument("--capture", help="append every received byte to this file")
    ap.add_argument("--stats", help="keep counters (idents_accepted, reads, writes, ...) in this file")
    ap.add_argument("--log", action="store_true", help="log traffic to stderr")
    ap.add_argument("--drop-first", type=int, default=0, help="drop the first N bytes after each open")
    ap.add_argument("--drop-ms", type=float, default=0, help="drop bytes arriving in the first MS ms after each open")
    ap.add_argument("--reply-delay", type=float, default=0, help="delay every answer by MS ms")
    args = ap.parse_args()

    ini = configparser.ConfigParser(interpolation=None, comment_prefixes=(";", "#"),
                                    inline_comment_prefixes=None)
    ini.read(args.model)
    radio = Radio(args, ini)

    master, slave = os.openpty()
    tty.setraw(slave)
    # packet mode: each read from the master starts with a control byte
    fcntl.ioctl(master, termios.TIOCPKT, struct.pack("i", 1))
    TIOCPKT_FLUSHWRITE = 0x02
    opened_at = [None]
    drop_left = [0]
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
    signal.signal(signal.SIGUSR1, lambda *_: radio.power_cycle())
    power_mtime = os.path.getmtime(args.power_file) if args.power_file and os.path.exists(args.power_file) else None
    last_rx = time.monotonic()
    radio.write_stats()

    def send(data):
        if args.reply_delay:
            time.sleep(args.reply_delay / 1000.0)
        if args.log:
            sys.stderr.write("<- %s\n" % data.hex())
        os.write(master, data)

    while running[0]:
        try:
            r, _, _ = select.select([master], [], [], 0.1)
        except InterruptedError:
            continue
        if args.power_file and os.path.exists(args.power_file):
            mt = os.path.getmtime(args.power_file)
            if mt != power_mtime:
                power_mtime = mt
                radio.power_cycle()
        radio.idle_tick(time.monotonic() - last_rx)
        if not r:
            continue
        try:
            pkt = os.read(master, 4097)
        except OSError:
            continue
        if not pkt:
            continue
        if pkt[0] != 0:
            # a control packet: the port was opened (both directions flushed)
            if pkt[0] & TIOCPKT_FLUSHWRITE:
                opened_at[0] = time.monotonic()
                drop_left[0] = args.drop_first
                radio.log("port opened")
            continue
        data = pkt[1:]
        if opened_at[0] is not None and args.drop_ms and time.monotonic() - opened_at[0] < args.drop_ms / 1000.0:
            radio.log("dropped %d bytes (just opened)" % len(data))
            continue
        if drop_left[0] > 0:
            cut = min(drop_left[0], len(data))
            drop_left[0] -= cut
            radio.log("dropped %d bytes (first after open)" % cut)
            data = data[cut:]
            if not data:
                continue
        last_rx = time.monotonic()
        if args.capture:
            with open(args.capture, "ab") as f:
                f.write(data)
        if args.log:
            sys.stderr.write("-> %s\n" % data.hex())
        radio.feed(data, send)
    radio.dump()
    os.close(slave)
    os.close(master)


if __name__ == "__main__":
    main()
