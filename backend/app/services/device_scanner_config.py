"""
Device Scanner Configuration
Defines detection rules for different device types including port scanning and identification
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class PortScanRule:
    """Port scanning rule for device identification"""
    port: int
    protocol: str  # 'tcp' or 'udp'
    description: str
    timeout_ms: int = 1000


@dataclass
class DeviceTypeConfig:
    """Configuration for identifying a specific device type"""
    device_type: str
    display_name: str
    mac_vendor_patterns: List[str]  # Vendor name patterns to match
    port_scans: List[PortScanRule]  # Ports to check for identification
    priority: int = 0  # Higher priority = checked first
    enabled: bool = True


# Device type configurations
DEVICE_TYPES = {
    # Samsung TVs
    "samsung_tv_legacy": DeviceTypeConfig(
        device_type="samsung_tv_legacy",
        display_name="Samsung TV (Legacy)",
        mac_vendor_patterns=["samsung"],
        port_scans=[
            PortScanRule(port=55000, protocol="tcp", description="Samsung Legacy Control API", timeout_ms=500),
        ],
        priority=100,
        enabled=True
    ),

    "samsung_tv_tizen": DeviceTypeConfig(
        device_type="samsung_tv_tizen",
        display_name="Samsung TV (Tizen)",
        mac_vendor_patterns=["samsung"],
        port_scans=[
            PortScanRule(port=8001, protocol="tcp", description="Samsung Tizen WebSocket API", timeout_ms=500),
            PortScanRule(port=8002, protocol="tcp", description="Samsung Tizen WebSocket SSL", timeout_ms=500),
        ],
        priority=90,
        enabled=True
    ),

    # LG TVs
    "lg_webos": DeviceTypeConfig(
        device_type="lg_webos",
        display_name="LG TV (webOS)",
        mac_vendor_patterns=["lg electronics", "lg innotek"],
        port_scans=[
            PortScanRule(port=3000, protocol="tcp", description="LG webOS WebSocket", timeout_ms=500),
            PortScanRule(port=3001, protocol="tcp", description="LG webOS SSL", timeout_ms=500),
        ],
        priority=80,
        enabled=True
    ),

    # Sony TVs
    "sony_bravia": DeviceTypeConfig(
        device_type="sony_bravia",
        display_name="Sony Bravia TV",
        mac_vendor_patterns=["sony"],
        port_scans=[
            PortScanRule(port=80, protocol="tcp", description="Sony IRCC HTTP API", timeout_ms=500),
            PortScanRule(port=50001, protocol="tcp", description="Sony Control", timeout_ms=500),
            PortScanRule(port=50002, protocol="tcp", description="Sony Control Alt", timeout_ms=500),
        ],
        priority=70,
        enabled=True
    ),

    # Philips TVs
    "philips_android": DeviceTypeConfig(
        device_type="philips_android",
        display_name="Philips Android TV",
        mac_vendor_patterns=["philips"],
        port_scans=[
            PortScanRule(port=1925, protocol="tcp", description="Philips JointSpace API", timeout_ms=500),
            PortScanRule(port=1926, protocol="tcp", description="Philips JointSpace SSL", timeout_ms=500),
        ],
        priority=60,
        enabled=True
    ),

    # Hisense TVs
    "hisense_vidaa": DeviceTypeConfig(
        device_type="hisense_vidaa",
        display_name="Hisense TV (VIDAA)",
        mac_vendor_patterns=["hisense"],
        port_scans=[
            PortScanRule(port=36669, protocol="tcp", description="Hisense Remote Control", timeout_ms=500),
            PortScanRule(port=3000, protocol="tcp", description="Hisense API", timeout_ms=500),
        ],
        priority=75,
        enabled=True
    ),

    # TCL/Roku TVs
    "tcl_roku": DeviceTypeConfig(
        device_type="tcl_roku",
        display_name="TCL Roku TV",
        mac_vendor_patterns=["tcl", "roku"],
        port_scans=[
            PortScanRule(port=8060, protocol="tcp", description="Roku External Control API", timeout_ms=500),
        ],
        priority=55,
        enabled=True
    ),

    # Vizio TVs
    "vizio_smartcast": DeviceTypeConfig(
        device_type="vizio_smartcast",
        display_name="Vizio SmartCast TV",
        mac_vendor_patterns=["vizio"],
        port_scans=[
            PortScanRule(port=7345, protocol="tcp", description="Vizio SmartCast API", timeout_ms=500),
            PortScanRule(port=9000, protocol="tcp", description="Vizio Cast", timeout_ms=500),
        ],
        priority=65,
        enabled=True
    ),

    # Android TV brands (CHiQ, TCL, Sharp, Toshiba)
    "chiq_android": DeviceTypeConfig(
        device_type="chiq_android",
        display_name="CHiQ Android TV",
        mac_vendor_patterns=["changhong", "chiq"],
        port_scans=[
            PortScanRule(port=6466, protocol="tcp", description="Android TV Remote Control", timeout_ms=500),
            PortScanRule(port=6467, protocol="tcp", description="Android TV Pairing", timeout_ms=500),
            PortScanRule(port=5555, protocol="tcp", description="Android ADB", timeout_ms=500),
        ],
        priority=72,
        enabled=True
    ),

    "tcl_android": DeviceTypeConfig(
        device_type="tcl_android",
        display_name="TCL Android TV",
        mac_vendor_patterns=["tcl"],
        port_scans=[
            PortScanRule(port=6466, protocol="tcp", description="Android TV Remote Control", timeout_ms=500),
            PortScanRule(port=6467, protocol="tcp", description="Android TV Pairing", timeout_ms=500),
            PortScanRule(port=8060, protocol="tcp", description="Roku ECP (some models)", timeout_ms=500),
        ],
        priority=71,
        enabled=True
    ),

    "sharp_android": DeviceTypeConfig(
        device_type="sharp_android",
        display_name="Sharp Android TV",
        mac_vendor_patterns=["sharp"],
        port_scans=[
            PortScanRule(port=6466, protocol="tcp", description="Android TV Remote Control", timeout_ms=500),
            PortScanRule(port=6467, protocol="tcp", description="Android TV Pairing", timeout_ms=500),
        ],
        priority=68,
        enabled=True
    ),

    "toshiba_android": DeviceTypeConfig(
        device_type="toshiba_android",
        display_name="Toshiba Android TV",
        mac_vendor_patterns=["toshiba"],
        port_scans=[
            PortScanRule(port=6466, protocol="tcp", description="Android TV Remote Control", timeout_ms=500),
            PortScanRule(port=6467, protocol="tcp", description="Android TV Pairing", timeout_ms=500),
        ],
        priority=67,
        enabled=True
    ),

    # Roku devices
    "roku": DeviceTypeConfig(
        device_type="roku",
        display_name="Roku Device",
        mac_vendor_patterns=["roku"],
        port_scans=[
            PortScanRule(port=8060, protocol="tcp", description="Roku External Control API", timeout_ms=500),
        ],
        priority=50,
        enabled=True
    ),

    # Apple TV
    "apple_tv": DeviceTypeConfig(
        device_type="apple_tv",
        display_name="Apple TV",
        mac_vendor_patterns=["apple"],
        port_scans=[
            PortScanRule(port=3689, protocol="tcp", description="Apple AirPlay", timeout_ms=500),
            PortScanRule(port=7000, protocol="tcp", description="Apple AirPlay Video", timeout_ms=500),
        ],
        priority=40,
        enabled=True
    ),

    # ESPHome IR Controllers
    "esphome_ir_controller": DeviceTypeConfig(
        device_type="esphome_ir_controller",
        display_name="ESPHome IR Controller",
        mac_vendor_patterns=["espressif"],  # ESP32/ESP8266 use Espressif MAC
        port_scans=[
            PortScanRule(port=6053, protocol="tcp", description="ESPHome Native API", timeout_ms=500),
            PortScanRule(port=80, protocol="tcp", description="ESPHome Web Server", timeout_ms=500),
        ],
        priority=110,  # High priority - check these first
        enabled=True
    ),

    # Generic smart devices (for future expansion)
    "chromecast": DeviceTypeConfig(
        device_type="chromecast",
        display_name="Google Chromecast",
        mac_vendor_patterns=["google"],
        port_scans=[
            PortScanRule(port=8008, protocol="tcp", description="Chromecast HTTP", timeout_ms=500),
            PortScanRule(port=8009, protocol="tcp", description="Chromecast HTTPS", timeout_ms=500),
        ],
        priority=30,
        enabled=True
    ),

    "fire_tv": DeviceTypeConfig(
        device_type="fire_tv",
        display_name="Amazon Fire TV",
        mac_vendor_patterns=["amazon"],
        port_scans=[
            PortScanRule(port=5555, protocol="tcp", description="Fire TV ADB", timeout_ms=500),
        ],
        priority=20,
        enabled=False  # Disabled by default, enable when needed
    ),

    # Generic devices to exclude from discovery
    "pc_workstation": DeviceTypeConfig(
        device_type="pc_workstation",
        display_name="PC/Workstation",
        mac_vendor_patterns=[
            "intel", "dell", "hp", "lenovo", "asus", "msi", "gigabyte",
            "asrock", "amd", "realtek", "microsoft"
        ],
        port_scans=[],  # No port scanning needed
        priority=1,  # Low priority
        enabled=True
    ),
}


def get_enabled_device_types() -> List[DeviceTypeConfig]:
    """Get all enabled device type configurations sorted by priority"""
    enabled = [config for config in DEVICE_TYPES.values() if config.enabled]
    return sorted(enabled, key=lambda x: x.priority, reverse=True)


def get_device_type_by_vendor(vendor_name: str) -> Optional[DeviceTypeConfig]:
    """
    Get device type config based on vendor name
    Returns highest priority match
    """
    if not vendor_name:
        return None

    vendor_lower = vendor_name.lower()

    # Get enabled types sorted by priority
    for config in get_enabled_device_types():
        for pattern in config.mac_vendor_patterns:
            if pattern.lower() in vendor_lower:
                return config

    return None


def get_all_tv_vendors() -> List[str]:
    """Get list of all TV vendor patterns for quick filtering"""
    tv_types = [
        "samsung_tv_legacy", "samsung_tv_tizen", "lg_webos", "sony_bravia",
        "philips_android", "hisense_vidaa", "tcl_roku", "vizio_smartcast",
        "chiq_android", "tcl_android", "sharp_android", "toshiba_android"
    ]
    patterns = []

    for device_type in tv_types:
        if device_type in DEVICE_TYPES and DEVICE_TYPES[device_type].enabled:
            patterns.extend(DEVICE_TYPES[device_type].mac_vendor_patterns)

    return patterns


def get_ports_for_device_type(device_type: str) -> List[int]:
    """Get list of ports to scan for a specific device type"""
    if device_type in DEVICE_TYPES:
        return [rule.port for rule in DEVICE_TYPES[device_type].port_scans]
    return []


# Port scanning configuration
PORT_SCAN_CONFIG = {
    "enabled": True,  # Enable/disable port scanning globally
    "timeout_ms": 500,  # Default timeout for port checks
    "max_concurrent": 10,  # Max concurrent port scans
}


# Example: How to add a new device type
"""
To add a new device type:

1. Add to DEVICE_TYPES dictionary:

    "vizio_smartcast": DeviceTypeConfig(
        device_type="vizio_smartcast",
        display_name="Vizio SmartCast TV",
        mac_vendor_patterns=["vizio"],
        port_scans=[
            PortScanRule(port=7345, protocol="tcp", description="Vizio SmartCast API", timeout_ms=500),
            PortScanRule(port=9000, protocol="tcp", description="Vizio Cast", timeout_ms=500),
        ],
        priority=65,
        enabled=True
    ),

2. The scanner will automatically:
   - Detect devices with "vizio" in vendor name
   - Scan ports 7345 and 9000 to verify it's a SmartCast TV
   - Assign device_type_guess as "vizio_smartcast"
   - Display as "Vizio SmartCast TV" in UI

3. No other code changes needed!
"""
