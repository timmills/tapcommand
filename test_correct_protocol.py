#!/usr/bin/env python3
"""
Test Plena Matrix UDP communication with CORRECT protocol format
Based on official API manual page 4
"""

import socket
import struct
import sys

# Protocol constants from API manual
PROTOCOL_ID_AMPLIFIER = 0x5E41  # PLM-4Px2x amplifiers
SUBTYPE_MASTER = 0x0001          # Packets from master (us)

def build_packet_header(sequence: int, chunk_length: int) -> bytes:
    """
    Build 10-byte UDP packet header per Plena Matrix API spec
    [Protocol ID: 2][Sub Type: 2][Sequence: 2][Reserved: 2][Chunk Length: 2]
    """
    return struct.pack(
        '>HHHHH',
        PROTOCOL_ID_AMPLIFIER,  # 0x5E41 for amplifier
        SUBTYPE_MASTER,         # 0x0001 for master
        sequence,               # Sequence number
        0x0000,                 # Reserved
        chunk_length            # Length of data after header
    )

def test_ping(ip_address: str, port: int = 12128, timeout: float = 3.0):
    """Test PING command with correct protocol"""

    print(f"\n{'='*70}")
    print(f"Testing PING with CORRECT protocol at {ip_address}:{port}")
    print(f"{'='*70}")

    try:
        # Create socket and bind to port 12129 to receive responses
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', 12129))  # Bind to port 12129 for receiving responses
        sock.settimeout(timeout)

        # Build PING packet
        command = b'PING'
        chunk_length = len(command)  # 4 bytes
        seq = 1

        header = build_packet_header(seq, chunk_length)
        packet = header + command

        print(f"\n📦 Packet structure:")
        print(f"   Header (10 bytes): {header.hex()}")
        print(f"   Command (4 bytes): {command.hex()}")
        print(f"   Total packet ({len(packet)} bytes): {packet.hex()}")
        print(f"\n   Breakdown:")
        print(f"   - Protocol ID: 0x{PROTOCOL_ID_AMPLIFIER:04X} (amplifier)")
        print(f"   - Sub Type: 0x{SUBTYPE_MASTER:04X} (master)")
        print(f"   - Sequence: {seq}")
        print(f"   - Reserved: 0x0000")
        print(f"   - Chunk Length: {chunk_length}")

        # Send packet to port 12128
        print(f"\n→ Sending {len(packet)}-byte packet to {ip_address}:{port}...")
        sock.sendto(packet, (ip_address, port))

        # Wait for response on port 12129
        print(f"← Waiting for response on port 12129 (timeout: {timeout}s)...")
        response, addr = sock.recvfrom(1024)

        print(f"\n✅ SUCCESS! Received response from {addr}")
        print(f"   Response size: {len(response)} bytes")
        print(f"   Response hex: {response.hex()}")

        # Parse response header (10 bytes)
        if len(response) >= 10:
            protocol_id, sub_type, seq_resp, reserved, chunk_len = struct.unpack('>HHHHH', response[0:10])
            print(f"\n   Response header:")
            print(f"   - Protocol ID: 0x{protocol_id:04X}")
            print(f"   - Sub Type: 0x{sub_type:04X} {'(slave)' if sub_type == 0x0100 else ''}")
            print(f"   - Sequence: {seq_resp}")
            print(f"   - Chunk Length: {chunk_len}")

            # Parse WHAT command (4 bytes)
            if len(response) >= 14:
                cmd = response[10:14]
                print(f"   - Command: {cmd.decode('ascii', errors='ignore')}")

                # Parse WHAT response data (per API manual page 8)
                if cmd == b'WHAT' and len(response) >= 32:
                    idx = 14
                    fw_major = response[idx]
                    fw_minor = response[idx+1]
                    fw_rev = struct.unpack('>H', response[idx+2:idx+4])[0]
                    idx += 4

                    mac = ':'.join(f'{b:02x}' for b in response[idx:idx+6])
                    idx += 6

                    ip = '.'.join(str(b) for b in response[idx:idx+4])
                    idx += 4

                    subnet = '.'.join(str(b) for b in response[idx:idx+4])
                    idx += 4

                    gateway = '.'.join(str(b) for b in response[idx:idx+4])
                    idx += 4

                    dhcp = response[idx]
                    custom_mode = response[idx+1]
                    lockout = response[idx+2]
                    idx += 3

                    device_name = response[idx:idx+32].rstrip(b'\x00').decode('ascii', errors='ignore')
                    idx += 32

                    if len(response) >= idx + 81:
                        user_name = response[idx:idx+81].rstrip(b'\x00').decode('utf-8', errors='ignore')
                    else:
                        user_name = "N/A"

                    print(f"\n   📋 Device Information:")
                    print(f"   - Firmware: v{fw_major}.{fw_minor}.{fw_rev}")
                    print(f"   - MAC Address: {mac}")
                    print(f"   - IP Address: {ip}")
                    print(f"   - Subnet Mask: {subnet}")
                    print(f"   - Gateway: {gateway}")
                    print(f"   - DHCP: {'Enabled' if dhcp else 'Disabled'}")
                    print(f"   - Custom Mode: 0x{custom_mode:02X} {'(125W)' if custom_mode == 0 else '(220W)'}")
                    print(f"   - Lockout: {'LOCKED' if lockout else 'FREE'}")
                    print(f"   - Device Name: {device_name}")
                    print(f"   - User Name: {user_name}")

        sock.close()
        return True

    except socket.timeout:
        print(f"\n❌ Timeout - no response received")
        sock.close()
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.90.17"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 12128

    success = test_ping(ip, port)

    print(f"\n{'='*70}")
    print(f"Result: {'✅ PASS' if success else '❌ FAIL'}")
    print(f"{'='*70}\n")

    sys.exit(0 if success else 1)
