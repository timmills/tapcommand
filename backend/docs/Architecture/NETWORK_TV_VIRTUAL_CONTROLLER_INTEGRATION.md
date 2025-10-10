# Network TV Virtual Controller Integration Strategy

**Document Version:** 1.0
**Date:** October 4, 2025
**Status:** Architectural Design
**Related:** TV_NETWORK_CONTROL_RESEARCH.md

---

## Executive Summary

This document defines how network-controllable TVs integrate seamlessly into the existing TapCommand architecture by treating them as **virtual IR controllers with a single port**. This approach maintains API compatibility, preserves existing workflows, and makes network TVs first-class citizens in the device management system.

**Key Principle:** A network TV = Virtual ESP8266 controller with 1 port (port 1) that controls itself

---

## 🎯 Design Philosophy

### Core Concept

```
┌──────────────────────────┐         ┌──────────────────────────┐
│  Physical ESP8266        │         │  Virtual "Controller"    │
│  "ir-abc123"            │         │  "network-samsung-001"   │
│                          │         │                          │
│  • Port 1 → TV #1       │         │  • Port 1 → Self (TV)    │
│  • Port 2 → TV #2       │         │                          │
│  • Port 3 → Foxtel Box  │         │  Type: network_tv        │
│  • Port 4 → Unused      │         │  Protocol: websocket     │
│  • Port 5 → Unused      │         │  Brand: Samsung          │
│                          │         │                          │
│  Type: ir_controller     │         │  (Same Device model,     │
│  Protocol: esphome       │         │   different backend)     │
└──────────────────────────┘         └──────────────────────────┘
```

### Why This Approach?

✅ **Zero API changes** - Existing endpoints work unchanged
✅ **Zero frontend changes** - UI shows network TVs like any other port assignment
✅ **Unified command routing** - Same `/commands/{hostname}/send` endpoint
✅ **Consistent UX** - Users don't need to know if control is IR or network
✅ **Graceful migration** - Add network TVs without disrupting IR workflows
✅ **Future-proof** - Easy to add more network device types (Foxtel IP boxes, etc.)

---

## 🏗️ Schema Integration

### Device Table Extension (Minimal Changes)

```sql
-- Add device_subtype to distinguish between physical and virtual controllers
ALTER TABLE devices ADD COLUMN device_subtype VARCHAR(50) DEFAULT 'physical';
-- Values: 'physical' (ESP8266), 'virtual_network_tv', 'virtual_ip_stb'

-- Add network_protocol to specify how to communicate
ALTER TABLE devices ADD COLUMN network_protocol VARCHAR(50);
-- Values: NULL (for IR), 'samsung_ws', 'lg_webos', 'sony_http', 'philips_jointspace'

-- The capabilities JSON already supports different command sets
-- Example for network TV:
-- {
--   "outputs": 1,  -- Always 1 for network TVs
--   "protocols": ["samsung_ws"],
--   "supports_status_feedback": true,
--   "max_volume": 100,
--   "available_inputs": ["HDMI1", "HDMI2", "HDMI3", "TV"]
-- }
```

### Port Assignment Usage

```sql
-- Network TVs ALWAYS use port_number = 1
-- This simplifies logic and UI display

INSERT INTO port_assignments (
    device_hostname,
    port_number,      -- Always 1 for network TVs
    library_id,       -- Links to Samsung/LG/Sony library
    device_name,      -- "Main Bar Samsung TV"
    is_active,
    gpio_pin          -- NULL for network TVs (no physical GPIO)
) VALUES (
    'network-samsung-bar-main',
    1,
    (SELECT id FROM ir_libraries WHERE brand='Samsung' AND model='Q80T' LIMIT 1),
    'Main Bar Samsung TV',
    TRUE,
    NULL  -- No GPIO for network devices
);
```

### New Table: Network TV Credentials

