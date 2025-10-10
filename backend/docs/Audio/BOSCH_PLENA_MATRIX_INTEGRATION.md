# Bosch Plena Matrix Integration

## Overview

The TapCommand system now supports **Bosch Plena Matrix** commercial audio amplifiers via the UDP API protocol.

### Supported Models

- **PLM-4P220** - 4 Channel DSP 220W Amplifier
- **PLM-4P120** - 4 Channel DSP 120W Amplifier
- Other PLM-4Px2x series amplifiers

## Protocol Details

### Communication

- **Protocol**: UDP (User Datagram Protocol)
- **Receive Port**: `12128` (device listens on this port)
- **Transmit Port**: `12129` (device sends responses from this port)
- **No authentication required**

### Command Structure

UDP packets follow this format:

```
[COMMAND_TYPE: 4 bytes]
[SEQUENCE_NUMBER: 2 bytes (uint16, big-endian)]
[DATA_LENGTH: 2 bytes (uint16, big-endian)]
[DATA: variable length]
```

### Command Types

- `PING` - Check device availability
- `WHAT` - Get device information
- `EXPL` - Get extended device information
- `GOBJ` - Global Object Read/Write (volume, mute, etc.)
- `POBJ` - Preset Object Read/Write
- `PSET` - Preset Change
- `SMON` - Signal Monitoring

## Features

### Zone Control

Each Plena Matrix amplifier can control multiple zones:

- **PLM-4P220/120**: 4 zones (4 x 220W or 4 x 120W)
- **Bridged mode**: 2 zones (2 x 385W)

### Supported Commands

- `set_volume` - Set zone volume (0-100%)
- `volume_up` - Increase volume by 5%
- `volume_down` - Decrease volume by 5%
- `mute` - Mute zone
- `unmute` - Unmute zone
- `toggle_mute` - Toggle mute state

### Volume Range

- **dB Range**: -80 dB to +10 dB
- **User Range**: 0% to 100%
- **Conversion**: Linear mapping between user percentage and dB value

## Setup

### 1. Network Configuration

Ensure the Plena Matrix amplifier is on the same network as the TapCommand backend:

```bash
# Test connectivity
ping <amplifier_ip>

# Test UDP port (optional)
nc -u <amplifier_ip> 12128
```

### 2. Add Amplifier via API

```bash
POST /api/audio/controllers/discover
Content-Type: application/json

{
  "ip_address": "192.168.101.50",
  "controller_name": "Main Dining Audio",
  "protocol": "bosch_plena_matrix",
  "port": 12128,
  "total_zones": 4,
  "venue_name": "Restaurant",
  "location": "Main Dining"
}
```

### 3. Verify Zones

```bash
GET /api/audio/zones?controller_id=plm-192-168-101-50
```

Response:
```json
[
  {
    "id": 1,
    "controller_id": 1,
    "controller_name": "Main Dining Audio",
    "zone_number": 1,
    "zone_name": "Zone 1",
    "device_type": "audio_zone",
    "protocol": "bosch_plena_matrix",
    "volume_level": 50,
    "is_muted": false,
    "is_online": true,
    "gain_range": [-80.0, 10.0],
    "has_mute": true
  },
  ...
]
```

## Usage Examples

### Set Volume

```bash
POST /api/audio/zones/1/volume
Content-Type: application/json

{
  "volume": 75
}
```

### Volume Up/Down

```bash
POST /api/audio/zones/1/volume/up
POST /api/audio/zones/1/volume/down
```

### Mute Control

```bash
# Mute
POST /api/audio/zones/1/mute
Content-Type: application/json
{
  "mute": true
}

# Unmute
POST /api/audio/zones/1/mute
Content-Type: application/json
{
  "mute": false
}

# Toggle
POST /api/audio/zones/1/mute
```

## Architecture

### Components

1. **BoschPlenaMatrixExecutor** (`app/commands/executors/audio/bosch_plena_matrix.py`)
   - Executes volume and mute commands
   - Handles UDP communication
   - Manages socket connections per controller

