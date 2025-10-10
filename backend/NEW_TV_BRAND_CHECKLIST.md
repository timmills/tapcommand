# Adding New TV Brand Support - Complete Checklist

**Date:** October 7, 2025
**Purpose:** Comprehensive checklist for adding network control support for new TV brands

---

## Prerequisites

Before starting, gather this information about the new TV brand:

- [ ] **Brand name** (e.g., "CHiQ", "Vizio", "Hisense")
- [ ] **Control protocol** (e.g., "Android TV Remote v2", "MQTT", "REST API")
- [ ] **Network ports** used for control
- [ ] **Authentication method** (pairing, PSK, token, none)
- [ ] **Python library** available (check PyPI)
- [ ] **MAC address prefixes** (OUI database lookup)
- [ ] **Power-on capability** (WOL, network command, IR only)
- [ ] **Status query capability** (power, volume, input, app)

---

## Step 1: Research & Documentation

### 1.1 Create Research Document

- [ ] Create `backend/[BRAND]_TV_RESEARCH.md`
- [ ] Document protocol details (ports, auth, capabilities)
- [ ] Document Python library (if available)
- [ ] Compare with other brands (create comparison table)
- [ ] Document power-on limitations
- [ ] Document status query capabilities
- [ ] Create implementation plan with code examples
- [ ] Estimate implementation time (backend + frontend)

**Example:** `backend/CHIQ_TV_RESEARCH.md`

### 1.2 Gather MAC Address Prefixes

- [ ] Look up manufacturer MAC OUI prefixes at https://maclookup.app/
- [ ] Find at least 5-10 common MAC prefixes
- [ ] Note any sub-brands that share MAC addresses
- [ ] Document MAC prefixes in research document

**Example MAC lookup sources:**
- IEEE OUI database
- Wireshark manufacturer database
- macvendors.com
- maclookup.app

---

## Step 2: Backend Implementation

### 2.1 Create Executor

- [ ] Create `backend/app/commands/executors/network/[brand].py`
- [ ] Implement `CommandExecutor` interface
- [ ] Define `KEY_MAP` with 50+ commands
- [ ] Implement `can_execute()` method
- [ ] Implement `execute()` method
- [ ] Add error handling and timeouts
- [ ] Add connection retry logic
- [ ] Test with mock connections

**Required methods:**
```python
class BrandExecutor(CommandExecutor):
    KEY_MAP = { ... }  # 50+ commands

    def can_execute(self, command: Command) -> bool
    async def execute(self, command: Command) -> ExecutionResult
```

**Standard commands to support:**
- Power: `power`, `power_on`, `power_off`
- Volume: `volume_up`, `volume_down`, `mute`
- Navigation: `up`, `down`, `left`, `right`, `ok`, `enter`, `back`, `home`, `menu`
- Numbers: `0` through `9`
- Channels: `channel_up`, `channel_down`
- Media: `play`, `pause`, `stop`, `rewind`, `fast_forward`
- Sources: `hdmi_1`, `hdmi_2`, `hdmi_3`, `hdmi_4`

### 2.2 Update Router

- [ ] Edit `backend/app/commands/router.py`
- [ ] Import new executor: `from .executors.network import BrandExecutor`
- [ ] Add routing logic in `get_executor()`:
  ```python
  elif command.protocol == "brand_protocol":
      return BrandExecutor(self.db)
  ```

### 2.3 Update __init__.py

- [ ] Edit `backend/app/commands/executors/network/__init__.py`
- [ ] Add import: `from .brand import BrandExecutor`
- [ ] Add to `__all__`: `"BrandExecutor"`

### 2.4 Add Dependencies

- [ ] Edit `backend/requirements.txt`
- [ ] Add Python library with pinned version
  ```
  brandlib>=1.0.0
  ```
- [ ] Test installation: `pip install -r requirements.txt`

### 2.5 Add Status Polling (if supported)

