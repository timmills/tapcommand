# Samsung TV Adoption: The Tricky Parts

## TL;DR - What Makes Samsung TVs Tricky

Samsung TVs are **not all the same**. There are **three completely different connection methods** depending on the model year, and the system must auto-detect which one to use:

1. **Legacy TVs (2011-2015)**: Port 55000, no authentication
2. **2016 TVs**: WebSocket on port 8001, no authentication
3. **Modern TVs (2017+)**: Secure WebSocket on port 8002, **requires token**

The **trickiest part** is the modern TV token authentication - you only get **one chance** to accept the permission dialog.

---

## The "One Chance" Problem 🎯

### What Happens

When adopting a modern Samsung TV (2017+):

1. SmartVenue connects via WebSocket
2. TV shows permission dialog: **"Allow SmartVenue to control this TV?"**
3. You have **30 seconds** to press "Allow"
4. If you press "Allow" → Token saved, adoption succeeds ✅
5. If you press "Deny" or timeout → Adoption fails ❌

### The Tricky Part

**If the TV's "Access Notification" setting is "First time only" (the default), and you deny or timeout, you're locked out permanently until you reset the TV's device list.**

The TV remembers your first response and won't show the dialog again. SmartVenue can't re-pair without user intervention on the TV itself.

### The Solution

**Before adopting a Samsung TV:**
1. Go to TV: **Settings → General → External Device Manager → Device Connection Manager**
2. Check **Device List** - if SmartVenue is listed as "Denied", delete it
3. Set **Access Notification** to **"First time only"**
4. Be ready to press "Allow" within 30 seconds when adopting

**If you get locked out:**
1. Go to TV's **Device Connection Manager → Device List**
2. Find **SmartVenue** and delete it
3. Try adoption again

---

## The Three Samsung TV Types

### Type 1: Legacy TVs (2011-2015)
- **Models**: D/E/F/H Series (pre-2016)
- **Port**: 55000 (TCP)
- **Authentication**: None
- **Encoding**: Base64
- **Library**: `samsungctl` (legacy protocol)
- **Adoption**: Immediate, no permission needed
- **Power-on**: Cannot use network (network interface off when TV off)
- **Tricky**: Must use IR or WOL for power-on

### Type 2: 2016 TVs (No TokenAuthSupport)
- **Models**: KU/KS Series (2016)
- **Port**: 8001 or 8002 (WebSocket)
- **Authentication**: None (WebSocket connects without token)
- **Detection**: Response event is `ms.channel.connect` (no token in response)
- **Library**: `samsungtvws`
- **Adoption**: Immediate, no permission needed
- **Power-on**: WOL (10-20 seconds)
- **Tricky**: Must detect that TokenAuthSupport is false

### Type 3: Modern TVs (2017+) with TokenAuthSupport
- **Models**: Q/QN/S/Frame Series (2017+)
- **Port**: 8002 (Secure WebSocket, `wss://`)
- **Authentication**: **Required** - token acquired during adoption
- **Detection**: Device info at `http://TV_IP:8001/api/v2/` has `"TokenAuthSupport": "true"`
- **Library**: `samsungtvws` with token
- **Adoption**: **Requires user to press "Allow" on TV within 30 seconds**
- **Power-on**: WOL (10-20 seconds)
- **Tricky**: **The "one chance" problem** + token must be saved and reused

---

## Token Authentication Deep Dive

### How It Works

1. **Detection Phase** (during discovery):
   ```bash
   curl http://192.168.101.52:8001/api/v2/
   ```
   Response contains:
   ```json
   {
     "device": {
       "TokenAuthSupport": "true",
       "model": "QA55Q7FAM",
       ...
     }
   }
   ```

2. **Adoption Phase** (when user clicks "Adopt"):
   ```python
   # Connect to secure WebSocket
   name = base64.b64encode('SmartVenue'.encode()).decode()
   url = f'wss://{ip}:8002/api/v2/channels/samsung.remote.control?name={name}'

   ws = websocket.create_connection(url, timeout=10, sslopt={"cert_reqs": ssl.CERT_NONE})

   # Wait for user to press "Allow" on TV
   response = ws.recv()  # Blocks until TV responds (max 30 seconds)
   data = json.loads(response)

   # Extract token
   token = data['data']['token']  # e.g., "14781540"
   ```

