# SmartVenue Development Plan

## Project Overview
Commercial hospitality display management system for pubs/restaurants. Replace 75+ minutes of daily manual TV control with centralized automation. Target: <5 minutes via touchscreen interface.

**ROI**: $11,400+ annual savings per venue

## Current Assets
- ✅ ESPHome firmware (Universal dual Samsung/LG + smart channel sequencing)
- ✅ Hardware: Raspberry Pi 4 hub + ESP8266 IR blasters (5 outputs each)
- ✅ Network: Hidden "TV" WiFi with MAC-based device identification
- ✅ Working IR commands for power, channels, volume, mute
- ✅ **70+ IR Device Library**: Samsung, LG, Sony, Foxtel, Audio systems from Flipper-IRDB
- ✅ **Dynamic YAML Generation**: Database-driven ESPHome template builder

## Architecture
```
Raspberry Pi 4 Hub (FastAPI + SQLite + React UI)
         ↓ (Hidden "TV" WiFi Network)
ESP8266 IR Blasters (5 ports each) → TVs/Audio/Foxtel via IR library selection
         ↑ (Tailscale VPN for remote management)
         ↑ (Capability reporting via report_capabilities service)
```

## Development Status

### ✅ Phase 1: Foundation - COMPLETE!
- ✅ **Project Structure**: FastAPI + SQLAlchemy + Alembic
- ✅ **Database Schema**: devices, venues, schedules, logs, IR libraries
- ✅ **mDNS Discovery**: Auto-detect ESPHome devices (`ir-*.local`)
- ✅ **ESPHome API Client**: Async device communication
- ✅ **Basic REST API**: Device CRUD operations

### ✅ Phase 2: Core Features - COMPLETE!
- ✅ **Command System**: Send IR to specific device/output
- ✅ **Bulk Operations**: "Mute all", "Power off all"
- ✅ **Device Health**: Status monitoring, connectivity checks
- ✅ **Web UI**: React frontend for device management
- ✅ **ESP Capability Capture**: Import supported brands/commands directly from firmware
- ✅ **YAML Builder UI**: Craft D1 Mini ESPHome templates with live previews
- ✅ **Device Management**: Full CRUD interface with 5-port IR mapping
- ✅ **Dynamic YAML Generation**: Database-driven template system with device selection
- ✅ **IR Library Management**: Hierarchical device browser (Category → Brand → Model)
- ✅ **Capability Reporting**: ESP devices auto-report supported brands/commands on adoption

### Phase 3: Automation
- [ ] **Schedule Engine**: Cron-style automation
- [ ] **Event Queue**: Reliable command execution
- [ ] **Staff Interface**: Touchscreen-friendly controls
- [ ] **Channel Presets**: "Sky Sports", "BBC News" shortcuts

### Phase 4: Production
- [ ] **Tailscale Integration**: Multi-venue management
- [ ] **Config Deployment**: Push settings to venues
- [ ] **Analytics**: Usage tracking and reporting
- [ ] **Hardening**: Error handling, offline operation

## 🚀 Current Status: FULL STACK OPERATIONAL!

**Backend Server**: `100.93.158.19:8000` (Tailscale)
**Frontend Ready**: React TypeScript with multi-page interface
**Discovered Device**: `ir-dc4516` (192.168.101.146)
**API Documentation**: `http://100.93.158.19:8000/docs`
**Device Management**: Complete with 5-port IR mapping

### 🎯 Major Architecture Changes:
- **Dynamic YAML Generation**: Users select devices from database via YAML Builder → generates ESPHome configs
- **Capability Auto-Detection**: ESP devices report supported brands/commands via `report_capabilities` service
- **Database-Driven Device Selection**: IR libraries organized hierarchically (Category → Brand → Model)
- **Port-Based Device Mapping**: Each IR sender has 5 configurable ports with device assignments
- **Real-time Capability Display**: Frontend shows device capabilities captured during adoption

### 🔧 Current Workflow:
1. **Device Discovery**: ESPHome devices auto-discovered via mDNS (`ir-*.local`)
2. **Device Adoption**: System calls `report_capabilities` to capture device capabilities
3. **YAML Builder**: Users browse device library, select profiles, map to ports
4. **Template Generation**: Dynamic YAML creation with placeholders replaced
5. **Capability Storage**: Device metadata stored in `discovery_properties.capabilities`

## Technology Stack
- **Backend**: FastAPI, SQLAlchemy, AsyncIO, APScheduler
- **Database**: SQLite with comprehensive IR library schema
- **Frontend**: React + TypeScript with multi-page interface (Devices, IR Senders, YAML Builder)
- **Discovery**: python-zeroconf (mDNS)
- **Device Control**: aioesphomeapi with capability reporting
- **IR Libraries**: Imported from Flipper-IRDB (70+ device profiles)
- **Template Engine**: Dynamic YAML generation with placeholder replacement

## Key Features

