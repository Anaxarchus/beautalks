#!/bin/bash
# Find the Baofeng programming cable on macOS.
# Usage: bash explore/find_cable.sh   (run once unplugged, once plugged in, and compare)
echo "== USB devices (look for Prolific/PL2303, WCH/CH340, FTDI, Silicon Labs CP210x) =="
system_profiler SPUSBDataType 2>/dev/null | grep -E -A6 -i 'serial|prolific|pl2303|ch34|wch|ftdi|cp210|silicon|usb-serial|baofeng' || echo "(no obvious USB-serial chip listed)"
echo
echo "== Vendor/product IDs =="
ioreg -p IOUSB -l -w0 2>/dev/null | grep -E '"USB Product Name"|"idVendor"|"idProduct"' | paste - - - 2>/dev/null
echo
echo "== Serial device nodes (use the /dev/cu.* one) =="
ls -l /dev/cu.* /dev/tty.* 2>/dev/null | grep -v -i bluetooth
echo
echo "== Loaded serial drivers =="
kextstat 2>/dev/null | grep -i -E 'serial|prolific|wch|ftdi|silabs' || systemextensionsctl list 2>/dev/null | grep -i -E 'serial|prolific|wch|ftdi|silabs'
