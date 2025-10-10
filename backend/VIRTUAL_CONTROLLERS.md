# Virtual Controllers - Network TV Integration

## Overview

Virtual Controllers are software-based controller representations for network-controllable devices (TVs, streaming devices, etc.). They provide a unified interface alongside physical IR controllers, allowing network TVs to be managed using the same UI and workflows.

## Architecture

### Key Components

1. **Virtual Controller** - Software representation of a network TV controller
2. **Virtual Device** - The actual network TV mapped to a Virtual Controller port
3. **Network Discovery** - Scans network for controllable TVs
4. **Adoption Flow** - Converts discovered TVs into Virtual Controllers
5. **Unified API** - Virtual Controllers appear as `ManagedDevice` objects alongside IR controllers

### Database Schema

```
virtual_controllers
├── id (primary key)
├── controller_name       # "Samsung TV Legacy (50) Controller"
├── controller_id         # "nw-b85a97" (nw-{last_6_mac_chars})
├── controller_type       # "network_tv" | "streaming_device"
├── protocol             # "samsung_legacy" | "lg_webos" | etc.
├── total_ports          # Always 1 for Virtual Controllers
├── capabilities         # JSON with ports array and brand info
├── is_active
├── is_online
└── ...metadata

virtual_devices
├── id (primary key)
├── controller_id (FK)
├── port_number          # Always 1
├── port_id             # "nw-b85a97-1"
├── device_name         # "Samsung TV Legacy (50)"
├── ip_address
├── mac_address
├── protocol
├── default_channel     # Default channel for this TV
├── tag_ids            # Device categorization tags
└── ...metadata

network_scan_cache
├── id (primary key)
├── ip_address
├── mac_address
├── vendor             # "Samsung Electronics Co.,Ltd"
├── is_adopted        # True if converted to Virtual Controller
├── is_hidden         # User manually hidden from discovery
└── ...discovery data
```

## Discovery & Adoption Flow

### 1. Network Scanning

The system continuously scans the network for controllable devices:

```python
# Network discovery identifies TVs by:
- MAC vendor lookup (Samsung, LG, Sony, etc.)
- Open ports (55000 for Samsung, 3000 for LG, etc.)
- Device type inference from vendor and ports

# Results stored in network_scan_cache table
```

### 2. Device Discovery Endpoint

```bash
GET /api/network-tv/discover
```

Returns non-adopted, non-hidden network TVs:
- Samsung TVs (ports 55000, 8001, 8002)
- LG TVs (port 3000)
- Sony TVs (port 20060)
- Other network-controllable devices

### 3. Adoption Process

```bash
POST /api/network-tv/adopt
{
  "ip": "192.168.101.50",
  "device_type": "samsung_tv_legacy"
}
```

**Adoption creates:**

1. **Virtual Controller** with:
   - Unique ID: `nw-{last_6_mac_chars}` (e.g., `nw-b85a97`)
   - Brand extracted from MAC vendor
   - 1 port (the TV itself)
   - IR-like capabilities with brand info

2. **Virtual Device** on port 1:
   - Network connection details
   - Protocol information
   - Default channel support
   - Tag support

3. **Network scan cache updated**:
   - `is_adopted = True`
   - Links to controller via `adopted_hostname`

### 4. Controller ID Format

**Format:** `nw-{last_6_mac_chars}`

Examples:
- MAC `E4:E0:C5:B8:5A:97` → Controller ID `nw-b85a97`
- MAC `E4:E0:C5:9C:F3:32` → Controller ID `nw-9cf332`

**Why this format?**
- `nw-` prefix identifies network controllers (vs `ir-` for IR controllers)
- MAC-based ensures uniqueness
- Short and recognizable
- Persists even if TV IP changes

## Capabilities Structure

Virtual Controllers have IR-like capabilities for frontend compatibility:

```json
{
  "power": true,
  "volume": true,
  "channels": true,
  "source_select": true,
  "ports": [{
    "port": 1,
    "brand": "Samsung",
    "description": "Samsung Network TV"
  }]
}
```

**Brand Detection Logic:**
```python
# Extracted from MAC vendor lookup
vendor = "Samsung Electronics Co.,Ltd"
→ brand = "Samsung"

vendor = "LG Electronics"
→ brand = "LG"

vendor = "Sony Corporation"
→ brand = "Sony"
```