```sql
-- Store network-specific authentication separately
CREATE TABLE network_tv_credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_hostname VARCHAR(255) UNIQUE NOT NULL,  -- FK to devices.hostname

    -- Connection details
    ip_address VARCHAR(45) NOT NULL,
    mac_address VARCHAR(17),
    port INTEGER DEFAULT 8001,

    -- Brand-specific auth
    protocol VARCHAR(50) NOT NULL,  -- 'samsung_ws', 'lg_webos', etc.
    auth_token_encrypted TEXT,      -- Encrypted pairing token
    auth_method VARCHAR(50),         -- 'token', 'psk', 'credentials'
    additional_auth_data JSON,       -- Brand-specific: PSK, username, etc.

    -- Status & monitoring
    last_successful_connection TIMESTAMP,
    last_connection_attempt TIMESTAMP,
    connection_failures INTEGER DEFAULT 0,
    is_reachable BOOLEAN DEFAULT FALSE,

    -- Pairing metadata
    paired_at TIMESTAMP,
    paired_by VARCHAR(255),  -- Admin who paired it
    pairing_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (device_hostname) REFERENCES devices(hostname) ON DELETE CASCADE
);

CREATE INDEX idx_network_tv_creds_ip ON network_tv_credentials(ip_address);
CREATE INDEX idx_network_tv_creds_protocol ON network_tv_credentials(protocol);
```

---

## 📡 Command Routing Architecture

### Unified Command Flow

```
User/Schedule → POST /api/v1/commands/{hostname}/send
                       ↓
                [Command Router]
                       ↓
              Check device.device_subtype
              /                          \
        'physical'                   'virtual_network_tv'
             ↓                                 ↓
    [ESPHome Client]                  [Network TV Client]
             ↓                                 ↓
    aioesphomeapi.send()          Samsung/LG/Sony controller
             ↓                                 ↓
       ESP8266 IR LED                    WebSocket/HTTP
             ↓                                 ↓
          TV (IR)                         TV (Network)
```

### Implementation: Smart Command Dispatcher

```python
# backend/app/services/command_dispatcher.py

from typing import Optional
from sqlalchemy.orm import Session
from .esphome_client import esphome_manager
from .network_tv_client import network_tv_manager  # New service
from ..models.device import Device
from ..models.network_tv import NetworkTVCredentials


class CommandDispatcher:
    """
    Unified command dispatcher that routes to appropriate backend
    based on device type without changing API surface
    """

    async def send_command(
        self,
        hostname: str,
        port: int,
        command: str,
        channel: Optional[str] = None,
        digit: Optional[int] = None,
        db: Session = None
    ) -> dict:
        """
        Send command to device - automatically routes to IR or network backend

        Args:
            hostname: Device hostname (e.g., "ir-abc123" or "network-samsung-001")
            port: Port number (always 1 for network TVs)
            command: Command name (e.g., "power", "vol_up", "channel")
            channel: Optional channel number for channel commands
            digit: Optional digit for digit commands
            db: Database session

        Returns:
            dict: {
                "success": bool,
                "method": str,  # 'esphome_ir', 'network_websocket', etc.
                "execution_time_ms": int,
                "verified": bool  # True if network control confirmed execution
            }
        """
        device = db.query(Device).filter(Device.hostname == hostname).first()
        if not device:
            return {
                "success": False,
                "error": f"Device {hostname} not found",
                "method": "none"
            }

        # Route based on device subtype
        if device.device_subtype == 'physical':
            return await self._send_esphome_command(
                device, port, command, channel, digit
            )

        elif device.device_subtype == 'virtual_network_tv':
            return await self._send_network_tv_command(
                device, command, channel, digit, db
            )

        else:
            return {
                "success": False,
                "error": f"Unknown device subtype: {device.device_subtype}",
                "method": "none"
            }

    async def _send_esphome_command(
        self,
        device: Device,
        port: int,
        command: str,
        channel: Optional[str],
        digit: Optional[int]
    ) -> dict:
        """Send command via ESPHome (existing IR logic)"""
        import time
        start_time = time.time()

        try:
            # Existing ESPHome logic (unchanged)
            result = await esphome_manager.send_command(
                hostname=device.hostname,
                ip_address=device.ip_address,
                command=command,
                box=port,
                channel=channel,
                digit=digit
            )

            execution_time = int((time.time() - start_time) * 1000)

            return {
                "success": result.get("success", False),
                "method": "esphome_ir",
                "execution_time_ms": execution_time,
                "verified": False  # IR is always unverified
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "method": "esphome_ir"
            }

    async def _send_network_tv_command(
        self,
        device: Device,
        command: str,
        channel: Optional[str],
        digit: Optional[int],
        db: Session
    ) -> dict:
        """Send command via network protocol (new logic)"""
        import time
        start_time = time.time()

        try:
            # Get network credentials
            creds = db.query(NetworkTVCredentials).filter(
                NetworkTVCredentials.device_hostname == device.hostname
            ).first()

            if not creds:
                return {
                    "success": False,
                    "error": "Network TV not paired (no credentials found)",
                    "method": "network_none"
                }

            # Route to brand-specific controller
            result = await network_tv_manager.send_command(
                protocol=creds.protocol,
                ip_address=creds.ip_address,
                port=creds.port,
                credentials=creds,
                command=command,
                channel=channel,
                digit=digit
            )

            execution_time = int((time.time() - start_time) * 1000)

            return {
                "success": result.get("success", False),
                "method": f"network_{creds.protocol}",
                "execution_time_ms": execution_time,
                "verified": result.get("verified", False),  # Network can verify!
                "status_data": result.get("status", {})  # Current TV state
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "method": "network_error"
            }


# Singleton instance
command_dispatcher = CommandDispatcher()
```

