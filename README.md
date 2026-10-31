# REST DHCPD
DHCP server controlled via REST endpoints.
This is a patched version created by Vinted - https://github.com/vinted/rest-dhcpd.git.
This version can be used with HPE Networking ZTP (tested on CX line) for adding Option 43 with SubOption 145 to provide the software image name.
PATCH-NOTES.md holds details of how patch is done.

/tools/optie43-hex.py is a simple script to generate the hex-value that needs to be added with the client DHCP record.

## Configuration

By default configuration files are located in `/etc/rest-dhcpd` directory.
This can be overridden with `-configPath` command-line argument.
Global server configuration is stored in `rest-dhcpd-config.json` file:

```
{
    "LeaseDuration": 30,
    "AuthToken": "secretToken",
    "HTTPListenAddress": "127.0.0.1:6767",
    "TLSEnabled": true,
    "TLSPrivateKeyFile": "example.key",
    "TLSCertificateFile": "example.crt",
    "Options": {
      "6": ["1.1.1.1", "8.8.8.8"]
    },
    "Interfaces": [
      {
        "Name": "virbr1",
        "IP": "192.168.100.1",
        "Options": {
          "1": "255.255.255.0",
          "3": "192.168.100.1"
        }
      },
      {
        "Name": "virbr2",
        "IP": "10.0.0.1",
        "LeaseDuration": 3600,
        "Options": {
          "1": "255.255.0.0",
          "3": "10.0.0.1"
        }
      }
    ]
}
```

- `LeaseDuration` - default DHCP lease duration in seconds. Used by any interface that does not set its own.
- `AuthToken` - authentication token for REST interface.
- `HTTPListenAddress` - address to listen for HTTP requests. To listen on all network addresses use port without any IP address `:6767`.
- `TLSEnabled` - start REST interface with HTTPS support.
- `TLSPrivateKeyFile` - private key file for HTTPS support.
- `TLSCertificateFile` - certificate file for HTTPS support.
- `Options` - top-level DHCP options applied to every interface as defaults. Per-interface `Options` override these per option key, and per-client `Options` override both.
- `Interfaces` - list of interfaces to listen on. Must contain at least one entry. Each entry has:
  - `Name` - network interface name (e.g. `virbr1`).
  - `IP` - IP address of the DHCP server on this interface (used as the server identifier in responses).
  - `LeaseDuration` - optional lease duration override for this interface. If omitted, the top-level value is used.
  - `Options` - DHCP options specific to this subnet. Merged on top of the top-level `Options`.

Requests are served by whichever interface received them; the response uses that interface's `IP` and its merged option set.

#### Migration from single-interface configs
If upgrading from a version with top-level `IP` and `ListenInterface`, move those values into a one-element `Interfaces` array along with the subnet-specific entries from `Options`. Any options shared across interfaces (e.g. DNS) can stay at the top level as defaults.

For backwards compatibility, the legacy top-level `IP` and `ListenInterface` fields are still accepted: if `Interfaces` is omitted and these fields are set, a single-entry `Interfaces` array is synthesized from them at startup and a deprecation warning is logged. Configs that set both forms are rejected.

### Basics
REST DHCP server does not provide dynamic DHCP leases. It only provides leases to configured clients.
Clients are added, deleted and modified via REST interface. Client configuration is stored in `-configPath` folder, `rest-dhcpd-clients.json` file.

## API

REST API supports following methods:
`GET, PUT, DELETE`

### API endpoints

`/` - supports `GET` method. Displays index page.  
`/metrics` - supports `GET` method. Displays prometheus metrics.  
`/clients` - supports `GET` method. Lists all configured clients.  
`/client/AA:BB:CC:DD:EE:FF` - supports:  
		- `GET` - displays configuration of a client defined by `AA:BB:CC:DD:EE:FF` `MAC` address.  
		- `DELETE` - deletes configuration of a client defined by `AA:BB:CC:DD:EE:FF` `MAC` address.  
		- `PUT` -  creates new or update existing configuration of a client defined by `AA:BB:CC:DD:EE:FF` `MAC` address.  

### Examples

#### List all available clients
```
curl http://127.0.0.1:6767/clients -H "REST-DHCPD-Auth-Token: secretToken"
```
##### Display configuration of a specific client
```
curl http://127.0.0.1:6767/client/aa:bb:cc:dd:ee:ff -H "REST-DHCPD-Auth-Token: secretToken"
```
#####  Add or update client
```
curl  -X PUT http://127.0.0.1:6767/client/aa:bb:cc:dd:ee:ff -H "REST-DHCPD-Auth-Token: secretToken" -d '{"Hostname":"test4","IP":"192.168.13.17","Options":{"13":"option13"}}'
```
##### HPE CX ZTP example

Option 43 carries encapsulated sub-options, so its value is given as a hex string prefixed
with `0x`. Sub-option 145 holds the firmware image filename the switch should fetch, as a
path relative to the TFTP root.

```
curl -X PUT http://127.0.0.1:6767/client/aa:bb:cc:dd:ee:ff -H "REST-DHCPD-Auth-Token: secretToken" -d '{"Hostname":"sw-01","IP":"192.168.13.17","Options":{"66":"192.168.13.1","43":"0x911941727562614f532d43585f31305f31335f313030302e737769"}}'
```

Here option 66 points at the TFTP server and the option 43 value decodes to sub-option 145
with the value `ArubaOS-CX_10_13_1000.swi`. Use `tools/optie43-hex.py` to generate the hex
string; see [tools/optie43-hex.md](tools/optie43-hex.md) for details.

##### Delete client
```
curl -X DELETE http://127.0.0.1:6767/client/aa:bb:cc:dd:ee:ff -H "REST-DHCPD-Auth-Token: secretToken"
```

#### HTTP return codes
`200` - OK. Request was completed successfully.  
`400` - BadRequest. Reports that configuration cannot be added or updated. HTTP body will display more detailed information about error.  
`401` - Unauthorized.  `REST-DHCPD-Auth-Token` provided by client does not mach token in configuration.  
