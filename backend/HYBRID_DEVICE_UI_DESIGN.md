# Hybrid Device UI Design - Network + IR Pairing

**Date:** October 7, 2025
**Purpose:** Define how hybrid devices (Network TV + IR fallback) are displayed and managed in the UI

---

## Core UX Principle

**User sees ONE device, not two separate devices.**

The IR controller port is a "fallback method" attached to the Network TV, not a separate device to manage.

---

## User Flow

### 1. Discovery & Adoption

#### Step 1: Discover Network TV

```
Network Controllers Page
┌──────────────────────────────────────────────────────────────┐
│ Discovered Devices                                           │
├──────────────────────────────────────────────────────────────┤
│ ┌────────────────────────────────────────────────────────┐   │
│ │ 📺 Samsung TV (D5500)                      [Ready]     │   │
│ │ 192.168.101.50 • Samsung • Score: 95/100              │   │
│ │                                                        │   │
│ │ Protocol: Samsung Legacy                              │   │
│ │ MAC: AA:BB:CC:DD:EE:50                               │   │
│ │                                                        │   │
│ │ [Hide] [Adopt TV]                                     │   │
│ └────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

#### Step 2: Click "Adopt TV" → Show Warning (if brand needs IR)

```
Adopt Network TV Modal
┌──────────────────────────────────────────────────────────────┐
│ Adopt TV as Virtual Controller                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ 📺 Samsung TV (D5500)                                │   │
│ │ 192.168.101.50 • Samsung Legacy                      │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                              │
│ ⚠️ Power-On Limitation Detected                             │
│                                                              │
│ Samsung Legacy TVs cannot power ON via network.              │
│ All other commands (volume, channels, etc.) work over        │
│ the network.                                                 │
│                                                              │
│ Would you like to link an IR controller for power-on?       │
│                                                              │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ ⚙️ Hybrid Setup (Recommended)                        │   │
│ │                                                        │   │
│ │ • Network control for speed & status feedback         │   │
│ │ • IR fallback for reliable power-on                   │   │
│ │ • Best user experience                                │   │
│ │                                                        │   │
│ │ [Configure IR Fallback →]                             │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                              │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ 🌐 Network Only                                       │   │
│ │                                                        │   │
│ │ • Fast network commands                               │   │
│ │ • Manual power-on required (remote or venue staff)    │   │
│ │                                                        │   │
│ │ [Skip IR Setup]                                       │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                              │
│ [Cancel]                                                     │
└──────────────────────────────────────────────────────────────┘
```

**Note for Roku:** Skip this warning entirely, go straight to adoption (network power-on works!)

---

#### Step 3a: If User Clicks "Configure IR Fallback"

```
Link IR Controller for Power-On
┌──────────────────────────────────────────────────────────────┐
│ Hybrid Setup: Link IR Controller                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ Select IR Controller:                                        │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ [ir-abc123 - Main Bar IR Controller ▼]              │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                              │
│ Select IR Port:                                              │
│ ┌────┬────┬────┬────┬────┐                                  │
│ │ 1  │ 2  │ 3  │ 4  │ 5  │                                  │
│ │ ✓  │    │ ✓  │    │ ✓  │  ✓ = In use                      │
│ └────┴────┴────┴────┴────┘                                  │
│                                                              │
│ Selected: Port 2                                             │
│                                                              │
│ Power-On Strategy:                                           │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ ( ) Network Only - Try WOL, fail if doesn't work     │   │
│ │ (•) Hybrid - Try network, fallback to IR             │   │
│ │ ( ) IR Only - Always use IR for power-on             │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                              │
│ Test IR Connection:                                          │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ [Test IR Power Command]                               │   │
│ │                                                        │   │
│ │ ✅ Test successful! (120ms)                           │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                              │
│ [Back] [Save Hybrid Setup]                                   │
└──────────────────────────────────────────────────────────────┘
```

---

#### Step 3b: If User Clicks "Skip IR Setup"

Adopt as network-only device, show warning in device card later.

---

### 2. Device Display (Management Page)

#### Option A: Show Network Device as Primary, IR as "Linked Fallback"

**Recommended approach** - user sees ONE device with hybrid control methods.

```
Device Management Page
┌──────────────────────────────────────────────────────────────┐
│ Adopted Devices                                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ 📺 Main Bar Samsung TV                      🟢 Online  │   │
│ │ nw-samsung-50 • Samsung Legacy                        │   │
│ ├────────────────────────────────────────────────────────┤   │
│ │                                                        │   │
│ │ Network Control (Primary)                             │   │
│ │ • IP: 192.168.101.50                                  │   │
│ │ • Protocol: Samsung Legacy                            │   │
│ │ • Status: 🟢 Online (245ms)                           │   │
│ │ • Last command: 2 minutes ago                         │   │
│ │                                                        │   │
│ │ IR Fallback (Power-On)                                │   │
│ │ • Controller: ir-abc123 (Main Bar IR)                 │   │
│ │ • Port: 2                                             │   │
│ │ • Status: 🟢 Online                                   │   │
│ │ • Strategy: Hybrid (Network → IR fallback)            │   │
│ │                                                        │   │
│ │ Control Status:                                       │   │
│ │ • Power-On: IR (WOL not supported)                    │   │
│ │ • Power-Off: Network                                  │   │
│ │ • Volume/Channels: Network                            │   │
│ │ • Fallback: IR (if network fails)                     │   │
│ │                                                        │   │
│ │ [Test Network] [Test IR] [Configure] [Unlink IR]     │   │
│ └────────────────────────────────────────────────────────┘   │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ 📺 Lobby LG webOS TV                    🟢 Online     │   │
│ │ nw-lg-55 • LG webOS                                   │   │
│ ├────────────────────────────────────────────────────────┤   │
│ │                                                        │   │
│ │ Network Control (Primary)                             │   │
│ │ • IP: 192.168.101.55                                  │   │
│ │ • Status: 🟢 On (Volume: 25, Input: HDMI 1)          │   │
│ │ • App: Netflix                                        │   │
│ │                                                        │   │
│ │ No IR Fallback Linked                                 │   │
│ │ [Link IR for Power-On]                                │   │
│ └────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