### Update Existing Command Router

```python
# backend/app/routers/commands.py (MINIMAL CHANGES)

from ..services.command_dispatcher import command_dispatcher  # New import

# ... existing code ...

async def send_command_direct(
    hostname: str,
    ip_address: str,  # This might not be used for network TVs (use credentials table instead)
    command: str,
    box: int,
    channel: Optional[str],
    digit: Optional[int],
    api_key: str,
    db: Session
) -> Dict[str, Any]:
    """
    Send command directly to device

    NOW ROUTES AUTOMATICALLY:
    - Physical ESP8266 → ESPHome API
    - Virtual Network TV → Network protocol
    """

    result = await command_dispatcher.send_command(
        hostname=hostname,
        port=box,
        command=command,
        channel=channel,
        digit=digit,
        db=db
    )

    return result
```

**Key Insight:** By abstracting the dispatch logic, existing endpoints work unchanged. The router doesn't need to know if it's IR or network - it just passes the command to the dispatcher!

---

## 🖥️ Frontend Integration

### Zero Changes Required

The frontend already works with the abstraction of:
- Device (hostname)
- Port (1-5 for physical, always 1 for network TVs)
- Command (power, vol_up, etc.)

**Example existing frontend code:**
```typescript
// This code works for BOTH IR and network TVs with ZERO changes!
const sendCommand = async (hostname: string, port: number, command: string) => {
  await fetch(`/api/v1/commands/${hostname}/send`, {
    method: 'POST',
    body: JSON.stringify({
      port: port,
      command: command
    })
  });
};

// Usage:
await sendCommand('ir-abc123', 2, 'power');  // Physical ESP, port 2
await sendCommand('network-samsung-001', 1, 'power');  // Network TV, port 1
```

### UI Enhancements (Optional, Future)

**Device Discovery Page** - Show network TVs alongside ESP8266 devices:
```
Discovered Devices
├── ESP8266 Controllers
│   ├── ir-abc123 (192.168.1.50) - 5 ports
│   └── ir-def456 (192.168.1.51) - 5 ports
└── Network TVs
    ├── Samsung Q80T (192.168.1.100) - Unpaired
    ├── LG C1 OLED (192.168.1.101) - Paired ✓
    └── Sony X90J (192.168.1.102) - Unpaired
```

**Port Assignment View** - Network TVs show as single port:
```
Device: network-samsung-bar-main
Type: Samsung Smart TV (Network Control)
Status: Online ✓

Port Assignments:
┌──────────────────────────────────────────┐
│ Port 1: Main Bar TV (Self)               │
│ ├─ Brand: Samsung                        │
│ ├─ Model: Q80T                           │
│ ├─ Control: WebSocket (Verified ✓)      │
│ ├─ Status: Power ON, Volume 45          │
│ └─ Last Command: 2 minutes ago           │
└──────────────────────────────────────────┘

(No ports 2-5 shown for network devices)
```

