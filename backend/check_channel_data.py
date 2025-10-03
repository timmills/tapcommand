import sqlite3

conn = sqlite3.connect('smartvenue.db')
cursor = conn.cursor()

print("=== IR Ports (excluding port 0) ===")
rows = cursor.execute('''
    SELECT ip.id, d.hostname, ip.port_number, ip.connected_device_name, ip.default_channel
    FROM ir_ports ip
    JOIN devices d ON d.id = ip.device_id
    WHERE ip.port_number != 0
    ORDER BY d.hostname, ip.port_number
    LIMIT 20
''').fetchall()

for row in rows:
    print(f"ID: {row[0]}, Hostname: {row[1]}, Port: {row[2]}, Device: {row[3]}, Default Channel: {row[4]}")

print("\n=== Channels Table (sample) ===")
channels = cursor.execute('''
    SELECT id, channel_number, lcn, name, is_active
    FROM channels
    LIMIT 10
''').fetchall()

for ch in channels:
    print(f"ID: {ch[0]}, Channel: {ch[1]}, LCN: {ch[2]}, Name: {ch[3]}, Active: {ch[4]}")

conn.close()
