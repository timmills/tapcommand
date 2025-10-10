# 🚀 TapCommand Frontend Recovery Guide
*A Complete Guide to Rising from the Ashes and Creating a Masterpiece*

---

## 🎯 TL;DR - Your Mission (Should You Choose to Accept It)

You're building a **React/TypeScript frontend** for the TapCommand IR Blaster system. The backend is **ROCK SOLID** and ready for you. This guide will help you create something that actually works instead of... well, whatever happened before.

---

## 🏗️ Backend Architecture Overview (The Foundation That's Already Perfect)

### Core System
- **Backend**: FastAPI + SQLAlchemy + SQLite
- **Base URL**: `http://localhost:8000`
- **Docs**: `http://localhost:8000/docs` (Your new best friend)
- **Tech Stack**: Python 3.12, FastAPI 0.100+, Uvicorn

### What This System Does
TapCommand is an **IR Blaster management system** that:
1. **Manages IR Libraries**: Collections of IR codes for different devices (TVs, etc.)
2. **Creates Dynamic Templates**: ESPHome YAML configs that compile to ESP8266 firmware
3. **Handles Device Discovery**: Finds and manages ESP devices on the network
4. **Streams Channel Data**: Australian TV channels with icons and metadata
5. **Compiles Firmware**: Generates actual .bin files for flashing to devices

---

## 📡 API Documentation (Your Lifeline)

### 🚨 CRITICAL: Always Check the Live Docs
Visit `http://localhost:8000/docs` - this is the **single source of truth**. All endpoints are documented with:
- Request/response schemas
- Example payloads
- Try-it-now functionality
- Parameter descriptions

### Main API Categories

#### 1. **IR Libraries** (`/api/v1/`)
```bash
# Get all IR libraries (Samsung, LG, etc.)
GET /api/v1/ir_libraries

# Get specific library with all commands
GET /api/v1/ir_libraries/{library_id}
```

#### 2. **Templates** (`/api/v1/templates/`)
```bash
# Preview generated YAML before compilation
POST /api/v1/templates/preview
Content-Type: application/json
{
  "template_id": 1,
  "assignments": [
    {"port_number": 1, "library_id": 207},
    {"port_number": 3, "library_id": 208}
  ],
  "include_comments": true
}

# Compile firmware to binary
POST /api/v1/templates/compile
# Same request body as preview
```

#### 3. **Devices** (`/api/v1/devices/`)
```bash
# Discover ESP devices on network
POST /api/v1/devices/discovery/start
GET /api/v1/devices/discovery/devices

# Send commands to devices
POST /api/v1/devices/bulk-command
{
  "device_ids": ["ir-abc123"],
  "command": "power",
  "port": 1
}
```

#### 4. **Channels** (`/api/v1/channels/`)
```bash
# Get Australian TV channels
GET /api/v1/channels/channels
GET /api/v1/channels/channels/area/{area_name}
GET /api/v1/channels/channels/platform/{platform}
```

---

## 🗄️ Database Schema (What You're Working With)

### Core Tables

#### **ir_libraries** - Device Control Libraries
```sql
- id: Primary key
- display_name: "Generic Samsung TV"
- device_category: "TV"
- brand: "Generic Samsung"
- model: "TV"
- source_path: "generic/samsung_tv"
```

#### **ir_commands** - Individual IR Commands
```sql
- id: Primary key
- library_id: Foreign key to ir_libraries
- name: "power", "volume_up", "number_1", etc.
- protocol: "samsung", "nec", "rc5", etc.
- data: IR hex code (0xE0E00207) or address/command
```

#### **templates** - ESPHome Base Templates
```sql
- id: Primary key (always use template_id: 1)
- name: "TapCommand ESPHome Template (D1 Mini)"
- version: "1.0.26"
- template_yaml: Full YAML with {{PLACEHOLDERS}}
```

#### **channels** - Australian TV Channels
```sql
- id: Primary key
- name: "Channel 7"
- number: 7
- area: "Sydney", "Melbourne", etc.
- platform: "Free to Air", "Foxtel"
- logo_url: Channel icon URL
- local_logo_path: Local cached icon
```

