## Network TV Command Executors

Comprehensive guide to network TV control protocols and how to add new brands.

### Supported Brands & Protocols

| Brand | Protocol | Port | Authentication | Status | Library |
|-------|----------|------|----------------|--------|---------|
| **Samsung (Legacy)** | Base64 TCP | 55000 | None | ✅ Implemented | `samsungctl` |
| **Samsung (Modern)** | WebSocket | 8001/8002 | Token | 📝 Planned | `samsungtvws` |
| **LG webOS** | WebSocket | 3000 | Pairing Key | 📝 Planned | `pylgtv` |
| **Sony Bravia** | REST/IRCC | 20060 | Pre-shared Key | 📝 Planned | `braviarc` |
| **Roku** | ECP (HTTP) | 8060 | None | 📝 Planned | REST API |
| **Android TV** | ADB | 5555 | ADB Auth | 📝 Planned | `androidtv` |
| **Philips** | JointSpace API | 1925 | Digest Auth | 📝 Planned | REST API |
| **Vizio SmartCast** | Cast Protocol | 9000 | Auth Token | 📝 Planned | REST API |

### Samsung TVs

#### Legacy Protocol (Pre-2016 - D/E/F Series)

**Port:** 55000
**Authentication:** None
**Library:** `samsungctl`

```python
# Install
pip install samsungctl

# Configuration
config = {
    "name": "TapCommand",
    "host": "192.168.1.100",
    "port": 55000,
    "method": "legacy",
    "timeout": 3
}

# Send command
with samsungctl.Remote(config) as remote:
    remote.control("KEY_POWER")
```

**Command Format:** `KEY_<ACTION>` (e.g., KEY_POWER, KEY_VOLUP)

#### Modern Protocol (2016+ - Tizen OS)

**Port:** 8001 (HTTP), 8002 (HTTPS)
**Authentication:** Token-based
**Library:** `samsungtvws`

```python
# Install
pip install samsungtvws

# First time pairing
from samsungtvws import SamsungTVWS
tv = SamsungTVWS("192.168.1.100")
token = tv.get_token()  # User accepts on TV

# Send command
tv.send_key("KEY_POWER", token)
```

**Notes:**
- Requires user to accept pairing on TV screen
- Token must be stored for future use
- Supports additional features (apps, running apps list)

### LG TVs (webOS)

**Port:** 3000
**Authentication:** Pairing key
**Library:** `pylgtv`

```python
# Install
pip install pylgtv

# First time pairing
from pylgtv import WebOsClient
client = WebOsClient("192.168.1.100")
client.connect()  # Generates pairing key on TV

# Store pairing key, then:
client = WebOsClient("192.168.1.100", key="PAIRING_KEY")
client.connect()

# Send command
client.volume_up()
client.set_channel(63)
```

**Command Methods:**
- `volume_up()`, `volume_down()`, `mute()`
- `channel_up()`, `channel_down()`, `set_channel(n)`
- `play()`, `pause()`, `stop()`
- `turn_off()`

### Sony Bravia TVs

**Port:** 20060
**Authentication:** Pre-shared Key
**Library:** `braviarc`

```python
# Install
pip install braviarc

# Setup (get PSK from TV settings)
from braviarc import BraviaRC
tv = BraviaRC("192.168.1.100", psk="0000")  # Default PSK

# Send command
tv.send_req_ircc("AAAAAQAAAAEAAAAVAw==")  # Power

# Or use convenience methods
tv.volume_up()
tv.set_channel(63)
```

**Notes:**
- PSK must be configured on TV (Settings → Network → IP Control)
- Commands are base64-encoded IRCC codes
- Library provides convenience methods for common commands

### Roku Devices

**Port:** 8060
**Authentication:** None
**Protocol:** ECP (External Control Protocol) - REST API

```python
# No library needed - pure HTTP
import requests

base_url = "http://192.168.1.100:8060"

# Send key press
requests.post(f"{base_url}/keypress/Power")
requests.post(f"{base_url}/keypress/VolumeUp")

# Launch app
requests.post(f"{base_url}/launch/12")  # Netflix

# Query active app
response = requests.get(f"{base_url}/query/active-app")
```

