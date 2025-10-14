# Sonos Integration Strategy - Deep Analysis

## Executive Summary

Based on comprehensive review of the Bosch Plena Matrix integration, this document outlines the exact architectural patterns and implementation strategy for integrating Sonos speakers into TapCommand using the **Virtual Controller + Command Queue** model.

**Key Finding**: The Plena Matrix integration provides a **perfect blueprint** for Sonos. Both systems share:
- Network-based control (UDP for Plena, HTTP/SOAP for Sonos)
- Multi-zone architecture (4 zones for Plena, N speakers for Sonos)
- Volume/mute control as primary operations
- Status querying capabilities
- No concept of IR commands

---

## 1. Bosch Plena Matrix Architecture Review

### 1.1 Database Model Pattern

**VirtualController** (Represents the amplifier itself):
```python
controller_id = "plm-192-168-1-100"  # Unique identifier
controller_name = "Main Bar Audio"    # Friendly name
controller_type = "audio"             # Type classification
protocol = "bosch_plena_matrix"       # Protocol identifier
ip_address = "192.168.1.100"          # ❌ NOT STORED HERE
port = 12128                          # ❌ NOT STORED HERE
connection_config = {
    "ip_address": "192.168.1.100",    # ✅ Stored in connection_config
    "port": 12128,                     # ✅ Stored in connection_config
    "mac_address": "...",
    "device_name": "...",
    "total_zones": 4,
    "presets": [...]
}
```

**Critical Discovery**: The `ip_address` and `port` fields on `VirtualController` are **not directly populated**. Instead, these values are stored in `connection_config` JSON and retrieved by executors.

**VirtualDevice** (Represents individual zones):
```python
controller_id = 1                      # FK to virtual_controllers.id
port_number = 1                        # Zone number (1-4)
device_name = "BAR"                    # Zone name
device_type = "audio_zone"             # Device classification
protocol = "bosch_plena_matrix"        # Inherited from controller
ip_address = "192.168.1.100"           # Retrieved from controller's connection_config
port = 12128                           # Retrieved from controller's connection_config
connection_config = {
    "zone_index": 0,                   # 0-indexed zone (port_number - 1)
    "gain_range": [-80.0, 10.0],       # dB range
    "supports_mute": True
}
cached_volume_level = 50               # 0-100 scale
cached_mute_status = False
```

**Important**: Each `VirtualDevice` stores the controller's IP/port redundantly. The executor retrieves IP from **controller's `connection_config`**, not from the VirtualDevice fields.

### 1.2 Command Queue Integration

**CommandQueue Entry**:
```python
hostname = "plm-192-168-1-100"         # controller_id
command = "set_volume"                 # Command type
port = 1                               # Zone number (maps to VirtualDevice.port_number)
channel = "50"                         # Volume value (stored in channel field!)
digit = 1                              # Zone number redundantly (historical)
command_class = "interactive"          # Command priority class
status = "pending"                     # Queue status
priority = 0                           # Execution priority
routing_method = "queued"              # How it was routed
max_attempts = 3                       # Retry limit
```

**Critical Pattern**: The queue stores:
- `hostname` = controller_id (NOT an actual hostname!)
- `port` = zone/port number
- `channel` = arbitrary data field (used for volume value!)
- `digit` = redundant zone number
- `command` = string command name

### 1.3 Executor Pattern

**BoschPlenaMatrixExecutor**:
```python
class BoschPlenaMatrixExecutor(CommandExecutor):
    def __init__(self, db: Session):
        self.db = db
        self._sockets: Dict[str, socket.socket] = {}        # Cache UDP sockets per controller
        self._sequence_numbers: Dict[str, int] = {}         # Track sequence numbers

    def can_execute(self, command: Command) -> bool:
        """Determine if this executor handles the command"""
        return (
            command.device_type == "audio_zone" and
            command.protocol == "bosch_plena_matrix"
        )

    async def execute(self, command: Command) -> ExecutionResult:
        """Main execution entry point"""

        # Step 1: Lookup VirtualController by controller_id
        vc = self.db.query(VirtualController).filter(
            VirtualController.controller_id == command.controller_id
        ).first()

        # Step 2: Extract IP/port from connection_config
        connection_config = vc.connection_config or {}
        ip_address = connection_config.get("ip_address")
        port = connection_config.get("port", 12128)

        # Step 3: For zone commands, lookup VirtualDevice
        zone_number = command.parameters.get("zone_number", 1)
        vd = self.db.query(VirtualDevice).filter(
            VirtualDevice.controller_id == vc.id,
            VirtualDevice.port_number == zone_number
        ).first()

        # Step 4: Execute command via UDP
        if command.command == "set_volume":
            volume = command.parameters.get("volume", 50)
            return await self._set_volume(vc, vd, volume)
        # ... more commands

    async def _set_volume(self, controller, zone, volume):
        """Send UDP packet to device"""
        # 1. Convert volume percentage to device-specific format (dB, LUT index, etc.)
        # 2. Build protocol-specific packet (POBJ for Plena)
        # 3. Send UDP packet to IP from controller.connection_config
        # 4. Wait for response
        # 5. Read back actual value to verify
        # 6. Update zone.cached_volume_level in database
        # 7. Return ExecutionResult
```

