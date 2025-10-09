# Samsung TV Adoption Troubleshooting Guide

## Overview

This guide covers common issues and solutions when adopting Samsung Smart TVs into the SmartVenue system. Samsung TVs use different connection methods depending on the model year and firmware version.

---

## Samsung TV Connection Methods

SmartVenue automatically detects and uses the appropriate method:

### 1. **Modern TVs with TokenAuthSupport (2017+)**
- **Ports**: 8001 (WebSocket) or 8002 (Secure WebSocket)
- **Authentication**: Requires token
- **Example Models**: Q7 Series (2017), Q8/Q9 Series, Frame TVs, etc.
- **Detection**: Has `"TokenAuthSupport": "true"` in device info

### 2. **2016 TVs without TokenAuthSupport**
- **Ports**: 8001 or 8002 (WebSocket)
- **Authentication**: No token required
- **Example Models**: KU6000 Series (2016), J Series
- **Detection**: WebSocket connects with `ms.channel.connect` event but no token returned

### 3. **Legacy TVs (Pre-2016)**
- **Port**: 55000 (TCP with base64 encoding)
- **Authentication**: No token required (but may show one-time permission prompt)
- **Example Models**: D/E/F Series (2011-2015)
- **Detection**: Port 55000 open, ports 8001/8002 closed

---

## Common Adoption Issues

### Issue 1: "Failed to acquire authentication token"

**Symptoms:**
- Adoption fails with error: "WebSocket connected but no token received. Permission may have been denied on TV."
- TV might show a permission dialog that wasn't accepted in time

**Causes:**
1. Permission dialog timed out (30 second window)
2. User pressed "Deny" instead of "Allow"
3. TV's "Access Notification" setting is set to "Never"
4. SmartVenue is already in the TV's denied devices list

**Solution:**

#### Step 1: Check TV Access Settings
1. On TV, go to: **Settings → General → External Device Manager → Device Connection Manager**
2. Set **Access Notification** to **"First time only"** (NOT "Always" or "Never")
3. Check **Device List**:
   - If "SmartVenue" is listed as **Denied**, delete it
   - If it exists, remove it completely to allow fresh pairing

#### Step 2: Retry Adoption
1. Delete the failed adoption from SmartVenue UI
2. Click "Adopt" again
3. **Watch the TV screen** - a permission dialog will appear
4. **Press "Allow" within 30 seconds**
5. System will save the token automatically

#### Step 3: If Still Failing
- Ensure TV is powered ON and connected to network
- Verify TV firmware is up to date
- Try power cycling the TV
- Check if TV's network control features are enabled

---

### Issue 2: Permission Prompt Shows on Every Command

**Symptoms:**
- TV control works, but asks for permission every time
- Token is not being saved/reused

**Cause:**
Token was not properly saved during adoption, or TV settings require permission on every connection.

**Solution:**

#### Check Token Storage
Verify token was saved in database:
```sql
SELECT connection_config FROM virtual_devices WHERE ip_address = 'TV_IP';
```

Should contain:
```json
{
  "auth_token": "12345678",
  "port": 8002,
  "method": "websocket"
}
```

#### Fix TV Settings
1. Go to: **Settings → General → External Device Manager → Device Connection Manager**
2. Set **Access Notification** to **"First time only"**
3. In **Device List**, verify SmartVenue is marked as **Allowed**

#### Re-adopt if Necessary
If token is missing:
1. Delete the virtual controller
2. Unadopt the device
3. Adopt again with correct TV settings

---

### Issue 3: TV Won't Turn On via Network

**Symptoms:**
- Power OFF works
- Power ON command does nothing
- TV network interface is off when TV is in standby

**Cause:**
Samsung TVs turn off their network interface when powered off. Network commands cannot reach the TV.

**Solution:**

#### Use Wake-on-LAN (WOL)
SmartVenue automatically uses WOL for power-on:
1. Ensure TV has **Wake-on-LAN enabled** in network settings
2. Command executor detects `power_on` and automatically sends WOL magic packets
3. TV takes 10-20 seconds to fully boot

#### Enable WOL on TV
1. **Settings → General → Network → Expert Settings**
2. Enable **"Power On with Mobile"** or **"Samsung Instant On"**
3. Ensure TV is connected via Ethernet (WOL is more reliable on wired connections)

#### Alternative: Hybrid Control
If WOL doesn't work, use IR fallback:
1. Link an IR controller to the virtual device
2. Set power_on_method to `"hybrid"`
3. System will use IR for power-on, network for other commands

---

### Issue 4: "You Only Get One Chance"

**Symptoms:**
- First adoption attempt shows permission dialog
- User doesn't accept in time or presses Deny
- Subsequent adoption attempts fail without showing permission dialog
- TV seems to remember the denial

**Cause:**
When TV's "Access Notification" is set to "First time only", it remembers the first response (Allow or Deny). If denied or timed out, SmartVenue is permanently blocked until TV settings are reset.

**Solution:**

