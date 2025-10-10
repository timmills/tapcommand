# TV Network Control Integration - Comprehensive Research & Implementation Plan

**Document Version:** 1.0
**Date:** October 4, 2025
**Status:** Research Complete - Awaiting Pilot Decision

---

## Executive Summary

Based on extensive research, **all major TV brands supported in TapCommand have network control capabilities** that could complement or replace IR control. This presents a significant opportunity to enhance the TapCommand system with bidirectional feedback, improved reliability, and advanced monitoring.

**Key Finding:** Modern smart TVs (2015+) universally support some form of local network control via HTTP, WebSocket, or MQTT protocols.

**Recommendation:** Implement hybrid IR + Network control starting with Samsung TV pilot (2-week implementation).

---

## 🔍 Research Findings: TV Brand Network Control Capabilities

### Tier 1: Excellent Network Control Support (Recommended Priority)

#### Samsung (TizenOS 2016+)
- **Protocol:** WebSocket
- **Port:** 8001 (WS), 8002 (WSS)
- **Authentication:** Pairing flow with on-screen PIN → persistent token
- **Python Library:** `samsungtvws` (actively maintained, last update Dec 2024)
- **Status Feedback:** ✅ Full (power, volume, current app, input source)
- **Special Features:**
  - Art mode control for The Frame TVs
  - Low power network mode in 2024 models (stays connected in standby)
  - Application launching (Netflix, YouTube, HDMI inputs by name)
- **Discovery:** SSDP (UPnP), responds to `urn:samsung.com:device:RemoteControlReceiver:1`
- **Documentation:** https://developer.samsung.com/smarttv/
- **Notes:** Most mature API, excellent for commercial installations

#### LG (webOS 3.0+)
- **Protocol:** WebSocket (WSS required for newer firmware)
- **Port:** 3000 (WS), 3001 (WSS)
- **Authentication:** On-screen prompt → store token in client key file
- **Python Libraries:**
  - `PyWebOSTV` (community maintained)
  - `aiowebostv` (Home Assistant team, async)
  - `bscpylgtv` (optimized fork)
- **Status Feedback:** ✅ Full (power, volume, app, input, foreground app info)
- **Special Features:**
  - Toast message display on TV
  - Application management (launch, close, list installed)
  - Input control (keyboard simulation, cursor movement)
  - Media control (play, pause, seek)
- **Discovery:** mDNS broadcast as `lgsmarttv.lan`
- **Configuration:** Enable "LG Connect Apps" in TV network settings
- **Documentation:** https://webostv.developer.lge.com/
- **Notes:** Best ecosystem, multiple maintained libraries, very reliable

#### Sony Bravia (2013+)
- **Protocol:** HTTP/REST + IRCC-IP (SOAP)
- **Port:** 80 (HTTP API), various for IRCC endpoints
- **Authentication:** Pre-Shared Key (PSK) configured in TV settings
- **Python Libraries:**
  - `bravia-tv` (HTTP API wrapper)
  - `braviaproapi` (Professional Display API, limited model support)
  - `py-sony-bravia-remote` (undocumented HTTP API)
- **Status Feedback:** ✅ Good (power, input, volume via REST API)
- **Special Features:**
  - IRCC protocol sends IR commands over IP (hybrid approach)
  - Wake-on-LAN support (in normal mode, not suspended)
  - Professional displays have more complete REST API
- **Discovery:** UPnP/SSDP
- **Authentication Header:** `X-Auth-PSK: {pre_shared_key}`
- **Documentation:** https://pro-bravia.sony.net/develop/integrate/
- **Notes:** Pro displays recommended for commercial use, consumer models have variable API support

#### Philips (Android TV 2015+, JointSpace v6)
- **Protocol:** HTTP (JointSpace API)
- **Port:** 1925 (non-Android), 1926 (Android TV)
- **Authentication:** HMAC signature using 88-character pairing key
- **Python Library:** `pylips` (reverse-engineered API with MQTT support)
- **Status Feedback:** ✅ Good (power, volume, input, Ambilight state)
- **Special Features:**
  - Ambilight control (color, brightness, effects)
  - Android TV app launching
  - Remote key simulation via POST to `/6/input/key`
- **Discovery:** SSDP/UPnP
- **Documentation:** http://jointspace.sourceforge.net/ (outdated, community docs better)
- **Notes:** API version varies by model year, v6 most common for Android TV

---

### Tier 2: Good Network Control (Secondary Priority)

#### Vizio (SmartCast 2016+)
- **Protocol:** HTTP/REST (undocumented)
- **Port:** 9000
- **Authentication:** PIN displayed on TV → auth token (reusable)
- **Libraries:**
  - `smartcast` (Rust)
  - `vizio-smart-cast` (Node.js, last updated 4 years ago)
- **Status Feedback:** ⚠️ Limited (basic state info)
- **Discovery:** SSDP query for `urn:schemas-kinoma-com:device:shell:1`
- **API Portal:** https://api.developer.external.plat.vizio.com/ (focused on app dev, not device control)
- **Notes:** No official documentation, community reverse-engineered, API described as "awkward and complicated"

#### TCL (Roku TV 2014+)
- **Protocol:** HTTP (External Control Protocol - ECP)
- **Port:** 8060
- **Authentication:** None
- **Libraries:**
  - `rokujs` (Node.js)
  - Simple curl commands work
- **Status Feedback:** ⚠️ Limited (basic device info)
- **Discovery:** SSDP (Simple Service Discovery Protocol)
- **Documentation:** https://developer.roku.com/docs/developer-program/dev-tools/external-control-api.md
- **Known Issues (2024):**
  - Some TCL Roku TVs drop off network after ~15 minutes in standby
  - May not respond to API via Ethernet until manually powered on with remote
  - WiFi reconnects after TV turned on, but power-on via API unreliable
- **Notes:** Simple REST API but power-on reliability concerns for hospitality use

#### Panasonic Viera (2012+ models)
- **Protocol:** SOAP (older models), REST (2018+ encrypted)
- **Port:** 55000
- **Authentication:** Network settings must enable "TV Remote App"
- **Libraries:**
  - `node-panasonic-viera` (Node.js, supports old and new models)
  - `viera-control` (REST API wrapper)
- **Status Feedback:** ⚠️ Limited (basic commands only)
- **Setup Requirements:**
  - Menu → Network → TV Remote App Settings
  - Enable: TV Remote, Powered On by Apps, Networked Standby
- **Power-On Support:**
  - 2012-2013 models (VT50/GT50/WT50/VT60/ZT60/WT60) support WoL via Ethernet (US only)
  - Older models: network interface unavailable in standby
