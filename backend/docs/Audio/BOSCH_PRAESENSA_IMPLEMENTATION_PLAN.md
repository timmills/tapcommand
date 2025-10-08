# Bosch Praesensa Implementation Plan
**Using AES70py - Audio Zone Control via Virtual Devices**

## Executive Summary

Implement Bosch Praesensa amplifier control using the **AES70py Python library** with zones mapped as Virtual Devices on a Virtual Audio Controller. This mirrors our successful network TV implementation.

**Timeline**: 3-4 weeks
**Complexity**: Medium (similar to network TV control)
**Cost**: $0 (open source, no licenses required)

---

## Architecture Overview

### Concept: Audio Zones as Virtual Devices

Just like network TVs, we'll treat audio zones as Virtual Devices:

```
Network TV:           Audio Zone:
-----------           -----------
nw-abc123            → aud-praesensa-001       (Virtual Controller)
  ├─ port 1 (TV)     →   ├─ zone 1 (Lobby)    (Virtual Device)
                         ├─ zone 2 (Cafe)      (Virtual Device)
                         └─ zone 3 (Office)    (Virtual Device)
```

**Key Insight**: Praesensa zones are discovered via AES70 role map, then mapped to Virtual Devices

---

## Database Schema

### Option 1: Reuse Existing Virtual Controllers (Recommended)

**No new tables needed!** Reuse `virtual_controllers` and `virtual_devices`:

```python
# Virtual Controller for Praesensa amplifier
VirtualController(
    controller_id="aud-praesensa-001",
    controller_name="Office Audio System",
    controller_type="audio",  # New type: "network_tv" or "audio"
    ip_address="192.168.1.100",
    port=65000,  # AES70 default port
    connection_config={
        "protocol": "aes70",
        "auth_username": "admin",  # Optional
        "auth_password": "****",   # Optional
        "keepalive_interval": 10
    },
    is_online=True,
    last_seen=datetime.now()
)

# Virtual Device for each zone
VirtualDevice(
    controller_id=1,  # FK to virtual_controllers
    device_name="Lobby Audio",
    device_type="audio_zone",
    protocol="bosch_aes70",
    port_number=1,  # Zone number (for compatibility)
    connection_config={
        "role_path": "Zones/Lobby",  # AES70 role map path
        "zone_id": "zone_001",
        "gain_range": [-80, 10],     # dB range
        "default_volume": -20         # Default dB level
    },
    # Status cache fields (already exist)
    cached_power_state="on",
    cached_volume_level=50,  # 0-100 scale (converted from dB)
    cached_mute_status=False,
    is_online=True,
    status_available=True
)
```

### Schema Additions Needed

**Add to `virtual_controllers` table**:
```sql
ALTER TABLE virtual_controllers ADD COLUMN controller_type VARCHAR(20) DEFAULT 'network_tv';
-- Values: 'network_tv', 'audio'
```

**Existing fields work perfectly**:
- ✅ `cached_volume_level` - Volume (0-100 scale)
- ✅ `cached_mute_status` - Mute state
- ✅ `cached_power_state` - Zone active/inactive
- ✅ `connection_config` - JSON for AES70 role paths
- ✅ `protocol` - "bosch_aes70"

---

## Discovery Service

### AES70 Zone Discovery

When a Praesensa controller is added, automatically discover zones:

```python
# backend/app/services/aes70_discovery.py

import asyncio
from typing import List, Dict, Any
from aes70 import tcp_connection, remote_device
from ..models.virtual_controller import VirtualController, VirtualDevice
from ..db.database import SessionLocal

class AES70DiscoveryService:
    """Discover AES70 audio zones and create Virtual Devices"""

    async def discover_praesensa_zones(
        self,
        controller_id: str,
        ip_address: str,
        port: int = 65000,
        username: str = None,
        password: str = None
    ) -> List[Dict[str, Any]]:
        """
        Connect to Praesensa and discover all zones via role map

        Returns list of zone configurations ready for VirtualDevice creation
        """

        # Connect to AES70 device
        connection = await tcp_connection.connect(
            ip_address=ip_address,
            port=port
        )

        device = remote_device.RemoteDevice(connection)
        device.set_keepalive_interval(10)

        # Get device info
        model = await device.DeviceManager.GetModelDescription()

        # Get role map (named objects)
        role_map = await device.get_role_map()

        # Find zone objects
        zones = []
        zone_number = 1

        for role_path, obj in role_map.items():
            # Look for gain controls (volume objects)
            # Typical paths: "Zones/Lobby/Gain", "Zone1/Volume", etc.
            if "zone" in role_path.lower() and "gain" in role_path.lower():
                # Extract zone name from path
                parts = role_path.split("/")
                zone_name = parts[-2] if len(parts) > 1 else f"Zone {zone_number}"

                # Check if there's a mute object nearby
                mute_path = role_path.replace("Gain", "Mute")
                has_mute = mute_path in role_map

                # Get gain range
                try:
                    min_gain = await obj.GetMinGain() if hasattr(obj, 'GetMinGain') else -80
                    max_gain = await obj.GetMaxGain() if hasattr(obj, 'GetMaxGain') else 10
                except:
                    min_gain, max_gain = -80, 10

                zones.append({
                    "zone_number": zone_number,
                    "zone_name": zone_name,
                    "role_path": role_path,
                    "mute_path": mute_path if has_mute else None,
                    "gain_range": [min_gain, max_gain],
                    "has_mute": has_mute
                })

                zone_number += 1

        await connection.close()

        return zones

    def create_virtual_devices_from_zones(
        self,
        db: SessionLocal,
        controller: VirtualController,
        zones: List[Dict[str, Any]]
    ):
        """Create VirtualDevice entries for discovered zones"""

        for zone in zones:
            # Check if device already exists
            existing = db.query(VirtualDevice).filter(
                VirtualDevice.controller_id == controller.id,
                VirtualDevice.port_number == zone["zone_number"]
            ).first()

            if existing:
                continue  # Skip if already exists

            # Create new Virtual Device for zone
            virtual_device = VirtualDevice(
                controller_id=controller.id,
                device_name=zone["zone_name"],
                device_type="audio_zone",
                protocol="bosch_aes70",
                port_number=zone["zone_number"],
                connection_config={
                    "role_path": zone["role_path"],
                    "mute_path": zone["mute_path"],
                    "gain_range": zone["gain_range"],
                    "default_volume": -20
                },
                cached_power_state="on",
                cached_volume_level=50,
                cached_mute_status=False,
                is_online=True,
                status_available=True
            )

            db.add(virtual_device)

        db.commit()


# Usage example:
async def add_praesensa_controller(ip_address: str, controller_name: str):
    db = SessionLocal()

    # Create Virtual Controller
    controller = VirtualController(
        controller_id=f"aud-praesensa-{ip_address.replace('.', '')}",
        controller_name=controller_name,
        controller_type="audio",
        ip_address=ip_address,
        port=65000,
        connection_config={"protocol": "aes70"},
        is_online=True
    )
    db.add(controller)
    db.commit()

    # Discover zones
    discovery = AES70DiscoveryService()
    zones = await discovery.discover_praesensa_zones(
        controller_id=controller.controller_id,
        ip_address=ip_address,
        port=65000
    )

    # Create Virtual Devices for zones
    discovery.create_virtual_devices_from_zones(db, controller, zones)

    db.close()
```

---

## Command Executor

### Bosch AES70 Executor