**Command History** - Shows method used:
```
Recent Commands - network-samsung-bar-main
├── 10:30 AM - Power ON - Network (Samsung WS) ✓ Verified
├── 10:28 AM - Volume Up x5 - Network (Samsung WS) ✓
├── 10:25 AM - Input HDMI1 - Network (Samsung WS) ✓
└── 10:20 AM - Power OFF - Network (Samsung WS) ✓ Verified
```

---

## 🔧 Device Lifecycle Management

### Discovery → Pairing → Assignment → Control

#### 1. Discovery (New Endpoint)

```python
# POST /api/v1/network-tv/discover
# Returns list of network TVs found on local network

{
  "discovered": [
    {
      "ip_address": "192.168.1.100",
      "mac_address": "AA:BB:CC:DD:EE:FF",
      "brand": "Samsung",
      "model": "QN55Q80T",
      "protocol": "samsung_ws",
      "hostname_suggestion": "network-samsung-bar-main",
      "already_paired": false
    },
    {
      "ip_address": "192.168.1.101",
      "mac_address": "11:22:33:44:55:66",
      "brand": "LG",
      "model": "OLED55C1PUB",
      "protocol": "lg_webos",
      "hostname_suggestion": "network-lg-lounge",
      "already_paired": false
    }
  ]
}
```

#### 2. Pairing (New Endpoint)

```python
# POST /api/v1/network-tv/pair
# Initiates pairing flow for a discovered TV

Request:
{
  "ip_address": "192.168.1.100",
  "protocol": "samsung_ws",
  "friendly_name": "Main Bar Samsung TV",
  "hostname": "network-samsung-bar-main"  # User can customize
}

Response (Success - Token returned):
{
  "success": true,
  "message": "Pairing successful. User accepted on TV.",
  "hostname": "network-samsung-bar-main",
  "token": "abc123def456...",  # Encrypted before storage
  "next_step": "assign_library"
}

Response (Pending - User must accept on TV):
{
  "success": false,
  "pending": true,
  "message": "Please accept pairing request on TV screen within 30 seconds",
  "retry_in_seconds": 5
}
```

#### 3. Device Creation (Automatic after pairing)

```python
# Automatically create virtual device entry

INSERT INTO devices (
    hostname,
    mac_address,
    ip_address,
    friendly_name,
    device_type,
    device_subtype,
    network_protocol,
    is_online,
    capabilities
) VALUES (
    'network-samsung-bar-main',
    'AA:BB:CC:DD:EE:FF',
    '192.168.1.100',
    'Main Bar Samsung TV',
    'universal',  -- Same as ESP8266 devices
    'virtual_network_tv',  -- NEW: Distinguishes from physical
    'samsung_ws',  -- NEW: Network protocol
    TRUE,
    JSON('{"outputs": 1, "protocols": ["samsung_ws"], "supports_status_feedback": true}')
);

INSERT INTO network_tv_credentials (
    device_hostname,
    ip_address,
    mac_address,
    port,
    protocol,
    auth_token_encrypted,
    auth_method,
    paired_at
) VALUES (
    'network-samsung-bar-main',
    '192.168.1.100',
    'AA:BB:CC:DD:EE:FF',
    8001,
    'samsung_ws',
    'ENCRYPTED_TOKEN_HERE',
    'token',
    CURRENT_TIMESTAMP
);
```

#### 4. Library Assignment (Uses existing PortAssignment table!)

```python
# Assign Samsung Q80T library to port 1 (standard flow, works unchanged)

POST /api/v1/port-assignments
{
  "device_hostname": "network-samsung-bar-main",
  "port_number": 1,  # Always 1 for network TVs
  "library_id": 1234,  # Samsung Q80T library from ir_libraries
  "device_name": "Main Bar TV"
}

# Now commands can be sent!
POST /api/v1/commands/network-samsung-bar-main/send
{
  "port": 1,
  "command": "power"
}
```

---

## 📊 Database Examples

### Complete Example: Samsung TV Setup

