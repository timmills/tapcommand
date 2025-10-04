#!/usr/bin/env python3
"""
Test script for legacy Samsung TVs (2011-2015 D/E/F/H/J series)
Uses samsungctl library for port 55000 protocol
"""

import samsungctl

# Samsung LA40D550 at 192.168.101.50
TV_CONFIG = {
    "name": "SmartVenue",
    "description": "SmartVenue Control System",
    "id": "smartvenue",
    "host": "192.168.101.50",
    "port": 55000,
    "method": "legacy",  # Legacy protocol for D-series
    "timeout": 3,
}

def test_connection():
    """Test connection to legacy Samsung TV"""
    print("=" * 70)
    print(f"Testing Legacy Samsung TV: {TV_CONFIG['host']}")
    print("=" * 70)
    print()

    try:
        # Open connection
        print("Connecting to TV...")
        with samsungctl.Remote(TV_CONFIG) as remote:
            print("✓ Connection successful!")
            print()

            # Test some basic commands
            print("Testing commands...")

            # Volume up
            print("  Sending: KEY_VOLUP")
            remote.control("KEY_VOLUP")
            print("  ✓ Volume up sent")

            # Wait a moment
            import time
            time.sleep(0.5)

            # Volume down
            print("  Sending: KEY_VOLDOWN")
            remote.control("KEY_VOLDOWN")
            print("  ✓ Volume down sent")

            print()
            print("=" * 70)
            print("SUCCESS: TV is controllable via legacy protocol")
            print("=" * 70)

            return True

    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print()
        print("Troubleshooting:")
        print("- Ensure TV is powered on")
        print("- Check if 'External Device Manager' is enabled in TV settings")
        print("- Verify IP address is correct")
        return False

def list_available_keys():
    """Show some common key codes for legacy Samsung TVs"""
    print("\nCommon key codes for Samsung D-series:")
    print("-" * 70)
    keys = [
        ("KEY_POWER", "Power on/off"),
        ("KEY_VOLUP", "Volume up"),
        ("KEY_VOLDOWN", "Volume down"),
        ("KEY_MUTE", "Mute/unmute"),
        ("KEY_CHUP", "Channel up"),
        ("KEY_CHDOWN", "Channel down"),
        ("KEY_SOURCE", "Input/source selection"),
        ("KEY_HDMI", "HDMI input"),
        ("KEY_MENU", "Menu"),
        ("KEY_TOOLS", "Tools"),
        ("KEY_INFO", "Info"),
        ("KEY_EXIT", "Exit/back"),
        ("KEY_RETURN", "Return"),
        ("KEY_UP", "Navigate up"),
        ("KEY_DOWN", "Navigate down"),
        ("KEY_LEFT", "Navigate left"),
        ("KEY_RIGHT", "Navigate right"),
        ("KEY_ENTER", "Enter/select"),
    ]

    for key, description in keys:
        print(f"  {key:15} - {description}")
    print(f"  KEY_0 to KEY_9  - Number keys 0-9")

if __name__ == "__main__":
    success = test_connection()

    if success:
        list_available_keys()
        print()
        print("TV Details:")
        print(f"  Model: LA40D550 (2011 D-series)")
        print(f"  IP: {TV_CONFIG['host']}")
        print(f"  MAC: E4:E0:C5:B8:5A:97")
        print(f"  Protocol: Legacy (port 55000)")
        print()
        print("Next steps:")
        print("1. Create virtual controller entry in database")
        print("2. Store TV credentials")
        print("3. Integrate with SmartVenue API")
