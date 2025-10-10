# Network Amplifier Control Implementation Guide

## Executive Summary

This document outlines the implementation strategy for integrating network-connected audio amplifiers into the TapCommand device management system, following the same architectural patterns established for network TV control.

**Primary Focus**: Bosch Praesensa and PLENA matrix systems
**Secondary Targets**: AUDAC, Powersoft, Sonos, Crown amplifiers
**Implementation Timeline**: Phased approach with Bosch as Phase 1

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Supported Amplifier Brands & Protocols](#supported-amplifier-brands--protocols)
3. [Database Schema](#database-schema)
4. [Backend Implementation](#backend-implementation)
5. [Frontend Implementation](#frontend-implementation)
6. [Protocol-Specific Implementations](#protocol-specific-implementations)
7. [Testing Strategy](#testing-strategy)
8. [Implementation Phases](#implementation-phases)

---

## Architecture Overview

### High-Level Design

Network amplifiers will integrate into the existing TapCommand architecture using the same patterns as network TV control:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │         /audio - Audio Systems Control Page              │   │
│  │  - Amplifier discovery and adoption                      │   │
│  │  - Volume control, mute, input selection                 │   │
│  │  - Zone management (multi-zone amplifiers)               │   │
│  │  - Preset management                                     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↕ REST API
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Unified Command Queue                        │   │
│  │  - Queue all audio commands (volume, mute, etc.)         │   │
│  │  - Protocol router selects appropriate executor          │   │
│  │  - Retry logic and error handling                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           Protocol Executors                              │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌──────────────┐       │   │
│  │  │   Bosch     │ │   AUDAC     │ │    Sonos     │       │   │
│  │  │  Praesensa  │ │   Dante     │ │   HTTP API   │       │   │
│  │  │  OMNEO/AES70│ │   Control   │ │              │       │   │
│  │  └─────────────┘ └─────────────┘ └──────────────┘       │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌──────────────┐       │   │
│  │  │  Powersoft  │ │    Crown    │ │   Generic    │       │   │
│  │  │  Armonía    │ │   HiQnet    │ │   REST API   │       │   │
│  │  └─────────────┘ └─────────────┘ └──────────────┘       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │         Amplifier Status Polling Service                  │   │
│  │  - Poll amplifier state (volume, mute, input, zones)     │   │
│  │  - Update cached status in database                      │   │
│  │  - Detect offline/online status                          │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                    Network Amplifiers                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │    Bosch     │  │    AUDAC     │  │    Sonos     │          │
│  │  Praesensa   │  │   Consenso   │  │     Amp      │          │
│  │192.168.x.x   │  │192.168.x.x   │  │192.168.x.x   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Reuse Existing Infrastructure**: Leverage Virtual Controllers model, command queue, and protocol router
2. **Unified Interface**: Same control paradigm as TVs (controllers → devices → commands)
3. **Protocol Abstraction**: Hide protocol complexity behind executor interface
4. **Scalability**: Support multiple brands/protocols through plugin architecture
5. **Status Tracking**: Real-time polling and caching of amplifier state

---

## Supported Amplifier Brands & Protocols

### Phase 1: Bosch Praesensa (Primary Focus)

**Protocol**: OMNEO with AES70 (OCA - Open Control Architecture)
**Communication**: TCP/IP over Ethernet
**Discovery**: OMNEO device discovery / manual IP configuration
**Control Capabilities**:
- System power control
- Volume adjustment (per zone/channel)
- Mute control (per zone/channel)
- Input source selection
- Zone routing and configuration
- Preset recall
- Audio routing between devices
- Fault monitoring

**Authentication**: SHA-256 hashed passwords via Open Interface API
**Encryption**: 128-bit AES, HMAC-SHA-1
**Audio Transport**: Dante (AES67 compatible)

**Technical Details**:
- **System Controller**: PRA-SCL (large) or PRA-SCS (small)
- **Network**: Supports multiple subnets, dynamic audio channel assignment
- **API**: Open Interface for third-party integration
- **Monitoring**: Device health, fault detection, battery backup status

**Implementation Approach**:
- Use AES70 (OCA) protocol library or REST API if available
- May require custom protocol implementation based on Bosch documentation
- Control via System Controller (not individual amplifiers directly)

### Phase 2: Additional Brands

#### AUDAC Consenso (Dante-based)
**Protocol**: Dante control protocol + HTTP/REST
**Features**: Multi-zone, DSP, matrix routing
**Difficulty**: ⭐⭐⭐ Medium

#### Sonos
**Protocol**: HTTP REST API (well-documented)
**Features**: Multi-room audio, streaming services
**Difficulty**: ⭐ Easy (existing Python libraries)

#### Powersoft
**Protocol**: Armonía Plus software API, likely REST/HTTP
**Features**: Professional amplification, DSP, Dante
**Difficulty**: ⭐⭐⭐ Medium

#### Crown/BSS (Harman)
**Protocol**: HiQnet protocol
**Features**: Commercial audio, BLU link, CobraNet
**Difficulty**: ⭐⭐⭐⭐ Hard (proprietary protocol)

---

## Database Schema

### New Tables

#### `audio_controllers`
```sql
CREATE TABLE audio_controllers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    controller_id VARCHAR(50) UNIQUE NOT NULL,  -- e.g., 'amp-bosch-001'
    controller_name VARCHAR(255) NOT NULL,
    controller_type VARCHAR(50) NOT NULL,        -- 'bosch_praesensa', 'audac', 'sonos'
    manufacturer VARCHAR(100),
    model VARCHAR(100),

    -- Network
    primary_ip_address VARCHAR(45),              -- Primary controller IP
    mac_address VARCHAR(17),
    subnet VARCHAR(45),

    -- Authentication
    auth_method VARCHAR(50),                      -- 'password', 'api_key', 'none'
    credentials JSON,                             -- Encrypted credentials

    -- Configuration
    zone_count INTEGER DEFAULT 1,
    channel_count INTEGER,
    max_volume INTEGER DEFAULT 100,
    supports_presets BOOLEAN DEFAULT FALSE,
    supports_routing BOOLEAN DEFAULT FALSE,

    -- Status
    is_online BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    last_seen TIMESTAMP,
    firmware_version VARCHAR(50),

    -- Metadata
    location VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `audio_devices`
```sql
CREATE TABLE audio_devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    controller_id INTEGER NOT NULL,              -- FK to audio_controllers
    device_id VARCHAR(50) UNIQUE NOT NULL,       -- e.g., 'amp-bosch-001-zone1'

    -- Device Info
    device_name VARCHAR(255) NOT NULL,           -- 'Main Hall Left'
    device_type VARCHAR(50) NOT NULL,            -- 'zone', 'channel', 'output'
    zone_number INTEGER,                          -- For multi-zone amps
    channel_number INTEGER,                       -- For multi-channel

    -- Physical Connection
    ip_address VARCHAR(45),                       -- If device has own IP (rare)
    physical_output VARCHAR(50),                  -- 'Speaker A', 'Line Out 1'

    -- Configuration
    min_volume INTEGER DEFAULT 0,
    max_volume INTEGER DEFAULT 100,
    default_volume INTEGER DEFAULT 50,
    default_input VARCHAR(50),
    available_inputs JSON,                        -- ['aux', 'mic1', 'dante1']

    -- Cached Status (updated by polling service)
    cached_power_state VARCHAR(20),               -- 'on', 'off', 'standby'
    cached_volume_level INTEGER,
    cached_mute_status BOOLEAN,
    cached_current_input VARCHAR(50),
    cached_preset_id VARCHAR(50),

    -- Polling
    status_available BOOLEAN DEFAULT TRUE,
    last_status_poll TIMESTAMP,
    status_poll_failures INTEGER DEFAULT 0,

    -- Audio Routing (for matrix systems)
    routing_config JSON,                          -- Matrix routing configuration

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    location VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (controller_id) REFERENCES audio_controllers(id) ON DELETE CASCADE
);
```

#### `audio_presets`
```sql
CREATE TABLE audio_presets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    controller_id INTEGER NOT NULL,
    preset_id VARCHAR(50) NOT NULL,
    preset_name VARCHAR(255) NOT NULL,

    -- Preset Configuration
    preset_data JSON NOT NULL,                    -- Full preset configuration

    -- Scope
    applies_to VARCHAR(50),                       -- 'controller', 'zone', 'channel'
    device_id INTEGER,                            -- FK to audio_devices if zone/channel specific

    -- Metadata
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (controller_id) REFERENCES audio_controllers(id) ON DELETE CASCADE,
    FOREIGN KEY (device_id) REFERENCES audio_devices(id) ON DELETE CASCADE
);
```

### Extensions to Existing Tables

#### `command_queue`
```sql
-- Add support for audio commands (already flexible enough, just document usage)
-- Examples:
-- command='set_volume', parameters={'volume': 75, 'zone': 1}
-- command='mute', parameters={'zone': 1}
-- command='select_input', parameters={'input': 'aux1', 'zone': 1}
-- command='recall_preset', parameters={'preset_id': 'meeting_mode'}
```

---

## Backend Implementation

### Directory Structure

```
backend/
├── app/
│   ├── commands/
│   │   ├── executors/
│   │   │   ├── audio/                    # NEW
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   ├── bosch_praesensa.py   # Bosch implementation
│   │   │   │   ├── audac_dante.py
│   │   │   │   ├── sonos.py
│   │   │   │   ├── powersoft.py
│   │   │   │   └── generic_rest.py
│   │   │   ├── network/                  # Existing TV executors
│   │   │   └── ir_executor.py
│   │   └── router.py                     # UPDATE: Add audio routing
│   ├── models/
│   │   ├── audio_controller.py           # NEW
│   │   └── audio_device.py               # NEW
│   ├── routers/
│   │   ├── audio_controllers.py          # NEW: Controller management
│   │   ├── audio_devices.py              # NEW: Device/zone control
│   │   └── audio_discovery.py            # NEW: Network discovery
│   ├── services/
│   │   ├── audio_status_poller.py        # NEW: Poll amplifier status
│   │   └── audio_discovery.py            # NEW: Discover amplifiers
│   └── main.py                            # UPDATE: Register new routers
└── docs/
    └── NETWORK_AMPLIFIER_IMPLEMENTATION_GUIDE.md  # This document
```

### Core Components

#### 1. Audio Controller Model (`models/audio_controller.py`)

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.orm import relationship
from ..db.database import Base
from datetime import datetime

class AudioController(Base):
    __tablename__ = "audio_controllers"

    id = Column(Integer, primary_key=True, index=True)
    controller_id = Column(String(50), unique=True, nullable=False, index=True)
    controller_name = Column(String(255), nullable=False)
    controller_type = Column(String(50), nullable=False)  # 'bosch_praesensa', etc.
    manufacturer = Column(String(100))
    model = Column(String(100))

    # Network
    primary_ip_address = Column(String(45))
    mac_address = Column(String(17))
    subnet = Column(String(45))

    # Authentication
    auth_method = Column(String(50))
    credentials = Column(JSON)  # Encrypted

    # Configuration
    zone_count = Column(Integer, default=1)
    channel_count = Column(Integer)
    max_volume = Column(Integer, default=100)
    supports_presets = Column(Boolean, default=False)
    supports_routing = Column(Boolean, default=False)

    # Status
    is_online = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime)
    firmware_version = Column(String(50))

    # Metadata
    location = Column(String(255))
    notes = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    devices = relationship("AudioDevice", back_populates="controller", cascade="all, delete-orphan")
    presets = relationship("AudioPreset", back_populates="controller", cascade="all, delete-orphan")
```

#### 2. Audio Executor Base Class (`commands/executors/audio/base.py`)

```python
from abc import ABC, abstractmethod
from typing import Optional
from sqlalchemy.orm import Session
from ...models import Command, ExecutionResult

class AudioExecutor(ABC):
    """
    Base class for audio amplifier command executors
    """

    def __init__(self, db: Session):
        self.db = db

    @abstractmethod
    async def execute(self, command: Command) -> ExecutionResult:
        """Execute audio command"""
        pass

    @abstractmethod
    async def get_status(self, controller_id: str) -> dict:
        """Get current amplifier status"""
        pass

    @abstractmethod
    def can_execute(self, command: Command) -> bool:
        """Check if this executor can handle the command"""
        pass

    # Common helper methods
    def normalize_volume(self, volume: int, max_vol: int = 100) -> int:
        """Normalize volume to 0-100 range"""
        return max(0, min(100, int((volume / max_vol) * 100)))

    def denormalize_volume(self, volume: int, max_vol: int = 100) -> int:
        """Convert 0-100 volume to device range"""
        return int((volume / 100) * max_vol)
```

#### 3. Bosch Praesensa Executor (`commands/executors/audio/bosch_praesensa.py`)

```python
"""
Bosch Praesensa Amplifier Executor

Protocol: OMNEO with AES70 (OCA - Open Control Architecture)
Communication: TCP/IP over Ethernet via System Controller
"""

import asyncio
import hashlib
import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from .base import AudioExecutor
from ...models import Command, ExecutionResult
from ....models.audio_controller import AudioController, AudioDevice

class BoschPraesensaExecutor(AudioExecutor):
    """
    Executor for Bosch Praesensa PA/VA systems

    Features:
    - Multi-zone volume control
    - Input routing
    - Preset recall
    - Fault monitoring
    - Battery backup status

    Requirements:
    - Access to System Controller (PRA-SCL/PRA-SCS)
    - Open Interface API credentials
    - Network connectivity to controller
    """

    DEFAULT_PORT = 9010  # Bosch Open Interface API port (TBD - needs verification)

    # Command mapping
    COMMAND_MAP = {
        "set_volume": "volume",
        "mute": "mute",
        "unmute": "unmute",
        "select_input": "input",
        "recall_preset": "preset",
        "power_on": "power_on",
        "power_off": "power_off"
    }

    def __init__(self, db: Session):
        super().__init__(db)
        self._sessions = {}  # Cache connections per controller

    async def execute(self, command: Command) -> ExecutionResult:
        """Execute command on Bosch Praesensa system"""
        try:
            # Get controller
            controller = self.db.query(AudioController).filter(
                AudioController.controller_id == command.controller_id
            ).first()

            if not controller:
                return ExecutionResult(
                    success=False,
                    message=f"Audio controller {command.controller_id} not found",
                    error="CONTROLLER_NOT_FOUND"
                )

            # Route to appropriate handler
            if command.command == "set_volume":
                return await self._set_volume(controller, command)
            elif command.command in ["mute", "unmute"]:
                return await self._set_mute(controller, command)
            elif command.command == "select_input":
                return await self._select_input(controller, command)
            elif command.command == "recall_preset":
                return await self._recall_preset(controller, command)
            else:
                return ExecutionResult(
                    success=False,
                    message=f"Unsupported command: {command.command}",
                    error="UNSUPPORTED_COMMAND"
                )

        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Bosch Praesensa command failed: {str(e)}",
                error=str(e)
            )

    async def _set_volume(
        self,
        controller: AudioController,
        command: Command
    ) -> ExecutionResult:
        """Set volume for specified zone/channel"""
        try:
            volume = command.parameters.get("volume")
            zone = command.parameters.get("zone", 1)

            if volume is None:
                raise ValueError("Volume parameter required")

            # Authenticate and connect
            session = await self._get_session(controller)

            # Send volume command via AES70/OCA
            # This is a placeholder - actual implementation depends on Bosch API
            response = await self._send_command(
                session,
                {
                    "method": "setVolume",
                    "params": {
                        "zone": zone,
                        "volume": volume
                    }
                }
            )

            return ExecutionResult(
                success=True,
                message=f"Volume set to {volume} for zone {zone}",
                data={"volume": volume, "zone": zone}
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Failed to set volume: {str(e)}",
                error=str(e)
            )

    async def _set_mute(
        self,
        controller: AudioController,
        command: Command
    ) -> ExecutionResult:
        """Mute/unmute specified zone"""
        mute = command.command == "mute"
        zone = command.parameters.get("zone", 1)

        # Implementation placeholder
        return ExecutionResult(
            success=True,
            message=f"Zone {zone} {'muted' if mute else 'unmuted'}",
            data={"muted": mute, "zone": zone}
        )

    async def _select_input(
        self,
        controller: AudioController,
        command: Command
    ) -> ExecutionResult:
        """Select input source for zone"""
        input_id = command.parameters.get("input")
        zone = command.parameters.get("zone", 1)

        # Implementation placeholder
        return ExecutionResult(
            success=True,
            message=f"Input {input_id} selected for zone {zone}",
            data={"input": input_id, "zone": zone}
        )

    async def _recall_preset(
        self,
        controller: AudioController,
        command: Command
    ) -> ExecutionResult:
        """Recall stored preset"""
        preset_id = command.parameters.get("preset_id")

        # Implementation placeholder
        return ExecutionResult(
            success=True,
            message=f"Preset {preset_id} recalled",
            data={"preset_id": preset_id}
        )

    async def _get_session(self, controller: AudioController):
        """Get or create authenticated session"""
        if controller.controller_id not in self._sessions:
            # Create new session
            # Authenticate using SHA-256 hashed password
            credentials = controller.credentials or {}
            username = credentials.get("username", "admin")
            password = credentials.get("password", "")

            # Hash password with SHA-256
            password_hash = hashlib.sha256(password.encode()).hexdigest()

            # Connect to System Controller
            # This is placeholder - actual implementation depends on Bosch API
            session = {
                "host": controller.primary_ip_address,
                "port": self.DEFAULT_PORT,
                "auth": {"username": username, "password_hash": password_hash}
            }

            self._sessions[controller.controller_id] = session

        return self._sessions[controller.controller_id]

    async def _send_command(self, session: dict, command: dict) -> dict:
        """Send command to Bosch system controller"""
        # This is a placeholder implementation
        # Actual implementation would use AES70/OCA protocol or REST API

        # For now, simulate successful response
        return {"status": "success", "result": command}

    async def get_status(self, controller_id: str) -> dict:
        """Get current status of Bosch Praesensa system"""
        controller = self.db.query(AudioController).filter(
            AudioController.controller_id == controller_id
        ).first()

        if not controller:
            return None

        # Query system controller for status
        # Placeholder implementation
        return {
            "power": "on",
            "zones": [
                {
                    "zone": 1,
                    "volume": 50,
                    "muted": False,
                    "input": "mic1"
                }
            ],
            "faults": [],
            "battery_status": "ok"
        }

    def can_execute(self, command: Command) -> bool:
        """Check if command is supported"""
        return command.command in self.COMMAND_MAP
```

#### 4. Protocol Router Update (`commands/router.py`)

```python
# Add to existing ProtocolRouter class

def get_executor(self, command: Command) -> Optional[CommandExecutor]:
    """Get the appropriate executor for a command"""

    # ... existing TV and IR routing ...

    # Audio Controllers
    if command.device_type == "audio":
        if command.protocol == "bosch_praesensa":
            from .executors.audio import BoschPraesensaExecutor
            return BoschPraesensaExecutor(self.db)

        elif command.protocol == "audac_dante":
            from .executors.audio import AudacDanteExecutor
            return AudacDanteExecutor(self.db)

        elif command.protocol == "sonos":
            from .executors.audio import SonosExecutor
            return SonosExecutor(self.db)

        elif command.protocol == "generic_rest":
            from .executors.audio import GenericRestExecutor
            return GenericRestExecutor(self.db)

    return None
```

#### 5. Audio Status Poller (`services/audio_status_poller.py`)

```python
"""
Audio Amplifier Status Polling Service

Polls network amplifiers for current status and caches in database
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from ..db.database import SessionLocal
from ..models.audio_controller import AudioController, AudioDevice

logger = logging.getLogger(__name__)


class AudioStatusPoller:
    """
    Background service to poll audio amplifiers for status

    Polling intervals:
    - Tier 1 (5s): Bosch Praesensa, AUDAC, Sonos
    - Tier 2 (10s): Generic REST APIs
    """

    def __init__(self):
        self.running = False
        self.poll_interval = 5  # seconds

    async def start(self):
        """Start polling service"""
        if self.running:
            logger.warning("Audio status poller already running")
            return

        self.running = True
        logger.info("🔊 Starting audio amplifier status polling service")

        asyncio.create_task(self._polling_loop())

    async def stop(self):
        """Stop polling service"""
        self.running = False
        logger.info("⏹️  Stopping audio status polling service")

    async def _polling_loop(self):
        """Main polling loop"""
        while self.running:
            try:
                db = SessionLocal()

                try:
                    # Get all active controllers
                    controllers = db.query(AudioController).filter(
                        AudioController.is_active == True
                    ).all()

                    logger.debug(f"Polling {len(controllers)} audio controllers")

                    # Poll each controller
                    for controller in controllers:
                        await self._poll_controller(controller, db)

                finally:
                    db.close()

            except Exception as e:
                logger.error(f"Error in audio polling loop: {e}")

            await asyncio.sleep(self.poll_interval)

    async def _poll_controller(
        self,
        controller: AudioController,
        db: Session
    ):
        """Poll a single controller for status"""
        try:
            # Get executor for this controller type
            from ..commands.router import ProtocolRouter
            from ..commands.models import Command

            # Create dummy command to get executor
            dummy_cmd = Command(
                controller_id=controller.controller_id,
                command="get_status",
                device_type="audio",
                protocol=controller.controller_type
            )

            router = ProtocolRouter(db)
            executor = router.get_executor(dummy_cmd)

            if not executor:
                logger.warning(
                    f"No executor for {controller.controller_type}"
                )
                return

            # Get status
            status = await executor.get_status(controller.controller_id)

            if status:
                # Update controller online status
                controller.is_online = True
                controller.last_seen = datetime.now()

                # Update device caches
                self._update_device_caches(controller, status, db)

                db.commit()
            else:
                # Mark offline after failures
                controller.is_online = False
                db.commit()

        except Exception as e:
            logger.error(f"Error polling {controller.controller_name}: {e}")

    def _update_device_caches(
        self,
        controller: AudioController,
        status: Dict[str, Any],
        db: Session
    ):
        """Update cached status for all devices/zones"""
        zones = status.get("zones", [])

        for zone_status in zones:
            zone_num = zone_status.get("zone")

            device = db.query(AudioDevice).filter(
                AudioDevice.controller_id == controller.id,
                AudioDevice.zone_number == zone_num
            ).first()

            if device:
                device.cached_power_state = "on"
                device.cached_volume_level = zone_status.get("volume")
                device.cached_mute_status = zone_status.get("muted")
                device.cached_current_input = zone_status.get("input")
                device.last_status_poll = datetime.now()
                device.status_poll_failures = 0


# Global poller instance
audio_status_poller = AudioStatusPoller()
```

---

## Frontend Implementation

### Page Structure: `/audio`

```
/audio
├── Audio Systems Dashboard
│   ├── Controllers Overview
│   │   ├── Controller cards (similar to TV controllers)
│   │   └── Quick actions (mute all, preset recall)
│   ├── Zone/Device Control
│   │   ├── Volume sliders per zone
│   │   ├── Mute toggles
│   │   ├── Input selectors
│   │   └── Real-time status display
│   └── Preset Management
│       ├── Preset list
│       ├── Recall buttons
│       └── Create/edit presets
└── Audio Discovery
    ├── Scan for amplifiers
    ├── Adopt discovered amplifiers
    └── Manual configuration
```

### Component Hierarchy

```
AudioSystemsPage
├── AudioControllersOverview
│   └── AudioControllerCard (for each controller)
│       ├── ControllerStatus
│       └── QuickActions
├── ZoneControl
│   └── ZoneControlPanel (for each zone/device)
│       ├── VolumeSlider
│       ├── MuteToggle
│       ├── InputSelector
│       └── StatusIndicators
└── PresetManager
    ├── PresetList
    └── PresetButton (for each preset)
```

### Key Components

#### AudioControllerCard
- Display controller name, type, status
- Show overall system health
- Quick mute all / unmute all
- Link to detailed view

#### ZoneControlPanel
- Real-time volume slider (0-100)
- Mute button with visual indicator
- Input source dropdown
- Current status display
- Optional: EQ controls (future)

#### PresetManager
- List of available presets
- One-click preset recall
- Visual feedback on active preset
- Create/edit/delete presets

### API Integration

```typescript
// Frontend API client
export const audioApi = {
  // Controllers
  getControllers: () => api.get('/audio/controllers'),
  getController: (id: string) => api.get(`/audio/controllers/${id}`),

  // Devices/Zones
  getDevices: (controllerId: string) =>
    api.get(`/audio/controllers/${controllerId}/devices`),

  // Commands
  setVolume: (deviceId: string, volume: number) =>
    api.post('/commands/audio/volume', { device_id: deviceId, volume }),

  setMute: (deviceId: string, muted: boolean) =>
    api.post('/commands/audio/mute', { device_id: deviceId, muted }),

  selectInput: (deviceId: string, input: string) =>
    api.post('/commands/audio/input', { device_id: deviceId, input }),

  recallPreset: (controllerId: string, presetId: string) =>
    api.post('/commands/audio/preset', { controller_id: controllerId, preset_id: presetId }),

  // Presets
  getPresets: (controllerId: string) =>
    api.get(`/audio/controllers/${controllerId}/presets`),

  createPreset: (controllerId: string, preset: Preset) =>
    api.post(`/audio/controllers/${controllerId}/presets`, preset),
};
```

---

## Protocol-Specific Implementations

### Bosch Praesensa Deep Dive

#### Authentication Flow

```
1. Connect to System Controller IP (port 9010 - TBD)
2. Send authentication request with SHA-256 hashed password
3. Receive session token (if using REST) or establish persistent connection (if TCP)
4. Include auth token/credentials in subsequent requests
5. Maintain connection or re-authenticate as needed
```

#### Command Examples (Conceptual)

**Set Volume:**
```json
{
  "method": "setVolume",
  "params": {
    "zone": 1,
    "volume": 75
  },
  "id": 1
}
```

**Mute Zone:**
```json
{
  "method": "setMute",
  "params": {
    "zone": 1,
    "muted": true
  },
  "id": 2
}
```

**Get System Status:**
```json
{
  "method": "getSystemStatus",
  "params": {},
  "id": 3
}
```

**Response:**
```json
{
  "result": {
    "zones": [
      {
        "id": 1,
        "name": "Main Hall",
        "volume": 75,
        "muted": false,
        "input": "microphone_1",
        "active": true
      }
    ],
    "faults": [],
    "battery": {
      "status": "ok",
      "voltage": 27.5
    }
  },
  "id": 3
}
```

#### Required Research

**Critical Questions for Bosch Implementation:**

1. **API Documentation**:
   - Where to get official Open Interface API documentation?
   - Is it REST-based or custom TCP protocol?
   - What is the actual API port?

2. **Protocol Details**:
   - Is AES70/OCA the control protocol or just audio transport?
   - Does Bosch provide Python SDK or must we implement from scratch?

3. **Authentication**:
   - Exact authentication flow and token management
   - Certificate requirements for AES encryption

4. **Discovery**:
   - How to discover Praesensa system controllers on network?
   - OMNEO discovery mechanism?

5. **Testing**:
   - Can we get access to a demo/test system?
   - Simulator or emulator available?

**Next Steps:**
- Contact Bosch technical support for API documentation
- Request developer access/credentials
- Obtain installation manual with network protocol details

---

## Testing Strategy

### Unit Tests

```python
# tests/test_bosch_executor.py

async def test_bosch_set_volume():
    """Test Bosch Praesensa volume control"""
    executor = BoschPraesensaExecutor(db)

    command = Command(
        controller_id="amp-bosch-001",
        command="set_volume",
        device_type="audio",
        protocol="bosch_praesensa",
        parameters={"volume": 75, "zone": 1}
    )

    result = await executor.execute(command)

    assert result.success
    assert result.data["volume"] == 75
    assert result.data["zone"] == 1

async def test_bosch_mute():
    """Test Bosch Praesensa mute control"""
    executor = BoschPraesensaExecutor(db)

    command = Command(
        controller_id="amp-bosch-001",
        command="mute",
        device_type="audio",
        protocol="bosch_praesensa",
        parameters={"zone": 1}
    )

    result = await executor.execute(command)

    assert result.success
    assert result.data["muted"] == True
```

### Integration Tests

```python
async def test_audio_command_queue_flow():
    """Test complete flow: queue → executor → status update"""

    # 1. Queue command
    cmd_id = await CommandQueueService.enqueue(
        db=db,
        hostname="amp-bosch-001",
        command="set_volume",
        port=1,  # zone
        channel=None,
        command_class="immediate",
        parameters={"volume": 80}
    )

    # 2. Wait for processing
    await asyncio.sleep(2)

    # 3. Verify command completed
    cmd = db.query(CommandQueue).get(cmd_id)
    assert cmd.status == "completed"

    # 4. Verify cached status updated
    device = db.query(AudioDevice).filter(
        AudioDevice.device_id == "amp-bosch-001-zone1"
    ).first()

    assert device.cached_volume_level == 80
```

### Manual Testing Checklist

- [ ] Discover Bosch Praesensa on network
- [ ] Adopt controller and configure zones
- [ ] Set volume via API - verify on physical amp
- [ ] Mute/unmute - verify on physical amp
- [ ] Select different inputs - verify routing
- [ ] Recall preset - verify all settings apply
- [ ] Monitor status polling - verify cache updates
- [ ] Test offline detection - disconnect network
- [ ] Test reconnection - verify auto-recovery

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goal**: Basic infrastructure and Bosch Praesensa support

**Tasks**:
1. ✅ Create database schema (tables, migrations)
2. ✅ Implement SQLAlchemy models
3. ✅ Create base executor interface
4. ✅ Implement Bosch Praesensa executor (basic volume/mute)
5. ✅ Update protocol router
6. ✅ Create basic API endpoints
7. ✅ Research Bosch API documentation

**Deliverables**:
- Database tables created
- Basic Bosch executor working
- API endpoints for controller management
- Commands queue through to executor

**Risks**:
- Bosch API documentation may be hard to obtain
- May need actual hardware for testing

### Phase 2: Status Polling & Frontend (Week 3-4)

**Goal**: Real-time status monitoring and basic UI

**Tasks**:
1. ✅ Implement audio status poller service
2. ✅ Create frontend `/audio` page
3. ✅ Build zone control components
4. ✅ Implement volume sliders with real-time feedback
5. ✅ Add mute controls and input selectors
6. ✅ Test end-to-end with physical Bosch system

**Deliverables**:
- Status polling service running
- Functional frontend UI
- Real-time control of Bosch amplifier

**Risks**:
- Polling frequency may need tuning
- Network latency issues

### Phase 3: Presets & Advanced Features (Week 5-6)

**Goal**: Preset management and advanced Bosch features

**Tasks**:
1. ✅ Implement preset storage and recall
2. ✅ Add fault monitoring for Bosch
3. ✅ Battery backup status display
4. ✅ Zone routing configuration
5. ✅ Preset UI components
6. ✅ Advanced configuration options

**Deliverables**:
- Full preset support
- Comprehensive Bosch integration
- Production-ready for Bosch systems

### Phase 4: Additional Brands (Week 7+)

**Goal**: Expand to AUDAC, Sonos, and others

**Tasks**:
1. ✅ AUDAC Dante executor
2. ✅ Sonos executor (easy win)
3. ✅ Generic REST API executor
4. ✅ Multi-brand testing
5. ✅ Documentation updates

**Deliverables**:
- Support for 3-4 amplifier brands
- Comprehensive brand comparison docs

---

## Success Criteria

### Minimum Viable Product (MVP)

- [ ] Bosch Praesensa controller discovered and adopted
- [ ] Volume control working on all zones
- [ ] Mute/unmute working on all zones
- [ ] Status polling updates UI in real-time
- [ ] Commands queue and execute reliably
- [ ] Basic error handling and offline detection

### Production Ready

- [ ] All Bosch features implemented (presets, routing, faults)
- [ ] Comprehensive error handling and retry logic
- [ ] Status polling optimized for performance
- [ ] Full test coverage (unit + integration)
- [ ] Documentation complete
- [ ] User training materials

### Full Feature Parity with TVs

- [ ] Same UI/UX patterns as TV control
- [ ] Discovery workflow identical
- [ ] Hybrid configurations (if needed)
- [ ] Scheduling support
- [ ] Command history and diagnostics

---

## Security Considerations

1. **Credential Storage**: Encrypt Bosch API credentials in database
2. **Network Security**: Ensure HTTPS for web UI, consider VPN for amplifier access
3. **Authentication**: Implement proper SHA-256 password hashing for Bosch
4. **Authorization**: Role-based access control for audio commands
5. **Audit Trail**: Log all volume changes and configuration modifications

---

## Performance Considerations

1. **Polling Frequency**: Balance status freshness vs network load (5-10s default)
2. **Command Queue**: Prevent command flooding, rate limiting per controller
3. **Caching**: Cache amplifier capabilities and configuration
4. **Connection Pooling**: Reuse connections to Bosch controllers
5. **Frontend Updates**: Use WebSocket for real-time status (future enhancement)

---

## Future Enhancements

1. **Scheduling**: Scheduled volume changes, preset recalls (reuse TV scheduling)
2. **Automation**: Trigger audio presets based on events
3. **Analytics**: Volume usage patterns, fault history
4. **Mobile App**: iOS/Android native apps for audio control
5. **Integration**: Trigger audio from TV events (e.g., mute audio when TV turns on)
6. **Advanced Routing**: Visual matrix routing editor
7. **Multi-Site**: Manage audio across multiple locations

---

## Appendix A: Bosch Praesensa System Overview

### System Architecture

```
Praesensa Network
├── System Controller (PRA-SCL or PRA-SCS)
│   ├── Central configuration and control
│   ├── Open Interface API endpoint
│   └── OMNEO audio routing
├── Power Amplifiers (PRA-Pxxx series)
│   ├── Multi-channel outputs
│   ├── Dante audio input
│   └── Network monitoring
├── Call Stations / Control Panels
│   ├── Paging microphones
│   └── Zone selection
└── Network Audio Devices
    ├── IP microphones
    ├── IP speakers
    └── Audio interfaces
```

### Typical Installation

- **1 System Controller** per site (up to 2 for redundancy)
- **Multiple Power Amplifiers** (4-16 channels each)
- **Network Infrastructure**: Managed switches, VLANs
- **Audio Transport**: Dante/AES67 for digital audio
- **Control**: Open Interface API for third-party integration

---

## Appendix B: Command Reference

### Audio Commands

| Command | Parameters | Description | Example |
|---------|-----------|-------------|---------|
| `set_volume` | `volume`, `zone` | Set volume level (0-100) | `{"volume": 75, "zone": 1}` |
| `mute` | `zone` | Mute specified zone | `{"zone": 1}` |
| `unmute` | `zone` | Unmute specified zone | `{"zone": 1}` |
| `select_input` | `input`, `zone` | Select input source | `{"input": "mic1", "zone": 1}` |
| `recall_preset` | `preset_id` | Recall stored preset | `{"preset_id": "meeting_mode"}` |
| `power_on` | - | Power on system | `{}` |
| `power_off` | - | Power off system | `{}` |

---

## Appendix C: Resources

### Documentation to Obtain

1. **Bosch Praesensa**:
   - Installation Manual (v1.50+)
   - Open Interface API Reference
   - System Configuration Guide
   - Network Architecture Guide

2. **OMNEO/AES70**:
   - AES70-1, AES70-2, AES70-3 standards
   - OCA Alliance documentation
   - Python OCA library (if exists)

3. **Dante**:
   - Audinate Dante Controller API
   - Dante discovery protocol

### Useful Libraries

- `aes70` - Python AES70/OCA implementation (if exists)
- `python-dante` - Dante control library
- `paho-mqtt` - For MQTT-based amplifiers
- `aiohttp` - For REST API communication
- `cryptography` - For credential encryption

### Contacts

- **Bosch Technical Support**: [To be added]
- **Local Bosch Distributor**: [To be added]
- **Integration Partner**: [To be added]

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-08 | Claude | Initial draft - comprehensive implementation guide |

---

## Conclusion

This implementation guide provides a complete blueprint for integrating network amplifiers into TapCommand, with primary focus on Bosch Praesensa systems. The architecture mirrors the successful network TV implementation, ensuring consistency and maintainability.

**Key Takeaways**:
- Reuse existing infrastructure (Virtual Controllers, command queue, protocol router)
- Phase 1 focuses exclusively on Bosch Praesensa
- Follow same patterns as TV control for UI/UX consistency
- Comprehensive status polling for real-time feedback
- Extensible design supports multiple brands in future phases

**Next Immediate Steps**:
1. Obtain Bosch Praesensa API documentation
2. Set up test environment with Bosch hardware or simulator
3. Implement Phase 1 tasks (database → backend → basic executor)
4. Coordinate with Bosch technical support for developer access

**Timeline**: 6-8 weeks for full Bosch integration, additional 2-4 weeks per brand thereafter.
