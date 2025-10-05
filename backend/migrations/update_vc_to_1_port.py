#!/usr/bin/env python3
"""
Migration: Update Virtual Controllers to 1 port with brand capabilities

Changes Virtual Controllers from 5 ports to 1 port
and adds IR-like capabilities with brand information
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings
import json

def run_migration():
    """Update Virtual Controllers to 1 port with brand capabilities"""

    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    )

    with engine.connect() as conn:
        print("Fetching Virtual Controllers...")

        # Get all virtual controllers with their device info
        result = conn.execute(text("""
            SELECT
                vc.id,
                vc.controller_id,
                vc.capabilities,
                vd.mac_address,
                (SELECT vendor FROM network_scan_cache WHERE mac_address = vd.mac_address LIMIT 1) as vendor
            FROM virtual_controllers vc
            LEFT JOIN virtual_devices vd ON vd.controller_id = vc.id AND vd.port_number = 1
        """))

        controllers = result.fetchall()

        if not controllers:
            print("No Virtual Controllers found to migrate")
            return

        print(f"\nFound {len(controllers)} Virtual Controller(s) to update:\n")

        for row in controllers:
            vc_id = row[0]
            controller_id = row[1]
            capabilities = json.loads(row[2]) if row[2] else {}
            mac_address = row[3]
            vendor = row[4]

            # Determine brand from vendor
            brand = "Unknown"
            if vendor:
                vendor_lower = vendor.lower()
                if "samsung" in vendor_lower:
                    brand = "Samsung"
                elif "lg" in vendor_lower:
                    brand = "LG"
                elif "sony" in vendor_lower:
                    brand = "Sony"
                elif "panasonic" in vendor_lower:
                    brand = "Panasonic"
                elif "philips" in vendor_lower:
                    brand = "Philips"
                elif "toshiba" in vendor_lower:
                    brand = "Toshiba"
                elif "vizio" in vendor_lower:
                    brand = "Vizio"
                elif "tcl" in vendor_lower:
                    brand = "TCL"
                elif "hisense" in vendor_lower:
                    brand = "Hisense"

            # Update capabilities with ports array
            capabilities["ports"] = [{
                "port": 1,
                "brand": brand,
                "description": f"{brand} Network TV"
            }]

            # Update total_ports to 1 and capabilities
            conn.execute(
                text("UPDATE virtual_controllers SET total_ports = 1, capabilities = :caps WHERE id = :vc_id"),
                {"caps": json.dumps(capabilities), "vc_id": vc_id}
            )

            print(f"  ✓ Updated {controller_id}: brand={brand}, ports=1")

        conn.commit()

    print(f"\n✅ Migration completed successfully!")
    print(f"\nUpdated {len(controllers)} Virtual Controllers:")
    print("  - Set total_ports = 1")
    print("  - Added brand to capabilities.ports")

if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
