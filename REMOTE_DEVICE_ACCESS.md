# Remote Device Access Functions

This document describes how to access and control functions on remote TapCommand ESPHome devices.

## Overview

TapCommand uses ESPHome-based controllers to manage IR devices in hospitality environments. Each controller exposes services that can be called remotely via the ESPHome API.

## Prerequisites

1. **ESPHome API Key**: Required for encrypted communication with devices
2. **Device Hostname/IP**: The network address of the target device
3. **Python Environment**: With `aioesphomeapi` library installed

## Getting the API Key

The ESPHome API key is stored in the TapCommand database:

```python
import sqlite3

# Connect to database
conn = sqlite3.connect('/home/coastal/tapcommand/backend/tapcommand.db')
cursor = conn.cursor()

# Get API key
cursor.execute("SELECT value FROM application_settings WHERE key = 'esphome_api_key'")
api_key = cursor.fetchone()[0]
conn.close()
```

**Current API Key**: `uuPgF8JOAV/ZhFbDV4iS4Kwr1MV5H97p6Nk+HnpE1+g=`

## Connecting to a Device

```python
import asyncio
from aioesphomeapi import APIClient

async def connect_to_device(hostname, api_key):
    client = APIClient(hostname, 6053, None)
    await client.connect(login=True, password=api_key)
    return client
```

## Available Services

Based on the dynamic table-dispatch system, devices expose the following services:

### 1. TV Power Control
- **Service**: `tv_power`
- **Parameters**:
  - `port` (int): IR port number (1-16)
- **Function**: Sends power toggle command to connected TV

### 2. TV Channel Control
- **Service**: `tv_channel`
- **Parameters**:
  - `port` (int): IR port number (1-16)
  - `channel` (int): Target channel number
- **Function**: Changes TV to specified channel using smart digit sequencing

### 3. TV Volume Control
- **Service**: `tv_volume_up` / `tv_volume_down`
- **Parameters**:
  - `port` (int): IR port number (1-16)
- **Function**: Adjusts TV volume up or down

## Example Usage

### Complete Device Control Example

```python
import asyncio
import sqlite3
from aioesphomeapi import APIClient

async def control_device_example():
    # Get API key from database
    conn = sqlite3.connect('/home/coastal/tapcommand/backend/tapcommand.db')
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM application_settings WHERE key = 'esphome_api_key'")
    api_key = cursor.fetchone()[0]
    conn.close()

    # Connect to device
    client = APIClient('ir-dc4516.local', 6053, None)
    await client.connect(login=True, password=api_key)

    # List available services
    entities, services = await client.list_entities_services()
    print("Available services:")
    for service in services:
        print(f"  - {service.name}: {service.key}")

    # Find services
    tv_power_service = next(s for s in services if s.name == 'tv_power')
    tv_channel_service = next(s for s in services if s.name == 'tv_channel')

    # Execute commands
    print("Sending power command...")
    await client.execute_service(tv_power_service, {'port': 1})

    # Wait before next command
    await asyncio.sleep(3)

    print("Changing to channel 50...")
    await client.execute_service(tv_channel_service, {'port': 1, 'channel': 50})

    # Disconnect
    await client.disconnect()

# Run the example
asyncio.run(control_device_example())
```

### Power Control Only

```python
async def power_off_device(hostname, port=1):
    # Get API key
    conn = sqlite3.connect('/home/coastal/tapcommand/backend/tapcommand.db')
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM application_settings WHERE key = 'esphome_api_key'")
    api_key = cursor.fetchone()[0]
    conn.close()

    # Connect and execute
    client = APIClient(hostname, 6053, None)
    await client.connect(login=True, password=api_key)

    entities, services = await client.list_entities_services()
    tv_power_service = next(s for s in services if s.name == 'tv_power')

    await client.execute_service(tv_power_service, {'port': port})
    await client.disconnect()

    print(f"✅ Power command sent to {hostname} port {port}")

# Usage
asyncio.run(power_off_device('ir-dc4516.local', 1))
```

### Channel Control with Smart Sequencing

```python
async def change_channel(hostname, port, channel):
    # Get API key
    conn = sqlite3.connect('/home/coastal/tapcommand/backend/tapcommand.db')
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM application_settings WHERE key = 'esphome_api_key'")
    api_key = cursor.fetchone()[0]
    conn.close()

    # Connect and execute
    client = APIClient(hostname, 6053, None)
    await client.connect(login=True, password=api_key)

    entities, services = await client.list_entities_services()
    tv_channel_service = next(s for s in services if s.name == 'tv_channel')

    await client.execute_service(tv_channel_service, {'port': port, 'channel': channel})
    await client.disconnect()

    print(f"✅ Channel {channel} command sent to {hostname} port {port}")
    print("📺 Smart channel system will send digits with appropriate delays")

# Usage
asyncio.run(change_channel('ir-dc4516.local', 1, 100))
```

## Device Discovery

To find available devices on the network:

```python
# Check managed devices in database
conn = sqlite3.connect('/home/coastal/tapcommand/backend/tapcommand.db')
cursor = conn.cursor()
cursor.execute("SELECT hostname, device_name, is_online FROM managed_devices WHERE is_online = 1")
devices = cursor.fetchall()
conn.close()

print("Online devices:")
for hostname, name, online in devices:
    print(f"  - {hostname} ({name})")
```

## Error Handling

Common errors and solutions:

### Connection Failed
- **Error**: `ConnectionRefusedError`
- **Solution**: Check device is online and ESPHome API is enabled

### Invalid Encryption Key
- **Error**: `InvalidEncryptionKey`
- **Solution**: Verify API key is correct and matches device configuration

### Service Not Found
- **Error**: Service not in available services list
- **Solution**: Check device has the expected firmware with table-dispatch services

## Smart Channel System

The channel control system automatically handles multi-digit channels:

- **Single digit (1-9)**: Sends digit directly
- **Double digit (10-99)**: Sends first digit, waits 500ms, sends second digit
- **Triple digit (100-999)**: Sends digits sequentially with 500ms delays

This ensures reliable channel changing across different TV models and brands.

## Security Notes

- API keys are stored encrypted in the database
- All communication uses ESPHome's native encryption
- Keys should be rotated periodically for security
- Never hardcode API keys in production code

## Troubleshooting

1. **Device not responding**: Check network connectivity and device power
2. **Service not available**: Verify device has correct firmware with expected services
3. **Intermittent failures**: Add retry logic with exponential backoff
4. **Channel changes fail**: Some TVs require longer delays between digits

## Integration with TapCommand Backend

The TapCommand backend provides REST API endpoints that internally use these ESPHome functions:

- `POST /api/devices/{device_id}/ir/power/{port}` - Power control
- `POST /api/devices/{device_id}/ir/channel/{port}` - Channel control
- `POST /api/devices/{device_id}/ir/volume/{port}/{direction}` - Volume control

These endpoints handle authentication, device lookup, and error handling automatically.