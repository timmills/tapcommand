# Device Status Monitoring System

## Overview

The Device Status Monitoring system provides real-time status tracking for network TV devices. It runs as a background service that periodically checks device availability and power state, storing results in a separate database table.

## Architecture

### Separation of Concerns
- **Command Queue**: Handles user-initiated commands
- **Device Status**: Background monitoring (separate system)
- No pollution of command queue with status checks

### Components

1. **Database Table**: `device_status`
   - Stores current status for each device
   - Tracks online/offline, power state, current channel
   - Records check timestamps and method

2. **Background Service**: `DeviceStatusChecker`
   - Runs every 5 minutes (configurable)
   - Protocol-specific status checking
   - Automatic lifecycle management (starts/stops with app)

3. **API Endpoints**: `/api/v1/device-status`
   - Query all device statuses
   - Get specific device status
   - On-demand status checks
   - Power state queries

## Status Checking Methods

### By Protocol

#### Roku (Full API Support)
- **Method**: HTTP API queries
- **Endpoints**:
  - `GET /query/device-info` - Device info and model
  - `GET /query/active-app` - Current channel/app
- **Data Retrieved**:
  - ✅ Online status
  - ✅ Power state (on if responding)
  - ✅ Current channel/app
  - ✅ Model information

#### Samsung Legacy (Ping Only)
- **Method**: ICMP ping
- **Data Retrieved**:
  - ✅ Online status
  - ⚠️ Power state (inferred from ping)
  - ❌ No channel information
- **Limitation**: Cannot determine actual power state

#### LG webOS (Stub - Future Implementation)
- **Method**: WebSocket queries (to be implemented)
- **Potential Endpoints**:
  - `getPowerState`
  - `getForegroundAppInfo`

#### Samsung Tizen (Stub - Future Implementation)
- **Method**: WebSocket queries (to be implemented)

## Database Schema

```sql
CREATE TABLE device_status (
    id INTEGER PRIMARY KEY,

    -- Device identification
    controller_id TEXT UNIQUE NOT NULL,
    device_type TEXT NOT NULL,
    protocol TEXT,

    -- Status information
    is_online BOOLEAN DEFAULT 0,
    power_state TEXT DEFAULT 'unknown',  -- 'on', 'off', 'unknown'
    current_channel TEXT,
    current_input TEXT,
    volume_level INTEGER,
    is_muted BOOLEAN,

    -- Metadata
    model_info TEXT,
    firmware_version TEXT,

    -- Check information
    check_method TEXT,  -- 'ping', 'roku_api', 'webos', etc.
    check_interval_seconds INTEGER DEFAULT 300,

    -- Timestamps
    last_checked_at TIMESTAMP,
    last_changed_at TIMESTAMP,
    last_online_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

## API Endpoints

### GET /api/v1/device-status
Get status for all devices

**Response:**
```json
[
  {
    "controller_id": "nw-b85a97",
    "device_type": "network_tv",
    "protocol": "samsung_legacy",
    "is_online": true,
    "power_state": "on",
    "current_channel": null,
    "check_method": "ping",
    "last_checked_at": "2025-10-05T13:00:59.427905"
  }
]
```

### GET /api/v1/device-status/{controller_id}
Get status for specific device

**Response:**
```json
{
  "controller_id": "nw-b85a97",
  "is_online": true,
  "power_state": "on",
  "check_method": "ping",
  "last_checked_at": "2025-10-05T13:00:59.427905"
}
```

### POST /api/v1/device-status/{controller_id}/check
Trigger immediate status check for a device

**Response:**
```json
{
  "controller_id": "nw-b85a97",
  "is_online": true,
  "power_state": "on",
  "check_method": "ping",
  "last_checked_at": "2025-10-05T13:05:30.123456"
}
```

### GET /api/v1/device-status/online/count
Get count of online vs offline devices

**Response:**
```json
{
  "online": 3,
  "total": 4,
  "offline": 1
}
```

### GET /api/v1/device-status/power/on
Get all powered on devices

### GET /api/v1/device-status/power/off
Get all powered off devices

## Service Lifecycle

The status checker integrates into the FastAPI application lifecycle:

```python
# Startup
await status_checker.start_status_monitoring()

# Runs background loop every 5 minutes
# Checks all virtual devices
# Updates device_status table

# Shutdown
await status_checker.stop_status_monitoring()
```

## Testing

Run the test script:
```bash
cd backend
source venv/bin/activate
python test_device_status.py
```

**Test Coverage:**
- ✅ Status Check - Tests protocol-specific checking
- ✅ On-Demand Check - Tests immediate status query
- ✅ Status History - Tests retrieval of status records

**Test Results (4 devices):**
- Samsung Legacy (192.168.101.50): ✅ Online, Power: ON
- Samsung Legacy (192.168.101.237): ❌ Offline, Power: OFF
- Samsung Legacy (192.168.101.52): ✅ Online, Power: ON
- Samsung Legacy (192.168.101.46): ✅ Online, Power: ON

## Configuration

### Check Interval
Default: 300 seconds (5 minutes)

Modify in `DeviceStatusChecker`:
```python
self.check_interval = 300  # seconds
```

### Per-Device Intervals
Can be configured per-device in `device_status.check_interval_seconds`

## Future Enhancements

### Roku Status Enhancement
- ✅ Already implemented
- Full API support for power, channel, model info

### LG webOS Implementation
- [ ] WebSocket connection handling
- [ ] Power state queries
- [ ] App/channel tracking
- [ ] Volume level monitoring

### Samsung Tizen Implementation
- [ ] WebSocket API integration
- [ ] Enhanced status queries
- [ ] Smart Hub app detection

### Status-Driven Features
- [ ] Auto-retry failed commands when device comes online
- [ ] Power state change notifications
- [ ] Dashboard widgets showing live status
- [ ] Alerts for devices that go offline

## Performance

- **Polling Interval**: 5 minutes (configurable)
- **Check Timeout**: 1-3 seconds per device
- **Database Impact**: Minimal (1 row per device, updated in-place)
- **Background Task**: Async, non-blocking

## Files Created

1. `migrations/add_device_status_table.py` - Database migration
2. `app/models/device_status.py` - SQLAlchemy model
3. `app/services/device_status_checker.py` - Background service
4. `app/routers/device_status.py` - API endpoints
5. `test_device_status.py` - Test script
6. Updated `app/main.py` - Lifecycle integration

## Usage Examples

### Query Device Status
```bash
curl http://localhost:8000/api/v1/device-status/nw-b85a97
```

### Trigger Immediate Check
```bash
curl -X POST http://localhost:8000/api/v1/device-status/nw-b85a97/check
```

### Get Online Count
```bash
curl http://localhost:8000/api/v1/device-status/online/count
```

---

**Implementation Status**: ✅ Complete and Tested
**Last Updated**: October 5, 2025
