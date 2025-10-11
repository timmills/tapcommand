# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TapCommand is a commercial hospitality display management system for pubs and restaurants that replaces 75+ minutes of daily manual TV control with centralized automation. The system controls IR-based devices (Foxtel boxes, TVs), network TVs (Samsung/LG/Sony), and AES70 audio amplifiers through a centralized FastAPI backend and React frontend.

**Architecture**: Raspberry Pi 4 hub running FastAPI + SQLite + React UI, controlling ESP8266 IR blasters over a hidden WiFi network, with direct IP control for network TVs and audio zones.

## Development Commands

### Backend

**Start development server:**
```bash
cd backend
source ../venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Run as systemd service:**
```bash
sudo systemctl start tapcommand-backend.service
sudo systemctl status tapcommand-backend.service
journalctl -u tapcommand-backend.service -f
```

**Install dependencies:**
```bash
source venv/bin/activate
pip install -r backend/requirements.txt
```

### Frontend

The frontend is in `frontend-v2/` (React + Vite + TypeScript):

```bash
cd frontend-v2
npm install
npm run dev          # Development server
npm run build        # Production build
npm run lint         # ESLint
```

**Note**: There is NO `frontend/` directory - the active frontend is `frontend-v2/`.

### ESPHome Firmware

ESPHome CLI is available in the virtualenv:

```bash
source venv/bin/activate
esphome compile esphome/esp_multi_report.yaml
esphome compile esphome/prototypes/ir_dynamic_test.yaml
```

**Key firmware files:**
- `esphome/esp_multi_report.yaml` - Production config with `report_capabilities` service
- `esphome/prototypes/ir_dynamic_test.yaml` - Dynamic IR testing prototype

## Architecture & Key Concepts

### Multi-Device Type System

TapCommand manages three device types through a unified command queue:

1. **IR Controllers** (`ir-*` hostname prefix)
   - ESP8266 devices with 5 IR output ports each
   - Discovered via mDNS (hostname pattern: `ir-*.local`)
   - Controlled via `aioesphomeapi`
   - Capabilities fetched on adoption and stored in `device.capabilities`

2. **Network TVs** (Virtual Controllers with `nw-*` prefix)
   - Direct IP control (Samsung Legacy, LG webOS, Sony Bravia, etc.)
   - Discovered via SSDP/UPnP
   - Can have hybrid IR fallback for power-on support
   - Represented as Virtual Controllers in database

3. **Audio Amplifiers** (Virtual Controllers with `audio-*` prefix)
   - Bosch Praesensa via AES70/OCA protocol
   - Discovered via AES70 mDNS
   - Zone-based control (volume 0-100%, mute/unmute)
   - Controlled via `aes70py` library

### Hybrid Command Routing Architecture

The system uses **smart routing** based on command classification (see `docs/QUEUE_ARCHITECTURE_DESIGN.md`):

- **Class A (Immediate)**: Direct execution only - diagnostic signals, health checks
- **Class B (Interactive)**: Try direct first, queue on failure - single device commands
- **Class C (Bulk)**: Always queued - multi-device operations, batch commands
- **Class D (System)**: Always queued with low priority - background tasks

**Why this matters**: Don't route everything through the queue. Interactive operations (ID button, single channel change) should use direct execution for instant feedback. Only bulk operations and retries use the queue.

### Database Models

**Key tables:**
- `devices` - All device types (IR controllers, network TVs, audio)
- `virtual_controllers` - Network TVs and audio amplifiers
- `device_discoveries` - mDNS discovered devices awaiting adoption
- `network_discoveries` - SSDP/UPnP discovered network devices
- `command_queue` - Unified command queue for all device types
- `command_history` - Execution history (cleaned up after 7 days)
- `port_status` - Current channel/state per IR port
- `ir_libraries` - IR code definitions (brands, models, commands)
- `users`, `roles`, `permissions` - RBAC authentication system

**No Alembic migrations**: Database schema is created via `create_tables()` in `backend/app/db/database.py`. Changes are made by modifying SQLAlchemy models and recreating tables (acceptable for this embedded system deployment model).

### Background Services

The backend runs multiple background services started in `app.main.py` lifespan:

1. **discovery_service** - mDNS discovery for IR controllers and audio
2. **health_checker** - Periodic health monitoring for managed devices
3. **queue_processor** - Processes queued commands with retry logic
4. **schedule_processor** - Executes scheduled automation tasks
5. **status_checker** - Monitors device online/offline status
6. **tv_status_poller** - Polls network TV status
7. **history_cleanup** - Purges old command history (7-day retention)

**Important**: These services start on app startup and stop on shutdown. They use AsyncIO and run in the main event loop. The `_main_loop` global variable enables scheduling async tasks from sync callbacks (see `on_device_discovered()`).

### ESPHome Integration Patterns

**Capabilities Discovery:**
- IR controllers expose a `report_capabilities` service
- Backend calls this on device adoption via `esphome_manager.fetch_capabilities()`
- Response stored in `device.capabilities` JSON field
- Capabilities include supported brands, commands, and IR libraries

**Parameter Translation:**
- API uses `box` parameter (1-5 for IR ports)
- ESPHome services expect `port` parameter
- Backend translates: `box` → `port` in `esphome_client.py`

**Service Mapping:**
```python
service_map = {
    "power": "tv_power",
    "channel": "tv_channel",
    "diagnostic_signal": "diagnostic_signal",
    # etc.
}
```

### Authentication & Authorization

**RBAC System:**
- 4 system roles: Super Admin, Administrator, Operator, Viewer
- Custom roles with granular permissions
- JWT token-based authentication
- Middleware handles authentication guard on protected routes

**Password Management:**
- CLI password reset tool: `./reset-password.sh username`
- Account lockout after 5 failed attempts (15-minute auto-unlock)
- "Must change password on next login" flag supported

## File Organization

```
backend/app/
├── api/           # V1 API endpoints (devices, management, admin)
├── routers/       # Newer endpoints (commands, schedules, auth, etc.)
├── commands/      # Unified command routing (api.py)
├── models/        # SQLAlchemy models
├── services/      # Business logic (discovery, queue, health, etc.)
├── db/            # Database setup (database.py)
├── core/          # Config (config.py)
└── main.py        # FastAPI app + lifespan events

