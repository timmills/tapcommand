# Samsung TV Network Control Setup Guide

**Date:** October 4, 2025
**Network:** 192.168.101.x/24
**TVs Identified:** 3 Samsung TVs at .48, .50, .52

---

## Current Status

**Discovery Test Results:**
- ❌ 192.168.101.48 - Connection timeout
- ❌ 192.168.101.50 - Connection refused
- ❌ 192.168.101.52 - Connection timeout

**Network Connectivity:**
- ✅ Server on same subnet (192.168.101.153/24)
- ❌ TVs not responding to ping or port 8001

---

## Required TV Settings for Network Control

Samsung Smart TVs require specific settings to be enabled for network control to work:

### Step 1: Enable Network Remote Control on Each TV

**On the TV (using physical remote):**

1. Press **Home** button
2. Navigate to **Settings** (gear icon)
3. Go to **General** → **External Device Manager**
4. Enable **Device Connect Manager** (or **Smart Things**)
5. Go to **General** → **Network**
6. Select **Expert Settings** → **Power On with Mobile**
7. **Enable "Power On with Mobile"** ✅

**Alternative path (varies by model year):**
- Settings → General → Network → Expert Settings → Turn on with Mobile
- Settings → General → Network → Network Settings → Expert Settings → Network Remote Control

### Step 2: Check Network Settings

1. **Settings** → **General** → **Network** → **Network Status**
2. Verify IP address matches expected (.48/.50/.52)
3. Ensure WiFi/Ethernet is connected
4. Note the MAC address for each TV

### Step 3: Test Basic Connectivity

**From SmartVenue server:**
```bash
# Test if TV responds to ping (must be powered on)
ping 192.168.101.48

# Test if port 8001 is open
nc -zv 192.168.101.48 8001

# Query TV info via REST API
curl http://192.168.101.48:8001/api/v2/
```

**Expected response if working:**
```json
{
  "device": {
    "type": "Samsung SmartTV",
    "name": "[TV]Samsung TV",
    "model": "QN55Q80T",
    "version": "2.4.0",
    "wifiMac": "aa:bb:cc:dd:ee:ff"
  }
}
```

---

## Common Issues & Solutions

### Issue: "Connection Timeout"

**Possible Causes:**
- TV is powered off or in standby
- Network control not enabled in TV settings
- TV on different VLAN/network

**Solutions:**
1. Power on TV using physical remote
2. Enable "Power On with Mobile" setting (see Step 1 above)
3. Restart TV: **Settings → Support → Self Diagnosis → Reset Smart Hub**
4. Check if TV and server are on same network segment

### Issue: "Connection Refused" (Port Closed)

**Possible Causes:**
- Network remote control disabled
- Firewall blocking port 8001
- TV firmware too old (pre-2016 models)

**Solutions:**
1. Enable Device Connect Manager
2. Update TV firmware: **Settings → Support → Software Update → Update Now**
3. Factory reset if needed: **Settings → Support → Self Diagnosis → Reset**

### Issue: TV Off Network After Standby

**2024 Samsung Models:**
- **Settings → General → Power and Energy Saving**
- Disable "Power Saving Mode" (keeps network active in standby)
- Or enable "Network Standby" if available

**Older Models:**
- May drop network connection in standby
- Requires Wake-on-LAN or IR power-on first

---

## Discovery Script Usage

**Run discovery test:**
```bash
cd /home/coastal/smartvenue/backend
source ../venv/bin/activate
python test_samsung_discovery.py
```

**Expected output when working:**
```
Testing 192.168.101.48...
✓ REST API accessible
  Name: [TV]Samsung Q80T
  Model: QN55Q80TAFXZA
  Version: 2.4.0
  WiFi MAC: AA:BB:CC:DD:EE:FF
✓ WebSocket port 8001 accessible
```

---

## Pairing Process (Once TVs Respond)

### Step 1: Initiate Pairing

```bash
# Test pairing with first TV
cd /home/coastal/smartvenue/backend
source ../venv/bin/activate

# Create pairing script
python3 << 'EOF'
from samsungtvws import SamsungTVWS

tv = SamsungTVWS(
    host='192.168.101.48',
    port=8001,
    name='SmartVenue Control System',
    timeout=10
)

print("Connecting to TV...")
print("CHECK TV SCREEN: Accept pairing request within 30 seconds")

try:
    tv.open()
    print(f"✓ Pairing successful!")
    print(f"Token: {tv.token}")
    print("\nSave this token for database entry")
except Exception as e:
    print(f"✗ Pairing failed: {e}")
EOF
```

### Step 2: Accept on TV Screen

**What happens:**
1. Script initiates connection
2. TV displays pop-up: "Allow SmartVenue Control System to connect?"
3. Select **Allow** using TV remote (within 30 seconds)
4. Script returns authentication token

### Step 3: Save Token

```bash
# Token will be encrypted and stored in network_tv_credentials table
# Example token: 12345678-90AB-CDEF-1234-567890ABCDEF
```

---

## Testing Commands (After Pairing)

