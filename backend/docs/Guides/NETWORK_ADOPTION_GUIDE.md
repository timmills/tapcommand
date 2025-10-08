# Network Device Adoption Guide

**Date:** October 4, 2025
**Status:** Implementation Guide

---

## Overview

This guide explains how to discover and adopt network-controllable TVs and displays into SmartVenue, creating "virtual IR controllers" that communicate over IP instead of infrared.

---

## Why Network Control?

### Benefits Over IR
- ⚡ **5-10x faster:** 50-100ms vs 500ms response time
- 🎯 **More reliable:** 99.9% vs 90-95% success rate
- 📡 **No line-of-sight:** Works through walls and obstacles
- 🔄 **Bidirectional:** Can query device status (power, volume, input)
- 💰 **Cost effective:** No IR blaster hardware needed ($0 vs $25 per TV)
- ⏱️ **Faster setup:** 2-5 minutes vs 30 minutes per TV

### Use Cases
1. **Retrofit existing venues** with Samsung/LG/Sony TVs
2. **New installations** where network is preferred
3. **Remote locations** where IR blaster placement is difficult
4. **High-reliability scenarios** where IR failures are unacceptable

---

## Supported Brands

### ✅ Currently Working
- **Samsung Legacy TVs (2011-2015):** D/E/F/H/J series via port 55000
  - 920 MAC prefixes identified
  - On-screen pairing required
  - No token storage needed
  - Example: LA40D550 @ 192.168.101.50

### 🔄 In Progress
- **Samsung Modern TVs (2016+):** Tizen via WebSocket port 8001
  - Token-based authentication
  - Full bidirectional control
  - Example: QA55Q7FAM @ 192.168.101.52

### 📋 Planned
- **LG WebOS TVs (2014+):** WebSocket port 3000 (185 MAC prefixes)
- **Sony Bravia TVs (2013+):** HTTP/IRCC port 80 (138 MAC prefixes)
- **Philips Android TVs (2016+):** REST API port 1925 (22 MAC prefixes)

---

## Network Discovery Methods

### Method 0: Onsite Discovery Tool (Standalone)
**Best for:** Initial venue surveys and site assessments

**Standalone Python script** for discovering TVs without SmartVenue backend running.

**Usage:**
```bash
# On venue laptop/device
pip3 install requests tabulate
sudo apt-get install nmap -y  # Optional

# Scan venue network
python3 venue_tv_discovery_nmap_optional.py 192.168.1
```

**Features:**
- ✅ Scans **all TV brands** (Samsung, LG, Sony, Philips, Roku, Apple TV, Vizio, Panasonic, TCL, Hisense, Sharp)
- ✅ **Port scanning** for protocol detection
- ✅ Works with or without nmap
- ✅ Generates JSON + CSV reports

**Output:**
- `tv_discovery_report_YYYYMMDD_HHMMSS.json`
- `tv_discovery_report_YYYYMMDD_HHMMSS.csv`

**Import reports into SmartVenue** to create virtual controllers automatically.

**Documentation:** See `/VENUE_DISCOVERY_README.md` for full guide.

**Pros:** No SmartVenue needed, comprehensive scan, all brands
**Cons:** Manual process, requires report import

---

### Method 1: Quick Scan (Recommended)
**Best for:** Finding TVs you know exist on the network

1. Navigate to `/network-controllers`
2. Click **"Discover TVs"**
3. System scans known TV IPs (from `KNOWN_TVS` list)
4. See online/offline status instantly
5. Click device to test commands

**Pros:** Fast (2-3 seconds), reliable, works immediately
**Cons:** Only finds pre-configured TVs

---

### Method 2: Network Sweep
**Best for:** Finding all possible TVs on the network

1. Click **"Scan Network"** button
2. System performs ping sweep of local subnet (e.g., 192.168.101.0/24)
3. ARP cache populated with MAC addresses
4. MAC vendor lookup identifies manufacturers
5. Results displayed in "Discovered Devices" table

**Columns shown:**
- IP Address
- MAC Address
- Vendor (from 55,805-entry database)
- Hostname (if resolvable)
- Online Status
- Device Type Guess
- Action buttons

**Filter options:**
- Show only Samsung
- Show only LG
- Show only Sony
- Show all potential TVs

**Scan duration:** ~30 seconds for /24 subnet (254 IPs)

---

### Method 3: Brand-Specific Scan
**Best for:** Finding specific brand TVs with protocol detection

1. Select brand from dropdown (Samsung/LG/Sony/Philips)
2. Click **"Scan for [Brand] TVs"**
3. System:
   - Filters to devices with matching MAC vendor
   - Port scans brand-specific ports
   - Attempts protocol detection
   - Queries device info (if accessible without auth)
4. Results show:
   - Detected protocol (e.g., "Samsung Legacy" vs "Samsung WebSocket")
   - Model name (if discovered)
   - Firmware version (if available)
   - Pairing status