**Key Responsibilities**:
1. **Lookup controller and zone** from database
2. **Extract IP/port** from `connection_config`
3. **Translate command** to protocol-specific format
4. **Send network request** (UDP for Plena, HTTP for Sonos)
5. **Verify result** by querying device state
6. **Update database cache** with actual values
7. **Return result** to queue processor

### 1.4 API Endpoint Pattern

**Endpoints** (`/api/audio/*`):
```python
@router.post("/zones/{zone_id}/volume")
async def set_zone_volume(zone_id: int, volume_data: VolumeControl, db: Session = Depends(get_db)):
    """Set zone volume (0-100)"""

    # Step 1: Lookup zone by database ID
    zone = db.query(VirtualDevice).get(zone_id)

    # Step 2: Lookup parent controller
    controller = db.query(VirtualController).get(zone.controller_id)

    # Step 3: Create CommandQueue entry
    queue_entry = CommandQueue(
        hostname=controller.controller_id,      # NOT an IP address!
        command="set_volume",
        port=zone.port_number,                  # Zone number
        command_class="interactive",
        status="pending",
        priority=0,
        max_attempts=3,
        routing_method="queued",
        channel=str(volume_data.volume),        # Store volume in channel field!
        digit=zone.port_number                  # Redundant zone number
    )

    db.add(queue_entry)
    db.commit()

    return {"success": True, "command_id": queue_entry.id}
```

**Important**: The API does NOT directly call the executor. It enqueues a command, and the background queue processor handles execution.

### 1.5 Discovery Pattern

**PlenaMatrixDiscoveryService**:
```python
async def discover_and_create_plena_matrix_controller(
    ip_address: str,
    controller_name: str,
    port: int = 12128,
    total_zones: int = 4,
    venue_name: Optional[str] = None,
    location: Optional[str] = None
) -> Tuple[str, int]:  # Returns (controller_id, num_devices)

    db = SessionLocal()

    # Step 1: Ping device to verify reachable
    if not await discovery.ping_device(ip_address, port):
        raise Exception("Device not responding")

    # Step 2: Query device info via protocol
    device_info = await discovery.get_device_info(ip_address, port)

    # Step 3: Query zone names from device
    sync_data = await discovery.get_sync_data(ip_address, SYNC_TYPE_SYSTEM, port)
    io_names = await discovery.parse_io_names(sync_data)
    zone_names = io_names.get("outputs", [])

    # Step 4: Create VirtualController
    controller_id = f"plm-{ip_address.replace('.', '-')}"
    connection_config = {
        "ip_address": ip_address,     # ✅ Store IP here
        "port": port,                  # ✅ Store port here
        "mac_address": device_info.get("mac_address"),
        "device_model": device_info.get("model"),
        "firmware_version": device_info.get("firmware_version"),
        "total_zones": total_zones,
        "presets": presets
    }

    controller = VirtualController(
        controller_id=controller_id,
        controller_name=controller_name,
        controller_type="audio",
        protocol="bosch_plena_matrix",
        is_online=True,
        connection_config=connection_config  # All connection details in JSON
    )
    db.add(controller)
    db.commit()

    # Step 5: Create VirtualDevice for each zone
    for zone_num in range(1, total_zones + 1):
        device = VirtualDevice(
            controller_id=controller.id,
            port_number=zone_num,
            device_name=zone_names[zone_num-1] if zone_names else f"Zone {zone_num}",
            device_type="audio_zone",
            protocol="bosch_plena_matrix",
            ip_address=ip_address,        # Redundant storage
            port=port,                     # Redundant storage
            connection_config={
                "zone_index": zone_num - 1,
                "gain_range": [-80.0, 10.0],
                "supports_mute": True
            },
            cached_volume_level=50,
            cached_mute_status=False,
            is_online=True
        )
        db.add(device)

    db.commit()

    # Return controller_id and device count
    return (controller_id, total_zones)
```

