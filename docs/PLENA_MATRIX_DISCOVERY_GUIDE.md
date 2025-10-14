# Bosch Plena Matrix Discovery & Adoption Guide

**Document Version:** 1.0
**Date:** 2025-10-13
**Status:** Implementation Complete

## Overview

This guide documents the discovery and adoption process for Bosch Plena Matrix PLM-4Px2x amplifiers in TapCommand. The system creates a Virtual Controller (like `nw-*` devices) with individual zones as Virtual Devices (like ports on IR controllers).

---

## Discovery Architecture

### Virtual Controller Model

Plena Matrix devices follow the same pattern as Network TVs:

**Controller (audio-*):**
- Controller ID: `audio-plm-{ip-with-dashes}` (e.g., `audio-plm-192-168-90-17`)
- Controller Type: `audio`
- Protocol: `bosch_plena_matrix`
- Stores device-level information (model, firmware, MAC, presets)

**Virtual Devices (zones):**
- Each amplifier zone becomes a Virtual Device
- Port number = Zone number (1-4 for PLM-4Px2x)
- Device Type: `audio_zone`
- Stores zone-specific config (gain range, mute support)

This aligns with the existing `nw-*` (Network TV) architecture pattern.

---

## Discovery Process

### Step 1: Device Ping (PING Command)

**Purpose:** Verify device is online and responding

**Packet Structure:**
```
[10-byte header][4-byte "PING"]
Total: 14 bytes
```

**Response:** WHAT packet with basic device info

### Step 2: Device Information (WHAT Command)

**Purpose:** Get comprehensive device details

**Information Retrieved:**
- **Firmware Version**: Major.Minor.Revision (e.g., v1.1.5)
- **MAC Address**: 6-byte hardware address (e.g., 00:1c:44:00:f0:58)
- **Model Detection**: From custom mode byte:
  - `0x00` = PLM-4P120 (125W)
  - `0x01` = PLM-4P220 (220W)
  - `0x04` = PLM-4P125 (actually 220W variant)
- **Device Name**: 32-byte ASCII string (factory default)
- **User Name**: 81-byte UTF-8 string (user-customizable name)
- **IP Address**: IPv4 address
- **Subnet Mask**: Network mask
- **Gateway**: Default gateway
- **DHCP Status**: Enabled/Disabled
- **Lockout Status**: Free/Locked by another master

**Stored in:** `VirtualController` fields:
- `device_model`: "PLM-4P125"
- `firmware_version`: "1.1.5"
- `mac_address`: "00:1c:44:00:f0:58" (via connection_config)

### Step 3: Preset Discovery (SYNC Type 101)

**Purpose:** Retrieve configured preset names

**Command:** `SYNC` with type byte `0x65` (101 decimal)

**Packet Structure:**
```
[10-byte header][4-byte "SYNC"][1-byte type: 0x65]
Total: 15 bytes
```

**Response Format:**
Each preset entry is 33 bytes:
- Byte 0: Validity flag (0x00 = invalid, 0x01+ = valid)
- Bytes 1-32: Preset name (32-byte UTF-8 string, null-padded)

**Typical preset count:** 4-8 presets depending on device configuration

**Example discovered presets:**
```
✓ Preset 1: "Music All + MIC" (valid)
✗ Preset 2: "Raffle" (invalid/inactive)
✓ Preset 3: "Function" (valid)
✓ Preset 4: "Backup" (valid)
```

**Stored in:** `VirtualController.connection_config`:
```json
{
  "presets": [
    {
      "preset_number": 1,
      "preset_name": "Music All + MIC",
      "is_valid": true,
      "preset_index": 0
    },
    ...
  ]
}
```

### Step 4: Zone Discovery

**Current Implementation:** Creates default zones (1-4) based on amplifier model

**Future Enhancement:** SYNC Type 100 can retrieve actual I/O names:
- Input names
- Output names
- Zone routing configuration

**Zone Structure:**
```python
{
    "zone_number": 1,       # Display number (1-4)
    "zone_name": "Zone 1",  # User-friendly name
    "zone_index": 0,        # API index (0-3)
    "gain_range": [-80.0, 10.0],  # dB range
    "supports_mute": True,
    "is_active": True
}
```

**Stored as:** Individual `VirtualDevice` records with:
- `port_number`: Zone number (1-4)
- `device_name`: Zone name
- `connection_config`: Zone-specific settings

---

## Data Storage Schema

### VirtualController Record

```python
VirtualController(
    controller_id="audio-plm-192-168-90-17",
    controller_name="Main Amplifier",  # User-provided
    controller_type="audio",
    protocol="bosch_plena_matrix",
    ip_address="192.168.90.17",
    port=12128,
    device_model="PLM-4P125",
    firmware_version="1.1.5",
    is_online=True,
    connection_config={
        "mac_address": "00:1c:44:00:f0:58",
        "device_name": "Bosch PLM-4P125",
        "user_name": "Main Amplifier",
        "total_zones": 4,
        "presets": [
            {
                "preset_number": 1,
                "preset_name": "Music All + MIC",
                "is_valid": True,
                "preset_index": 0
            },
            ...
        ],
        "discovered_at": 1234567890.123
    }
)
```

