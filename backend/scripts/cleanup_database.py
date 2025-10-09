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
        # Get counts before cleanup
        cursor.execute("SELECT COUNT(*) FROM discovered_devices WHERE 1=1")
        discovered_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM managed_devices WHERE 1=1")
        managed_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM device_controllers WHERE 1=1")
        controller_count = cursor.fetchone()[0]

        print(f"\n📊 Current database state:")
        print(f"   • Discovered devices: {discovered_count}")
        print(f"   • Managed devices: {managed_count}")
        print(f"   • Controllers: {controller_count}")

        if discovered_count == 0 and managed_count == 0 and controller_count == 0:
            print("\n✨ Database is already clean!")
            return

        print(f"\n🗑️  Removing cached data...")

        # Delete discovered devices
        cursor.execute("DELETE FROM discovered_devices")
        print(f"   ✓ Removed {discovered_count} discovered devices")

        # Delete managed devices and their relationships
        cursor.execute("DELETE FROM managed_devices")
        print(f"   ✓ Removed {managed_count} managed devices")

        # Delete device controllers
        cursor.execute("DELETE FROM device_controllers")
        print(f"   ✓ Removed {controller_count} controllers")

        # Reset any cached state
        cursor.execute("DELETE FROM device_status WHERE 1=1")
        print(f"   ✓ Cleared device status cache")

        # Optionally clean IR libraries (usually keep these)
        if not keep_ir_libraries:
            cursor.execute("DELETE FROM ir_commands WHERE 1=1")
            cursor.execute("DELETE FROM ir_libraries WHERE 1=1")
            print(f"   ✓ Removed IR libraries and commands")
        else:
            cursor.execute("SELECT COUNT(*) FROM ir_libraries")
            lib_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM ir_commands")
            cmd_count = cursor.fetchone()[0]
            print(f"   ℹ️  Kept {lib_count} IR libraries with {cmd_count} commands")

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
