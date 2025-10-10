# Network TV Setup Guide

Complete guide for setting up network-controlled TVs with TapCommand

**Supported Brands:** Samsung, Hisense, LG, Sony, Roku, Vizio, Philips

---

## Quick Start

1. **Enable network control** on your TV (see brand-specific sections below)
2. **Discover TV** using TapCommand network scan
3. **Complete authentication** (if required by your brand)
4. **Test commands** to verify functionality
5. **Adopt as Virtual Controller** in TapCommand

---

## Brand-Specific Setup Instructions

### Samsung Legacy TVs (D/E/F Series, 2011-2015)

**Port:** 55000 | **Auth:** None | **Setup Time:** 2 minutes

#### Enable Network Control
1. Press **MENU** on TV remote
2. Navigate to **Network** → **AllShare Settings**
3. Enable **AllShare** or **External Device Control**
4. (Some models): **System** → **Device Manager** → **Enable External Device Control**

#### Test Connection
```bash
cd /home/coastal/tapcommand/backend
source ../venv/bin/activate
python test_legacy_samsung.py
```

#### Notes
- ⚠️ Cannot power ON via network - use IR for power-on
- ✅ No pairing required
- ✅ Works immediately after enabling

**Full Guide:** [LEGACY_SAMSUNG_TV_SETUP.md](LEGACY_SAMSUNG_TV_SETUP.md)

---

### Hisense TVs (VIDAA OS)

**Port:** 36669 | **Auth:** Default credentials | **Setup Time:** 3 minutes

#### Enable Network Control
- Usually enabled by default on VIDAA OS
- Check: **Settings** → **Network** → ensure TV is connected

#### First Connection
1. Some models show authorization prompt on TV screen
2. Accept the connection when prompted
3. May require SSL (auto-detected)

#### Test Connection
```bash
cd /home/coastal/tapcommand/backend
source ../venv/bin/activate

# Edit test_hisense.py with your TV's IP
python test_hisense.py
```

#### Wake-on-LAN Setup (Optional)
1. **Settings** → **Network** → **Wake on LAN**
2. Enable if available (not all models support)
3. Configure MAC address in TapCommand

#### Notes
- ⚠️ WOL unreliable - use WOL + IR fallback for power-on
- ⚠️ Some models need SSL, others don't (auto-detected)
- ✅ Can query TV state (volume, sources)

**Full Guide:** [HISENSE_TV_INTEGRATION.md](HISENSE_TV_INTEGRATION.md)

---

### LG webOS TVs (2014+)

**Port:** 3000/3001 | **Auth:** Pairing key | **Setup Time:** 5 minutes

#### Enable Network Control
1. **Settings** → **General** → **LG Connect Apps**
2. Ensure TV is connected to network
3. Note: Network control usually enabled by default

#### Pairing Process
1. Run connection from TapCommand
2. **TV displays pairing code on screen** (6 digits)
3. Accept pairing on TV within 30 seconds
4. Pairing key is automatically stored
5. Future connections use stored key

#### Wake-on-LAN Setup
1. **Settings** → **General** → **Mobile TV On**
2. Enable "Turn on via WiFi" or "Turn on via Mobile"
3. Configure MAC address in TapCommand

#### Test Connection
```bash
# Use pylgtv CLI or TapCommand test
pip install pylgtv
lgtv 192.168.101.XX scan  # Discover
lgtv 192.168.101.XX auth  # Pair
```

#### Notes
- ✅ WOL usually works well
- ⚠️ Cannot power ON via network protocol (only OFF)
- ✅ Rich API with status feedback
- ⚠️ Pairing required (one-time)

---

### Sony Bravia TVs (2013+)

**Port:** 80 (or 50001/50002) | **Auth:** PSK or PIN | **Setup Time:** 4 minutes

#### Enable IP Control
1. **Settings** → **Network** → **IP Control**
2. Enable **Authentication**
3. Set **Pre-Shared Key (PSK)** - e.g., "0000" or "1234"
4. Write down the PSK

OR (some models):
1. **Settings** → **Network** → **Remote Start**
2. Enable **Remote Start**

#### Configure TapCommand
- Store PSK in TV credentials
- PSK sent with each command via `X-Auth-PSK` header

#### Wake-on-LAN (Optional)
- Support varies by model
- Enable in **Network** → **Remote Start** if available

#### Test Connection
```bash
# Test IRCC command manually
curl -X POST http://192.168.101.XX/sony/IRCC \
  -H "Content-Type: text/xml" \
  -H "X-Auth-PSK: 0000" \
  -H 'SOAPACTION: "urn:schemas-sony-com:service:IRCC:1#X_SendIRCC"' \
  -d '<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body><u:X_SendIRCC xmlns:u="urn:schemas-sony-com:service:IRCC:1"><IRCCCode>AAAAAQAAAAEAAAASAw==</IRCCCode></u:X_SendIRCC></s:Body></s:Envelope>'
```

#### Notes
- ✅ Uses IRCC (IR over IP) - very reliable
- ⚠️ PSK required (configured in TV)
- ⚠️ WOL varies by model
- ✅ No pairing prompt (PSK pre-configured)