### VirtualDevice Records (Zones)

```python
VirtualDevice(
    controller_id=controller.id,
    port_number=1,  # Zone 1
    device_name="Zone 1",
    device_type="audio_zone",
    protocol="bosch_plena_matrix",
    ip_address="192.168.90.17",
    port=12128,
    is_active=True,
    is_online=True,
    connection_config={
        "zone_index": 0,  # 0-based for API
        "gain_range": [-80.0, 10.0],
        "supports_mute": True
    },
    cached_volume_level=50,  # 0-100%
    cached_mute_status=False
)
```

---

## Adoption UI Flow

### Display During Adoption

When adopting a Plena Matrix device, the UI should display:

1. **Device Information** (from WHAT response):
   ```
   ╔═══════════════════════════════════════════════════╗
   ║ Discovering Bosch Plena Matrix Device            ║
   ╟───────────────────────────────────────────────────╢
   ║ Model:          PLM-4P125                         ║
   ║ Firmware:       v1.1.5                            ║
   ║ MAC Address:    00:1c:44:00:f0:58                 ║
   ║ IP Address:     192.168.90.17                     ║
   ║ Device Name:    Bosch PLM-4P125                   ║
   ╚═══════════════════════════════════════════════════╝
   ```

2. **Discovered Presets** (from SYNC 101):
   ```
   ╔═══════════════════════════════════════════════════╗
   ║ Available Presets                                 ║
   ╟───────────────────────────────────────────────────╢
   ║ ✓ Preset 1: Music All + MIC                      ║
   ║ ✗ Preset 2: Raffle (inactive)                    ║
   ║ ✓ Preset 3: Function                             ║
   ║ ✓ Preset 4: Backup                               ║
   ╚═══════════════════════════════════════════════════╝
   ```

3. **Zones Being Created**:
   ```
   ╔═══════════════════════════════════════════════════╗
   ║ Creating Audio Zones                              ║
   ╟───────────────────────────────────────────────────╢
   ║ ✓ Zone 1 created                                  ║
   ║ ✓ Zone 2 created                                  ║
   ║ ✓ Zone 3 created                                  ║
   ║ ✓ Zone 4 created                                  ║
   ╚═══════════════════════════════════════════════════╝
   ```

4. **Adoption Complete**:
   ```
   ╔═══════════════════════════════════════════════════╗
   ║ ✅ Adoption Complete!                             ║
   ╟───────────────────────────────────────────────────╢
   ║ Controller: Main Amplifier                        ║
   ║ Zones: 4                                          ║
   ║ Presets: 4 (3 active)                             ║
   ╚═══════════════════════════════════════════════════╝
   ```

### Progressive Discovery

The discovery process should show progress:

```
🔍 Step 1/4: Pinging device...        ✓ Online (0.2ms)
🔍 Step 2/4: Getting device info...   ✓ PLM-4P125 v1.1.5
🔍 Step 3/4: Discovering presets...   ✓ Found 4 presets
🔍 Step 4/4: Creating zones...        ✓ Created 4 zones
```

---

## API Endpoints

### Discovery & Adoption

**POST** `/api/audio/plena-matrix/discover`

Request:
```json
{
  "ip_address": "192.168.90.17",
  "controller_name": "Main Amplifier",
  "total_zones": 4,
  "venue_name": "My Venue",
  "location": "Main Floor"
}
```

Response:
```json
{
  "controller": {
    "id": 123,
    "controller_id": "audio-plm-192-168-90-17",
    "controller_name": "Main Amplifier",
    "device_model": "PLM-4P125",
    "firmware_version": "1.1.5",
    "connection_config": {
      "mac_address": "00:1c:44:00:f0:58",
      "presets": [...]
    }
  },
  "zones": [
    {
      "id": 456,
      "port_number": 1,
      "device_name": "Zone 1",
      "device_type": "audio_zone"
    },
    ...
  ]
}
```

### Get Controller Details

**GET** `/api/audio/controllers/{controller_id}`

Returns full controller information including discovered presets and zone configuration.

---

## Zone Control

Once adopted, zones can be controlled like any other audio device:

### Volume Control

**POST** `/api/audio/zones/{zone_id}/volume`

```json
{
  "level": 75  // 0-100%
}
```

Backend converts percentage to dB range (-80 to +10 dB).

### Mute Control

**POST** `/api/audio/zones/{zone_id}/mute`

```json
{
  "mute": true
}
```

### Preset Recall

**POST** `/api/audio/controllers/{controller_id}/preset`

```json
{
  "preset_number": 1  // Recall "Music All + MIC"
}
```

---

## Future Enhancements

### 1. Zone Name Discovery (SYNC Type 100)