- **Custom Commands:** NRC_HDMI1-ONOFF, NRC_NETFLIX-ONOFF, etc.
- **Notes:** Older protocol, limited WoL support, better for newer models only

#### Hisense (Vidaa OS)
- **Protocol:** MQTT
- **Port:** 36669
- **Authentication:**
  - Username: `hisenseservice`
  - Password: `multimqttservice`
  - Some models require client certificates
- **Python Library:** `hisensetv` (MQTT broker wrapper)
- **Status Feedback:** ⚠️ Limited (keypress simulation, basic state)
- **Discovery:** Direct connection to TV's IP on port 36669
- **Notes:**
  - Built-in MQTT broker accessible on local network
  - Vidaa 6+ updates have locked down access on some models
  - Newer firmware may restrict MQTT entirely
  - Works like IR remote over MQTT (send keypresses)

---

### Tier 3: Limited/Undocumented (Use IR as Primary)

#### Sharp Aquos
- **Protocol:** TCP/Text (proprietary)
- **Port:** 10002
- **Authentication:** Username/password (configured in TV settings)
- **Libraries:**
  - `sharp_aquos_rc` (Python)
  - `sharp-aquos-remote-control` (Node.js)
- **Status Feedback:** ⚠️ Limited
- **Documentation:** Pages 8-3 through 8-8 in Sharp user manual (IP Control section)
- **Notes:** Older protocol, community-maintained libraries only, no official API

#### Toshiba (Vestel Chassis)
- **Protocol:** HTTP/XML (undocumented)
- **Port:** 56789
- **Endpoint:** `/apps/SmartCenter`
- **Authentication:** None
- **Method:** HTTP POST with XML-formatted remote key codes
- **Libraries:** `toshiba-stv-ip-remote` (GitHub community project)
- **Alternative:** ADB (Android Debug Bridge) for Android TV models
- **Status Feedback:** ⚠️ Minimal
- **Notes:** Largely undocumented, only works on specific chassis types, unreliable

---

## 📊 Key Advantages of Network Control Over IR

### 1. Bidirectional Communication

**IR Control (Current):**
```
TapCommand → ESP8266 → IR LED → TV
           (one-way, blind)
```
- No confirmation command was received
- No way to verify TV actually changed state
- Can't detect manual changes by staff
- Impossible to read current settings

**Network Control:**
```
TapCommand ←→ TV (WebSocket/HTTP)
           (two-way, verified)
```
- Immediate success/failure feedback
- Read current state: power, volume, input, app
- Detect manual changes (staff used physical remote)
- Query capabilities and settings

**Real-World Benefits:**
- Know if "Power On" actually worked vs TV was already on
- Detect if staff manually changed input from HDMI1 to TV tuner
- Read current volume level before adjusting (vs blind IR increments)
- Verify scheduled commands executed successfully

### 2. Reliability Improvements

| Aspect | IR Control | Network Control |
|--------|------------|-----------------|
| **Line of Sight** | Required, physical alignment critical | Not required, works through walls |
| **Latency** | 200-500ms per command sequence | 50-200ms direct connection |
| **Verification** | None (blind transmission) | Success/failure response |
| **Concurrent Commands** | Sequential only (IR conflicts) | Multiple simultaneous connections |
| **Power State** | Must be on to receive (most models) | Low-power network mode (2024+ TVs) |
| **Distance Limitation** | 5-10m max IR range | Anywhere on network |
| **Environmental Interference** | Sunlight, fluorescent lights | Network congestion only |

**Failure Modes:**
- **IR:** LED misalignment, obstructions, IR receiver failure → silent failure
- **Network:** Connection timeout → retry logic, fallback to IR

### 3. Advanced Features Enabled

#### Direct Input Selection
**IR:** Send 15+ "Input" button presses, hope we count correctly
**Network:** `setInput("HDMI 2")` or `launchApp("Netflix")`

#### Volume Synchronization
**IR:** Send 10x "Volume Up" blind increments
**Network:** `getCurrentVolume()` → `setVolume(50)` absolute

#### Application Control
**IR:** Navigate menus with arrow keys (slow, unreliable)
**Network:** `launchApp("com.netflix.ninja")` direct launch

#### Picture Profiles
**IR:** Not possible
**Network:** Read/set picture mode, brightness, contrast (brand-dependent)

#### Diagnostics & Monitoring
**IR:** Not possible
**Network:**
- Model number, firmware version
- Uptime, last boot time
- Network connection quality
- Temperature sensors (some models)
- Error logs (professional displays)

### 4. Operational Intelligence

**Current Blind Control:**
```
User: "Power on all TVs"
System: Sends IR power commands
Result: ¯\_(ツ)_/¯ (hope it worked)
```

**Network Control with Feedback:**
```
User: "Power on all TVs"
System: Sends network power commands
System: Polls each TV for status
Result: "5/6 TVs powered on successfully. Bar TV #3 not responding (network issue detected)"
```

**Use Cases:**
- **Daily health check:** Verify all TVs reachable before opening
- **Post-command verification:** Confirm scheduled input change executed
- **Staff activity monitoring:** Alert if manual changes override automation
- **Predictive maintenance:** Detect TVs losing network connectivity (early failure warning)
- **Usage analytics:** Track actual viewing patterns (which inputs used most)

---

## 🏗️ Proposed Architecture

### Hybrid Control Strategy (Recommended)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TapCommand Backend (FastAPI)                     │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │         Unified Device Control Abstraction Layer             │  │
│  │                                                               │  │
│  │  • Single API for all control methods                        │  │
│  │  • Automatic method selection (network preferred)            │  │
│  │  • Fallback logic (network fail → IR backup)                │  │
│  │  • Command verification & retry                              │  │
│  └────────────┬─────────────────────────────┬───────────────────┘  │
│               │                             │                       │
│      ┌────────▼──────────┐         ┌────────▼────────────────┐     │
│      │  IR Control       │         │  Network Control        │     │
│      │  Service          │         │  Service                │     │
│      │                   │         │                         │     │
│      │ • ESPHome API     │         │ • Samsung WebSocket     │     │
│      │ • Flipper-IRDB    │         │ • LG WebOS              │     │
│      │ • Reliable        │         │ • Sony HTTP             │     │
│      │   fallback        │         │ • Philips JointSpace    │     │
│      │                   │         │ • SSDP Discovery        │     │
│      │                   │         │ • Token Management      │     │
│      │                   │         │ • Status Polling        │     │
│      └───────────────────┘         └─────────────────────────┘     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                        │                           │
           ─────────────┴───────────────────────────┴─────────────
           │                                               │
      ┌────▼──────┐                                ┌───────▼────────┐
      │  ESP8266  │                                │  Samsung TV    │
      │  IR       │──────IR Pulses────────────▶    │  (TizenOS)     │
      │  Blaster  │                                │                │
      │           │◀──────Network Status───────────│  • WebSocket   │
      └───────────┘       (if available)           │  • Port 8001   │
                                                   │  • Bidirectional│
                                                   └────────────────┘
