#!/usr/bin/env python3
"""
Migration: Add Command Queue System

Creates three new tables:
1. command_queue - Queue for reliable command execution with retry logic
2. port_status - Track last successful channel per port for UI feedback
3. command_history - 7-day rotating log of all command executions

Usage:
    cd backend
    python migrations/add_command_queue_system.py
"""

import sqlite3
import sys
import os


def run_migration():
    """Create command queue system tables"""
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

        # Check if tables already exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='command_queue'")
        if cursor.fetchone():
            print("Command queue tables already exist.")
            conn.close()
            return True

        print("Creating command queue system tables...")

        # 1. Create command_queue table
        create_command_queue_sql = """
        CREATE TABLE command_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            hostname TEXT NOT NULL,
            command TEXT NOT NULL,
            port INTEGER DEFAULT 0,
            channel TEXT,
            digit INTEGER,

            command_class TEXT NOT NULL,
            batch_id TEXT,

            status TEXT DEFAULT 'pending',
            priority INTEGER DEFAULT 0,
            scheduled_at TIMESTAMP,

            attempts INTEGER DEFAULT 0,
            max_attempts INTEGER DEFAULT 3,
            last_attempt_at TIMESTAMP,
            completed_at TIMESTAMP,

            success BOOLEAN,
            error_message TEXT,
            execution_time_ms INTEGER,

            routing_method TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT,
            user_ip TEXT,
            notes TEXT
        )
        """
        cursor.execute(create_command_queue_sql)
        print("✓ Created 'command_queue' table")

        # Create indexes for command_queue
        cursor.execute("CREATE INDEX idx_cq_status_priority ON command_queue(status, priority)")
        cursor.execute("CREATE INDEX idx_cq_hostname_status ON command_queue(hostname, status)")
        cursor.execute("CREATE INDEX idx_cq_batch ON command_queue(batch_id)")
        cursor.execute("CREATE INDEX idx_cq_scheduled ON command_queue(scheduled_at)")
        cursor.execute("CREATE INDEX idx_cq_created ON command_queue(created_at)")
        cursor.execute("CREATE INDEX idx_cq_hostname ON command_queue(hostname)")
        cursor.execute("CREATE INDEX idx_cq_status ON command_queue(status)")
        cursor.execute("CREATE INDEX idx_cq_priority ON command_queue(priority)")
        print("✓ Created indexes for command_queue")

        # 2. Create port_status table
        create_port_status_sql = """
        CREATE TABLE port_status (
            hostname TEXT NOT NULL,
            port INTEGER NOT NULL,
            last_channel TEXT,
            last_command TEXT,
            last_command_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (hostname, port)
        )
        """
        cursor.execute(create_port_status_sql)
        print("✓ Created 'port_status' table")

        # 3. Create command_history table
        create_command_history_sql = """
        CREATE TABLE command_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            queue_id INTEGER,
            hostname TEXT NOT NULL,
            command TEXT NOT NULL,
            port INTEGER,
            channel TEXT,
            success BOOLEAN NOT NULL,
            execution_time_ms INTEGER,
            routing_method TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        cursor.execute(create_command_history_sql)
        print("✓ Created 'command_history' table")

        # Create indexes for command_history
        cursor.execute("CREATE INDEX idx_ch_hostname_created ON command_history(hostname, created_at)")
        cursor.execute("CREATE INDEX idx_ch_hostname ON command_history(hostname)")
        cursor.execute("CREATE INDEX idx_ch_created ON command_history(created_at)")
        print("✓ Created indexes for command_history")

        # Commit the changes
        conn.commit()
        print("\nMigration completed successfully!")

        # Verify tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('command_queue', 'port_status', 'command_history')")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Created tables: {tables}")

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
    print("Running migration: Add Command Queue System")
    print("=" * 60)
    print()
    success = run_migration()

    if success:
        print("\n✅ Migration completed successfully!")
        print("\nNew tables created:")
        print("  - command_queue: Queue for reliable command execution")
        print("  - port_status: Track last channel per port")
        print("  - command_history: 7-day rotating command log")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
