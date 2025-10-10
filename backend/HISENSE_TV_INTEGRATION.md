# Hisense TV Network Control Integration

**Date:** October 6, 2025
**Protocol:** MQTT on port 36669
**Library:** `hisensetv` v0.3.0
**Status:** ✅ Implemented and ready for testing

---

## Overview

Hisense TVs with VIDAA OS can be controlled via their internal MQTT broker running on port 36669. This integration provides full remote control capabilities including volume, channels, navigation, and power management.

### Key Features

✅ Full remote control via MQTT
✅ Wake-on-LAN support for power-on
✅ Source/input switching
✅ Query TV state (volume, sources)
✅ App launching (Netflix, YouTube, etc.)
✅ No authentication tokens required (uses default credentials)

---

## How It Works

### MQTT Protocol

Hisense TVs run an MQTT broker (mosquitto 1.4.2) on port 36669:
- **Username:** `hisenseservice`
- **Password:** `multimqttservice`
- **Port:** 36669
- **SSL:** Optional (some models require it, others don't)

### Command Flow

```
TapCommand → MQTT Connection → Hisense TV (port 36669) → Command Execution
```

For power-on:
```
TapCommand → WOL Magic Packet → TV Wake → MQTT Connection → Power Command
```

---

## Supported Commands

### Power
- `power` - Toggle power on/off
- `power_on` - Turn on (uses WOL if MAC configured)
- `power_off` - Turn off

### Volume
- `volume_up` - Increase volume
- `volume_down` - Decrease volume
- `mute` - Toggle mute

### Channels
- `channel_up` - Next channel
- `channel_down` - Previous channel

### Navigation
- `up`, `down`, `left`, `right` - D-pad navigation
- `ok`, `enter`, `select` - Confirm selection
- `menu` - Open menu
- `home` - Home screen
- `back`, `return` - Go back
- `exit` - Exit current screen

### Playback
- `play` - Play
- `pause` - Pause
- `stop` - Stop
- `fast_forward` - Fast forward
- `rewind` - Rewind
- `subtitle` - Toggle subtitles

### Numbers
- `0` through `9` - Number keys

### Sources (Direct Input Selection)
- `source_0` through `source_7` - Switch to specific input

---

## Implementation Files

### Executor
**File:** `backend/app/commands/executors/network/hisense.py`

```python
class HisenseExecutor(CommandExecutor):
    """Executor for Hisense TVs (VIDAA OS)"""

    async def execute(self, command: Command) -> ExecutionResult:
        # Connects via MQTT and sends commands
        # Supports Wake-on-LAN for power-on
        # Auto-retries with SSL if initial connection fails
```

**Features:**
- Automatic SSL fallback if needed
- Wake-on-LAN integration for power-on
- Command mapping from standard names to Hisense KEY codes
- Error handling with helpful troubleshooting messages

### Router Integration
**File:** `backend/app/commands/router.py`

```python
# Hisense VIDAA
elif command.protocol == "hisense_vidaa":
    return HisenseExecutor(self.db)
```

### Discovery
**File:** `backend/app/services/device_scanner_config.py`

```python
"hisense_vidaa": DeviceTypeConfig(
    device_type="hisense_vidaa",
    display_name="Hisense TV (VIDAA)",
    mac_vendor_patterns=["hisense"],
    port_scans=[
        PortScanRule(port=36669, protocol="tcp", description="Hisense Remote Control"),
        PortScanRule(port=3000, protocol="tcp", description="Hisense API"),
    ],
)
```

**File:** `backend/app/routers/network_tv.py` (lines 62-64)

```python
elif device.device_type_guess == "hisense_vidaa":
    protocol = "hisense_vidaa"
    port = 36669
```

---

## Setup & Testing

### 1. Install Dependencies

```bash
cd /home/coastal/tapcommand/backend
source ../venv/bin/activate
pip install hisensetv wakeonlan
```

Or install from requirements.txt:
```bash
pip install -r requirements.txt
```

### 2. Find Your Hisense TV

The network discovery system will automatically detect Hisense TVs:
- Scans port 36669 (MQTT)
- Matches MAC vendor "Hisense"
- Assigns device type `hisense_vidaa`

### 3. Test Connection

**File:** `backend/test_hisense.py`

```bash
cd /home/coastal/tapcommand/backend
source ../venv/bin/activate

# Edit test_hisense.py and set:
# TV_IP = "192.168.101.XX"
# TV_MAC = "XX:XX:XX:XX:XX:XX"

python test_hisense.py
```

**Test Script Features:**
- Connection test (with/without SSL)
- Command test (volume up/down)
- Wake-on-LAN test
- TV information query (sources, volume)
- Comprehensive error troubleshooting

### 4. Adopt as Virtual Controller

Once discovered:
1. TV appears in network scan results
2. Protocol: `hisense_vidaa`
3. Adopt as Virtual Controller via API
4. Commands are routed through `HisenseExecutor`

---

## Configuration

### TV Settings

**Enable Network Control:**
Most Hisense TVs have network control enabled by default.

**Check Network Settings:**
- Go to TV Settings → Network
- Note the IP address (assign static IP recommended)
- Find MAC address (for WOL)

**Wake-on-LAN (Optional):**
- Settings → Network → Wake on LAN
- Enable for power-on capability
- Note: WOL reliability varies by model

### Database Schema

```sql
-- Virtual Device
INSERT INTO virtual_devices (
    device_name,
    mac_address,
    ip_address,
    device_type,
    device_subtype,
    protocol
) VALUES (
    'Living Room Hisense TV',
    'AA:BB:CC:DD:EE:FF',
    '192.168.101.100',
    'network_tv',
    'hisense_vidaa',
    'hisense_vidaa'
);

-- Virtual Controller
INSERT INTO virtual_controllers (
    controller_id,
    device_id,
    controller_name,
    protocol
) VALUES (
    'nw-eeff00',  -- From MAC last 6 chars
    (SELECT id FROM virtual_devices WHERE ip_address='192.168.101.100'),
    'Living Room Hisense TV',
    'hisense_vidaa'
);
```

---

## Power-On Behavior

### Wake-on-LAN (Recommended)

When MAC address is configured:
1. TapCommand sends 16 WOL magic packets
2. TV wakes from deep sleep (5-15 seconds)
3. Success response returned immediately
4. User waits for TV to fully boot

**Requirements:**
- MAC address stored in database
- WOL enabled in TV settings
- TV on same subnet

**Limitations:**
- Hisense WOL reliability varies by model
- Some models don't support WOL at all
- TV must be in standby, not fully unplugged

### Without WOL

If MAC address not configured:
- `power_on` command attempts MQTT power toggle
- Only works if TV is in light sleep (network active)
- If TV is in deep sleep, command fails

**Recommendation:** Always use WOL or IR for power-on

---

## Error Handling

### Connection Errors

**SSL Errors:**
- Executor automatically retries with SSL enabled
- Some models require `ssl_context=None`
- Others require SSL with certificate verification disabled

**Timeout:**
```
Possible causes:
1. TV is in deep sleep (network unpowered)
2. IP address incorrect
3. Port 36669 blocked by firewall
4. TV on different network
```

**Authorization Required:**
```
Some models require:
1. Accept prompt on TV screen
2. Pairing via RemoteNow mobile app first
3. One-time authorization code
```

**Connection Refused:**
```
Causes:
1. MQTT service disabled (rare)
2. TV in deep sleep
3. Firewall blocking connection
```

---

## Known Limitations

### Wake-on-LAN
- ⚠️ **Unreliable on some models** - WOL support varies
- ⚠️ **Deep sleep issue** - When TV is fully off, MQTT broker stops
- ✅ **Workaround:** Use IR control for power-on fallback

### SSL Requirements
- Some models require SSL, others fail with SSL
- Executor handles this automatically with retry logic

### First Connection
- Some models show authorization prompt on TV
- May require accepting connection on TV screen
- One-time setup per control device

### Repository Status
- ⚠️ `hisensetv` library is **no longer maintained** (as of 2024)
- ✅ Still functional and widely used
- ✅ Stable API, unlikely to break

---

## Troubleshooting

### TV Won't Wake with WOL

**Test WOL manually:**
```bash
wakeonlan AA:BB:CC:DD:EE:FF
```

**Check:**
- ✓ WOL enabled in TV settings
- ✓ TV in standby (not unplugged)
- ✓ Same subnet as server
- ✓ MAC address correct

**Solution:** Use IR control for power-on

### Commands Don't Work

**Verify TV is ON:**
- MQTT only works when TV network is active
- Deep sleep = no network = no MQTT

**Test with CLI:**
```bash
hisensetv 192.168.101.100 --key volume_up
```

**Check firewall:**
```bash
nc -zv 192.168.101.100 36669
```

### Authorization Required

Some models require first-time pairing:
1. Watch TV screen when connecting
2. Accept authorization prompt
3. Or use RemoteNow app to pair first
4. After pairing, TapCommand connections work

---

## Comparison: Hisense vs Samsung

| Feature | Hisense VIDAA | Samsung Legacy |
|---------|---------------|----------------|
| **Port** | 36669 (MQTT) | 55000 (TCP) |
| **Authentication** | Default creds | None |
| **Power-On** | WOL (unreliable) | ✗ Not supported |
| **When TV Off** | Deep sleep (MQTT stops) | Network powered down |
| **State Query** | ✅ Volume, sources | ✗ No feedback |
| **SSL** | Sometimes required | Not applicable |
| **Reliability** | Good (when ON) | Excellent (when ON) |
| **Recommendation** | WOL + IR fallback | IR for power-on |

---

## API Usage Examples

### Send Command via Virtual Controller

```bash
POST /api/commands
{
  "controller_id": "nw-eeff00",
  "command": "volume_up",
  "device_type": "network_tv",
  "protocol": "hisense_vidaa"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Hisense command 'volume_up' sent successfully",
  "data": {
    "execution_time_ms": 245,
    "device": "Living Room Hisense TV",
    "ip": "192.168.101.100",
    "key": "KEY_VOLUMEUP",
    "protocol": "mqtt"
  }
}
```

### Power On via WOL

```bash
POST /api/commands
{
  "controller_id": "nw-eeff00",
  "command": "power_on",
  "device_type": "network_tv",
  "protocol": "hisense_vidaa"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Wake-on-LAN packets sent to Living Room Hisense TV",
  "data": {
    "execution_time_ms": 125,
    "device": "Living Room Hisense TV",
    "ip": "192.168.101.100",
    "mac_address": "AA:BB:CC:DD:EE:FF",
    "method": "wake_on_lan",
    "packets_sent": 16,
    "note": "Hisense WOL may be unreliable. TV may take 5-15 seconds to boot."
  }
}
```

---

## Advanced Features

### Query TV State

The executor supports querying TV information:

```python
from hisensetv import HisenseTv

tv = HisenseTv(hostname="192.168.101.100")
with tv:
    # Get current volume
    volume = tv.get_volume()
    # {'volume_type': 0, 'volume_value': 25}

    # Get available sources
    sources = tv.get_sources()
    # [{'sourceid': '1', 'sourcename': 'TV', 'is_signal': '1'}, ...]
```

### App Launching

Hisense executor supports launching apps via MQTT:

```python
tv.send_key_netflix()   # Launch Netflix
tv.send_key_youtube()   # Launch YouTube
tv.send_key_amazon()    # Launch Prime Video
```

**Note:** Currently not exposed via API, but can be added as custom commands.

---

## Production Recommendations

### For Reliable Power-On

**Option 1: Hybrid IR + Network** ⭐ Recommended
- Power-on: IR control (guaranteed)
- All other commands: Network (faster, status feedback)

**Option 2: WOL + IR Fallback**
- Try WOL first
- If fails after 15 seconds, use IR
- Best user experience when WOL works

**Option 3: Keep TV in Standby**
- Never fully power off
- Network remains active
- MQTT commands work instantly
- Higher power consumption

### Network Setup

**Static IP Assignment:**
- Reserve IP in DHCP or set static on TV
- Prevents IP changes breaking control

**Firewall Rules:**
- Allow port 36669 TCP
- Allow UDP 9 for WOL

**Network Topology:**
- Same subnet as TapCommand server
- Low latency for fast response

---

## Testing Checklist

Before production deployment:

- [ ] Discovery detects Hisense TV correctly
- [ ] Can connect via MQTT (with/without SSL)
- [ ] Volume up/down commands work
- [ ] Power command toggles TV
- [ ] Channel navigation works
- [ ] WOL wakes TV from standby (if enabled)
- [ ] Virtual Controller adoption successful
- [ ] Commands work via TapCommand API
- [ ] Error handling tested (TV off, wrong IP, etc.)
- [ ] Execution time < 500ms for commands

---

## Files Summary

| File | Purpose |
|------|---------|
| `app/commands/executors/network/hisense.py` | Main executor implementation |
| `app/commands/router.py` | Routes hisense_vidaa to HisenseExecutor |
| `app/commands/executors/network/__init__.py` | Exports HisenseExecutor |
| `app/services/device_scanner_config.py` | Discovery configuration |
| `app/routers/network_tv.py` | Protocol mapping |
| `test_hisense.py` | Test script for validation |
| `requirements.txt` | Dependency: hisensetv==0.3.0 |
| `HISENSE_TV_INTEGRATION.md` | This documentation |

---

## Next Steps

1. ✅ Test with actual Hisense TV (if available)
2. ✅ Verify WOL functionality with your specific model
3. ✅ Document model-specific quirks (SSL yes/no)
4. ✅ Consider IR fallback implementation for power-on
5. ✅ Add app launching as custom commands (optional)
6. ✅ Monitor executor performance in production

---

## References

- **Library:** https://github.com/newAM/hisensetv
- **PyPI:** https://pypi.org/project/hisensetv/
- **Documentation:** https://hisensetv.readthedocs.io/
- **MQTT Details:** https://github.com/Krazy998/mqtt-hisensetv
- **Home Assistant Integration:** https://github.com/sehaas/ha_hisense_tv

---

**Implementation Status:** ✅ Complete and ready for testing
**Last Updated:** October 6, 2025
**Maintainer:** TapCommand Backend Team
