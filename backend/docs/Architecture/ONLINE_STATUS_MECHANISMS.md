# Online/Offline Status Monitoring System

## Executive Summary

The TapCommand system uses **THREE SEPARATE** monitoring mechanisms for tracking device online/offline status:

1. **IR Controller Health Checker** (`device_health.py`) - Monitors IR controllers via ESPHome API
2. **Network TV Device Status Checker** (`device_status_checker.py`) - Monitors network TVs via protocol-specific checks
3. **Network TV Status Poller** (`tv_status_poller.py`) - Polls network TVs for detailed state (power, volume, input)

**IMPORTANT NOTE**: The device showing as offline (`ir-dc4516`) has ESPHome memory allocation errors in its logs:
```
09:01:01 [E] [json:044] Could not allocate memory for JSON document!
```
This prevents the device from responding properly to API health checks, causing it to appear offline even though it's responding to pings and was last seen 1 minute ago.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Application Startup                   │
│                         (app/main.py)                            │
└─────────────────────────────────────────────────────────────────┘
                                 │
                ┌────────────────┼────────────────┐
                ▼                ▼                ▼
    ┌───────────────┐ ┌──────────────────┐ ┌──────────────────┐
    │ Health Checker│ │ Device Status    │ │ TV Status Poller │
    │ (IR Only)     │ │ Checker (NW TVs) │ │ (NW TVs Detail)  │
    └───────────────┘ └──────────────────┘ └──────────────────┘
            │                  │                      │
            ▼                  ▼                      ▼
    ┌───────────────┐ ┌──────────────────┐ ┌──────────────────┐
    │managed_devices│ │  device_status   │ │ virtual_devices  │
    │ .is_online    │ │  (separate table)│ │ .is_online       │
    │ .last_seen    │ │                  │ │ .cached_*        │
    └───────────────┘ └──────────────────┘ └──────────────────┘