#### Reset TV's Device Memory
1. Go to: **Settings → General → External Device Manager → Device Connection Manager → Device List**
2. Find **SmartVenue** in the list
3. **Delete it** completely
4. Alternatively, select it and change status to "Allowed" if option is available

#### Clear All Pairings (Nuclear Option)
If above doesn't work:
1. Go to: **Settings → General → External Device Manager → Device Connection Manager**
2. Select **"Delete All"** or similar option to clear all device permissions
3. Re-adopt all devices that need access

#### Recommended Prevention
- Set "Access Notification" to **"First time only"** BEFORE attempting adoption
- Be ready to press "Allow" when adopting
- Don't let the 30-second timeout expire
- Don't press "Deny" unless you really mean it

---

### Issue 5: WebSocket Connects But No Control

**Symptoms:**
- Adoption succeeds
- WebSocket connects
- Commands are sent but nothing happens on TV

**Causes:**
1. Wrong port (8001 vs 8002)
2. Token not included in command requests
3. TV requires secure WebSocket (wss) but using non-secure (ws)

**Solution:**

#### Verify Connection Config
Check saved configuration:
```sql
SELECT protocol, connection_config FROM virtual_devices WHERE ip_address = 'TV_IP';
```

For TVs with TokenAuthSupport:
- Should use port **8002** (secure)
- Should have `auth_token` in config
- Protocol should be `samsung_websocket`

#### Test Manual Control
```python
from samsungtvws import SamsungTVWS

tv = SamsungTVWS(
    host='TV_IP',
    port=8002,
    token='SAVED_TOKEN',  # Use token from database
    name='SmartVenue'
)

tv.shortcuts().volume_up()
```

If this works but system doesn't, check command executor is using token correctly.

---

### Issue 6: Legacy Port 55000 Not Working

**Symptoms:**
- Older Samsung TV (pre-2016)
- Port 55000 detected but commands fail
- Connection refused errors

**Cause:**
Legacy protocol requires network remote control to be enabled in TV settings.

**Solution:**

#### Enable Legacy Network Control
1. **Settings → Network → Expert Settings**
2. Enable **"Power On with Mobile"** or **"Network Remote Control"**
3. Some models may require enabling under **System → Expert Settings**

#### Verify Port is Open
```bash
nc -zv TV_IP 55000
```

Should show: `Connection to TV_IP 55000 port [tcp/*] succeeded!`

#### Try Different Protocol
If port 55000 still doesn't work, TV might actually support WebSocket:
- Check if ports 8001/8002 are open
- Try manual WebSocket connection
- Re-detect connection method

---

## Adoption Best Practices

### Before Adoption

1. **TV Settings Checklist:**
   - ✅ TV is powered ON
   - ✅ TV connected to same network as SmartVenue
   - ✅ Network remote control enabled (varies by model)
   - ✅ Access Notification set to "First time only"
   - ✅ No existing SmartVenue entry in denied devices list

2. **SmartVenue Checklist:**
   - ✅ TV appears in discovery list
   - ✅ TV shows as "Ready to Adopt" (high confidence score)
   - ✅ No previous failed adoption attempts for this TV

### During Adoption

1. Click "Adopt" button in UI
2. **Immediately watch the TV screen**
3. Permission dialog should appear within 2-5 seconds
4. **Press "Allow" or "Always Allow"**
5. Wait for adoption to complete (5-10 seconds)

### After Adoption

1. **Test immediately:**
   - Send a volume command
   - Verify it works WITHOUT permission prompt

2. **If permission prompt appears again:**
   - Token wasn't saved properly
   - Delete and re-adopt with correct TV settings

3. **Test power control:**
   - Turn TV OFF (should work via network)
   - Turn TV ON (should work via WOL after 10-20 seconds)

---

## Token Management

### How Tokens Work

1. **During Adoption:**
   - System connects to TV via WebSocket
   - TV shows permission dialog
   - User accepts → TV returns unique token
   - Token saved to `virtual_devices.connection_config`

2. **During Control:**
   - Command executor reads token from database
   - Includes token in WebSocket URL: `wss://TV_IP:8002/...?token=TOKEN`
   - TV validates token
   - No permission prompt needed

3. **Token Lifetime:**
   - Tokens are permanent until TV settings reset
   - Stored in TV's memory per device name
   - Same token works until explicitly revoked

### Token Debugging

#### Check if Token Was Saved
```sql
SELECT
    device_name,
    ip_address,
    protocol,
    json_extract(connection_config, '$.auth_token') as token,
    json_extract(connection_config, '$.port') as port,
    json_extract(connection_config, '$.method') as method
FROM virtual_devices
WHERE ip_address = 'TV_IP';
```

#### Verify Token Still Works
```bash
curl http://TV_IP:8001/api/v2/
```

Check response for `TokenAuthSupport` field.

