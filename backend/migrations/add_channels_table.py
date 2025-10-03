#!/usr/bin/env python3
"""
Migration: Add channels table for Australian TV channels
"""

import sqlite3
import sys
import os
from pathlib import Path


def run_migration():
    """Create channels table"""
    # Use the default database path
    db_path = "smartvenue.db"

    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        print("Please run the backend server first to create the database.")
        return False

    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='channels'")
        if cursor.fetchone():
            print("Channels table already exists.")
            conn.close()
            return True

        print("Creating channels table...")

        # Create channels table
        create_table_sql = """
        CREATE TABLE channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            broadcaster_network TEXT NOT NULL,
            channel_name TEXT NOT NULL,
            lcn TEXT,
            foxtel_number TEXT,
            broadcast_hours TEXT,
            format TEXT,
            programming_content TEXT,
            availability TEXT,
            logo_url TEXT,
            notes TEXT,
            internal BOOLEAN NOT NULL DEFAULT 0,
            disabled BOOLEAN NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        cursor.execute(create_table_sql)
        print("Created 'channels' table")

        # Create indexes for better performance
        cursor.execute("CREATE INDEX idx_channels_platform ON channels(platform)")
        cursor.execute("CREATE INDEX idx_channels_broadcaster ON channels(broadcaster_network)")
        cursor.execute("CREATE INDEX idx_channels_name ON channels(channel_name)")
        cursor.execute("CREATE INDEX idx_channels_lcn ON channels(lcn)")
        cursor.execute("CREATE INDEX idx_channels_disabled ON channels(disabled)")
        print("Created indexes for channels table")

        # Commit the changes
        conn.commit()
        print("Migration completed successfully!")

        # Verify the table was created
        cursor.execute("PRAGMA table_info(channels)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"Table columns: {columns}")

        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    print("Running migration: Add channels table...")
    success = run_migration()

    if success:
        print("\n✅ Migration completed successfully!")
        print("You can now run the CSV import script.")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)