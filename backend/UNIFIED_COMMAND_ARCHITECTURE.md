# Unified Command Queue Architecture

## Overview

SmartVenue now uses a **unified command queue system** that routes all device commands (IR and Network) through a single, consistent pipeline. This provides:

- **Protocol Abstraction** - Frontend doesn't need to know if device is IR or Network
- **Easy Extensibility** - Add new TV brands by creating one executor file
- **Consistent Logging** - All commands tracked in one place
- **Future Features** - Queue enables retry logic, scheduling, bulk operations

## Architecture Diagram

```
┌─────────────┐
│   Frontend  │
│  (User UI)  │
└──────┬──────┘
       │ POST /api/commands/execute
       │ { controller_id, command, parameters }
       ▼
┌─────────────────────────────────┐
│     Unified Command API         │
│  (Single endpoint for all)      │
└──────┬──────────────────────────┘
       │ Creates Command object
       ▼
┌─────────────────────────────────┐
│      Command Queue (DB)         │
│  Stores: id, controller_id,     │
│  command, status, timestamps    │
└──────┬──────────────────────────┘
       │ Queue Manager picks up
       ▼
┌─────────────────────────────────┐
│      Protocol Router            │
│  Examines device_type+protocol  │
│  Returns appropriate executor   │
└──────┬──────────────────────────┘
       │
       ├──→ IR? ──────→ IRExecutor ────────→ ESPHome/GPIO
       │
       ├──→ Samsung? ──→ SamsungExecutor ──→ TCP:55000
       │
       ├──→ LG? ──────→ LGExecutor ────────→ WebSocket:3000
       │
       ├──→ Roku? ────→ RokuExecutor ──────→ HTTP:8060
       │
       └──→ [Future brands...]
              │
              ▼
       ┌─────────────────┐
       │  Execution      │
       │  Result         │
       │  (success/fail) │
       └─────────────────┘
```

## Directory Structure

```
app/
├── commands/
│   ├── __init__.py
│   ├── models.py              # Command, ExecutionResult, enums
│   ├── router.py              # Protocol router
│   ├── queue.py               # Queue manager (to be created)
│   ├── api.py                 # Unified command endpoint (to be created)
│   │
│   └── executors/
│       ├── __init__.py
│       ├── base.py            # CommandExecutor ABC
│       ├── ir_executor.py     # IR/ESPHome executor
│       │
│       └── network/
│           ├── __init__.py
│           ├── samsung_legacy.py     # ✅ Implemented
│           ├── samsung_websocket.py  # 📝 Planned
│           ├── lg_webos.py           # 📝 Stub
│           ├── sony_bravia.py        # 📝 Planned
│           ├── roku.py               # ✅ Implemented
│           ├── android_tv.py         # 📝 Planned
│           ├── philips.py            # 📝 Planned
│           └── vizio.py              # 📝 Planned
```

## Key Components

### 1. Command Model (`models.py`)

```python
class Command(Base):
    id = Column(Integer, primary_key=True)
    command_id = Column(String, unique=True)  # UUID

    # Device info
    controller_id = Column(String)  # ir-dc4516 or nw-b85a97
    device_type = Column(String)    # "universal" or "network_tv"
    protocol = Column(String)        # "samsung_legacy", etc.

    # Command
    command = Column(String)         # "power", "volume_up", etc.
    parameters = Column(JSON)        # {port: 1, channel: "63"}

    # Status
    status = Column(Enum)            # QUEUED/EXECUTING/COMPLETED/FAILED
    result_data = Column(JSON)
    error_message = Column(String)

    # Timestamps
    created_at, started_at, completed_at
```

### 2. Base Executor (`executors/base.py`)

```python
class CommandExecutor(ABC):
    def __init__(self, db: Session):
        self.db = db

    @abstractmethod
    async def execute(self, command: Command) -> ExecutionResult:
        """Execute command, return result"""
        pass

    @abstractmethod
    def can_execute(self, command: Command) -> bool:
        """Check if this executor handles this command"""
        pass
```

### 3. Protocol Router (`router.py`)

```python
class ProtocolRouter:
    def get_executor(self, command: Command) -> CommandExecutor:
        # IR Controllers
        if command.device_type in ["universal", "ir"]:
            return IRExecutor(self.db)

        # Network TVs
        if command.device_type == "network_tv":
            if command.protocol == "samsung_legacy":
                return SamsungLegacyExecutor(self.db)
            elif command.protocol == "roku":
                return RokuExecutor(self.db)
            # ... etc
```

## Implemented Executors

### ✅ IR Executor

**File:** `executors/ir_executor.py`

**Handles:** All IR controllers (universal, ir)

**Protocol:** ESPHome API

**Key Code:**
```python
device = self.db.query(ManagedDevice).filter_by(
    hostname=command.controller_id
).first()

success = await esphome_manager.send_tv_command(
    hostname=device.hostname,
    ip_address=device.current_ip_address,
    command=command.command,
    box=port,
    channel=channel,
    api_key=device.api_key
)
```