frontend-v2/src/
├── components/    # React components
├── features/      # Feature-based modules
├── lib/           # Utilities
└── services/      # API clients

esphome/
├── esp_multi_report.yaml          # Production IR firmware
├── prototypes/                    # Experimental firmware
└── (generated configs per device)

docs/
├── QUEUE_ARCHITECTURE_DESIGN.md   # Command routing design doc
├── ESP_DEVICE_CONTROL_API.md      # API reference
├── USER_MANAGEMENT_GUIDE.md       # RBAC guide
├── SCHEDULING_SYSTEM.md           # Automation docs
└── (other guides)
```

## Common Development Tasks

### Adding a New IR Library

See `docs/ADDING_NATIVE_IR_LIBRARIES.md` for step-by-step guide.

### Adding a New Network TV Brand

1. Create service class in `backend/app/services/` (e.g., `roku_service.py`)
2. Implement standard methods: `send_power()`, `send_volume()`, `get_status()`, etc.
3. Update discovery in `network_tv_router.py`
4. Add brand detection logic in SSDP discovery

### Working with the Command Queue

- Queue model: `backend/app/models/command_queue.py`
- Queue service: `backend/app/services/command_queue.py`
- Processor: `backend/app/services/queue_processor.py`
- Unified API: `backend/app/commands/api.py`

**Enqueuing a command:**
```python
from app.services.command_queue import enqueue_command

await enqueue_command(
    db=db,
    hostname="ir-dcf89f",
    command="power",
    port=1,
    priority=0,
    batch_id=None
)
```

### Running Tests

There is currently no formal test suite. The system uses:
- Manual testing via the UI
- `health-check.sh` script for deployment verification
- Diagnostic endpoints (`/api/commands/{hostname}/diagnostic`)

### Database Inspection

SQLite database is at `backend/tapcommand.db` (or configured path):

```bash
sqlite3 backend/tapcommand.db
.schema
SELECT * FROM devices;
SELECT * FROM command_queue WHERE status = 'pending';
```

## Configuration & Settings

**Backend settings:**
- Managed via `backend/app/core/config.py`
- Environment variables or `.env` file
- Database settings stored in `settings` table (managed via Settings API)

**ESPHome credentials:**
- SSID, password, API key stored in `settings` table
- Accessed via `settings_service.get_setting("esphome_api_key")`
- Used for generating device configs and connecting to devices

**Frontend API base URL:**
- Configured in `frontend-v2/.env.local`
- Typically points to `http://100.93.158.19:8000` (Tailscale IP)

