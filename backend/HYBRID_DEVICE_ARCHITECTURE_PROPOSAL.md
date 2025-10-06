# Hybrid IR + Network TV Control - Architecture Proposal

**Date:** October 7, 2025
**Status:** Design Proposal
**Problem:** Network-controlled TVs cannot power ON reliably (except Roku), but network control is superior once TV is ON

---

## Executive Summary

### The Problem
We've implemented network control for 7 TV brands, but discovered a critical limitation:
- **Samsung Legacy TVs:** Cannot power ON via network (WOL fails, network interface powered down)
- **Hisense, LG, Sony, Philips:** WOL unreliable or non-existent
- **Only Roku:** Can power ON via network reliably

This means users still need IR for power-on, but we want network control for everything else.

### The Question
**Should we:**
1. **Go back to IR-only?** (Simplest, but loses network benefits)
2. **Hybrid approach:** Combine IR controller + Network controller into one "logical device"?
3. **Network-only with limitations?** (Document that power-on requires manual intervention)

---

## Recommendation: Hybrid Device Architecture ✅

**Best approach:** Allow users to associate an IR controller port with a Network TV to create a "hybrid device" that:
- Uses **IR for power-on** (reliable, always works)
- Uses **Network for everything else** (faster, status feedback, no line-of-sight)
- Presents as **single device** to the user
- Provides **fallback to IR** if network fails

---

## Comparison Matrix

| Approach | User Experience | Setup Complexity | Reliability | Future-Proof |
|----------|----------------|------------------|-------------|--------------|
| **IR-Only** | Simple, works everywhere | Easy | 98%+ | Limited (no apps, no status) |
| **Network-Only** | Fast, rich features | Medium-High | 85-99% | Best (apps, status, no IR hardware) |
| **Hybrid (RECOMMENDED)** | Best of both | Medium | 98%+ | Best (graceful degradation) |

---

## Detailed Architecture Design

### 1. Database Schema Changes

#### Option A: Add `fallback_ir_port` to VirtualDevice (Simple)

**Modify `app/models/virtual_controller.py`:**

```python
class VirtualDevice(Base):
    """Virtual Device with optional IR fallback"""
    __tablename__ = "virtual_devices"

    # ... existing fields ...

    # Hybrid control support
    fallback_ir_controller = Column(String, nullable=True)  # hostname of IR controller (e.g., "ir-abc123")
    fallback_ir_port = Column(Integer, nullable=True)  # port number (0-4) on IR controller

    # Control strategy
    control_strategy = Column(String, default="network_only")  # "network_only", "hybrid_ir_fallback", "ir_only"
    power_on_method = Column(String, default="network")  # "network", "ir", "hybrid"
```

**Pros:**
- ✅ Minimal schema changes
- ✅ Each network TV optionally linked to IR port
- ✅ Backward compatible (nullable fields)

**Cons:**
- ⚠️ IR controller and network TV treated as separate devices
- ⚠️ User sees two devices in UI (though could hide IR)

---

#### Option B: Unified Device Model (Complex but cleaner)

**Create new `UnifiedDevice` table:**

```python
class UnifiedDevice(Base):
    """Unified device that may have multiple control methods"""
    __tablename__ = "unified_devices"

    id = Column(Integer, primary_key=True)
    device_name = Column(String, nullable=False)  # "Main Bar Samsung TV"
    device_type = Column(String, nullable=False)  # "tv", "set_top_box", "projector"

    # Location
    venue_name = Column(String, nullable=True)
    location = Column(String, nullable=True)

    # Control methods (JSON array)
    control_methods = Column(JSON, nullable=False)
    # Example:
    # [
    #   {"type": "network", "protocol": "samsung_legacy", "ip": "192.168.1.50", "mac": "AA:BB:CC:DD:EE:FF", "priority": 1},
    #   {"type": "ir", "controller": "ir-abc123", "port": 2, "priority": 2}
    # ]

    # Strategy
    power_on_strategy = Column(String, default="auto")  # "auto", "network_only", "ir_only", "network_then_ir"
    control_strategy = Column(String, default="auto")   # "auto", "prefer_network", "prefer_ir"

    # Tags
    tag_ids = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

**Pros:**
- ✅ Clean user experience (one device, multiple control methods)
- ✅ Flexible (can add more control methods later: HDMI-CEC, HTTP, etc.)
- ✅ Strategy-based routing (automatic or user-defined)

**Cons:**
- ⚠️ Major schema change
- ⚠️ Requires migration of existing data
- ⚠️ More complex to implement

---

### 2. Command Routing Logic

#### Hybrid Routing Strategy

```python
class HybridCommandRouter:
    """
    Routes commands using hybrid strategy:
    - Power-on: Try network (if WOL enabled), fallback to IR
    - Power-off: Prefer network (faster, status confirmation)
    - All other: Prefer network, fallback to IR if network fails
    """

    async def execute_command(self, device: UnifiedDevice, command: str) -> ExecutionResult:
        control_methods = sorted(device.control_methods, key=lambda x: x['priority'])

        # Special handling for power-on
        if command == "power_on":
            return await self._execute_power_on(device, control_methods)

        # For all other commands, try in priority order
        for method in control_methods:
            result = await self._try_method(device, command, method)
            if result.success:
                return result

            # If network fails, log and try next method
            logger.warning(f"Method {method['type']} failed for {device.device_name}, trying next...")

        # All methods failed
        return ExecutionResult(success=False, error="ALL_METHODS_FAILED")

    async def _execute_power_on(self, device: UnifiedDevice, methods: list) -> ExecutionResult:
        """
        Power-on strategy:
        1. If device has network + WOL capability: try WOL
        2. If WOL fails or not available: use IR
        3. Wait for device to boot (5-15 seconds)
        4. Verify device is on (network ping or status check)
        """
        power_on_strategy = device.power_on_strategy

        if power_on_strategy == "ir_only":
            return await self._power_on_via_ir(device)

        if power_on_strategy == "network_only":
            return await self._power_on_via_network(device)

        # Auto strategy: try network, fallback to IR
        result = await self._power_on_via_network(device)
        if not result.success:
            logger.info(f"Network power-on failed for {device.device_name}, falling back to IR")
            result = await self._power_on_via_ir(device)

        return result