3. **Token Storage**:
   ```json
   {
     "auth_token": "14781540",
     "port": 8002,
     "method": "websocket"
   }
   ```
   Saved to `virtual_devices.connection_config` as JSON

4. **Command Execution** (using saved token):
   ```python
   from samsungtvws import SamsungTVWS

   tv = SamsungTVWS(
       host=device.ip_address,
       port=8002,
       token='14781540',  # From database
       name='SmartVenue'
   )

   tv.shortcuts().send_key('KEY_VOLUP')  # No permission prompt!
   ```

### What Goes Wrong

#### Problem 1: Token Not Saved
**Symptom**: TV asks for permission on every command

**Cause**: Token acquired but not saved to `connection_config`

**Fix**: Verify token is in database:
```sql
SELECT
    device_name,
    ip_address,
    json_extract(connection_config, '$.auth_token') as token
FROM virtual_devices
WHERE ip_address = '192.168.101.52';
```

#### Problem 2: Token Not Used
**Symptom**: TV asks for permission on every command (even though token is saved)

**Cause**: Command executor not passing token to `SamsungTVWS`

**Fix**: Ensure executor loads token from `connection_config` and passes it:
```python
connection_config = json.loads(device.connection_config)
auth_token = connection_config.get('auth_token')

tv = SamsungTVWS(
    host=device.ip_address,
    port=8002,
    token=auth_token,  # MUST pass token here
    name='SmartVenue'
)
```

#### Problem 3: New Token Requested Each Time
**Symptom**: TV shows permission dialog on every command

**Cause**: Not passing token parameter → library requests new token each time

**Fix**: Same as Problem 2 - must pass `token=` to `SamsungTVWS()`

#### Problem 4: "One Chance" Lockout
**Symptom**: Adoption fails, no permission dialog shown, even though it worked before

**Cause**: User denied or timed out on first attempt, TV remembers denial

**Fix**: Reset TV's device list (see "The One Chance Problem" above)

---

## Auto-Detection Logic

The adoption flow must detect which of the three types it's dealing with:

```python
async def _get_samsung_token(ip: str, db: Session):
    """
    Auto-detect Samsung TV type and acquire token if needed
    """
    # Step 1: Check if TV supports token authentication
    try:
        device_info_url = f"http://{ip}:8001/api/v2/"
        response = requests.get(device_info_url, timeout=3)
        device_info = response.json()
        token_required = device_info.get('device', {}).get('TokenAuthSupport') == 'true'
    except:
        # Port 8001 not responding → probably legacy TV
        return {
            "success": True,
            "token": None,
            "port": 55000,
            "method": "legacy",
            "protocol": "samsung_legacy"
        }

    # Step 2: Use appropriate port
    if token_required:
        port = 8002  # Secure WebSocket
        protocol_prefix = 'wss'
    else:
        port = 8001  # Non-secure WebSocket
        protocol_prefix = 'ws'

    # Step 3: Connect and wait for response
    name = base64.b64encode('SmartVenue'.encode()).decode()
    url = f'{protocol_prefix}://{ip}:{port}/api/v2/channels/samsung.remote.control?name={name}'

    ws = websocket.create_connection(
        url,
        timeout=10,
        sslopt={"cert_reqs": ssl.CERT_NONE} if protocol_prefix == 'wss' else None
    )

    response = ws.recv()
    data = json.loads(response)
    ws.close()

    # Step 4: Parse response
    if 'data' in data and 'token' in data['data']:
        # Modern TV with token (2017+)
        return {
            "success": True,
            "token": data['data']['token'],
            "port": port,
            "method": "websocket",
            "protocol": "samsung_websocket",
            "message": f"Token acquired: {data['data']['token']}"
        }
    elif 'event' in data and data['event'] == 'ms.channel.connect':
        # 2016 TV without token
        return {
            "success": True,
            "token": None,
            "port": port,
            "method": "websocket",
            "protocol": "samsung_websocket",
            "message": "WebSocket connected (no token required)"
        }
    else:
        # Unknown response
        return {
            "success": False,
            "message": f"Unexpected WebSocket response: {data}"
        }
```

