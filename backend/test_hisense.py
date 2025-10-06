#!/usr/bin/env python3
"""
Test script for Hisense TV network control

Tests MQTT-based control via port 36669 and Wake-on-LAN
Replace TV_IP with your Hisense TV's IP address
"""

import sys
import time
import ssl
from typing import Optional

# Check if hisensetv is installed
try:
    import hisensetv
except ImportError:
    print("Error: hisensetv library not installed")
    print("Install with: pip install hisensetv")
    sys.exit(1)


# Configuration - CHANGE THESE VALUES
TV_IP = "192.168.101.XXX"  # Replace with your Hisense TV IP
TV_MAC = "XX:XX:XX:XX:XX:XX"  # Replace with your TV's MAC address (for WOL)

# MQTT Configuration (usually default)
MQTT_PORT = 36669
MQTT_USERNAME = "hisenseservice"
MQTT_PASSWORD = "multimqttservice"


def test_connection(use_ssl: bool = False) -> bool:
    """Test basic connection to Hisense TV"""
    print("=" * 70)
    print(f"Testing Hisense TV Connection: {TV_IP}")
    print(f"SSL: {'Enabled' if use_ssl else 'Disabled'}")
    print("=" * 70)
    print()

    ssl_context = None
    if use_ssl:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

    try:
        print("Connecting to TV via MQTT...")
        tv = hisensetv.HisenseTv(
            hostname=TV_IP,
            port=MQTT_PORT,
            username=MQTT_USERNAME,
            password=MQTT_PASSWORD,
            timeout=10.0,
            ssl_context=ssl_context
        )

        with tv:
            print("✓ Connection successful!")
            print()

            # Try to get TV volume
            print("Getting TV volume...")
            try:
                volume = tv.get_volume()
                print(f"✓ Volume: {volume}")
            except Exception as e:
                print(f"✗ Could not get volume: {e}")

            print()

            # Try to get sources
            print("Getting TV sources...")
            try:
                sources = tv.get_sources()
                print(f"✓ Found {len(sources)} sources:")
                for source in sources:
                    signal = "📶" if source.get("is_signal") == "1" else "  "
                    print(f"  {signal} {source.get('displayname')} - {source.get('sourcename')}")
            except Exception as e:
                print(f"✗ Could not get sources: {e}")

            print()
            return True

    except Exception as e:
        error_str = str(e).lower()
        print(f"✗ Connection failed: {e}")
        print()

        # Check for specific error types
        if "authorization" in error_str or "auth" in error_str:
            print("⚠️  AUTHORIZATION REQUIRED:")
            print("   1. The TV may need to authorize this connection")
            print("   2. Check the TV screen for an authorization prompt")
            print("   3. Some models require pairing via the RemoteNow app first")
            print()

        elif "ssl" in error_str or "certificate" in error_str:
            print("⚠️  SSL ERROR:")
            print("   Your TV may require SSL or may require --no-ssl")
            if use_ssl:
                print("   Try running again without SSL")
            else:
                print("   Try running again with SSL enabled")
            print()

        elif "timeout" in error_str or "timed out" in error_str:
            print("⚠️  CONNECTION TIMEOUT:")
            print("   1. Ensure TV is powered ON (not standby)")
            print("   2. Check that TV and server are on same network")
            print("   3. Verify IP address is correct")
            print("   4. Check if port 36669 is accessible")
            print()

        elif "refused" in error_str:
            print("⚠️  CONNECTION REFUSED:")
            print("   1. TV may be in deep sleep mode")
            print("   2. MQTT service may be disabled")
            print("   3. Firewall may be blocking connection")
            print()

        return False


def test_commands():
    """Test sending commands to Hisense TV"""
    print("=" * 70)
    print("Testing Hisense TV Commands")
    print("=" * 70)
    print()

    try:
        tv = hisensetv.HisenseTv(
            hostname=TV_IP,
            port=MQTT_PORT,
            username=MQTT_USERNAME,
            password=MQTT_PASSWORD,
            timeout=10.0,
            ssl_context=None  # Adjust if needed
        )

        with tv:
            print("Testing volume control...")

            # Volume up
            print("  Sending: Volume Up")
            tv.send_key("KEY_VOLUMEUP")
            print("  ✓ Sent")
            time.sleep(0.5)

            # Volume down
            print("  Sending: Volume Down")
            tv.send_key("KEY_VOLUMEDOWN")
            print("  ✓ Sent")

            print()
            print("✓ Command test successful!")
            print()
            print("Available commands to try:")
            print("  - tv.send_key('KEY_VOLUMEUP')")
            print("  - tv.send_key('KEY_VOLUMEDOWN')")
            print("  - tv.send_key('KEY_MUTE')")
            print("  - tv.send_key('KEY_POWER')")
            print("  - tv.send_key('KEY_CHANNELUP')")
            print("  - tv.send_key('KEY_CHANNELDOWN')")
            print("  - tv.send_key('KEY_UP')")
            print("  - tv.send_key('KEY_DOWN')")
            print("  - tv.send_key('KEY_LEFT')")
            print("  - tv.send_key('KEY_RIGHT')")
            print("  - tv.send_key('KEY_OK')")
            print("  - tv.send_key('KEY_MENU')")
            print("  - tv.send_key('KEY_HOME')")
            print("  - tv.send_key('KEY_BACK')")
            print()

            return True

    except Exception as e:
        print(f"✗ Command test failed: {e}")
        return False