#### Manually Update Token
If you have a working token from another system (e.g., Home Assistant):
```sql
UPDATE virtual_devices
SET connection_config = json_set(
    connection_config,
    '$.auth_token',
    'YOUR_TOKEN_HERE'
)
WHERE ip_address = 'TV_IP';
```

---

## Error Messages Reference

### "Failed to acquire authentication token"
- **Cause**: WebSocket connected but TV didn't return token
- **Fix**: Check TV permission settings, ensure you pressed "Allow"

### "No auth token configured"
- **Cause**: Token missing from database
- **Fix**: Re-adopt device

### "Connection refused"
- **Cause**: TV port is closed or TV is off
- **Fix**: Enable network control in TV settings, ensure TV is on

### "Connection timed out"
- **Cause**: TV not responding on network
- **Fix**: Check network connectivity, verify TV IP address

### "Invalid close opcode 1005"
- **Cause**: TV closing connection (usually permission denied)
- **Fix**: Check TV device list, remove denied entries

---

## Model-Specific Notes

### Q7/Q8/Q9 Series (2017-2020)
- Always require tokens
- Use port 8002 (secure WebSocket)
- Very reliable with proper token

### KU6000/KU7000 Series (2016)
- WebSocket but no token required
- Use port 8001 or 8002
- Connect without authentication

### Smart TV D/E/F Series (2011-2015)
- Legacy protocol on port 55000
- May show one-time permission on first connect
- No token mechanism

### Frame TV
- Same as modern TVs (requires token)
- Has additional art mode features
- Port 8002 recommended

---

## Developer Notes

### Connection Detection Flow

```python
async def _get_samsung_token(ip: str):
    # 1. Check device info for TokenAuthSupport
    device_info = requests.get(f"http://{ip}:8001/api/v2/")
    token_required = device_info['device'].get('TokenAuthSupport') == 'true'

    # 2. Try WebSocket connection
    if token_required:
        port = 8002  # Secure
        protocol = 'wss'
    else:
        port = 8001  # Non-secure
        protocol = 'ws'

    # 3. Connect and wait for response
    ws = websocket.create_connection(f'{protocol}://{ip}:{port}/...')
    response = json.loads(ws.recv())

    # 4. Parse response
    if 'data' in response and 'token' in response['data']:
        # Modern TV with token
        return response['data']['token']
    elif response['event'] == 'ms.channel.connect':
        # 2016 TV without token
        return None

    # 5. Fallback to legacy if WebSocket fails
    if port_55000_open(ip):
        return "legacy_protocol"
```

### Token Storage Schema

```json
{
  "ip": "192.168.101.52",
  "port": 8002,
  "protocol": "samsung_legacy",  // From discovery
  "vendor": "Samsung Electronics Co.,Ltd",
  "model": "QA55Q7FAM",
  "auth_token": "14781540",     // Acquired during adoption
  "method": "websocket"          // Detected method
}
```

### Command Execution

```python
def execute_websocket_command(device, command):
    config = json.loads(device.connection_config)

    tv = SamsungTVWS(
        host=device.ip_address,
        port=config['port'],
        token=config.get('auth_token'),  # May be None for 2016 TVs
        name='SmartVenue'
    )

    tv.shortcuts().send_key(command)
```

---

## Support Matrix

| TV Series | Years | Port | Token Required | Notes |
|-----------|-------|------|----------------|-------|
| Q/QN/S Series | 2017+ | 8002 | ✅ Yes | Most reliable, full features |
| KU/KS Series | 2016 | 8001/8002 | ❌ No | WebSocket without token |
| JU/JS Series | 2015 | 8001 or 55000 | ❌ No | Transitional, try both |
| HU/H Series | 2014 | 55000 | ❌ No | Legacy only |
| F Series | 2013 | 55000 | ❌ No | Legacy only |
| E/ES Series | 2012 | 55000 | ❌ No | Legacy only |
| D Series | 2011 | 55000 | ❌ No | Legacy only |

---

## Quick Reference

### Adoption Failed?
1. Check TV is ON and on network
2. Verify "Access Notification" = "First time only"
3. Remove SmartVenue from TV's denied list
4. Try again and press "Allow" within 30 seconds

### Commands Not Working?
1. Check token is saved in database
2. Verify correct port (8001 vs 8002)
3. Test with manual WebSocket connection
4. Check TV network control is still enabled

### Can't Power On?
1. Enable "Power On with Mobile" in TV settings
2. Use Wake-on-LAN (10-20 second delay)
3. Consider IR fallback for instant power-on

### Locked Out After Denial?
1. Go to TV Device Connection Manager
2. Delete SmartVenue from device list
3. Ensure "First time only" is set
4. Adopt fresh

---

## Conclusion

Samsung TV adoption is reliable once you understand the three connection types and permission system. The key is:

1. **Correct TV settings** before adoption
2. **Prompt attention** during the 30-second permission window
3. **Token saved** in database for reuse
4. **Wake-on-LAN** for power-on when TV is off

With these in place, Samsung TVs provide excellent network control with minimal latency and no permission prompts after initial setup.
