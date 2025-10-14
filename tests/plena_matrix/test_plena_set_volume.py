#!/usr/bin/env python3
"""
Test script for setting Zone 2 (POKIES) volume on Plena Matrix PLM-4Px2x

Usage:
    python3 test_plena_set_volume.py -6.0

This will attempt to set Zone 2 to -6.0dB using GOBJ command
"""
import socket
import struct
import sys

DEVICE_IP = "192.168.90.17"
RECEIVE_PORT = 12128
TRANSMIT_PORT = 12129

def db_to_lut_index(db_value: float) -> int:
    """
    Convert dB value to DSP Volume LUT index
    Formula: lut_index = (dB + 100.0) / 0.5 + 1
    Range: 1-249 (0 is reserved for MUTE)
    """
    lut_index = int((db_value + 100.0) / 0.5 + 1)
    return max(1, min(249, lut_index))

def lut_index_to_db(lut_index: int) -> float:
    """Convert LUT index back to dB"""
    return (lut_index - 1) * 0.5 - 100.0

def set_zone_2_volume(db_value: float) -> bool:
    """
    Attempt to set Zone 2 (POKIES) volume using GOBJ command
    
    Args:
        db_value: Desired volume in dB (-100 to +24)
    
    Returns:
        True if command was accepted, False otherwise
    """
    object_id = 23  # Zone 2 (POKIES) global object
    lut_index = db_to_lut_index(db_value)
    mute_flag = 0x00  # Unmuted
    
    print(f"Setting Zone 2 (POKIES) to {db_value}dB")
    print(f"  Object ID: {object_id}")
    print(f"  LUT Index: {lut_index}")
    print(f"  Mute Flag: 0x{mute_flag:02x}")
    
    # GOBJ WRITE format:
    # [GOBJ][Is Read Flag:1][Global Object ID:2][NV Commit Flag:1][Object Data:x]
    is_read_flag = 0x00  # Write operation
    nv_commit_flag = 0x00  # Don't commit to NV memory (RAM only)
    
    # Object data: 2-byte DSP Volume LUT Block [LUT index][mute flag]
    object_data = struct.pack('BB', lut_index, mute_flag)
    
    command_data = b'GOBJ' + struct.pack('>BHB', is_read_flag, object_id, nv_commit_flag) + object_data
    
    # Build UDP packet header
    protocol_id = 0x5E41  # PLM-4Px2x protocol
    sub_type = 0x0001     # Master (us)
    sequence = 1
    reserved = 0x0000
    chunk_length = len(command_data)
    
    header = struct.pack('>HHHHH', protocol_id, sub_type, sequence, reserved, chunk_length)
    packet = header + command_data
    
    print(f"\nPacket ({len(packet)} bytes): {packet.hex()}")
    print(f"  Header: {header.hex()}")
    print(f"  Command: {command_data.hex()}")
    print(f"    GOBJ: 474f424a")
    print(f"    Is Read: 0x{is_read_flag:02x}")
    print(f"    Object ID: {object_id} (0x{object_id:04x})")
    print(f"    NV Commit: 0x{nv_commit_flag:02x}")
    print(f"    Object Data: {object_data.hex()}")
    
    # Send command
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', TRANSMIT_PORT))
    sock.settimeout(3.0)
    
    try:
        sock.sendto(packet, (DEVICE_IP, RECEIVE_PORT))
        print(f"\n✓ Sent to {DEVICE_IP}:{RECEIVE_PORT}")
        
        # Wait for response
        response, addr = sock.recvfrom(1024)
        print(f"✓ Response from {addr}: {response.hex()}")
        
        # Parse response
        if len(response) >= 14:
            cmd = response[10:14]
            data = response[14:]
            
            print(f"\nResponse breakdown:")
            print(f"  Command: {cmd}")
            print(f"  Data: {data.hex() if data else '(ACK)'}")
            
            if cmd == b'GOBJ':
                print(f"\n✅ SUCCESS! Volume should be set to {db_value}dB")
                return True
            elif cmd == b'ACKN':
                print(f"\n✅ ACKN received - command accepted")
                return True
            elif cmd == b'NACK':
                if len(data) >= 4:
                    nack_code = struct.unpack('>I', data[:4])[0]
                    print(f"\n❌ NACK code: 0x{nack_code:08x}")
                    
                    # Decode NACK error
                    if nack_code == 0x00030001:
                        print("   Error: Corrupt packet")
                    elif nack_code == 0x00030002:
                        print("   Error: Bad global object ID")
                    elif nack_code == 0x00030003:
                        print("   Error: NV operation failure")
                    elif nack_code == 0x00030004:
                        print("   Error: RAM operation failure")
                    elif nack_code == 0x00030005:
                        print("   Error: Incorrect hardware state")
                else:
                    print(f"\n❌ NACK received")
                return False
            else:
                print(f"\n⚠️  Unexpected response: {cmd}")
                return False
                
    except socket.timeout:
        print("\n⚠️  Timeout - no response from device")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    finally:
        sock.close()

def verify_volume():
    """Read Zone 2 volume via SYNC Type 102 to verify"""
    print("\n" + "="*70)
    print("Verifying actual volume via SYNC Type 102...")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", TRANSMIT_PORT))
    sock.settimeout(3.0)
    
    try:
        # Build SYNC Type 102 request
        packet = struct.pack(">HHHHH", 0x5E41, 0x0001, 0x0001, 0x0000, 5) + b"SYNC" + struct.pack("B", 102)
        sock.sendto(packet, (DEVICE_IP, RECEIVE_PORT))
        
        data, _ = sock.recvfrom(4096)
        payload = data[14:]
        
        # Zone 2 is at offset 32
        zone2_lut = payload[32]
        zone2_flags = payload[32 + 1]
        zone2_db = lut_index_to_db(zone2_lut)
        zone2_muted = (zone2_flags != 0x00)
        
        print(f"\nZone 2 (POKIES) actual state:")
        print(f"  LUT Index: {zone2_lut}")
        print(f"  Volume: {zone2_db:.1f}dB")
        print(f"  Muted: {zone2_muted}")
        
    except Exception as e:
        print(f"Could not verify: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_plena_set_volume.py <db_value>")
        print("Example: python3 test_plena_set_volume.py -6.0")
        sys.exit(1)
    
    try:
        db_value = float(sys.argv[1])
        
        if db_value < -100 or db_value > 24:
            print(f"Error: dB value must be between -100 and +24")
            sys.exit(1)
        
        print("="*70)
        print("Plena Matrix PLM-4Px2x - Zone 2 Volume Control Test")
        print("="*70)
        print()
        
        success = set_zone_2_volume(db_value)
        
        # Always verify actual volume
        verify_volume()
        
        print("\n" + "="*70)
        if success:
            print("Command was accepted by device")
        else:
            print("Command was rejected by device")
        print("="*70)
        
    except ValueError:
        print(f"Error: Invalid dB value '{sys.argv[1]}'")
        sys.exit(1)
