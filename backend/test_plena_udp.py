#!/usr/bin/env python3
"""
Plena Matrix UDP Diagnostic Tool

Tests UDP communication with PLM-4P125 amplifier
"""

import socket
import struct
import sys
import time

def test_plena_ping(ip_address, port=12128, timeout=5.0):
    """Test PING command to Plena Matrix"""

    print(f"Testing Plena Matrix at {ip_address}:{port}")
    print("-" * 60)

    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)

        print(f"✓ Created UDP socket")

        # Build PING packet
        # Format: [COMMAND_TYPE: 4 bytes][SEQUENCE_NUMBER: 2 bytes][DATA_LENGTH: 2 bytes]
        seq = 1
        length = 0
        packet = b'PING' + struct.pack('>HH', seq, length)

        print(f"✓ Built PING packet: {packet.hex()}")
        print(f"  - Command: PING")
        print(f"  - Sequence: {seq}")
        print(f"  - Length: {length}")
        print(f"  - Total packet size: {len(packet)} bytes")

        # Send packet
        print(f"\n→ Sending PING to {ip_address}:{port}...")
        bytes_sent = sock.sendto(packet, (ip_address, port))
        print(f"✓ Sent {bytes_sent} bytes")

        # Wait for response
        print(f"\n← Waiting for response (timeout: {timeout}s)...")
        start_time = time.time()

        try:
            response, addr = sock.recvfrom(1024)
            elapsed = time.time() - start_time

            print(f"✓ Received response from {addr}")
            print(f"  - Response time: {elapsed*1000:.1f}ms")
            print(f"  - Response size: {len(response)} bytes")
            print(f"  - Response hex: {response.hex()}")

            # Parse response
            if len(response) >= 8:
                cmd = response[0:4]
                seq_resp = struct.unpack('>H', response[4:6])[0]
                length_resp = struct.unpack('>H', response[6:8])[0]
                data = response[8:]

                print(f"\n  Response breakdown:")
                print(f"    - Command: {cmd.decode('ascii', errors='ignore')}")
                print(f"    - Sequence: {seq_resp}")
                print(f"    - Data length: {length_resp}")
                print(f"    - Data: {data.hex()}")

            print(f"\n✅ SUCCESS: Device responded to PING")
            return True

        except socket.timeout:
            elapsed = time.time() - start_time
            print(f"✗ Timeout after {elapsed:.1f}s - no response received")
            print(f"\n❌ FAILED: Device did not respond")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        sock.close()
        print(f"\n✓ Closed socket")


def test_plena_what(ip_address, port=12128, timeout=5.0):
    """Test WHAT command (device info) to Plena Matrix"""

    print(f"\n\nTesting WHAT command at {ip_address}:{port}")
    print("-" * 60)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)

        # Build WHAT packet
        seq = 2
        length = 0
        packet = b'WHAT' + struct.pack('>HH', seq, length)

        print(f"✓ Built WHAT packet: {packet.hex()}")

        # Send packet
        print(f"\n→ Sending WHAT to {ip_address}:{port}...")
        sock.sendto(packet, (ip_address, port))

        # Wait for response
        print(f"\n← Waiting for response (timeout: {timeout}s)...")

        try:
            response, addr = sock.recvfrom(1024)

            print(f"✓ Received response from {addr}")
            print(f"  - Response size: {len(response)} bytes")
            print(f"  - Response hex: {response.hex()}")

            if len(response) >= 8:
                cmd = response[0:4]
                seq_resp = struct.unpack('>H', response[4:6])[0]
                length_resp = struct.unpack('>H', response[6:8])[0]
                data = response[8:8+length_resp]

                print(f"\n  Response breakdown:")
                print(f"    - Command: {cmd.decode('ascii', errors='ignore')}")
                print(f"    - Sequence: {seq_resp}")
                print(f"    - Data length: {length_resp}")
                print(f"    - Data hex: {data.hex()}")
                print(f"    - Data ASCII: {data.decode('ascii', errors='ignore')}")

            print(f"\n✅ SUCCESS: Device responded to WHAT")
            return True

        except socket.timeout:
            print(f"✗ Timeout - no response received")
            print(f"\n❌ FAILED: Device did not respond")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        sock.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_plena_udp.py <ip_address> [port] [timeout]")
        print("Example: python test_plena_udp.py 192.168.90.17 12128 5")
        sys.exit(1)

    ip = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 12128
    timeout = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0

    print("=" * 60)
    print("PLENA MATRIX UDP DIAGNOSTIC TOOL")
    print("=" * 60)
    print(f"Target: {ip}:{port}")
    print(f"Timeout: {timeout}s")
    print("=" * 60)

    # Test PING
    ping_success = test_plena_ping(ip, port, timeout)

    # Test WHAT
    what_success = test_plena_what(ip, port, timeout)

    # Summary
    print("\n")
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"PING test: {'✅ PASS' if ping_success else '❌ FAIL'}")
    print(f"WHAT test: {'✅ PASS' if what_success else '❌ FAIL'}")
    print("=" * 60)

    sys.exit(0 if (ping_success or what_success) else 1)
