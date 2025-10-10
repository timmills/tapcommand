"""
Fix default_channel format in ir_ports table
Remove 'channel:' prefix and replace with actual foxtel_number
"""
import sqlite3
import re

conn = sqlite3.connect('tapcommand.db')
cursor = conn.cursor()

# Get all ports with default_channel that starts with 'channel:'
ports_to_fix = cursor.execute('''
    SELECT id, default_channel
    FROM ir_ports
    WHERE default_channel LIKE 'channel:%'
''').fetchall()

print(f"Found {len(ports_to_fix)} ports with 'channel:' format")

for port_id, channel_value in ports_to_fix:
    # Extract the channel ID from 'channel:357' format
    match = re.match(r'channel:(\d+)', channel_value)
    if match:
        channel_id = int(match.group(1))

        # Look up the foxtel_number for this channel
        channel = cursor.execute('''
            SELECT foxtel_number, channel_name
            FROM channels
            WHERE id = ?
        ''', (channel_id,)).fetchone()

        if channel and channel[0]:
            foxtel_number = channel[0]
            channel_name = channel[1]
            print(f"Port {port_id}: '{channel_value}' -> '{foxtel_number}' ({channel_name})")

            # Update the port
            cursor.execute('''
                UPDATE ir_ports
                SET default_channel = ?
                WHERE id = ?
            ''', (foxtel_number, port_id))
        else:
            print(f"Port {port_id}: Could not find channel {channel_id} in channels table")

conn.commit()
conn.close()

print("\nDone! Default channels updated.")
