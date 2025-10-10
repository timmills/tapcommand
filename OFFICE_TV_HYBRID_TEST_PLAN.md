# Office TV - Hybrid Control Test Plan

**Date:** October 7, 2025
**Current Status:** Office TV exists as network-only (ID: 1)
**Goal:** Re-configure with hybrid IR + Network control

---

## Current Configuration

**Office TV (Virtual Controller ID: 1)**
- Name: "Office TV (Network)"
- Type: network_tv
- Protocol: samsung_legacy
- Status: Network control only (no IR fallback configured)

**Migration Status:** ❌ Hybrid fields NOT in database yet (migration needs to run)

---

## Step-by-Step Test Plan

### Phase 1: Backend Deployment (5 minutes)

#### Step 1.1: Run Database Migration

```bash
cd /home/coastal/tapcommand/backend
source ../venv/bin/activate
python migrations/run_migration.py
```

**Expected Output:**
```
🔧 TapCommand Database Migration Runner
Database: /home/coastal/tapcommand/backend/tapcommand.db

📋 Running migration: 001_add_hybrid_support_to_virtual_devices.sql
  Executing: ALTER TABLE virtual_devices ADD COLUMN fallback_ir_cont...
  Executing: ALTER TABLE virtual_devices ADD COLUMN fallback_ir_port...
  ... (12 ALTER TABLE statements)
✅ Migration completed successfully!
```

**If migration fails with "column already exists":**
- Migration already ran, skip to Step 1.2

#### Step 1.2: Restart Backend

```bash
cd /home/coastal/tapcommand/backend
./restart.sh
```

**Or manually:**
```bash
# Find backend process
ps aux | grep uvicorn

# Kill it
kill <pid>

# Restart
source ../venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
```

#### Step 1.3: Verify Hybrid Endpoints

```bash
curl http://localhost:8000/api/hybrid-devices/1/control-status
```

**Expected Response:**
```json
{
  "device_id": 1,
  "device_name": "Office TV (Network)",
  "network_available": true,
  "ir_fallback_configured": false,
  "power_on_method": "network",
  "control_strategy": "network_only",
  "recommended_power_on": "ir",
  "status_available": false,
  "protocol": "samsung_legacy"
}
```

---

### Phase 2: Identify IR Controller (2 minutes)

#### Step 2.1: List Available IR Controllers

```bash
cd /home/coastal/tapcommand/backend
source ../venv/bin/activate
python3 -c "
from app.db.database import SessionLocal
from app.models.device import Device

db = SessionLocal()
ir_controllers = db.query(Device).filter(Device.device_type == 'ir_controller').all()

print('Available IR Controllers:')
for ir in ir_controllers:
    print(f'  Hostname: {ir.hostname}')
    print(f'  IP: {ir.ip_address}')
    print(f'  Status: {\"Online\" if ir.is_online else \"Offline\"}')
    print('---')
"
```

**Note the IR controller hostname** (e.g., "ir-abc123" or "esphome-ir-blaster")

#### Step 2.2: Identify Which Port Controls Office TV

**Option A: Check existing IR port mappings**
```bash
python3 -c "
from app.db.database import SessionLocal
from app.models.ir_port import IRPort

db = SessionLocal()
ports = db.query(IRPort).filter(IRPort.device_name.ilike('%office%')).all()

for port in ports:
    print(f'Port {port.port_number} on {port.ir_controller_hostname}: {port.device_name}')
"
```

**Option B: Manual test**
- Power off Office TV
- Test IR ports 0-4 on your IR controller until TV powers on
- Note which port works

---

### Phase 3: Link IR Fallback (API Method)

#### Step 3.1: Link IR Fallback via API

**Replace these values:**
- `<IR_CONTROLLER_HOSTNAME>`: From Step 2.1 (e.g., "ir-abc123")
- `<IR_PORT_NUMBER>`: From Step 2.2 (e.g., 2)

```bash
curl -X POST http://localhost:8000/api/hybrid-devices/1/link-ir-fallback \
  -H "Content-Type: application/json" \
  -d '{
    "ir_controller_hostname": "<IR_CONTROLLER_HOSTNAME>",
    "ir_port": <IR_PORT_NUMBER>,
    "power_on_method": "hybrid",
    "control_strategy": "hybrid_ir_fallback"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "IR fallback linked successfully",
  "device_id": 1,
  "ir_controller": "ir-abc123",
  "ir_port": 2,
  "power_on_method": "hybrid"
}
```

#### Step 3.2: Verify Configuration

```bash
curl http://localhost:8000/api/hybrid-devices/1/control-status
```

