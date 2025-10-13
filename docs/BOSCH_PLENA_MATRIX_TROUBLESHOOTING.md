# Bosch Plena Matrix Troubleshooting Guide

**Document Version:** 1.0
**Last Updated:** 2025-10-13
**Device Model:** PLM-4P125 (applies to all PLM-4Px2x series)

## Overview

This guide documents findings from diagnosing and implementing Bosch Plena Matrix amplifier integration. It covers the correct UDP protocol implementation, common issues, and resolution steps.

---

## Table of Contents

1. [Protocol Implementation](#protocol-implementation)
2. [Common Issues](#common-issues)
3. [Network Connectivity](#network-connectivity)
4. [API Configuration](#api-configuration)
5. [Testing Tools](#testing-tools)
6. [Device Lockout & Multi-Master](#device-lockout--multi-master)

---

## Protocol Implementation

### Critical Finding: 10-Byte Header Required

**ISSUE:** Initial implementation was sending incorrect packet format, causing devices to ignore all commands.

**INCORRECT FORMAT** (original):
```
[COMMAND: 4 bytes][SEQUENCE: 2 bytes][LENGTH: 2 bytes]
Total: 8 bytes
```

**CORRECT FORMAT** (per official API manual page 4):
```
[Protocol ID: 2 bytes][Sub Type: 2 bytes][Sequence: 2 bytes][Reserved: 2 bytes][Chunk Length: 2 bytes][COMMAND DATA: variable]
Total: 10-byte header + command data
```

### Header Field Values

| Field | Size | Value | Description |
|-------|------|-------|-------------|
| Protocol ID | 2 bytes | `0x5E41` | PLM-4Px2x amplifiers |
| Protocol ID | 2 bytes | `0x5E40` | PLM-8M8 matrix mixer |
| Sub Type | 2 bytes | `0x0001` | Master (controller/us) |
| Sub Type | 2 bytes | `0x0100` | Slave (device response) |
| Sequence Number | 2 bytes | `0x0001-0xFFFF` | Never 0, wraps at 65535 |
| Reserved | 2 bytes | `0x0000` | Always zero |
| Chunk Length | 2 bytes | `0x0004+` | Length of data after header |

### Example PING Packet

```
Correct 14-byte PING packet:
5E 41 00 01 00 01 00 00 00 04 50 49 4E 47
│     │     │     │     │     │
│     │     │     │     │     └─ "PING" command (4 bytes)
│     │     │     │     └─────── Chunk length: 4
│     │     │     └───────────── Reserved: 0x0000
│     │     └─────────────────── Sequence: 1
│     └───────────────────────── Sub Type: 0x0001 (master)
└─────────────────────────────── Protocol ID: 0x5E41 (amplifier)
```

### Implementation Reference

See: `backend/app/services/plena_matrix_discovery.py`

Key methods:
- `_build_packet_header()`: Constructs the 10-byte header
- `ping_device()`: Sends PING with correct format
- `get_device_info()`: Sends WHAT command with correct format

---

## Common Issues

### 1. Device Not Responding to UDP Commands

**Symptoms:**
- ICMP ping succeeds (device is online)
- UDP commands timeout with no response
- Ports 12128/12129 show as `open|filtered` in nmap

**Root Cause:**
UDP API is disabled in the device configuration.

**Resolution:**
1. Open **Bosch Audio Configurator** on PC
2. Connect to the device (IP: 192.168.90.17 for our test device)
3. Look for API settings:
   - "API Enable" or "External Control Enable"
   - "UDP Control Enable"
   - "3rd Party Integration"
   - "Network Control"
4. **Enable the UDP API**
5. Upload/apply configuration to device
6. **Close the Bosch Audio Configurator completely**
7. **Close any iPad/mobile apps** connected to the device
8. Test again

### 2. Exclusive Device Lock

**Symptoms:**
- Device was responding, then suddenly stops
- Device becomes unreachable (100% ICMP packet loss)
- Commands timeout

**Root Cause:**
Bosch devices allow only **one active control connection** at a time. When Bosch Audio Configurator or the iPad app connects, it locks out all other controllers.

**Resolution:**
1. Close Bosch Audio Configurator
2. Close iPad/mobile apps
3. Wait 10-30 seconds for the connection to fully release
4. Test network connectivity: `ping 192.168.90.17`
5. Test UDP: `python test_correct_protocol.py 192.168.90.17`

**Prevention:**
According to the API manual (page 6), masters should:
- Send SEIZ command with poll sub-type every 3 seconds
- Monitor the lockout count in SEPL responses
- Detect when another master has seized control
- Request SYNC packets to resynchronize after lockout release

### 3. Network Routing Issues

**Symptoms:**
- User can ping device from workstation
- Server cannot ping device
- Different subnets or VLANs

**Resolution:**
1. Check server network interfaces: `ip addr show`
2. Check routing: `ip route | grep 192.168.90`
3. Verify the server has a route to the device's subnet
4. Check for firewall rules blocking traffic
5. For VLAN issues, consult network administrator

---

## Network Connectivity

### UDP Port Configuration

| Port | Direction | Purpose |
|------|-----------|---------|
| 12128 | RX (device receives) | Commands from master to device |
| 12129 | TX (device transmits) | Responses from device to master |

**Note:** Both master and device use UDP. The device listens on 12128 and replies from 12129.

### Testing Network Connectivity

```bash
# 1. Test ICMP (basic connectivity)
ping -c 3 192.168.90.17

# 2. Test UDP ports (requires root)
sudo nmap -sU -p 12128,12129 192.168.90.17

# 3. Test UDP protocol
python test_correct_protocol.py 192.168.90.17 12128
```

### Expected Results

**Healthy device:**
```
ICMP: 0% packet loss, <1ms latency
UDP ports: open|filtered (typical for UDP)
Protocol test: Receives WHAT response with device info
```

**API disabled:**
```
ICMP: 0% packet loss
UDP ports: open|filtered
Protocol test: Timeout, no response
```

**Device locked/offline:**
```
ICMP: 100% packet loss
UDP ports: filtered/timeout
Protocol test: No response
```

---

## API Configuration

### POTA File Analysis

POTA files (.pota) are Bosch Audio Configurator project files. They contain:
- Device IP addresses and network settings
- Zone names and configuration
- **Important:** Device presets, but NOT the API enable flag

**To analyze a POTA file:**
```bash
python backend/analyze_pota.py path/to/file.pota
```

### Key Configuration Settings

When configuring in Bosch Audio Configurator:

1. **Network Settings**
   - IP Address: Static recommended
   - Subnet: Must match your network
   - Gateway: Set if device needs external access

2. **API Settings** (Location varies by firmware version)
   - Look in: System → Network → External Control
   - Or: System → API Settings
   - Enable: UDP API or External Control
   - Port: Defaults to 12128/12129

3. **Zone Configuration**
   - PLM-4P125 has 4 zones (4-channel amp)
   - Zone names from POTA: BAR, POKIES, OUTSIDE, BISTRO (our test device)
   - Gain range: -80dB to +10dB

### Device Information

**Test Device:**
- Model: PLM-4P125 (4-channel, 125W)
- IP: 192.168.90.17
- MAC: 00:1C:44:00:F0:58 (Bosch Security Systems)
- Zones: 4 (BAR, POKIES, OUTSIDE, BISTRO)

---

## Testing Tools

### 1. test_correct_protocol.py

Tests UDP communication with correct protocol format.

```bash
# Usage
python test_correct_protocol.py <ip_address> [port]

# Example
python test_correct_protocol.py 192.168.90.17 12128
```

**Output:**
- Shows packet structure with header breakdown
- Displays hex dump of sent packet
- Parses response header and command
- Returns success/fail status

### 2. test_plena_udp.py

Legacy test (uses incorrect 8-byte format - for comparison only).

```bash
python backend/test_plena_udp.py 192.168.90.17 12128 2
```

**Note:** This will fail with timeout because it uses the old incorrect format.

### 3. test_plena_seize.py

Tests SEIZ/PASS command sequence (for devices requiring authentication).

```bash
python backend/test_plena_seize.py 192.168.90.17 12128
```

### 4. analyze_pota.py

Analyzes POTA configuration files.

```bash
python backend/analyze_pota.py path/to/config.pota
```

---

## Device Lockout & Multi-Master

### Multi-Master System

Plena Matrix devices support multiple simultaneous controllers (iPad app, PC software, 3rd party integrations). However, there are coordination mechanisms:

### SEIZ (Seize) Command

Used to temporarily lock out other masters during bulk operations.

**When to use:**
- Performing bulk parameter downloads
- Uploading entire configurations
- Reading complete SYNC data sets

**Protocol (page 10):**
```python
# Poll lockout state (recommended every 3 seconds)
SEIZ command with sub-command 0x1F

# Response: SEPL packet
- Lock-Out State (1 byte): 0=free, 1=locked
- Lock-Out Owner (4 bytes): IP address of master holding lock
- Lock-Out Count (4 bytes): Number of times device has been seized
```

**Best Practice:**
1. Send SEIZ poll every 3 seconds
2. Track the Lock-Out Count
3. If count increases, another master seized control
4. Wait for lock release (random 3-5 second delay)
5. Request full SYNC to resynchronize
6. Resume normal operation

### PASS (Password) Command

**Purpose:** Get/set device password for preventing unintended access.

**Protocol (page 10):**
```
Send: PASS command (empty)
Response:
- Hardware Password Enforced (1 byte): 0=not required, 1=required
- Hardware Password (31 bytes): UTF-8 string, null-padded
```

**Implementation Note:**
Password is sent unencrypted. It's meant to prevent *unintended* access, not *unauthorized* access. Not a security feature.

### SYNC (Synchronization) Command

**Purpose:** Retrieve complete device state for synchronization.

**SYNC Packet Types:**

**For PLM-4Px2x Amplifiers:**
- Type 100: System state, I/O names, global settings
- Type 101: Preset names and validity
- Type 102: All audio parameters (volume, bass, etc.)

**Request (page 43):**
```python
SYNC command with Sync Request byte:
- 100 = First type
- 101 = Second type
- 102 = Third type
```

**Usage:**
1. On initial connection: Request all SYNC types
2. After lockout release: Request all SYNC types
3. Periodically (every 500ms-1s): Request type 102 (audio params)

**Response parsing:**
- Each SYNC response contains complete state for that category
- Update GUI/internal state from SYNC data
- Ignore SYNC values for parameters changed in last 2 seconds (avoid race conditions)

---

## Diagnostic Checklist

When a Plena Matrix device won't connect:

### Step 1: Network Layer
- [ ] Can server ping device? (`ping 192.168.90.17`)
- [ ] Is latency reasonable? (<10ms on local network)
- [ ] Check server routing to device subnet
- [ ] Check for VLAN isolation issues

### Step 2: Application Layer
- [ ] Are UDP ports accessible? (`sudo nmap -sU -p 12128,12129 <ip>`)
- [ ] Is packet format correct? (14-byte PING with 10-byte header)
- [ ] Test with `test_correct_protocol.py`

### Step 3: Device Configuration
- [ ] Is UDP API enabled in Bosch Audio Configurator?
- [ ] Is device password set? (try PASS command)
- [ ] Is another controller connected? (close all apps)
- [ ] Check device firmware version (older versions may differ)

### Step 4: Exclusive Lock
- [ ] Close Bosch Audio Configurator on PC
- [ ] Close iPad/mobile apps
- [ ] Wait 30 seconds for connection release
- [ ] Re-test connectivity

### Step 5: Protocol Verification
- [ ] Protocol ID correct? (`0x5E41` for amplifiers)
- [ ] Sub Type correct? (`0x0001` for master)
- [ ] Sequence number valid? (1-65535, never 0)
- [ ] Chunk length matches data? (4 for PING)

---

## Reference Documents

1. **PLENA_matrix_API_Operation_Manual_enUS_66188793867.pdf**
   - Official Bosch API documentation
   - Located in project root
   - Covers protocol details, packet structures, command reference

2. **backend/app/services/plena_matrix_discovery.py**
   - Corrected implementation with 10-byte header
   - Discovery and zone configuration

3. **backend/app/commands/executors/audio/bosch_plena_matrix.py**
   - Command executor for volume/mute control
   - GOBJ/POBJ command implementation

4. **POTA file (13-10-25_TIM.pota)**
   - Example configuration file
   - Contains zone names and device info
   - Located in project root

---

## Command Reference Quick Sheet

### PING (Device Health Check)
- **Purpose:** Verify device is online and responding
- **Packet:** 14 bytes (10 header + 4 "PING")
- **Response:** WHAT packet with device info (unicast) or EXPL (broadcast)
- **Note:** Always replies, even if locked out

### WHAT (Device Information)
- **Purpose:** Get firmware, MAC, IP, device name
- **Packet:** 14 bytes (10 header + 4 "WHAT")
- **Response:** Device info (firmware, MAC, IP, subnet, gateway, name)
- **Parse:** 136 bytes total (see manual page 8)

### PASS (Password Check)
- **Purpose:** Get password requirements
- **Packet:** 14 bytes (10 header + 4 "PASS")
- **Response:** Enforced flag + password string (36 bytes)

### SEIZ (Lockout Control)
- **Purpose:** Check/set device lockout state
- **Packet:** 15 bytes (10 header + 4 "SEIZ" + 1 sub-command)
- **Sub-command:** `0x1F` for poll
- **Response:** SEPL with lockout state + owner IP + count

### GOBJ (Global Object Control)
- **Purpose:** Set system-wide parameters
- **Examples:** Standby mode, global mute
- **Packet:** Variable (header + "GOBJ" + object ID + data)

### POBJ (Preset Object Control)
- **Purpose:** Set zone-specific parameters
- **Examples:** Volume, bass enhance, input levels
- **Packet:** Variable (header + "POBJ" + preset + object ID + data)

### SYNC (State Synchronization)
- **Purpose:** Download complete device state
- **Packet:** 15 bytes (10 header + 4 "SYNC" + 1 type)
- **Types:** 100, 101, 102 (see manual section 3.4)

---

## Troubleshooting Summary

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| ICMP timeout | Network routing issue | Check routing, VLANs, firewall |
| ICMP OK, UDP timeout | API disabled | Enable UDP API in configurator |
| Was working, now timeout | Exclusive lock | Close other apps, wait 30s |
| Wrong packet format | Missing 10-byte header | Use corrected implementation |
| Sequence number 0 | Invalid sequence | Use 1-65535, never 0 |
| Device offline after config | Config software connected | Close configurator app |

---

## Success Criteria

A properly configured and connected Plena Matrix device will:

1. ✅ Respond to ICMP ping with <10ms latency
2. ✅ Respond to UDP PING with WHAT packet (136 bytes)
3. ✅ Return firmware version, MAC, IP in WHAT response
4. ✅ Accept GOBJ commands for standby/mute
5. ✅ Accept POBJ commands for volume/zone control
6. ✅ Provide SYNC data for state synchronization
7. ✅ Support multiple masters via SEIZ coordination

---

## Future Improvements

### Recommended Enhancements:

1. **Auto-detect API disabled**
   - Add error detection for "device online but UDP not responding"
   - Display helpful error message directing user to enable API

2. **Password support**
   - Implement PASS command sequence
   - Prompt user for password if required
   - Store encrypted password in database

3. **SEIZ coordination**
   - Implement lockout polling (every 3 seconds)
   - Auto-resync after lockout release
   - Show "Device busy" status in UI

4. **Firmware version detection**
   - Parse WHAT response for actual firmware version
   - Adjust protocol based on version if needed

5. **Zone name discovery**
   - Implement SYNC packet parsing
   - Auto-populate zone names from device
   - Support for custom zone names

6. **Connection health monitoring**
   - Periodic PING to detect offline devices
   - Automatic reconnection on network recovery
   - Status indicators in UI

---

## Conclusion

The Plena Matrix UDP API implementation required corrections to match the official protocol specification. The key finding was the 10-byte header requirement (Protocol ID + Sub Type + Sequence + Reserved + Chunk Length) before command data.

With the corrected implementation, devices should respond reliably once:
1. UDP API is enabled in device configuration
2. No other applications hold exclusive lock
3. Network routing is properly configured

For questions or issues, refer to the official API manual or contact Bosch support.

**Document Author:** Claude (AI Assistant)
**Verified On:** PLM-4P125 at 192.168.90.17
**TapCommand Version:** 2025-10-13
