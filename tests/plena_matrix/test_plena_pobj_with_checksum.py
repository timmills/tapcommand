#!/usr/bin/env python3
"""
Test POBJ write with checksum byte for Zone 2 volume control
Based on PLM-4Px2x API documentation
"""
import socket
import struct
import sys

DEVICE_IP = "192.168.90.17"
RECEIVE_PORT = 12128
TRANSMIT_PORT = 12129

def db_to_lut_index(db_value: float) -> int:
    """Convert dB to LUT index (1-249, 0=mute)"""
    lut_index = int((db_value + 100.0) / 0.5 + 1)
    return max(1, min(249, lut_index))

def lut_index_to_db(lut_index: int) -> float:
    """Convert LUT index back to dB"""
    return (lut_index - 1) * 0.5 - 100.0

def set_zone_2_volume_pobj(db_value: float) -> bool:
    """
    Set Zone 2 volume using POBJ command with checksum
    
    POBJ format:
    [POBJ][IsRead:1][PresetNumber:1][PresetObjectID:2][NV:1][Data:2][Checksum:1]
    """
    preset_object_id = 52  # POBJ_AMPCH2_CB_OUTPUTLEVEL (Zone 2)
    lut_index = db_to_lut_index(db_value)
    
    print(f"Setting Zone 2 (POKIES) to {db_value}dB using POBJ")
    print(f"  Preset Object ID: {preset_object_id} (0x{preset_object_id:04x})")
    print(f"  LUT Index: {lut_index}")
    
    # POBJ WRITE format with checksum
    is_read = 0x00           # Write
    preset_number = 0x00     # Live/Current preset (not stored preset 1-5)
    nv_commit = 0x00         # RAM only (don't save to NV)
    lut_byte = lut_index
    flags = 0x00             # Unmuted
    checksum = 0x00          # Required checksum byte
    
    # Build POBJ command: POBJ + IsRead + PresetNum + ObjID(2) + NV + Data(2) + Checksum
    command_data = (
        b'POBJ' +
        struct.pack('B', is_read) +
        struct.pack('B', preset_number) +
        struct.pack('>H', preset_object_id) +  # 2-byte big-endian
        struct.pack('B', nv_commit) +
        struct.pack('BB', lut_byte, flags) +    # 2-byte data
        struct.pack('B', checksum)
    )
    
    # Build UDP packet header
    protocol_id = 0x5E41
    sub_type = 0x0001
    sequence = 1
    reserved = 0x0000
    chunk_length = len(command_data)
    
    header = struct.pack('>HHHHH', protocol_id, sub_type, sequence, reserved, chunk_length)
    packet = header + command_data
    
    print(f"\nPacket ({len(packet)} bytes): {packet.hex()}")
    print(f"  Command breakdown:")
    print(f"    POBJ: 504f424a")
    print(f"    IsRead: 0x{is_read:02x}")
    print(f"    PresetNumber: 0x{preset_number:02x} (live)")
    print(f"    PresetObjectID: 0x{preset_object_id:04x} ({preset_object_id})")
    print(f"    NV Commit: 0x{nv_commit:02x}")
    print(f"    LUT Index: 0x{lut_byte:02x} ({lut_byte})")
    print(f"    Flags: 0x{flags:02x}")
    print(f"    Checksum: 0x{checksum:02x}")
    
    # Send command
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', TRANSMIT_PORT))
    sock.settimeout(3.0)
    
    try:
        sock.sendto(packet, (DEVICE_IP, RECEIVE_PORT))
        print(f"\n✓ Sent to {DEVICE_IP}:{RECEIVE_PORT}")
        
        response, addr = sock.recvfrom(1024)
        print(f"✓ Response: {response.hex()}")
        
        if len(response) >= 14:
            cmd = response[10:14]
            data = response[14:]
            
            print(f"\nResponse:")
            print(f"  Command: {cmd}")
            print(f"  Data: {data.hex() if data else '(ACK)'}")
            
            if cmd == b'POBJ':
                print(f"\n✅ SUCCESS! POBJ acknowledged")
                if len(data) >= 2:
                    returned_lut = data[0]
                    returned_flags = data[1]
                    returned_db = lut_index_to_db(returned_lut)
                    print(f"   Returned: LUT={returned_lut}, dB={returned_db:.1f}, Muted={returned_flags!=0}")
                return True
            elif cmd == b'ACKN':
                print(f"\n✅ ACKN received")
                return True
            elif cmd == b'NACK':
                if len(data) >= 4:
                    nack_code = struct.unpack('>I', data[:4])[0]
                    print(f"\n❌ NACK: 0x{nack_code:08x}")
                return False
                
    except socket.timeout:
        print("\n⚠️  Timeout")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    finally:
        sock.close()

def verify_via_sync():
    """Verify volume via SYNC Type 102"""
    print("\n" + "="*70)
    print("Verifying via SYNC Type 102...")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", TRANSMIT_PORT))
    sock.settimeout(3.0)
    
    try:
        packet = struct.pack(">HHHHH", 0x5E41, 0x0001, 0x0001, 0x0000, 5) + b"SYNC" + struct.pack("B", 102)
        sock.sendto(packet, (DEVICE_IP, RECEIVE_PORT))
        
        data, _ = sock.recvfrom(4096)
        payload = data[14:]
        
        # Zone 2 at offset 32
        zone2_lut = payload[32]
        zone2_flags = payload[32 + 1]
        zone2_db = lut_index_to_db(zone2_lut)
        
        print(f"  Zone 2: LUT={zone2_lut}, {zone2_db:.1f}dB, Muted={zone2_flags!=0}")
        
    except Exception as e:
        print(f"  Could not verify: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_plena_pobj_with_checksum.py <db_value>")
        print("Example: python3 test_plena_pobj_with_checksum.py -6.0")
        sys.exit(1)
    
    db_value = float(sys.argv[1])
    
    print("="*70)
    print("PLM-4Px2x POBJ Write Test (with checksum)")
    print("="*70)
    print()
    
    success = set_zone_2_volume_pobj(db_value)
    verify_via_sync()
    
    print("\n" + "="*70)
    print("✅ SUCCESS" if success else "❌ FAILED")
    print("="*70)