### Test Power Control

```python
from samsungtvws import SamsungTVWS

# Use saved token
tv = SamsungTVWS(
    host='192.168.101.48',
    port=8001,
    token='YOUR_TOKEN_HERE',  # From pairing step
    name='SmartVenue Control System'
)

# Send power command
tv.shortcuts().power()
print("Power command sent")

# Query power state
info = tv.rest_device_info()
power_state = info['device']['PowerState']
print(f"Power state: {power_state}")  # 'on' or 'standby'
```

### Test Volume Control

```python
tv.shortcuts().volume_up()  # Increase volume
tv.shortcuts().volume_down()  # Decrease volume
tv.shortcuts().mute()  # Toggle mute
```

### Test Input Selection

```python
tv.shortcuts().hdmi1()  # Switch to HDMI 1
tv.shortcuts().hdmi2()  # Switch to HDMI 2
```

---

## Network Topology Verification

**Current Setup:**
```
SmartVenue Hub: 192.168.101.153/24
Samsung TV #1:  192.168.101.48/24
Samsung TV #2:  192.168.101.50/24
Samsung TV #3:  192.168.101.52/24

Subnet: 192.168.101.0/24
Gateway: (check TV network settings)
```

**Required for Network Control:**
- ✅ Same subnet: Yes (192.168.101.x)
- ✅ Routing: Direct L2 communication
- ❓ Port 8001 open: Unknown (TVs not responding)
- ❓ Network control enabled: Unknown (need to check TV settings)

---

## Next Actions

### Immediate (Requires Physical Access to TVs)

1. **Power on each TV** using physical remote
2. **Navigate to Settings → General → External Device Manager**
3. **Enable Device Connect Manager and Network Remote Control**
4. **Verify network connection and IP addresses match**
5. **Re-run discovery script** to confirm TVs respond

### After TVs Respond

1. **Pair first TV** (192.168.101.48) using pairing script
2. **Test basic commands** (power, volume, input)
3. **Document token** securely
4. **Create virtual device** entry in SmartVenue database
5. **Assign port 1** with Samsung TV library
6. **Test via SmartVenue API** using existing command endpoint

### Long-term Integration

1. Implement auto-discovery endpoint
2. Add pairing wizard to frontend
3. Create network TV monitoring service
4. Migrate from IR to network control for these 3 TVs
5. Compare performance: network vs IR

---

## Troubleshooting Commands

```bash
# Check if TV is on network
ping -c 4 192.168.101.48

# Scan for open ports on TV
nmap -p 8001,8002 192.168.101.48

# Test REST API
curl -v http://192.168.101.48:8001/api/v2/

# Check ARP table (get MAC address)
arp -a | grep 192.168.101.48

# Test WebSocket connectivity
wscat -c ws://192.168.101.48:8001/api/v2/channels/samsung.remote.control
```

---

## Model-Specific Notes

### 2020-2024 Models (Tizen 5.5+)
- Port 8001: Unencrypted WebSocket
- Port 8002: Encrypted WebSocket (WSS) - preferred
- Low power network mode available
- Better status feedback

### 2016-2019 Models (Tizen 3.0-5.0)
- Port 8001 only
- May drop network in standby
- Basic remote control functionality
- Limited status queries

### Pre-2016 Models
- Network control may not be available
- Stick with IR control for these
- Check model number to confirm Tizen version

---

## Security Considerations

**Token Security:**
- Tokens are long-lived (don't expire automatically)
- Encrypt tokens before storing in database
- Use per-TV tokens (don't share across TVs)
- Store in `network_tv_credentials` table with Fernet encryption

**Network Isolation:**
- TVs on same network as control system
- Consider VLAN segmentation for production
- Firewall rules to restrict access to port 8001
- Monitor for unauthorized connection attempts

**Factory Reset Warning:**
- Factory reset invalidates all pairing tokens
- Must re-pair after TV reset
- Document recovery procedure

---

## Expected Timeline

**Phase 1: TV Configuration (1 hour)**
- Enable network control on all 3 TVs
- Verify connectivity
- Document MAC addresses and firmware versions

**Phase 2: Pairing (30 minutes)**
- Pair TV #1 as pilot
- Test basic commands
- Document token securely

**Phase 3: Database Integration (2 hours)**
- Create virtual device entry
- Add network credentials
- Assign library to port 1
- Test via SmartVenue API

**Phase 4: Rollout (1 hour)**
- Pair remaining 2 TVs
- Create virtual devices
- Update port assignments
- Verify all commands work

**Total:** ~4.5 hours for complete integration of 3 Samsung TVs

---

## Success Criteria

✅ All 3 TVs respond to discovery script
✅ Successful pairing with token exchange
✅ Power on/off via network confirmed
✅ Volume control works
✅ Input switching functional
✅ Status queries return accurate data
✅ Latency < 500ms for commands
✅ Success rate > 95% over 24 hours

---

**Status:** Waiting for TV configuration
**Next Step:** Enable network control in TV settings and re-run discovery
**Contact:** Test from TV network or enable network control features
