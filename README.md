# TapCommand Device Management System
## Dynamic IR Prototype Notes

- Prototype ESPHome firmware: `esphome/prototypes/ir_dynamic_test.yaml`
- Latest compiled binary: `esphome/prototypes/ir_dynamic_test.bin`
- Generated from Dynamic IR migration plan (see `docs/dynamic_ir_migration_plan.md`)

Commercial hospitality display management system for pubs and restaurants. Replace 75+ minutes of daily manual TV control with centralized automation.

**ROI**: $11,400+ annual savings per venue

## 🚀 Quick Start

### Backend
```bash
cd backend
source ../venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Run the backend as a service (recommended)

```bash
sudo cp deploy/systemd/tapcommand-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tapcommand-backend.service
sudo systemctl status tapcommand-backend.service
```

Tail the logs at any time with:

```bash
journalctl -u tapcommand-backend.service -f
```

> The UI will show “Backend API unreachable. Ensure the TapCommand backend service is running.” if this service is stopped.

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 🏗️ Architecture

```
Raspberry Pi 4 Hub (FastAPI + SQLite + React UI)
         ↓ (Hidden "TV" WiFi Network)
ESP8266 IR Blasters → Foxtel Boxes/Samsung/LG TVs
         ↓ (Venue Network)
Network TVs (Samsung/LG/Sony/etc) → Direct IP Control
         ↓ (Venue Network)
Audio Amplifiers (Bosch Praesensa/AES70) → Zone Control
         ↑ (Tailscale VPN for remote management)
```

## ✅ Current Status: FULL STACK OPERATIONAL!

- **Backend**: `100.93.158.19:8000` (FastAPI + Device Discovery)
- **Frontend**: `100.93.158.19:3000` (React + TypeScript)
- **Discovery**: Auto-detects ESPHome devices (`ir-dc4516` found)
- **Database**: 70+ device models (Samsung, LG, Sony, Foxtel, etc.)

## 📱 Features

### Device Management
- **IR Controllers**: Auto-discovery via mDNS (`ir-*.local`)
  - 5-port IR mapping per device
  - Capability snapshots imported from ESPHome firmware
  - Live YAML builder for crafting new templates
- **Network TVs**: SSDP/UPnP discovery and adoption
  - Direct IP control for Samsung, LG, Sony, Hisense, Roku, etc.
  - Virtual Controller architecture for management
  - Hybrid IR fallback for power-on support
- **Audio Amplifiers**: AES70 auto-discovery
  - Bosch Praesensa zone control (volume, mute)
  - Automatic zone detection via AES70 role maps
  - Real-time dB range discovery
- Device registration with friendly names
- Health monitoring (online/offline status)
- Template editor in Settings with Wi-Fi credential management

### Control System
- **IR Commands**: Direct commands (`Box 2 Power`, `Channel 2-501`)
- **Network TV Control**: Power, volume, input switching via IP
- **Audio Zone Control**: Volume (0-100%), mute/unmute per zone
- **Unified Command Queue**: All commands routed through single queue
- Bulk operations: `Power off all displays`
- Device status synchronization
- Real-time connectivity monitoring

### Technology Stack
- **Backend**: FastAPI, SQLAlchemy, AsyncIO, APScheduler
- **Frontend**: React + Vite + TypeScript
- **Database**: SQLite with Alembic migrations
- **Discovery**: python-zeroconf (mDNS), SSDP (UPnP)
- **Device Control**:
  - IR Controllers: aioesphomeapi
  - Network TVs: Samsung Legacy, LG webOS, Sony Bravia, Hisense, Roku, etc.
  - Audio Amplifiers: AES70py (Bosch Praesensa), AES70/OCA protocol
- **Deployment**: Docker ready

## 🎯 API Endpoints

### IR Controller Management
- `GET /api/v1/management/discovered` - List discovered ESPHome devices
- `POST /api/v1/management/sync-discovered` - Sync device discovery (mDNS)
- `GET /api/v1/management/managed` - List managed IR controllers
- `POST /api/v1/management/manage/{hostname}` - Add device to management
- `DELETE /api/v1/management/managed/{id}` - Remove device
- `POST /api/v1/management/managed/{id}/health-check` - Run device health check
- `POST /api/v1/management/managed/health-check-all` - Check all devices
- `GET /api/v1/management/health-status` - Monitor health polling service

### Network TV Discovery & Control
- `GET /api/network-tv/discover` - Discover TVs via SSDP/UPnP
- `POST /api/network-tv/command` - Send command to TV (power, volume, etc.)
- `GET /api/network-tv/test/{ip}` - Test TV connectivity
- `POST /api/network-tv/adopt/{ip}` - Adopt TV as Virtual Controller
- `POST /api/network-tv/hide/{mac_address}` - Hide device from discovery
- `GET /api/network-tv/hidden` - List hidden devices

### Audio Controller Management
- `POST /api/audio/controllers/discover` - Discover Bosch Praesensa (AES70)
- `GET /api/audio/controllers` - List audio controllers with zones
- `GET /api/audio/zones` - List all audio zones
- `POST /api/audio/zones/{zone_id}/volume` - Set zone volume (0-100%)
- `POST /api/audio/zones/{zone_id}/volume/up` - Increase volume by 5%
- `POST /api/audio/zones/{zone_id}/volume/down` - Decrease volume by 5%
- `POST /api/audio/zones/{zone_id}/mute` - Toggle mute or set mute state
- `POST /api/audio/controllers/{controller_id}/rediscover` - Rediscover zones
- `DELETE /api/audio/controllers/{controller_id}` - Delete audio controller

### Virtual Controllers (Network TVs & Audio)
- `GET /api/virtual-controllers/` - List all virtual controllers
- `GET /api/virtual-controllers/devices/all` - List all virtual devices
- `DELETE /api/virtual-controllers/{controller_id}` - Delete virtual controller
- `POST /api/hybrid-devices/{device_id}/link-ir-fallback` - Link IR fallback for TV
- `DELETE /api/v1/hybrid-devices/{device_id}/unlink-ir-fallback` - Unlink IR fallback

### Unified Command Queue (IR, TV, Audio)
- `POST /api/commands/{hostname}/command` - Send command to any device type
- `POST /api/commands/bulk` - Send bulk commands (batch operations)
- `GET /api/commands/bulk/{batch_id}/status` - Check bulk command status
- `GET /api/commands/queue/all` - View entire command queue
- `GET /api/commands/queue/metrics` - Queue performance metrics
- `GET /api/commands/{hostname}/health` - Check device health
- `POST /api/commands/{hostname}/diagnostic` - Run diagnostics
- `GET /api/commands/{hostname}/port-status` - Get port status (IR controllers)
- `POST /api/commands/maintenance/cleanup-history` - Clean old command history

### IR Templates & Libraries
- `GET /api/v1/templates/base` - Get default ESP template for YAML builder
- `GET /api/v1/templates/device-hierarchy` - IR library hierarchy
- `POST /api/v1/templates/preview` - Generate YAML preview
- `GET /api/v1/templates/{template_id}` - Get stored template
- `PUT /api/v1/templates/{template_id}` - Update stored template

Full API documentation: `http://100.93.158.19:8000/docs`