```

### Device Type Taxonomy

```
Device
├── IR-Only Device (legacy TVs, set-top boxes)
│   └── Control: IR blaster only
├── Network-Only Device (modern smart TVs without IR ports)
│   └── Control: Network API only
└── Hybrid Device (smart TVs with both IR receiver + network)
    ├── Primary: Network control (faster, verified)
    └── Fallback: IR control (reliable backup)
```

### Control Flow with Intelligent Fallback

```python
# Pseudo-code for smart device selection
async def send_command(device_id: int, command: Command) -> CommandResult:
    device = get_device(device_id)

    # 1. Try network control first (if available)
    if device.supports_network_control:
        try:
            result = await network_control_service.send(device, command)

            # Verify command executed (if brand supports status feedback)
            if result.success and device.supports_status_feedback:
                await asyncio.sleep(0.5)  # Brief delay for TV to update
                status = await network_control_service.get_status(device)

                if verify_command_executed(command, status):
                    log_success(f"Network command verified: {command}")
                    return CommandResult(success=True, verified=True, method="network")
                else:
                    log_warning(f"Network command sent but not verified: {command}")
                    # Continue to IR fallback

            elif result.success:
                log_success(f"Network command sent (no verification available): {command}")
                return CommandResult(success=True, verified=False, method="network")

        except NetworkTimeout as e:
            log_warning(f"Network timeout for {device.name}, falling back to IR: {e}")
        except ConnectionRefused as e:
            log_warning(f"Network connection refused for {device.name}, falling back to IR: {e}")
        except Exception as e:
            log_error(f"Unexpected network error for {device.name}: {e}")

    # 2. Fallback to IR control (always available)
    if device.supports_ir_control:
        result = await ir_control_service.send(device, command)
        return CommandResult(
            success=result.success,
            verified=False,  # IR is always unverified
            method="ir"
        )

    # 3. No control method available
    raise NoControlMethodAvailable(f"Device {device.name} has no control method configured")


def verify_command_executed(command: Command, status: DeviceStatus) -> bool:
    """Verify TV state matches expected command result"""
    if command.type == "power_on":
        return status.power_state == True
    elif command.type == "power_off":
        return status.power_state == False
    elif command.type == "set_volume":
        return abs(status.volume - command.target_volume) <= 2  # Allow small variance
    elif command.type == "set_input":
        return status.current_input == command.target_input
    # Add more verification logic as needed
    return False  # Unknown command type, can't verify
```

---

## 🎯 Implementation Plan

### Phase 1: Discovery & Database Schema (Week 1-2)

**Objectives:**
- Add network TV discovery capabilities
- Extend database schema to support dual control methods
- Implement SSDP/mDNS discovery services

#### Database Schema Changes

```sql
-- Extend Device table to support network control
ALTER TABLE devices ADD COLUMN control_methods JSON DEFAULT '{"ir": false, "network": false}';
-- Example: {"ir": true, "network": true, "preferred": "network"}

ALTER TABLE devices ADD COLUMN network_config JSON;
-- Example: {
--   "brand": "Samsung",
--   "model": "QN55Q80T",
--   "protocol": "websocket",
--   "protocol_version": "v2",
--   "ip_address": "192.168.1.100",
--   "mac_address": "AA:BB:CC:DD:EE:FF",
--   "port": 8001,
--   "auth_token_encrypted": "base64_encrypted_token_here",
--   "last_paired": "2025-10-04T10:30:00Z",
--   "supports_wol": true,
--   "capabilities": ["power", "volume", "input", "apps", "status"],
--   "api_version": "TizenOS 6.0"
-- }

ALTER TABLE devices ADD COLUMN last_network_status JSON;
-- Example: {
--   "timestamp": "2025-10-04T10:35:00Z",
--   "reachable": true,
--   "power_state": true,
--   "volume": 45,
--   "muted": false,
--   "current_input": "HDMI 1",
--   "current_app": "com.netflix.ninja",
--   "firmware_version": "1560.5"
-- }

-- New table for network TV discovery log
CREATE TABLE network_tv_discovery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address TEXT NOT NULL,
    mac_address TEXT,
    hostname TEXT,
    brand TEXT,
    model TEXT,
    discovery_method TEXT NOT NULL,  -- "ssdp", "mdns", "manual", "network_scan"
    discovery_details JSON,  -- Raw discovery response data
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    paired BOOLEAN DEFAULT FALSE,
    device_id INTEGER,  -- Foreign key to devices table once paired
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE SET NULL
);

CREATE INDEX idx_network_discovery_ip ON network_tv_discovery(ip_address);
CREATE INDEX idx_network_discovery_mac ON network_tv_discovery(mac_address);
CREATE INDEX idx_network_discovery_paired ON network_tv_discovery(paired);

-- New table for network control command log
CREATE TABLE network_command_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    command_type TEXT NOT NULL,  -- "power", "volume", "input", "app_launch", "status_query"
    command_details JSON,
    method TEXT NOT NULL,  -- "network", "ir", "hybrid"
    network_protocol TEXT,  -- "websocket", "http", "mqtt" (if network method used)
    success BOOLEAN,
    verified BOOLEAN,  -- Did we confirm command executed via status check?
    error_message TEXT,
    execution_time_ms INTEGER,
    fallback_used BOOLEAN DEFAULT FALSE,  -- Did we fall back from network to IR?
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

CREATE INDEX idx_network_cmd_log_device ON network_command_log(device_id);
CREATE INDEX idx_network_cmd_log_timestamp ON network_command_log(timestamp);
CREATE INDEX idx_network_cmd_log_success ON network_command_log(success);
```

#### Discovery Service Implementation

```python
# backend/app/services/network_tv/discovery.py

import asyncio
import socket
from typing import List, Dict, Optional
from ssdpy import SSDPClient
from zeroconf import ServiceBrowser, Zeroconf, ServiceListener
import logging

logger = logging.getLogger(__name__)


