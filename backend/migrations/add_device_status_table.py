#!/usr/bin/env python3
"""
Migration: Add Device Status Table

Creates a table to track real-time status of network devices including:
- Power state (on/off)
- Online status
- Current channel/input
- Last check timestamp

This enables status monitoring without polluting the command queue.

Usage:
    cd backend
    python migrations/add_device_status_table.py
"""

import sqlite3
import sys
import os


def run_migration():
    """Create device_status table"""
    # Use the default database path
    db_path = "tapcommand.db"

    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        print("Please run the backend server first to create the database.")
        return False

    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if device_status exists and drop it
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='device_status'")
        if cursor.fetchone():
            print("Found existing device_status table - dropping it...")
            cursor.execute("DROP TABLE IF EXISTS device_status")
            print("✓ Dropped old device_status table")

        print("Creating device_status table...")

        # Create the device_status table
        create_device_status_sql = """
        CREATE TABLE device_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Device identification
            controller_id TEXT UNIQUE NOT NULL,
            device_type TEXT NOT NULL,
            protocol TEXT,

            -- Status information
            is_online BOOLEAN DEFAULT 0,
            power_state TEXT DEFAULT 'unknown',
            current_channel TEXT,
            current_input TEXT,
            volume_level INTEGER,
            is_muted BOOLEAN,

            -- Additional metadata
            model_info TEXT,
            firmware_version TEXT,

            -- Check method and timing
            check_method TEXT,
            check_interval_seconds INTEGER DEFAULT 300,

            -- Timestamps
            last_checked_at TIMESTAMP,
            last_changed_at TIMESTAMP,
            last_online_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        cursor.execute(create_device_status_sql)
        print("✓ Created 'device_status' table")

        # Create indexes for efficient querying
        cursor.execute("CREATE INDEX idx_ds_controller_id ON device_status(controller_id)")
        cursor.execute("CREATE INDEX idx_ds_device_type ON device_status(device_type)")
        cursor.execute("CREATE INDEX idx_ds_is_online ON device_status(is_online)")
        cursor.execute("CREATE INDEX idx_ds_power_state ON device_status(power_state)")
        cursor.execute("CREATE INDEX idx_ds_last_checked ON device_status(last_checked_at)")
        print("✓ Created indexes for device_status")

        # Commit the changes
        conn.commit()
        print("\nMigration completed successfully!")

        # Verify table was created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='device_status'")
        if cursor.fetchone():
            print("✓ Verified: device_status table exists")

            # Show table schema
            cursor.execute("PRAGMA table_info(device_status)")
            columns = cursor.fetchall()
            print("\nTable schema:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")

        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Running migration: Add Device Status Table")
    print("=" * 60)
    print()
    success = run_migration()

    if success:
        print("\n✅ Migration completed successfully!")
        print("\nDevice status tracking ready for:")
        print("  - Real-time power state monitoring")
        print("  - Online/offline detection")
        print("  - Current channel tracking")
        print("  - Protocol-specific status queries")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