```

---

### 3. User Interface Changes

#### Device Management UI

**Show unified device with multiple control methods:**

```
┌─────────────────────────────────────────────────────────┐
│ 📺 Main Bar Samsung TV                                   │
│ Location: Main Bar                                       │
├─────────────────────────────────────────────────────────┤
│ Control Methods:                                        │
│                                                          │
│ ✅ Network Control (Primary)                            │
│    Protocol: Samsung Legacy                             │
│    IP: 192.168.101.50                                   │
│    Status: Online                                       │
│    Response Time: 250ms                                 │
│                                                          │
│ ✅ IR Control (Fallback)                                │
│    Controller: ir-abc123 (Main Bar IR)                  │
│    Port: 2                                              │
│    Status: Online                                       │
│                                                          │
│ Power-On Strategy: [Auto ▼]                             │
│   • Auto (Network → IR fallback)                        │
│   • Network Only                                        │
│   • IR Only                                             │
│                                                          │
│ [Test Network] [Test IR] [Configure]                    │
└─────────────────────────────────────────────────────────┘
```

#### During Device Setup

**Flow for network TV adoption:**

```
1. Discover TV on network
   ↓
2. Adopt as Network Controller
   ↓
3. [Optional] "Would you like to add IR fallback for power-on?"
   ↓
   If YES:
   4a. Select existing IR controller
   4b. Select which port (1-5)
   4c. Test IR power command
   4d. Link IR port to Network TV
   ↓
5. Save hybrid device configuration
```

---

### 4. API Design

#### New Endpoints

**Link IR fallback to network TV:**
```http
POST /api/virtual-controllers/{controller_id}/link-ir-fallback
{
  "ir_controller_hostname": "ir-abc123",
  "ir_port": 2,
  "power_on_method": "ir",  // "ir", "network", "hybrid"
  "test_before_link": true
}
```

**Unlink IR fallback:**
```http
DELETE /api/virtual-controllers/{controller_id}/unlink-ir-fallback
```

**Get device control status:**
```http
GET /api/devices/{device_id}/control-status
Response:
{
  "device_name": "Main Bar Samsung TV",
  "control_methods": [
    {
      "type": "network",
      "status": "online",
      "last_success": "2025-10-07T10:30:00Z",
      "response_time_ms": 245,
      "capabilities": ["power_off", "volume", "channels", "inputs"]
    },
    {
      "type": "ir",
      "status": "online",
      "last_success": "2025-10-07T09:15:00Z",
      "capabilities": ["power_on", "power_off", "volume", "channels"]
    }
  ],
  "current_strategy": "hybrid_ir_fallback",
  "power_on_recommendation": "ir"
}
```

---

### 5. Command Execution Flow

#### Example: Power-On Command

```python
# User clicks "Power On" for Main Bar Samsung TV

# Step 1: Get device configuration
device = db.get_unified_device("Main Bar Samsung TV")
# device.control_methods = [
#   {"type": "network", "protocol": "samsung_legacy", "ip": "192.168.1.50", ...},
#   {"type": "ir", "controller": "ir-abc123", "port": 2}
# ]
# device.power_on_strategy = "auto"  # Try network, fallback to IR