class NetworkTVDiscoveryService:
    """Discover network-controllable TVs using SSDP and mDNS"""

    def __init__(self):
        self.discovered_devices: List[Dict] = []

    async def discover_all(self, timeout: int = 10) -> List[Dict]:
        """Run all discovery methods concurrently"""
        results = await asyncio.gather(
            self.discover_ssdp(timeout),
            self.discover_mdns(timeout),
            return_exceptions=True
        )

        # Combine and deduplicate results
        all_devices = []
        seen_ips = set()

        for result_set in results:
            if isinstance(result_set, Exception):
                logger.error(f"Discovery method failed: {result_set}")
                continue

            for device in result_set:
                if device['ip_address'] not in seen_ips:
                    all_devices.append(device)
                    seen_ips.add(device['ip_address'])

        return all_devices

    async def discover_ssdp(self, timeout: int = 10) -> List[Dict]:
        """Discover TVs using SSDP (UPnP)"""
        discovered = []

        # Search for multiple device types
        search_targets = [
            "ssdp:all",  # All devices
            "urn:samsung.com:device:RemoteControlReceiver:1",  # Samsung TVs
            "urn:lge:device:tv:1",  # LG TVs (older)
            "urn:schemas-upnp-org:device:tvdevice:1",  # Generic TV
            "urn:schemas-kinoma-com:device:shell:1",  # Vizio SmartCast
        ]

        for target in search_targets:
            try:
                client = SSDPClient()
                devices = client.m_search(target, timeout=timeout)

                for device in devices:
                    tv_info = {
                        'ip_address': self._extract_ip_from_location(device.get('location', '')),
                        'discovery_method': 'ssdp',
                        'brand': self._detect_brand_from_ssdp(device),
                        'discovery_details': device
                    }

                    if tv_info['ip_address']:
                        discovered.append(tv_info)

            except Exception as e:
                logger.warning(f"SSDP search failed for {target}: {e}")

        return discovered

    async def discover_mdns(self, timeout: int = 10) -> List[Dict]:
        """Discover TVs using mDNS (Zeroconf)"""
        discovered = []

        class TVListener(ServiceListener):
            def __init__(self, device_list):
                self.devices = device_list

            def add_service(self, zeroconf, service_type, name):
                info = zeroconf.get_service_info(service_type, name)
                if info:
                    # LG TVs broadcast as lgsmarttv.lan
                    if 'lg' in name.lower() or 'webos' in name.lower():
                        device = {
                            'ip_address': socket.inet_ntoa(info.addresses[0]),
                            'hostname': name,
                            'discovery_method': 'mdns',
                            'brand': 'LG',
                            'discovery_details': {
                                'service_type': service_type,
                                'name': name,
                                'port': info.port
                            }
                        }
                        self.devices.append(device)

        zeroconf = Zeroconf()
        listener = TVListener(discovered)

        # Search for common TV service types
        services = [
            "_androidtvremote2._tcp.local.",  # Android TV
            "_googlecast._tcp.local.",  # Chromecast/Google TV
            "_webos-tv._tcp.local.",  # LG webOS (if advertised)
        ]

        browsers = [ServiceBrowser(zeroconf, service, listener) for service in services]

        # Wait for discovery
        await asyncio.sleep(timeout)

        # Cleanup
        for browser in browsers:
            browser.cancel()
        zeroconf.close()

        return discovered

    async def scan_subnet(self, subnet: str = "192.168.1.0/24", ports: List[int] = None) -> List[Dict]:
        """Network scan for TVs on specific ports (fallback method)"""
        if ports is None:
            ports = [
                8001,  # Samsung WebSocket
                8060,  # Roku
                1925,  # Philips
                3000,  # LG WebOS
                9000,  # Vizio SmartCast
            ]

        # Implementation would scan subnet for open ports
        # This is a slower fallback method
        # Return format same as other discovery methods
        pass

    def _extract_ip_from_location(self, location: str) -> Optional[str]:
        """Extract IP address from SSDP location URL"""
        try:
            # location format: http://192.168.1.100:8080/description.xml
            import re
            match = re.search(r'http://([0-9.]+)', location)
            return match.group(1) if match else None
        except:
            return None

    def _detect_brand_from_ssdp(self, ssdp_response: Dict) -> Optional[str]:
        """Detect TV brand from SSDP response"""
        response_str = str(ssdp_response).lower()

        if 'samsung' in response_str:
            return 'Samsung'
        elif 'lg' in response_str or 'webos' in response_str:
            return 'LG'
        elif 'sony' in response_str or 'bravia' in response_str:
            return 'Sony'
        elif 'philips' in response_str:
            return 'Philips'
        elif 'vizio' in response_str or 'kinoma' in response_str:
            return 'Vizio'
        elif 'roku' in response_str or 'tcl' in response_str:
            return 'TCL/Roku'

        return None
```

---

### Phase 2: Network Control Services (Week 3-4)

**Objectives:**
- Implement brand-specific network control services
- Create unified control interface
- Add token/credential management

#### Base Controller Interface

```python
# backend/app/services/network_tv/base.py

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class ControlMethod(Enum):
    NETWORK = "network"
    IR = "ir"
    HYBRID = "hybrid"


@dataclass
class CommandResult:
    success: bool
    verified: bool  # Was execution confirmed via status check?
    method: ControlMethod
    execution_time_ms: int
    error_message: Optional[str] = None
    response_data: Optional[Dict] = None


@dataclass
class DeviceStatus:
    power_state: bool
    volume: Optional[int] = None
    muted: Optional[bool] = None
    current_input: Optional[str] = None
    current_app: Optional[str] = None
    firmware_version: Optional[str] = None
    additional_info: Optional[Dict] = None


class BaseNetworkTVController(ABC):
    """Abstract base class for network TV controllers"""

    def __init__(self, ip_address: str, port: int, **kwargs):
        self.ip_address = ip_address
        self.port = port
        self.config = kwargs
        self._client = None

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to TV"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to TV"""
        pass

    @abstractmethod
    async def pair(self) -> Dict[str, Any]:
        """Initiate pairing flow, return credentials"""
        pass

    @abstractmethod
    async def send_power(self, state: bool) -> CommandResult:
        """Send power on/off command"""
        pass

    @abstractmethod
    async def send_volume(self, level: int) -> CommandResult:
        """Set absolute volume level (0-100)"""
        pass

    @abstractmethod
    async def send_volume_up(self, steps: int = 1) -> CommandResult:
        """Increase volume by steps"""
        pass

    @abstractmethod
    async def send_volume_down(self, steps: int = 1) -> CommandResult:
        """Decrease volume by steps"""
        pass

    @abstractmethod
    async def send_mute(self, state: bool) -> CommandResult:
        """Mute/unmute audio"""
        pass

    @abstractmethod
    async def send_input(self, input_source: str) -> CommandResult:
        """Change input source (HDMI1, HDMI2, TV, etc.)"""
        pass

    @abstractmethod
    async def send_key(self, key: str) -> CommandResult:
        """Send remote control key press"""
        pass

    @abstractmethod
    async def get_status(self) -> DeviceStatus:
        """Query current device status"""
        pass

    @abstractmethod
    async def list_inputs(self) -> List[str]:
        """Get list of available input sources"""
        pass

    # Optional methods (not all brands support)
    async def launch_app(self, app_id: str) -> CommandResult:
        """Launch application by ID"""
        raise NotImplementedError("App launching not supported by this brand")

    async def list_apps(self) -> List[Dict[str, str]]:
        """Get list of installed applications"""
        raise NotImplementedError("App listing not supported by this brand")

    async def get_device_info(self) -> Dict[str, Any]:
        """Get device model, firmware, capabilities"""
        raise NotImplementedError("Device info not supported by this brand")