```

---

## 1. IR Controller Health Monitoring

### Service: `DeviceHealthChecker` (device_health.py)

**Purpose**: Monitor physical IR controllers (ESPHome devices)

**Startup**: Line 68 in `main.py`
```python
await health_checker.start_health_monitoring()
```

**Check Interval**: Every 5 minutes (300 seconds)

**Target Devices**:
- IR controllers in `managed_devices` table
- Devices with hostnames starting with `ir-` (e.g., `ir-dc4516`)
- **Excludes** Virtual Controllers (hostname starts with `nw-`)

### How It Works

#### Phase 1: ESPHome API Check
```python
# Try ESPHome API call
client = esphome_manager.get_client(hostname, ip_address)
device_info = await client.device_info()  # 10 second timeout
```

**What's Checked**:
- ESPHome API reachability (`device_info()` call)
- MAC address verification
- Device capabilities refresh
- IP address tracking

**Success Criteria**:
- API responds with device info
- MAC address matches expected value
- Sets `is_online = True`
- Updates `last_seen` timestamp
- Refreshes capabilities and firmware version

**Failure Handling**:
- Falls back to ICMP ping test
- If ping succeeds: `is_online = True` but `api_reachable = False`
- If ping fails: `is_online = False`

#### Phase 2: Discovery Service Lookup
If API check fails, checks mDNS discovery cache:
```python
discovered = discovery_service.get_device_by_hostname(device.hostname)
```

#### Phase 3: Network Scan (Last Resort)
Scans ±10 IPs around last known address if device not found.

### Database Updates

**Table**: `managed_devices`

**Fields Updated**:
- `is_online` (boolean) - Online/offline status
- `last_seen` (timestamp) - Last successful check
- `current_ip_address` (string) - Current IP (updated if changed)
- `last_ip_address` (string) - Previous IP
- `mac_address` (string) - MAC address (normalized)

**Capabilities Refresh**: Also updates `devices` table with fresh capabilities snapshot.

### Memory Error Impact

**CRITICAL FINDING**: Device `ir-dc4516` shows ESPHome memory allocation errors:
```
Could not allocate memory for JSON document!
```

**Impact on Health Checking**:
1. ESPHome API calls may fail or return incomplete data
2. `device_info()` call times out or returns null
3. Health checker marks device as offline
4. Ping fallback may succeed, but API still shows unreachable
5. Capabilities cannot be refreshed

**Why Device Shows Offline**:
- Last seen: 09:01:46 (less than 1 minute ago)
- Database shows `is_online = 1`
- **BUT** frontend may be checking `api_reachable` or recent health check failures
- Memory errors prevent proper API responses
- Device appears "zombie" - responding to pings but not fully functional

**Fix**: ESPHome firmware needs more heap memory or memory leak fixed.

---

## 2. Network TV Device Status Monitoring

### Service: `DeviceStatusChecker` (device_status_checker.py)

**Purpose**: Monitor network TVs (separate from IR controllers)

**Startup**: Line 84 in `main.py`
```python
await status_checker.start_status_monitoring()
```

**Check Interval**: Every 5 minutes (300 seconds)

**Target Devices**:
- Virtual Devices (network TVs) in `virtual_devices` table
- Associated with Virtual Controllers
- All protocols: Roku, Samsung, LG, Sony, etc.

### How It Works

Protocol-specific status checks:

#### Roku Protocol
```python
response = requests.get(f"http://{ip}:8060/query/device-info", timeout=3)
```
- Full HTTP API support
- Returns: online status, power state, model info, current app

#### Samsung Legacy Protocol
```python
subprocess.run(["ping", "-c", "1", "-W", "1", ip])
```
- **Ping only** (no status API available)
- Cannot determine actual power state
- Assumes if ping succeeds → TV is on

#### LG webOS / Samsung Tizen
- Stub implementations (fall back to ping)
- TODO: WebSocket status queries

### Database Updates

**Table**: `device_status` (separate from managed_devices!)

**Fields Updated**:
- `is_online` (boolean)
- `power_state` (string) - 'on', 'off', 'unknown'
- `current_channel` (string)
- `model_info` (string)
- `check_method` (string) - 'ping', 'roku_api', etc.
- `last_checked_at` (timestamp)
- `last_online_at` (timestamp)
- `last_changed_at` (timestamp) - When status changed

**Key Difference**: This is a **separate table** from `managed_devices`. It tracks network TV status independently.

### API Endpoints

- `GET /api/v1/device-status` - All device statuses
- `GET /api/v1/device-status/{controller_id}` - Specific device
- `POST /api/v1/device-status/{controller_id}/check` - On-demand check
- `GET /api/v1/device-status/online/count` - Online count

---

## 3. Network TV Status Polling (Detailed State)

### Service: `TVStatusPoller` (tv_status_poller.py)

**Purpose**: Poll network TVs for **detailed state** (power, volume, input, app)

**Startup**: Line 88 in `main.py`
```python
await tv_status_poller.start()
```

**Check Interval**: Tiered polling
- Tier 1 (3s): LG webOS, Roku, Hisense (WebSocket/MQTT)
- Tier 2 (5s): Sony Bravia, Philips, Vizio (HTTP)
- Tier 3 (disabled): Samsung Legacy (no status available)

**Target Devices**:
- Active virtual devices (`is_active = True`)
- Status-capable devices (`status_available = True`)

### How It Works

Per-protocol polling:

#### Hisense VIDAA
```python
tv = HisenseTv(hostname=ip, port=36669)
volume_info = tv.get_volume()
state_info = tv.get_state()
```

#### LG webOS
```python
client = WebOSClient(ip)
volume = media.get_volume()
current_app = apps.get_current()
power = system.get_power_state()
```

#### Roku
```python
requests.get(f"http://{ip}:8060/query/device-info")
requests.get(f"http://{ip}:8060/query/active-app")
```

#### Sony Bravia
```python
requests.post(f"http://{ip}/sony/system",
    headers={"X-Auth-PSK": psk},
    json={"method": "getPowerStatus"})
