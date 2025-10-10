#!/usr/bin/env python3
"""
Migration: Add local_logo_path field to channels table
"""

import sqlite3
import sys
import os
from pathlib import Path


def run_migration():
    """Add local_logo_path column to channels table"""
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

        # Check if column already exists
        cursor.execute("PRAGMA table_info(channels)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'local_logo_path' in columns:
            print("local_logo_path column already exists in channels table.")
            conn.close()
            return True

        print("Adding local_logo_path column to channels table...")

        # Add local_logo_path column
        cursor.execute("ALTER TABLE channels ADD COLUMN local_logo_path TEXT")
        print("Added 'local_logo_path' column")

        # Commit the changes
        conn.commit()
        print("Migration completed successfully!")

        # Verify the changes
        cursor.execute("PRAGMA table_info(channels)")
        columns_after = [row[1] for row in cursor.fetchall()]
        print(f"Updated table columns: {columns_after}")

        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    print("Running migration: Add local_logo_path field...")
    success = run_migration()

    if success:
        print("\n✅ Migration completed successfully!")
        print("You can now run the icon download script.")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)