```

#### Samsung WebSocket Controller

```python
# backend/app/services/network_tv/samsung_controller.py

import asyncio
import logging
from typing import Optional, Dict, Any, List
from samsungtvws import SamsungTVWS
from .base import BaseNetworkTVController, CommandResult, DeviceStatus, ControlMethod

logger = logging.getLogger(__name__)


class SamsungTVController(BaseNetworkTVController):
    """Samsung Tizen TV WebSocket controller"""

    def __init__(self, ip_address: str, port: int = 8001, token: Optional[str] = None, **kwargs):
        super().__init__(ip_address, port, **kwargs)
        self.token = token
        self.name = kwargs.get('name', 'TapCommand Control')

    async def connect(self) -> bool:
        """Establish WebSocket connection to Samsung TV"""
        try:
            self._client = SamsungTVWS(
                host=self.ip_address,
                port=self.port,
                token=self.token,
                name=self.name,
                timeout=5
            )

            # Test connection
            await asyncio.to_thread(self._client.open)
            logger.info(f"Connected to Samsung TV at {self.ip_address}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Samsung TV at {self.ip_address}: {e}")
            return False

    async def disconnect(self) -> None:
        """Close WebSocket connection"""
        if self._client:
            try:
                await asyncio.to_thread(self._client.close)
            except:
                pass

    async def pair(self) -> Dict[str, Any]:
        """
        Initiate pairing flow
        Returns token that should be saved for future connections
        """
        try:
            # Connection attempt triggers on-screen PIN prompt
            temp_client = SamsungTVWS(
                host=self.ip_address,
                port=self.port,
                name=self.name
            )

            # User must accept on TV, library handles token exchange
            await asyncio.to_thread(temp_client.open)
            token = temp_client.token

            return {
                'success': True,
                'token': token,
                'message': 'Pairing successful. Save token for future use.'
            }

        except Exception as e:
            logger.error(f"Samsung TV pairing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Pairing failed. Ensure TV is on and user accepted prompt.'
            }

    async def send_power(self, state: bool) -> CommandResult:
        """Send power command"""
        start_time = asyncio.get_event_loop().time()

        try:
            if not self._client:
                await self.connect()

            # Samsung doesn't have separate on/off, just toggle
            # We need to check current state first
            current_status = await self.get_status()

            if current_status.power_state == state:
                # Already in desired state
                return CommandResult(
                    success=True,
                    verified=True,
                    method=ControlMethod.NETWORK,
                    execution_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000),
                    response_data={'message': 'Already in desired power state'}
                )

            # Send power key to toggle
            await asyncio.to_thread(self._client.send_key, 'KEY_POWER')

            # Verify state changed
            await asyncio.sleep(1)
            new_status = await self.get_status()

            execution_time = int((asyncio.get_event_loop().time() - start_time) * 1000)

            return CommandResult(
                success=True,
                verified=(new_status.power_state == state),
                method=ControlMethod.NETWORK,
                execution_time_ms=execution_time
            )

        except Exception as e:
            logger.error(f"Samsung power command failed: {e}")
            return CommandResult(
                success=False,
                verified=False,
                method=ControlMethod.NETWORK,
                execution_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000),
                error_message=str(e)
            )

    async def send_volume(self, level: int) -> CommandResult:
        """Set absolute volume level"""
        # Samsung doesn't support absolute volume via WebSocket
        # We'd need to get current volume and send +/- steps
        # For now, raise NotImplementedError
        raise NotImplementedError("Absolute volume not supported, use send_volume_up/down")

    async def send_volume_up(self, steps: int = 1) -> CommandResult:
        """Increase volume"""
        start_time = asyncio.get_event_loop().time()

        try:
            if not self._client:
                await self.connect()

            for _ in range(steps):
                await asyncio.to_thread(self._client.send_key, 'KEY_VOLUP')
                await asyncio.sleep(0.1)  # Brief delay between presses

            return CommandResult(
                success=True,
                verified=False,  # Can't verify volume level
                method=ControlMethod.NETWORK,
                execution_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000)
            )

        except Exception as e:
            return CommandResult(
                success=False,
                verified=False,
                method=ControlMethod.NETWORK,
                execution_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000),
                error_message=str(e)
            )

    async def send_volume_down(self, steps: int = 1) -> CommandResult:
        """Decrease volume"""
        start_time = asyncio.get_event_loop().time()

        try:
            if not self._client:
                await self.connect()

            for _ in range(steps):
                await asyncio.to_thread(self._client.send_key, 'KEY_VOLDOWN')
                await asyncio.sleep(0.1)

            return CommandResult(
                success=True,
                verified=False,
                method=ControlMethod.NETWORK,
                execution_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000)
            )

        except Exception as e:
            return CommandResult(
                success=False,
                verified=False,
                method=ControlMethod.NETWORK,
                execution_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000),
                error_message=str(e)
            )

    async def send_mute(self, state: bool) -> CommandResult:
        """Toggle mute"""
        start_time = asyncio.get_event_loop().time()

        try:
            if not self._client:
                await self.connect()

            await asyncio.to_thread(self._client.send_key, 'KEY_MUTE')

            return CommandResult(
                success=True,
                verified=False,
                method=ControlMethod.NETWORK,
                execution_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000)
            )

        except Exception as e:
            return CommandResult(
                success=False,
                verified=False,
                method=ControlMethod.NETWORK,
                execution_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000),
                error_message=str(e)
            )

    async def send_input(self, input_source: str) -> CommandResult:
        """Change input source"""
        start_time = asyncio.get_event_loop().time()

        # Map friendly names to Samsung keys
        input_map = {
            'HDMI1': 'KEY_HDMI1',
            'HDMI2': 'KEY_HDMI2',
            'HDMI3': 'KEY_HDMI3',
            'HDMI4': 'KEY_HDMI4',
            'TV': 'KEY_TV',
        }

        try:
            if not self._client:
                await self.connect()

            key = input_map.get(input_source.upper())
            if not key:
                # Fallback to source button
                key = 'KEY_SOURCE'

            await asyncio.to_thread(self._client.send_key, key)

            return CommandResult(
                success=True,
                verified=False,
                method=ControlMethod.NETWORK,
                execution_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000)
            )

        except Exception as e:
            return CommandResult(
                success=False,
                verified=False,
                method=ControlMethod.NETWORK,
                execution_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000),
                error_message=str(e)
            )

    async def send_key(self, key: str) -> CommandResult:
        """Send arbitrary remote key"""
        start_time = asyncio.get_event_loop().time()

        try:
            if not self._client:
                await self.connect()

            await asyncio.to_thread(self._client.send_key, key)

            return CommandResult(
                success=True,
                verified=False,
                method=ControlMethod.NETWORK,
                execution_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000)
            )

        except Exception as e:
            return CommandResult(
                success=False,
                verified=False,
                method=ControlMethod.NETWORK,
                execution_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000),
                error_message=str(e)
            )

    async def get_status(self) -> DeviceStatus:
        """Get current TV status"""
        try:
            if not self._client:
                await self.connect()

            # Get device info (includes power state)
            info = await asyncio.to_thread(self._client.rest_device_info)

            return DeviceStatus(
                power_state=(info.get('device', {}).get('PowerState') == 'on'),
                additional_info=info
            )

        except Exception as e:
            logger.error(f"Failed to get Samsung TV status: {e}")
            # Return unknown state
            return DeviceStatus(power_state=False)

    async def list_inputs(self) -> List[str]:
        """Get list of available inputs"""
        # Samsung doesn't provide API to list inputs dynamically
        # Return standard HDMI inputs
        return ['HDMI1', 'HDMI2', 'HDMI3', 'HDMI4', 'TV']

    async def launch_app(self, app_id: str) -> CommandResult:
        """Launch application"""
        start_time = asyncio.get_event_loop().time()

        try:
            if not self._client:
                await self.connect()

            await asyncio.to_thread(self._client.run_app, app_id)

            return CommandResult(
                success=True,
                verified=False,
                method=ControlMethod.NETWORK,
                execution_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000)
            )

        except Exception as e:
            return CommandResult(
                success=False,
                verified=False,
                method=ControlMethod.NETWORK,
                execution_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000),
                error_message=str(e)
            )

    async def list_apps(self) -> List[Dict[str, str]]:
        """Get installed apps"""
        try:
            if not self._client:
                await self.connect()

            apps = await asyncio.to_thread(self._client.app_list)
            return apps

        except Exception as e:
            logger.error(f"Failed to list Samsung TV apps: {e}")
            return []
