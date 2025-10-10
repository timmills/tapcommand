#!/usr/bin/env python3
"""
Create test data for port_status table

This creates dummy channel data for testing the UI display:
- Some ports with channel data
- Some ports without data (for error checking)
"""

import sqlite3
from datetime import datetime

def create_test_data():
    conn = sqlite3.connect('tapcommand.db')
    cursor = conn.cursor()

    print("Creating test port status data...")

    # Test data: mix of channels and empty ports
    # NOTE: Port 0 is for diagnostics only and should never have channel data
    test_data = [
        # ir-dc4516 - has some channels set
        ("ir-dc4516", 1, "500", "channel", datetime.now().isoformat()),  # Port 1: Channel 500
        ("ir-dc4516", 2, "101", "channel", datetime.now().isoformat()),  # Port 2: Channel 101
        ("ir-dc4516", 3, "205", "channel", datetime.now().isoformat()),  # Port 3: Channel 205
        # Port 4, 5 intentionally left blank for ir-dc4516

        # ir-dca172 - has different channels
        ("ir-dca172", 1, "502", "channel", datetime.now().isoformat()),  # Port 1: Channel 502
        ("ir-dca172", 2, "200", "channel", datetime.now().isoformat()),  # Port 2: Channel 200
        # Port 3, 4, 5 intentionally left blank for ir-dca172

        # ir-dcf89f - mostly empty (for error checking)
        ("ir-dcf89f", 1, "501", "channel", datetime.now().isoformat()),  # Port 1: Channel 501
        # Ports 2, 3, 4, 5 intentionally left blank for ir-dcf89f
    ]

    # Insert test data
    for hostname, port, channel, command, timestamp in test_data:
        cursor.execute("""
            INSERT OR REPLACE INTO port_status
            (hostname, port, last_channel, last_command, last_command_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (hostname, port, channel, command, timestamp, timestamp))
        print(f"  ✓ {hostname} port {port}: Channel {channel}")

    conn.commit()

    # Verify data
    print("\nVerifying port status data:")
    cursor.execute("""
        SELECT hostname, port, last_channel
        FROM port_status
        ORDER BY hostname, port
    """)

    results = cursor.fetchall()
    print(f"\nTotal records: {len(results)}")

    for hostname, port, channel in results:
        print(f"  {hostname} port {port} -> Channel {channel}")

    conn.close()
    print("\n✅ Test data created successfully!")
    print("\nDevices with intentionally blank ports for error checking:")
    print("  - ir-dc4516: ports 4, 5 (blank)")
    print("  - ir-dca172: ports 3, 4, 5 (blank)")
    print("  - ir-dcf89f: ports 2, 3, 4, 5 (blank)")
    print("\nNOTE: Port 0 is diagnostic only and has no channel data")

if __name__ == "__main__":
    create_test_data()