---

## Power-On Challenges

### The Problem

**Samsung TVs turn off their network interface when powered off.** You can't send network commands to a TV that's off.

### The Solution: Wake-on-LAN (WOL)

Instead of using Samsung protocol for power-on, send WOL magic packets to the TV's MAC address:

```python
from wakeonlan import send_magic_packet

# Send multiple packets for reliability
for _ in range(16):
    send_magic_packet(device.mac_address)
```

**Important notes:**
- TV takes **10-20 seconds** to fully boot
- WOL works best on **wired (Ethernet)** connections
- Must enable "Power On with Mobile" or "Samsung Instant On" in TV settings
- Some models don't support WOL → use IR fallback for instant power-on

---

## Status Polling Challenges

### The Problem

When polling TV status, the system must use the **saved token** (if the TV requires one).

### The Solution

Device status checker reads token from database:

```python
async def _check_samsung_tizen_status(self, device: VirtualDevice):
    import json

    # Get saved token from connection_config
    connection_config = json.loads(device.connection_config) if device.connection_config else {}
    auth_token = connection_config.get('auth_token')
    port = connection_config.get('port', 8002)

    # Try REST API first (quick check)
    device_info_url = f"http://{device.ip_address}:8001/api/v2/"
    response = requests.get(device_info_url, timeout=2)

    if response.status_code == 200:
        result["is_online"] = True
        result["power_state"] = "on"
    else:
        # REST API failed, fall back to ping
        ping_result = await self._check_ping_only(device)
        result["is_online"] = ping_result["is_online"]
        result["power_state"] = "standby" if ping_result["is_online"] else "off"
```

**Key insight**: Don't use WebSocket for status checks - it's slower and requires token. Use REST API at `http://TV_IP:8001/api/v2/` for quick online check.

---

## User Experience Lessons

### What Users Need to Know

1. **"Watch the TV screen"** - The permission dialog is on the TV, not the computer
2. **"You have 30 seconds"** - Make this very clear in the UI
3. **"Press Allow, not Deny"** - Obvious, but worth stating
4. **"If you miss it, reset the TV's device list"** - Provide clear instructions

### UI Recommendations

**During adoption:**
```
⏳ Waiting for TV permission...

📺 LOOK AT YOUR TV SCREEN
A permission dialog should appear on the TV asking:
"Allow SmartVenue to control this TV?"

⏱️ Press "Allow" within 30 seconds

If you don't see the dialog, check your TV's settings:
Settings → General → External Device Manager → Device Connection Manager
```

**After successful adoption:**
```
✅ Samsung TV adopted successfully!

Token saved - you won't be asked for permission again.

Note: Power-on via network takes 10-20 seconds.
For instant power-on, consider linking an IR controller.
```

**After failed adoption:**
```
❌ Failed to acquire authentication token

Possible causes:
• You didn't press "Allow" within 30 seconds
• You pressed "Deny" on the TV
• TV's "Access Notification" is set to "Never"
• SmartVenue is in TV's denied devices list

To fix:
1. Go to TV: Settings → General → External Device Manager → Device Connection Manager
2. In Device List, find "SmartVenue" and delete it
3. Set "Access Notification" to "First time only"
4. Try adopting again (be ready to press Allow!)
```

---

## Debugging Tips

### Check TV Type
```bash
curl http://TV_IP:8001/api/v2/
```
Look for `"TokenAuthSupport": "true"` or `"false"`

### Check if Token Was Saved
```sql
SELECT
    controller_id,
    device_name,
    ip_address,
    protocol,
    connection_config
FROM virtual_devices
JOIN virtual_controllers ON virtual_devices.id = virtual_controllers.virtual_device_id
WHERE ip_address = 'TV_IP';
```