```

---

### Phase 3: Pairing & Authentication UI (Week 5)

[Frontend implementation details would go here - React components for discovery, pairing wizard, device management]

---

### Phase 4: Status Monitoring & Feedback (Week 6)

[Background polling service implementation]

---

### Phase 5: Intelligent Command Routing (Week 7)

[Hybrid control strategy implementation]

---

### Phase 6: Advanced Features (Week 8+)

[Conditional logic, analytics, health monitoring]

---

## ⚡ Quick Win: Samsung TV Pilot (Week 1-2)

### Recommended Starting Point

**Objective:** Validate network control concept with minimal risk

**Target:** Samsung TVs only (most mature API)

**Why Samsung First:**
1. Most actively maintained library (`samsungtvws` updated Dec 2024)
2. Clear pairing flow (on-screen PIN)
3. Good documentation and community support
4. Low-power network mode in 2024 models (always reachable)
5. Supports status feedback

### Pilot Implementation Steps

**Day 1-2: Environment Setup**
```bash
# Install Samsung library
cd backend
source ../venv/bin/activate
pip install samsungtvws

# Add to requirements.txt
echo "samsungtvws>=2.6.0" >> requirements.txt
```

**Day 3-4: Discovery Service**
```python
# Create basic discovery endpoint
POST /api/v1/network-control/discover/samsung
# Returns: List of Samsung TVs found on network

# Test with curl
curl -X POST http://localhost:8000/api/v1/network-control/discover/samsung
```

**Day 5-6: Pairing Flow**
```python
# Create pairing endpoint
POST /api/v1/network-control/samsung/pair
{
  "ip": "192.168.1.100",
  "name": "Bar Main TV"
}

# User accepts on TV → returns token
# Save encrypted token to database
```

**Day 7-8: Basic Commands**
```python
# Implement power control
POST /api/v1/network-control/samsung/power
{
  "device_id": 123,
  "state": true
}

# Implement volume control
POST /api/v1/network-control/samsung/volume-up
{
  "device_id": 123,
  "steps": 5
}
```

**Day 9-10: Status Monitoring**
```python
# Add status endpoint
GET /api/v1/network-control/samsung/status/123
# Returns: power_state, current_app, etc.

# Compare to IR control
# - Measure latency difference
# - Test reliability
# - Verify status accuracy
```

### Success Criteria

✅ Can discover Samsung TVs automatically
✅ Successful pairing with token storage
✅ Power on/off via network works
✅ Volume control works
✅ Status feedback accurate
✅ Network latency < IR latency
✅ Fallback to IR if network fails

### Go/No-Go Decision Points

**GO:** If pilot shows network control is:
- Faster than IR (expected: 2-3x)
- More reliable (>95% success rate)
- Provides useful status feedback
- Easy to pair and manage

**ITERATE:** If:
- Some features work but need refinement
- Pairing flow needs UI improvements
- Status polling needs optimization

**NO-GO:** If:
- Network control is slower or less reliable than IR
- Too complex to implement/maintain
- TVs frequently disconnect
- Pairing is too difficult for end users

---

## 📋 Technology Stack Additions

### Python Dependencies

```txt
# Add to backend/requirements.txt

# Samsung TV Control
samsungtvws>=2.6.0

# LG TV Control (for future phases)
aiowebostv>=0.4.0
PyWebOSTV>=0.2.0

# Sony TV Control (for future phases)
bravia-tv>=1.0.12

# Philips TV Control (for future phases)
# (pylips may require manual install from GitHub)

# Network Discovery
ssdpy>=0.4.0            # SSDP/UPnP discovery
zeroconf>=0.132.0       # Already installed for mDNS