### ✅ Samsung Legacy Executor

**File:** `executors/network/samsung_legacy.py`

**Handles:** Pre-2016 Samsung TVs (D/E/F series)

**Protocol:** Base64 TCP commands on port 55000

**Library:** `samsungctl`

**Key Code:**
```python
config = {
    "host": device.ip_address,
    "port": 55000,
    "method": "legacy"
}

key = KEY_MAP.get(command.command, f"KEY_{command.command.upper()}")

with samsungctl.Remote(config) as remote:
    remote.control(key)
```

### ✅ Roku Executor

**File:** `executors/network/roku.py`

**Handles:** Roku devices and Roku TVs

**Protocol:** ECP (HTTP REST API) on port 8060

**Library:** None (pure HTTP)

**Key Code:**
```python
key = KEY_MAP.get(command.command.lower(), command.command.title())
url = f"http://{device.ip_address}:8060/keypress/{key}"
response = requests.post(url, timeout=3)
```

## Command Flow Example

### User Clicks "Power" on Samsung TV

1. **Frontend**
   ```javascript
   POST /api/commands/execute
   {
     "controller_id": "nw-b85a97",
     "command": "power"
   }
   ```

2. **API Layer**
   - Validates request
   - Looks up controller in DB
   - Gets device_type ("network_tv") and protocol ("samsung_legacy")
   - Creates Command object
   - Saves to queue with status=QUEUED

3. **Queue Manager**
   - Picks up command from queue
   - Updates status=EXECUTING

4. **Protocol Router**
   - Sees device_type="network_tv" + protocol="samsung_legacy"
   - Returns SamsungLegacyExecutor

5. **Samsung Legacy Executor**
   - Gets device IP from Virtual Device
   - Maps "power" → "KEY_POWER"
   - Sends to Samsung TV on port 55000
   - Returns ExecutionResult

6. **Queue Manager**
   - Updates command status=COMPLETED
   - Stores result_data
   - Returns response to API

7. **API Response**
   ```json
   {
     "command_id": "uuid-...",
     "status": "completed",
     "result_data": {
       "execution_time_ms": 234,
       "device": "Samsung TV Legacy (50)",
       "key": "KEY_POWER"
     }
   }
   ```

## Adding a New Brand

See `NETWORK_TV_EXECUTORS.md` for detailed guide.

**Quick Steps:**

1. Create executor file: `executors/network/brand_name.py`
2. Extend CommandExecutor base class
3. Implement `can_execute()` and `execute()` methods
4. Map commands to brand's protocol
5. Add to Protocol Router
6. Test!

**Example Template:**
```python
class BrandExecutor(CommandExecutor):
    KEY_MAP = {"power": "BRAND_POWER_CODE", ...}

    def can_execute(self, command):
        return command.protocol == "brand_protocol"

    async def execute(self, command):
        device = self._get_device(command.controller_id)
        # Send command using brand's library/protocol
        return ExecutionResult(success=True, ...)
```

## Standard Command Names

For consistency across all brands:

**Power:** `power`, `power_on`, `power_off`
**Volume:** `volume_up`, `volume_down`, `mute`
**Channels:** `channel_up`, `channel_down`, `channel_direct`
**Navigation:** `up`, `down`, `left`, `right`, `ok`, `back`, `home`, `menu`
**Transport:** `play`, `pause`, `stop`, `rewind`, `fast_forward`
**Sources:** `source`, `hdmi1`, `hdmi2`, `hdmi3`, `hdmi4`
**Digits:** `0` through `9`

## Benefits

### 1. Unified Frontend
- Single API endpoint for all devices
- No need to know IR vs Network
- Consistent response format

### 2. Easy Maintenance
- Each brand in separate file
- Clear separation of concerns
- Well-documented protocols

### 3. Scalability
- Add brands without changing core code
- Protocol router handles routing
- Executors are independent

### 4. Future Features
- **Retry Logic** - Auto-retry failed commands
- **Scheduling** - Queue commands for later
- **Bulk Operations** - Send to multiple devices
- **Rate Limiting** - Throttle per device
- **Command History** - Full audit trail
- **Conditional Execution** - Only if device online

## Next Steps

1. ✅ Command models created
2. ✅ Base executor created
3. ✅ IR executor implemented
4. ✅ Samsung Legacy executor implemented
5. ✅ Roku executor implemented
6. ✅ Protocol router created
7. ✅ Documentation written
8. 📝 Queue manager (next)
9. 📝 Unified API endpoint (next)
10. 📝 Database migration (next)
11. 📝 Frontend integration (next)

## Related Documentation

- `NETWORK_TV_EXECUTORS.md` - Detailed guide to all TV protocols
- `VIRTUAL_CONTROLLERS.md` - Virtual Controller system docs
- `VIRTUAL_CONTROLLER_ADOPTION.md` - Adoption flow docs
