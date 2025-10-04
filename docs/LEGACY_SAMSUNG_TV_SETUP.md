# Legacy Samsung TV Network Control Setup

**Date:** October 4, 2025
**TV Model:** LA40D550 (2011 D-series)
**IP:** 192.168.101.50
**MAC:** E4:E0:C5:B8:5A:97

---

## Discovery Results

✅ **TV Found and Identified**
- Model: Samsung LA40D550 (2011 D-series)
- Protocol: Legacy Samsung protocol (port 55000)
- Port 55000: **OPEN** ✓
- Network: Same subnet as SmartVenue (192.168.101.x)
- Status: Online and reachable

**Library Used:** `samsungctl` (not `samsungtvws`)
- Modern Samsung TVs (2016+): Use WebSocket on port 8001/8002
- Legacy Samsung TVs (2011-2015): Use TCP on port 55000

---

## Connection Test Results

### Initial Connection Attempt
```
Testing Legacy Samsung TV: 192.168.101.50
Connecting to TV...
✗ Connection failed: timed out
WARNING: Waiting for authorization...
```

**Interpretation:**
- Port 55000 is accessible ✓
- TV received connection request ✓
- **TV is waiting for user to accept pairing on-screen** ⏳

This is the same pairing flow as newer Samsung TVs - the user must accept the connection request on the TV screen.

---

## Pairing Procedure

### Step 1: Enable Network Control on TV

**On the TV (using physical remote):**

1. Press **MENU** button
2. Navigate to **Network** (or **System**)
3. Look for **AllShare Settings** or **Network Remote Control**
4. Enable the network control feature

**D-Series Specific Paths:**
- Menu → Network → AllShare Settings → Enable
- Menu → System → Device Manager → Enable External Device Control

### Step 2: Initiate Pairing from Server

Run the pairing script:

```bash
cd /home/coastal/smartvenue/backend
source ../venv/bin/activate
python test_legacy_samsung.py
```

**What happens:**
1. Script connects to TV on port 55000
2. TV displays on-screen prompt: "Allow SmartVenue to connect?"
3. **Accept on TV within 30 seconds** using remote
4. Connection succeeds and test commands execute

### Step 3: Accept Pairing on TV Screen

**Watch for pop-up on TV:**
- Message: "SmartVenue wants to connect to this TV"
- Options: "Allow" / "Deny"
- **Select "Allow" using TV remote**

**Note:** Some D-series models may show:
- "External Device Connection Request"
- "PC/Mobile Connection"
- Similar authorization message

---

## Available Commands

Once paired, the following commands are available:

| Command | Description |
|---------|-------------|
| `KEY_POWER` | Power on/off toggle |
| `KEY_VOLUP` | Volume up |
| `KEY_VOLDOWN` | Volume down |
| `KEY_MUTE` | Mute/unmute |
| `KEY_CHUP` | Channel up |
| `KEY_CHDOWN` | Channel down |
| `KEY_SOURCE` | Input/source selection |
| `KEY_HDMI` | HDMI input |
| `KEY_MENU` | Menu |
| `KEY_TOOLS` | Tools menu |
| `KEY_INFO` | Info display |
| `KEY_EXIT` | Exit/back |
| `KEY_RETURN` | Return |
| `KEY_UP` | Navigate up |
| `KEY_DOWN` | Navigate down |
| `KEY_LEFT` | Navigate left |
| `KEY_RIGHT` | Navigate right |
| `KEY_ENTER` | Enter/select |
| `KEY_0` to `KEY_9` | Number keys |

---

## Python Code Example

```python
import samsungctl

config = {
    "name": "SmartVenue",
    "description": "SmartVenue Control System",
    "id": "smartvenue",
    "host": "192.168.101.50",
    "port": 55000,
    "method": "legacy",
    "timeout": 3,
}

# Send command
with samsungctl.Remote(config) as remote:
    remote.control("KEY_VOLUP")
    remote.control("KEY_POWER")
```

---

## Key Differences: Legacy vs Modern Samsung TVs

| Feature | Legacy (D/E/F series) | Modern (Tizen 2016+) |
|---------|----------------------|----------------------|
| **Port** | 55000 (TCP) | 8001/8002 (WebSocket) |
| **Library** | `samsungctl` | `samsungtvws` |
| **Protocol** | Binary TCP | WebSocket/JSON |
| **Authentication** | On-screen pairing | Token-based |
| **Token Storage** | Not needed | Required for future connections |
| **Status Queries** | Limited/none | Full status feedback |
| **Power On** | Wake-on-LAN or IR | Network command |

---

## Integration Plan

### Database Schema

**For Legacy Samsung TVs:**
```sql
-- Virtual device entry
INSERT INTO devices (hostname, ip_address, device_type, device_subtype, network_protocol)
VALUES ('samsung-tv-50', '192.168.101.50', 'universal', 'virtual_network_tv', 'samsung_legacy');

-- Port assignment (port 1, no GPIO)
INSERT INTO port_assignments (device_hostname, port_number, library_id, device_name)
VALUES ('samsung-tv-50', 1, 123, 'Bar TV - Samsung LA40D550');

-- Network credentials (legacy method doesn't need token)
INSERT INTO network_tv_credentials (device_hostname, protocol, host, port, method)
VALUES ('samsung-tv-50', 'samsung_legacy', '192.168.101.50', 55000, 'legacy');
```

### Command Dispatcher Logic

```python
def send_tv_command(hostname: str, command: str):
    device = get_device(hostname)

    if device.network_protocol == 'samsung_legacy':
        # Use samsungctl
        config = {
            "host": device.ip_address,
            "port": 55000,
            "method": "legacy",
            "name": "SmartVenue",
        }
        with samsungctl.Remote(config) as remote:
            remote.control(f"KEY_{command.upper()}")

    elif device.network_protocol == 'samsung_websocket':
        # Use samsungtvws for newer TVs
        tv = SamsungTVWS(host=device.ip_address, token=device.token)
        tv.shortcuts().power()
```

---

## Next Steps

1. **Accept pairing on TV screen** when running test script
2. **Verify commands work** (volume up/down test)
3. **Map IR commands to KEY codes** (create translation table)
4. **Implement backend API endpoint** for legacy Samsung control
5. **Create virtual device entry** in database
6. **Test via SmartVenue API** using existing command structure

---

## Troubleshooting

### Issue: "Waiting for authorization" timeout

**Cause:** User didn't accept pairing within timeout period

**Solution:**
1. Re-run pairing script
2. Watch TV screen immediately
3. Accept pairing popup within 30 seconds

### Issue: Connection refused

**Cause:** Network control disabled in TV settings

**Solution:**
1. Press MENU on TV remote
2. Navigate to Network or System settings
3. Enable "AllShare Settings" or network remote control
4. Restart TV

### Issue: Commands don't work after pairing

**Cause:** Pairing was denied or timed out

**Solution:**
- Pair again and ensure "Allow" is selected
- Check TV logs/settings for connected devices
- Some models require pairing each time (no persistent token)

---

## Status

- ✅ TV discovered on network
- ✅ Port 55000 accessible
- ✅ samsungctl library installed
- ⏳ **Waiting: Accept pairing on TV screen**
- ⏳ Test commands (volume, power)
- ⏳ Database integration
- ⏳ API endpoint implementation

**Current Blocker:** Need physical access to TV to accept pairing popup

---

## References

- **Library:** https://github.com/Ape/samsungctl
- **Home Assistant Integration:** Uses same library for D/E/F/H/J series
- **Protocol:** Samsung Legacy Remote Control Protocol (port 55000)