# Utilities
cryptography>=41.0.0    # Token encryption (may already be installed)
```

### New Backend Structure

```
backend/app/
├── services/
│   ├── network_tv/
│   │   ├── __init__.py
│   │   ├── base.py                    # Abstract base controller
│   │   ├── samsung_controller.py      # Samsung WebSocket implementation
│   │   ├── lg_controller.py           # LG WebOS implementation (Phase 2)
│   │   ├── sony_controller.py         # Sony Bravia implementation (Phase 2)
│   │   ├── philips_controller.py      # Philips JointSpace implementation (Phase 2)
│   │   ├── discovery.py               # SSDP/mDNS scanner
│   │   ├── pairing_manager.py         # Token management & encryption
│   │   └── controller_factory.py      # Factory to create brand-specific controllers
│   ├── hybrid_control.py              # Unified control layer (network + IR)
│   └── status_monitor.py              # Background polling service
├── models/
│   ├── network_tv.py                  # New DB models for network control
│   └── network_discovery.py           # Discovery log models
└── routers/
    ├── network_control.py             # New API endpoints
    └── network_discovery.py           # Discovery API endpoints
```

---

## 🔒 Security Considerations

### 1. Token Storage & Encryption

**Problem:** Network control requires storing authentication tokens/credentials

**Solution:**
```python
from cryptography.fernet import Fernet
import os
import base64

# Generate encryption key (store in environment)
# NETWORK_TV_ENCRYPTION_KEY=<base64_encoded_32_byte_key>

