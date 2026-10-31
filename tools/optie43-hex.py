#!/usr/bin/env python3
"""Generate the hexadecimal value for DHCP option 43 with sub-options.

Usage: ./optie43-hex.py 145 "ArubaOS-CX_10_13_1000.swi"
       ./optie43-hex.py 144 "primary" 145 "ArubaOS-CX_10_13_1000.swi"
"""
import sys

args = sys.argv[1:]
if not args or len(args) % 2:
    sys.exit("Usage: optie43-hex.py <subcode> <value> [<subcode> <value> ...]")

tlv = b""
for i in range(0, len(args), 2):
    code = int(args[i])
    value = args[i + 1].encode("ascii")
    if not 0 <= code <= 255:
        sys.exit(f"Sub-option code {code} is outside 0-255")
    if len(value) > 255:
        sys.exit(f"Value for sub-option {code} is too long ({len(value)} bytes)")
    tlv += bytes([code, len(value)]) + value

if len(tlv) > 255:
    sys.exit(f"Total option 43 is too long ({len(tlv)} bytes)")

print("0x" + tlv.hex())