```python
# backend/app/commands/executors/audio/bosch_aes70.py

import asyncio
from typing import Optional
from aes70 import tcp_connection, remote_device
from aes70.types import OcaMuteState

from ...models import Command, CommandResult
from ...router import CommandExecutor
from ....models.virtual_controller import VirtualController, VirtualDevice
from ....db.database import SessionLocal

class BoschAES70Executor(CommandExecutor):
    """Execute commands on Bosch Praesensa via AES70 protocol"""

    def __init__(self, db: SessionLocal):
        self.db = db
        self._connections = {}  # Cache connections per controller

    async def execute(self, command: Command) -> CommandResult:
        """Execute audio zone command"""

        # Get Virtual Controller
        vc = self.db.query(VirtualController).filter(
            VirtualController.controller_id == command.controller_id
        ).first()

        if not vc:
            return CommandResult(
                success=False,
                message=f"Audio controller {command.controller_id} not found"
            )

        # Get Virtual Device (zone)
        # Note: port_number is used to identify the zone
        vd = self.db.query(VirtualDevice).filter(
            VirtualDevice.controller_id == vc.id,
            VirtualDevice.port_number == command.parameters.get("zone_number", 1)
        ).first()

        if not vd:
            return CommandResult(
                success=False,
                message=f"Zone not found for controller {command.controller_id}"
            )

        # Get or create AES70 connection
        device = await self._get_connection(vc)

        if not device:
            return CommandResult(
                success=False,
                message=f"Failed to connect to {vc.controller_name}"
            )

        # Execute command based on type
        try:
            if command.command == "volume_up":
                return await self._volume_up(device, vd)
            elif command.command == "volume_down":
                return await self._volume_down(device, vd)
            elif command.command == "set_volume":
                volume = command.parameters.get("volume", 50)
                return await self._set_volume(device, vd, volume)
            elif command.command == "mute":
                return await self._mute(device, vd, True)
            elif command.command == "unmute":
                return await self._mute(device, vd, False)
            elif command.command == "toggle_mute":
                return await self._toggle_mute(device, vd)
            else:
                return CommandResult(
                    success=False,
                    message=f"Unknown command: {command.command}"
                )

        except Exception as e:
            return CommandResult(
                success=False,
                message=f"AES70 error: {str(e)}"
            )

    async def _get_connection(self, controller: VirtualController) -> Optional[remote_device.RemoteDevice]:
        """Get or create AES70 connection to controller"""

        controller_id = controller.controller_id

        # Return cached connection if exists
        if controller_id in self._connections:
            return self._connections[controller_id]

        try:
            # Connect
            connection = await tcp_connection.connect(
                ip_address=controller.ip_address,
                port=controller.port or 65000
            )

            device = remote_device.RemoteDevice(connection)
            device.set_keepalive_interval(10)

            # Cache connection
            self._connections[controller_id] = device

            return device

        except Exception as e:
            print(f"Failed to connect to {controller.controller_name}: {e}")
            return None

    async def _set_volume(self, device: remote_device.RemoteDevice, zone: VirtualDevice, volume: int) -> CommandResult:
        """Set volume (0-100 scale) on zone"""

        # Get role map
        role_map = await device.get_role_map()

        # Get gain object from zone config
        role_path = zone.connection_config.get("role_path")
        gain_obj = role_map.get(role_path)

        if not gain_obj:
            return CommandResult(
                success=False,
                message=f"Gain object not found at {role_path}"
            )

        # Convert 0-100 volume to dB
        gain_range = zone.connection_config.get("gain_range", [-80, 10])
        min_db, max_db = gain_range
        db_value = min_db + (volume / 100.0) * (max_db - min_db)

        # Set gain
        await gain_obj.SetGain(db_value)

        # Update cache
        zone.cached_volume_level = volume
        self.db.commit()

        return CommandResult(
            success=True,
            message=f"Set {zone.device_name} to {volume}% ({db_value:.1f}dB)"
        )

    async def _volume_up(self, device: remote_device.RemoteDevice, zone: VirtualDevice) -> CommandResult:
        """Increase volume by 5%"""
        current_volume = zone.cached_volume_level or 50
        new_volume = min(100, current_volume + 5)
        return await self._set_volume(device, zone, new_volume)

    async def _volume_down(self, device: remote_device.RemoteDevice, zone: VirtualDevice) -> CommandResult:
        """Decrease volume by 5%"""
        current_volume = zone.cached_volume_level or 50
        new_volume = max(0, current_volume - 5)
        return await self._set_volume(device, zone, new_volume)

    async def _mute(self, device: remote_device.RemoteDevice, zone: VirtualDevice, mute: bool) -> CommandResult:
        """Mute/unmute zone"""

        # Get role map
        role_map = await device.get_role_map()

        # Get mute object from zone config
        mute_path = zone.connection_config.get("mute_path")
        if not mute_path:
            return CommandResult(
                success=False,
                message=f"Zone {zone.device_name} does not support mute"
            )

        mute_obj = role_map.get(mute_path)
        if not mute_obj:
            return CommandResult(
                success=False,
                message=f"Mute object not found at {mute_path}"
            )

        # Set mute state
        new_state = OcaMuteState.Muted if mute else OcaMuteState.Unmuted
        await mute_obj.SetState(new_state)

        # Update cache
        zone.cached_mute_status = mute
        self.db.commit()

        return CommandResult(
            success=True,
            message=f"{'Muted' if mute else 'Unmuted'} {zone.device_name}"
        )

    async def _toggle_mute(self, device: remote_device.RemoteDevice, zone: VirtualDevice) -> CommandResult:
        """Toggle mute state"""
        current_mute = zone.cached_mute_status or False
        return await self._mute(device, zone, not current_mute)

    async def cleanup(self):
        """Close all connections"""
        for connection in self._connections.values():
            try:
                await connection.connection.close()
            except:
                pass
        self._connections.clear()
```