---

### Roku TVs / Devices (All Models)

**Port:** 8060 | **Auth:** None | **Setup Time:** 1 minute

#### Enable ECP (External Control Protocol)
- **Already enabled by default** on all Roku devices
- No setup required!

#### Test Connection
```bash
# Get device info
curl http://192.168.101.XX:8060/query/device-info

# Send command (volume up)
curl -X POST http://192.168.101.XX:8060/keypress/VolumeUp
```

#### Notes
- ✅ **Best network TV for simplicity**
- ✅ No authentication required
- ✅ Can power ON via network (discrete PowerOn command)
- ✅ Immediate setup - works out of the box
- ✅ Fast and reliable

---

### Vizio SmartCast TVs (2016+)

**Port:** 7345 or 9000 | **Auth:** Auth token | **Setup Time:** 6 minutes

#### Pairing Required
Must pair to get auth token before control works.

#### Pairing Process
1. Install pyvizio: `pip install pyvizio`
2. Discover TV: `pyvizio --ip=0 discover`
3. Pair: `pyvizio --ip=192.168.101.XX pair`
4. TV displays 4-digit PIN code on screen
5. Enter PIN when prompted
6. **Save auth token** from output
7. Store token in TapCommand credentials

#### Test Connection
```bash
# After pairing, test command
pyvizio --ip=192.168.101.XX --auth=YOUR_TOKEN volume-up
```

#### Notes
- ⚠️ **Pairing required** before any control works
- ⚠️ Token invalidated by factory reset
- ⚠️ HTTPS with self-signed cert
- ⚠️ Power-on reliability varies
- ⚠️ Firmware 4.0+ uses port 7345, older uses 9000

---

### Philips Android TVs (2015+)

**Port:** 1926 (Android) or 1925 (older) | **Auth:** May require digest auth | **Setup Time:** 3-5 minutes

#### Enable JointSpace API
- Usually enabled by default on Android TVs
- Some models may require enabling in developer settings

#### Authentication (if required)
1. Some models require username/password (digest auth)
2. Check TV documentation for default credentials
3. May be configurable in TV settings

#### Port Detection
- **Android TVs:** Port 1926 (HTTPS)
- **Non-Android TVs:** Port 1925 (HTTP)
- TapCommand auto-detects correct port

#### Test Connection
```bash
# Try port 1926 (Android)
curl -k -X POST https://192.168.101.XX:1926/6/input/key \
  -H "Content-Type: application/json" \
  -d '{"key":"VolumeUp"}'

# If that fails, try port 1925 (older)
curl -X POST http://192.168.101.XX:1925/6/input/key \
  -H "Content-Type: application/json" \
  -d '{"key":"VolumeUp"}'
```

#### Notes
- ⚠️ Port and authentication vary by model
- ✅ JointSpace API v6
- ⚠️ Power-on varies by model
- ✅ Auto-detects port 1925 vs 1926

---

## Universal Setup Steps

### 1. Network Configuration

#### Assign Static IP
**Recommended:** Reserve IP in DHCP server

1. Find TV's MAC address
2. In router: assign static IP via DHCP reservation
3. Prevents IP changes that break control

**Alternative:** Configure static IP on TV
- **Settings** → **Network** → **IP Settings** → **Manual**
- Enter IP, subnet, gateway, DNS

#### Verify Connectivity
```bash
# Ping TV
ping 192.168.101.XX

# Check port open (example for port 3000)
nc -zv 192.168.101.XX 3000
```

### 2. Discovery in TapCommand

```bash
# Run network scan
GET /api/network-discovery/scan

# Check results
GET /api/network-discovery/devices
```

TVs should appear with:
- Device type (e.g., `lg_webos`, `hisense_vidaa`)
- IP address
- MAC address
- Open ports

### 3. Complete Authentication

Follow brand-specific instructions above.

### 4. Test Commands

Use brand-specific test scripts in `/backend/`:
- `test_legacy_samsung.py`
- `test_hisense.py`
- Or use library CLI tools

### 5. Adopt as Virtual Controller

```bash
POST /api/virtual-controllers/adopt
{
  "device_name": "Living Room TV",
  "ip_address": "192.168.101.50",
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "protocol": "hisense_vidaa",
  "device_type": "network_tv"
}
```

### 6. Verify in TapCommand

```bash
# Send test command
POST /api/commands
{
  "controller_id": "nw-XXXXXX",
  "command": "volume_up",
  "device_type": "network_tv",
  "protocol": "hisense_vidaa"
}
```

---

## Troubleshooting

### Connection Refused

**Symptoms:** `Connection refused` or `Port closed`

**Causes:**
- TV powered off or in deep sleep
- Network control not enabled
- Firewall blocking port

**Solutions:**
1. Power on TV with remote
2. Check TV settings (see brand-specific sections)
3. Verify firewall allows outbound connections
4. Test from command line

### Connection Timeout

**Symptoms:** `Connection timeout` or `No route to host`