**Key Pattern**: Discovery returns `(controller_id, num_devices)` tuple to avoid SQLAlchemy session issues.

---

## 2. Sonos Integration Mapping

### 2.1 Architectural Parallels

| Aspect | Plena Matrix | Sonos |
|--------|--------------|-------|
| **Physical Device** | PLM-4P220 Amplifier | Sonos Beam/One/Play:5 |
| **Network Protocol** | UDP (ports 12128/12129) | HTTP/SOAP (port 1400) |
| **Multi-Zone Model** | 4 fixed zones (BAR, POKIES, OUTSIDE, BISTRO) | N speakers per household |
| **Controller ID** | `plm-192-168-1-100` | `sonos-192-168-1-100` |
| **Zone Representation** | VirtualDevice per zone | VirtualDevice per speaker |
| **Primary Commands** | set_volume, mute, recall_preset | set_volume, mute, play, pause |
| **State Query** | SYNC Type 102 (read volumes) | GetVolume, GetTransportInfo |
| **Cached State** | cached_volume_level, cached_mute_status | Same + cached_power_state, connection_config.current_track |
| **Connection Config** | UDP socket, sequence numbers | SoCo speaker object cache |

### 2.2 Database Schema for Sonos

**VirtualController** (One per household or per speaker - decision point below):
```python
controller_id = "sonos-192-168-1-100"   # Unique identifier
controller_name = "Living Room Sonos"   # Friendly name
controller_type = "audio"               # Type classification
protocol = "sonos_upnp"                 # Protocol identifier
is_online = True
connection_config = {
    "ip_address": "192.168.1.100",      # Primary speaker IP
    "port": 1400,                        # Always 1400 for Sonos
    "uuid": "RINCON_B8E93791AF5C01400",  # Sonos UUID
    "model": "Sonos Beam",
    "serial_number": "...",
    "household_id": "...",               # All speakers in household
    "firmware_version": "70.3-50220",
    "is_coordinator": False,             # If grouped
    "group_coordinator_uuid": "...",     # UUID of coordinator
    "group_members": [...]               # List of grouped speaker UUIDs
}
capabilities = {
    "volume": True,
    "mute": True,
    "playback": True,   # play/pause/stop
    "grouping": True,   # join/unjoin
    "queue": True       # queue management
}
```

**VirtualDevice** (One per speaker):
```python
controller_id = 1                        # FK to virtual_controllers.id
port_number = 1                          # Speaker number (1-N)
device_name = "Living Room"              # Speaker zone name from Sonos
device_type = "audio_zone"               # Device classification
protocol = "sonos_upnp"                  # Inherited from controller
ip_address = "192.168.1.100"             # Speaker's IP
port = 1400                              # Always 1400
connection_config = {
    "uuid": "RINCON_B8E93791AF5C01400",  # Sonos speaker UUID
    "model": "Sonos Beam",
    "is_visible": True,
    "is_coordinator": False,
    "group_coordinator_ip": "192.168.1.101",  # If grouped
    "music_source": "LIBRARY"            # Current source
}
cached_volume_level = 50                 # 0-100 scale
cached_mute_status = False
cached_power_state = "on"                # Always "on" for Sonos
cached_current_input = None              # Not applicable
last_status_poll = datetime.now()
status_available = True
```

**Connection Config Storage** (enhanced):
```python
connection_config = {
    # Transport state
    "transport_state": "PLAYING",        # PLAYING, PAUSED_PLAYBACK, STOPPED
    "play_mode": "NORMAL",               # NORMAL, REPEAT_ALL, SHUFFLE, etc.

    # Current track
    "current_track": {
        "title": "Song Title",
        "artist": "Artist Name",
        "album": "Album Name",
        "album_art": "http://...",
        "position": "0:02:30",
        "duration": "0:03:45",
        "uri": "x-sonos-spotify:..."
    },

    # Audio settings
    "bass": 0,                           # -10 to +10
    "treble": 0,                         # -10 to +10
    "loudness": False,

    # Last polled
    "last_polled_at": 1625097600.0
}
```