- [ ] Edit `backend/app/services/tv_status_poller.py`
- [ ] Add brand to `SUPPORTED_PROTOCOLS` dict
- [ ] Implement `_poll_[brand]()` method
- [ ] Return status dict with: `power`, `volume`, `muted`, `input`, `app`
- [ ] Handle connection failures gracefully

**Example:**
```python
async def _poll_brand(self, device: VirtualDevice) -> Optional[Dict[str, Any]]:
    try:
        # Query TV status
        return {
            "power": "on",  # "on"|"off"|"standby"
            "volume": 25,   # 0-100
            "muted": False,
            "input": "HDMI 1",
            "app": "Netflix"
        }
    except Exception as e:
        logger.debug(f"Brand poll failed: {e}")
        return None
```

### 2.6 Update Virtual Device Model (if needed)

- [ ] Check if `backend/app/models/virtual_controller.py` needs updates
- [ ] Add any brand-specific config fields to `connection_config` JSON
- [ ] Update migration if database schema changes

---

## Step 3: Network Discovery

### 3.1 Update device_scanner_config.py

- [ ] Edit `backend/app/services/device_scanner_config.py`
- [ ] Add new entry to `DEVICE_TYPES` dict
- [ ] Define `mac_vendor_patterns` (all MAC prefixes)
- [ ] Define `port_scans` (ports to check)
- [ ] Set `priority` (100 = highest)
- [ ] Set `enabled = True`

**Example:**
```python
"brand_model": DeviceTypeConfig(
    device_type="brand_model",
    display_name="Brand Model TV",
    mac_vendor_patterns=["brand", "brand electronics"],
    port_scans=[
        PortScanRule(port=1234, protocol="tcp", description="Brand Control API", timeout_ms=500),
    ],
    priority=85,
    enabled=True
),
```

### 3.2 Update venue_tv_discovery.py

- [ ] Edit `venue_tv_discovery.py`
- [ ] Add MAC prefixes to `TV_VENDORS` dict (lines 53-86)
  ```python
  "AA:BB:CC": "Brand", "DD:EE:FF": "Brand",
  ```
- [ ] Add protocol to `PROTOCOL_PORTS` dict (lines 88-96)
  ```python
  "Brand Protocol": [1234, 5678],
  ```
- [ ] Update `detect_tv_protocol()` function (lines 229-270)
  - Add vendor check: `elif vendor == "Brand":`
  - Add ports to check: `ports_to_check.extend([1234])`
  - Add port-to-protocol mapping
- [ ] Update `print_adoption_guide()` (lines 448-493)
  - Add section for new brand with setup instructions

### 3.3 Update get_all_tv_vendors()

- [ ] Edit `backend/app/services/device_scanner_config.py`
- [ ] Add new device type to `tv_types` list in `get_all_tv_vendors()` function (line 238)

---

## Step 4: API Endpoints (if pairing required)

### 4.1 Create Pairing Router (if needed)

- [ ] Create `backend/app/routers/[brand]_pairing.py`
- [ ] Implement pairing start endpoint
- [ ] Implement pairing complete endpoint
- [ ] Store pairing credentials in `connection_config` JSON
- [ ] Return success/failure messages

**Example for pairing-based auth:**
```python
@router.post("/start")
async def start_pairing(request: PairingStartRequest):
    # Initiate pairing, show code on TV
    pass

@router.post("/complete")
async def complete_pairing(request: PairingCodeRequest):
    # Complete pairing, store certificate/key
    pass
```

### 4.2 Register Router in main.py

- [ ] Edit `backend/app/main.py`
- [ ] Import pairing router: `from .routers.brand_pairing import router as brand_pairing_router`
- [ ] Register router: `app.include_router(brand_pairing_router)`

---

## Step 5: Database Updates

### 5.1 Update Migration (if needed)

- [ ] Check if new fields needed in `virtual_devices` table
- [ ] Create migration script if needed
- [ ] Test migration on test database

### 5.2 Update Models

- [ ] Edit `backend/app/models/virtual_controller.py` if needed
- [ ] Add any brand-specific fields
- [ ] Document fields in model docstring

