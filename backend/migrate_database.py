#!/usr/bin/env python3
"""
Database migration utility for handling schema updates
This script helps update existing databases when the schema changes
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.database import SessionLocal, create_tables, engine
from app.core.config import settings


def backup_database():
    """Create a backup of the current database"""
    db_path = Path(settings.DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", ""))

    if not db_path.exists():
        print("No existing database to backup")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.parent / f"tapcommand_backup_{timestamp}.db"

    print(f"Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)
    print(f"✓ Backup created successfully")

    return backup_path


def get_table_names(engine: Engine) -> set:
    """Get all table names in the database"""
    inspector = inspect(engine)
    return set(inspector.get_table_names())


def get_table_columns(engine: Engine, table_name: str) -> set:
    """Get all column names for a table"""
    inspector = inspect(engine)
    try:
        columns = inspector.get_columns(table_name)
        return {col['name'] for col in columns}
    except Exception:
        return set()


def detect_schema_changes():
    """Detect differences between current database and expected schema"""
    print("\n" + "="*50)
    print("Analyzing database schema...")
    print("="*50)

    existing_tables = get_table_names(engine)

    # Import all models to get expected schema
    from app.models.device import Base as DeviceBase
    from app.models.device_management import Base as ManagementBase
    from app.models.ir_codes import Base as IRCodesBase
    from app.models.command_queue import Base as CommandQueueBase
    from app.models.ir_capture import Base as IRCaptureBase
    from app.models.network_discovery import Base as NetworkDiscoveryBase
    from app.models.virtual_controller import Base as VirtualControllerBase

    # Get expected tables from all bases
    expected_tables = set()
    for base in [DeviceBase, ManagementBase, IRCodesBase, CommandQueueBase,
                 IRCaptureBase, NetworkDiscoveryBase, VirtualControllerBase]:
        expected_tables.update(base.metadata.tables.keys())

    # Find missing tables
    missing_tables = expected_tables - existing_tables
    extra_tables = existing_tables - expected_tables

    print(f"\nExisting tables: {len(existing_tables)}")
    print(f"Expected tables: {len(expected_tables)}")

    if missing_tables:
        print(f"\n⚠ Missing tables ({len(missing_tables)}):")
        for table in sorted(missing_tables):
            print(f"  - {table}")

    if extra_tables:
        print(f"\n⚠ Extra tables ({len(extra_tables)}):")
        for table in sorted(extra_tables):
            print(f"  - {table}")

    if not missing_tables and not extra_tables:
        print("\n✓ All expected tables present")

    return {
        'missing_tables': missing_tables,
        'extra_tables': extra_tables,
        'existing_tables': existing_tables
    }


def apply_migrations():
    """Apply necessary migrations to update the database"""
    print("\n" + "="*50)
    print("Applying migrations...")
    print("="*50)

    changes_applied = []

    # Migration 1: Ensure ir_libraries.hidden column
    inspector = inspect(engine)
    if 'ir_libraries' in inspector.get_table_names():
        columns = get_table_columns(engine, 'ir_libraries')
        if 'hidden' not in columns:
            print("\n→ Adding 'hidden' column to ir_libraries table...")
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE ir_libraries ADD COLUMN hidden INTEGER NOT NULL DEFAULT 0"
                ))
                conn.execute(text(
                    "UPDATE ir_libraries SET hidden = CASE WHEN device_category = 'TV' THEN 0 ELSE 1 END"
                ))
            print("  ✓ Column added")
            changes_applied.append("Added hidden column to ir_libraries")

    # Migration 2: Create any missing tables
    schema_info = detect_schema_changes()
    if schema_info['missing_tables']:
        print(f"\n→ Creating {len(schema_info['missing_tables'])} missing tables...")
        create_tables()
        print("  ✓ Tables created")
        changes_applied.append(f"Created {len(schema_info['missing_tables'])} missing tables")

    # Migration 3: Add indexes if they don't exist (example)
    # You can add more specific migrations here as your schema evolves

    if changes_applied:
        print("\n" + "="*50)
        print("Migration Summary:")
        print("="*50)
        for change in changes_applied:
            print(f"  ✓ {change}")
    else:
        print("\n✓ No migrations needed - database is up to date")

    return changes_applied


def verify_migration():
    """Verify the database is working after migration"""
    print("\n" + "="*50)
    print("Verifying database...")
    print("="*50)

    db = SessionLocal()
    try:
        # Try to query some basic tables
        from app.models.user import User, Role

        user_count = db.query(User).count()
        role_count = db.query(Role).count()

        print(f"\n✓ Database verification successful")
        print(f"  - Users: {user_count}")
        print(f"  - Roles: {role_count}")

        return True
    except Exception as e:
        print(f"\n✗ Database verification failed: {e}")
        return False
    finally:
        db.close()


def main():
    """Main migration process"""
    print("\n" + "="*70)
    print(" TapCommand Database Migration Utility")
    print("="*70)

    # Check if database exists
    db_path = Path(settings.DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", ""))
    if not db_path.exists():
        print(f"\n✗ Database not found: {db_path}")
        print("  Run the application first to create the initial database")
        print("  Or use create_template_db.py to create a fresh database")
        sys.exit(1)

    print(f"\nDatabase: {db_path}")
    print(f"Size: {db_path.stat().st_size / 1024:.2f} KB")

    # Ask for confirmation
    response = input("\nCreate backup and apply migrations? (y/N): ")
    if response.lower() != 'y':
        print("Migration cancelled")
        sys.exit(0)

    # Backup
    backup_path = backup_database()

    try:
        # Detect changes
        detect_schema_changes()

        # Apply migrations
        changes = apply_migrations()

        # Verify
        if verify_migration():
            print("\n" + "="*70)
            print(" Migration completed successfully!")
            print("="*70)
            if backup_path:
                print(f"\nBackup saved to: {backup_path}")
        else:
            print("\n" + "="*70)
            print(" Migration completed with warnings")
            print("="*70)
            print(f"\nIf there are issues, restore from backup:")
            print(f"  cp {backup_path} {db_path}")

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        print(f"\nRestore from backup:")
        print(f"  cp {backup_path} {db_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