## Unified Management API

### ManagedDevice Transformation

Virtual Controllers are transformed to match the `ManagedDevice` interface:

```python
# GET /api/v1/management/managed returns both:
- IR Controllers (positive IDs: 1, 2, 3, ...)
- Virtual Controllers (negative IDs: -10001, -10002, ...)

# Virtual Controller → ManagedDevice mapping:
{
  "id": -10001,                    # Negative ID
  "hostname": "nw-b85a97",         # Controller ID
  "device_type": "network_tv",     # Identifies as network TV
  "total_ir_ports": 1,             # Always 1 port
  "ir_ports": [                    # Virtual Device as IRPort
    {
      "port_number": 1,
      "port_id": "nw-b85a97-1",
      "connected_device_name": "Samsung TV Legacy (50)",
      "default_channel": "63",
      "tag_ids": [1, 2],
      "is_active": true,
      ...
    }
  ],
  "capabilities": {                # IR-like capabilities
    "ports": [{
      "port": 1,
      "brand": "Samsung",
      "description": "Samsung Network TV"
    }]
  }
}
```

### Edit Operations

Virtual Controllers use the same Edit modal as IR controllers:

**Update Endpoint:**
```bash
PUT /api/v1/management/managed/{device_id}
```

The endpoint detects Virtual Controllers by negative ID:
```python
if device_id < 0:
    # Handle Virtual Controller update
    vc_id = abs(device_id) - 10000
    # Update Virtual Controller and Virtual Devices
else:
    # Handle IR Controller update
```

**Supported Updates:**
- Controller name, location, notes
- Port 1 device name
- Default channel assignment
- Tag management
- Active/inactive status

## Hide/Unhide Devices

Users can hide discovered devices from the discovery list:

### Hide Device
```bash
POST /api/network-tv/hide/{mac_address}
```

Marks device as `is_hidden = True` in `network_scan_cache`

### Unhide Device
```bash
DELETE /api/network-tv/hide/{mac_address}
```

### List Hidden Devices
```bash
GET /api/network-tv/hidden
```

Returns all hidden devices for management

## Protocol Support

### Samsung TVs

**Legacy Protocol** (Port 55000):
- Older Samsung TVs (pre-2016)
- Base64 encoded commands
- No authentication required

**WebSocket Protocol** (Port 8001/8002):
- Modern Samsung TVs (2016+)
- WebSocket connection
- Token-based authentication

### LG TVs

**webOS Protocol** (Port 3000):
- LG Smart TVs with webOS
- WebSocket connection
- Pairing/handshake required

### Sony TVs

**IRCC Protocol** (Port 20060):
- Sony Bravia TVs
- REST API
- Pre-shared key authentication

## Frontend Integration

### Device List Display

Virtual Controllers appear alongside IR controllers:
```typescript
// Both types in same list
devices = [
  { id: 1, hostname: "ir-dc4516", device_type: "universal" },      // IR
  { id: 2, hostname: "ir-dcf89f", device_type: "universal" },      // IR
  { id: -10001, hostname: "nw-b85a97", device_type: "network_tv" }, // Virtual
  { id: -10002, hostname: "nw-9cf332", device_type: "network_tv" }  // Virtual
]
```

### Edit Modal

Same modal for both controller types:
- Reads `capabilities.ports` to determine which ports to show
- Virtual Controllers show only Port 1
- IR Controllers show Ports 1-5 (based on capabilities)
- All features work the same: default channels, tags, notes

### Control Page

Virtual Controllers appear in controller selection:
- Icon/badge indicates network TV vs IR
- Commands route to network protocol instead of IR

## Command Routing

### IR Controllers
```
User clicks "Power"
→ POST /api/v1/commands/{controller_id}/command
→ ESPHome GPIO IR blast
→ TV responds
```

### Virtual Controllers
```
User clicks "Power"
→ POST /api/network-tv/command/{controller_id}
→ Network protocol (Samsung/LG/Sony API)
→ TV responds over network
```

## Migration Scripts

### 1. Add is_hidden Column
```bash
python3 migrations/add_hidden_devices.py
```

Adds `is_hidden` column to `network_scan_cache`

### 2. Update Controller IDs
```bash
python3 migrations/update_virtual_controller_ids.py
```

Changes from `vc-samsung-electronics-co.,ltd-50` → `nw-b85a97`

