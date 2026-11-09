#!/usr/bin/env python3
# beautalks - radio programming software
# Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
#
# tools/emu.py with the radio switched OFF for the first --on-after seconds:
# the port exists from the start (the cable is plugged in) but nothing
# answers; after that the radio behaves as just switched on. For the app's
# presence-probe test ("radio switched on later"). Every other option is
# tools/emu.py's.
#
#   python3 tools/emu_late.py --on-after 6 --model models/uv-5rm.ini \
#       --image testdata/uv5rm.img --port-file /tmp/emu.port

import importlib.util
import os
import sys
import time


def main():
    on_after = 0.0
    argv = sys.argv[1:]
    if "--on-after" in argv:
        i = argv.index("--on-after")
        on_after = float(argv[i + 1])
        del argv[i:i + 2]
    sys.argv = [sys.argv[0]] + argv
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("emu", os.path.join(here, "emu.py"))
    emu = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(emu)
    t0 = time.monotonic()
    feed = emu.Radio.feed

    def feed_when_on(self, data, send):
        if time.monotonic() - t0 < on_after:
            self.log("off: ignored %d bytes" % len(data))
            return
        feed(self, data, send)
    emu.Radio.feed = feed_when_on
    emu.main()


if __name__ == "__main__":
    main()