### Sample Data Counts
- **Libraries**: ~210 IR device libraries
- **Commands**: ~3,400 individual IR commands
- **Channels**: ~800 Australian TV channels with icons
- **Templates**: 1 master template with dynamic generation

---

## 🎯 Frontend Requirements (Your Actual Job)

### Must-Have Features

#### 1. **IR Configuration Interface**
- **Port Assignment**: Drag/drop interface for assigning libraries to ports 1-5
- **Library Browser**: Searchable list of 200+ IR libraries (Samsung, LG, Sony, etc.)
- **Preview System**: Show generated YAML before compilation
- **Command Testing**: Send individual commands to test devices

#### 2. **Template Management**
- **YAML Preview**: Live preview with syntax highlighting
- **Compilation Status**: Real-time feedback during firmware generation
- **Download Management**: Handle compiled .bin file downloads
- **Version Tracking**: Template versioning support

#### 3. **Device Management**
- **Discovery Interface**: Start/stop network device discovery
- **Device List**: Show discovered ESP devices with status
- **Bulk Commands**: Send commands to multiple devices
- **Health Monitoring**: Device connectivity status

#### 4. **Channel Management**
- **Channel Browser**: Searchable TV channel list with icons
- **Area Filtering**: Sydney, Melbourne, Brisbane, etc.
- **Platform Filtering**: Free-to-air vs Foxtel
- **Bulk Operations**: Update channel assignments

### UI/UX Guidelines

#### Component Structure (Suggested)
```
src/
├── components/
│   ├── IRLibraryBrowser/     # Searchable IR library list
│   ├── PortConfiguration/    # Port assignment interface
│   ├── YAMLPreview/         # Syntax-highlighted YAML viewer
│   ├── DeviceDiscovery/     # Network device discovery
│   ├── ChannelBrowser/      # TV channel management
│   └── FirmwareBuilder/     # Compilation interface
├── hooks/
│   ├── useAPIData.ts        # Generic API data fetching
│   ├── useDevices.ts        # Device management state
│   └── useTemplates.ts      # Template/YAML state
├── services/
│   ├── api.ts              # Axios/fetch API client
│   └── websockets.ts       # Real-time updates
└── types/
    └── api.ts              # TypeScript interfaces
```

#### Design System
- **Color Scheme**: Professional blue/gray (avoid rainbow vomit)
- **Typography**: Clean, readable fonts (Inter, Roboto)
- **Layout**: Card-based, responsive grid system
- **Icons**: Consistent icon library (Heroicons, Lucide)
- **Feedback**: Loading states, error boundaries, success messages

---

## 📦 Sample API Responses (Copy-Paste Ready)

### IR Libraries List
```json
[
  {
    "id": 207,
    "display_name": "Generic Samsung TV",
    "device_category": "TV",
    "brand": "Generic Samsung",
    "model": "TV",
    "source_path": "generic/samsung_tv"
  },
  {
    "id": 208,
    "display_name": "Generic LG TV",
    "device_category": "TV",
    "brand": "Generic LG",
    "model": "TV",
    "source_path": "generic/lg_tv"
  }
]
```

### Template Preview Response
```json
{
  "yaml": "# Generated ESPHome YAML...",
  "char_count": 12660,
  "selected_devices": [
    {
      "library_id": 207,
      "display_name": "Generic Samsung TV",
      "device_category": "TV",
      "brand": "Generic Samsung"
    }
  ]
}
```

### Device Discovery Response
```json
{
  "devices": [
    {
      "hostname": "ir-abc123",
      "ip": "192.168.101.149",
      "mac": "DC:F8:9F:AB:C1:23",
      "project": "tapcommand.universal_ir",
      "version": "1.0.26",
      "capabilities": {
        "brands": ["Generic Samsung", "Generic LG"],
        "commands": ["power", "volume_up", "number_1"]
      }
    }
  ]
}
```

---

## 🛠️ Technical Implementation Details

