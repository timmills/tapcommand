#!/usr/bin/env python3
"""
Database migration script to remove Foxtel distinction and consolidate to universal devices.

This script:
1. Renames foxtel_box_number column to device_number in ir_ports table
2. Updates all device_type values to "universal" in both managed_devices and device_discoveries tables
3. Handles the migration safely with proper error handling

Run this script after updating the codebase to remove Foxtel-specific logic.
"""

import sqlite3
import os
import sys
from pathlib import Path

# Database path - adjust if needed
DB_PATH = "tapcommand.db"

def migrate_database():
    """Perform the database migration to remove Foxtel distinction"""
    db_path = DB_PATH

    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}")
        return False

    print(f"Starting migration on database: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Step 1: Check if the column rename is needed
        cursor.execute("PRAGMA table_info(ir_ports)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'foxtel_box_number' in columns and 'device_number' not in columns:
            print("Renaming foxtel_box_number column to device_number...")

            # SQLite doesn't support direct column rename, so we need to recreate the table
            # First, backup the data
            cursor.execute("""
                CREATE TABLE ir_ports_backup AS
                SELECT * FROM ir_ports
            """)

            # Drop the original table
            cursor.execute("DROP TABLE ir_ports")

            # Recreate the table with the new column name
            cursor.execute("""
                CREATE TABLE ir_ports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    port_number INTEGER NOT NULL,
                    port_id VARCHAR,
                    gpio_pin VARCHAR,
                    connected_device_name VARCHAR,
                    is_active BOOLEAN DEFAULT 1,
                    cable_length VARCHAR,
                    installation_notes TEXT,
                    tag_ids JSON,
                    default_channel VARCHAR,
                    device_number INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES managed_devices (id)
                )
            """)

            # Copy data back with column rename
            cursor.execute("""
                INSERT INTO ir_ports (
                    id, device_id, port_number, port_id, gpio_pin, connected_device_name,
                    is_active, cable_length, installation_notes, tag_ids, default_channel,
                    device_number, created_at, updated_at
                )
                SELECT
                    id, device_id, port_number, port_id, gpio_pin, connected_device_name,
                    is_active, cable_length, installation_notes, tag_ids, default_channel,
                    foxtel_box_number, created_at, updated_at
                FROM ir_ports_backup
            """)

            # Drop the backup table
            cursor.execute("DROP TABLE ir_ports_backup")

            print("✓ Column foxtel_box_number renamed to device_number")

        elif 'device_number' in columns:
            print("✓ Column device_number already exists, skipping rename")
        else:
            print("✗ Unexpected table structure, manual intervention required")
            return False

        # Step 2: Update all device types to universal in managed_devices
        cursor.execute("SELECT COUNT(*) FROM managed_devices WHERE device_type != 'universal'")
        count = cursor.fetchone()[0]

        if count > 0:
            print(f"Updating {count} managed devices to universal type...")
            cursor.execute("UPDATE managed_devices SET device_type = 'universal'")
            print(f"✓ Updated {count} managed devices to universal")
        else:
            print("✓ All managed devices already universal")

        # Step 3: Update all device types to universal in device_discoveries
        cursor.execute("SELECT COUNT(*) FROM device_discoveries WHERE device_type != 'universal'")
        count = cursor.fetchone()[0]

        if count > 0:
            print(f"Updating {count} discovered devices to universal type...")
            cursor.execute("UPDATE device_discoveries SET device_type = 'universal'")
            print(f"✓ Updated {count} discovered devices to universal")
        else:
            print("✓ All discovered devices already universal")

        # Step 4: Update the legacy devices table if it exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='devices'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM devices WHERE device_type != 'universal'")
            count = cursor.fetchone()[0]

            if count > 0:
                print(f"Updating {count} legacy devices to universal type...")
                cursor.execute("UPDATE devices SET device_type = 'universal'")
                print(f"✓ Updated {count} legacy devices to universal")
            else:
                print("✓ All legacy devices already universal")

        # Commit all changes
        conn.commit()
        print("\n✅ Migration completed successfully!")
        print("All Foxtel-specific distinctions have been removed.")
        print("All devices are now universal with support for multi-device setups via device_number field.")

        return True

    except sqlite3.Error as e:
        print(f"✗ Database error during migration: {e}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        print(f"✗ Unexpected error during migration: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def verify_migration():
    """Verify the migration was successful"""
    db_path = DB_PATH

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("\n🔍 Verifying migration...")

        # Check ir_ports table structure
        cursor.execute("PRAGMA table_info(ir_ports)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'device_number' in columns and 'foxtel_box_number' not in columns:
            print("✓ ir_ports table structure correct")
        else:
            print("✗ ir_ports table structure incorrect")
            return False

        # Check device types
        cursor.execute("SELECT DISTINCT device_type FROM managed_devices")
        managed_types = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT DISTINCT device_type FROM device_discoveries")
        discovery_types = [row[0] for row in cursor.fetchall()]

        if managed_types == ['universal'] and discovery_types == ['universal']:
            print("✓ All devices are universal type")
        else:
            print(f"✗ Found non-universal device types: managed={managed_types}, discovery={discovery_types}")
            return False

        print("✅ Migration verification successful!")
        return True

    except sqlite3.Error as e:
        print(f"✗ Database error during verification: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🔄 Starting Foxtel distinction removal migration...")
    print("This will consolidate all devices to universal type and rename foxtel_box_number to device_number")

    # Perform migration
    if migrate_database():
        # Verify migration
        if verify_migration():
            print("\n🎉 Migration completed and verified successfully!")
            print("\nNext steps:")
            print("1. Restart your backend application")
            print("2. Test device management functionality")
            print("3. Verify IR command sending works correctly")
        else:
            print("\n⚠️  Migration completed but verification failed")
            sys.exit(1)
    else:
        print("\n❌ Migration failed")
        sys.exit(1)