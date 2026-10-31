# Fork notes — hex-encoded DHCP option values

This fork adds one capability to upstream `vinted/rest-dhcpd`: the ability to configure
**binary DHCP options**, in particular option 43 (vendor specific information) carrying
encapsulated sub-options.

- **Based on upstream:** tag `0.4.0`, commit `e7c0e15` ("Add multi-interface support")
- **Scope:** one changed line, one new file, one helper script. No change to existing behaviour.

---

## Why this change exists

The server is used to drive Zero Touch Provisioning for HPE Aruba AOS-CX switches. Those
switches expect option 43 with sub-option 145, which carries the firmware image filename.

Option 43 is not a string. It is a container of TLV triplets — sub-option code, length byte,
payload:

```
2B 1B 91 19 41 72 75 62 61 ...
│  │  │  │  └─ payload (the image filename)
│  │  │  └──── length of sub-option payload (25 = 0x19)
│  │  └─────── sub-option 145 (0x91)
│  └────────── length of option 43 (27 = 0x1B)
└───────────── option 43 (0x2B)
```

Upstream builds every non-IP option value with `[]byte(fmt.Sprint(value))` in `BuildOptions`
(`pkg/dhcpd/dhcpd.go`). JSON strings in Go are UTF-8, so a byte such as `0x91` is encoded as
two bytes (`0xC2 0x91`) once cast. The length byte is usually a non-printable control
character as well. A TLV header therefore cannot be expressed through a JSON string, and
option 43 with sub-options was impossible to configure.

## What changed

### `pkg/dhcpd/hexoption.go` (new)

Adds `optionValueToBytes(value interface{}) []byte`:

- A value prefixed with `0x` or `0X` is decoded with `hex.DecodeString` and used as raw bytes.
- Any other value is cast exactly as before, so existing configurations are unaffected.
- A value that looks hexadecimal but fails to decode is logged and falls back to plain text,
  so a typo never silently produces an empty option.

### `pkg/dhcpd/dhcpd.go` (one line)

```diff
-			val = []byte(fmt.Sprint(value))
+			val = optionValueToBytes(value)
```

Because `BuildOptions` is called for global, per-interface and per-client options alike, hex
values work at all three levels without further changes.

### `tools/optie43-hex.py` (new)

Helper that builds the hex string, so length bytes never have to be counted by hand:

```
./tools/optie43-hex.py 145 "ArubaOS-CX_6300_10_16_1040.swi"
./tools/optie43-hex.py 144 "primary" 145 "ArubaOS-CX_6300_10_16_1040.swi"
```

It validates that each sub-option code fits in a byte, that each payload is at most 255
bytes, and that the whole option stays within 255 bytes. The output contains **only the
encapsulated sub-options** — the DHCP library adds option code 43 and the outer length byte
itself.

## Usage

Any option may now take a hex value. In `rest-dhcpd-config.json`, globally or per interface:

```json
"Options": {
  "6": ["10.0.0.10", "10.0.0.11"],
  "43": "0x9119417275626146532d4358..."
}
```

Or per client over the REST API:

```bash
curl -X PUT http://127.0.0.1:6767/client/aa:bb:cc:dd:ee:ff \
  -H "REST-DHCPD-Auth-Token: $TOKEN" \
  -d '{"Hostname":"sw-01","IP":"10.10.10.50","Options":{"43":"0x9119..."}}'
```

## Verification

`go test ./...` passes. `pkg/dhcpd` is the only package with tests, and it is the package
changed here: `TestBuildOptions` exercises the modified code path, so the existing behaviour
for text and IP options is covered.

On the wire, option 43 should appear in the DHCPOFFER as `2b 1b 91 19 ...`:

```bash
sudo tcpdump -ni <interface> -vv -X port 67 or port 68
```

Note that `SelectOrderOrAll` filters the reply against the client's parameter request list
(option 55). A correctly configured option that the client does not request will not be sent.

## Maintenance

To carry this change onto a newer upstream release, rebase this branch onto the new tag. The
patch touches a single line of existing code, so conflicts are unlikely unless `BuildOptions`
itself is rewritten.
