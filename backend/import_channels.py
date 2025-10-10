#!/usr/bin/env python3
"""
Import Australian TV channels from CSV file
"""

import csv
import sqlite3
import sys
import os
from pathlib import Path


def import_channels_from_csv(csv_file_path):
    """Import channels from CSV file to database"""
    # Use the default database path
    db_path = "tapcommand.db"

    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        print("Please run the migration first.")
        return False

    if not os.path.exists(csv_file_path):
        print(f"CSV file not found: {csv_file_path}")
        return False

    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if channels table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='channels'")
        if not cursor.fetchone():
            print("Channels table does not exist. Please run the migration first.")
            conn.close()
            return False

        print(f"Importing channels from {csv_file_path}...")

        # Clear existing data (optional - comment out if you want to append instead)
        cursor.execute("DELETE FROM channels")
        print("Cleared existing channel data")

        # Read and import CSV data
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            inserted_count = 0
            for row in reader:
                # Map CSV columns to database columns
                insert_sql = """
                INSERT INTO channels (
                    platform, broadcaster_network, channel_name, lcn, foxtel_number,
                    broadcast_hours, format, programming_content, availability,
                    logo_url, notes, internal, disabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

                values = (
                    row.get('Platform', ''),
                    row.get('Broadcaster/Network', ''),
                    row.get('Channel Name', ''),
                    row.get('LCN', ''),
                    row.get('Foxtel Number', ''),
                    row.get('Broadcast Hours', ''),
                    row.get('Format', ''),
                    row.get('Programming Content', ''),
                    row.get('Availability', ''),
                    row.get('LogoURL', ''),
                    row.get('Notes', ''),
                    False,  # internal = False
                    True    # disabled = True (as requested)
                )

                cursor.execute(insert_sql, values)
                inserted_count += 1

        # Commit the changes
        conn.commit()
        print(f"Successfully imported {inserted_count} channels")

        # Show some statistics
        cursor.execute("SELECT COUNT(*) FROM channels")
        total_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM channels WHERE disabled = 1")
        disabled_count = cursor.fetchone()[0]

        cursor.execute("SELECT DISTINCT platform FROM channels")
        platforms = [row[0] for row in cursor.fetchall()]

        print(f"\nImport Summary:")
        print(f"Total channels: {total_count}")
        print(f"Disabled channels: {disabled_count}")
        print(f"Platforms: {', '.join(platforms)}")

        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    # Look for CSV file in the project root
    project_root = Path(__file__).parent.parent
    csv_files = list(project_root.glob("au_channels_NSW*.csv"))

    if not csv_files:
        print("No Australian channels CSV file found in project root.")
        print("Looking for files matching pattern: au_channels_NSW*.csv")
        sys.exit(1)

    csv_file = csv_files[0]
    print(f"Found CSV file: {csv_file}")

    success = import_channels_from_csv(str(csv_file))

    if success:
        print("\n✅ Channel import completed successfully!")
        print("All imported channels are disabled by default as requested.")
    else:
        print("\n❌ Channel import failed!")
        sys.exit(1)