### 2.3 Command Queue Pattern for Sonos

**Example Queue Entries**:

```python
# Set Volume Command
CommandQueue(
    hostname="sonos-192-168-1-100",      # controller_id
    command="set_volume",
    port=1,                               # Speaker number (VirtualDevice.port_number)
    channel="50",                         # Volume value in channel field!
    digit=1,                              # Redundant speaker number
    command_class="interactive",
    status="pending",
    priority=0,
    max_attempts=3,
    routing_method="queued"
)

# Play Command
CommandQueue(
    hostname="sonos-192-168-1-100",
    command="play",
    port=1,
    channel=None,
    digit=1,
    command_class="interactive",
    status="pending",
    priority=0,
    max_attempts=3,
    routing_method="queued"
)

# Mute Command
CommandQueue(
    hostname="sonos-192-168-1-100",
    command="mute",
    port=1,
    channel=None,
    digit=1,
    command_class="interactive",
    status="pending",
    priority=0,
    max_attempts=3,
    routing_method="queued"
)
```

**Parameters Field** (alternative approach):
Some executors use `parameters` JSON field instead of `channel`/`digit`. We should **follow Plena Matrix pattern** and use `channel` for simplicity.

### 2.4 Executor Implementation

**SonosUPnPExecutor**:
```python
class SonosUPnPExecutor(CommandExecutor):
    """Execute commands on Sonos speakers via SoCo library"""

    def __init__(self, db: Session):
        self.db = db
        self._speakers: Dict[str, SoCo] = {}  # Cache SoCo speaker objects by device IP

    def can_execute(self, command: Command) -> bool:
        """Check if this executor can handle the command"""
        return (
            command.device_type == "audio_zone" and
            command.protocol == "sonos_upnp"
        )

    async def execute(self, command: Command) -> ExecutionResult:
        """Execute audio zone command"""

        # Step 1: Lookup VirtualController by controller_id
        vc = self.db.query(VirtualController).filter(
            VirtualController.controller_id == command.controller_id
        ).first()

        if not vc:
            return ExecutionResult(
                success=False,
                message=f"Sonos controller {command.controller_id} not found"
            )

        # Step 2: Lookup VirtualDevice (speaker) by port_number
        speaker_number = command.port  # Direct from queue.port field
        vd = self.db.query(VirtualDevice).filter(
            VirtualDevice.controller_id == vc.id,
            VirtualDevice.port_number == speaker_number
        ).first()

        if not vd:
            return ExecutionResult(
                success=False,
                message=f"Speaker {speaker_number} not found for controller {command.controller_id}"
            )

        # Step 3: Get or create SoCo speaker object
        speaker = self._get_speaker(vd)

        if not speaker:
            return ExecutionResult(
                success=False,
                message=f"Failed to connect to {vd.device_name} at {vd.ip_address}"
            )

        # Step 4: Execute command based on type
        try:
            if command.command == "set_volume":
                # Volume stored in channel field!
                volume = int(command.channel) if command.channel else 50
                return await self._set_volume(speaker, vd, volume)

            elif command.command == "volume_up":
                current = vd.cached_volume_level or 50
                new_volume = min(100, current + 5)
                return await self._set_volume(speaker, vd, new_volume)

            elif command.command == "volume_down":
                current = vd.cached_volume_level or 50
                new_volume = max(0, current - 5)
                return await self._set_volume(speaker, vd, new_volume)

            elif command.command == "mute":
                return await self._mute(speaker, vd, True)

            elif command.command == "unmute":
                return await self._mute(speaker, vd, False)

            elif command.command == "toggle_mute":
                current_mute = vd.cached_mute_status or False
                return await self._mute(speaker, vd, not current_mute)

            elif command.command == "play":
                return await self._play(speaker, vd)

            elif command.command == "pause":
                return await self._pause(speaker, vd)

            elif command.command == "stop":
                return await self._stop(speaker, vd)

            elif command.command == "next":
                return await self._next(speaker, vd)

            elif command.command == "previous":
                return await self._previous(speaker, vd)

            else:
                return ExecutionResult(
                    success=False,
                    message=f"Unknown command: {command.command}"
                )

        except SoCoUPnPException as e:
            logger.error(f"Sonos UPnP error: {e.error_code} - {e.error_description}")
            return ExecutionResult(
                success=False,
                message=f"UPnP error {e.error_code}: {e.error_description}"
            )
        except Exception as e:
            logger.error(f"Sonos command error: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                message=f"Error: {str(e)}"
            )

    def _get_speaker(self, device: VirtualDevice) -> Optional[SoCo]:
        """Get or create SoCo speaker object (cached by IP)"""

        ip_address = device.ip_address

        # Return cached speaker if exists
        if ip_address in self._speakers:
            return self._speakers[ip_address]

        try:
            # Create new SoCo object
            speaker = SoCo(ip_address)

            # Test connection by getting player name
            _ = speaker.player_name

            # Cache speaker
            self._speakers[ip_address] = speaker

            logger.info(f"✓ Connected to {device.device_name} at {ip_address}")
            return speaker

        except Exception as e:
            logger.error(f"Failed to connect to {device.device_name}: {e}")
            return None

    async def _set_volume(
        self,
        speaker: SoCo,
        zone: VirtualDevice,
        volume: int
    ) -> ExecutionResult:
        """Set volume (0-100 scale) on speaker"""

        # Validate volume range
        if volume < 0 or volume > 100:
            return ExecutionResult(
                success=False,
                message=f"Volume must be 0-100, got {volume}"
            )

        # Run in thread pool (SoCo is synchronous)
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: setattr(speaker, 'volume', volume)
        )

        # Verify by reading back (optional but recommended like Plena)
        actual_volume = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: speaker.volume
        )

        # Update cache with actual value
        zone.cached_volume_level = actual_volume
        self.db.commit()

        logger.info(f"✓ Set {zone.device_name} to {actual_volume}%")

        return ExecutionResult(
            success=True,
            message=f"Set {zone.device_name} to {actual_volume}%",
            data={"volume": actual_volume, "requested": volume}
        )

    async def _mute(
        self,
        speaker: SoCo,
        zone: VirtualDevice,
        mute: bool
    ) -> ExecutionResult:
        """Mute/unmute speaker"""

        # Set mute state
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: setattr(speaker, 'mute', mute)
        )

        # Verify by reading back
        actual_mute = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: speaker.mute
        )

        # Update cache
        zone.cached_mute_status = actual_mute
        self.db.commit()

        action = "Muted" if mute else "Unmuted"
        logger.info(f"✓ {action} {zone.device_name}")

        return ExecutionResult(
            success=True,
            message=f"{action} {zone.device_name}",
            data={"muted": actual_mute}
        )

    async def _play(self, speaker: SoCo, zone: VirtualDevice) -> ExecutionResult:
        """Start playback"""
        await asyncio.get_event_loop().run_in_executor(None, speaker.play)

        # Update cached state
        zone.connection_config = zone.connection_config or {}
        zone.connection_config["transport_state"] = "PLAYING"
        self.db.commit()

        logger.info(f"✓ Started playback on {zone.device_name}")
        return ExecutionResult(success=True, message=f"Started playback on {zone.device_name}")

    async def cleanup(self):
        """Clear speaker cache"""
        self._speakers.clear()
        logger.info("Cleared Sonos speaker cache")
```

