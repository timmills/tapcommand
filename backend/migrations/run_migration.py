#!/usr/bin/env python3
"""
Database Migration Runner
Run SQL migrations against the SQLite database
"""

import sqlite3
import os
import sys
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent / "smartvenue.db"
MIGRATIONS_DIR = Path(__file__).parent


def run_migration(migration_file: str):
    """Run a SQL migration file"""
    migration_path = MIGRATIONS_DIR / migration_file

    if not migration_path.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False

    print(f"📋 Running migration: {migration_file}")

    try:
        # Read migration SQL
        with open(migration_path, 'r') as f:
            sql = f.read()

        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Execute migration (split by semicolon for multiple statements)
        statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]

        for statement in statements:
            if statement:
                print(f"  Executing: {statement[:60]}...")
                cursor.execute(statement)

        conn.commit()
        conn.close()

        print(f"✅ Migration completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


def check_columns_exist():
    """Check if migration has already been applied"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if fallback_ir_controller column exists
    cursor.execute("PRAGMA table_info(virtual_devices)")
    columns = [col[1] for col in cursor.fetchall()]

    conn.close()

    return 'fallback_ir_controller' in columns


if __name__ == "__main__":
    print("🔧 SmartVenue Database Migration Runner")
    print(f"Database: {DB_PATH}")
    print()

    # Check if already applied
    if check_columns_exist():
        print("✅ Migration already applied (columns exist)")
        sys.exit(0)

    # Run migration
    success = run_migration("001_add_hybrid_support_to_virtual_devices.sql")

    if success:
        print()
        print("✅ All migrations completed!")
        print("You can now restart the backend server.")
    else:
        print()
        print("❌ Migration failed. Please check the error above.")
        sys.exit(1)
