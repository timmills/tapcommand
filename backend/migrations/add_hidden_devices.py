#!/usr/bin/env python3
"""
Migration: Add is_hidden column to network_scan_cache

Allows users to hide devices from discovery list
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from app.core.config import settings

def run_migration():
    """Add is_hidden column to network_scan_cache table"""

    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    )

    # Check if column already exists
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('network_scan_cache')]

    if 'is_hidden' in columns:
        print("✓ Column 'is_hidden' already exists in network_scan_cache")
        return

    with engine.connect() as conn:
        print("Adding is_hidden column to network_scan_cache...")

        # Add is_hidden column
        conn.execute(text("""
            ALTER TABLE network_scan_cache
            ADD COLUMN is_hidden BOOLEAN DEFAULT 0
        """))

        conn.commit()

    print("\n✅ Migration completed successfully!")
    print("\nChanges:")
    print("  - Added is_hidden column to network_scan_cache")
    print("  - Default value: False (0)")

if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)