---

## Step 6: Frontend Integration

### 6.1 Update Brand Info Cards

- [ ] Edit `frontend-v2/src/features/network-controllers/components/brand-info-cards.tsx`
- [ ] Add new brand to `brandData` object
- [ ] Include: name, protocol, port, auth method, powerOn capability
- [ ] Add setup steps array
- [ ] Add notes/warnings array

**Example:**
```typescript
'brand_protocol': {
  name: 'Brand Model TV',
  protocol: 'brand_protocol',
  port: '1234',
  auth: 'Pairing Required',
  powerOn: '✓ Network (WOL)',
  setupSteps: [
    'Ensure TV is on same network',
    'Enable network control in TV settings',
    'Pair via TapCommand UI'
  ],
  notes: [
    'Supports full bidirectional control',
    'Status polling available'
  ]
}
```

### 6.2 Update Network Controllers Page

- [ ] Edit `frontend-v2/src/features/network-controllers/pages/network-controllers-page.tsx`
- [ ] Verify brand appears in brand selector
- [ ] Test brand info card expansion
- [ ] Test protocol selection

### 6.3 Create Pairing UI (if needed)

- [ ] Create pairing modal component
- [ ] Add pairing flow to adoption process
- [ ] Show pairing code from TV
- [ ] Handle pairing success/failure
- [ ] Store pairing credentials

---

## Step 7: Documentation

### 7.1 Update SUPPORTED_NETWORK_TVS.md

- [ ] Edit `backend/SUPPORTED_NETWORK_TVS.md`
- [ ] Add brand to comparison matrix
- [ ] Update total brand count
- [ ] Add brand-specific notes

### 7.2 Update NETWORK_TV_SETUP_GUIDE.md

- [ ] Edit `backend/NETWORK_TV_SETUP_GUIDE.md`
- [ ] Add setup section for new brand
- [ ] Include prerequisites
- [ ] Include step-by-step setup
- [ ] Include troubleshooting tips

### 7.3 Update NETWORK_TV_STATUS_CAPABILITIES.md

- [ ] Edit `backend/NETWORK_TV_STATUS_CAPABILITIES.md`
- [ ] Add status capability matrix for new brand
- [ ] Document what can be queried (power, volume, etc.)
- [ ] Add API examples

### 7.4 Update HYBRID_DEVICE_ARCHITECTURE_PROPOSAL.md

- [ ] Update power-on recommendations for new brand
- [ ] Add to "Status Monitoring Capabilities" section

---

## Step 8: Testing

### 8.1 Unit Tests

- [ ] Create `backend/tests/test_[brand]_executor.py`
- [ ] Test `can_execute()` logic
- [ ] Test command execution with mocks
- [ ] Test error handling
- [ ] Test timeout handling

### 8.2 Integration Tests

- [ ] Test discovery with real TV (if available)
- [ ] Test pairing process
- [ ] Test basic commands (power, volume, navigation)
- [ ] Test status polling
- [ ] Test error scenarios (TV offline, network issues)

### 8.3 Manual Testing Checklist

With real TV:
- [ ] Discover TV on network
- [ ] Verify correct MAC vendor detection
- [ ] Verify correct port detection
- [ ] Complete pairing (if required)
- [ ] Test power toggle
- [ ] Test volume up/down
- [ ] Test navigation (up/down/left/right/OK)
- [ ] Test input switching
- [ ] Verify status polling updates (if supported)
- [ ] Test error handling (unplug network cable)

---

## Step 9: Git Workflow

### 9.1 Branch Management

- [ ] Create feature branch: `git checkout -b feature/add-[brand]-tv-support`
- [ ] Commit incrementally:
  - Backend executor
  - Discovery updates
  - Frontend updates
  - Documentation
- [ ] Push to GitHub: `git push origin feature/add-[brand]-tv-support`

### 9.2 Commit Messages

