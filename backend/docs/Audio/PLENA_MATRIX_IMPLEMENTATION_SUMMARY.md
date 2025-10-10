# Bosch Plena Matrix Implementation Summary

## Overview

Successfully integrated **Bosch Plena Matrix** commercial audio amplifiers (PLM-4Px2x series) into TapCommand alongside the existing Bosch Praesensa (AES70) support.

## What Was Added

### Backend Components

1. **BoschPlenaMatrixExecutor** (`app/commands/executors/audio/bosch_plena_matrix.py`)
   - UDP-based command executor
   - Sends commands to ports 12128 (receive) / 12129 (transmit)
   - Supports volume control (0-100%, maps to -80dB to +10dB)
   - Supports mute/unmute
   - Stateless UDP communication with sequence numbering

2. **PlenaMatrixDiscoveryService** (`app/services/plena_matrix_discovery.py`)
   - Ping devices to check availability
   - Query device information via UDP
   - Create Virtual Controllers and Devices (zones)
   - Manual zone configuration (no auto-discovery unlike AES70)

3. **Command Router Updates** (`app/commands/router.py`)
   - Added routing for `bosch_plena_matrix` protocol
   - Routes audio_zone commands to appropriate executor

4. **Audio Controller API Updates** (`app/routers/audio_controllers.py`)
   - Updated `AudioControllerCreate` model to include:
     - `protocol` field (bosch_aes70 or bosch_plena_matrix)
     - `total_zones` field (for Plena Matrix, default 4)
   - Updated discovery endpoint to route based on protocol
   - Default ports: 65000 (AES70) or 12128 (Plena Matrix)

### Frontend Components

1. **Audio Page Updates** (`frontend-v2/src/features/audio/pages/audio-page.tsx`)
   - Added protocol selector dropdown
   - Dynamic port selection based on protocol
   - Zone count input for Plena Matrix
   - Updated form to send protocol, port, and total_zones

2. **Amplifier Info Cards** (`frontend-v2/src/features/audio/components/amplifier-info-cards.tsx`)
   - Added Plena Matrix card with implementation details
   - Marked as "implemented" status
   - Includes setup steps and notes

### Documentation

1. **Integration Guide** (`docs/Audio/BOSCH_PLENA_MATRIX_INTEGRATION.md`)
   - Complete protocol documentation
   - Setup instructions
   - API reference
   - Troubleshooting guide
   - Comparison with AES70/Praesensa

## Supported Models

- **PLM-4P220** - 4 Channel DSP 220W Amplifier
- **PLM-4P120** - 4 Channel DSP 120W Amplifier
- Other PLM-4Px2x series amplifiers

## Protocol Comparison

| Feature | Praesensa (AES70) | Plena Matrix (UDP) |
|---------|-------------------|---------------------|
| **Protocol** | AES70/OMNEO (TCP) | Proprietary UDP |
| **Port** | 65000 | 12128 (RX) / 12129 (TX) |
| **Connection** | Persistent TCP | Stateless UDP |
| **Discovery** | Auto (role-based) | Manual configuration |
| **Zones** | Auto-detected | Manual (default 4) |
| **Volume Control** | ✅ 0-100% | ✅ 0-100% |
| **Mute** | ✅ Yes | ✅ Yes |
| **Authentication** | None | None (optional PASS) |
| **Use Case** | Enterprise PA | Commercial audio |

## Usage Example

### Add Plena Matrix Amplifier

```bash
POST /api/audio/controllers/discover
{
  "ip_address": "192.168.101.50",
  "controller_name": "Main Dining Audio",
  "protocol": "bosch_plena_matrix",
  "port": 12128,
  "total_zones": 4,
  "location": "Main Dining"
}
```

### Control Zone Volume

```bash
POST /api/audio/zones/1/volume
{
  "volume": 75
}
```

### Mute/Unmute

```bash
POST /api/audio/zones/1/mute
{
  "mute": true
}
```

## Technical Details

### UDP Packet Structure

```
[COMMAND_TYPE: 4 bytes]  # e.g., "GOBJ", "PING"
[SEQUENCE_NUMBER: 2 bytes]  # uint16 big-endian
[DATA_LENGTH: 2 bytes]  # uint16 big-endian
[DATA: variable]  # Command-specific data
```

### Volume Conversion

- User input: 0-100%
- Amplifier range: -80 dB to +10 dB
- Linear mapping: `dB = -80 + (volume/100) × 90`

### Zone Configuration

Stored in `VirtualDevice.connection_config`:
```json
{
  "zone_index": 0,
  "gain_range": [-80.0, 10.0],
  "supports_mute": true
}
```

## Database Schema

### VirtualController (Amplifier)

```sql
controller_id: plm-<ip-address>
controller_type: audio
protocol: bosch_plena_matrix
ip_address: <amplifier_ip>
port: 12128
```

### VirtualDevice (Zone)

```sql
device_type: audio_zone
protocol: bosch_plena_matrix
port_number: 1-4
connection_config: {zone_index, gain_range, supports_mute}
cached_volume_level: 0-100
cached_mute_status: boolean
```

## Files Modified/Created

### Backend
- ✅ `app/commands/executors/audio/bosch_plena_matrix.py` (new)
- ✅ `app/commands/executors/audio/__init__.py` (updated)
- ✅ `app/services/plena_matrix_discovery.py` (new)
- ✅ `app/commands/router.py` (updated)
- ✅ `app/routers/audio_controllers.py` (updated)
- ✅ `docs/Audio/BOSCH_PLENA_MATRIX_INTEGRATION.md` (new)
- ✅ `docs/Audio/PLENA_MATRIX_IMPLEMENTATION_SUMMARY.md` (new)

### Frontend
- ✅ `src/features/audio/pages/audio-page.tsx` (updated)
- ✅ `src/features/audio/components/amplifier-info-cards.tsx` (updated)

## Testing Checklist

- [ ] Add Plena Matrix amplifier via UI
- [ ] Verify 4 zones are created
- [ ] Test volume control (0-100%)
- [ ] Test volume up/down buttons
- [ ] Test mute/unmute
- [ ] Test with actual PLM-4P220 hardware
- [ ] Verify UDP communication logs
- [ ] Test concurrent zone control
- [ ] Test with bridged mode (2 zones)

## Future Enhancements

1. **Enhanced Discovery**
   - Parse actual device info from WHAT command
   - Detect model automatically (PLM-4P220 vs PLM-4P120)
   - Auto-detect bridged mode

2. **Advanced Features**
   - Preset recall (PSET command)
   - Signal monitoring (SMON command)
   - Input gain control
   - Routing configuration
   - Password/seize support (PASS, SEIZ)

3. **Protocol Improvements**
   - Implement full packet parsing
   - Handle error responses
   - Retry logic for UDP packets
   - Connection pooling optimization

## Notes

- Protocol does NOT use AES70 (despite Bosch making both)
- OMNEO is used for **audio routing**, not control
- Plena Matrix has its own proprietary UDP API
- No authentication required by default
- Stateless UDP is simpler than AES70 TCP but less feature-rich

## References

- [Plena Matrix API Manual](https://resources-boschsecurity-cdn.azureedge.net/public/documents/PLENA_matrix_API_Operation_Manual_enUS_66188793867.pdf)
- [PLM-4Px2x Datasheet](https://resources-boschsecurity-cdn.azureedge.net/public/documents/PLM_4Px2x_Data_sheet_enUS_11767088523.pdf)