**Key Differences from Plena Matrix**:
1. **Connection**: SoCo HTTP vs UDP sockets
2. **Synchronous Library**: SoCo is sync, requires `run_in_executor` wrapper
3. **Simpler Protocol**: No packet building, just property setters
4. **Direct Control**: No concept of LUT indices or POBJ commands

### 2.5 Discovery Service

**SonosDiscoveryService**:
```python
async def discover_and_create_sonos_controller(
    ip_address: str,
    controller_name: str,
    venue_name: Optional[str] = None,
    location: Optional[str] = None
) -> Tuple[str, int]:  # Returns (controller_id, num_speakers)
    """
    Discover a Sonos speaker and create controller + device

    NOTE: For simplicity, create ONE controller per speaker discovered.
    Grouping is handled dynamically via connection_config updates.
    """

    db = SessionLocal()

    try:
        # Step 1: Connect to speaker via SoCo
        speaker = SoCo(ip_address)

        # Step 2: Query speaker info
        speaker_info = await asyncio.get_event_loop().run_in_executor(
            None,
            speaker.get_speaker_info
        )

        player_name = speaker_info['zone_name']
        model = speaker_info['model_name']
        uuid = speaker_info['uid']
        serial = speaker_info['serial_number']
        mac = speaker_info['mac_address']
        software_version = speaker_info['software_version']
        hardware_version = speaker_info['hardware_version']

        # Step 3: Query household info
        household_id = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: speaker.deviceProperties.GetHouseholdID()['CurrentHouseholdID']
        )

        # Step 4: Query group topology
        is_coordinator = speaker.is_coordinator
        group = speaker.group
        coordinator = group.coordinator

        # Step 5: Create VirtualController
        controller_id = f"sonos-{ip_address.replace('.', '-')}"

        connection_config = {
            "ip_address": ip_address,
            "port": 1400,
            "uuid": uuid,
            "model": model,
            "serial_number": serial,
            "mac_address": mac,
            "firmware_version": software_version,
            "hardware_version": hardware_version,
            "household_id": household_id,
            "is_coordinator": is_coordinator,
            "group_coordinator_uuid": coordinator.uid if not is_coordinator else uuid,
            "discovered_at": time.time()
        }

        controller = VirtualController(
            controller_id=controller_id,
            controller_name=controller_name,
            controller_type="audio",
            protocol="sonos_upnp",
            is_online=True,
            connection_config=connection_config,
            capabilities={
                "volume": True,
                "mute": True,
                "playback": True,
                "grouping": True,
                "queue": True
            }
        )
        db.add(controller)
        db.commit()
        db.refresh(controller)

        logger.info(f"✓ Created Sonos controller: {controller_name}")

        # Step 6: Create VirtualDevice (one per speaker)
        device = VirtualDevice(
            controller_id=controller.id,
            port_number=1,                     # Always 1 for single-speaker-per-controller model
            device_name=player_name,            # "Living Room" from Sonos
            device_type="audio_zone",
            protocol="sonos_upnp",
            ip_address=ip_address,
            port=1400,
            connection_config={
                "uuid": uuid,
                "model": model,
                "is_visible": speaker.is_visible,
                "is_coordinator": is_coordinator,
                "music_source": speaker.music_source
            },
            cached_volume_level=speaker.volume,
            cached_mute_status=speaker.mute,
            cached_power_state="on",           # Sonos is always "on"
            is_online=True,
            status_available=True
        )
        db.add(device)
        db.commit()

        logger.info(f"✓ Created Sonos speaker: {player_name}")

        return (controller_id, 1)

    except Exception as e:
        logger.error(f"Failed to discover Sonos speaker: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()
```