Use descriptive commit messages:
- `feat: Add [Brand] TV executor with [protocol] support`
- `feat: Add [Brand] MAC prefixes to discovery`
- `docs: Add [Brand] TV setup guide and capabilities`
- `test: Add unit tests for [Brand] executor`

---

## Step 10: Deployment

### 10.1 Backend Deployment

- [ ] Run database migration (if needed)
- [ ] Install new dependencies: `pip install -r requirements.txt`
- [ ] Restart backend service
- [ ] Verify API docs show new endpoints
- [ ] Check logs for errors

### 10.2 Frontend Deployment

- [ ] Build frontend: `npm run build`
- [ ] Restart frontend service
- [ ] Verify brand appears in UI
- [ ] Test adoption flow end-to-end

---

## Quick Reference: File Locations

### Backend Files to Modify:
1. `backend/app/commands/executors/network/[brand].py` - **NEW**
2. `backend/app/commands/router.py` - Add routing
3. `backend/app/commands/executors/network/__init__.py` - Export executor
4. `backend/requirements.txt` - Add library
5. `backend/app/services/tv_status_poller.py` - Add polling
6. `backend/app/services/device_scanner_config.py` - Add discovery config
7. `backend/app/routers/[brand]_pairing.py` - **NEW** (if pairing needed)
8. `backend/app/main.py` - Register router (if pairing)

### Discovery Files to Modify:
1. `venue_tv_discovery.py` - Add MAC prefixes, ports, protocols
2. `backend/app/services/device_scanner_config.py` - Add to DEVICE_TYPES

### Frontend Files to Modify:
1. `frontend-v2/src/features/network-controllers/components/brand-info-cards.tsx`
2. `frontend-v2/src/features/network-controllers/pages/network-controllers-page.tsx`

### Documentation Files to Update:
1. `backend/[BRAND]_TV_RESEARCH.md` - **NEW**
2. `backend/SUPPORTED_NETWORK_TVS.md`
3. `backend/NETWORK_TV_SETUP_GUIDE.md`
4. `backend/NETWORK_TV_STATUS_CAPABILITIES.md`
5. `backend/HYBRID_DEVICE_ARCHITECTURE_PROPOSAL.md`
6. `backend/NEW_TV_BRAND_CHECKLIST.md` - This file!

---

## Estimated Time Per Brand

| Task | Time |
|------|------|
| Research & Documentation | 1-2 hours |
| Backend Executor | 1-2 hours |
| Discovery Integration | 30 min |
| Frontend Integration | 1-2 hours |
| Testing | 1 hour |
| Documentation Updates | 30 min |
| **Total** | **5-8 hours** |

---

## Android TV Brands Quick Reference

Brands using **Android TV / Google TV** protocol (same as CHiQ):

| Brand | MAC Prefix Examples | Notes |
|-------|---------------------|-------|
| CHiQ | (Changhong prefixes) | Sub-brand of Changhong |
| TCL | 00:0C:61, 10:05:01, C8:28:32 | Some models use Roku instead |
| Sharp | 00:03:A0, 00:17:C8, 08:7A:4C | Mix of Android TV and proprietary |
| Toshiba | 00:00:39, 00:0D:F6, 00:21:35 | Newer models use Android TV |
| Hisense | See device_scanner_config | Mix of VIDAA and Android TV |
| Philips | See device_scanner_config | Mix of Android TV and proprietary |
| Sony | See device_scanner_config | All newer models use Google TV |
| Motorola | (Varies by region) | Budget Android TVs |
| Nokia | (Varies by region) | Licensed Android TVs |

**Android TV Remote Protocol v2:**
- Port: 6466 (control), 6467 (pairing)
- Library: `androidtvremote2`
- Authentication: Pairing (4-digit code on TV screen)
- Status: Power state, current app

---

## Notes

- **Always test with real hardware** before marking complete
- **Document quirks** in brand research file
- **Ask user for approval** before major architecture changes
- **Keep documentation updated** as you discover issues
- **Use consistent naming** across all files (e.g., "brand_protocol" not "Brand-Protocol")

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