**Expected Response:**
```json
{
  "device_id": 1,
  "device_name": "Office TV (Network)",
  "network_available": true,
  "ir_fallback_configured": true,
  "power_on_method": "hybrid",
  "control_strategy": "hybrid_ir_fallback",
  "recommended_power_on": "ir",
  "status_available": false,
  "protocol": "samsung_legacy",
  "ir_controller": "ir-abc123",
  "ir_port": 2
}
```

---

### Phase 4: Test Hybrid Control (10 minutes)

#### Test 4.1: Test Network Commands (Volume)

**Turn on TV first (manually if needed)**

```bash
# Volume Up via Network
curl -X POST http://localhost:8000/api/commands/execute \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": 1,
    "device_type": "network_tv",
    "command": "volume_up"
  }'
```

**Expected:**
- ✅ Volume increases on TV (fast, ~200-300ms)
- ✅ Response shows `"success": true`
- ✅ Response shows `"execution_time_ms": 200-300`

#### Test 4.2: Test Power-Off (Network First, IR Fallback)

**Power off the TV:**
```bash
curl -X POST http://localhost:8000/api/commands/execute \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": 1,
    "device_type": "network_tv",
    "command": "power_off"
  }'
```

**Expected:**
- ✅ TV powers off
- ✅ Network command succeeds (Samsung Legacy supports power-off via network)

#### Test 4.3: Test Hybrid Power-On (IR Fallback)

**Power on the TV:**
```bash
curl -X POST http://localhost:8000/api/commands/execute \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": 1,
    "device_type": "network_tv",
    "command": "power_on"
  }'
```

