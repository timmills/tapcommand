# CHiQ TV Network Control - Research & Implementation Plan

**Date:** October 7, 2025
**Status:** Research Complete ✅ | Ready to Implement 🚀

---

## Executive Summary

**Good news!** CHiQ TVs can be controlled via network using **Android TV protocols**.

CHiQ is a sub-brand of **Changhong Electric** (Chinese manufacturer) and their TVs run **Android TV** operating system, making them compatible with existing Android TV control libraries.

We can add CHiQ support using the same approach as generic Android TV devices.

---

## Key Findings

### 1. CHiQ TV Background

- **Manufacturer:** Sichuan Changhong Electric Co., Ltd. (founded 1958)
- **Brand:** CHiQ (international brand name for Changhong)
- **Market:** Budget-friendly smart TVs
- **Operating System:** Android TV (NOT VIDAA - that's Hisense)
- **Network:** 2.4 GHz WiFi or Ethernet (RJ45)

### 2. Network Control Methods

CHiQ TVs support **two network control protocols**:

#### Option A: Android TV Remote Protocol v2 (RECOMMENDED ✅)
- **Protocol:** Android TV Remote v2 (same as Google TV app)
- **Port:** 6466 (control), 6467 (pairing)
- **Authentication:** Pairing required (one-time)
- **Library:** `androidtvremote2` (Python)
- **Advantages:**
  - ✅ No ADB required
  - ✅ No developer mode needed
  - ✅ Works out of the box
  - ✅ Same protocol as official Google TV app
  - ✅ More reliable than ADB

#### Option B: ADB (Android Debug Bridge)
- **Protocol:** ADB over network
- **Port:** 5555 (default)
- **Authentication:** None (after enabling developer mode)
- **Library:** `androidtv` (Python)
- **Disadvantages:**
  - ⚠️ Requires enabling developer mode (build number tap 10x)
  - ⚠️ Requires enabling network debugging in settings
  - ⚠️ User approval dialog on first connection
  - ⚠️ Less reliable (can disconnect)

**Recommendation:** Use **Option A (Android TV Remote Protocol v2)** for better user experience.

---

## Python Libraries Available

### 1. `androidtvremote2` (RECOMMENDED)

**Install:**
```bash
pip install androidtvremote2
```

**Features:**
- Android TV Remote protocol v2
- No ADB or developer mode required
- Pairing-based authentication
- Key press simulation
- App launching
- Volume control
- Power control

**Documentation:** https://github.com/tronikos/androidtvremote2

**Example Usage:**
```python
from androidtvremote2 import AndroidTVRemote

# Connect to TV
tv = AndroidTVRemote("192.168.1.50", "SmartVenue")

# Pair (one-time, shows code on TV)
await tv.async_connect()
pairing_code = "1234"  # User enters from TV screen
await tv.async_pair(pairing_code)

# Send commands
await tv.send_key_command("KEYCODE_POWER")
await tv.send_key_command("KEYCODE_VOLUME_UP")
await tv.send_key_command("KEYCODE_DPAD_CENTER")

# Get status
is_on = await tv.is_on()
current_app = await tv.get_current_app()
```

### 2. `androidtv` (Alternative - ADB-based)

**Install:**
```bash
pip install androidtv
```

**Features:**
- ADB over network
- State detection (on/off, current app, volume)
- Command execution
- App launching

**Documentation:** https://github.com/JeffLIrion/python-androidtv

**Example Usage:**
```python
from androidtv import AndroidTV

# Connect via ADB
tv = AndroidTV("192.168.1.50")
tv.connect()

# Send commands
tv.key("POWER")
tv.key("VOLUME_UP")

# Get status
state = tv.get_state()  # "on", "off", "standby"
current_app = tv.get_current_app()
```

---

## Capabilities Comparison

| Feature | CHiQ (Android TV Remote) | CHiQ (ADB) | Hisense (VIDAA) | LG webOS | Sony Bravia |
|---------|-------------------------|------------|-----------------|----------|-------------|
| **Power State** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Volume Level** | ⚠️ Limited | ⚠️ Limited | ✅ Yes | ✅ Yes | ✅ Yes |
| **Mute Status** | ⚠️ Limited | ⚠️ Limited | ✅ Yes | ✅ Yes | ✅ Yes |
| **Current App** | ✅ Yes | ✅ Yes | ⚠️ Limited | ✅ Yes | ⚠️ Limited |
| **Current Input** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Power-On** | ⚠️ WOL | ⚠️ WOL | ⚠️ WOL | ⚠️ WOL | ⚠️ WOL |
| **Setup Complexity** | Medium | High | Low | Medium | Medium |
| **Auth Required** | Pairing | Developer mode | Default creds | Pairing | PSK |

---

## Implementation Plan

### Step 1: Create CHiQ Executor

**File:** `backend/app/commands/executors/network/chiq.py`

```python
"""
CHiQ TV Executor
Uses Android TV Remote Protocol v2
"""

import asyncio
from typing import Optional
from androidtvremote2 import AndroidTVRemote

from ..base import CommandExecutor
from ...models import Command, ExecutionResult


class CHiQExecutor(CommandExecutor):
    """
    Executor for CHiQ TVs (Android TV)

    Protocol: Android TV Remote v2
    Port: 6466 (control), 6467 (pairing)
    Authentication: Pairing required (one-time)
    """

    KEY_MAP = {
        "power": "KEYCODE_POWER",
        "power_on": "KEYCODE_POWER",  # No discrete power-on
        "power_off": "KEYCODE_POWER",
        "volume_up": "KEYCODE_VOLUME_UP",
        "volume_down": "KEYCODE_VOLUME_DOWN",
        "mute": "KEYCODE_MUTE",
        "up": "KEYCODE_DPAD_UP",
        "down": "KEYCODE_DPAD_DOWN",
        "left": "KEYCODE_DPAD_LEFT",
        "right": "KEYCODE_DPAD_RIGHT",
        "ok": "KEYCODE_DPAD_CENTER",
        "enter": "KEYCODE_DPAD_CENTER",
        "back": "KEYCODE_BACK",
        "home": "KEYCODE_HOME",
        "menu": "KEYCODE_MENU",
        # ... 50+ more commands
    }

    def can_execute(self, command: Command) -> bool:
        return (
            command.device_type == "network_tv" and
            command.protocol == "chiq_android"
        )

    async def execute(self, command: Command) -> ExecutionResult:
        """Execute command on CHiQ TV"""
        start_time = time.time()

        try:
            # Get pairing certificate from connection_config
            pairing_cert = None
            if command.connection_config:
                pairing_cert = command.connection_config.get("pairing_certificate")

            if not pairing_cert:
                return ExecutionResult(
                    success=False,
                    message="CHiQ TV not paired. Please pair first.",
                    error="NOT_PAIRED"
                )

            # Connect to TV
            tv = AndroidTVRemote(command.ip_address, "SmartVenue")
            tv.certificate = pairing_cert

            await tv.async_connect()

            # Map command to keycode
            keycode = self.KEY_MAP.get(command.command)
            if not keycode:
                return ExecutionResult(
                    success=False,
                    message=f"Unknown command: {command.command}",
                    error="UNKNOWN_COMMAND"
                )

            # Send keycode
            await tv.send_key_command(keycode)

            execution_time_ms = int((time.time() - start_time) * 1000)

            return ExecutionResult(
                success=True,
                message=f"CHiQ TV command {command.command} sent",
                data={
                    "execution_time_ms": execution_time_ms,
                    "device": command.device_name,
                    "protocol": "android_tv_remote_v2",
                    "keycode": keycode
                }
            )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                message=f"CHiQ TV command failed: {str(e)}",
                error="COMMAND_FAILED",
                data={
                    "execution_time_ms": execution_time_ms,
                    "error_detail": str(e)
                }
            )
```

### Step 2: Add Pairing Endpoint

**File:** `backend/app/routers/chiq_pairing.py`

```python
"""
CHiQ TV Pairing API
Handles Android TV Remote v2 pairing
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from androidtvremote2 import AndroidTVRemote

router = APIRouter(prefix="/chiq-pairing", tags=["chiq-pairing"])


class PairingStartRequest(BaseModel):
    ip_address: str
    device_name: str


class PairingCodeRequest(BaseModel):
    ip_address: str
    pairing_code: str


@router.post("/start")
async def start_pairing(request: PairingStartRequest):
    """
    Start pairing with CHiQ TV

    This will show a 4-digit code on the TV screen
    User must enter this code to complete pairing
    """
    try:
        tv = AndroidTVRemote(request.ip_address, "SmartVenue")
        await tv.async_connect()

        # Pairing code will be shown on TV screen
        # User needs to enter it in next step

        return {
            "success": True,
            "message": "Pairing started. Check TV screen for 4-digit code.",
            "ip_address": request.ip_address,
            "device_name": request.device_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complete")
async def complete_pairing(request: PairingCodeRequest):
    """
    Complete pairing with CHiQ TV

    User provides the 4-digit code shown on TV screen
    Returns pairing certificate to store in database
    """
    try:
        tv = AndroidTVRemote(request.ip_address, "SmartVenue")
        await tv.async_connect()
        await tv.async_pair(request.pairing_code)

        # Get certificate to store
        certificate = tv.certificate

        return {
            "success": True,
            "message": "Pairing successful!",
            "pairing_certificate": certificate,
            "ip_address": request.ip_address
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Pairing failed: {str(e)}")
```

### Step 3: Update Router

**File:** `backend/app/commands/router.py`

```python
# Add import
from .executors.network import CHiQExecutor

# Add to get_executor():
elif command.protocol == "chiq_android":
    return CHiQExecutor(self.db)
```

### Step 4: Add to Status Poller

**File:** `backend/app/services/tv_status_poller.py`

```python
async def _poll_chiq(self, device: VirtualDevice) -> Optional[Dict[str, Any]]:
    """Poll CHiQ (Android TV) for status"""
    try:
        from androidtvremote2 import AndroidTVRemote

        # Get pairing certificate
        pairing_cert = None
        if device.connection_config and isinstance(device.connection_config, dict):
            pairing_cert = device.connection_config.get("pairing_certificate")

        if not pairing_cert:
            return None

        tv = AndroidTVRemote(device.ip_address, "SmartVenue")
        tv.certificate = pairing_cert
        await tv.async_connect()

        # Get status
        is_on = await tv.is_on()
        current_app = await tv.get_current_app()

        return {
            "power": "on" if is_on else "off",
            "volume": None,  # Android TV Remote v2 doesn't provide volume query
            "muted": None,
            "input": None,
            "app": current_app
        }

    except Exception as e:
        logger.debug(f"CHiQ poll failed: {e}")
        return None
```

---

## Setup Instructions for Users

### Step 1: Ensure TV is on Network

CHiQ TV must be connected to the same network as SmartVenue:
- Connect via WiFi (2.4 GHz only) or Ethernet

### Step 2: Pair with TV

1. In SmartVenue, click "Add CHiQ TV"
2. Enter TV IP address
3. Click "Start Pairing"
4. **TV will show 4-digit code on screen**
5. Enter code in SmartVenue
6. Click "Complete Pairing"
7. Pairing certificate stored automatically

### Step 3: Test Commands

- Power toggle
- Volume up/down
- Navigation (up/down/left/right/OK)

---

## Comparison with Other Brands

### CHiQ vs Hisense

| Feature | CHiQ (Android TV) | Hisense (VIDAA) |
|---------|-------------------|-----------------|
| OS | Android TV | VIDAA OS |
| Protocol | Android TV Remote v2 | MQTT |
| Pairing | Required (one-time) | Optional |
| Volume Query | ❌ No | ✅ Yes |
| App Detection | ✅ Yes | ⚠️ Limited |
| Setup Complexity | Medium | Low |

### CHiQ vs Generic Android TV

CHiQ TVs ARE Android TVs, so they work identically to any other Android TV device (Sony, TCL, Philips Android models, etc.)

---

## Power-On Capability

**WOL (Wake-on-LAN):** ⚠️ **May work, but unreliable**

Like most Android TVs, CHiQ TVs may support WOL if:
1. TV is in standby (not fully powered off)
2. Network adapter stays powered in standby
3. WOL setting enabled in TV network settings

**Recommendation:** Use **hybrid approach** - link IR controller for reliable power-on, use network for everything else.

---

## Implementation Estimate

### Backend (3-4 hours)
- ✅ Create CHiQ executor (~1 hour)
- ✅ Add pairing endpoints (~1 hour)
- ✅ Update router and status poller (~30 min)
- ✅ Add to requirements.txt (~5 min)
- ✅ Test with mock connection (~1 hour)
- ✅ Documentation (~30 min)

### Frontend (2-3 hours)
- ✅ Pairing flow UI (~1 hour)
- ✅ Add CHiQ to brand selector (~30 min)
- ✅ Update brand info cards (~30 min)
- ✅ Test pairing UI (~1 hour)

**Total:** 5-7 hours

---

## Dependencies

### Add to requirements.txt:
```
androidtvremote2>=0.0.14
```

Optional (if using ADB approach):
```
androidtv>=0.0.73
```

---

## Testing Checklist

### With Real CHiQ TV:
- [ ] Discover CHiQ TV on network
- [ ] Start pairing process
- [ ] Enter 4-digit code from TV screen
- [ ] Complete pairing successfully
- [ ] Test power toggle
- [ ] Test volume up/down
- [ ] Test navigation commands
- [ ] Test app launching
- [ ] Verify pairing persists across restarts
- [ ] Test status polling (power state, current app)

### Without Real TV (Mock):
- [ ] Unit tests for CHiQ executor
- [ ] Mock pairing flow
- [ ] Mock command execution
- [ ] Error handling tests

---

## Potential Issues & Solutions

### Issue 1: Pairing Fails

**Cause:** TV firewall blocking port 6466/6467

**Solution:**
- Check TV is on same network
- Restart TV
- Check no VPN or network isolation

### Issue 2: Commands Not Working After Pairing

**Cause:** Pairing certificate not stored

**Solution:**
- Store certificate in `connection_config` JSON field
- Verify certificate is passed to executor

### Issue 3: TV Not Responding

**Cause:** TV in deep sleep

**Solution:**
- Wake TV manually first
- Or use IR power-on (hybrid approach)

---

## Next Steps

1. **Add CHiQ Executor** (1 hour)
   - Create `chiq.py` executor file
   - Implement Android TV Remote v2 protocol
   - Add key mapping (50+ keys)

2. **Add Pairing Endpoints** (1 hour)
   - Create pairing router
   - Start/complete pairing flow
   - Store certificate in database

3. **Update Frontend** (2 hours)
   - Add CHiQ to brand selector
   - Create pairing flow UI
   - Update brand info cards

4. **Test with Real TV** (1 hour)
   - If you have access to CHiQ TV
   - Test pairing and commands
   - Document any quirks

5. **Update Documentation** (30 min)
   - Add CHiQ to SUPPORTED_NETWORK_TVS.md
   - Add setup instructions
   - Update comparison matrix

---

## Recommendation

**✅ PROCEED WITH IMPLEMENTATION**

CHiQ TVs use standard Android TV protocols, making them easy to add with existing Python libraries. The pairing process is similar to LG webOS (one-time, user-friendly).

**Benefits:**
- ✅ Large market (budget TV segment)
- ✅ Standard Android TV protocol (well documented)
- ✅ Existing Python library (androidtvremote2)
- ✅ No developer mode required
- ✅ Similar to LG webOS UX (pairing-based)

**This would bring our total to 8 supported brands!** 🎉

---

**Status:** Ready to implement when you want to add CHiQ support!

🤖 Generated with [Claude Code](https://claude.com/claude-code)
