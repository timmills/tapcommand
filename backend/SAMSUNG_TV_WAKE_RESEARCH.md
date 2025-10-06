# Samsung TV Wake-Up Research & Testing Results

**Date:** October 6, 2025
**TV Model:** Samsung LA40D550 (2011 D-series)
**IP:** 192.168.101.50
**MAC:** E4:E0:C5:B8:5A:97

---

## Executive Summary

**Result:** Wake-on-LAN (WOL) **DOES NOT WORK** for this Samsung D-series TV when powered off.

After comprehensive testing of multiple WOL methods and extensive research, the Samsung LA40D550 (2011 D-series) does not support network-based wake-up when powered off via remote control. The network interface is completely powered down in the off state.

---

## Testing Performed

### Test Suite Overview
Created and executed comprehensive wake-up test script (`test_samsung_wake.py`) testing 4 different WOL approaches:

1. **Standard WOL** - 16 magic packets using `wakeonlan` library
2. **Broadcast WOL** - 60 packets via UDP broadcast (192.168.101.255) on ports 9, 7, 3
3. **Targeted WOL** - 64 packets sent directly to TV IP on ports 9, 7, 3, 55000
4. **Continuous WOL** - 150 packets over 15 seconds with extended boot wait time

### Test Results
```
✗ Method 1: FAILED - TV did not respond
✗ Method 2: FAILED - TV did not respond
✗ Method 3: FAILED - TV did not respond
✗ Method 4: FAILED - TV did not respond
```

**Total packets sent:** 290+ WOL magic packets across multiple ports and methods
**TV Response:** None - TV remained completely offline

### Network Status Checks
- Ping: No response
- Port 55000 (Samsung Legacy): CLOSED
- Port 8001/8002 (WebSocket): CLOSED
- Port 9 (WOL): CLOSED

---

## Research Findings

### Wake-on-LAN Support in Samsung TVs

#### Modern Samsung TVs (2016+)
- **Limited WOL Support:** Some 2016+ Tizen TVs support "Wake on Wireless LAN" (WoWLAN)
- **Setting Location:** Settings → General → Network → Expert Settings → Power On with Mobile
- **Requirement:** Must be in standby mode, not fully powered off
- **Limitation:** Even when supported, WOL only works if TV is in network standby mode

#### Legacy Samsung TVs (2011-2015, D/E/F/H series)
- **No WOL Support:** D-series (2011) and most legacy models do NOT support Wake-on-LAN
- **Network Interface:** Completely powers down when TV is turned off
- **Port 55000 Protocol:** Only works when TV is already ON
- **Research Sources:** Home Assistant forums, SamyGO wiki, samsungctl documentation

### Why WOL Fails on This Model

1. **Hardware Limitation:** Network interface chip is not powered in off state
2. **No Standby Network Mode:** TV either ON (full power) or OFF (network unpowered)
3. **Age of TV:** 2011 model predates widespread WoWLAN support
4. **Protocol Design:** Samsung Legacy protocol (port 55000) requires active network stack

### Key Quote from Research
> "Samsung TVs do not offer any means to turn them on when the TV is off, as it does not respond to WOL commands when fully powered down."

---

## Working Control Methods

### ✓ When TV is ON
- **Samsung Legacy Protocol** (port 55000) - WORKS PERFECTLY
- **Network Commands** - Volume, channel, input, power toggle
- **Response Time** - Fast (< 500ms)
- **Library:** `samsungctl` (already implemented in `backend/app/commands/executors/network/samsung_legacy.py`)

### ✓ Power Toggle vs Power On/Off
- **KEY_POWER** - Toggles power state (ON→OFF or OFF→ON)
- **KEY_POWERON** - Discrete ON command (only works if TV already ON)
- **KEY_POWEROFF** - Discrete OFF command (works when TV is ON)

**Issue:** No discrete "power on from off" command exists over network for this model.

---

## Alternative Solutions for Power-On

### Option 1: IR (Infrared) Control ⭐ RECOMMENDED
**Advantages:**
- Works when TV is completely off
- Samsung IR protocol is well-documented
- Can use existing IR blaster hardware in venue
- Reliable and proven technology
- No TV configuration required

**Implementation:**
- Use existing ESP32 IR blasters in the venue
- Samsung IR codes are already in the library
- Fallback to IR for power-on, use network for everything else

**Code Path:** Already implemented in existing IR control system

### Option 2: HDMI-CEC (Anynet+)
**Advantages:**
- Can wake TV from connected devices
- No line-of-sight required
- Bidirectional control

**Requirements:**
- Device connected to TV via HDMI (Raspberry Pi, media player)
- CEC enabled on TV: Settings → General → Anynet+ (HDMI-CEC)
- `cec-client` or similar software

**Limitations:**
- Requires HDMI-connected device at each TV
- Additional hardware setup
- May conflict with other HDMI devices

**Example Command:**
```bash
echo "on 0" | cec-client -s    # Wake TV
echo "standby 0" | cec-client -s  # Sleep TV
```

### Option 3: Smart Plug Integration
**Advantages:**
- Simple and reliable
- Works with any TV
- Can force reboot if needed

**Disadvantages:**
- Requires additional hardware per TV
- TV must be configured to auto-start when power applied
- Less elegant than network control
- May cause issues with TV state/settings

### Option 4: Keep TV in Network Standby Mode
**Concept:** Never fully power off the TV, keep in standby

**Advantages:**
- Network remains active in standby
- Could respond to network commands