```sql
-- 1. Device entry (virtual controller)
INSERT INTO devices (hostname, mac_address, ip_address, friendly_name, device_type, device_subtype, network_protocol, is_online, capabilities)
VALUES (
    'network-samsung-bar-main',
    'AA:BB:CC:DD:EE:FF',
    '192.168.1.100',
    'Main Bar Samsung TV',
    'universal',
    'virtual_network_tv',
    'samsung_ws',
    1,
    '{"outputs": 1, "protocols": ["samsung_ws"], "supports_status_feedback": true, "available_inputs": ["HDMI1", "HDMI2", "HDMI3", "TV"], "supports_app_launch": true}'
);

-- 2. Network credentials (pairing info)
INSERT INTO network_tv_credentials (device_hostname, ip_address, mac_address, port, protocol, auth_token_encrypted, auth_method, paired_at, is_reachable)
VALUES (
    'network-samsung-bar-main',
    '192.168.1.100',
    'AA:BB:CC:DD:EE:FF',
    8001,
    'samsung_ws',
    'ENC:gAAAAABhPqK5vN8xQ...',  -- Fernet encrypted token
    'token',
    '2025-10-04 10:30:00',
    1
);

-- 3. Port assignment (port 1 = the TV itself)
INSERT INTO port_assignments (device_hostname, port_number, library_id, device_name, is_active, gpio_pin)
VALUES (
    'network-samsung-bar-main',
    1,
    (SELECT id FROM ir_libraries WHERE brand='Samsung' AND model='Q80T' LIMIT 1),
    'Main Bar TV',
    1,
    NULL  -- No GPIO for network devices
);

-- 4. Now this works via existing API!
-- POST /api/v1/commands/network-samsung-bar-main/send
-- {"port": 1, "command": "power"}
-- → Dispatcher detects device_subtype='virtual_network_tv'
-- → Routes to Samsung WebSocket controller
-- → Sends power command
-- → Returns success + verified status
```

### Mixed Environment Example

```sql
-- Typical venue setup: 2 ESP8266 controllers + 2 network TVs

-- Physical ESP8266 #1
INSERT INTO devices VALUES ('ir-abc123', ..., 'physical', NULL, ...);
INSERT INTO port_assignments VALUES ('ir-abc123', 1, lib_foxtel, ...);
INSERT INTO port_assignments VALUES ('ir-abc123', 2, lib_samsung, ...);
INSERT INTO port_assignments VALUES ('ir-abc123', 3, lib_lg, ...);

-- Physical ESP8266 #2
INSERT INTO devices VALUES ('ir-def456', ..., 'physical', NULL, ...);
INSERT INTO port_assignments VALUES ('ir-def456', 1, lib_foxtel, ...);
INSERT INTO port_assignments VALUES ('ir-def456', 2, lib_sony, ...);

-- Virtual Network TV #1 (Samsung)
INSERT INTO devices VALUES ('network-samsung-001', ..., 'virtual_network_tv', 'samsung_ws', ...);
INSERT INTO network_tv_credentials VALUES ('network-samsung-001', ...);
INSERT INTO port_assignments VALUES ('network-samsung-001', 1, lib_samsung, ...);

-- Virtual Network TV #2 (LG)
INSERT INTO devices VALUES ('network-lg-001', ..., 'virtual_network_tv', 'lg_webos', ...);
INSERT INTO network_tv_credentials VALUES ('network-lg-001', ...);
INSERT INTO port_assignments VALUES ('network-lg-001', 1, lib_lg, ...);

-- All 4 devices appear in device list
-- All can receive commands via same API
-- Dispatcher routes automatically based on device_subtype
```

---

## 🔄 Migration Strategy

### Phase 1: Add Virtual Device Support (No Breaking Changes)

**Schema Updates:**
```sql
-- Add new columns with defaults (safe, non-breaking)
ALTER TABLE devices ADD COLUMN device_subtype VARCHAR(50) DEFAULT 'physical';
ALTER TABLE devices ADD COLUMN network_protocol VARCHAR(50) DEFAULT NULL;

-- Create new table (doesn't affect existing data)
CREATE TABLE network_tv_credentials ( ... );

-- Update existing ESP8266 devices to have explicit subtype
UPDATE devices SET device_subtype = 'physical' WHERE device_type = 'universal';
```