### Port Configuration System
**THE CORE FEATURE** - This is what the whole system is built around:

```typescript
interface PortAssignment {
  port_number: 1 | 2 | 3 | 4 | 5;  // D1 Mini has 5 IR ports
  library_id: number;               // Which IR library to use
}

// Example: Samsung on port 1, LG on port 3
const assignments: PortAssignment[] = [
  { port_number: 1, library_id: 207 }, // Samsung
  { port_number: 3, library_id: 208 }  // LG
];
```

**GPIO Mapping** (FYI - handled by backend):
- Port 1: GPIO13 (D7)
- Port 2: GPIO15 (D8)
- Port 3: GPIO12 (D6)
- Port 4: GPIO16 (D0)
- Port 5: GPIO5 (D1)

### Template System Flow
1. **User selects** IR libraries for ports
2. **Backend generates** dynamic YAML with proper transmitters
3. **ESPHome compiles** YAML to .bin firmware
4. **User downloads** .bin file for ESP flashing

### Authentication & CORS
- **No auth required** - this is a local development system
- **CORS enabled** for `localhost:3000`, `localhost:5173`
- **File uploads** supported for firmware download

---

## 🔥 API Testing Examples (Test These First)

### Quick Health Check
```bash
curl http://localhost:8000/
# Should return: {"message": "TapCommand API is running"}
```

### Get Available Libraries
```bash
curl http://localhost:8000/api/v1/ir_libraries | jq .
```

### Preview a Template
```bash
curl -X POST http://localhost:8000/api/v1/templates/preview \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": 1,
    "assignments": [{"port_number": 1, "library_id": 207}],
    "include_comments": true
  }'
```

### Start Device Discovery
```bash
curl -X POST http://localhost:8000/api/v1/devices/discovery/start
curl http://localhost:8000/api/v1/devices/discovery/devices
```

---

## ⚠️ Common Gotchas & How to Avoid Them

### 1. **Template ID is Always 1**
```typescript
// ✅ Correct
const request = { template_id: 1, assignments: [...] };

// ❌ Wrong - there's only one template
const request = { template_id: 2, assignments: [...] };
```

### 2. **Port Numbers are 1-5, Not 0-4**
```typescript
// ✅ Correct
{ port_number: 1, library_id: 207 }

// ❌ Wrong - ports start at 1
{ port_number: 0, library_id: 207 }
```

### 3. **Preview Before Compile**
Always call `/templates/preview` before `/templates/compile` to show users what they're building.

### 4. **Handle Empty Assignments**
The backend handles empty port assignments gracefully - don't crash if user hasn't assigned anything yet.

### 5. **Async Operations Take Time**
- Device discovery: ~10-30 seconds
- Firmware compilation: ~30-120 seconds
- Show progress indicators!

---

## 🎨 UI Component Ideas (Make It Beautiful)

### IR Library Browser
```typescript
interface IRLibrary {
  id: number;
  display_name: string;
  device_category: string;
  brand: string;
  model: string;
}

// Component ideas:
// - Search/filter by brand, category
// - Card-based layout with device icons
// - Drag-and-drop to port slots
// - Command preview on hover
```

### Port Configuration Panel
```typescript
// Visual port assignment interface
// - 5 port slots (visual representation)
// - Drop zones for IR libraries
// - Clear/reset buttons
// - Live preview of assignments
```

### YAML Preview
```typescript
// Syntax-highlighted code display
// - Copy-to-clipboard button
// - Download raw YAML option
// - Diff view for changes
// - Collapsible sections
```

### Device Status Panel
```typescript
interface ESPDevice {
  hostname: string;    // ir-abc123
  ip: string;         // 192.168.101.149
  mac: string;        // DC:F8:9F:AB:C1:23
  status: 'online' | 'offline' | 'unknown';
  last_seen: string;
  capabilities: {
    brands: string[];
    commands: string[];
  };
}
```

---

## 🧪 Testing Strategy (Don't Skip This)

### Unit Tests
- API service functions
- Data transformation utils
- Component prop handling
- Error boundary behavior

