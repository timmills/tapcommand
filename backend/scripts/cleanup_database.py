#!/usr/bin/env python3
"""
Database cleanup script for fresh SmartVenue installations.
Removes cached discovery data and resets the database to a clean state.
"""

import sqlite3
import sys
from pathlib import Path

def cleanup_database(db_path: str, keep_ir_libraries: bool = True):
    """
    Clean up the database by removing cached/discovered items.

    Args:
        db_path: Path to the SQLite database file
        keep_ir_libraries: If True, keeps IR libraries and commands (default: True)
    """

    print(f"🧹 Cleaning up database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Get counts before cleanup (with error handling for missing tables)
        def safe_count(table_name):
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                return cursor.fetchone()[0]
            except sqlite3.Error:
                return 0

        discovered_count = safe_count("device_discoveries")
        managed_count = safe_count("managed_devices")
        devices_count = safe_count("devices")  # Legacy devices table
        virtual_controller_count = safe_count("virtual_controllers")
        virtual_device_count = safe_count("virtual_devices")
        network_scan_count = safe_count("network_scan_cache")
        command_history_count = safe_count("command_history")
        command_queue_count = safe_count("command_queue")
        ir_ports_count = safe_count("ir_ports")

        print(f"\n📊 Current database state:")
        print(f"   • Discovered devices: {discovered_count}")
        print(f"   • Managed devices: {managed_count}")
        print(f"   • Legacy devices: {devices_count}")
        print(f"   • Virtual controllers: {virtual_controller_count}")
        print(f"   • Virtual devices: {virtual_device_count}")
        print(f"   • Network scan cache: {network_scan_count}")
        print(f"   • Command history: {command_history_count}")
        print(f"   • Command queue: {command_queue_count}")
        print(f"   • IR ports: {ir_ports_count}")

        total_items = discovered_count + managed_count + devices_count + virtual_controller_count + virtual_device_count + network_scan_count + command_history_count + command_queue_count
        if total_items == 0:
            print("\n✨ Database is already clean!")
            return

        print(f"\n🗑️  Removing cached data...")

        # Delete discovered devices
        if discovered_count > 0:
            cursor.execute("DELETE FROM device_discoveries")
            print(f"   ✓ Removed {discovered_count} discovered devices")

        # Delete managed devices and their relationships
        if managed_count > 0:
            cursor.execute("DELETE FROM managed_devices")
            print(f"   ✓ Removed {managed_count} managed devices")

        # Delete IR ports (orphaned port configurations)
        if ir_ports_count > 0:
            cursor.execute("DELETE FROM ir_ports")
            print(f"   ✓ Removed {ir_ports_count} IR port configurations")

        # Delete legacy devices table
        if devices_count > 0:
            cursor.execute("DELETE FROM devices")
            print(f"   ✓ Removed {devices_count} legacy devices")

        # Delete virtual controllers and devices
        if virtual_device_count > 0:
            cursor.execute("DELETE FROM virtual_devices")
            print(f"   ✓ Removed {virtual_device_count} virtual devices")

        if virtual_controller_count > 0:
            cursor.execute("DELETE FROM virtual_controllers")
            print(f"   ✓ Removed {virtual_controller_count} virtual controllers")

        # Clear network scan cache
        if network_scan_count > 0:
            cursor.execute("DELETE FROM network_scan_cache")
            print(f"   ✓ Cleared {network_scan_count} network scan entries")

        # Clear command queue and history
        if command_queue_count > 0:
            cursor.execute("DELETE FROM command_queue")
            print(f"   ✓ Cleared {command_queue_count} queued commands")

        if command_history_count > 0:
            cursor.execute("DELETE FROM command_history")
            print(f"   ✓ Cleared {command_history_count} command history entries")

        # Reset any cached state (device_status might not exist)
        try:
            cursor.execute("DELETE FROM device_status")
            print(f"   ✓ Cleared device status cache")
        except sqlite3.Error:
            pass

        # Optionally clean IR libraries (usually keep these)
        if not keep_ir_libraries:
            cursor.execute("DELETE FROM ir_commands WHERE 1=1")
            cursor.execute("DELETE FROM ir_libraries WHERE 1=1")
            print(f"   ✓ Removed IR libraries and commands")
        else:
            lib_count = safe_count("ir_libraries")
            cmd_count = safe_count("ir_commands")
            if lib_count > 0 or cmd_count > 0:
                print(f"   ℹ️  Kept {lib_count} IR libraries with {cmd_count} commands")

        # Always keep channels
        channel_count = safe_count("channels")
        if channel_count > 0:
            print(f"   ℹ️  Kept {channel_count} channels")

        conn.commit()
        print(f"\n✅ Database cleanup completed successfully!")

    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


def main():
    # Find database file
    backend_dir = Path(__file__).parent.parent
    db_path = backend_dir / "smartvenue.db"

    if not db_path.exists():
        print(f"❌ Database not found at: {db_path}")
        sys.exit(1)

    # Parse arguments
    keep_ir = "--remove-ir" not in sys.argv

    cleanup_database(str(db_path), keep_ir_libraries=keep_ir)


if __name__ == "__main__":
    main()