**Code Updates:**
```python
# Add command_dispatcher.py (new file, no changes to existing code)
# Update commands.py to use dispatcher (1 line change in send_command_direct)
# Add network_tv_client.py (new service)
# Add network TV endpoints (new router, doesn't affect existing routes)
```

**Testing:**
```bash
# Verify existing ESP8266 commands still work
curl -X POST http://localhost:8000/api/v1/commands/ir-abc123/send \
  -d '{"port": 1, "command": "power"}'

# Should return: {"success": true, "method": "esphome_ir", ...}
```

### Phase 2: Add Network TV Discovery & Pairing

**New Endpoints (additive only):**
```
POST /api/v1/network-tv/discover
POST /api/v1/network-tv/pair
GET /api/v1/network-tv/status/{hostname}
```

**Install Dependencies:**
```bash
pip install samsungtvws aiowebostv bravia-tv ssdpy
```

### Phase 3: Pilot Test with 1-2 Network TVs

**Add first network TV:**
1. Discover Samsung TV via new endpoint
2. Pair and create virtual device
3. Assign library to port 1
4. Send commands via existing API
5. Verify routing works correctly

### Phase 4: Rollout to All Network-Capable TVs

**Gradually replace IR control:**
- TVs with network capability → Pair as network devices
- Set-top boxes / older TVs → Keep on ESP8266 IR ports
- Hybrid approach for reliability

---

## 🎮 Command Mapping

### Standard Commands (Work for Both IR and Network)

| Command | IR Behavior | Network Behavior |
|---------|-------------|------------------|
| `power` | Send IR power toggle | Send WebSocket power toggle + verify state |
| `vol_up` | Send IR vol+ signal | Send network vol+ OR set absolute volume |
| `vol_down` | Send IR vol- signal | Send network vol- OR set absolute volume |
| `mute` | Send IR mute toggle | Send network mute toggle |
| `ch_up` | Send IR ch+ signal | Send network ch+ key |
| `ch_down` | Send IR ch- signal | Send network ch- key |
| `channel` | Send digit sequence | Send digit sequence (or direct tune if supported) |
| `input` | Send IR input/source key | Send direct input selection (HDMI1, HDMI2, etc.) |

### Network-Exclusive Commands (New Capabilities)

```python
# These commands only work for network TVs (gracefully fail for IR)

POST /api/v1/commands/{hostname}/send
{
  "port": 1,
  "command": "launch_app",
  "app_id": "com.netflix.ninja"  # Direct to Netflix app
}

POST /api/v1/commands/{hostname}/send
{
  "port": 1,
  "command": "set_volume_absolute",
  "volume": 50  # Set to exact volume level
}

POST /api/v1/commands/{hostname}/send
{
  "port": 1,
  "command": "set_input_direct",
  "input": "HDMI 2"  # Direct input selection (no cycling)
}

# Status query (network only)
GET /api/v1/commands/{hostname}/status/1
{
  "power_state": true,
  "volume": 45,
  "muted": false,
  "current_input": "HDMI 1",
  "current_app": "com.netflix.ninja",
  "last_updated": "2025-10-04T10:35:00Z"
}
```

---

## 🔍 Discovery Flow (Detailed)

### SSDP Discovery for Samsung TVs