**Example Samsung Scan:**
```
Found 3 Samsung devices:

192.168.101.50 - E4:E0:C5:B8:5A:97
  → Protocol: Samsung Legacy (port 55000)
  → Model: LA40D550
  → Status: Ready to pair

192.168.101.52 - 01:23:45:67:89:AB
  → Protocol: Samsung WebSocket (port 8001)
  → Model: QA55Q7FAM
  → Status: Requires pairing

192.168.101.46 - XX:XX:XX:XX:XX:XX
  → Protocol: Samsung WebSocket (port 8001)
  → Model: UA75MU6100
  → Status: Offline
```

---

### Method 4: Manual Entry
**Best for:** Known IP addresses or troubleshooting

1. Click **"Add Device Manually"**
2. Enter IP address
3. System:
   - Pings device
   - Retrieves MAC via ARP
   - Looks up vendor
   - Suggests protocol
4. User confirms/selects protocol
5. Follow pairing workflow

---

## Adoption Workflow

### Step 1: Discover
Use one of the discovery methods above to find your TV

### Step 2: Verify
Click "Test" to verify device is reachable:
- ✅ Green: Device online and ready
- ⚠️ Yellow: Device online but protocol unclear
- ❌ Red: Device offline or unreachable

### Step 3: Add to Controllers
Click **"Adopt"** button:

#### What happens:
1. System checks MAC not already adopted
2. Generates unique hostname (e.g., `samsung-tv-52`)
3. Creates virtual controller in `devices` table:
   ```sql
   hostname: "samsung-tv-52"
   mac_address: "01:23:45:67:89:AB"
   ip_address: "192.168.101.52"
   device_type: "universal"
   device_subtype: "virtual_network_tv"
   network_protocol: "samsung_websocket"
   ```
4. Creates port assignment (port 1 = the TV itself)
5. Creates network credentials entry:
   ```sql
   device_hostname: "samsung-tv-52"
   protocol: "samsung_websocket"
   host: "192.168.101.52"
   port: 8001
   is_paired: false
   ```
6. Initiates pairing (if required)
7. Tests basic command (volume up/down)
8. Marks as adopted in scan cache

### Step 4: Pair (if required)

#### Samsung Legacy (D/E/F series):
1. Pairing request sent to TV
2. TV displays: **"SmartVenue wants to connect"**
3. User presses **"Allow"** on TV within 30 seconds
4. Connection established ✅
5. No token stored (pair each time)

#### Samsung Modern (Tizen):
1. Pairing request sent to port 8001
2. TV displays pairing popup
3. User accepts on TV
4. System receives auth token
5. Token stored in `network_tv_credentials.token`
6. Future connections use stored token ✅

#### LG WebOS (planned):
1. Connection request sent to port 3000
2. TV displays 6-digit pairing key
3. User enters key in SmartVenue UI
4. Client key received and stored
5. Future connections automatic ✅

### Step 5: Test & Configure
1. System sends test command (volume up)
2. User verifies TV responded
3. Configure friendly name (optional)
4. Configure location (optional)
5. Assign to room/zone (optional)

### Step 6: Done!
Device now appears in:
- Controllers list
- Control page (with same UI as IR controllers)
- Schedules (can be targeted)
- Command API (same endpoints)

---

## Using Network TVs

### Via UI (Control Page)
Network TVs appear identically to IR controllers:
- Same device card
- Same buttons (power, channel, volume)
- Same channel grid
- Badge shows "Network" vs "IR"

**User doesn't need to know the difference!**

### Via API
```bash
# Same API format as IR controllers
POST /api/v1/commands/samsung-tv-52/send
{
  "port": 1,
  "command": "power"
}
```

**Backend routes to correct transport** (network vs IR) automatically.

### Via Schedules
Network TVs can be scheduled exactly like IR controllers:
- Individual targeting
- Group targeting
- Time-based actions
- Same command types

---

## Troubleshooting

### Discovery Issues

**No devices found:**
- Verify TVs are powered on
- Check TVs are on same subnet as SmartVenue
- Verify no firewall blocking:
  - ICMP (ping)
  - ARP requests
  - TV control ports

**Wrong vendor shown:**
- MAC vendor database may be outdated
- Some devices use generic MACs
- Manual protocol selection available

**Device shown as offline:**
- TV may be in standby (Wake-on-LAN needed)
- Check network cable connected
- Verify IP address hasn't changed

### Pairing Issues

**Pairing timeout (Samsung Legacy):**
- Ensure user is at TV to accept prompt
- Check TV network control enabled:
  - Menu → Network → AllShare Settings → Enable
- Try pairing again within 30 seconds of popup

**Token invalid (Samsung Modern):**
- TV may have been factory reset
- Token expired (rare)
- Re-pair from SmartVenue UI
- Delete and re-add device

**Wrong protocol detected:**
- Port scan may be misleading
- Manually select correct protocol
- Verify TV firmware version matches protocol

### Command Issues

**Commands not working:**
- Verify pairing still valid
- Check token not expired
- Test network connectivity to TV
- Try re-pairing device