### 3. Update to 1 Port Structure
```bash
python3 migrations/update_vc_to_1_port.py
```

Updates Virtual Controllers:
- Sets `total_ports = 1`
- Adds brand to `capabilities.ports`

## Best Practices

### Adoption
1. Always scan network first to get latest devices
2. Only adopt devices you intend to control
3. Use hide feature for devices you don't want to see

### Controller Management
1. Give Virtual Controllers descriptive names (e.g., "Main Bar Samsung TV")
2. Set default channels for frequently used channels
3. Use tags to organize devices by area/function

### Network Configuration
1. Assign static IPs to network TVs when possible
2. Ensure TVs are on same network as TapCommand backend
3. Check firewall rules allow control ports (55000, 8001, 3000, etc.)

### Troubleshooting
1. If TV not discovered: Check network connectivity and supported ports
2. If adoption fails: Verify TV protocol support and authentication
3. If control fails: Check TV is online and protocol is correct

## API Reference

### Network TV Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/network-tv/discover` | GET | List discoverable network TVs |
| `/api/network-tv/adopt` | POST | Adopt TV as Virtual Controller |
| `/api/network-tv/hide/{mac}` | POST | Hide device from discovery |
| `/api/network-tv/hide/{mac}` | DELETE | Unhide device |
| `/api/network-tv/hidden` | GET | List hidden devices |

### Management Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/management/managed` | GET | List all controllers (IR + Virtual) |
| `/api/v1/management/managed/{id}` | GET | Get specific controller |
| `/api/v1/management/managed/{id}` | PUT | Update controller (handles both types) |
| `/api/v1/management/managed/{id}` | DELETE | Delete controller |

## Example Workflow

### Complete Setup Flow

```bash
# 1. Discover network TVs
curl http://localhost:8000/api/network-tv/discover

# Response:
# [
#   {
#     "ip": "192.168.101.50",
#     "mac": "E4:E0:C5:B8:5A:97",
#     "vendor": "Samsung Electronics Co.,Ltd",
#     "device_type": "samsung_tv_legacy",
#     "protocol": "samsung_legacy",
#     "port": 55000
#   }
# ]

# 2. Adopt the TV
curl -X POST http://localhost:8000/api/network-tv/adopt \
  -H "Content-Type: application/json" \
  -d '{"ip": "192.168.101.50", "device_type": "samsung_tv_legacy"}'

# Response:
# {
#   "controller_id": "nw-b85a97",
#   "controller_name": "Samsung TV Legacy (50) Controller",
#   "virtual_device": {
#     "port_number": 1,
#     "device_name": "Samsung TV Legacy (50)"
#   }
# }

# 3. Get all managed devices
curl http://localhost:8000/api/v1/management/managed

# Response includes both IR and Virtual Controllers:
# [
#   {"id": 1, "hostname": "ir-dc4516", ...},        // IR Controller
#   {"id": -10001, "hostname": "nw-b85a97", ...}    // Virtual Controller
# ]

# 4. Update Virtual Controller (set default channel)
curl -X PUT http://localhost:8000/api/v1/management/managed/-10001 \
  -H "Content-Type: application/json" \
  -d '{
    "device_name": "Main Bar TV",
    "location": "Sports Bar",
    "ir_ports": [{
      "port_number": 1,
      "connected_device_name": "Main Bar Samsung TV",
      "default_channel": "63",
      "tag_ids": [1, 3],
      "is_active": true
    }]
  }'
```

## Future Enhancements

### Planned Features
- [ ] Multiple TVs per Virtual Controller (multi-zone)
- [ ] Bulk operations (turn on all TVs in zone)
- [ ] TV state monitoring (power, input, volume)
- [ ] Automatic TV discovery via SSDP/mDNS
- [ ] WebSocket events for real-time TV status
- [ ] TV scheduling (auto on/off by schedule)

### Protocol Expansion
- [ ] Roku support
- [ ] Apple TV support
- [ ] Chromecast support
- [ ] Fire TV support
- [ ] Generic HDMI-CEC support

## Related Documentation

- [Virtual Controller Adoption Flow](VIRTUAL_CONTROLLER_ADOPTION.md) - Original adoption system design
- [Network Discovery](../app/services/network_discovery.py) - Discovery service implementation
- [Device Management API](../app/api/device_management.py) - Unified management endpoints
