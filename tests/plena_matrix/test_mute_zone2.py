#!/usr/bin/env python3
"""Test muting Zone 2 - comparing two approaches"""
import socket
import struct

DEVICE_IP = "192.168.90.17"
RECEIVE_PORT = 12128
TRANSMIT_PORT = 12129

def lut_index_to_db(lut_index: int) -> float:
    return (lut_index - 1) * 0.5 - 100.0

def read_zone2_current_volume():
    """Read current Zone 2 volume via SYNC Type 102"""
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
        
        print(f"Current Zone 2 state:")
        print(f"  LUT: {zone2_lut} ({zone2_db:.1f}dB)")
        print(f"  Flags: 0x{zone2_flags:02x} (Muted: {zone2_flags != 0})")
        
        return zone2_lut, zone2_flags
        
    finally:
        sock.close()

def send_pobj_mute(lut_index, mute_flag):
    """Send POBJ write with specified LUT and mute flag"""
    preset_object_id = 52  # Zone 2
    
    command_data = (
        b'POBJ' +
        struct.pack('B', 0x00) +              # IsRead = write
        struct.pack('B', 0x00) +              # PresetNumber = live
        struct.pack('>H', preset_object_id) + # Object ID
        struct.pack('B', 0x00) +              # NV commit
        struct.pack('BB', lut_index, mute_flag) + # Data
        struct.pack('B', 0x00)                # Checksum
    )
    
    header = struct.pack('>HHHHH', 0x5E41, 0x0001, 1, 0x0000, len(command_data))
    packet = header + command_data
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', TRANSMIT_PORT))
    sock.settimeout(3.0)
    
    try:
        sock.sendto(packet, (DEVICE_IP, RECEIVE_PORT))
        response, _ = sock.recvfrom(1024)
        cmd = response[10:14]
        return cmd
    except:
        return b'TIME'
    finally:
        sock.close()

print("="*70)
print("Testing Zone 2 Mute - Two Approaches")
print("="*70)
print()

# Read current state
current_lut, current_flags = read_zone2_current_volume()

print("\n" + "="*70)
print("Approach 1: Mute with LUT=0 (your suggestion)")
print("="*70)
result1 = send_pobj_mute(lut_index=0x00, mute_flag=0x01)
print(f"Response: {result1}")

import time
time.sleep(1)

# Check what happened
new_lut1, new_flags1 = read_zone2_current_volume()

print("\n" + "="*70)
print("Approach 2: Mute with current LUT preserved")
print("="*70)

# First unmute to reset
send_pobj_mute(lut_index=current_lut, mute_flag=0x00)
time.sleep(1)

# Now mute with current LUT
result2 = send_pobj_mute(lut_index=current_lut, mute_flag=0x01)
print(f"Response: {result2}")

time.sleep(1)

# Check result
new_lut2, new_flags2 = read_zone2_current_volume()

print("\n" + "="*70)
print("RESULTS:")
print("="*70)
print(f"Approach 1 (LUT=0): LUT changed from {current_lut} to {new_lut1}")
print(f"Approach 2 (LUT={current_lut}): LUT changed from {current_lut} to {new_lut2}")
print()
if new_lut1 == 0:
    print("⚠️  WARNING: Approach 1 sets volume to mute/off (LUT=0)")
    print("✅ RECOMMENDATION: Use Approach 2 (preserve LUT when muting)")
else:
    print("✅ Approach 1 preserves volume")