```python
# backend/app/services/network_tv/discovery/samsung.py

import asyncio
from ssdpy import SSDPClient
from typing import List, Dict

async def discover_samsung_tvs(timeout: int = 10) -> List[Dict]:
    """Discover Samsung TVs on local network using SSDP"""

    discovered = []

    try:
        client = SSDPClient()

        # Search for Samsung RemoteControlReceiver
        devices = client.m_search(
            "urn:samsung.com:device:RemoteControlReceiver:1",
            timeout=timeout
        )

        for device in devices:
            # Extract info from SSDP response
            location = device.get('location', '')
            ip = extract_ip_from_url(location)

            if ip:
                tv_info = {
                    'ip_address': ip,
                    'mac_address': None,  # Fetch via ARP or separate API call
                    'brand': 'Samsung',
                    'protocol': 'samsung_ws',
                    'port': 8001,
                    'discovery_method': 'ssdp',
                    'raw_response': device
                }

                # Try to get model info from TV's REST API
                try:
                    model_info = await fetch_samsung_model_info(ip)
                    tv_info['model'] = model_info.get('model', 'Unknown')
                    tv_info['friendly_name'] = model_info.get('name', f'Samsung TV ({ip})')
                except:
                    tv_info['model'] = 'Unknown'
                    tv_info['friendly_name'] = f'Samsung TV ({ip})'

                discovered.append(tv_info)

    except Exception as e:
        logger.error(f"Samsung discovery failed: {e}")

    return discovered


async def fetch_samsung_model_info(ip: str) -> Dict:
    """Fetch model info from Samsung TV REST API"""
    import aiohttp

    url = f"http://{ip}:8001/api/v2/"

    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=5) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    'model': data.get('device', {}).get('model', 'Unknown'),
                    'name': data.get('device', {}).get('name', 'Samsung TV'),
                    'firmware': data.get('device', {}).get('version', 'Unknown')
                }

    return {}
```

### Unified Discovery Endpoint

```python
# POST /api/v1/network-tv/discover

{
  "brands": ["samsung", "lg", "sony"],  # Optional: filter by brand
  "timeout": 10  # Discovery timeout in seconds
}

Response:
{
  "discovered": [
    {
      "ip_address": "192.168.1.100",
      "mac_address": "AA:BB:CC:DD:EE:FF",
      "brand": "Samsung",
      "model": "QN55Q80T",
      "protocol": "samsung_ws",
      "port": 8001,
      "friendly_name": "Samsung Q80T",
      "hostname_suggestion": "network-samsung-001",
      "already_paired": false,
      "can_pair_now": true
    },
    {
      "ip_address": "192.168.1.101",
      "mac_address": "11:22:33:44:55:66",
      "brand": "LG",
      "model": "OLED55C1PUB",
      "protocol": "lg_webos",
      "port": 3001,
      "friendly_name": "LG C1 OLED",
      "hostname_suggestion": "network-lg-001",
      "already_paired": true,
      "existing_hostname": "network-lg-lounge"
    }
  ],
  "discovery_time_ms": 8432,
  "brands_searched": ["samsung", "lg", "sony"]
}
```

---

## 📈 Status Monitoring & Health Checks

### Background Monitoring Service

```python
# backend/app/services/network_tv_monitor.py

import asyncio
from typing import List
from datetime import datetime
from sqlalchemy.orm import Session
from ..models.device import Device
from ..models.network_tv import NetworkTVCredentials
from .network_tv_client import network_tv_manager

class NetworkTVMonitor:
    """Background service to poll network TV status"""

    def __init__(self, interval_seconds: int = 60):
        self.interval = interval_seconds
        self.running = False

    async def start(self, db: Session):
        """Start monitoring loop"""
        self.running = True

        while self.running:
            try:
                await self._poll_all_network_tvs(db)
            except Exception as e:
                logger.error(f"Monitor poll failed: {e}")

            await asyncio.sleep(self.interval)

    async def _poll_all_network_tvs(self, db: Session):
        """Poll status of all network TVs"""

        # Get all virtual network TV devices
        network_devices = db.query(Device).filter(
            Device.device_subtype == 'virtual_network_tv'
        ).all()

        for device in network_devices:
            await self._poll_device(device, db)

    async def _poll_device(self, device: Device, db: Session):
        """Poll single network TV"""

        creds = db.query(NetworkTVCredentials).filter(
            NetworkTVCredentials.device_hostname == device.hostname
        ).first()

        if not creds:
            return

        try:
            # Query TV status
            status = await network_tv_manager.get_status(
                protocol=creds.protocol,
                ip_address=creds.ip_address,
                port=creds.port,
                credentials=creds
            )

            if status:
                # Update device online status
                device.is_online = True
                device.last_seen = datetime.now()

                # Update credentials reachability
                creds.is_reachable = True
                creds.last_successful_connection = datetime.now()
                creds.connection_failures = 0

                # Store current status in capabilities JSON
                device.capabilities = {
                    **device.capabilities,
                    "last_status": {
                        "power_state": status.power_state,
                        "volume": status.volume,
                        "muted": status.muted,
                        "current_input": status.current_input,
                        "current_app": status.current_app,
                        "timestamp": datetime.now().isoformat()
                    }
                }

                db.commit()

        except Exception as e:
            logger.warning(f"Failed to poll {device.hostname}: {e}")

            # Update failure tracking
            creds.connection_failures += 1
            creds.last_connection_attempt = datetime.now()

            if creds.connection_failures >= 3:
                device.is_online = False
                creds.is_reachable = False

            db.commit()


# Start monitor on backend startup
# backend/app/main.py

from .services.network_tv_monitor import NetworkTVMonitor

@app.on_event("startup")
async def startup_network_monitor():
    monitor = NetworkTVMonitor(interval_seconds=60)
    asyncio.create_task(monitor.start(get_db()))
```