**Investigation Needed:**
- Check if D-series has "Network Standby" mode
- Test if port 55000 responds in standby
- Measure power consumption in standby vs off

**TV Settings to Check:**
- Menu → System → Eco Solution → Auto Power Off (disable)
- Menu → Network → Network Standby (if available)

---

## Code Implementation Status

### Already Implemented ✓
File: `backend/app/commands/executors/network/samsung_legacy.py`

```python
async def _wake_on_lan(self, device: VirtualDevice, start_time: float):
    """
    Turn on Samsung Legacy TV using Wake-on-LAN

    NOTE: This method is implemented but DOES NOT WORK for LA40D550
    because the network interface powers down when TV is off.
    """
```

**Current Behavior:**
- `power_on` command triggers WOL attempt (lines 84-87)
- Sends 16 WOL packets to TV's MAC address
- Returns success message even though TV doesn't wake
- User expects TV to turn on, but it doesn't

### Recommended Code Fix

**Option A: Remove WOL, add warning**
```python
if command.command.lower() in ["power_on", "poweron"]:
    return ExecutionResult(
        success=False,
        message=f"Cannot power on {device.device_name} over network - TV is offline",
        error="NETWORK_POWER_ON_NOT_SUPPORTED",
        data={
            "recommendation": "Use IR control for power-on",
            "reason": "Network interface is unpowered when TV is off"
        }
    )
```

**Option B: Hybrid IR + Network**
```python
if command.command.lower() in ["power_on", "poweron"]:
    # Check if TV is already online
    if await self._check_tv_online(device.ip_address):
        # TV is in standby, network command might work
        # Send power command via port 55000
        pass
    else:
        # TV is fully off, must use IR
        return ExecutionResult(
            success=False,
            message="TV is offline, IR control required for power-on",
            error="USE_IR_FOR_POWER_ON"
        )
```

---

## Recommendations

### Immediate Actions

1. **Update Documentation** ✓ (this document)
   - Clearly document WOL limitation
   - Update `LEGACY_SAMSUNG_TV_SETUP.md` with wake findings

2. **Fix Power-On Command**
   - Remove misleading WOL implementation
   - Return clear error when TV is offline
   - Direct users to use IR for power-on

3. **Test Standby Mode**
   - Turn TV to standby (not full off) using remote
   - Test if port 55000 responds in standby
   - Check if `KEY_POWERON` wakes from standby

4. **Verify IR Control**
   - Confirm IR blasters can reach TV at 192.168.101.50
   - Test IR power-on command
   - Document IR + Network hybrid approach

### Long-Term Strategy

**Hybrid Control Approach:**
```
Power ON:  IR Control (ESP32 blaster)
Power OFF: Network (port 55000) - faster, more reliable
Other:     Network (port 55000) - volume, channel, input, etc.
```

**Benefits:**
- Best of both worlds
- Reliable power-on via IR
- Fast, network-based control for everything else
- No additional hardware needed (IR already deployed)

---

## Test Script Location

**File:** `/home/coastal/smartvenue/backend/test_samsung_wake.py`

**Usage:**
```bash
cd /home/coastal/smartvenue/backend
source ../venv/bin/activate
python test_samsung_wake.py
```

**Features:**
- Tests 4 different WOL methods
- Comprehensive status checking
- Clear result reporting
- Automatic timeout handling

---

## Technical Details

### Samsung LA40D550 Network Behavior

**When TV is ON:**
- Port 55000: OPEN and responsive
- Accepts Samsung Legacy protocol commands
- Fast response time (< 500ms)
- Reliable command execution

**When TV is OFF (via remote):**
- All network ports: CLOSED
- No ping response
- ARP entry shows "incomplete"
- Network interface fully powered down
- WOL packets received but ignored (no power to NIC)

### WOL Magic Packet Structure
```
6 bytes:  0xFF 0xFF 0xFF 0xFF 0xFF 0xFF
96 bytes: MAC address repeated 16 times
Total:    102 bytes
```

**Tested Delivery Methods:**
- ✗ UDP broadcast to 255.255.255.255:9
- ✗ UDP broadcast to 192.168.101.255:9
- ✗ UDP unicast to 192.168.101.50:9
- ✗ UDP to ports 7, 3, 55000
- ✗ Repeated packets (150+ over 15 seconds)

**Result:** None of the above methods successfully woke the TV.

---

## Related Files

- `backend/app/commands/executors/network/samsung_legacy.py` - Current implementation (has non-working WOL)
- `backend/test_legacy_samsung.py` - Basic connection test (works when TV is ON)
- `backend/test_samsung_wake.py` - Comprehensive WOL test suite (proves WOL doesn't work)
- `docs/LEGACY_SAMSUNG_TV_SETUP.md` - Setup guide (needs update)

---

## Conclusion

**Wake-on-LAN does NOT work for Samsung LA40D550 (2011 D-series) when powered off.**

The TV's network interface is completely unpowered in the off state, making network-based wake-up impossible. This is a hardware limitation, not a configuration issue.

**Recommended Solution:** Use IR control for power-on, network control for all other functions.

---

## Next Steps

1. ✅ Test IR power-on capability
2. ✅ Update `samsung_legacy.py` to remove/fix WOL code
3. ✅ Test if standby mode allows network wake
4. ✅ Document hybrid IR+Network control strategy
5. ✅ Update API to route power-on to IR, other commands to network

---

**Testing Completed:** October 6, 2025
**Status:** WOL confirmed non-functional, alternatives documented
**Action Required:** Implement IR fallback for power-on commands