class TokenManager:
    def __init__(self):
        key = os.environ.get('NETWORK_TV_ENCRYPTION_KEY')
        if not key:
            raise ValueError("NETWORK_TV_ENCRYPTION_KEY not set")
        self.cipher = Fernet(key.encode())

    def encrypt_token(self, token: str) -> str:
        """Encrypt auth token for storage"""
        encrypted = self.cipher.encrypt(token.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt auth token for use"""
        encrypted = base64.b64decode(encrypted_token.encode())
        return self.cipher.decrypt(encrypted).decode()
```

**Best Practices:**
- Never log tokens in plaintext
- Rotate encryption key periodically
- Use environment variables (never commit keys to git)
- Implement token expiry checking
- Re-pair if tokens become invalid

### 2. Network Isolation

**Recommended Network Architecture:**

```
┌─────────────────────────────────────────┐
│  Management VLAN (10.0.1.0/24)         │
│                                         │
│  • TapCommand Hub (10.0.1.10)          │
│  • Admin Access                         │
│  • VPN Gateway (Tailscale)             │
└──────────────┬──────────────────────────┘
               │ VLAN Trunk
┌──────────────▼──────────────────────────┐
│  Device VLAN (10.0.2.0/24)             │
│                                         │
│  • ESP8266 IR Blasters (10.0.2.x)      │
│  • Network TVs (10.0.2.100+)           │
│  • Isolated from guest WiFi            │
└─────────────────────────────────────────┘
```

**Security Rules:**
- Device VLAN can't initiate connections to management VLAN
- Management VLAN can send commands to device VLAN
- No internet access for device VLAN (optional: allow firmware updates only)
- Firewall logs all traffic between VLANs

**If Using Existing "TV" WiFi:**
- Document that TVs are on same network as TapCommand hub
- Consider WPA2-Enterprise for device authentication
- MAC address filtering for known devices only
- Regular security audits

### 3. Rate Limiting

**Problem:** Prevent command flooding, respect TV API limits

**Implementation:**
```python
from asyncio import Semaphore
from collections import defaultdict
import time

class RateLimiter:
    def __init__(self, max_requests_per_minute: int = 30):
        self.max_requests = max_requests_per_minute
        self.request_times = defaultdict(list)
        self.semaphore = Semaphore(10)  # Max 10 concurrent connections

    async def acquire(self, device_id: int):
        """Check if request is within rate limit"""
        async with self.semaphore:
            now = time.time()
            minute_ago = now - 60

            # Remove old requests
            self.request_times[device_id] = [
                t for t in self.request_times[device_id]
                if t > minute_ago
            ]

            # Check limit
            if len(self.request_times[device_id]) >= self.max_requests:
                raise TooManyRequests(
                    f"Rate limit exceeded for device {device_id}. "
                    f"Max {self.max_requests} requests/minute."
                )

            # Record request
            self.request_times[device_id].append(now)
```

### 4. Input Validation

**Prevent Command Injection:**
```python
from pydantic import BaseModel, validator

class NetworkControlCommand(BaseModel):
    device_id: int
    command_type: str
    parameters: dict

    @validator('command_type')
    def validate_command(cls, v):
        allowed_commands = [
            'power', 'volume', 'mute', 'input',
            'key', 'app_launch', 'status_query'
        ]
        if v not in allowed_commands:
            raise ValueError(f'Invalid command type: {v}')
        return v

    @validator('parameters')
    def sanitize_parameters(cls, v, values):
        command = values.get('command_type')

        if command == 'key':
            # Only allow predefined Samsung key codes
            allowed_keys = [
                'KEY_POWER', 'KEY_VOLUP', 'KEY_VOLDOWN',
                'KEY_MUTE', 'KEY_HDMI1', 'KEY_HDMI2',
                # ... full list
            ]
            if v.get('key') not in allowed_keys:
                raise ValueError(f'Invalid key code: {v.get("key")}')

        return v
```

---

## 📊 Expected Benefits

### Operational Improvements

| Metric | Current (IR Only) | With Network Control | Improvement |
|--------|-------------------|----------------------|-------------|
| **Command Execution Time** | 200-500ms | 50-200ms | **2-3x faster** |
| **Success Verification** | 0% (blind) | 95%+ (with feedback) | **Measurable reliability** |
| **Diagnostic Capability** | None | Real-time status | **Proactive monitoring** |
| **Remote Troubleshooting** | Impossible | Full remote visibility | **Reduced site visits** |
| **Manual Override Detection** | None | Immediate alerts | **Staff accountability** |

### Feature Expansion Opportunities

**Smart Input Switching:**
- Current: Send "Input" button 15 times, hope we counted right
- Network: Direct HDMI selection or app launch
- **Benefit:** 5-10 second operation → <1 second

**Volume Normalization:**
- Current: Blind volume up/down increments
- Network: Read current level (e.g., 85), set to target (e.g., 50)
- **Benefit:** Consistent audio levels across all TVs

**Application Direct Launch:**
- Current: Navigate menus with arrow keys (slow, unreliable)
- Network: `launchApp("com.netflix.ninja")` → instant
- **Benefit:** Sports channel apps, news apps directly accessible

**Scheduled Verification:**
- Current: Schedule runs, assume it worked
- Network: Post-execution status check, alert on failure
- **Benefit:** Confidence scheduled operations actually executed

### ROI Enhancement

**Current ROI (IR Only):**
- Time savings: 75 minutes → 5 minutes daily (70 min saved)
- Annual value: $11,400+ per venue
- Payback: ~3-4 months

**Projected ROI (Hybrid Network + IR):**
- Additional time savings: 20-30% faster operations (1-1.5 min/day)
- Remote diagnostic time savings: 2-4 hours/month (eliminate site visits)
- Annual additional value: $2,000-3,000 per venue
- **Total Annual Value: $13,500-14,500 per venue**
- Enhanced reliability reduces support calls
- Predictive maintenance (alert before failures)

---

## ⚠️ Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation Strategy |
|------|------------|--------|---------------------|
| **Firmware updates break API** | Medium | Medium | • Maintain IR fallback<br>• Version detection<br>• Community monitoring<br>• Test firmware updates in staging |
| **Network dropouts** | Medium | Medium | • Auto-fallback to IR<br>• Connection pooling<br>• Health monitoring<br>• Alert on degradation |
| **Token expiration** | Low | Low | • Auto-renewal logic<br>• Re-pairing alerts<br>• Graceful degradation<br>• Admin notifications |
| **Brand discontinues API** | Low | Low | • Hybrid approach insulates<br>• IR remains primary<br>• Monitor vendor announcements |
| **Security vulnerabilities** | Medium | High | • Token encryption<br>• Network isolation<br>• Input validation<br>• Regular security audits |
| **Increased system complexity** | High | Medium | • Thorough testing<br>• Gradual rollout<br>• Documentation<br>• Training materials |
| **TV models incompatible** | Low | Low | • Pre-deployment testing<br>• Compatibility matrix<br>• Graceful fallback to IR |

---

## 🎯 Recommended Next Steps

### Immediate Actions (This Week)

1. **Decision Point:** Approve Samsung TV pilot (2 weeks, low risk)
2. **Environment Setup:** Install `samsungtvws` in backend venv
3. **Network Reconnaissance:**
   - Identify Samsung TVs currently deployed
   - Document IP addresses, models
   - Test SSDP discovery on your network
4. **Database Planning:** Review proposed schema changes

### Pilot Phase (Weeks 1-2)

**Week 1:**
- [ ] Install dependencies
- [ ] Implement Samsung discovery service
- [ ] Create basic pairing endpoint
- [ ] Test pairing with 1-2 Samsung TVs
- [ ] Document pairing flow

**Week 2:**
- [ ] Implement power control
- [ ] Implement volume control
- [ ] Add status monitoring
- [ ] Compare latency: network vs IR
- [ ] Document findings & metrics

### Go/No-Go Decision (End of Week 2)

**Evaluation Criteria:**
- Network control faster than IR? (Target: 2x faster)
- Success rate >95%?
- Status feedback reliable?
- Pairing process acceptable?
- Any showstopper issues?

**Outcomes:**
- **GO:** Proceed to Phase 2 (expand to LG, Sony)
- **ITERATE:** Refine Samsung implementation, extend pilot
- **NO-GO:** Document lessons learned, stick with IR

### Full Rollout (Weeks 3-8) - If Pilot Succeeds

**Week 3-4:** Implement LG WebOS + Sony Bravia controllers
**Week 5:** Build pairing UI components
**Week 6:** Add status monitoring service
**Week 7:** Implement hybrid control routing
**Week 8:** Advanced features & analytics

---

## 📚 Additional Resources

### Official Documentation

- **Samsung Tizen Developer:** https://developer.samsung.com/smarttv/
- **LG webOS Developer:** https://webostv.developer.lge.com/
- **Sony Bravia Pro:** https://pro-bravia.sony.net/develop/integrate/
- **Philips JointSpace:** http://jointspace.sourceforge.net/

### Python Libraries

- **Samsung:** https://github.com/xchwarze/samsung-tv-ws-api
- **LG:** https://github.com/supersaiyanmode/PyWebOSTV
- **Sony:** https://pypi.org/project/bravia-tv/
- **Philips:** https://github.com/eslavnov/pylips

### Community References

- **Home Assistant Integrations:** https://www.home-assistant.io/integrations/#tv
  - Real-world implementations of all major brands
  - Active maintenance and issue tracking
  - Good source of troubleshooting tips

### Testing Tools

- **SSDP Scanner:** `ssdpy` Python library or mobile apps
- **Network Scanner:** `nmap` for port discovery
- **API Testing:** Postman/curl for HTTP endpoints
- **WebSocket Testing:** `wscat` or browser DevTools
- **Packet Analysis:** Wireshark for protocol reverse engineering

### Research Papers & Whitepapers

- UPnP Device Architecture specification
- HDMI-CEC technical specifications
- Smart TV security analysis (various academic papers)

---

## Summary & Final Recommendation

### Key Findings

✅ **Network control is technically viable** for all major TV brands
✅ **Hybrid approach minimizes risk** (IR fallback always available)
✅ **Significant operational benefits** (faster, verified, monitored)
✅ **Commercial differentiation** (status monitoring unique in hospitality space)
✅ **ROI enhancement** ($2-3K additional annual value per venue)

### Recommended Implementation Strategy

**Phase 1: Samsung Pilot (2 weeks)**
- Low risk, high learning value
- Most mature API, best documentation
- Single brand reduces complexity
- Clear go/no-go decision criteria

**Phase 2: Expand Brands (4 weeks)** - If pilot succeeds
- Add LG WebOS (2nd best ecosystem)
- Add Sony Bravia (good for pro displays)
- Philips optional (if deployed)

**Phase 3: Production Hardening (2 weeks)**
- Status monitoring service
- Analytics dashboard
- Advanced routing logic
- Security hardening

### Expected Timeline

- **Pilot:** 2 weeks
- **Go/No-Go Decision:** 1 week
- **Full Implementation:** 6-8 weeks (if approved)
- **Production Deployment:** 10-12 weeks total

### Investment Required

**Development Time:**
- Phase 1 (Pilot): 40-60 hours
- Phase 2-3 (Full): 160-200 hours
- **Total:** ~200-260 hours

**Infrastructure:**
- No additional hardware required
- Python library licenses: Free (all open source)
- Network segmentation (optional): Varies by venue

**Training:**
- Admin training: 2-4 hours
- Staff training: 1 hour (UI stays same)

### Risk Assessment

**Overall Risk Level: LOW-MEDIUM**

- IR fallback mitigates most failure scenarios
- Pilot validates concept before full commitment
- Open source libraries widely used & maintained
- Commercial benefit justifies investment

---

**Status:** Awaiting approval for Samsung TV pilot implementation

**Next Action:** Approve pilot → Install dependencies → Begin discovery implementation

**Questions or Concerns?** Document any hesitations now before starting pilot.
