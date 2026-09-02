package dhcpd

import (
	"encoding/hex"
	"fmt"
	"log"
	"strings"
)

// optionValueToBytes converts a configured DHCP option value into raw bytes.
//
// Values prefixed with "0x" are decoded as hexadecimal. This makes it possible
// to configure binary options such as option 43 (vendor specific information)
// with encapsulated sub-options, which cannot be expressed as plain text.
//
// Any other value keeps the previous behaviour and is used as-is. A value that
// looks like hex but fails to decode is logged and used as plain text, so a
// typo never silently produces an empty option.
func optionValueToBytes(value interface{}) []byte {
	s := fmt.Sprint(value)

	if len(s) > 2 && (strings.HasPrefix(s, "0x") || strings.HasPrefix(s, "0X")) {
		decoded, err := hex.DecodeString(s[2:])
		if err != nil {
			log.Printf("dhcpd: option value %q looks hexadecimal but could not be decoded (%v), using it as plain text", s, err)
			return []byte(s)
		}
		return decoded
	}

	return []byte(s)
}