## Important Implementation Details

### Device Hostname Prefixes

- `ir-*` = IR controllers (ESPHome devices)
- `nw-*` = Network TVs (virtual controllers)
- `audio-*` = Audio amplifiers (virtual controllers)

**Why this matters**: Discovery and connection logic branches on hostname prefix.

### Hybrid IR Fallback

Network TVs can have an IR fallback device linked for power-on (many TVs don't respond to network commands when off):

- Link: `POST /api/hybrid-devices/{device_id}/link-ir-fallback`
- Uses both network control (preferred) and IR power-on fallback

### Port vs Box Terminology

- **Frontend/API**: Uses "box" (historical naming)
- **ESPHome/Backend**: Uses "port" (correct hardware term)
- Backend translates between them

### Diagnostic Signal Pattern

Special command for LED identification:
```json
{
  "command": "diagnostic_signal",
  "box": 0,
  "digit": 1
}
```
Flashes device LED at 3Hz for 2 minutes. Port MUST be 0, digit MUST be 1.

### Multi-Digit Channel Entry

The `smart_channel` ESPHome script automatically splits multi-digit channels:
- Frontend sends: `{"command": "channel", "box": 1, "channel": "60"}`
- ESP device sends: digit "6", wait 300ms, digit "0"

### Settings Management

System settings (WiFi credentials, API keys, etc.) stored in database:
```python
from app.services.settings_service import settings_service

api_key = settings_service.get_setting("esphome_api_key")
settings_service.set_setting("esphome_ssid", "MyNetwork")
```

## API Documentation

Full OpenAPI docs available at: `http://localhost:8000/docs`

**Key endpoint patterns:**
- `/api/v1/devices/{hostname}/command` - Send command to device
- `/api/commands/{hostname}/command` - Unified command API (queue-aware)
- `/api/commands/bulk` - Bulk operations
- `/api/network-tv/*` - Network TV discovery and control
- `/api/audio/*` - Audio controller management
- `/api/v1/management/*` - IR controller adoption
- `/api/v1/schedules/*` - Automation schedules

## Deployment

**Install script:**
```bash
curl -fsSL http://100.93.158.19:8000/install-fancy.sh | bash
```

**Manual deployment:**
1. Copy repository to Raspberry Pi
2. Run `./bootstrap.sh` to create virtualenv and install dependencies
3. Configure systemd service: `sudo cp deploy/systemd/tapcommand-backend.service /etc/systemd/system/`
4. Enable and start: `sudo systemctl enable --now tapcommand-backend.service`
5. Build and deploy frontend (or run via npm)

**Health check:**
```bash
./health-check.sh
```

## Debugging Tips

**Backend logs:**
```bash
journalctl -u tapcommand-backend.service -f
```

**Check queue status:**
```bash
curl http://localhost:8000/api/commands/queue/metrics
```

**Device connectivity:**
```bash
curl http://localhost:8000/api/v1/management/managed
curl http://localhost:8000/api/commands/ir-dcf89f/health
```

**Database queries:**
```bash
sqlite3 backend/tapcommand.db "SELECT * FROM command_queue WHERE status != 'completed' ORDER BY created_at DESC LIMIT 10;"
```

## Known Patterns & Conventions

- **Async everywhere**: All device communication is async (aioesphomeapi, httpx, asyncio)
- **Session management**: Database sessions created via `SessionLocal()`, always use try/finally to close
- **Error handling**: Commands return success boolean, log errors but don't raise exceptions to caller
- **Retry logic**: Queue processor handles retries with exponential backoff (2^attempts seconds)
- **Device state**: Assume IR devices are stateless; track last-sent command in `port_status` table
- **Discovery callbacks**: Device discovery runs in separate thread; use `asyncio.run_coroutine_threadsafe()` to schedule async work

## References

For detailed information on specific subsystems, see:
- Queue architecture: `docs/QUEUE_ARCHITECTURE_DESIGN.md`
- API reference: `docs/ESP_DEVICE_CONTROL_API.md`
- User management: `docs/USER_MANAGEMENT_GUIDE.md`
- IR library integration: `docs/ADDING_NATIVE_IR_LIBRARIES.md`
- Scheduling: `docs/SCHEDULING_SYSTEM.md`