### Status API Endpoint

```python
# GET /api/v1/network-tv/status/{hostname}

Response:
{
  "hostname": "network-samsung-bar-main",
  "is_online": true,
  "is_reachable": true,
  "last_successful_connection": "2025-10-04T10:35:00Z",
  "connection_failures": 0,

  "current_status": {
    "power_state": true,
    "volume": 45,
    "muted": false,
    "current_input": "HDMI 1",
    "current_app": null,
    "firmware_version": "1560.5"
  },

  "monitoring": {
    "poll_interval_seconds": 60,
    "last_poll": "2025-10-04T10:35:00Z",
    "next_poll_estimated": "2025-10-04T10:36:00Z"
  }
}
```

---

## 🚀 Implementation Checklist

### Week 1: Foundation
- [ ] Add `device_subtype` and `network_protocol` columns to devices table
- [ ] Create `network_tv_credentials` table
- [ ] Implement `CommandDispatcher` service
- [ ] Update `send_command_direct()` to use dispatcher
- [ ] Test that existing ESP8266 commands still work (regression testing)

### Week 2: Samsung Pilot
- [ ] Install `samsungtvws` library
- [ ] Implement Samsung discovery
- [ ] Implement Samsung pairing endpoint
- [ ] Create first virtual device (manual SQL for testing)
- [ ] Send power command via network
- [ ] Verify command routing works

### Week 3: Network TV Client Service
- [ ] Implement `NetworkTVManager` service
- [ ] Add Samsung controller
- [ ] Add LG controller (optional)
- [ ] Add status querying
- [ ] Test mixed environment (ESP8266 + network TVs)

### Week 4: API & UI Integration
- [ ] Add discovery endpoints
- [ ] Add pairing endpoints
- [ ] Add status monitoring service
- [ ] Frontend: Show network TVs in device list
- [ ] Frontend: Pairing wizard UI

---

## 📝 Summary

### What Changes?

**Schema:**
- 2 new columns in `devices` table
- 1 new table `network_tv_credentials`

**Backend Services:**
- New: `CommandDispatcher` (routes to IR or network)
- New: `NetworkTVManager` (manages brand controllers)
- New: `NetworkTVMonitor` (background status polling)
- Modified: `send_command_direct()` (1 line to use dispatcher)

**API:**
- New endpoints: `/network-tv/discover`, `/network-tv/pair`, `/network-tv/status`
- Existing endpoints: UNCHANGED (same input/output)

**Frontend:**
- Optional: Discovery UI, pairing wizard
- Existing command UI: UNCHANGED (works automatically)

### What Stays the Same?

✅ All existing API endpoints
✅ Command request/response format
✅ Port assignment flow
✅ Device management workflow
✅ Command queue system
✅ Scheduling system

### Key Benefits

✅ **Zero breaking changes** - IR devices work exactly as before
✅ **API compatibility** - Same POST `/commands/{hostname}/send` for all devices
✅ **Unified UX** - Users don't need to know IR vs network
✅ **Gradual migration** - Add network TVs one at a time
✅ **Future-proof** - Easy to add more network device types

---

**Next Steps:** Review this integration strategy and confirm approach before implementing Phase 1 (foundation schema updates).