---

## Protocol Router Integration

Update the Protocol Router to support audio zones:

```python
# backend/app/commands/router.py

from .executors.audio.bosch_aes70 import BoschAES70Executor

class ProtocolRouter:
    def get_executor(self, command: Command) -> Optional[CommandExecutor]:
        # ... existing code ...

        # Audio Zone Controllers
        if command.device_type == "audio_zone":
            if command.protocol == "bosch_aes70":
                return BoschAES70Executor(self.db)

        # ... rest of code ...
```

---

## Queue Processor Integration

The queue processor already supports Virtual Devices! Just needs to handle `audio_zone` device type:

```python
# backend/app/services/queue_processor.py (minimal changes needed)

# Device type detection (around line 132)
if cmd.hostname.startswith('aud-'):
    # Audio controller
    vc = db.query(VirtualController).filter(
        VirtualController.controller_id == cmd.hostname
    ).first()

    if vc:
        vd = db.query(VirtualDevice).filter(
            VirtualDevice.controller_id == vc.id,
            VirtualDevice.port_number == cmd.port
        ).first()

        if vd:
            device_type = "audio_zone"
            protocol = vd.protocol  # "bosch_aes70"
```

---

## API Endpoints

### Add Audio Controller

```python
# backend/app/routers/audio_controllers.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..services.aes70_discovery import AES70DiscoveryService
from ..db.database import get_db

router = APIRouter(prefix="/api/audio", tags=["audio"])

@router.post("/controllers/discover")
async def discover_audio_controller(
    ip_address: str,
    controller_name: str,
    db: Session = Depends(get_db)
):
    """
    Add a Bosch Praesensa controller and discover zones
    """

    # Create Virtual Controller
    controller = VirtualController(
        controller_id=f"aud-praesensa-{ip_address.replace('.', '')}",
        controller_name=controller_name,
        controller_type="audio",
        ip_address=ip_address,
        port=65000,
        connection_config={"protocol": "aes70"},
        is_online=True
    )
    db.add(controller)
    db.commit()

    # Discover zones
    discovery = AES70DiscoveryService()
    zones = await discovery.discover_praesensa_zones(
        controller_id=controller.controller_id,
        ip_address=ip_address,
        port=65000
    )

    # Create Virtual Devices
    discovery.create_virtual_devices_from_zones(db, controller, zones)

    return {
        "controller": controller,
        "zones_discovered": len(zones),
        "zones": zones
    }

@router.get("/zones")
async def list_audio_zones(db: Session = Depends(get_db)):
    """Get all audio zones"""

    zones = db.query(VirtualDevice).filter(
        VirtualDevice.device_type == "audio_zone"
    ).all()

    return zones

@router.post("/zones/{zone_id}/volume")
async def set_zone_volume(
    zone_id: int,
    volume: int,
    db: Session = Depends(get_db)
):
    """Set zone volume (0-100)"""

    # Queue command
    from ..services.command_queue import CommandQueueService

    zone = db.query(VirtualDevice).get(zone_id)
    controller = db.query(VirtualController).get(zone.controller_id)

    cmd = CommandQueueService.queue_command(
        db=db,
        hostname=controller.controller_id,
        port=zone.port_number,
        command="set_volume",
        parameters={"volume": volume}
    )

    return {"queued": True, "command_id": cmd.id}
```

---

## Frontend - /audio Page

### Audio Control Page Structure