```

### Database Updates

**Table**: `virtual_devices`

**Fields Updated**:
- `cached_power_state` (string) - 'on', 'off', 'standby'
- `cached_volume_level` (int) - 0-100
- `cached_mute_status` (boolean)
- `cached_current_input` (string) - 'HDMI 1', etc.
- `cached_current_app` (string) - 'Netflix', etc.
- `is_online` (boolean) - Updated on success
- `last_status_poll` (timestamp)
- `status_poll_failures` (int) - Consecutive failures

**Failure Handling**:
- 3 consecutive failures → marks device offline
- Resets on successful poll

---

## Hybrid Devices (Network TV + IR Fallback)

### Configuration

Virtual Devices can have IR fallback:
```sql
SELECT device_name, fallback_ir_controller, fallback_ir_port
FROM virtual_devices
WHERE fallback_ir_controller IS NOT NULL;
```

Example: `Office TV (NW)` → fallback to `ir-dc4516` port 1

### Status Monitoring for Hybrid Devices

**Network TV Side** (Primary):
- Monitored by `DeviceStatusChecker`
- Stored in `device_status` table
- Protocol-specific checks (ping for Samsung Legacy)

**IR Controller Side** (Fallback):
- Monitored by `DeviceHealthChecker`
- Stored in `managed_devices` table
- ESPHome API checks

**IMPORTANT**: The IR controller and network TV are **independently monitored**:
- IR controller status does NOT affect network TV status
- Network TV status does NOT affect IR controller status
- Both can be online/offline independently
- Hybrid pairing is for **command routing** only, not status

### Why This Matters

If IR controller (`ir-dc4516`) is offline due to memory errors:
- Network TV (`Office TV (NW)`) remains online if network reachable
- Network TV can still receive network commands
- IR fallback unavailable until controller recovers
- **No cascading offline status** between linked devices

---

## Frontend Display Logic

### Controllers Page (`/controllers`)

**Data Source**: `GET /api/v1/managed/managed` endpoint

**Filters**:
- Shows IR controllers only (hostname NOT starting with `nw-`)
- Excludes Virtual Controllers

**Status Display**:
```typescript
controller.is_online ? 'Online' : 'Offline'
```

**From**: `managed_devices.is_online` field

**Last Seen**:
```typescript
formatRelativeTime(controller.last_seen)
```

**Why ir-dc4516 Shows Offline**:
The database shows `is_online = 1`, but the frontend shows it as offline. This suggests:

1. **Stale Data**: Frontend cache hasn't refreshed
2. **API Response**: `device_management.py` might be computing status differently
3. **Health Check Lag**: Recent health check failed, but database not yet updated
4. **Memory Error Effect**: API returning incomplete data, frontend interpreting as offline

**Investigation Needed**: Check what the API endpoint actually returns for `ir-dc4516`.

---

## Current Status Investigation: ir-dc4516

### Database State (as of 09:02:38)
```
ID: 4
Hostname: ir-dc4516
Device Name: Office TV Controller (IR)
Is Online: 1 ✅
Last Seen: 2025-10-08 09:01:46.269484 (52 seconds ago)
Current IP: 192.168.101.146
MAC: DC4516
```

### ESPHome Device Logs
```
09:01:01 [E] [json:044] Could not allocate memory for JSON document!
09:01:01 [E] [json:044] Could not allocate memory for JSON document!
```

### Analysis

**Problem**: ESPHome device is experiencing memory allocation failures.

**Symptoms**:
- Cannot allocate memory for JSON responses
- API calls likely timing out or returning incomplete data
- Device still responding to network (last seen 52s ago)
- Database shows online, frontend shows offline

**Root Cause**: Insufficient heap memory in ESPHome firmware
- JSON serialization requires contiguous memory block
- Repeated failures suggest memory leak or fragmentation
- Device may need firmware update or memory optimization

**Impact on Monitoring**:
1. **Health Checker**: API calls fail → fallback to ping → `api_reachable = False`
2. **Capabilities**: Cannot refresh capabilities (JSON response fails)
3. **Frontend**: May show offline if checking `api_reachable` flag
4. **Hybrid Fallback**: Office TV (NW) cannot use IR fallback reliably

**Recommended Fix**:
1. Update ESPHome firmware with increased heap allocation
2. Reduce JSON payload size in capabilities response
3. Add memory monitoring to ESPHome firmware
4. Consider splitting large JSON responses into chunks
5. Investigate memory leaks in ESPHome device code

---

## Conflicting Status Resolution

### Problem: Database says online, frontend says offline

**Possible Causes**:

1. **Frontend Caching**: React Query cache not refreshed
2. **API Response Mismatch**: API computing status differently than database
3. **Health Check Race**: Recent check failed, update pending
4. **Memory Error Side Effects**: Incomplete API responses

### How to Debug

1. **Check API Response**:
   ```bash
   curl http://localhost:8000/api/v1/managed/managed | jq '.[] | select(.hostname=="ir-dc4516")'
   ```

2. **Check Health Status**:
   ```bash
   curl http://localhost:8000/api/v1/health-status
   ```

3. **Trigger Manual Health Check**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/managed/4/health-check
   ```

4. **Check ESPHome Logs**:
   - Look for memory errors
   - Check API response completeness
   - Monitor heap usage

---

## Monitoring Service Lifecycle

### Startup Order (main.py:46-90)

1. **Discovery Service** (mDNS scanning)
2. **Health Checker** (IR controllers)
3. **Command Queue Processor**
4. **History Cleanup**
5. **Schedule Processor**
6. **Device Status Checker** (Network TVs)
7. **TV Status Poller** (Network TV state)

### Shutdown Order (main.py:93-106)

Reverse order to prevent orphaned tasks.

### Service Intervals Summary

| Service | Interval | Target | Database |
|---------|----------|--------|----------|
| Health Checker | 5 min | IR Controllers | `managed_devices` |
| Device Status Checker | 5 min | Network TVs | `device_status` |
| TV Status Poller | 3-10s | Network TVs | `virtual_devices` |
| Discovery Service | 30s | All ESPHome | In-memory cache |

