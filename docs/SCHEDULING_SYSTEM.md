# Scheduling System Documentation

## Overview

The TapCommand scheduling system allows users to create recurring or one-time automated actions for IR-controlled devices. Schedules can target devices by selection, tags, locations, or all devices, and execute sequences of up to 4 actions with configurable delays.

## Architecture

### Backend Components

#### 1. Database Models (`backend/app/models/device.py`)

**Schedule Model:**
```python
class Schedule(Base):
    id: int                          # Primary key
    name: str                        # Schedule name (e.g., "Morning Bar Setup")
    description: str                 # Optional description
    cron_expression: str             # Cron expression (e.g., "0 8 * * 1-5")
    target_type: str                 # 'all', 'selection', 'tag', 'location'
    target_data: dict                # {device_ids: [], tag_ids: [], locations: []}
    actions: list[dict]              # [{type, value, repeat, wait_after}]
    is_active: bool                  # Enable/disable schedule
    last_run: datetime               # Last execution timestamp
    next_run: datetime               # Next scheduled execution
    created_at: datetime
    updated_at: datetime
```

**ScheduleExecution Model:**
```python
class ScheduleExecution(Base):
    id: int
    schedule_id: int                 # Foreign key to schedules
    batch_id: str                    # Batch ID for command queue
    executed_at: datetime
    total_commands: int              # Total commands queued
    succeeded: int                   # Commands that succeeded
    failed: int                      # Commands that failed
    avg_execution_time_ms: int       # Average execution time
```

#### 2. API Endpoints (`backend/app/routers/schedules.py`)

**Base Path:** `/api/v1/schedules`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/` | Create a new schedule |
| GET | `/` | List all schedules (with filtering) |
| GET | `/upcoming` | Get upcoming schedules (next 5 by default) |
| GET | `/{id}` | Get specific schedule |
| PUT | `/{id}` | Update schedule |
| DELETE | `/{id}` | Delete schedule |
| PATCH | `/{id}/toggle` | Toggle active status |
| POST | `/{id}/run` | Manually trigger schedule execution |
| GET | `/{id}/history` | Get execution history |

**Request Examples:**

Create Schedule:
```json
POST /api/v1/schedules
{
  "name": "Morning Bar Setup",
  "description": "Power on all bar TVs and set to news",
  "cron_expression": "0 8 * * 1-5",
  "target_type": "tag",
  "target_data": {"tag_ids": [1, 3]},
  "actions": [
    {"type": "power", "value": "on", "wait_after": 10},
    {"type": "volume_down", "repeat": 5, "wait_after": 2},
    {"type": "channel", "value": "502"}
  ],
  "is_active": true
}
```

List Schedules:
```
GET /api/v1/schedules?active_only=true&limit=50&offset=0
```

Get Upcoming:
```
GET /api/v1/schedules/upcoming?limit=5
```

Run Manually:
```
POST /api/v1/schedules/123/run
```

#### 3. Schedule Processor (`backend/app/services/schedule_processor.py`)

**Purpose:** Background service that executes scheduled commands using APScheduler.

**Key Features:**
- Loads active schedules on startup
- Uses cron triggers for timing
- Executes actions sequentially with delays
- Resolves targets dynamically
- Queues commands via existing queue system
- Updates last_run and next_run timestamps
- Logs executions to database

**Lifecycle:**
- Started in `main.py` app lifespan
- Runs continuously in background
- Can add/remove/update schedules dynamically

**Execution Flow:**
```
1. Cron trigger fires
2. Load schedule from database
3. Resolve target devices (by type)
4. For each action:
   a. Queue commands for all targets
   b. Handle repeats (for volume actions)
   c. Wait if wait_after specified
