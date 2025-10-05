# Virtual Controller Adoption System

## Overview

The Virtual Controller Adoption System allows network-discovered TVs and streaming devices to be adopted into the SmartVenue control system. When a device is adopted, a Virtual Controller is automatically created and the device is mapped to port 1 of that controller.

## Architecture

### Database Models

#### VirtualController
Software representation of a TV/device controller for network-based devices.

**Table:** `virtual_controllers`

**Columns:**
- `id` - Primary key
- `controller_id` - Unique identifier (e.g., "vc-samsung-50")
- `controller_name` - Display name (e.g., "Living Room TV Controller")
- `controller_type` - Type: "network_tv", "streaming_device", "generic"
- `protocol` - Control protocol (e.g., "samsung_legacy", "lg_webos", "roku_ecp")
- `venue_name` - Venue name (optional)
- `location` - Location within venue (optional)
- `total_ports` - Number of ports (default: 5)
- `capabilities` - JSON object with capabilities
- `is_active` - Active status
- `is_online` - Online status
- `last_seen` - Last seen timestamp
- `notes` - Additional notes
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

#### VirtualDevice
Represents a device mapped to a specific port on a Virtual Controller.

**Table:** `virtual_devices`

**Columns:**
- `id` - Primary key
- `controller_id` - Foreign key to virtual_controllers
- `port_number` - Port number (1-5)
- `port_id` - Unique port identifier (e.g., "vc-samsung-50-1")
- `device_name` - Device display name
- `device_type` - Device type (from network discovery)
- `ip_address` - Device IP address
- `mac_address` - Device MAC address
- `port` - Control port number (55000, 8001, etc.)
- `protocol` - Control protocol
- `connection_config` - JSON with protocol-specific config
- `default_channel` - Default channel (optional)
- `capabilities` - JSON with device capabilities
- `is_active` - Active status
- `is_online` - Online status
- `last_seen` - Last seen timestamp
- `tag_ids` - JSON array of tag IDs
- `installation_notes` - Notes about installation
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

## Adoption Workflow

### Step 1: Network Discovery
Devices are discovered through the network scan system:
```bash
POST /api/network/scan/trigger
```

### Step 2: View Discovered TVs
Get list of adoptable devices:
```bash
GET /api/network-tv/discover
```

Response includes:
- `adoptable` status: "ready", "needs_config", or "unlikely"
- `confidence_score`: 0-100 likelihood of being a TV
- `confidence_reason`: Explanation of score

### Step 3: Adopt Device
Adopt a device by IP address:
```bash
POST /api/network-tv/adopt/192.168.101.50
```

This endpoint:
1. Retrieves device from network scan cache
2. Generates unique controller ID
3. Creates Virtual Controller
4. Creates Virtual Device on port 1
5. Marks device as adopted in scan cache

**Example Response:**
```json
{
  "success": true,
  "message": "Device 192.168.101.50 (Samsung Electronics) has been adopted and mapped to Virtual Controller",
  "virtual_controller": {
    "id": 1,
    "controller_id": "vc-samsung-50",
    "controller_name": "Samsung Tv Legacy (50) Controller",
    "controller_type": "network_tv",
    "protocol": "samsung_legacy",
    "total_ports": 5,
    "is_online": true
  },
  "virtual_device": {
    "id": 1,
    "port_number": 1,
    "port_id": "vc-samsung-50-1",
    "device_name": "Samsung Tv Legacy (50)",
    "ip_address": "192.168.101.50",
    "mac_address": "E4:E0:C5:B8:5A:97",
    "protocol": "samsung_legacy",
    "device_type": "samsung_tv_legacy"
  },
  "scan_cache_device": {
    "ip": "192.168.101.50",
    "mac": "E4:E0:C5:B8:5A:97",
    "vendor": "Samsung Electronics",
    "hostname": "samsung-la40d550",
    "device_type": "samsung_tv_legacy",
    "is_adopted": true
  }
}
```

### Step 4: Un-adopt Device (Optional)
Remove adoption and delete Virtual Controller:
```bash
DELETE /api/network-tv/adopt/192.168.101.50
```

This endpoint:
1. Finds Virtual Device by IP
2. Deletes Virtual Controller (cascade deletes Virtual Device)
3. Marks device as not adopted in scan cache

## Virtual Controller Management API

### List All Virtual Controllers
```bash
GET /api/virtual-controllers/
```

Query params:
- `controller_type`: Filter by type
- `is_active`: Filter by active status

### Get Specific Virtual Controller
```bash
GET /api/virtual-controllers/vc-samsung-50
```

Returns controller with all its devices.

### List Controller Devices
```bash
GET /api/virtual-controllers/vc-samsung-50/devices
```

### Get Device on Specific Port
```bash
GET /api/virtual-controllers/vc-samsung-50/port/1
```

### Delete Virtual Controller
```bash
DELETE /api/virtual-controllers/vc-samsung-50
```

Cascade deletes all virtual devices.

### List All Virtual Devices
```bash
GET /api/virtual-controllers/devices/all
```

Query params:
- `device_type`: Filter by device type
- `is_online`: Filter by online status

### Get Statistics
```bash
GET /api/virtual-controllers/stats/summary
```

Returns:
- Total controllers by type
- Active/online counts
- Device counts by type

## Supported Device Types