```typescript
// frontend-v2/src/features/audio/pages/audio-page.tsx

import { useQuery, useMutation } from '@tanstack/react-query';
import { Volume2, VolumeX, Volume1 } from 'lucide-react';

export function AudioPage() {
  const { data: zones } = useQuery({
    queryKey: ['audio-zones'],
    queryFn: () => fetch('/api/audio/zones').then(r => r.json())
  });

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Audio Control</h1>

      {/* Group by controller */}
      {Object.entries(groupByController(zones)).map(([controller, zones]) => (
        <div key={controller} className="mb-8">
          <h2 className="text-xl font-semibold mb-4">{controller}</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {zones.map(zone => (
              <ZoneCard key={zone.id} zone={zone} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function ZoneCard({ zone }) {
  const setVolume = useMutation({
    mutationFn: (volume: number) =>
      fetch(`/api/audio/zones/${zone.id}/volume`, {
        method: 'POST',
        body: JSON.stringify({ volume })
      })
  });

  const toggleMute = useMutation({
    mutationFn: () =>
      fetch(`/api/audio/zones/${zone.id}/mute`, {
        method: 'POST'
      })
  });

  const volume = zone.cached_volume_level || 50;
  const isMuted = zone.cached_mute_status || false;

  return (
    <div className="border rounded-lg p-4">
      <h3 className="font-medium mb-3">{zone.device_name}</h3>

      {/* Mute button */}
      <button
        onClick={() => toggleMute.mutate()}
        className={`mb-3 p-2 rounded ${isMuted ? 'bg-red-500' : 'bg-gray-200'}`}
      >
        {isMuted ? <VolumeX /> : <Volume2 />}
      </button>

      {/* Volume slider */}
      <div className="flex items-center gap-3">
        <Volume1 className="w-4 h-4" />
        <input
          type="range"
          min="0"
          max="100"
          value={volume}
          onChange={(e) => setVolume.mutate(Number(e.target.value))}
          className="flex-1"
        />
        <span className="text-sm w-12">{volume}%</span>
      </div>
    </div>
  );
}
```

---

## Implementation Timeline

### Week 1: Foundation
- ✅ Install AES70py library
- ✅ Add `controller_type` to database schema
- ✅ Create AES70DiscoveryService
- ✅ Test discovery with Praesensa hardware
- ✅ Create initial Virtual Devices for zones

### Week 2: Backend Implementation
- ✅ Build BoschAES70Executor
- ✅ Integrate with Protocol Router
- ✅ Update Queue Processor for audio zones
- ✅ Create API endpoints for zone control
- ✅ Test volume/mute commands

### Week 3: Frontend
- ✅ Build /audio page layout
- ✅ Implement zone cards with volume sliders
- ✅ Add mute buttons
- ✅ Real-time status updates via polling

### Week 4: Testing & Polish
- ✅ Test with multiple zones
- ✅ Add preset management (save/recall zone configs)
- ✅ Error handling & connection recovery
- ✅ Documentation & deployment

---

## Testing Checklist

### Discovery
- [ ] Connect to Praesensa controller
- [ ] Discover all configured zones
- [ ] Map zones to Virtual Devices correctly
- [ ] Handle zones with/without mute support

### Control
- [ ] Set absolute volume (0-100)
- [ ] Volume up/down commands
- [ ] Mute/unmute zones
- [ ] Queue commands correctly
- [ ] Handle errors gracefully

### Status Polling
- [ ] Poll zone status every 5 seconds
- [ ] Update cached volume levels
- [ ] Update mute status
- [ ] Detect offline zones

### Frontend
- [ ] Display all zones grouped by controller
- [ ] Volume sliders update in real-time
- [ ] Mute buttons work correctly
- [ ] Responsive design on mobile

---

## Success Criteria

✅ **Phase 1 Complete When**:
- Praesensa controller discovered
- All zones visible as Virtual Devices
- Volume control working (0-100 scale)
- Mute control working
- /audio page displays zones
- Commands queue and execute successfully

✅ **Future Enhancements**:
- Preset management (save zone configs)
- Multi-zone control (adjust all at once)
- Audio routing/source selection
- Integration with /control page (unified control)
- Support for additional amplifier brands

---

## Document Version
- **Created**: January 2025
- **Status**: Ready for implementation
- **Estimated Completion**: 3-4 weeks
