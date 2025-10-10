#!/usr/bin/env python3
"""
Migration: Add Unified Command Queue

Updates the command_queue table to support the unified command architecture
where all commands (IR and Network) go through a single queue with protocol routing.

This replaces the old command_queue with a new schema that supports:
- Device type and protocol fields for routing
- Command ID tracking (UUID)
- Execution results and error tracking
- Proper timestamps

Usage:
    cd backend
    python migrations/add_unified_command_queue.py
"""

import sqlite3
import sys
import os


def run_migration():
    """Create unified command queue table"""
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

        # Check if old command_queue exists and drop it
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='command_queue'")
        if cursor.fetchone():
            print("Found existing command_queue table - dropping it...")
            cursor.execute("DROP TABLE IF EXISTS command_queue")
            print("✓ Dropped old command_queue table")

        print("Creating unified command_queue table...")

        # Create the new unified command_queue table
        create_command_queue_sql = """
        CREATE TABLE command_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            command_id TEXT UNIQUE NOT NULL,

            -- Controller/Device info
            controller_id TEXT NOT NULL,
            device_type TEXT NOT NULL,
            protocol TEXT,

            -- Command details
            command TEXT NOT NULL,
            parameters TEXT,

            -- Execution tracking
            status TEXT DEFAULT 'queued',
            priority INTEGER DEFAULT 5,

            -- Results
            result_data TEXT,
            error_message TEXT,

            -- Timestamps
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP
        )
        """
        cursor.execute(create_command_queue_sql)
        print("✓ Created unified 'command_queue' table")

        # Create indexes for efficient querying
        cursor.execute("CREATE INDEX idx_ucq_command_id ON command_queue(command_id)")
        cursor.execute("CREATE INDEX idx_ucq_controller_id ON command_queue(controller_id)")
        cursor.execute("CREATE INDEX idx_ucq_status ON command_queue(status)")
        cursor.execute("CREATE INDEX idx_ucq_status_priority ON command_queue(status, priority)")
        cursor.execute("CREATE INDEX idx_ucq_created_at ON command_queue(created_at)")
        print("✓ Created indexes for command_queue")

        # Commit the changes
        conn.commit()
        print("\nMigration completed successfully!")

        # Verify table was created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='command_queue'")
        if cursor.fetchone():
            print("✓ Verified: command_queue table exists")

            # Show table schema
            cursor.execute("PRAGMA table_info(command_queue)")
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
    print("Running migration: Add Unified Command Queue")
    print("=" * 60)
    print()
    success = run_migration()

    if success:
        print("\n✅ Migration completed successfully!")
        print("\nUnified command queue ready for:")
        print("  - IR commands (ESPHome)")
        print("  - Samsung Legacy TVs (TCP port 55000)")
        print("  - Roku devices (HTTP REST)")
        print("  - LG webOS TVs (WebSocket)")
        print("  - Future protocols...")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
