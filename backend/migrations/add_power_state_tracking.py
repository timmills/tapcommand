"""
Add power state tracking to port_status table

This migration adds two new columns to track the last known power state
for each port, following the same pattern as channel tracking.
"""
import sqlite3
from pathlib import Path

def migrate():
    """Add power state tracking columns to port_status table"""
    db_path = Path(__file__).parent.parent / "smartvenue.db"

    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(port_status)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'last_power_state' in columns:
            print("Migration already applied - columns exist")
            return

        # Add new columns
        print("Adding last_power_state column...")
        cursor.execute("""
            ALTER TABLE port_status
            ADD COLUMN last_power_state TEXT
        """)

        print("Adding last_power_command_at column...")
        cursor.execute("""
            ALTER TABLE port_status
            ADD COLUMN last_power_command_at TIMESTAMP
        """)

        conn.commit()
        print("✅ Migration completed: Added power state tracking columns")

        # Verify columns were added
        cursor.execute("PRAGMA table_info(port_status)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"   Current columns: {', '.join(columns)}")

    except sqlite3.Error as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
