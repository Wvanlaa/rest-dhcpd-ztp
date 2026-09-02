#!/usr/bin/env python3
"""Genereer de hexwaarde voor DHCP optie 43 met sub-opties.

Gebruik: ./optie43-hex.py 145 "http://10.10.10.1/ztp.cfg"
         ./optie43-hex.py 144 "primary" 145 "http://10.10.10.1/ztp.cfg"
"""
import sys

args = sys.argv[1:]
if not args or len(args) % 2:
    sys.exit("Gebruik: optie43-hex.py <subcode> <waarde> [<subcode> <waarde> ...]")

tlv = b""
for i in range(0, len(args), 2):
    code = int(args[i])
    value = args[i + 1].encode("ascii")
    if not 0 <= code <= 255:
        sys.exit(f"Sub-optiecode {code} valt buiten 0-255")
    if len(value) > 255:
        sys.exit(f"Waarde voor sub-optie {code} is te lang ({len(value)} bytes)")
    tlv += bytes([code, len(value)]) + value

if len(tlv) > 255:
    sys.exit(f"Totale optie 43 is te lang ({len(tlv)} bytes)")

print("0x" + tlv.hex())