**Advantages:**
- ✅ User sees one device
- ✅ Clear which control method is used for what
- ✅ Easy to link/unlink IR
- ✅ Shows real-time status from network

---

#### Option B: Collapsed View (Default), Expandable for Details

**More compact** - same info, but collapsed by default.

```
Device Management Page (Collapsed)
┌──────────────────────────────────────────────────────────────┐
│ ┌────────────────────────────────────────────────────────┐   │
│ │ 📺 Main Bar Samsung TV          🟢 Online   [▼ Expand] │   │
│ │ Network + IR Hybrid • 192.168.101.50                  │   │
│ └────────────────────────────────────────────────────────┘   │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ 📺 Lobby LG webOS TV            🟢 Online   [▼ Expand] │   │
│ │ Network Only • 192.168.101.55 • Vol: 25 • HDMI 1     │   │
│ └────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘

(Click expand to see full details like Option A)
```

---

### 3. Control Interface (Sending Commands)

When user sends a command, UI shows which method was used:

```
Command Execution Feedback
┌──────────────────────────────────────────────────────────────┐
│ Main Bar Samsung TV                                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ Command: Power On                                            │
│                                                              │
│ Execution Log:                                               │
│ • [0ms] Attempting network power-on (WOL)...                 │
│ • [2000ms] Network power-on not supported                    │
│ • [2100ms] Falling back to IR power-on...                   │
│ • [2280ms] ✅ IR power-on successful (180ms)                │
│ • [2280ms] Waiting for TV to boot (10s)...                  │
│ • [12280ms] Verifying network connection...                  │
│ • [12450ms] ✅ Network online                               │
│                                                              │
│ Total Time: 12.5 seconds                                     │
│ Method: IR Fallback                                          │
└──────────────────────────────────────────────────────────────┘

vs.

┌──────────────────────────────────────────────────────────────┐
│ Main Bar Samsung TV                                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ Command: Volume Up                                           │
│                                                              │
│ Execution Log:                                               │
│ • [0ms] Sending via network...                               │
│ • [245ms] ✅ Success                                         │
│                                                              │
│ Total Time: 245ms                                            │
│ Method: Network (Samsung Legacy)                             │
└──────────────────────────────────────────────────────────────┘
```

