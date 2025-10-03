#!/usr/bin/env python3
"""
Migration: Add version control columns to esp_templates table
"""

import sqlite3
import sys
import os
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings


def run_migration():
    """Add version and revision columns to esp_templates table"""
    db_path = settings.SQLITE_DATABASE_PATH

    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        print("Please run the backend server first to create the database.")
        return False

    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if columns already exist
        cursor.execute("PRAGMA table_info(esp_templates)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'version' in columns and 'revision' in columns:
            print("Version control columns already exist in esp_templates table.")
            conn.close()
            return True

        print("Adding version control columns to esp_templates table...")

        # Add version column with default value
        if 'version' not in columns:
            cursor.execute("ALTER TABLE esp_templates ADD COLUMN version TEXT NOT NULL DEFAULT '1.0.0'")
            print("Added 'version' column")

        # Add revision column with default value
        if 'revision' not in columns:
            cursor.execute("ALTER TABLE esp_templates ADD COLUMN revision INTEGER NOT NULL DEFAULT 1")
            print("Added 'revision' column")

        # Commit the changes
        conn.commit()
        print("Migration completed successfully!")

        # Verify the changes
        cursor.execute("PRAGMA table_info(esp_templates)")
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
    print("Running migration: Add template versioning...")
    success = run_migration()

    if success:
        print("\n✅ Migration completed successfully!")
        print("You can now restart the backend server.")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)