## 🔧 Hardware

- **Hub**: Raspberry Pi 4 (FastAPI backend)
- **IR Blasters**: ESP8266 with 5 GPIO outputs each
- **Network**: Hidden "TV" WiFi with MAC-based identification
- **Connectivity**: Tailscale VPN for remote management

## 📁 Project Structure

```
tapcommand/
├── backend/           # FastAPI application
│   ├── app/
│   │   ├── api/       # REST API endpoints
│   │   ├── models/    # Database models
│   │   ├── services/  # Business logic
│   │   └── db/        # Database & migrations
├── frontend/          # React TypeScript UI
│   ├── src/
│   │   ├── components/
│   │   └── services/
├── esphome/          # Device firmware configs (generated + dynamic templates)
└── README.md
```

### ESPHome Firmware Notes

- `esphome/esp_multi_report.yaml` duplicates the production config and adds the `report_capabilities` service for querying supported brands/commands.
- The backend calls this service when a device is adopted, storing the JSON payload in `device_discoveries.discovery_properties.capabilities`.
- Compile locally with `esphome compile esphome/esp_multi_report.yaml` (ESPHome CLI is available inside the repo virtualenv).
- You can call the service manually via `aioesphomeapi` to refresh metadata for an existing sender.
- The default template now exposes a `wifi_hidden` substitution; edit it from the Settings → ESPHome Templates page alongside SSID/password/API key. The YAML builder consumes these values when generating device configs.

## 🚧 Roadmap

### Phase 3: Automation (Next)
- [ ] Schedule Engine: Cron-style automation
- [ ] Event Queue: Reliable command execution
- [ ] Staff Interface: Touchscreen-friendly controls
- [ ] Channel Presets: "Sky Sports", "BBC News" shortcuts

### Phase 4: Production
- [ ] Tailscale Integration: Multi-venue management
- [ ] Config Deployment: Push settings to venues
- [ ] Analytics: Usage tracking and reporting
- [ ] Hardening: Error handling, offline operation

## 🏢 Commercial Benefits

- **Time Savings**: 75+ minutes → <5 minutes daily
- **Cost Reduction**: $11,400+ annual savings per venue
- **Centralized Control**: Single touchscreen interface
- **Remote Management**: Multi-venue support via VPN
- **Automated Scheduling**: Set-and-forget channel changes