**Design Decision: One Controller Per Speaker**

**Why?**
1. **Simplicity**: Each speaker has its own IP address
2. **Independent Control**: Users may want to manage speakers individually
3. **Flexible Grouping**: Groups change dynamically; easier to track per-speaker
4. **Consistent Pattern**: Matches Plena Matrix (one controller per amplifier)

**How Grouping Works**:
- Each VirtualDevice stores `group_coordinator_uuid` in `connection_config`
- Executor checks if speaker is grouped and routes commands accordingly
- Frontend can display grouped speakers together via UI logic

**Alternative Approach** (Not Recommended):
- One controller per household with N devices (one per speaker)
- More complex to manage; requires household discovery

### 2.6 API Endpoints

**Reuse Existing `/api/audio/*` Endpoints**:

```python
# Volume control
POST /api/audio/zones/{zone_id}/volume
{
    "volume": 50
}

# Playback control
POST /api/audio/zones/{zone_id}/playback/play
POST /api/audio/zones/{zone_id}/playback/pause
POST /api/audio/zones/{zone_id}/playback/stop
POST /api/audio/zones/{zone_id}/playback/next
POST /api/audio/zones/{zone_id}/playback/previous

# Mute control
POST /api/audio/zones/{zone_id}/mute
{
    "mute": true  # Optional
}

# Grouping (new endpoints)
POST /api/audio/zones/{zone_id}/group/join
{
    "target_zone_id": 2
}

POST /api/audio/zones/{zone_id}/group/leave

# Status query (new endpoint)
GET /api/audio/zones/{zone_id}/status
```