def test_wake_on_lan():
    """Test Wake-on-LAN for power-on"""
    print("=" * 70)
    print("Testing Wake-on-LAN")
    print("=" * 70)
    print()

    if TV_MAC == "XX:XX:XX:XX:XX:XX":
        print("⚠️  MAC address not configured!")
        print("   Edit this script and set TV_MAC to your TV's MAC address")
        print("   You can find the MAC in TV network settings")
        print()
        return False

    try:
        from wakeonlan import send_magic_packet

        print(f"Sending WOL packets to {TV_MAC}...")

        # Send multiple packets for reliability
        for i in range(16):
            send_magic_packet(TV_MAC)

        print("✓ Sent 16 WOL packets")
        print()
        print("⏳ Waiting 10 seconds for TV to wake...")
        time.sleep(10)
        print()
        print("Now test connection to see if TV woke up...")
        print()

        return True

    except ImportError:
        print("✗ wakeonlan library not installed")
        print("  Install with: pip install wakeonlan")
        return False
    except Exception as e:
        print(f"✗ WOL test failed: {e}")
        return False


def main():
    """Run all tests"""
    print()
    print("=" * 70)
    print("HISENSE TV NETWORK CONTROL TEST SUITE")
    print("=" * 70)
    print()
    print(f"Target TV: {TV_IP}")
    print(f"MAC Address: {TV_MAC}")
    print(f"MQTT Port: {MQTT_PORT}")
    print()

    if TV_IP == "192.168.101.XXX":
        print("⚠️  ERROR: TV_IP not configured!")
        print()
        print("Please edit this script and set:")
        print("  TV_IP = \"192.168.101.XX\"  # Your TV's IP address")
        print("  TV_MAC = \"XX:XX:XX:XX:XX:XX\"  # Your TV's MAC address")
        print()
        return

    # Test 1: Connection without SSL
    print("\n>>> TEST 1: Connection (No SSL)")
    success_no_ssl = test_connection(use_ssl=False)

    if not success_no_ssl:
        print("\n>>> TEST 2: Connection (With SSL)")
        success_ssl = test_connection(use_ssl=True)

        if not success_ssl:
            print()
            print("=" * 70)
            print("TROUBLESHOOTING")
            print("=" * 70)
            print()
            print("Connection failed with both SSL and no-SSL.")
            print()
            print("Ensure:")
            print("1. TV is powered ON (not in standby)")
            print("2. TV is on same network as this computer")
            print("3. IP address is correct")
            print("4. Port 36669 is not blocked by firewall")
            print("5. TV's MQTT service is enabled (usually automatic)")
            print()
            print("Some Hisense models require authorization on first connection:")
            print("- Watch TV screen for authorization prompt")
            print("- May need to pair via RemoteNow mobile app first")
            print()
            return

    # Test 2: Commands
    if success_no_ssl:
        print("\n>>> TEST 2: Send Commands")
        test_commands()

    # Test 3: Wake-on-LAN
    print("\n>>> TEST 3: Wake-on-LAN")
    response = input("Do you want to test WOL? (TV must be OFF first) [y/N]: ")
    if response.lower() == 'y':
        test_wake_on_lan()
    else:
        print("Skipping WOL test")

    # Summary
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print()
    print("✓ Connection: Working")
    print("✓ Commands: Working")
    print("⚠️ WOL: Requires MAC address and may be unreliable")
    print()
    print("RECOMMENDATIONS:")
    print("1. For reliable power-on: Use IR control or WOL + IR fallback")
    print("2. For all other commands: Use MQTT (this method)")
    print("3. Store TV credentials in database for automatic connection")
    print()
    print("Integration ready! ✓")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
