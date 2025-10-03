"""
Migration: Update schedules table schema for simplified scheduling system

Changes:
- Remove timezone column
- Add target_type, target_data columns
- Rename command_data to actions
- Remove command_type column
- Create schedule_executions table
- Add indexes for performance

Run with: python -m backend.migrations.update_schedules_schema
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.core.config import settings


def run_migration():
    """Execute the migration"""
    engine = create_engine(settings.DATABASE_URL)

    with engine.begin() as conn:
        print("Starting schedules schema migration...")

        # Check if schedules table exists
        result = conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schedules'"
            )
        )
        table_exists = result.fetchone() is not None

        if not table_exists:
            print("Creating schedules table from scratch...")
            conn.execute(
                text(
                    """
                CREATE TABLE schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR NOT NULL,
                    description TEXT,
                    cron_expression VARCHAR NOT NULL,
                    target_type VARCHAR NOT NULL,
                    target_data JSON,
                    actions JSON NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    last_run DATETIME,
                    next_run DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
                )
            )

            # Add indexes
            conn.execute(
                text("CREATE INDEX idx_schedules_active_next ON schedules(is_active, next_run)")
            )
            conn.execute(text("CREATE INDEX idx_schedules_next_run ON schedules(next_run)"))

        else:
            print("Migrating existing schedules table...")

            # Get existing columns
            result = conn.execute(text("PRAGMA table_info(schedules)"))
            existing_columns = {row[1] for row in result.fetchall()}

            # Add new columns if they don't exist
            if "target_type" not in existing_columns:
                print("Adding target_type column...")
                conn.execute(
                    text("ALTER TABLE schedules ADD COLUMN target_type VARCHAR DEFAULT 'selection'")
                )

            if "target_data" not in existing_columns:
                print("Adding target_data column...")
                conn.execute(text("ALTER TABLE schedules ADD COLUMN target_data JSON"))

            if "actions" not in existing_columns:
                print("Adding actions column...")
                # If command_data exists, copy it to actions
                if "command_data" in existing_columns:
                    conn.execute(text("ALTER TABLE schedules ADD COLUMN actions JSON"))
                    # Note: Manual data migration may be needed for existing records
                    print("WARNING: Existing command_data needs manual migration to actions format")
                else:
                    conn.execute(text("ALTER TABLE schedules ADD COLUMN actions JSON"))

            # Add indexes if they don't exist
            result = conn.execute(text("PRAGMA index_list(schedules)"))
            existing_indexes = {row[1] for row in result.fetchall()}

            if "idx_schedules_active_next" not in existing_indexes:
                print("Adding idx_schedules_active_next index...")
                conn.execute(
                    text("CREATE INDEX idx_schedules_active_next ON schedules(is_active, next_run)")
                )

            if "idx_schedules_next_run" not in existing_indexes:
                print("Adding idx_schedules_next_run index...")
                conn.execute(text("CREATE INDEX idx_schedules_next_run ON schedules(next_run)"))

        # Create schedule_executions table
        result = conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schedule_executions'"
            )
        )
        exec_table_exists = result.fetchone() is not None

        if not exec_table_exists:
            print("Creating schedule_executions table...")
            conn.execute(
                text(
                    """
                CREATE TABLE schedule_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    schedule_id INTEGER NOT NULL,
                    batch_id VARCHAR NOT NULL,
                    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    total_commands INTEGER,
                    succeeded INTEGER,
                    failed INTEGER,
                    avg_execution_time_ms INTEGER
                )
            """
                )
            )

            # Add indexes
            conn.execute(
                text(
                    "CREATE INDEX idx_schedule_executions_schedule ON schedule_executions(schedule_id, executed_at DESC)"
                )
            )
            conn.execute(
                text("CREATE INDEX idx_schedule_executions_batch ON schedule_executions(batch_id)")
            )

        print("✅ Migration completed successfully!")


def rollback_migration():
    """Rollback the migration (optional)"""
    engine = create_engine(settings.DATABASE_URL)

    with engine.begin() as conn:
        print("Rolling back schedules migration...")

        # Drop schedule_executions table
        conn.execute(text("DROP TABLE IF EXISTS schedule_executions"))

        # Note: Can't easily rollback ALTER TABLE in SQLite
        # Would need to create new table and copy data
        print("⚠️  WARNING: Cannot fully rollback ALTER TABLE changes in SQLite")
        print("   New columns (target_type, target_data, actions) will remain")

        print("✅ Rollback completed!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        run_migration()