**New Endpoint Implementation**:
```python
@router.get("/zones/{zone_id}/status")
async def get_zone_status(zone_id: int, db: Session = Depends(get_db)):
    """Get current status of a Sonos speaker"""

    zone = db.query(VirtualDevice).get(zone_id)
    if not zone or zone.protocol != "sonos_upnp":
        raise HTTPException(status_code=404, detail="Sonos zone not found")

    # Call executor to query live status
    from ..commands.executors.audio.sonos_upnp import SonosUPnPExecutor

    executor = SonosUPnPExecutor(db)

    try:
        speaker = SoCo(zone.ip_address)

        # Query current state
        volume = speaker.volume
        mute = speaker.mute
        transport_info = speaker.get_current_transport_info()
        track_info = speaker.get_current_track_info() if transport_info['current_transport_state'] == 'PLAYING' else None

        return {
            "zone_id": zone_id,
            "zone_name": zone.device_name,
            "volume": volume,
            "muted": mute,
            "transport_state": transport_info['current_transport_state'],
            "current_track": {
                "title": track_info['title'],
                "artist": track_info['artist'],
                "album": track_info['album'],
                "position": track_info['position'],
                "duration": track_info['duration']
            } if track_info else None,
            "is_coordinator": speaker.is_coordinator,
            "group_members": [m.player_name for m in speaker.group.members]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query status: {str(e)}")
    finally:
        await executor.cleanup()
```

---

## 3. Implementation Roadmap

### Phase 1: Foundation (Week 1)
- [x] Create comprehensive Sonos documentation
- [ ] Install SoCo library: `pip install soco`
- [ ] Create `backend/app/services/sonos_discovery.py`
- [ ] Implement SSDP discovery (optional; can manually adopt via IP)
- [ ] Create `discover_and_create_sonos_controller()` function
- [ ] Test discovery with one Sonos speaker

### Phase 2: Executor (Week 2)
- [ ] Create `backend/app/commands/executors/audio/sonos_upnp.py`
- [ ] Implement `SonosUPnPExecutor` class
- [ ] Implement `can_execute()` method
- [ ] Implement `execute()` method with command routing
- [ ] Implement `_set_volume()`, `_mute()`, `_toggle_mute()`
- [ ] Test volume control via direct executor calls

### Phase 3: Queue Integration (Week 2)
- [ ] Register `SonosUPnPExecutor` in executor registry
- [ ] Test command queue integration
- [ ] Verify commands execute from queue
- [ ] Test retry logic on failures
- [ ] Add command history logging

### Phase 4: API Endpoints (Week 3)
- [ ] Update `/api/audio/controllers/discover` to support `protocol="sonos_upnp"`
- [ ] Test discovery endpoint with Sonos speaker
- [ ] Verify volume control endpoints work
- [ ] Verify mute control endpoints work
- [ ] Test from frontend UI

### Phase 5: Playback Control (Week 3)
- [ ] Implement `_play()`, `_pause()`, `_stop()` in executor
- [ ] Implement `_next()`, `_previous()` in executor
- [ ] Add playback control API endpoints (optional if reusing `/audio/zones/{id}/*`)
- [ ] Test playback commands from UI

### Phase 6: Status Monitoring (Week 4)
- [ ] Implement status polling service
- [ ] Update `cached_volume_level`, `cached_mute_status` every 15-30 seconds
- [ ] Store current track info in `connection_config`
- [ ] Add `/api/audio/zones/{zone_id}/status` endpoint
- [ ] Display current track in frontend

### Phase 7: Advanced Features (Week 5+)
- [ ] Implement speaker grouping commands
- [ ] Add group management API endpoints
- [ ] Implement queue management (optional)
- [ ] Add bass/treble/EQ controls (optional)
- [ ] UPnP event subscriptions for real-time updates (optional)

---

## 4. Critical Implementation Notes

### 4.1 Connection Config Pattern

**✅ DO THIS** (Like Plena Matrix):
```python
# Store IP/port in connection_config
controller.connection_config = {
    "ip_address": "192.168.1.100",
    "port": 1400,
    # ... other fields
}

# Retrieve in executor
connection_config = controller.connection_config or {}
ip_address = connection_config.get("ip_address")
```

**❌ DON'T DO THIS**:
```python
# Don't use controller.ip_address directly
ip_address = controller.ip_address  # May be empty!
```

### 4.2 Command Queue Field Usage

**✅ DO THIS** (Like Plena Matrix):
```python
# Store volume in channel field
queue_entry = CommandQueue(
    hostname=controller.controller_id,  # NOT an IP!
    command="set_volume",
    port=zone.port_number,              # Zone/speaker number
    channel=str(volume_data.volume),    # Volume value here
    digit=zone.port_number              # Redundant
)
```

**Why `channel` field?** Historical reasons. The queue schema predates parameter JSON fields. Plena Matrix uses `channel` for volume, so we should too for consistency.

### 4.3 Async Wrapper for SoCo

