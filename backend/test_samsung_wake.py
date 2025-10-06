#!/usr/bin/env python3
"""
Comprehensive Samsung TV Wake-up Testing Script

Tests multiple methods to wake a Samsung TV from power-off state:
1. Wake-on-LAN (WOL) - Standard magic packets
2. Broadcast WOL - UDP broadcast on subnet
3. Multiple port attempts (9, 7, 3)
4. Status checking

For Samsung LA40D550 (D-series 2011) at 192.168.101.50
"""

import socket
import subprocess
import time
from wakeonlan import send_magic_packet


# TV Configuration
TV_IP = "192.168.101.50"
TV_MAC = "E4:E0:C5:B8:5A:97"
TV_PORT = 55000
BROADCAST_IP = "192.168.101.255"


def create_magic_packet(mac_address: str) -> bytes:
    """Create WOL magic packet from MAC address"""
    mac_bytes = bytes.fromhex(mac_address.replace(':', ''))
    # Magic packet: 6 bytes of 0xFF + 16 repetitions of MAC
    packet = b'\xff' * 6 + mac_bytes * 16
    return packet


def check_tv_online(timeout: int = 2) -> bool:
    """Check if TV responds to ping"""
    result = subprocess.run(
        ['ping', '-c', '1', '-W', str(timeout), TV_IP],
        capture_output=True,
        text=True
    )
    return result.returncode == 0


def check_port_open(port: int, timeout: int = 2) -> bool:
    """Check if specific port is open on TV"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        result = sock.connect_ex((TV_IP, port))
        sock.close()
        return result == 0
    except:
        return False


def method_1_standard_wol(packet_count: int = 16):
    """Method 1: Standard WOL using wakeonlan library"""
    print("\n" + "="*70)
    print("METHOD 1: Standard Wake-on-LAN (wakeonlan library)")
    print("="*70)

    print(f"Sending {packet_count} WOL magic packets to {TV_MAC}...")
    for i in range(packet_count):
        send_magic_packet(TV_MAC)

    print(f"✓ Sent {packet_count} packets")


def method_2_broadcast_wol(packet_count: int = 20):
    """Method 2: Broadcast WOL on subnet"""
    print("\n" + "="*70)
    print("METHOD 2: Broadcast WOL (UDP to 192.168.101.255)")
    print("="*70)

    packet = create_magic_packet(TV_MAC)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    print(f"Broadcasting {packet_count} WOL packets...")
    for i in range(packet_count):
        # Try multiple ports
        for port in [9, 7, 3]:
            sock.sendto(packet, (BROADCAST_IP, port))

    sock.close()
    print(f"✓ Sent {packet_count * 3} packets (ports 9, 7, 3)")


def method_3_targeted_wol(packet_count: int = 16):
    """Method 3: Targeted WOL to specific IP"""
    print("\n" + "="*70)
    print("METHOD 3: Targeted WOL (direct to TV IP)")
    print("="*70)

    packet = create_magic_packet(TV_MAC)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"Sending {packet_count} targeted WOL packets...")
    for i in range(packet_count):
        # Try multiple ports
        for port in [9, 7, 3, 55000]:
            try:
                sock.sendto(packet, (TV_IP, port))
            except:
                pass

    sock.close()
    print(f"✓ Sent {packet_count * 4} packets (ports 9, 7, 3, 55000)")


def method_4_repeated_wol(duration: int = 10):
    """Method 4: Continuous WOL for extended period"""
    print("\n" + "="*70)
    print(f"METHOD 4: Continuous WOL (for {duration} seconds)")
    print("="*70)

    packet = create_magic_packet(TV_MAC)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    start_time = time.time()
    count = 0

    print("Sending continuous WOL packets...")
    while time.time() - start_time < duration:
        sock.sendto(packet, (BROADCAST_IP, 9))
        count += 1
        time.sleep(0.1)  # 10 packets per second

    sock.close()
    print(f"✓ Sent {count} packets over {duration} seconds")


def check_tv_status():
    """Check current TV network status"""
    print("\n" + "="*70)
    print("TV STATUS CHECK")
    print("="*70)

    print(f"IP Address: {TV_IP}")
    print(f"MAC Address: {TV_MAC}")
    print()

    # Ping test
    print("Testing connectivity...")
    if check_tv_online(timeout=2):
        print("  ✓ TV responds to ping")
    else:
        print("  ✗ TV does not respond to ping")

    # Port tests
    print("\nTesting ports...")
    ports_to_check = [55000, 8001, 8002, 9]
    for port in ports_to_check:
        if check_port_open(port, timeout=2):
            print(f"  ✓ Port {port} is OPEN")
        else:
            print(f"  ✗ Port {port} is CLOSED")


def main():
    """Run all wake-up tests"""
    print("="*70)
    print("SAMSUNG TV WAKE-UP TEST SUITE")
    print("="*70)
    print(f"Target TV: Samsung LA40D550 (D-series 2011)")
    print(f"IP: {TV_IP}")
    print(f"MAC: {TV_MAC}")
    print("="*70)

    # Initial status
    print("\n>>> INITIAL STATUS CHECK")
    check_tv_status()

    initial_online = check_tv_online(timeout=1)
    if initial_online:
        print("\n⚠️  WARNING: TV appears to already be online!")
        print("    Turn off the TV with the remote control for accurate testing.")
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Test cancelled.")
            return

    # Test each method
    print("\n>>> STARTING WAKE-UP ATTEMPTS")

    # Method 1
    method_1_standard_wol(packet_count=16)
    print("Waiting 5 seconds...")
    time.sleep(5)
    if check_tv_online(timeout=2):
        print("✓✓✓ SUCCESS! TV is now online (Method 1)")
        check_tv_status()
        return
    else:
        print("✗ TV still offline")

    # Method 2
    method_2_broadcast_wol(packet_count=20)
    print("Waiting 5 seconds...")
    time.sleep(5)
    if check_tv_online(timeout=2):
        print("✓✓✓ SUCCESS! TV is now online (Method 2)")
        check_tv_status()
        return
    else:
        print("✗ TV still offline")

    # Method 3
    method_3_targeted_wol(packet_count=16)
    print("Waiting 5 seconds...")
    time.sleep(5)
    if check_tv_online(timeout=2):
        print("✓✓✓ SUCCESS! TV is now online (Method 3)")
        check_tv_status()
        return
    else:
        print("✗ TV still offline")

    # Method 4 - Last resort
    method_4_repeated_wol(duration=15)
    print("Waiting 10 seconds for TV to boot...")
    time.sleep(10)
    if check_tv_online(timeout=3):
        print("✓✓✓ SUCCESS! TV is now online (Method 4)")
        check_tv_status()
        return
    else:
        print("✗ TV still offline")

    # Final status
    print("\n>>> FINAL STATUS CHECK")
    check_tv_status()

    # Results
    print("\n" + "="*70)
    print("TEST RESULTS")
    print("="*70)
    print("✗ All WOL methods FAILED to wake the TV")
    print()
    print("POSSIBLE REASONS:")
    print("1. TV does not support Wake-on-LAN (common for 2011 models)")
    print("2. WOL feature is disabled in TV settings")
    print("3. TV must be in standby mode, not fully powered off")
    print("4. Network interface is powered down when TV is off")
    print()
    print("RECOMMENDED ALTERNATIVES:")
    print("1. Use IR (infrared) control for power-on")
    print("2. Use HDMI-CEC if connected to another device")
    print("3. Keep TV in standby mode instead of fully off")
    print("4. Use smart plug to control TV power")
    print("="*70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