5. Update schedule (last_run, next_run)
6. Log execution to schedule_executions
```

## Scheduling Concepts

### Cron Expressions

Uses standard cron syntax (server time, no timezone):
```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday to Saturday)
│ │ │ │ │
│ │ │ │ │
* * * * *
```

**Common Examples:**
- `0 8 * * *` - Daily at 8:00 AM
- `0 8 * * 1-5` - Weekdays at 8:00 AM
- `0 8 * * 6,0` - Weekends at 8:00 AM
- `0 */2 * * *` - Every 2 hours
- `30 17 * * *` - Daily at 5:30 PM
- `0 8 1 * *` - First day of month at 8:00 AM

### Target Types

**1. All Devices**
```json
{
  "target_type": "all",
  "target_data": null
}
```
Targets all active IRPorts.

**2. Selection**
```json
{
  "target_type": "selection",
  "target_data": {"device_ids": [1, 5, 8, 12]}
}
```
Targets specific IRPort IDs.

**3. Tag**
```json
{
  "target_type": "tag",
  "target_data": {"tag_ids": [1, 3]}
}
```
Targets all IRPorts with ANY of the specified tags.

**4. Location**
```json
{
  "target_type": "location",
  "target_data": {"locations": ["Main Bar", "VIP Lounge"]}
}
```
Targets all IRPorts in specified locations.

### Action Types

**1. Power**
```json
{"type": "power", "value": "on"}
```
Toggle power on/off. Tracks power state in port_status.

**2. Mute**
```json
{"type": "mute", "value": "on"}
```
Toggle mute on/off.

**3. Volume Up/Down**
```json
{"type": "volume_down", "repeat": 5}
```
Adjust volume. Can repeat 1-10 times.

**4. Channel**
```json
{"type": "channel", "value": "502"}
```
Change to specific channel (channel ID).

**5. Default Channel**
```json
{"type": "default_channel"}
```
Change to each device's configured default_channel.

### Action Sequences

Actions execute sequentially for ALL devices before moving to the next action.

**Example:**
```json
"actions": [
  {"type": "power", "wait_after": 10},
  {"type": "volume_down", "repeat": 5, "wait_after": 2},
  {"type": "channel", "value": "502"}
]
```

**Execution:**
1. Queue 'power' command for all 12 devices
2. Wait 10 seconds
3. Queue 5x 'volume_down' commands for all 12 devices (60 commands total)
4. Wait 2 seconds
5. Queue 'channel' command for all 12 devices

### Wait Times

Supported wait intervals (seconds):
- 5, 10, 15, 30 seconds
- 60, 120, 300, 600, 900 seconds (1m, 2m, 5m, 10m, 15m)
- 3600, 10800, 18000 seconds (1h, 3h, 5h)

## Integration with Queue System

Scheduled commands integrate seamlessly with the existing command queue:

**Command Classification:** `"system"` (Class D)
- Always queued (never direct)
- Priority: 0 (normal)
- Routing method: `"scheduled"`

**Batch Operations:**
- All commands in a schedule execution share a batch_id
- Format: `sched_{schedule_id}_{uuid}`
- Enables batch status tracking
- Links to schedule_executions table

**Benefits:**
- Reliable execution (retries on failure)
- Avoids overloading devices
- Observable via queue metrics
- Command history tracking

## Frontend Components (To Be Implemented)

### 1. Schedule List Page (`/schedules`)

**Features:**
- Table view of all schedules
- Show next run time and countdown
- Enable/disable toggle
- Edit/delete/duplicate actions
- "Run Now" manual trigger
- Expandable rows showing details

**Filters:**
- Active only
- Search by name
- Sort by next run

### 2. Schedule Form Modal

**Multi-section form:**
1. **Basic Info:** Name, description
2. **Timing:** Cron builder with presets
3. **Targets:** Device selector with tag/location filters
4. **Actions:** Action sequence builder (max 4)

**Cron Builder Options:**
- Daily
- Weekly (with day selection)
- Monthly
- Custom (manual cron input)

**Device Selector:**
- Quick select: All, By Tag, By Location
- Search/filter
- Shows selection count
- Grouped by tags/locations

**Action Builder:**
- Dropdown for action type
- Action-specific inputs (channel selector, repeat count)
- Wait time selector
- Add/remove actions
- Visual summary

### 3. Control Page Integration

**Next Schedule Banner:**
```
┌─────────────────────────────────────────────────────────────┐
│  🕐 Next: "Evening News" in 1h 23m → Sports TVs (5)    [→] │
└─────────────────────────────────────────────────────────────┘
```

Click expands to show upcoming schedules in slide-out panel.

### 4. Execution History

**Per-schedule history:**
- Last 10 executions
- Success/failure count
- Failed device details
- Average execution time
- Batch ID for queue lookup

## API Response Examples

**Schedule Response:**
```json
{
  "id": 1,
  "name": "Morning Bar Setup",
  "description": "Power on all bar TVs",
  "cron_expression": "0 8 * * 1-5",
  "target_type": "tag",
  "target_data": {"tag_ids": [1, 3]},
  "actions": [
    {"type": "power", "value": "on", "wait_after": 10},
    {"type": "volume_down", "repeat": 5, "wait_after": 2},
    {"type": "channel", "value": "502"}
  ],
  "is_active": true,
  "last_run": "2025-10-03T08:00:00Z",
  "next_run": "2025-10-04T08:00:00Z",
  "created_at": "2025-10-01T10:30:00Z",
  "updated_at": "2025-10-03T08:00:00Z"
}
```

**List Response:**
```json
{
  "schedules": [...],
  "total": 12
}
```

**Execution History Response:**
```json
[
  {
    "id": 45,
    "schedule_id": 1,
    "batch_id": "sched_1_abc12345",
    "executed_at": "2025-10-03T08:00:00Z",
    "total_commands": 36,
    "succeeded": 34,
    "failed": 2,
    "avg_execution_time_ms": 234
  }
]
```

**Run Now Response:**
```json
{
  "batch_id": "manual_1_xyz67890",
  "queued_count": 36,
  "command_ids": [1234, 1235, 1236, ...]
}
```

## Configuration

### Dependencies

**Python packages** (in `requirements.txt`):
```
croniter>=6.0.0
apscheduler>=3.10.4
python-dateutil>=2.9.0
```

**Install:**
```bash
pip install croniter apscheduler
```

### Environment Variables

None required - uses server system time.

### Database Migrations

Run migration to create/update tables:
```bash
python -m backend.migrations.update_schedules_schema
```

Or manually drop and recreate if needed.

## Troubleshooting

### Schedule Not Executing

**Check:**
1. Is schedule active? (`is_active = true`)
2. Is `next_run` in the future?
3. Check schedule processor logs
4. Verify cron expression is valid

**Logs:**
```
✅ Schedule processor started successfully
⏰ Executing schedule: Morning Bar Setup (ID: 1)
  📍 Found 12 target devices
  🎬 Action 1/3: power
  ⏱️  Waiting 10s before next action...