**Expected:**
- ⚠️ Network WOL attempt fails (Samsung Legacy doesn't support WOL)
- ✅ Hybrid router automatically tries IR fallback
- ✅ TV powers on via IR (180-500ms)
- ✅ Response shows: `"method": "ir_fallback"` or similar

**Check backend logs:**
```bash
tail -f /home/coastal/tapcommand/backend/backend.out | grep -i "power\|hybrid"
```

Should see:
```
INFO - Attempting network power-on for Office TV (Network)
WARNING - Network power-on failed, falling back to IR
INFO - IR power-on successful via ir-abc123:2
```

#### Test 4.4: Test Other Commands (Network)

**Test navigation (should use network, not IR):**
```bash
curl -X POST http://localhost:8000/api/commands/execute \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": 1,
    "device_type": "network_tv",
    "command": "up"
  }'
```

**Expected:**
- ✅ Command sent via network (fast)
- ✅ TV responds to navigation

---

### Phase 5: Test IR-Only Mode (Optional)

If you want to force IR-only for all commands:

```bash
curl -X POST http://localhost:8000/api/hybrid-devices/1/link-ir-fallback \
  -H "Content-Type: application/json" \
  -d '{
    "ir_controller_hostname": "<IR_CONTROLLER_HOSTNAME>",
    "ir_port": <IR_PORT_NUMBER>,
    "power_on_method": "ir",
    "control_strategy": "ir_only"
  }'
```

**Test all commands use IR:**
```bash
curl -X POST http://localhost:8000/api/commands/execute \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": 1,
    "device_type": "network_tv",
    "command": "volume_up"
  }'
```

**Expected:**
- ✅ Volume up sent via IR
- ✅ Response shows IR execution

**Revert back to hybrid mode:**
```bash
curl -X POST http://localhost:8000/api/hybrid-devices/1/link-ir-fallback \
  -H "Content-Type: application/json" \
  -d '{
    "ir_controller_hostname": "<IR_CONTROLLER_HOSTNAME>",
    "ir_port": <IR_PORT_NUMBER>,
    "power_on_method": "hybrid",
    "control_strategy": "hybrid_ir_fallback"
  }'
```

---

### Phase 6: Unlink IR (Cleanup Test)

If you want to remove IR fallback and go back to network-only:

```bash
curl -X DELETE http://localhost:8000/api/hybrid-devices/1/unlink-ir-fallback
```

**Expected Response:**
```json
{
  "success": true,
  "message": "IR fallback unlinked successfully",
  "device_id": 1
}
```

**Verify:**
```bash
curl http://localhost:8000/api/hybrid-devices/1/control-status
```

Should show:
```json
{
  "ir_fallback_configured": false,
  "power_on_method": "network",
  "control_strategy": "network_only"
}
```

---

## Alternative: Database Method (Direct SQL)

If APIs aren't working, you can update the database directly:

```bash
cd /home/coastal/tapcommand/backend
source ../venv/bin/activate
python3 -c "
from app.db.database import SessionLocal
from app.models.virtual_controller import VirtualDevice

db = SessionLocal()

# Get Office TV virtual device
office_vdev = db.query(VirtualDevice).filter(VirtualDevice.controller_id == 1).first()

if office_vdev:
    # Link IR fallback
    office_vdev.fallback_ir_controller = 'ir-abc123'  # REPLACE WITH YOUR IR CONTROLLER
    office_vdev.fallback_ir_port = 2  # REPLACE WITH YOUR PORT
    office_vdev.power_on_method = 'hybrid'
    office_vdev.control_strategy = 'hybrid_ir_fallback'

    db.commit()
    print('✅ Office TV configured for hybrid control')
    print(f'   IR Controller: {office_vdev.fallback_ir_controller}')
    print(f'   IR Port: {office_vdev.fallback_ir_port}')
    print(f'   Power Method: {office_vdev.power_on_method}')
else:
    print('❌ No virtual device found for Office TV')
"
```

---

## Expected Behavior Summary

### Hybrid Mode (Recommended)

| Command | Method | Speed | Fallback |
|---------|--------|-------|----------|
| **Power On** | IR (primary) | 180-500ms | Network WOL (rarely works) |
| **Power Off** | Network | 200-300ms | IR if network fails |
| **Volume Up/Down** | Network | 200-300ms | IR if network fails |
| **Navigation** | Network | 200-300ms | IR if network fails |
| **Channels** | Network | 200-300ms | IR if network fails |

### Network-Only Mode

| Command | Method | Speed | Fallback |
|---------|--------|-------|----------|
| **Power On** | Network WOL | ❌ Fails | None |
| **Power Off** | Network | 200-300ms | None |
| **Volume Up/Down** | Network | 200-300ms | None |
| **All Others** | Network | 200-300ms | None |

### IR-Only Mode

| Command | Method | Speed | Fallback |
|---------|--------|-------|----------|
| **All Commands** | IR | 180-500ms | None |

---

## Success Criteria

✅ **Migration runs successfully**
✅ **Hybrid endpoints respond** (`/api/hybrid-devices/1/...`)
✅ **IR fallback links successfully**
✅ **Power-on uses IR** (because Samsung Legacy WOL doesn't work)
✅ **Other commands use network** (faster than IR)
✅ **Automatic fallback works** if network fails
✅ **No duplicate commands** (one device, not two separate controllers)

---

## Troubleshooting

### Migration Fails

**Error:** "table virtual_devices has no column named fallback_ir_controller"

**Solution:** Migration hasn't run. Check:
```bash
ls -la /home/coastal/tapcommand/backend/migrations/
```

Ensure `001_add_hybrid_support_to_virtual_devices.sql` exists.

### API Returns 404

**Error:** Hybrid endpoints not found

**Solution:** Backend not restarted after migration. Restart:
```bash
cd /home/coastal/tapcommand/backend
./restart.sh
```

### IR Not Working

**Error:** IR fallback linked but commands don't work

**Check:**
1. IR controller is online: `curl http://localhost:8000/api/management/devices`
2. IR port is correct (test manually)
3. Backend logs show IR execution: `tail -f backend.out`

### Network Not Working

**Error:** Network commands fail

**Check:**
1. TV is on same network
2. TV IP address is correct
3. Port 55000 is open: `nc -zv <TV_IP> 55000`

---

## Quick Command Reference

**Link IR Fallback:**
```bash
curl -X POST http://localhost:8000/api/hybrid-devices/1/link-ir-fallback \
  -H "Content-Type: application/json" \
  -d '{"ir_controller_hostname": "IR_HOST", "ir_port": PORT, "power_on_method": "hybrid", "control_strategy": "hybrid_ir_fallback"}'
```

**Get Control Status:**
```bash
curl http://localhost:8000/api/hybrid-devices/1/control-status
```

**Unlink IR:**
```bash
curl -X DELETE http://localhost:8000/api/hybrid-devices/1/unlink-ir-fallback
```

**Test Power On:**
```bash
curl -X POST http://localhost:8000/api/commands/execute \
  -H "Content-Type: application/json" \
  -d '{"device_id": 1, "device_type": "network_tv", "command": "power_on"}'
```

**Test Volume:**
```bash
curl -X POST http://localhost:8000/api/commands/execute \
  -H "Content-Type: application/json" \
  -d '{"device_id": 1, "device_type": "network_tv", "command": "volume_up"}'
```

---

## Next Steps After Testing

If hybrid control works well:

1. **Apply to other TVs** - Link IR fallback to all Samsung Legacy TVs
2. **Update documentation** - Add test results to HYBRID_IMPLEMENTATION_GUIDE.md
3. **Frontend UI** - Implement IR linking modal for easy configuration
4. **Status Monitoring** - Enable status polling for supported brands

---

**Ready to test!** Start with Phase 1 (Backend Deployment) 🚀

🤖 Generated with [Claude Code](https://claude.com/claude-code)