**✅ DO THIS**:
```python
# SoCo is synchronous - wrap in executor
volume = await asyncio.get_event_loop().run_in_executor(
    None,
    lambda: speaker.volume
)
```

**❌ DON'T DO THIS**:
```python
# Don't call synchronous methods directly in async functions
volume = speaker.volume  # Blocks event loop!
```

### 4.4 Cache Verification Pattern

**✅ DO THIS** (Like Plena Matrix):
```python
# Set value
speaker.volume = 50

# Read back to verify
actual_volume = speaker.volume

# Update cache with actual value
zone.cached_volume_level = actual_volume
self.db.commit()
```

**Why?** Device may not accept exact value requested (rounding, limits, etc.). Always verify.

### 4.5 Error Handling

**✅ DO THIS**:
```python
try:
    speaker.play()
except SoCoUPnPException as e:
    # Specific Sonos errors
    return ExecutionResult(
        success=False,
        message=f"UPnP error {e.error_code}: {e.error_description}"
    )
except Exception as e:
    # Generic errors
    return ExecutionResult(
        success=False,
        message=f"Error: {str(e)}"
    )
```

### 4.6 Speaker Cache Management

**✅ DO THIS**:
```python
# Cache SoCo objects by IP address
self._speakers: Dict[str, SoCo] = {}

def _get_speaker(self, device: VirtualDevice) -> Optional[SoCo]:
    ip = device.ip_address
    if ip not in self._speakers:
        self._speakers[ip] = SoCo(ip)
    return self._speakers[ip]

async def cleanup(self):
    self._speakers.clear()
```

**Why?** SoCo objects are lightweight but connection setup has overhead. Cache for performance.

---

## 5. Testing Strategy

### 5.1 Unit Tests
```python
async def test_sonos_executor_can_execute():
    executor = SonosUPnPExecutor(db)

    command = Command(
        controller_id="sonos-test",
        device_type="audio_zone",
        protocol="sonos_upnp",
        command="set_volume"
    )

    assert executor.can_execute(command) == True

async def test_sonos_set_volume():
    executor = SonosUPnPExecutor(db)

    # Mock SoCo speaker
    mock_speaker = MagicMock()
    mock_speaker.volume = 50

    result = await executor._set_volume(mock_speaker, mock_zone, 75)

    assert result.success == True
    assert mock_speaker.volume == 75
```

### 5.2 Integration Tests
```python
async def test_sonos_discovery_flow():
    # Discover speaker
    controller_id, num_speakers = await discover_and_create_sonos_controller(
        ip_address="192.168.1.100",
        controller_name="Test Sonos"
    )

    assert controller_id == "sonos-192-168-1-100"
    assert num_speakers == 1

    # Verify controller created
    controller = db.query(VirtualController).filter_by(controller_id=controller_id).first()
    assert controller is not None
    assert controller.protocol == "sonos_upnp"

    # Verify device created
    devices = controller.virtual_devices
    assert len(devices) == 1
    assert devices[0].device_type == "audio_zone"
```

### 5.3 Manual Testing
1. Discover Sonos speaker via API
2. Set volume to 50% via API
3. Verify volume changed on physical speaker
4. Press play button via API
5. Verify audio starts playing
6. Check database cache updated correctly

---

## 6. Conclusion

The Bosch Plena Matrix integration provides a **perfect architectural blueprint** for Sonos:

1. **Virtual Controller Model** - One controller per speaker (or per household)
2. **Command Queue Integration** - All commands go through queue with retry logic
3. **Protocol Executor** - SonosUPnPExecutor handles HTTP/SOAP via SoCo library
4. **Connection Config Storage** - IP/port stored in JSON, not table columns
5. **Cache-and-Verify Pattern** - Update database cache after successful commands
6. **Async Wrapper Pattern** - Wrap synchronous SoCo calls in `run_in_executor`
7. **Discovery Service** - Query device info and create controller + devices

**Key Differences**:
- HTTP/SOAP instead of UDP
- SoCo library (sync) instead of raw sockets (async)
- More features (playback, grouping) beyond volume/mute

**Recommended Approach**:
- Start with Phase 1-3 (volume control only)
- Verify command queue integration works
- Add playback control in Phase 5
- Add status monitoring in Phase 6
- Leave grouping/advanced features for later

**Estimated Timeline**: 4-6 weeks for full implementation

The existing Plena Matrix code can serve as a **direct template** - many patterns can be copy-pasted and adapted with minimal changes.