### Dynamic Device Configuration
- **YAML Builder**: Visual interface for creating ESPHome templates
- **Device Library Browser**: Hierarchical selection (Category → Brand → Model)
- **Port Assignment**: Map IR libraries to specific ESP8266 GPIO ports
- **Live Preview**: Real-time YAML generation with character counts
- **Template Customization**: Include/exclude comments, substitution support

### Enhanced Device Management
- **Auto-discovery via mDNS**: Detect `ir-*.local` devices automatically
- **Capability Reporting**: ESP devices auto-report supported brands/commands via `report_capabilities` service
- **5-Port Configuration**: Each IR sender supports 5 independent device connections
- **Real-time Status**: Online/offline monitoring with IP tracking
- **Device Adoption**: One-click addition from discovery to management

### Advanced IR Control
- **Database-Driven Commands**: IR codes stored in SQLite with protocol support
- **Multi-Protocol Support**: Samsung32, NEC, Sony, RC5, Pronto codes
- **Smart Channel System**: Automatic digit sequencing (501 → 5,0,1)
- **Dual-Brand Blasting**: Samsung + LG simultaneous transmission
- **Command Categorization**: Power, volume, navigation command grouping

### Modern Web Interface
- **Multi-Page Navigation**: Devices, IR Senders, YAML Builder tabs
- **Connected Device View**: Unified table showing all port-connected devices
- **IR Sender Management**: Configuration modals for port assignments
- **Capability Display**: Live view of device-reported functions
- **Status Monitoring**: Real-time online/offline indicators

## API Endpoints (Updated)

### Device Management
- `GET /api/v1/management/discovered` - List discovered devices
- `POST /api/v1/management/sync-discovered` - Sync device discovery
- `GET /api/v1/management/managed` - List managed devices
- `POST /api/v1/management/manage/{hostname}` - Add device to management (with capability capture)
- `DELETE /api/v1/management/managed/{id}` - Remove device
- `POST /api/v1/management/managed/{id}/sync-status` - Sync device status

### Template System
- `GET /api/v1/templates/base` - Get base ESPHome template
- `GET /api/v1/templates/device-hierarchy` - IR library hierarchy (Category → Brand → Model)
- `POST /api/v1/templates/preview` - Generate YAML preview from port assignments

### IR Library Management
- `GET /api/v1/ir-codes/libraries` - Browse IR device libraries
- `GET /api/v1/ir-codes/categories` - Device categories
- `GET /api/v1/ir-codes/brands/{category}` - Brands within category

## Current File Structure
```
smartvenue/
├── backend/
│   ├── app/
│   │   ├── api/           # REST endpoints
│   │   │   ├── devices.py
│   │   │   ├── device_management.py
│   │   │   └── admin.py
│   │   ├── routers/       # Additional routers
│   │   │   ├── ir_codes.py
│   │   │   └── templates.py
│   │   ├── models/        # Database schemas
│   │   │   ├── device.py
│   │   │   ├── device_management.py
│   │   │   └── ir_codes.py
│   │   ├── services/      # Business logic
│   │   │   ├── discovery.py
│   │   │   ├── esphome_client.py
│   │   │   ├── ir_import.py
│   │   │   └── ir_updater.py
│   │   ├── db/           # Database setup
│   │   │   ├── database.py
│   │   │   └── seed_data.py
│   │   └── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx       # Multi-page React interface
│   │   ├── main.tsx
│   │   └── index.css
│   └── package.json
├── esphome/
│   ├── esp_multi_report.yaml    # Production firmware with capability reporting
│   └── templates/
│       └── d1_mini_base.yaml    # Base template for YAML builder
├── data/                        # IR library data
│   └── Flipper-IRDB/           # Imported IR device profiles
└── README.md
```

## Quick Start Commands

Start the backend server:
```bash
cd backend
source ../venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Start the frontend:
```bash
cd frontend
npm install
npm run dev
```

Access the application:
- **Frontend**: http://100.93.158.19:3000
- **API Docs**: http://100.93.158.19:8000/docs
- **Database Admin**: http://100.93.158.19:8000/api/v1/admin/

Test the new API endpoints:

```bash
# Sync discovered devices
curl -X POST "http://100.93.158.19:8000/api/v1/management/sync-discovered"

# List discovered devices
curl -X GET "http://100.93.158.19:8000/api/v1/management/discovered"

# Add device to management (with capability capture)
curl -X POST "http://100.93.158.19:8000/api/v1/management/manage/ir-dc4516" \
  -H "Content-Type: application/json" \
  -d '{"device_name": "Main Bar Controller", "location": "Main Bar"}'

# Get device hierarchy for YAML builder
curl -X GET "http://100.93.158.19:8000/api/v1/templates/device-hierarchy"

# Generate YAML preview
curl -X POST "http://100.93.158.19:8000/api/v1/templates/preview" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": 1,
    "assignments": [
      {"port_number": 1, "library_id": 1},
      {"port_number": 2, "library_id": 2}
    ],
    "include_comments": true
  }'
```

## Git Commands for Commits

When you ask me to commit changes, I will run these commands:

```bash
# Stage all changes
git add .

# Create descriptive commit with emojis
git commit -m "✨ Commit message here