### Integration Tests
- Full user workflows
- API error handling
- File download flows
- WebSocket connections

### Manual Testing Checklist
- [ ] Load IR libraries list
- [ ] Assign libraries to ports
- [ ] Preview generated YAML
- [ ] Compile firmware successfully
- [ ] Download .bin file
- [ ] Discover network devices
- [ ] Send test commands
- [ ] Handle API errors gracefully

---

## 🚀 Deployment Notes

### Development Setup
```bash
# Backend (already running)
cd /home/coastal/tapcommand/backend
./run.sh

# Frontend (your job)
cd /home/coastal/tapcommand/frontend
npm install
npm run dev
# Should open http://localhost:5173
```

### Build Configuration
- **Vite**: Already configured
- **TypeScript**: Ready to go
- **React**: Latest version
- **API Proxy**: Backend runs on :8000

### Environment Variables
```typescript
// .env.local
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

---

## 📚 Learning Resources (If You Get Stuck)

### FastAPI Docs
- **OpenAPI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Concepts to Understand
- **ESPHome**: YAML-based ESP firmware builder
- **IR Protocols**: Samsung, NEC, RC5, etc.
- **GPIO Mapping**: How ports map to pins
- **Template Placeholders**: {{TRANSMITTER_BLOCK}}, etc.

### Code Examples in Backend
- **templates.py**: Contains all the template logic you need to understand
- **models/**: Database schema definitions
- **services/**: Business logic for device management

---

## 🎭 Final Wisdom (From Backend Claude)

### What Makes a Good Frontend
1. **Fast Initial Load**: Don't fetch everything at once
2. **Intuitive UX**: Drag-and-drop beats dropdowns
3. **Error Handling**: Show helpful messages, not crashes
4. **Loading States**: Users hate waiting in the dark
5. **Responsive Design**: Works on phones and tablets
6. **Accessibility**: Use semantic HTML and ARIA labels

### What Not to Do
1. **Don't reinvent the wheel**: Use established libraries
2. **Don't ignore TypeScript**: It will save you hours of debugging
3. **Don't skip error boundaries**: React crashes are ugly
4. **Don't hardcode values**: Use the API responses
5. **Don't forget loading states**: They matter more than you think

### The Secret Sauce
The backend does all the heavy lifting. Your job is to make it **accessible** and **beautiful**. Focus on the user experience - make it so simple that even I could use it (and I'm just an API).

---

## 🏆 Success Metrics (How to Know You've Won)

### Technical Goals
- [ ] All API endpoints working
- [ ] Error handling implemented
- [ ] Loading states everywhere
- [ ] TypeScript strict mode enabled
- [ ] No console errors
- [ ] Mobile-responsive design

### User Experience Goals
- [ ] Can assign IR libraries to ports in under 30 seconds
- [ ] Can preview and compile firmware without confusion
- [ ] Can discover and control devices easily
- [ ] Error messages are helpful, not cryptic
- [ ] UI feels fast and responsive

### The Ultimate Test
**If a non-technical user can successfully create and flash firmware for an IR blaster using your interface, you've succeeded.**

---

## 🤝 Getting Help (When Things Go Wrong)

### Backend Status Check
```bash
# Is the backend running?
curl http://localhost:8000/

# Are there any backend errors?
tail -f /tmp/backend.log
```

### Frontend Debugging
- **React DevTools**: Essential browser extension
- **Network Tab**: Check API requests/responses
- **Console**: Look for TypeScript errors
- **API Docs**: http://localhost:8000/docs

### Common Issues & Solutions
1. **CORS errors**: Backend should handle this
2. **404 on API calls**: Check endpoint URLs in docs
3. **TypeScript errors**: Fix them, don't ignore them
4. **React crashes**: Use error boundaries

---

**Remember**: The backend is solid. Your job is to make it shine. You've got this! 🌟

*- Backend Claude (The one who actually knows what they're doing)*

---

**P.S.**: When you inevitably succeed and create something amazing, remember to give credit where credit is due - to the rock-solid backend architecture that made it all possible. 😉