#!/usr/bin/env python3
"""
Import MAC vendor database from CSV
"""
import csv
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from app.db.database import SessionLocal
from app.models.network_discovery import MACVendor

def import_mac_vendors(csv_path: str):
    """Import MAC vendors from CSV file"""
    db = SessionLocal()

    try:
        # Clear existing vendors
        print("Clearing existing MAC vendors...")
        db.query(MACVendor).delete()
        db.commit()

        # Import new vendors
        print(f"Importing MAC vendors from {csv_path}...")
        count = 0
        batch = []
        batch_size = 1000

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                vendor = MACVendor(
                    mac_prefix=row['Mac Prefix'],
                    vendor_name=row['Vendor Name'],
                    is_private=row['Private'].lower() == 'true',
                    block_type=row['Block Type'],
                    last_update=row['Last Update']
                )
                batch.append(vendor)
                count += 1

                # Commit in batches for performance
                if len(batch) >= batch_size:
                    db.bulk_save_objects(batch)
                    db.commit()
                    print(f"Imported {count} vendors...")
                    batch = []

        # Commit remaining
        if batch:
            db.bulk_save_objects(batch)
            db.commit()

        print(f"✅ Successfully imported {count} MAC vendors")

        # Show some stats
        samsung_count = db.query(MACVendor).filter(
            MACVendor.vendor_name.like('%Samsung%')
        ).count()
        lg_count = db.query(MACVendor).filter(
            MACVendor.vendor_name.like('%LG %')
        ).count()
        sony_count = db.query(MACVendor).filter(
            MACVendor.vendor_name.like('%Sony%')
        ).count()
        philips_count = db.query(MACVendor).filter(
            MACVendor.vendor_name.like('%Philips%')
        ).count()

        print(f"\nTV Manufacturer Prefixes:")
        print(f"  Samsung: {samsung_count}")
        print(f"  LG: {lg_count}")
        print(f"  Sony: {sony_count}")
        print(f"  Philips: {philips_count}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error importing MAC vendors: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    csv_file = "../mac-vendors-export.csv"

    if not Path(csv_file).exists():
        print(f"❌ File not found: {csv_file}")
        sys.exit(1)

    import_mac_vendors(csv_file)