---

### 4. IR Controller View (What Happens to IR Controller?)

#### Important: IR Controller Port "Claimed" by Hybrid Device

When an IR port is linked to a Network TV:
- **Option A:** Hide that port from IR controller view (RECOMMENDED)
- **Option B:** Show as "Linked to Network TV"

**Recommended: Option A (Hide linked ports)**

```
IR Controller: ir-abc123 (Main Bar IR)
┌──────────────────────────────────────────────────────────────┐
│ Ports:                                                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ Port 1: Main Bar Set-Top Box                     [Configure] │
│ Port 2: (Linked to Main Bar Samsung TV - Hybrid)  [Unlink]  │  ← Show but grayed out
│ Port 3: Available                                   [Setup]   │
│ Port 4: Available                                   [Setup]   │
│ Port 5: Available                                   [Setup]   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Alternative: Hide completely**

```
IR Controller: ir-abc123 (Main Bar IR)
┌──────────────────────────────────────────────────────────────┐
│ Ports:                                                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ Port 1: Main Bar Set-Top Box                     [Configure] │
│ Port 3: Available                                   [Setup]   │
│ Port 4: Available                                   [Setup]   │
│ Port 5: Available                                   [Setup]   │
│                                                              │
│ ℹ️ Port 2 is linked to "Main Bar Samsung TV" as hybrid     │
│    fallback. Unlink from Network Controllers page.          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**My Recommendation:** Show grayed out with "[Unlink]" button for transparency.

---

### 5. Status Display with Real-Time Updates

Add status info to device cards (answering your "status info" question):

```
Network Controllers Page (with Status)
┌──────────────────────────────────────────────────────────────┐
│ Adopted Virtual Controllers                                  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ 📺 Main Bar Samsung TV                                 │   │
│ │ nw-samsung-50 • Samsung Legacy                        │   │
│ │                                                        │   │
│ │ Connection: 🟢 Online (192.168.101.50)                │   │
│ │ Response: 245ms                                        │   │
│ │                                                        │   │
│ │ Status: ⚠️ Not Available                              │   │
│ │ (Samsung Legacy doesn't support status queries)       │   │
│ │                                                        │   │
│ │ Last Command: Volume Up (2 min ago)                   │   │
│ │ Assumed State: On                                     │   │
│ │                                                        │   │
│ │ Hybrid: IR Fallback Linked (ir-abc123 Port 2)        │   │
│ └────────────────────────────────────────────────────────┘   │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ 📺 Lobby LG webOS TV                                   │   │
│ │ nw-lg-55 • LG webOS                                   │   │
│ │                                                        │   │
│ │ Connection: 🟢 Online (192.168.101.55)                │   │
│ │ Response: 420ms                                        │   │
│ │                                                        │   │
│ │ Real-Time Status: ✅ Available                        │   │
│ │ • Power: 🟢 On (Active)                               │   │
│ │ • Volume: 🔊 25 (Not muted)                           │   │
│ │ • Input: 📡 HDMI 1                                    │   │
│ │ • App: Netflix                                        │   │
│ │ • Last Updated: 3 seconds ago                         │   │
│ │                                                        │   │
│ │ [Refresh Status Now]                                  │   │
│ └────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

**Status Indicators:**
- ✅ Available - TV supports status queries (LG, Sony, Hisense, etc.)
- ⚠️ Not Available - TV doesn't support status (Samsung Legacy)
- 🔄 Polling... - Currently fetching status
- ❌ Failed - Last status query failed

---

### 6. Discovery Page (Add Status Info)

**Add live status to discovery page** (before adoption):

```
Network Discovery Page
┌──────────────────────────────────────────────────────────────┐
│ Discovered Devices                                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ 📺 LG webOS TV                         [Ready to Adopt] │   │
│ │ 192.168.101.55 • LG • Score: 98/100                   │   │
│ │                                                        │   │
│ │ Live Status: ✅                                        │   │
│ │ • Power: On                                           │   │
│ │ • Volume: 25                                          │   │
│ │ • Input: HDMI 1                                       │   │
│ │ • App: Netflix                                        │   │
│ │                                                        │   │
│ │ [Hide] [Adopt TV]                                     │   │
│ └────────────────────────────────────────────────────────┘   │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ 📺 Samsung TV (D5500)                  [Ready to Adopt] │   │
│ │ 192.168.101.50 • Samsung • Score: 95/100              │   │
│ │                                                        │   │
│ │ Status: ⚠️ Not Available (Protocol limitation)        │   │
│ │ • Power-On: Requires IR fallback                      │   │
│ │                                                        │   │
│ │ [Hide] [Adopt TV]                                     │   │
│ └────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