2. **PlenaMatrixDiscoveryService** (`app/services/plena_matrix_discovery.py`)
   - Discovers amplifiers on network
   - Queries device information
   - Creates Virtual Controllers and Devices

3. **Audio Router** (`app/routers/audio_controllers.py`)
   - HTTP API endpoints
   - Routes commands to appropriate executor
   - Supports both Praesensa (AES70) and Plena Matrix (UDP)

### Database Schema

**VirtualController** (Audio Amplifier):
- `controller_id`: `plm-<ip-address>`
- `controller_type`: `audio`
- `protocol`: `bosch_plena_matrix`
- `ip_address`: Amplifier IP
- `port`: `12128`

**VirtualDevice** (Audio Zone):
- `device_type`: `audio_zone`
- `protocol`: `bosch_plena_matrix`
- `port_number`: Zone number (1-4)
- `connection_config`:
  ```json
  {
    "zone_index": 0,
    "gain_range": [-80.0, 10.0],
    "supports_mute": true
  }
  ```

## Comparison: Praesensa vs Plena Matrix

| Feature | Praesensa (AES70) | Plena Matrix (UDP) |
|---------|-------------------|---------------------|
| Protocol | AES70/OMNEO (TCP) | Proprietary UDP |
| Port | 65000 | 12128 (RX) / 12129 (TX) |
| Connection | Persistent TCP | Stateless UDP |
| Discovery | Role-based objects | Manual configuration |
| Use Case | Enterprise PA systems | Commercial audio zones |
| Complexity | High (OCA standard) | Medium (custom API) |

## Troubleshooting

### Amplifier Not Responding

```bash
# 1. Check network connectivity
ping <amplifier_ip>

# 2. Check UDP port (Linux)
sudo nmap -sU -p 12128 <amplifier_ip>

# 3. Check firewall
sudo ufw status
sudo ufw allow 12128/udp
sudo ufw allow 12129/udp
```

### Commands Not Working

- Check zone number (1-4 for PLM-4P220)
- Verify volume range (-80 to +10 dB)
- Check logs for UDP errors:
  ```bash
  tail -f backend/backend.out | grep -i plena
  ```

### Discovery Fails

- Ensure amplifier is powered on
- Check IP address is correct
- Verify network segment (no VLANs blocking UDP)
- Check amplifier firmware version (may affect API)

## API Reference

### Complete OpenAPI Documentation

Available at: `http://<backend_ip>:8000/docs#/audio`

### Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/audio/controllers/discover` | POST | Add amplifier |
| `/api/audio/controllers` | GET | List all controllers |
| `/api/audio/zones` | GET | List all zones |
| `/api/audio/zones/{id}/volume` | POST | Set volume |
| `/api/audio/zones/{id}/volume/up` | POST | Volume +5% |
| `/api/audio/zones/{id}/volume/down` | POST | Volume -5% |
| `/api/audio/zones/{id}/mute` | POST | Mute/unmute |
| `/api/audio/controllers/{id}` | DELETE | Remove controller |

## Future Enhancements

- [ ] Parse actual device info from `WHAT` command response
- [ ] Support for preset recall (`PSET` command)
- [ ] Signal monitoring (`SMON` command)
- [ ] Input gain control
- [ ] Routing configuration
- [ ] Automatic device discovery via broadcast
- [ ] Password/seize support (`PASS`, `SEIZ` commands)

## References

- [Plena Matrix API Manual](https://resources-boschsecurity-cdn.azureedge.net/public/documents/PLENA_matrix_API_Operation_Manual_enUS_66188793867.pdf)
- [PLM-4Px2x Datasheet](https://resources-boschsecurity-cdn.azureedge.net/public/documents/PLM_4Px2x_Data_sheet_enUS_11767088523.pdf)
- [Bosch Commercial Audio](https://www.boschsecurity.com/xc/en/solutions/public-address-and-voice-alarm/plena-matrix/)
