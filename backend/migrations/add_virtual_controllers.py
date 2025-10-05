#!/usr/bin/env python3
"""
Migration: Add Virtual Controller tables

Creates:
- virtual_controllers: Software representation of TV/device controllers
- virtual_devices: Devices mapped to virtual controller ports
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings

def run_migration():
    """Add Virtual Controller tables to database"""

    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    )

    with engine.connect() as conn:
        print("Creating Virtual Controller tables...")

        # Create virtual_controllers table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS virtual_controllers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                controller_name VARCHAR NOT NULL,
                controller_id VARCHAR UNIQUE NOT NULL,
                controller_type VARCHAR NOT NULL,
                protocol VARCHAR,
                venue_name VARCHAR,
                location VARCHAR,
                total_ports INTEGER DEFAULT 5,
                capabilities JSON,
                is_active BOOLEAN DEFAULT 1,
                is_online BOOLEAN DEFAULT 0,
                last_seen TIMESTAMP,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        print("✓ Created virtual_controllers table")

        # Create virtual_devices table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS virtual_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                controller_id INTEGER NOT NULL,
                port_number INTEGER NOT NULL,
                port_id VARCHAR,
                device_name VARCHAR NOT NULL,
                device_type VARCHAR,
                ip_address VARCHAR NOT NULL,
                mac_address VARCHAR,
                port INTEGER,
                protocol VARCHAR,
                connection_config JSON,
                default_channel VARCHAR,
                capabilities JSON,
                is_active BOOLEAN DEFAULT 1,
                is_online BOOLEAN DEFAULT 0,
                last_seen TIMESTAMP,
                tag_ids JSON,
                installation_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (controller_id) REFERENCES virtual_controllers(id) ON DELETE CASCADE
            )
        """))

        print("✓ Created virtual_devices table")

        # Create indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_virtual_controllers_controller_id ON virtual_controllers(controller_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_virtual_devices_controller_id ON virtual_devices(controller_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_virtual_devices_port_id ON virtual_devices(port_id)"))

        print("✓ Created indexes")

        conn.commit()

    print("\n✅ Migration completed successfully!")
    print("\nNew tables:")
    print("  - virtual_controllers: Virtual controller definitions")
    print("  - virtual_devices: Devices mapped to virtual controller ports")

if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)