## Key UI/UX Decisions

### 1. Primary Device View

**Decision:** Network TV is the primary device, IR is a "linked fallback method"

**Rationale:**
- User thinks "I want to control my TV"
- They don't care that it uses IR for power-on vs network for volume
- They just want it to work

---

### 2. IR Port Visibility

**Decision:** Show IR port as "Linked to [Device Name]" in IR controller view

**Rationale:**
- Transparency - user can see where all ports are used
- Easy to unlink if needed
- Prevents confusion about "missing" ports

---

### 3. Status Display

**Decision:** Show different status UI based on TV capabilities

- **Full status** (LG, Sony, Hisense): Show power, volume, input, app
- **Limited status** (Samsung Legacy): Show "Not Available" + assumed state
- **Partial status** (Roku): Show power and app, note volume not available

**Rationale:**
- Set accurate expectations
- Don't show "Loading..." for status that will never load
- Highlight advantages of network control for capable TVs

---

### 4. Linking Flow

**Decision:** Suggest IR linking during adoption for brands that need it

**Rationale:**
- Proactive - user doesn't discover limitation later
- Educational - explains why hybrid is better
- Optional - power users can skip if they want network-only

---

### 5. Command Execution Feedback

**Decision:** Show which method was used for each command

**Rationale:**
- Transparency - user learns the system
- Debugging - helps diagnose issues
- Trust - user sees fallback working

---

## Implementation Checklist

### Backend
- [ ] Add `fallback_ir_controller`, `fallback_ir_port` to `VirtualDevice` model
- [ ] Add `power_on_method` field ("network", "ir", "hybrid")
- [ ] Add `cached_power_state`, `cached_volume_level`, etc. for status
- [ ] Implement hybrid command router (try network, fallback to IR)
- [ ] Add API endpoints: `/link-ir-fallback`, `/unlink-ir-fallback`, `/get-status`

### Frontend
- [ ] Modify adoption modal to show IR fallback option
- [ ] Add IR controller selector and port picker
- [ ] Update device card to show hybrid control methods
- [ ] Add status display (power, volume, input, app)
- [ ] Show real-time status updates (WebSocket or polling)
- [ ] Add "Method Used" badge on command execution

### Testing
- [ ] Test hybrid power-on flow (network fails → IR succeeds)
- [ ] Test status polling for LG/Hisense/Sony
- [ ] Test UI with network-only device (Roku)
- [ ] Test UI with hybrid device (Samsung Legacy + IR)
- [ ] Test IR port visibility in IR controller view

---

## Visual Summary

### User Journey

```
1. Discover Network TV
   ↓
2. Click "Adopt TV"
   ↓
3. System detects: "This TV needs IR for power-on"
   ↓
4. User chooses:
   a) Hybrid Setup (link IR) → Best UX
   b) Network Only → Limited power-on
   ↓
5. Device shows as ONE device with:
   - Network control (primary)
   - IR fallback (power-on)
   - Real-time status (if available)
   ↓
6. User sends commands:
   - Power-On → IR (reliable)
   - Volume → Network (fast)
   - Status → Network (real-time)
```

---

**End of Document**

**Next Steps:**
1. Implement backend hybrid routing
2. Add status polling for capable brands
3. Update frontend to show hybrid devices
4. Test with real Samsung TV + IR controller