```

### Commands Not Queuing

**Check:**
1. Are target devices active? (`is_active = true`)
2. Do tags/locations match devices?
3. Check queue processor status
4. Review command queue logs

### Execution History Missing

**Check:**
1. Is `schedule_executions` table created?
2. Check for database errors in logs
3. Verify batch_id format

### Cron Expression Invalid

**Validation:**
- Use [crontab.guru](https://crontab.guru) for testing
- API returns 400 error if invalid
- Check minute/hour/day ranges

## Performance Considerations

### Scalability

- **Max schedules:** No hard limit, APScheduler handles hundreds
- **Max actions per schedule:** 4 (configurable)
- **Max devices:** Limited by queue capacity (~1000s)

### Execution Time

- Actions execute sequentially (blocking)
- Use `wait_after` wisely (delays accumulate)
- Queue workers process commands concurrently

### Database Growth

- `schedule_executions` grows over time
- Recommended retention: 30 days
- Add cleanup job similar to `command_history`

## Security Considerations

- No authentication yet (future: user roles)
- Server-side cron validation prevents injection
- Queue system prevents command flooding
- Rate limiting recommended for API endpoints

## Future Enhancements

1. **Conditional Execution**
   - Only run if device is online
   - Skip if already in desired state

2. **Advanced Targeting**
   - Combine tag + location filters
   - Exclude specific devices

3. **Notifications**
   - Email/webhook on execution failure
   - Summary reports

4. **Schedule Templates**
   - Pre-built schedules (Morning, Evening, Cleanup)
   - Clone existing schedules

5. **Timezone Support**
   - Per-schedule timezone
   - Venue-level default timezone

6. **Conflict Detection**
   - Warn if schedules overlap
   - Priority-based execution

7. **Execution Preview**
   - "Dry run" mode
   - Show what will execute before saving

## Support

For issues or questions:
- Check logs: `backend/app/services/schedule_processor.py`
- Review queue metrics: `GET /api/v1/commands/queue/metrics`
- Inspect database: `sqlite3 tapcommand.db`

## Version History

- **v1.0** (2025-10-03): Initial implementation
  - Basic scheduling with cron
  - Action sequences with delays
  - Target by all/selection/tag/location
  - APScheduler integration
  - Queue system integration