### Network TVs
- **Samsung Legacy** (D/E/F series 2011-2015)
  - Protocol: `samsung_legacy`
  - Port: 55000
  - Control: samsungctl library

- **Samsung Tizen** (2016+)
  - Protocol: `samsung_websocket`
  - Port: 8001, 8002 (SSL)
  - Control: WebSocket API

- **LG webOS**
  - Protocol: `lg_webos`
  - Port: 3000, 3001 (SSL)
  - Control: WebSocket API

- **Sony Bravia**
  - Protocol: `sony_bravia`
  - Port: 80, 50001, 50002
  - Control: IRCC HTTP API

- **Hisense VIDAA**
  - Protocol: `hisense_vidaa`
  - Port: 36669, 3000
  - Control: VIDAA API

- **Philips Android TV**
  - Protocol: `philips_jointspace`
  - Port: 1925, 1926 (SSL)
  - Control: JointSpace API

- **TCL/Roku**
  - Protocol: `roku_ecp`
  - Port: 8060
  - Control: External Control Protocol

- **Vizio SmartCast**
  - Protocol: `vizio_smartcast`
  - Port: 7345, 9000
  - Control: SmartCast API

### Streaming Devices
- **Apple TV**
  - Protocol: `apple_airplay`
  - Port: 3689, 7000

- **Google Chromecast**
  - Protocol: `chromecast`
  - Port: 8008, 8009

- **Amazon Fire TV**
  - Protocol: `fire_tv`
  - Port: 5555 (ADB)

## Controller ID Generation

Controller IDs are generated using the pattern:
```
vc-{vendor}-{last-octet}
```

Examples:
- `vc-samsung-50` - Samsung device at .50
- `vc-lg-101` - LG device at .101
- `vc-sony-25` - Sony device at .25

If a conflict occurs, a counter is appended:
- `vc-samsung-50-1`
- `vc-samsung-50-2`

## Port Assignment

By default:
- Port 1: Adopted device (TV/streaming device)
- Ports 2-5: Available for future expansion

Each Virtual Controller supports 5 ports, mirroring the physical IR controller design.

## Integration Points

### Network Discovery System
- Virtual Controller adoption reads from `network_scan_cache` table
- Confidence scoring determines adoptability
- Device type detection determines protocol

### Command Routing
Future integration will route commands through Virtual Controllers:
1. Command sent to Virtual Controller
2. Virtual Controller looks up device on port 1
3. Device connection config provides IP, port, protocol
4. Command executed via appropriate protocol library

### Device Control
Each Virtual Device stores `connection_config`:
```json
{
  "ip": "192.168.101.50",
  "port": 55000,
  "protocol": "samsung_legacy",
  "vendor": "Samsung Electronics",
  "model": "LA40D550"
}
```

## Database Migration

Run migration to create tables:
```bash
python3 migrations/add_virtual_controllers.py
```

Tables created:
- `virtual_controllers`
- `virtual_devices`

Indexes created:
- `idx_virtual_controllers_controller_id`
- `idx_virtual_devices_controller_id`
- `idx_virtual_devices_port_id`

## API Testing Examples

### 1. Discover TVs
```bash
curl http://localhost:8000/api/network-tv/discover
```

### 2. Adopt Samsung TV
```bash
curl -X POST http://localhost:8000/api/network-tv/adopt/192.168.101.50
```

### 3. List Virtual Controllers
```bash
curl http://localhost:8000/api/virtual-controllers/
```

### 4. Get Controller Details
```bash
curl http://localhost:8000/api/virtual-controllers/vc-samsung-50
```

### 5. Get Device on Port 1
```bash
curl http://localhost:8000/api/virtual-controllers/vc-samsung-50/port/1
```

### 6. Un-adopt Device
```bash
curl -X DELETE http://localhost:8000/api/network-tv/adopt/192.168.101.50
```

## Next Steps

1. **Frontend Integration**
   - Build TV discovery UI
   - Add adoption button
   - Show Virtual Controller status

2. **Command Routing**
   - Implement protocol handlers
   - Route commands through Virtual Controllers
   - Support multi-device control

3. **Advanced Features**
   - Add devices to ports 2-5
   - Support device grouping
   - Implement macros across multiple devices

## Files Modified/Created

### Models
- `app/models/virtual_controller.py` - Virtual Controller and Virtual Device models

### Routers
- `app/routers/virtual_controllers.py` - Virtual Controller management API
- `app/routers/network_tv.py` - Enhanced adoption endpoints

### Database
- `app/db/database.py` - Added Virtual Controller table creation
- `migrations/add_virtual_controllers.py` - Migration script

### Main Application
- `app/main.py` - Registered virtual_controllers router

## Troubleshooting

### Issue: Adoption fails with "Device not found"
- Run network scan first: `POST /api/network/scan/trigger`
- Verify device in scan cache: `GET /api/network/scan-cache`

### Issue: Controller ID conflict
- System auto-increments: `vc-samsung-50-1`, `vc-samsung-50-2`
- No manual intervention needed

### Issue: Device shows as "needs_config"
- TV remote control access disabled
- Enable "External Device Manager" in TV settings
- Re-run network scan to detect open ports

### Issue: Protocol not detected
- Check device_type_guess in scan cache
- Verify port scanning detected control ports
- May need to add device type to `device_scanner_config.py`
