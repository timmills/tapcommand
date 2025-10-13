#!/usr/bin/env python3
"""
Test SYNC command to retrieve preset names from Plena Matrix device
"""

import socket
import struct
import sys

# Protocol constants
PROTOCOL_ID_AMPLIFIER = 0x5E41
SUBTYPE_MASTER = 0x0001
CMD_SYNC = b'SYNC'
SYNC_TYPE_PRESETS = 101  # Preset names and validity

def build_packet_header(sequence: int, chunk_length: int) -> bytes:
    """Build 10-byte UDP packet header"""
    return struct.pack(
        '>HHHHH',
        PROTOCOL_ID_AMPLIFIER,
        SUBTYPE_MASTER,
        sequence,
        0x0000,
        chunk_length
    )

def test_sync_presets(ip_address: str, port: int = 12128):
    """Test SYNC Type 101 command"""

    print(f"\n{'='*70}")
    print(f"Testing SYNC Type 101 (Preset Names) at {ip_address}:{port}")
    print(f"{'='*70}")

    try:
        # Create socket and bind to port 12129
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', 12129))
        sock.settimeout(5.0)

        # Build SYNC packet: [10-byte header][4-byte SYNC][1-byte type]
        seq = 1
        command_data = CMD_SYNC + struct.pack('B', SYNC_TYPE_PRESETS)
        chunk_length = len(command_data)  # 5 bytes

        header = build_packet_header(seq, chunk_length)
        packet = header + command_data

        print(f"\n📦 Packet structure:")
        print(f"   Header (10 bytes): {header.hex()}")
        print(f"   Command (5 bytes): {command_data.hex()}")
        print(f"   Total packet ({len(packet)} bytes): {packet.hex()}")

        # Send packet
        print(f"\n→ Sending {len(packet)}-byte SYNC packet...")
        sock.sendto(packet, (ip_address, port))

        # Wait for response
        print(f"← Waiting for SYNC response (timeout: 5.0s)...")
        response, addr = sock.recvfrom(4096)

        print(f"\n✅ SUCCESS! Received response from {addr}")
        print(f"   Response size: {len(response)} bytes")
        print(f"   Response hex (first 50 bytes): {response[:50].hex()}...")

        # Parse response header
        if len(response) >= 14:
            protocol_id, sub_type, seq_resp, reserved, chunk_len = struct.unpack('>HHHHH', response[0:10])
            cmd = response[10:14]
            data = response[14:] if chunk_len > 4 else b''

            print(f"\n   Response header:")
            print(f"   - Protocol ID: 0x{protocol_id:04X}")
            print(f"   - Sub Type: 0x{sub_type:04X} {'(slave)' if sub_type == 0x0100 else ''}")
            print(f"   - Sequence: {seq_resp}")
            print(f"   - Chunk Length: {chunk_len}")
            print(f"   - Command: {cmd.decode('ascii', errors='ignore')}")
            print(f"   - Data size: {len(data)} bytes")

            # Parse preset names
            if cmd == CMD_SYNC and len(data) > 0:
                print(f"\n   📋 Preset Information:")
                idx = 0
                preset_num = 1
                while idx + 33 <= len(data) and preset_num <= 8:
                    is_valid = data[idx] != 0
                    preset_name = data[idx+1:idx+33].rstrip(b'\x00').decode('utf-8', errors='ignore')

                    status = "✓" if is_valid else "✗"
                    print(f"   {status} Preset {preset_num}: {preset_name or '(unnamed)'}")

                    idx += 33
                    preset_num += 1

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

    success = test_sync_presets(ip, port)

    print(f"\n{'='*70}")
    print(f"Result: {'✅ PASS' if success else '❌ FAIL'}")
    print(f"{'='*70}\n")

    sys.exit(0 if success else 1)