**Key Codes:**
- `Power`, `PowerOn`, `PowerOff`
- `VolumeUp`, `VolumeDown`, `VolumeMute`
- `Home`, `Back`, `Select`
- `Up`, `Down`, `Left`, `Right`
- `Play`, `Pause`, `Rev`, `Fwd`

### Android TV

**Port:** 5555
**Authentication:** ADB authorization
**Library:** `androidtv`

```python
# Install
pip install androidtv

# Setup ADB connection
from androidtv import AndroidTV
tv = AndroidTV("192.168.1.100", adb_server_ip="127.0.0.1")
tv.connect()  # May require pairing on TV

# Send command
tv.power()
tv.volume_up()
tv.media_play()
tv.home()
```

**Notes:**
- Requires ADB server running
- First connection needs authorization on TV
- Very powerful - can launch apps, check state, etc.

### Philips TVs (JointSpace API)

**Port:** 1925
**Authentication:** Digest authentication
**Protocol:** REST API

```python
# No dedicated library - use requests
import requests
from requests.auth import HTTPDigestAuth

base_url = "http://192.168.1.100:1925/1"
auth = HTTPDigestAuth("username", "password")

# Send key
data = {"key": "Power"}
requests.post(f"{base_url}/input/key", json=data, auth=auth)

# Volume
data = {"current": 20}  # Volume 20
requests.post(f"{base_url}/audio/volume", json=data, auth=auth)
```

### Vizio SmartCast

**Port:** 9000
**Authentication:** Auth token
**Protocol:** Cast protocol (REST-like)

```python
# Install
pip install pyvizio

# Pairing required
from pyvizio import Vizio
tv = Vizio("192.168.1.100", "device_name", auth_token="TOKEN")

# Send command
tv.pow_on()
tv.vol_up()
tv.ch_up()
```

---

## Adding a New Brand

### Step 1: Research the Protocol

Find documentation for:
1. **Control port** - What port does the TV listen on?
2. **Protocol type** - REST API, WebSocket, TCP, etc.
3. **Authentication** - None, token, pairing key, PSK?
4. **Command format** - How are commands structured?
5. **Python library** - Is there an existing library?

### Step 2: Create the Executor

Create a new file in `app/commands/executors/network/`:

```python
# app/commands/executors/network/brand_name.py

import time
from ..base import CommandExecutor
from ...models import Command, ExecutionResult
from ....models.virtual_controller import VirtualDevice

class BrandNameExecutor(CommandExecutor):
    """Executor for Brand Name TVs"""

    KEY_MAP = {
        "power": "BRAND_POWER_CODE",
        "volume_up": "BRAND_VOL_UP_CODE",
        # ... map all commands
    }

    def can_execute(self, command: Command) -> bool:
        return (
            command.device_type == "network_tv" and
            command.protocol == "brand_protocol_name"
        )

    async def execute(self, command: Command) -> ExecutionResult:
        start_time = time.time()

        try:
            # Get device info
            device = self._get_device(command.controller_id)

            # Send command using brand's library/protocol
            # ... your implementation here

            return ExecutionResult(
                success=True,
                message=f"Command sent successfully",
                data={"execution_time_ms": ...}
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Command failed: {str(e)}",
                error=str(e)
            )

    def _get_device(self, controller_id: str):
        from ....models.virtual_controller import VirtualController
        return self.db.query(VirtualDevice).join(
            VirtualController
        ).filter(
            VirtualController.controller_id == controller_id
        ).first()
```

### Step 3: Register in Router

Add to `app/commands/router.py`:

```python
from .executors.network.brand_name import BrandNameExecutor

# In get_executor() function:
elif command.protocol == "brand_protocol_name":
    return BrandNameExecutor(db)
```

### Step 4: Update Discovery

Add to `app/routers/network_tv.py` discovery logic:

