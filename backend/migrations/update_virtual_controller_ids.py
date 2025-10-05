#!/usr/bin/env python3
"""
Migration: Update Virtual Controller IDs to use MAC-based format

Changes controller IDs from: vc-{vendor}-{ip_octet}
To: nw-{last_6_mac_chars}

Example: vc-samsung-electronics-co.,ltd-50 -> nw-b85a97
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings

def run_migration():
    """Update Virtual Controller IDs to MAC-based format"""

    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    )

    with engine.connect() as conn:
        print("Fetching Virtual Controllers and their device MAC addresses...")

        # Get all virtual controllers with their associated device MAC addresses
        result = conn.execute(text("""
            SELECT
                vc.id,
                vc.controller_id as old_controller_id,
                vd.mac_address,
                vd.port_id as old_port_id
            FROM virtual_controllers vc
            LEFT JOIN virtual_devices vd ON vd.controller_id = vc.id
            ORDER BY vc.id
        """))

        controllers = result.fetchall()

        if not controllers:
            print("No Virtual Controllers found to migrate")
            return

        print(f"\nFound {len(controllers)} Virtual Controller(s) to update:\n")

        updates = []
        for row in controllers:
            vc_id = row[0]
            old_controller_id = row[1]
            mac_address = row[2]
            old_port_id = row[3]

            if not mac_address:
                print(f"  ⚠ Controller {old_controller_id} has no MAC address, skipping")
                continue

            # Generate new controller ID: nw-{last_6_mac_chars}
            mac_suffix = mac_address.replace(':', '').lower()[-6:]
            new_controller_id = f"nw-{mac_suffix}"

            # Generate new port ID
            new_port_id = f"{new_controller_id}-1" if old_port_id else None

            print(f"  {old_controller_id} -> {new_controller_id}")
            if new_port_id:
                print(f"    Port: {old_port_id} -> {new_port_id}")

            updates.append({
                'vc_id': vc_id,
                'new_controller_id': new_controller_id,
                'old_port_id': old_port_id,
                'new_port_id': new_port_id
            })

        if not updates:
            print("\nNo controllers to update")
            return

        print(f"\nUpdating {len(updates)} controller(s)...")

        for update in updates:
            # Update virtual_controllers table
            conn.execute(
                text("UPDATE virtual_controllers SET controller_id = :new_id WHERE id = :vc_id"),
                {"new_id": update['new_controller_id'], "vc_id": update['vc_id']}
            )

            # Update virtual_devices port_id if exists
            if update['new_port_id']:
                conn.execute(
                    text("UPDATE virtual_devices SET port_id = :new_port_id WHERE port_id = :old_port_id"),
                    {"new_port_id": update['new_port_id'], "old_port_id": update['old_port_id']}
                )

        conn.commit()

    print("\n✅ Migration completed successfully!")
    print("\nVirtual Controller IDs updated to MAC-based format (nw-xxxxxx)")

if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