Brief description of changes made.

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push to GitHub repository
git push origin main
```

**GitHub Repository**: https://github.com/timmills/smartvenue-device-management

## Allowed Bash Commands

For API testing and development verification, these bash commands are pre-approved:

```bash
# API Health Checks & Testing
curl http://localhost:8000/
curl http://localhost:8000/docs
curl http://localhost:8000/api/v1/management/discovered
curl http://localhost:8000/api/v1/ir-codes/libraries
curl -X POST http://localhost:8000/api/v1/templates/preview

# Development Server Status
curl http://localhost:5173/
curl http://localhost:5174/  # New frontend during development

# Network & System Checks
timeout 5 curl -s http://localhost:8000/health
timeout 10 curl -s "http://localhost:5173/"
```

These commands help verify API endpoints, test backend connectivity, and validate frontend deployment during the fresh start implementation.

## Architecture Analysis & Recommendations

### Critical Issues Identified (September 2025)

#### 1. Frontend Monolith Crisis
- **38,410-token single file** (`App.tsx`) containing entire application
- Development severely impacted by file size and complexity
- Multiple developers cannot work simultaneously
- IDE performance issues and syntax highlighting struggles

#### 2. Template Generation Complexity
- **1000+ line monolithic function** for YAML generation (`_render_dynamic_yaml()`)
- String-based template system with placeholder replacement
- No validation until ESPHome compile time
- Complex database queries for each template generation
- Generated templates can exceed 1500+ lines

#### 3. mDNS Integration Limitations
- Manual backend startup required (`./run.sh`) for device discovery
- No bidirectional communication between devices and management system
- Limited utilization of mDNS capabilities
- No real-time device status updates

### Recommended Architecture Improvements

#### Phase 1: Immediate Refactoring (1-2 weeks)
1. **Frontend Component Extraction**
   - Split App.tsx into separate page components
   - Extract common UI components and proper state management
   - Implement TypeScript interfaces for all data models

2. **Template Generation Refactoring**
   - Break down massive `_render_dynamic_yaml()` function
   - Add input validation and error handling
   - Implement template caching for identical configurations

#### Phase 2: Component-Based Template System (3-4 weeks)
1. **Modular Template Architecture**
   ```python
   class TemplateComponent:
       def generate(self, context: dict) -> dict
       def validate(self) -> List[str]
       def dependencies(self) -> List[str]
   ```

2. **Direct IR Code Assignment**
   - Replace library-based assignments with direct code-to-port mapping
   - Eliminate complex conditional logic in YAML generation
   - Simpler and more efficient approach

#### Phase 3: Enhanced mDNS Integration
1. **Bidirectional mDNS Communication**
   - Backend service advertisement via mDNS
   - Real-time device health monitoring
   - Device capability broadcasting via mDNS TXT records

2. **Eliminate Backend Discovery Dependency**
   - Frontend-direct mDNS discovery capabilities
   - Reduced infrastructure dependencies

### Alternative YAML Generation Approaches

#### Current Issues with String Templates
- No composition or modularity
- Difficult to test and debug
- No reusability across devices
- Error-prone placeholder replacement

#### Recommended: Component Composition Engine
```python
class TemplateComposer:
    def add_component(self, name: str, component: YAMLComponent)
    def generate_template(self, device_config: dict) -> str
```

### Modularization Strategy

#### Frontend Structure (Recommended)
```
src/
├── components/DeviceManagement/
├── components/IRSenders/
├── components/YAMLBuilder/
├── components/Settings/
├── services/
├── stores/
└── pages/
```

#### Backend Domain Structure (Recommended)
```
backend/app/
├── domain/devices/
├── domain/templates/
├── domain/ir_codes/
├── domain/firmware/
├── infrastructure/
└── interfaces/
```

## Next Steps

### Immediate Actions Required
1. **Create comprehensive analysis branch** - See `COMPREHENSIVE_ANALYSIS.md`
2. **Begin frontend component extraction** to enable parallel development
3. **Refactor template generation** to reduce complexity and improve maintainability

### Long-term Vision
Transform the codebase from maintenance burden into modern, scalable system supporting:
- Parallel development by multiple teams
- Component-based template system
- Real-time device management via enhanced mDNS
- Comprehensive testing infrastructure
- Performance optimization with caching

Ready for architectural transformation and Phase 3 implementation!

## Key Database Models

### IR Library Management
- **IRLibrary**: Device profiles with category/brand/model hierarchy
- **IRCommand**: Individual IR codes with protocol-specific data (Samsung32, NEC, Sony, etc.)
- **ESPTemplate**: Base YAML templates for dynamic generation

### Device Management
- **ManagedDevice**: ESP IR senders with 5-port configuration
- **IRPort**: Individual port assignments with connected device info
- **DeviceDiscovery**: Auto-discovered devices with capability snapshots

### Capability Reporting
- ESP devices call `report_capabilities` service during adoption
- Capabilities stored in `discovery_properties.capabilities` as JSON
- Includes supported brands, commands, firmware version, project info
