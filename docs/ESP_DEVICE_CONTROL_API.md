# ESP Device Control API Documentation

**Version:** 1.0
**Last Updated:** 2025-10-01
**Purpose:** Complete reference for controlling SmartVenue ESPHome IR blaster devices

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [API Endpoint](#api-endpoint)
4. [Command Reference](#command-reference)
5. [Code Examples](#code-examples)
6. [Backend Implementation](#backend-implementation)
7. [ESPHome Service Layer](#esphome-service-layer)
8. [Error Handling](#error-handling)
9. [Queue System Integration](#queue-system-integration)

---

## Overview

The SmartVenue IR Control System allows remote control of multiple IR devices (TVs, projectors, etc.) through ESPHome-based ESP8266 controllers. Each controller supports up to 5 independent IR output ports.

### Key Concepts

- **Device Hostname**: Unique identifier for each ESP controller (e.g., `ir-dcf89f`, `ir-dc4516`)
- **Port (Box)**: IR output port number (1-5) on the controller
- **Channel**: TV channel number or multi-digit code
- **Command**: Action to perform (power, mute, volume, channel change, etc.)

---

## Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   Frontend UI   │─────▶│  FastAPI Backend │─────▶│ ESPHome Device  │
│   (React)       │      │  (Python)        │      │  (ESP8266)      │
└─────────────────┘      └──────────────────┘      └─────────────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  Command Queue   │
                         │  (Future)        │
                         └──────────────────┘
```

### Flow

1. **Frontend** sends command request to REST API
2. **Backend** validates request and routes to ESPHome Manager
3. **ESPHome Manager** translates parameters and calls ESPHome service
4. **ESP Device** executes IR transmission
5. **Response** confirms success/failure

---

## API Endpoint

### Send Command to Device

**Endpoint:** `POST /api/v1/devices/{hostname}/command`

**Headers:**
```
Content-Type: application/json
```

**URL Parameters:**
- `hostname` (string, required): Device hostname (e.g., `ir-dcf89f`)

**Request Body Schema:**
```typescript
{
  command: string;      // Command type (required)
  box?: number;         // IR port number (optional, default: 0)
  channel?: string;     // Channel number for "channel" command
  digit?: number;       // Digit for "number" command
}
```

**Response Schema:**
```typescript
{
  success: boolean;           // Command execution status
  message: string;            // Human-readable message
  execution_time_ms?: number; // Time taken to execute (optional)
}
```

**Success Response Example:**
```json
{
  "success": true,
  "message": "Command 'power' sent successfully",
  "execution_time_ms": 2574
}
```

**Error Response Example:**
```json
{
  "success": false,
  "message": "Failed to send command 'channel'",
  "execution_time_ms": 122
}
```

---

## Command Reference

### 1. Power Control

**Command:** `power`

Toggles power on/off for the device on the specified port.

**Request:**
```json
{
  "command": "power",
  "box": 1
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/devices/ir-dcf89f/command" \
  -H "Content-Type: application/json" \
  -d '{"command": "power", "box": 1}'
```

---

### 2. Mute Control

**Command:** `mute`

Toggles audio mute on/off for the device on the specified port.

**Request:**
```json
{
  "command": "mute",
  "box": 1
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/devices/ir-dcf89f/command" \
  -H "Content-Type: application/json" \
  -d '{"command": "mute", "box": 1}'
```

---

### 3. Volume Control

**Command:** `volume_up` or `volume_down`

Increases or decreases volume by one step.

**Request (Volume Up):**
```json
{
  "command": "volume_up",
  "box": 1
}
```

**Request (Volume Down):**
```json
{
  "command": "volume_down",
  "box": 1
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/devices/ir-dcf89f/command" \
  -H "Content-Type: application/json" \
  -d '{"command": "volume_up", "box": 1}'
```

---

### 4. Channel Navigation

**Command:** `channel_up` or `channel_down`

Navigates to next or previous channel.

**Request (Channel Up):**
```json
{
  "command": "channel_up",
  "box": 1
}
```

**Request (Channel Down):**
```json
{
  "command": "channel_down",
  "box": 1
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/devices/ir-dcf89f/command" \
  -H "Content-Type: application/json" \
  -d '{"command": "channel_up", "box": 1}'
```

---

### 5. Direct Channel Change

**Command:** `channel`

Changes to a specific channel number. The system automatically handles multi-digit channel entry with proper timing.

**Request:**
```json
{
  "command": "channel",
  "box": 1,
  "channel": "60"
}
```

**Format:** `{box}-{channel}`
- Example: Port 1, Channel 60 = `1-60`
- Example: Port 2, Channel 123 = `2-123`

**Multi-Digit Behavior:**
- Automatically splits channel into individual digits
- Sends each digit with 300ms delay between transmissions
- Example: Channel "60" → sends "6", waits 300ms, sends "0"

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/devices/ir-dcf89f/command" \
  -H "Content-Type: application/json" \
  -d '{"command": "channel", "box": 1, "channel": "60"}'
```

---

### 6. Single Digit Entry

**Command:** `number`

Sends a single digit (0-9) to the device. Useful for manual multi-digit entry or custom sequences.

**Request:**
```json
{
  "command": "number",
  "box": 1,
  "digit": 5
}
```

**Valid Digits:** 0-9

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/devices/ir-dcf89f/command" \
  -H "Content-Type: application/json" \
  -d '{"command": "number", "box": 1, "digit": 5}'
```

---

### 7. Diagnostic LED Signal

**Command:** `diagnostic_signal`

Triggers visual device identification by flashing the onboard LED at 3Hz for 2 minutes.

**Request:**
```json
{
  "command": "diagnostic_signal",
  "box": 0,
  "digit": 1
}
```

**Special Code:** `0-0001` (Port 0, Code 1)
- Port must be `0`
- Digit (code) must be `1`
- Only this specific combination triggers the diagnostic LED

**LED Behavior:**
- Flashes at 3Hz (3 flashes per second)
- Duration: 2 minutes (360 total flashes)
- After completion: LED stays on solid

**Use Cases:**
- Physical device identification in crowded installations
- Confirming device connectivity
- Troubleshooting device location

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/devices/ir-dcf89f/command" \
  -H "Content-Type: application/json" \
  -d '{"command": "diagnostic_signal", "box": 0, "digit": 1}'
```

---

## Code Examples

### Frontend (TypeScript/React)

**API Client Function:**
```typescript
// File: frontend-v2/src/features/devices/api/devices-api.ts

import { apiClient } from '@/lib/api-client';

interface CommandRequest {
  command: string;
  box?: number;
  channel?: string;
  digit?: number;
}

interface CommandResponse {
  success: boolean;
  message: string;
  execution_time_ms?: number;
}

export const sendCommand = async (
  hostname: string,
  request: CommandRequest
): Promise<CommandResponse> => {
  const response = await apiClient.post<CommandResponse>(
    `/api/v1/devices/${hostname}/command`,
    request
  );
  return response.data;
};

// Convenience functions for specific commands

export const sendPower = async (hostname: string, port: number = 1): Promise<void> => {
  await sendCommand(hostname, {
    command: 'power',
    box: port
  });
};

export const sendChannel = async (
  hostname: string,
  port: number,
  channel: string
): Promise<void> => {
  await sendCommand(hostname, {
    command: 'channel',
    box: port,
    channel: channel
  });
};

export const sendDiagnosticSignal = async (
  hostname: string,
  port: number = 0,
  code: number = 1
): Promise<void> => {
  await sendCommand(hostname, {
    command: 'diagnostic_signal',
    box: port,
    digit: code
  });
};
```

**React Component Usage:**
```typescript
import { sendPower, sendChannel, sendDiagnosticSignal } from '@/features/devices/api/devices-api';

function DeviceControl() {
  const handlePowerOn = async () => {
    try {
      await sendPower('ir-dcf89f', 1);
      console.log('Power command sent successfully');
    } catch (error) {
      console.error('Failed to send power command:', error);
    }
  };

  const handleChangeChannel = async () => {
    try {
      await sendChannel('ir-dcf89f', 1, '60');
      console.log('Channel changed to 60');
    } catch (error) {
      console.error('Failed to change channel:', error);
    }
  };

  const handleIdentifyDevice = async () => {
    try {
      await sendDiagnosticSignal('ir-dcf89f', 0, 1);
      console.log('Diagnostic LED activated');
    } catch (error) {
      console.error('Failed to activate diagnostic:', error);
    }
  };

  return (
    <div>
      <button onClick={handlePowerOn}>Power On</button>
      <button onClick={handleChangeChannel}>Channel 60</button>
      <button onClick={handleIdentifyDevice}>Identify Device</button>
    </div>
  );
}
```

---

### Backend (Python/FastAPI)

**API Endpoint Handler:**
```python
# File: backend/app/api/devices.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models import Device, ManagedDevice
from app.services.esphome_client import esphome_manager
from app.services.settings_service import settings_service

router = APIRouter()

class CommandRequest(BaseModel):
    command: str          # "power", "mute", "channel", etc.
    box: Optional[int] = 0    # For multi-port setups
    channel: Optional[str] = None  # For channel commands
    digit: Optional[int] = None    # For number commands

class CommandResponse(BaseModel):
    success: bool
    message: str
    execution_time_ms: Optional[int] = None

@router.post("/{hostname}/command", response_model=CommandResponse)
async def send_command(
    hostname: str,
    command_request: CommandRequest,
    db: Session = Depends(get_db)
):
    """Send a command to a specific device"""

    # Get device from database
    device = db.query(Device).filter(Device.hostname == hostname).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    start_time = datetime.now()
    success = False
    error_message = None

    try:
        # Get API key for device
        api_key = None
        managed = db.query(ManagedDevice).filter(
            ManagedDevice.hostname == hostname
        ).first()

        if managed and managed.api_key:
            api_key = managed.api_key
        if not api_key:
            api_key = settings_service.get_setting("esphome_api_key")

        # Send command to ESPHome device
        success = await esphome_manager.send_tv_command(
            hostname=device.hostname,
            ip_address=device.ip_address,
            command=command_request.command,
            box=command_request.box or 0,
            channel=command_request.channel,
            digit=command_request.digit,
            api_key=api_key,
        )

        if success:
            message = f"Command '{command_request.command}' sent successfully"
        else:
            message = f"Failed to send command '{command_request.command}'"
            error_message = "Command execution failed"

    except Exception as e:
        success = False
        message = f"Error sending command: {str(e)}"
        error_message = str(e)

    # Calculate execution time
    execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

    return CommandResponse(
        success=success,
        message=message,
        execution_time_ms=execution_time_ms
    )
```

---

## Backend Implementation

### ESPHome Manager Class

**File:** `backend/app/services/esphome_client.py`

**Key Method:** `send_tv_command()`

```python
async def send_tv_command(
    self,
    hostname: str,
    ip_address: str,
    command: str,
    box: int = 0,
    *,
    api_key: Optional[str] = None,
    **kwargs,
) -> bool:
    """
    Send a TV command to a specific device

    Args:
        hostname: Device hostname (e.g., 'ir-dcf89f')
        ip_address: Device IP address
        command: Command type ('power', 'channel', etc.)
        box: Port number (1-5, or 0 for diagnostic)
        api_key: ESPHome API encryption key
        **kwargs: Additional parameters (channel, digit, etc.)

    Returns:
        bool: True if command sent successfully
    """

    client = self.get_client(hostname, ip_address, api_key)

    # Map command types to ESPHome service names
    service_map = {
        "power": "tv_power",
        "mute": "tv_mute",
        "volume_up": "tv_volume_up",
        "volume_down": "tv_volume_down",
        "channel_up": "tv_channel_up",
        "channel_down": "tv_channel_down",
        "channel": "tv_channel",
        "number": "tv_number",
        "diagnostic_signal": "diagnostic_signal"
    }

    service_name = service_map.get(command)
    if not service_name:
        logger.error(f"Unknown command: {command}")
        return False

    # Prepare service data
    service_data = {}

    # Add port parameter if specified
    # ESPHome services expect 'port' parameter, not 'box'
    if box > 0:
        service_data["port"] = box

    # Handle command-specific parameters
    if command == "channel":
        if "channel" in kwargs:
            # ESPHome tv_channel service expects separate port and channel parameters
            service_data["channel"] = int(kwargs["channel"])
            # Port is already added above if box > 0
        else:
            logger.error("Channel command requires 'channel' parameter")
            return False

    elif command == "number":
        if "digit" in kwargs:
            service_data["digit"] = kwargs["digit"]
        else:
            logger.error("Number command requires 'digit' parameter")
            return False

    elif command == "diagnostic_signal":
        # Handle diagnostic signal parameters
        # Accept either 'port' or 'box' parameter names
        port_param = kwargs.get("port", box)
        code_param = kwargs.get("code", kwargs.get("digit"))

        if code_param is not None:
            service_data["port"] = port_param
            service_data["code"] = code_param
        else:
            logger.error("Diagnostic signal command requires 'code' parameter")
            return False

    # Call the ESPHome service
    return await client.call_service(service_name, service_data)
```

### Parameter Translation

**Important:** The backend translates between API parameter names and ESPHome service parameter names:

| API Parameter | ESPHome Parameter | Description |
|--------------|-------------------|-------------|
| `box` | `port` | IR output port number (1-5) |
| `channel` | `channel` | Channel number (as integer) |
| `digit` | `digit` or `code` | Single digit or diagnostic code |

---

## ESPHome Service Layer

### Service Definitions (on ESP Device)

The ESP8266 device runs ESPHome firmware with the following services defined:

```yaml
api:
  services:
    - service: tv_power
      variables:
        port: int
      then:
        - script.execute:
            id: dispatch_power
            target_port: !lambda 'return port;'

    - service: tv_mute
      variables:
        port: int
      then:
        - script.execute:
            id: dispatch_mute
            target_port: !lambda 'return port;'

    - service: tv_channel
      variables:
        port: int
        channel: int
      then:
        - script.execute:
            id: smart_channel
            target_port: !lambda 'return port;'
            channel: !lambda 'return channel;'

    - service: tv_number
      variables:
        port: int
        digit: int
      then:
        - script.execute:
            id: dispatch_digit
            target_port: !lambda 'return port;'
            digit: !lambda 'return digit;'

    - service: diagnostic_signal
      variables:
        port: int
        code: int
      then:
        - lambda: |-
            ESP_LOGI("diagnostic", "Received diagnostic signal - Port: %d, Code: %d", port, code);
            if (port == 0 && code == 1) {
              id(diagnostic_alert_start).execute();
            }
```

### Smart Channel Script

The `smart_channel` script handles multi-digit channel entry automatically:

```yaml
script:
  - id: smart_channel
    parameters:
      target_port: int
      channel: int
    then:
      # Convert channel number to string of digits
      - lambda: |-
          id(target_port_store) = target_port;
          id(channel_digits) = std::to_string(channel);
          id(digit_index) = 0;
      # Start sending digits sequentially
      - script.execute: send_next_channel_digit

  - id: send_next_channel_digit
    mode: restart
    then:
      - lambda: |-
          if (id(digit_index) >= id(channel_digits).length()) {
            ESP_LOGI("smart_channel", "Channel sequence complete");
            return;
          }
          int digit = id(channel_digits)[id(digit_index)] - '0';
          id(current_digit) = digit;
          id(digit_index) += 1;
      # Send the digit
      - script.execute:
          id: dispatch_digit
          target_port: !lambda 'return id(target_port_store);'
          digit: !lambda 'return id(current_digit);'
      # Wait 300ms before next digit
      - if:
          condition:
            lambda: 'return id(digit_index) < id(channel_digits).length();'
          then:
            - delay: 300ms
            - script.execute: send_next_channel_digit
```

### Diagnostic LED Script

```yaml
script:
  - id: diagnostic_alert_start
    mode: restart
    then:
      - script.stop: diagnostic_alert_running
      - script.execute: diagnostic_alert_running

  - id: diagnostic_alert_running
    mode: restart
    then:
      - lambda: |-
          ESP_LOGI("diagnostic", "Starting LED diagnostic alert - 3Hz for 2 minutes");
      - repeat:
          count: 360  # 3 flashes/sec × 120 seconds = 360 flashes
          then:
            - output.turn_on: diagnostic_led
            - delay: 166ms  # On for 166ms (3Hz = 333ms cycle)
            - output.turn_off: diagnostic_led
            - delay: 167ms  # Off for 167ms
      - script.execute: diagnostic_alert_end

  - id: diagnostic_alert_end
    then:
      - lambda: |-
          ESP_LOGI("diagnostic", "Diagnostic alert completed - resuming normal LED behavior");
      - output.turn_on: diagnostic_led
```

---

## Error Handling

### Common Error Scenarios

#### 1. Device Not Found
**HTTP Status:** 404
**Response:**
```json
{
  "detail": "Device not found"
}
```
**Cause:** Hostname doesn't exist in database
**Solution:** Verify hostname is correct and device is registered

#### 2. Device Offline
**HTTP Status:** 200
**Response:**
```json
{
  "success": false,
  "message": "Failed to send command 'power'",
  "execution_time_ms": 2000
}
```
**Cause:** Device not reachable on network
**Solution:** Check device power, network connectivity, IP address

#### 3. Port Not Configured
**HTTP Status:** 200
**Response:**
```json
{
  "success": false,
  "message": "Failed to send command 'power'",
  "execution_time_ms": 120
}
```
**Cause:** Specified port has no IR library assigned
**Solution:** Assign IR library to port in management interface

#### 4. Invalid Parameters
**HTTP Status:** 422
**Response:**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "command"],
      "msg": "Field required"
    }
  ]
}
```
**Cause:** Required field missing or invalid type
**Solution:** Check request body matches CommandRequest schema

#### 5. Service Not Found
**HTTP Status:** 200
**Response:**
```json
{
  "success": false,
  "message": "Error calling service 'unknown_service' on device: Service not found",
  "execution_time_ms": 150
}
```
**Cause:** Device firmware doesn't support requested command
**Solution:** Update device firmware to latest version

### Retry Logic Recommendations

For production queue system implementation:

```python
import asyncio
from typing import Optional

async def send_command_with_retry(
    hostname: str,
    command: str,
    box: int,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    **kwargs
) -> bool:
    """
    Send command with automatic retry logic

    Args:
        hostname: Device hostname
        command: Command type
        box: Port number
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries in seconds
        **kwargs: Additional command parameters

    Returns:
        bool: True if command succeeded within retry limit
    """

    for attempt in range(max_retries):
        try:
            success = await esphome_manager.send_tv_command(
                hostname=hostname,
                ip_address=get_device_ip(hostname),  # Helper function
                command=command,
                box=box,
                **kwargs
            )

            if success:
                return True

            # Command sent but failed - wait before retry
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)

        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")

            # Don't retry on certain errors
            if "not found" in str(e).lower():
                return False

            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)

    return False
```

---

## Queue System Integration

### Recommended Database Schema

For the upcoming command queuing system:

```sql
CREATE TABLE command_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hostname VARCHAR NOT NULL,              -- Target device
    command VARCHAR NOT NULL,                -- Command type
    port INTEGER DEFAULT 0,                  -- IR port (box)
    channel VARCHAR,                         -- For channel commands
    digit INTEGER,                           -- For number/diagnostic commands

    -- Queue management
    status VARCHAR DEFAULT 'pending',        -- pending, processing, completed, failed
    priority INTEGER DEFAULT 0,              -- Higher = more urgent
    scheduled_at DATETIME,                   -- When to execute (NULL = ASAP)

    -- Execution tracking
    attempts INTEGER DEFAULT 0,              -- Retry counter
    max_attempts INTEGER DEFAULT 3,          -- Max retries
    last_attempt_at DATETIME,                -- Last execution attempt
    completed_at DATETIME,                   -- When completed/failed

    -- Results
    success BOOLEAN,                         -- Final result
    error_message TEXT,                      -- Error details if failed
    execution_time_ms INTEGER,               -- Time taken

    -- Metadata
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR,                      -- User/system that created
    notes TEXT,                              -- Optional context

    -- Indexes for performance
    INDEX idx_status (status),
    INDEX idx_scheduled (scheduled_at),
    INDEX idx_hostname (hostname),
    INDEX idx_created (created_at)
);
```

### Queue Processing Logic

```python
from datetime import datetime, timedelta
from sqlalchemy import and_, or_

class CommandQueueProcessor:
    """
    Background worker that processes queued commands
    """

    def __init__(self, poll_interval: float = 1.0):
        self.poll_interval = poll_interval
        self.running = False

    async def start(self):
        """Start the queue processor"""
        self.running = True
        while self.running:
            await self.process_batch()
            await asyncio.sleep(self.poll_interval)

    async def process_batch(self, batch_size: int = 10):
        """Process a batch of queued commands"""

        db = next(get_db())
        try:
            # Get pending commands ready to execute
            now = datetime.now()
            commands = db.query(CommandQueue).filter(
                and_(
                    CommandQueue.status == 'pending',
                    CommandQueue.attempts < CommandQueue.max_attempts,
                    or_(
                        CommandQueue.scheduled_at == None,
                        CommandQueue.scheduled_at <= now
                    )
                )
            ).order_by(
                CommandQueue.priority.desc(),
                CommandQueue.created_at.asc()
            ).limit(batch_size).all()

            for cmd in commands:
                await self.execute_command(cmd, db)

        finally:
            db.close()

    async def execute_command(self, cmd: CommandQueue, db: Session):
        """Execute a single queued command"""

        # Mark as processing
        cmd.status = 'processing'
        cmd.attempts += 1
        cmd.last_attempt_at = datetime.now()
        db.commit()

        try:
            # Get device info
            device = db.query(Device).filter(
                Device.hostname == cmd.hostname
            ).first()

            if not device:
                raise Exception(f"Device {cmd.hostname} not found")

            # Execute command
            start_time = datetime.now()

            success = await esphome_manager.send_tv_command(
                hostname=cmd.hostname,
                ip_address=device.ip_address,
                command=cmd.command,
                box=cmd.port,
                channel=cmd.channel,
                digit=cmd.digit,
                api_key=get_device_api_key(cmd.hostname)
            )

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            # Update command record
            cmd.success = success
            cmd.execution_time_ms = int(execution_time)
            cmd.completed_at = datetime.now()

            if success:
                cmd.status = 'completed'
            else:
                # Retry if attempts remaining
                if cmd.attempts < cmd.max_attempts:
                    cmd.status = 'pending'
                    cmd.error_message = "Command failed, will retry"
                else:
                    cmd.status = 'failed'
                    cmd.error_message = "Max retry attempts exceeded"

        except Exception as e:
            cmd.error_message = str(e)

            # Retry if attempts remaining
            if cmd.attempts < cmd.max_attempts:
                cmd.status = 'pending'
            else:
                cmd.status = 'failed'
                cmd.success = False
                cmd.completed_at = datetime.now()

        db.commit()
```

### API Endpoints for Queue Management

```python
@router.post("/queue-command", response_model=QueueCommandResponse)
async def queue_command(
    request: QueueCommandRequest,
    db: Session = Depends(get_db)
):
    """Add command to execution queue"""

    cmd = CommandQueue(
        hostname=request.hostname,
        command=request.command,
        port=request.port,
        channel=request.channel,
        digit=request.digit,
        priority=request.priority or 0,
        scheduled_at=request.scheduled_at,
        created_by=request.created_by
    )

    db.add(cmd)
    db.commit()
    db.refresh(cmd)

    return QueueCommandResponse(
        id=cmd.id,
        status=cmd.status,
        message="Command queued successfully"
    )

@router.post("/bulk-queue", response_model=BulkQueueResponse)
async def bulk_queue_commands(
    requests: List[QueueCommandRequest],
    db: Session = Depends(get_db)
):
    """Queue multiple commands at once"""

    queued_ids = []

    for req in requests:
        cmd = CommandQueue(
            hostname=req.hostname,
            command=req.command,
            port=req.port,
            channel=req.channel,
            digit=req.digit,
            priority=req.priority or 0,
            scheduled_at=req.scheduled_at,
            created_by=req.created_by
        )
        db.add(cmd)
        queued_ids.append(cmd.id)

    db.commit()

    return BulkQueueResponse(
        queued_count=len(queued_ids),
        command_ids=queued_ids,
        message=f"Queued {len(queued_ids)} commands successfully"
    )
```

### Frontend Queue Integration

```typescript
// Queue commands instead of executing immediately
export const queueCommand = async (
  hostname: string,
  command: string,
  port?: number,
  channel?: string,
  digit?: number,
  priority?: number
): Promise<{ id: number; status: string }> => {
  const response = await apiClient.post('/api/v1/devices/queue-command', {
    hostname,
    command,
    port,
    channel,
    digit,
    priority
  });
  return response.data;
};

// Bulk queue for multiple commands
export const bulkQueueCommands = async (
  commands: Array<{
    hostname: string;
    command: string;
    port?: number;
    channel?: string;
    digit?: number;
  }>
): Promise<{ queued_count: number; command_ids: number[] }> => {
  const response = await apiClient.post('/api/v1/devices/bulk-queue', commands);
  return response.data;
};

// Usage example: Change all TVs to channel 60
const changeAllToChannel60 = async () => {
  const commands = devices.map(device => ({
    hostname: device.hostname,
    command: 'channel',
    port: 1,
    channel: '60'
  }));

  const result = await bulkQueueCommands(commands);
  console.log(`Queued ${result.queued_count} channel change commands`);
};
```

---

## Command History & Status Display

### Database Schema for History

```sql
-- Store last successful channel per port for status display
CREATE TABLE port_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hostname VARCHAR NOT NULL,
    port INTEGER NOT NULL,
    last_channel VARCHAR,                  -- Last channel sent (e.g., "60")
    last_command VARCHAR,                   -- Last command type
    last_success_at DATETIME,               -- When last successful
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(hostname, port)
);
```

### Update Logic

```python
# After successful channel command
if success and command == "channel":
    # Update or create port status
    port_status = db.query(PortStatus).filter(
        and_(
            PortStatus.hostname == hostname,
            PortStatus.port == port
        )
    ).first()

    if port_status:
        port_status.last_channel = channel
        port_status.last_command = command
        port_status.last_success_at = datetime.now()
        port_status.updated_at = datetime.now()
    else:
        port_status = PortStatus(
            hostname=hostname,
            port=port,
            last_channel=channel,
            last_command=command,
            last_success_at=datetime.now()
        )
        db.add(port_status)

    db.commit()
```

### Display in UI

```typescript
interface PortStatus {
  hostname: string;
  port: number;
  lastChannel?: string;
  lastSuccessAt?: string;
}

const DevicePortStatus: React.FC<{ status: PortStatus }> = ({ status }) => {
  return (
    <div className="port-status">
      <span className="port-label">Port {status.port}:</span>
      {status.lastChannel ? (
        <span className="channel-display">
          Channel {status.lastChannel}
          <span className="timestamp">
            {formatRelativeTime(status.lastSuccessAt)}
          </span>
        </span>
      ) : (
        <span className="no-data">No channel data</span>
      )}
    </div>
  );
};
```

---

## Appendix: Complete Command Summary

| Command | Port Required | Additional Params | Description | Example |
|---------|--------------|-------------------|-------------|---------|
| `power` | Yes (1-5) | None | Toggle power | `{"command":"power","box":1}` |
| `mute` | Yes (1-5) | None | Toggle mute | `{"command":"mute","box":1}` |
| `volume_up` | Yes (1-5) | None | Increase volume | `{"command":"volume_up","box":1}` |
| `volume_down` | Yes (1-5) | None | Decrease volume | `{"command":"volume_down","box":1}` |
| `channel_up` | Yes (1-5) | None | Next channel | `{"command":"channel_up","box":1}` |
| `channel_down` | Yes (1-5) | None | Previous channel | `{"command":"channel_down","box":1}` |
| `channel` | Yes (1-5) | `channel` (string) | Direct channel | `{"command":"channel","box":1,"channel":"60"}` |
| `number` | Yes (1-5) | `digit` (0-9) | Single digit | `{"command":"number","box":1,"digit":5}` |
| `diagnostic_signal` | Must be 0 | `digit=1` | LED flash | `{"command":"diagnostic_signal","box":0,"digit":1}` |

---

## Version History

- **1.0** (2025-10-01): Initial comprehensive documentation
  - All command types documented
  - Backend implementation details
  - ESPHome service layer explanation
  - Queue system integration design
  - Error handling and retry logic
  - Code examples for frontend and backend

---

## Support & Troubleshooting

For issues or questions:
1. Check device is online and reachable
2. Verify port has IR library assigned (except diagnostic)
3. Check backend logs for detailed error messages
4. Confirm ESPHome firmware is up to date
5. Test with diagnostic signal (0-0001) to verify basic connectivity

**Backend Logs Location:** `backend/app/services/esphome_client.py` (logger: `app.services.esphome_client`)

**Common Log Messages:**
- `Connected to ESPHome device: {hostname}` - Connection successful
- `Called service '{service}' on {hostname} with data: {data}` - Command sent
- `Error calling service '{service}' on {hostname}: {error}` - Command failed
- `Service '{service}' not found on device {hostname}` - Firmware issue