Expected `connection_config` for modern TV:
```json
{
  "ip": "192.168.101.52",
  "port": 8002,
  "protocol": "samsung_legacy",
  "vendor": "Samsung Electronics Co.,Ltd",
  "model": "QA55Q7FAM",
  "auth_token": "14781540",
  "method": "websocket"
}
```

### Test Token Manually
```python
from samsungtvws import SamsungTVWS

tv = SamsungTVWS(
    host='192.168.101.52',
    port=8002,
    token='14781540',  # Use saved token
    name='SmartVenue'
)

# Should work WITHOUT permission prompt
tv.shortcuts().volume_up()
```

### Check if TV is Reachable
```bash
# Check REST API
curl http://TV_IP:8001/api/v2/

# Check WebSocket ports
nc -zv TV_IP 8001
nc -zv TV_IP 8002

# Check legacy port
nc -zv TV_IP 55000
```

---

## Code Locations

### Backend

**Token acquisition**:
- `/home/coastal/smartvenue/backend/app/routers/network_tv.py` - `_get_samsung_token()` function

**Adoption flow**:
- `/home/coastal/smartvenue/backend/app/routers/network_tv.py` - `adopt_device()` endpoint

**Command execution**:
- `/home/coastal/smartvenue/backend/app/commands/executors/network/samsung_legacy.py` - `_execute_websocket()` method

**Status polling**:
- `/home/coastal/smartvenue/backend/app/services/device_status_checker.py` - `_check_samsung_tizen_status()` method

### Frontend

**Brand info cards**:
- `/home/coastal/smartvenue/frontend-v2/src/features/network-controllers/components/brand-info-cards.tsx`

**Network controllers page**:
- `/home/coastal/smartvenue/frontend-v2/src/features/network-controllers/pages/network-controllers-page.tsx`

---

## Summary

### What Makes Samsung TVs Tricky

1. **Three different protocols** - must auto-detect
2. **Token authentication** - only modern TVs (2017+)
3. **"One chance" problem** - 30-second window to accept
4. **Token must be saved AND used** - both storage and usage critical
5. **Network interface off when TV off** - must use WOL for power-on
6. **Status polling** - must use saved token or REST API
7. **User attention required** - can't auto-pair like Roku

### What Makes It Work

1. **Auto-detection** - check `TokenAuthSupport` at `http://TV_IP:8001/api/v2/`
2. **WebSocket with timeout** - wait up to 30 seconds for user to accept
3. **Token storage** - save to `connection_config` JSON field
4. **Token reuse** - pass `token=` parameter to `SamsungTVWS()`
5. **Clear UI** - tell user to watch TV screen, 30-second countdown
6. **Recovery instructions** - how to reset TV's device list
7. **WOL for power-on** - send multiple magic packets

### The Golden Rule

**Once you have the token, save it and use it on every connection. Never request a new token unless the old one stops working.**

---

## Real-World Example

**Adopted TVs in current system:**

1. **Office Samsung TV** (192.168.101.52)
   - Model: QA55Q7FAM (2017 Q7 Series)
   - TokenAuthSupport: true
   - Port: 8002
   - Token: 14781540
   - Status: ✅ Working perfectly, no permission prompts

2. **Samsung TV Legacy 46** (192.168.101.46)
   - TokenAuthSupport: true
   - Port: 8002
   - Token: 27564066
   - Status: ✅ Working perfectly

3. **Bedroom TV** (192.168.101.237)
   - Model: UA40KU6000 (2016 KU Series)
   - TokenAuthSupport: false
   - Port: 8001
   - Token: None (not needed)
   - Status: ✅ Working perfectly, no permission prompts

All three adopted successfully using the auto-detection logic. User only had to press "Allow" once for TVs #1 and #2. TV #3 connected immediately without permission.

---

**Document created**: 2025-10-08
**Based on**: Real-world adoption of 3 Samsung TVs with different protocols
**Status**: All tricky parts documented and solved ✅
