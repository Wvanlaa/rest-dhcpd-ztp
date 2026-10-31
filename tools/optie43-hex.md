# optie43-hex.py

Generates the hexadecimal value for DHCP option 43 with encapsulated sub-options, for use
with the hex-encoded option support added in this fork (see [`PATCH-NOTES.md`](../PATCH-NOTES.md)).

Writing option 43 by hand means counting bytes and converting ASCII to hex without making a
mistake in the length fields. This script does that for you.

---

## Why option 43 needs a generator

Option 43 is not a plain string. It is a container holding one or more TLV triplets —
**T**ype (the sub-option code), **L**ength, **V**alue:

```
2B 1B 91 19 41 72 75 62 61 4F 53 ...
│  │  │  │  └─ value: the image filename, in ASCII
│  │  │  └──── length of the sub-option value (25 bytes = 0x19)
│  │  └─────── sub-option code 145 (0x91)
│  └────────── length of option 43 (27 bytes = 0x1B)
└───────────── option code 43 (0x2B)
```

The script produces **only the inner part** — the sub-option triplets. The DHCP library adds
option code `43` and the outer length byte itself, so you never supply those.

Every length byte has to match its value exactly. Change one character in a filename and the
length changes with it; a mismatch makes the switch reject or misread the option. That is the
entire reason this script exists.

## Requirements

Python 3. No modules beyond the standard library, so it runs on any stock system.

```bash
chmod +x tools/optie43-hex.py
```

## Usage

```
./tools/optie43-hex.py <sub-option> <value> [<sub-option> <value> ...]
```

Arguments come in pairs: a sub-option code (0–255) followed by its value. The output is a
single `0x…` string, ready to paste into the configuration.

### One sub-option

```bash
$ ./tools/optie43-hex.py 145 "ArubaOS-CX_10_13_1000.swi"
0x911941727562614f532d43585f31305f31335f313030302e737769
```

### Several sub-options

Order is preserved, so they appear on the wire in the order you list them:

```bash
$ ./tools/optie43-hex.py 144 "primary" 145 "ArubaOS-CX_10_13_1000.swi"
0x90077072696d617279911941727562614f532d43585f31305f31335f313030302e737769
```

## Using the output

Paste the value under option `43`. It works globally, per interface, or per client, because
all three go through the same option builder.

In `rest-dhcpd-config.json`:

```json
"Options": {
  "6": ["10.0.0.10", "10.0.0.11"],
  "43": "0x911941727562614f532d43585f31305f31335f313030302e737769"
}
```

Or per client over the REST API:

```bash
curl -X PUT http://127.0.0.1:6767/client/aa:bb:cc:dd:ee:ff \
  -H "REST-DHCPD-Auth-Token: $TOKEN" \
  -d '{"Hostname":"sw-01","IP":"10.10.10.50",
       "Options":{"43":"0x911941727562614f532d43585f31305f31335f313030302e737769"}}'
```

---

## Important: pass the filename exactly as the client must request it

**The script never looks at the filesystem.** It encodes the literal text you pass, byte for
byte. Whatever string goes in is exactly what the switch will ask the TFTP server for.

So the value must be the path **relative to the TFTP root**, not a path on your own machine.
If the image sits in the root of the TFTP server, that means the bare filename and nothing
else:

```bash
# correct — image is in the TFTP root
$ cd /srv/tftp
$ ~/optie43-hex.py 145 "ArubaOS-CX_10_13_1000.swi"
0x911941727562614f532d43585f31305f31335f313030302e737769
```

```bash
# wrong — the whole local path ends up in the hex
$ ~/optie43-hex.py 145 "/srv/tftp/ArubaOS-CX_10_13_1000.swi"
```

In the second case the switch requests `/srv/tftp/ArubaOS-CX_10_13_1000.swi` *relative to the
TFTP root*, which does not exist, and the ZTP boot fails with a file-not-found that gives no
hint about the real cause.

This is easy to get wrong through shell tab-completion: completing a filename from another
directory inserts the full path. **Run the script from the TFTP root directory**, so that
tab-completion produces the bare filename and what you type is what the client gets.

If the image lives in a subdirectory of the TFTP root, include that subdirectory and nothing
above it:

```bash
$ cd /srv/tftp
$ ~/optie43-hex.py 145 "images/ArubaOS-CX_10_13_1000.swi"
0x9120696d616765732f41727562614f532d43585f31305f31335f313030302e737769
```

### Verify the file is actually there

The script cannot catch a typo, and neither can the DHCP exchange — the failure only shows up
when the switch tries to download. Check before you generate:

```bash
cd /srv/tftp
IMAGE="ArubaOS-CX_10_13_1000.swi"
ls -l "$IMAGE" && ~/optie43-hex.py 145 "$IMAGE"
```

No hex output means the file is not where you think it is.

---

## Limits and validation

The script refuses input that cannot be encoded, rather than producing a value that silently
fails on the wire:

| Check | Message |
| --- | --- |
| Arguments not in pairs | `Usage: optie43-hex.py <subcode> <value> ...` |
| Sub-option code outside 0–255 | `Sub-option code N is outside 0-255` |
| A single value longer than 255 bytes | `Value for sub-option N is too long` |
| All sub-options together over 255 bytes | `Total option 43 is too long` |

Values are encoded as ASCII. A non-ASCII character raises a `UnicodeEncodeError` — filenames
for network boot should be plain ASCII anyway.

## Decoding a value you already have

To read back an existing hex string, for example from a configuration file you inherited:

```bash
python3 -c "
import sys, binascii
b = binascii.unhexlify(sys.argv[1].removeprefix('0x'))
i = 0
while i < len(b):
    code, length = b[i], b[i+1]
    print(f'sub-option {code}: {b[i+2:i+2+length].decode(\"ascii\", \"replace\")}')
    i += 2 + length
" 0x911941727562614f532d43585f31305f31335f313030302e737769
```

## Checking the result on the wire

```bash
sudo tcpdump -ni <interface> -vv -X port 67 or port 68
```

Look for `2b 1b 91 19 …` in the DHCPOFFER: option 43, its total length, then your first
sub-option.

Note that the reply is filtered against the client's parameter request list (option 55). If
the switch does not ask for option 43, the server will not send it, no matter how the value
is configured.
