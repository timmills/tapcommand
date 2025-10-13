#!/usr/bin/env python3
"""
Plena Matrix SEIZE/PASS Test

Some Plena Matrix devices require PASS or SEIZ commands before responding
"""

import socket
import struct
import sys

def test_with_seize(ip_address, port=12128):
    """Try SEIZ command first, then PING"""

    print(f"Testing with SEIZE/PASS protocol at {ip_address}:{port}")
    print("=" * 60)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3.0)

    try:
        # Try SEIZ command first (take control)
        print("\n1. Sending SEIZ (seize control)...")
        seiz_packet = b'SEIZ' + struct.pack('>HH', 1, 0)
        print(f"   Packet: {seiz_packet.hex()}")
        sock.sendto(seiz_packet, (ip_address, port))

        try:
            response, addr = sock.recvfrom(1024)
            print(f"   ✓ SEIZ Response: {response.hex()}")
        except socket.timeout:
            print(f"   ✗ No SEIZ response (this might be OK)")

        # Try PASS command (password - empty)
        print("\n2. Sending PASS (password)...")
        pass_packet = b'PASS' + struct.pack('>HH', 2, 0)
        print(f"   Packet: {pass_packet.hex()}")
        sock.sendto(pass_packet, (ip_address, port))

        try:
            response, addr = sock.recvfrom(1024)
            print(f"   ✓ PASS Response: {response.hex()}")
        except socket.timeout:
            print(f"   ✗ No PASS response (this might be OK)")

        # Now try PING
        print("\n3. Sending PING...")
        ping_packet = b'PING' + struct.pack('>HH', 3, 0)
        print(f"   Packet: {ping_packet.hex()}")
        sock.sendto(ping_packet, (ip_address, port))

        try:
            response, addr = sock.recvfrom(1024)
            print(f"   ✓ PING Response: {response.hex()}")
            print(f"\n✅ SUCCESS! Device responded after SEIZ/PASS")
            return True
        except socket.timeout:
            print(f"   ✗ Still no PING response")

        # Try WHAT
        print("\n4. Sending WHAT...")
        what_packet = b'WHAT' + struct.pack('>HH', 4, 0)
        print(f"   Packet: {what_packet.hex()}")
        sock.sendto(what_packet, (ip_address, port))

        try:
            response, addr = sock.recvfrom(1024)
            print(f"   ✓ WHAT Response: {response.hex()}")
            print(f"\n✅ SUCCESS! Device responded to WHAT")
            return True
        except socket.timeout:
            print(f"   ✗ No WHAT response either")

        print(f"\n❌ Device not responding even with SEIZ/PASS")
        return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        sock.close()


if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.90.17"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 12128

    test_with_seize(ip, port)