**Slow response:**
- Network congestion
- TV processing lag
- Check for firmware updates
- Consider IR fallback

**Intermittent failures:**
- TV may be sleeping/waking
- Network switch issues
- Check power saving settings on TV
- Verify MAC hasn't changed (DHCP renewal)

---

## MAC Address Verification

SmartVenue uses MAC addresses as the **source of truth** for device identity:

### Why MAC over IP?
- IP addresses can change (DHCP)
- MAC addresses are permanent (hardware)
- Prevents controlling wrong device
- Enables MAC-based adoption rules

### How it works:
1. During discovery: MAC stored in `network_scan_cache`
2. During adoption: MAC stored in `devices.mac_address`
3. Before each command: Verify current MAC matches
4. If mismatch: Alert user, update IP, log event

### ARP Cache Management:
```python
# Refresh ARP cache before sending command
subprocess.run(["ping", "-c", "1", ip_address])
mac = get_mac_from_arp(ip_address)

if mac != device.mac_address:
    log_warning(f"MAC mismatch for {hostname}: expected {device.mac_address}, got {mac}")
    # Update IP if needed, but keep original MAC
```

---

## Migration from IR to Network

### Strategy 1: Gradual Migration
1. Identify TVs with network support
2. Add as network devices (keep IR as backup)
3. Test network control thoroughly
4. Once confident, disable IR controller port
5. Update documentation

### Strategy 2: A/B Testing
1. Add TV via both IR and network
2. Track success rate and latency
3. Compare reliability over 1 week
4. Keep better-performing method

### Strategy 3: Hybrid Mode
1. Primary: Network control (fast, reliable)
2. Fallback: IR control (if network fails)
3. Automatic failover on timeout
4. Alert user to network issues

---

## Best Practices

### Network Setup
1. **Static IPs:** Assign static IPs to TVs via DHCP reservation
2. **Same Subnet:** Keep all TVs on same subnet as SmartVenue
3. **VLAN (optional):** Separate VLAN for displays
4. **QoS:** Prioritize TV control traffic
5. **Monitoring:** Monitor TV connectivity

### Security
1. **Token Encryption:** Encrypt tokens in database
2. **Rate Limiting:** Prevent command flooding
3. **Audit Logging:** Log all network commands
4. **Access Control:** Restrict who can adopt devices
5. **SSL/TLS:** Use encrypted ports when available

### Maintenance
1. **Regular Scans:** Re-scan network monthly
2. **MAC Verification:** Verify MACs haven't changed
3. **Firmware Updates:** Check for TV firmware updates
4. **Token Rotation:** Rotate tokens quarterly (where supported)
5. **Health Checks:** Automated ping tests

### Documentation
1. **Label TVs:** Physical labels with hostname
2. **Network Diagram:** Map TV locations and IPs
3. **Pairing Guide:** Document per-brand pairing steps
4. **Troubleshooting:** Maintain FAQ for common issues

---

## Performance Metrics

### Target KPIs
- **Discovery Time:** <30 seconds for full subnet scan
- **Pairing Time:** <2 minutes per device
- **Command Latency:** <100ms average
- **Success Rate:** >99% for network devices
- **Uptime:** >99.9% device availability

### Monitoring
```sql
-- Command success rate by protocol
SELECT
    network_protocol,
    COUNT(*) as total_commands,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
    AVG(execution_time_ms) as avg_latency_ms
FROM command_logs
WHERE device_hostname IN (
    SELECT hostname FROM devices WHERE device_subtype = 'virtual_network_tv'
)
GROUP BY network_protocol;
```

---

## ROI Analysis

### Time Savings
- **Discovery:** 25 minutes saved per TV (30min IR vs 5min network)
- **Troubleshooting:** 80% fewer issues (99% vs 90% reliability)
- **Maintenance:** 50% less time (no IR blaster alignment)

### Cost Savings
- **Hardware:** $25 saved per TV (no IR blaster needed)
- **Labor:** 20 hours saved per 50 TVs
- **Downtime:** Reduced guest complaints from failed IR

### Example Venue (50 TVs)
- **Setup Time Saved:** 25 min × 50 = 20.8 hours
- **Hardware Cost Saved:** $25 × 50 = $1,250
- **ROI:** Immediate (network infrastructure already exists)

---

## Next Steps

1. ✅ Complete Samsung WebSocket implementation
2. 📋 Implement LG WebOS support
3. 📋 Implement Sony IRCC support
4. 📋 Build automatic network scanning service
5. 📋 Create adoption wizard UI
6. 📋 Develop hybrid IR/Network failover

---

## References

- [Network Device Protocols](/docs/NETWORK_DEVICE_PROTOCOLS.md)
- [Samsung TV Setup Guide](/docs/SAMSUNG_TV_SETUP_GUIDE.md)
- [Legacy Samsung Setup](/docs/LEGACY_SAMSUNG_TV_SETUP.md)
- [Network TV Proof of Concept](/docs/NETWORK_TV_PROOF_OF_CONCEPT.md)