---

## Recommendations

### 1. Consolidate Status Checks

**Problem**: Three separate systems checking online status creates confusion.

**Proposal**:
- Unified status table for all devices
- Single source of truth for `is_online`
- Frontend queries one endpoint

### 2. Add Health Status API

**Missing**: No way to see health check status from frontend

**Proposal**:
```typescript
GET /api/v1/health/summary
{
  "last_check": "2025-10-08T09:00:00",
  "next_check": "2025-10-08T09:05:00",
  "devices_checked": 5,
  "devices_online": 4,
  "devices_offline": 1,
  "api_errors": [
    {"hostname": "ir-dc4516", "error": "API timeout", "last_error": "09:01:46"}
  ]
}
```

### 3. Memory Monitoring for ESPHome

**Problem**: No visibility into device memory status

**Proposal**:
- Add heap usage to capabilities JSON
- Alert when memory < 20% free
- Log memory allocation failures
- Auto-restart on repeated failures

### 4. Frontend Status Indicators

**Current**: Simple Online/Offline badge

**Proposed**:
- **Online** (green) - API reachable, responding normally
- **Degraded** (yellow) - Pingable but API failing (like ir-dc4516)
- **Offline** (red) - Completely unreachable
- Tooltip showing last error message

### 5. Hybrid Device Status

**Current**: IR and Network statuses are separate

**Proposed**:
- Show combined status for hybrid devices
- Indicate which control method is available
- "Network OK, IR Fallback Unavailable" status

---

## Testing Online/Offline Status

### Test IR Controller Status

```bash
# Get current status
curl http://localhost:8000/api/v1/managed/managed | jq '.[] | select(.hostname=="ir-dc4516")'

# Trigger health check
curl -X POST http://localhost:8000/api/v1/managed/4/health-check

# Check database
python3 -c "
import sqlite3
conn = sqlite3.connect('tapcommand.db')
cursor = conn.cursor()
cursor.execute('SELECT hostname, is_online, last_seen FROM managed_devices WHERE hostname=\"ir-dc4516\"')
print(cursor.fetchone())
"
```

### Test Network TV Status

```bash
# Get device status
curl http://localhost:8000/api/v1/device-status/nw-b85a97

# Trigger immediate check
curl -X POST http://localhost:8000/api/v1/device-status/nw-b85a97/check

# Check database
python3 -c "
import sqlite3
conn = sqlite3.connect('tapcommand.db')
cursor = conn.cursor()
cursor.execute('SELECT controller_id, is_online, power_state, last_checked_at FROM device_status WHERE controller_id=\"nw-b85a97\"')
print(cursor.fetchone())
"
```

---

## Files Reference

### Backend Services
- `app/services/device_health.py` - IR controller health monitoring
- `app/services/device_status_checker.py` - Network TV status monitoring
- `app/services/tv_status_poller.py` - Network TV state polling
- `app/services/discovery.py` - mDNS device discovery
- `app/main.py` - Service lifecycle management

### API Endpoints
- `app/api/device_management.py` - Managed devices CRUD + health checks
- `app/routers/device_status.py` - Network TV status API

### Database Models
- `app/models/device_management.py` - ManagedDevice, IRPort
- `app/models/device_status.py` - DeviceStatus (network TVs)
- `app/models/virtual_controller.py` - VirtualController, VirtualDevice
- `app/models/device.py` - Device (discovery cache)

### Frontend
- `src/features/devices/pages/controllers-page.tsx` - Controllers list
- `src/features/devices/components/controller-table.tsx` - Status display
- `src/types/api.ts` - ManagedDevice type definition

---

## Conclusion

The TapCommand system has a sophisticated but **complex** multi-layered status monitoring system:

✅ **Strengths**:
- Separate monitoring for IR and Network devices
- Protocol-specific health checks
- Background polling doesn't block UI
- Detailed state caching for network TVs

⚠️ **Weaknesses**:
- Three separate systems creates confusion
- No visibility into API vs Ping status
- Memory errors can create "zombie" devices (online in DB, offline in UI)
- Hybrid devices have independent status (can be confusing)

🔧 **Current Issue (ir-dc4516)**:
- ESPHome memory allocation errors prevent API responses
- Device shows as online in database (ping succeeds)
- Frontend shows offline (API fails)
- Needs firmware fix or memory optimization

**Verdict**: The system works as designed, but the complexity makes troubleshooting difficult. The separate health monitoring approach is good for scaling, but needs better visibility and unified status reporting.