**Causes:**
- Wrong IP address
- TV on different network/VLAN
- Network issues

**Solutions:**
1. Ping the TV: `ping 192.168.101.XX`
2. Check TV is on same subnet
3. Verify IP didn't change (use static IP)
4. Check network cable/WiFi connection

### Authentication Failed

**Brand-specific solutions:**

**LG webOS:** Accept pairing on TV screen (30 second window)
**Sony Bravia:** Configure PSK in TV settings, store in TapCommand
**Vizio:** Run pairing process with `pyvizio` CLI
**Philips:** Configure digest auth credentials
**Hisense:** May need to accept authorization on TV screen

### Slow Response

**Causes:**
- Network latency
- TV processing slow
- WiFi interference

**Solutions:**
- Use wired Ethernet instead of WiFi
- Check ping time: `ping 192.168.101.XX`
- Upgrade TV firmware if available
- Reduce network congestion

### Commands Don't Work

1. **Verify TV is ON** - Most TVs require power to respond
2. **Check authentication** - Ensure pairing/PSK is correct
3. **Test with CLI tools** - Isolate issue to TapCommand vs TV
4. **Review TV logs** - Check for error messages
5. **Factory reset TV** (last resort) - Re-pair after reset

---

## Power-On Strategies

### Strategy 1: IR-Only Power-On (Most Reliable)
```
Power ON:  IR Control
Power OFF: Network Control
Other:     Network Control
```

**Pros:** Always works
**Cons:** Requires IR blaster line-of-sight

### Strategy 2: WOL + IR Fallback
```
Power ON:  Try WOL → wait 15s → if fail, use IR
Power OFF: Network Control
Other:     Network Control
```

**Pros:** Best user experience when WOL works
**Cons:** More complex logic

### Strategy 3: Network-Only (Roku)
```
Power ON:  Network (PowerOn command)
Power OFF: Network (PowerOff command)
Other:     Network Control
```

**Pros:** Simplest, fastest
**Cons:** Only works for Roku

### Strategy 4: Keep TV in Standby
```
Never fully power off TV, use standby mode
All commands via network
```

**Pros:** Network always responsive
**Cons:** Higher power consumption

---

## Network Ports Reference

| Brand | Port(s) | Protocol | SSL |
|-------|---------|----------|-----|
| Samsung Legacy | 55000 | TCP | No |
| Hisense | 36669 | TCP | Optional |
| LG webOS | 3000, 3001 | TCP/WebSocket | Optional (3001) |
| Sony Bravia | 80, 50001, 50002, 20060 | TCP/HTTP | Varies |
| Roku | 8060 | TCP/HTTP | No |
| Vizio | 7345, 9000 | TCP/HTTPS | Yes |
| Philips | 1925, 1926 | TCP/HTTP(S) | 1926 only |

**WOL (all brands):** UDP port 9

---

## Best Practices

### Network Setup
- ✅ Use static IP or DHCP reservation
- ✅ Same subnet as TapCommand server
- ✅ Low latency (< 10ms ping)
- ✅ Wired Ethernet preferred over WiFi
- ✅ Document TV IP/MAC in spreadsheet

### Security
- ✅ Store auth tokens/PSKs encrypted
- ✅ Limit network access to TapCommand server
- ✅ Use VLAN segmentation in production
- ✅ Regular credential rotation (if supported)

### Reliability
- ✅ Test all commands before deployment
- ✅ Implement retry logic (3 attempts)
- ✅ Monitor command success rate
- ✅ Have IR fallback ready
- ✅ Keep TV firmware updated

### Monitoring
- ✅ Log all command executions
- ✅ Track response times
- ✅ Alert on failures > 10%
- ✅ Periodic health checks (ping + port check)

---

## Common Commands

All brands support these standard commands (mapped internally):

**Power:**
- `power` - Toggle
- `power_on` - Turn on (WOL/network)
- `power_off` - Turn off

**Volume:**
- `volume_up`
- `volume_down`
- `mute`

**Navigation:**
- `up`, `down`, `left`, `right`
- `ok` / `enter` / `select`
- `back` / `return`
- `home`
- `menu`

**Playback:**
- `play`, `pause`, `stop`
- `rewind`, `fast_forward`

**Numbers:**
- `0` through `9`

---

## Quick Reference: Which Brand Should I Use?

**Easiest Setup:** Roku (no auth, works immediately)
**Best Features:** LG webOS (rich API, pairing persists)
**Most Reliable Power-On:** Roku (network PowerOn)
**Best WOL Support:** LG webOS
**No Setup Required:** Samsung Legacy, Roku
**Requires Pairing:** LG webOS, Vizio, (sometimes Sony)

---

## Support

For brand-specific documentation:
- [Samsung Legacy](LEGACY_SAMSUNG_TV_SETUP.md)
- [Hisense](HISENSE_TV_INTEGRATION.md)
- [All Supported TVs](SUPPORTED_NETWORK_TVS.md)
- [API Documentation](../docs/API.md)

---

**Last Updated:** October 6, 2025
**Maintained by:** TapCommand Development Team