```python
# In identify_device_type()
if vendor == "Brand Name":
    if port_open(ip, BRAND_CONTROL_PORT):
        return {
            "device_type": "brand_tv",
            "protocol": "brand_protocol_name",
            "port": BRAND_CONTROL_PORT
        }
```

### Step 5: Test

1. Discover the TV
2. Adopt it as Virtual Controller
3. Send test commands through unified API
4. Verify commands execute correctly

---

## Command Mapping Best Practices

### Standard Command Names

Use these standard command names for consistency:

**Power:**
- `power` - Toggle
- `power_on` - Turn on
- `power_off` - Turn off

**Volume:**
- `volume_up`
- `volume_down`
- `mute`

**Channels:**
- `channel_up`
- `channel_down`
- `channel_direct` - Use with parameters: `{channel: "63"}`

**Navigation:**
- `up`, `down`, `left`, `right`
- `ok` / `select` / `enter`
- `back` / `return`
- `home`
- `menu`

**Transport:**
- `play`, `pause`, `stop`
- `rewind`, `fast_forward`
- `record`

**Sources:**
- `source` - Cycle sources
- `hdmi1`, `hdmi2`, `hdmi3`, `hdmi4`
- `tv`, `av`, `component`

**Digits:**
- `0` through `9`

### Brand-Specific Commands

If a brand has unique commands, prefix with brand name:
- `samsung_smart_hub`
- `lg_live_tv`
- `roku_star` (asterisk button)

---

## Error Handling

All executors should handle:

1. **Device Not Found** - Return `DEVICE_NOT_FOUND` error
2. **Connection Timeout** - Return `TIMEOUT` error
3. **Authentication Failed** - Return `AUTH_FAILED` error
4. **Command Not Supported** - Return `UNSUPPORTED_COMMAND` error
5. **General Errors** - Return exception message

Always include execution time in response data for monitoring.

---

## Testing Checklist

When adding a new brand:

- [ ] Discovery detects the TV correctly
- [ ] Adoption creates Virtual Controller
- [ ] Power commands work
- [ ] Volume commands work
- [ ] Channel commands work
- [ ] Navigation works
- [ ] Error handling tested (disconnect TV, wrong IP, etc.)
- [ ] Execution time logged
- [ ] Documentation updated

---

## Future Enhancements

### Planned Features

1. **State Monitoring**
   - Query TV power state
   - Get current channel
   - Get current volume
   - Get current input source

2. **Advanced Features**
   - Launch specific apps (Netflix, YouTube, etc.)
   - Text input for search
   - Screenshot capture
   - Get running apps list

3. **Bulk Operations**
   - Send command to multiple TVs
   - Zone-based control
   - Synchronized commands

4. **Smart Retry**
   - Auto-retry on failure
   - Exponential backoff
   - Dead letter queue

### Additional Brands to Add

- [ ] Hisense (VIDAA OS)
- [ ] TCL (Roku TV / Google TV)
- [ ] Panasonic
- [ ] Toshiba
- [ ] Sharp (Aquos Net+)
- [ ] Insignia (Fire TV Edition)
- [ ] Westinghouse

---

## Resources

### Libraries

- **Samsung (Legacy):** https://github.com/Ape/samsungctl
- **Samsung (Modern):** https://github.com/xchwarze/samsung-tv-ws-api
- **LG webOS:** https://github.com/klattimer/LGWebOSRemote
- **Sony Bravia:** https://github.com/aparraga/braviarc
- **Roku:** https://developer.roku.com/docs/developer-program/debugging/external-control-api.md
- **Android TV:** https://github.com/JeffLIrion/python-androidtv
- **Philips:** https://github.com/eslavnov/pylips

### Protocol Documentation

- **Samsung:** https://github.com/Sc0rpio/samsung-tv-control-doc
- **LG webOS:** http://webostv.developer.lge.com/
- **Sony:** https://pro-bravia.sony.net/develop/
- **Roku ECP:** https://developer.roku.com/docs/developer-program/debugging/external-control-api.md
