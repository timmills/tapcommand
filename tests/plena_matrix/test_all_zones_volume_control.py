#!/usr/bin/env python3
"""
Test volume control on all 4 zones of PLM-4Px2x
Tests both volume setting and mute/unmute
"""
import socket
import struct
import sys
import time

DEVICE_IP = "192.168.90.17"
RECEIVE_PORT = 12128
TRANSMIT_PORT = 12129

def lut_index_to_db(lut_index: int) -> float:
    """Convert LUT index to dB"""
    return (lut_index - 1) * 0.5 - 100.0

def db_to_lut_index(db_value: float) -> int:
    """Convert dB to LUT index"""
    lut_index = int((db_value + 100.0) / 0.5 + 1)
    return max(1, min(249, lut_index))

def read_all_zones():
    """Read current state of all 4 zones via SYNC Type 102"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", TRANSMIT_PORT))
    sock.settimeout(3.0)

    try:
        packet = struct.pack(">HHHHH", 0x5E41, 0x0001, 0x0001, 0x0000, 5) + b"SYNC" + struct.pack("B", 102)
        sock.sendto(packet, (DEVICE_IP, RECEIVE_PORT))

        data, _ = sock.recvfrom(4096)
        payload = data[14:]

        # Zone offsets in SYNC Type 102
        zone_offsets = {1: 17, 2: 32, 3: 47, 4: 62}
        zone_names = {1: "BAR", 2: "POKIES", 3: "OUTSIDE", 4: "BISTRO"}

        zones = {}
        for zone_num, offset in zone_offsets.items():
            lut = payload[offset]
            flags = payload[offset + 1]
            db = lut_index_to_db(lut)
            muted = (flags != 0x00)

            zones[zone_num] = {
                "name": zone_names[zone_num],
                "lut": lut,
                "db": db,
                "flags": flags,
                "muted": muted
            }

        return zones

    finally:
        sock.close()

def set_zone_volume(zone_number: int, db_value: float) -> bool:
    """Set zone volume using POBJ command"""
    zone_object_ids = {1: 26, 2: 52, 3: 78, 4: 104}
    preset_object_id = zone_object_ids[zone_number]
    lut_index = db_to_lut_index(db_value)

    command_data = (
        b'POBJ' +
        struct.pack('B', 0x00) +              # IsRead = write
        struct.pack('B', 0x00) +              # PresetNumber = live
        struct.pack('>H', preset_object_id) + # Object ID
        struct.pack('B', 0x00) +              # NV commit
        struct.pack('BB', lut_index, 0x00) +  # LUT + flags (unmuted)
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
        return cmd in [b'POBJ', b'ACKN']
    except:
        return False
    finally:
        sock.close()

def set_zone_mute(zone_number: int, mute: bool, current_lut: int) -> bool:
    """Mute/unmute zone (preserving volume)"""
    zone_object_ids = {1: 26, 2: 52, 3: 78, 4: 104}
    preset_object_id = zone_object_ids[zone_number]
    mute_flag = 0x01 if mute else 0x00

    command_data = (
        b'POBJ' +
        struct.pack('B', 0x00) +              # IsRead = write
        struct.pack('B', 0x00) +              # PresetNumber = live
        struct.pack('>H', preset_object_id) + # Object ID
        struct.pack('B', 0x00) +              # NV commit
        struct.pack('BB', current_lut, mute_flag) +  # Preserve LUT + mute flag
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
        return cmd in [b'POBJ', b'ACKN']
    except:
        return False
    finally:
        sock.close()

def print_zones(zones):
    """Print zone status table"""
    print(f"{'Zone':<10} {'Name':<10} {'LUT':<5} {'dB':<8} {'Muted':<8}")
    print("-" * 50)
    for zone_num, info in sorted(zones.items()):
        mute_str = "YES" if info["muted"] else "NO"
        print(f"Zone {zone_num:<5} {info['name']:<10} {info['lut']:<5} {info['db']:<8.1f} {mute_str:<8}")

if __name__ == "__main__":
    print("=" * 70)
    print("PLM-4Px2x - All Zones Volume Control Test")
    print("=" * 70)
    print()

    # Read initial state
    print("📊 Reading initial state...")
    initial_zones = read_all_zones()
    print_zones(initial_zones)
    print()

    # Test volume control on each zone
    test_db = -6.0
    print(f"🔊 Testing volume set to {test_db}dB on all zones...")

    for zone_num in [1, 2, 3, 4]:
        zone_name = initial_zones[zone_num]["name"]
        print(f"  Setting Zone {zone_num} ({zone_name}) to {test_db}dB...", end=" ")

        if set_zone_volume(zone_num, test_db):
            print("✅")
        else:
            print("❌ FAILED")

        time.sleep(0.5)

    time.sleep(1)

    # Verify volume changes
    print("\n📊 Verifying volume changes...")
    after_volume = read_all_zones()
    print_zones(after_volume)
    print()

    # Test mute on all zones (preserving volume)
    print("🔇 Testing mute on all zones (preserving volume)...")

    for zone_num in [1, 2, 3, 4]:
        zone_name = after_volume[zone_num]["name"]
        current_lut = after_volume[zone_num]["lut"]
        print(f"  Muting Zone {zone_num} ({zone_name}, LUT={current_lut})...", end=" ")

        if set_zone_mute(zone_num, True, current_lut):
            print("✅")
        else:
            print("❌ FAILED")

        time.sleep(0.5)

    time.sleep(1)

    # Verify mute
    print("\n📊 Verifying mute state...")
    after_mute = read_all_zones()
    print_zones(after_mute)
    print()

    # Test unmute on all zones
    print("🔊 Testing unmute on all zones...")

    for zone_num in [1, 2, 3, 4]:
        zone_name = after_mute[zone_num]["name"]
        current_lut = after_mute[zone_num]["lut"]
        print(f"  Unmuting Zone {zone_num} ({zone_name}, LUT={current_lut})...", end=" ")

        if set_zone_mute(zone_num, False, current_lut):
            print("✅")
        else:
            print("❌ FAILED")

        time.sleep(0.5)

    time.sleep(1)

    # Final state
    print("\n📊 Final state...")
    final_zones = read_all_zones()
    print_zones(final_zones)
    print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    volume_success = all(
        abs(final_zones[z]["db"] - test_db) < 0.6 for z in [1, 2, 3, 4]
    )

    mute_preserved = all(
        final_zones[z]["lut"] == after_mute[z]["lut"] for z in [1, 2, 3, 4]
    )

    all_unmuted = all(
        not final_zones[z]["muted"] for z in [1, 2, 3, 4]
    )

    if volume_success:
        print("✅ Volume control working on all zones")
    else:
        print("❌ Volume control issues detected")

    if mute_preserved:
        print("✅ Mute preserves volume level (LUT unchanged)")
    else:
        print("❌ Mute changed volume levels")

    if all_unmuted:
        print("✅ All zones unmuted successfully")
    else:
        print("❌ Some zones still muted")

    print("=" * 70)