# Step 2: Route command
router = HybridCommandRouter(db)
result = await router.execute_command(device, "power_on")

# Step 3: Execution
# → Try WOL (Samsung Legacy doesn't support, skip)
# → Try IR power-on via ir-abc123 port 2
# → IR succeeds in 180ms
# → Wait 10 seconds for TV to boot
# → Verify network is available (ping 192.168.1.50)
# → Return success

# Result:
{
  "success": true,
  "method": "ir_fallback",
  "message": "TV powered on via IR (network WOL not supported)",
  "execution_time_ms": 180,
  "boot_wait_ms": 10000
}
```

#### Example: Volume Up Command

```python
# User clicks "Volume Up" for Main Bar Samsung TV

# Step 1: Route command with "auto" strategy
result = await router.execute_command(device, "volume_up")

# Step 2: Try network first (priority 1)
# → Send Samsung Legacy network command
# → Success in 245ms

# Result:
{
  "success": true,
  "method": "network",
  "message": "Volume up sent via Samsung Legacy protocol",
  "execution_time_ms": 245
}

# If network failed:
# → Fallback to IR controller
# → Send IR volume_up command
# → Success in 120ms
```

---

## Implementation Roadmap

### Phase 1: Simple Hybrid (Recommended Starting Point)

**Time Estimate:** 2-3 days

1. **Database Changes** (2 hours)
   - Add `fallback_ir_controller` and `fallback_ir_port` to `VirtualDevice`
   - Add `power_on_method` field
   - Run migration

2. **Backend Logic** (1 day)
   - Modify command router to check for IR fallback
   - Implement power-on logic (try network, fallback to IR)
   - Add API endpoints for linking/unlinking IR

3. **Frontend UI** (1 day)
   - Add "Link IR Fallback" button during TV adoption
   - Show IR fallback status in device details
   - Add power-on method selector

4. **Testing** (4 hours)
   - Test hybrid power-on flow
   - Test fallback when network fails
   - Test with real Samsung TV

**Deliverables:**
- ✅ Network TVs can have optional IR fallback
- ✅ Power-on uses IR when network WOL unavailable
- ✅ User sees single device with two control methods

---

### Phase 2: Advanced Hybrid (Future Enhancement)

**Time Estimate:** 1-2 weeks

1. **Unified Device Model** (3 days)
   - Create `UnifiedDevice` table
   - Migrate existing devices
   - Support multiple control methods per device

2. **Smart Routing** (2 days)
   - Implement strategy-based routing
   - Add health checking for control methods
   - Auto-failover when method fails

3. **Enhanced UI** (3 days)
   - Control method dashboard
   - Real-time status for each method
   - Strategy configuration UI
   - Execution history per method

4. **Analytics** (2 days)
   - Track success rate per method
   - Response time tracking
   - Automatic method priority adjustment

---

## Alternative: IR-Only (Fallback Plan)

### When to use IR-Only?

If hybrid approach proves too complex, we can revert to IR-only:

**Pros:**
- ✅ Simplest approach
- ✅ Works for ALL TVs (even non-network)
- ✅ No authentication/pairing required
- ✅ 98%+ reliability

**Cons:**
- ❌ No status feedback (blind commands)
- ❌ Requires line-of-sight
- ❌ Cannot launch apps or get TV state
- ❌ Slower than network (sometimes)

**Verdict:** Only use if hybrid proves too problematic. Network control benefits are significant.

---

## Alternative: Network-Only with Documented Limitations

### When to use Network-Only?

For venues where:
- Staff manually powers on TVs in the morning
- TVs never fully power off (standby mode only)
- Only Roku TVs deployed (network power-on works)

**Implementation:**
- Document that power-on requires manual intervention
- Focus on Roku TVs for new deployments
- Use network control for everything except power-on

**Pros:**
- ✅ Simpler than hybrid
- ✅ Best performance (network is faster for most commands)
- ✅ Rich features (status, apps, inputs)

**Cons:**
- ❌ Power-on limitation frustrating for users
- ❌ Not suitable for unmanned venues
- ❌ Requires TV to stay in standby

---

## Cost-Benefit Analysis

### Hybrid Approach (Recommended)

**Development Cost:** 2-3 days (Phase 1) or 1-2 weeks (Phase 2)

**User Benefits:**
- ✅ Reliable power-on (IR)
- ✅ Fast network commands (250-500ms)
- ✅ Status feedback from network
- ✅ Fallback if network fails
- ✅ Best user experience

**Business Value:**
- Higher customer satisfaction
- Competitive advantage (best of both worlds)
- Future-proof (can add more control methods)

---

### IR-Only

**Development Cost:** Negative (remove network TV code)

**User Benefits:**
- ✅ Simple, works everywhere

**Business Value:**
- Lower complexity
- Easier support
- BUT: Limited features compared to competitors

---

### Network-Only

**Development Cost:** 0 (current implementation)

**User Benefits:**
- ✅ Fast, rich features
- ❌ Power-on limitation

**Business Value:**
- Works for specific use cases
- NOT suitable for general deployment

---

## Recommendation Summary

### Go with: **Hybrid Approach - Phase 1**

**Why:**
1. **Solves power-on problem** without losing network benefits
2. **Relatively simple** to implement (2-3 days)
3. **Backward compatible** (optional feature)
4. **Best user experience** (reliable + fast)
5. **Future-proof** (can evolve to Phase 2)

### Implementation Priority:
1. Start with Phase 1 (simple hybrid)
2. Test with Samsung Legacy TVs (worst case for WOL)
3. If successful, consider Phase 2 for richer features
4. Keep IR-only as fallback if hybrid proves problematic

---

## Technical Decisions Required

### 1. Schema Approach

**Question:** Add fields to `VirtualDevice` (Option A) or create `UnifiedDevice` (Option B)?

**Recommendation:** Start with Option A (simpler), migrate to Option B if needed.

---

### 2. User Interface Flow

**Question:** Should linking IR fallback be:
- Required during network TV adoption?
- Optional step after adoption?
- Automatic (system suggests based on TV brand)?

**Recommendation:** Optional but suggested. Show warning during adoption:

```
⚠️ Samsung Legacy TVs cannot power ON via network.
Would you like to link an IR controller for power-on? [Yes] [Skip]
```

---

### 3. Command Routing Priority

**Question:** When both methods available, which to use?

**Recommendation:**
- **Power-on:** Always IR (unless Roku or user overrides)
- **Power-off:** Network (faster, confirmation)
- **Volume/Channels:** Network (faster, no IR line-of-sight)
- **If network fails:** Auto-fallback to IR

---

### 4. Fallback Timeout

**Question:** How long to wait before falling back to IR?

**Recommendation:**
- **Network command timeout:** 5 seconds
- **If timeout:** Immediately try IR
- **Total max time:** 10 seconds (user feedback)

---

## Next Steps

1. **User Decision:** Choose between Hybrid, IR-Only, or Network-Only
2. **If Hybrid chosen:**
   - Approve Phase 1 implementation plan
   - Decide on schema approach (Option A recommended)
   - Define UI flow for linking IR fallback
3. **Implementation:**
   - Database migration
   - Backend router logic
   - Frontend UI updates
   - Testing with real TVs

---

## Appendices

### A. Network TV Power-On Capabilities Reference

| Brand | Network Power-On | WOL | Recommendation |
|-------|------------------|-----|----------------|
| Samsung Legacy | ✗ No | ✗ No | **IR Required** |
| Hisense | ✗ No | ⚠️ Unreliable | **IR Recommended** |
| LG webOS | ✗ No | ✅ Usually works | **WOL or IR** |
| Sony Bravia | ⚠️ Varies | ⚠️ Sometimes | **Try WOL, fallback IR** |
| Roku | ✅ Yes | N/A | **Network Only** |
| Vizio | ⚠️ Sometimes | ⚠️ Varies | **IR Recommended** |
| Philips | ⚠️ Varies | ⚠️ Varies | **IR Recommended** |

**Conclusion:** Only Roku can reliably power-on via network. All others benefit from IR fallback.

---

### B. Example Database Schema (Option A - Simple Hybrid)

```sql
-- Add to virtual_devices table
ALTER TABLE virtual_devices ADD COLUMN fallback_ir_controller TEXT NULL;
ALTER TABLE virtual_devices ADD COLUMN fallback_ir_port INTEGER NULL;
ALTER TABLE virtual_devices ADD COLUMN power_on_method TEXT DEFAULT 'network';
ALTER TABLE virtual_devices ADD COLUMN control_strategy TEXT DEFAULT 'network_only';

-- Example data
INSERT INTO virtual_devices (
  device_name, ip_address, protocol,
  fallback_ir_controller, fallback_ir_port,
  power_on_method, control_strategy
) VALUES (
  'Main Bar Samsung TV',
  '192.168.101.50',
  'samsung_legacy',
  'ir-abc123',  -- IR controller hostname
  2,            -- Port 2 on that controller
  'ir',         -- Always use IR for power-on
  'hybrid_ir_fallback'  -- Network primary, IR fallback
);
```

---

**End of Proposal**

**Author:** Claude Code
**Reviewed by:** [Pending]
**Status:** Awaiting Decision