Implement parsing of SYNC Type 100 to retrieve:
- Actual input names (from device config)
- Actual output names (zone names from configurator)
- Routing configuration

**Example:**
```python
# Instead of "Zone 1", "Zone 2"...
zones = ["BAR", "POKIES", "OUTSIDE", "BISTRO"]
```

### 2. Real-time Audio Monitoring (SYNC Type 102)

Poll SYNC Type 102 every 500ms-1s to get:
- Current volume levels per zone
- Mute status per zone
- Input signal levels
- Clipping/limiting indicators

**Use case:** Live status monitoring in UI

### 3. Device Lockout Handling (SEIZ Command)

Implement SEIZ polling to:
- Detect when another master has control
- Display "Device Busy" status in UI
- Auto-resync after lockout release

### 4. Password Support (PASS Command)

Handle devices with password protection:
- Check if password required on adoption
- Prompt user for password
- Store encrypted in database
- Send with subsequent commands

---

## Testing Tools

### 1. test_correct_protocol.py

Tests basic PING/WHAT communication:
```bash
python test_correct_protocol.py 192.168.90.17 12128
```

**Output:** Device info (model, firmware, MAC)

### 2. test_sync_presets.py

Tests SYNC Type 101 preset retrieval:
```bash
python test_sync_presets.py 192.168.90.17 12128
```

**Output:** List of preset names and validity

### 3. Integration Test

Test full discovery via API:
```bash
curl -X POST http://localhost:8000/api/audio/plena-matrix/discover \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "192.168.90.17",
    "controller_name": "Test Amplifier",
    "total_zones": 4
  }'
```

---

## Known Limitations

### 1. SYNC Type 100 Not Yet Implemented

Currently creates default zone names ("Zone 1", "Zone 2"...). Real names from device config not yet retrieved.

**Workaround:** User can rename zones after adoption.

### 2. No Real-time Status Polling

Current implementation doesn't poll for volume/mute status changes.

**Impact:** UI won't reflect changes made by other controllers until next command is sent.

### 3. Exclusive Lock Not Handled

If Bosch Audio Configurator or iPad app connects, device becomes unavailable.

**Detection:** Commands will timeout
**Resolution:** User must close other applications

### 4. Password Protection Not Supported

If device has password enabled, adoption will fail.

**Workaround:** Disable password in Bosch Audio Configurator before adoption.

---

## Troubleshooting

### Device Not Found During Discovery

**Symptoms:**
- PING times out
- "Device not responding" error

**Checks:**
1. ✓ Device online? (`ping 192.168.90.17`)
2. ✓ UDP API enabled in device config?
3. ✓ No other applications connected?
4. ✓ Server has route to device subnet?

### Preset Discovery Fails

**Symptoms:**
- Device info retrieved successfully
- SYNC command times out
- No presets listed

**Possible Causes:**
- Device locked by another master
- SYNC not supported on older firmware
- UDP buffer size too small

**Resolution:**
- Close other applications
- Update firmware
- Check logs for specific error

### Zones Not Created

**Symptoms:**
- Controller created successfully
- No zone Virtual Devices

**Checks:**
1. Check `total_zones` parameter (should be 4 for PLM-4Px2x)
2. Check database for existing zone records
3. Review logs for SQL errors

---

## Implementation Checklist

For developers implementing Plena Matrix support:

- [x] Implement 10-byte header format
- [x] Bind socket to port 12129 for responses
- [x] Implement WHAT command parsing
- [x] Implement SYNC Type 101 (presets)
- [x] Store device info in VirtualController
- [x] Store presets in connection_config
- [x] Create Virtual Devices for zones
- [ ] Implement SYNC Type 100 (zone names)
- [ ] Implement SYNC Type 102 (audio monitoring)
- [ ] Implement SEIZ lockout handling
- [ ] Implement PASS password support
- [ ] Create adoption UI flow
- [ ] Display discovered info during adoption
- [ ] Implement zone control commands (POBJ)
- [ ] Implement preset recall (POBJ)
- [ ] Add real-time status polling

---

## References

1. **PLENA_matrix_API_Operation_Manual_enUS_66188793867.pdf**
   - Official Bosch documentation
   - Section 1.1: Protocol header structure
   - Section 1.5: PING command
   - Section 1.6: WHAT response format
   - Section 3.4: SYNC commands (Types 100, 101, 102)

2. **Implementation Files:**
   - `backend/app/services/plena_matrix_discovery.py` - Discovery service
   - `backend/app/commands/executors/audio/bosch_plena_matrix.py` - Command executor
   - `backend/app/models/virtual_controller.py` - Data models

3. **Test Tools:**
   - `test_correct_protocol.py` - Basic connectivity test
   - `test_sync_presets.py` - Preset discovery test

---

**Document Author:** Claude (AI Assistant)
**Last Updated:** 2025-10-13
**Status:** ✅ Core Implementation Complete
