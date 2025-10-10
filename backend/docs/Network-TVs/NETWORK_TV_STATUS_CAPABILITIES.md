# Network TV Status Capabilities & Monitoring

**Date:** October 7, 2025
**Purpose:** Document what status information can be reliably retrieved from network-controlled TVs

---

## Executive Summary

One of the **biggest advantages** of network control over IR is **status feedback** - we can query the TV's current state instead of sending blind commands.

### Status Capabilities by Brand

| Brand | Power State | Volume Level | Mute Status | Current Input | Current App | Picture Mode | Response Time |
|-------|-------------|--------------|-------------|---------------|-------------|--------------|---------------|
| **Samsung Legacy** | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No | N/A |
| **Samsung Modern** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ~500ms |
| **Hisense VIDAA** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ Limited | ⚠️ Limited | ~400ms |
| **LG webOS** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ~600ms |
| **Sony Bravia** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ Limited | ✅ Yes | ~500ms |
| **Roku** | ✅ Yes | ⚠️ No | ⚠️ No | N/A | ✅ Yes | N/A | ~200ms |
| **Vizio SmartCast** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ Limited | ~700ms |
| **Philips JointSpace** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ Limited | ⚠️ Limited | ~600ms |

**Legend:**
- ✅ Fully supported - reliable status queries
- ⚠️ Limited - may work, but unreliable or incomplete
- ❌ Not available - protocol doesn't support

---

## Brand-by-Brand Breakdown

### 1. Samsung Legacy (D/E/F Series, 2011-2015)

**Protocol:** TCP port 55000 (samsungctl library)

#### Status Capabilities: ❌ **NONE**

The Samsung Legacy protocol is **one-way only** - it can send commands but **cannot query status**.

```python
# NO STATUS QUERIES AVAILABLE
# Protocol only supports sending IR codes over network
# No way to read volume, input, power state, etc.
```

**Workaround:** Maintain "assumed state" based on commands sent:
- Track last command sent (e.g., "volume_up")
- Assume TV is in that state
- Reset on TV reboot or manual control

**Recommendation:** This is a **major limitation** of Samsung Legacy. Consider upgrading to Samsung Modern (Tizen 2016+) for status feedback.

---

### 2. Samsung Modern (2016+ Tizen)

**Protocol:** WebSocket port 8001/8002 (samsungtvws library)

#### Status Capabilities: ✅ **EXCELLENT**

Modern Samsung TVs have a rich REST API + WebSocket interface.

**Available Status Queries:**

```python
# Power State
GET http://TV_IP:8001/api/v2/
Response: {"device": {"PowerState": "on"}}  # "on", "standby", "off"

# Volume Level
WebSocket: {"method": "ms.channel.emit", "params": {"event": "ed.audioVolume"}}
Response: {"volume": 15, "muted": false}  # 0-100

# Current Input
WebSocket: {"method": "ms.channel.emit", "params": {"event": "ed.installedApp.get"}}
Response: {"appId": "111299001912", "name": "HDMI 1"}

# Current App
WebSocket: {"method": "ms.channel.emit", "params": {"event": "ed.apps.launch"}}
Response: {"appId": "3201907018807", "name": "Netflix"}

# Picture Mode
GET /api/v2/picturemode
Response: {"mode": "Dynamic", "brightness": 45}
```

**Polling Frequency:** Every 5-10 seconds (WebSocket maintains connection)

**Note:** Not yet implemented in TapCommand (planned for future).

---

### 3. Hisense VIDAA

**Protocol:** MQTT port 36669 (hisensetv library)

#### Status Capabilities: ✅ **GOOD**

Hisense uses MQTT protocol with pub/sub for status updates.

**Available Status Queries:**

```python
from hisensetv import HisenseTv

tv = HisenseTv('192.168.1.50')

# Power State
state = tv.get_state()
# Returns: {"statetype": "sourceswitch", "sourceid": "3", "sourcename": "HDMI 1"}
# Can infer power state from response (no response = off)

# Volume Level
volume = tv.get_volume()
# Returns: {"volume_type": 0, "volume_value": 15}
# volume_type: 0 = speaker, 1 = headphone
# volume_value: 0-100

# Available Sources (Inputs)
sources = tv.get_sources()
# Returns: [
#   {"sourceid": "0", "sourcename": "TV", "displayname": "TV"},
#   {"sourceid": "3", "sourcename": "HDMI 1", "displayname": "HDMI 1"},
#   {"sourceid": "4", "sourcename": "HDMI 2", "displayname": "HDMI 2"},
#   ...
# ]

# Current Source
# Available via get_state() response (see above)

# Mute Status
# Included in volume query (volume_value: -1 means muted on some models)
```

**Polling Frequency:** Every 5 seconds (MQTT broker maintains connection)

**Limitations:**
- Current app detection limited (can see source, not app within source)
- Picture mode queries not well documented

---

### 4. LG webOS

**Protocol:** WebSocket port 3000/3001 (pywebostv library)

#### Status Capabilities: ✅ **EXCELLENT**

LG webOS has one of the **richest APIs** for status queries.

**Available Status Queries:**

```python
from pywebostv.connection import WebOSClient
from pywebostv.controls import MediaControl, SystemControl, ApplicationControl, InputControl

client = WebOSClient('192.168.1.50')
client.connect()

media = MediaControl(client)
system = SystemControl(client)
apps = ApplicationControl(client)
inputs = InputControl(client)

# Power State
power_state = system.get_power_state()
# Returns: {"state": "Active"}  # "Active", "ActiveStandby", "Suspend"

# Volume Level
volume = media.get_volume()
# Returns: {"scenario": "mastervolume_tv_speaker", "volume": 15, "muted": false}
# volume: 0-100

# Mute Status
# Included in volume query (see above)

# Current Input
current_input = inputs.get_input()
# Returns: {"id": "HDMI_1", "label": "HDMI 1", "connected": true, "icon": "..."}

# Available Inputs
all_inputs = inputs.list_inputs()
# Returns: [
#   {"id": "HDMI_1", "label": "HDMI 1", "connected": true},
#   {"id": "HDMI_2", "label": "HDMI 2", "connected": false},
#   ...
# ]

# Current App
current_app = apps.get_current()
# Returns: {"id": "netflix", "title": "Netflix", "icon": "..."}

# Available Apps
all_apps = apps.list_apps()
# Returns: [
#   {"id": "netflix", "title": "Netflix", "largeIcon": "..."},
#   {"id": "youtube.leanback.v4", "title": "YouTube", "largeIcon": "..."},
#   ...
# ]

# System Info
info = system.info()
# Returns: {
#   "modelName": "OLED55C1PUB",
#   "firmwareVersion": "04.30.50",
#   "manufacturer": "LG Electronics"
# }
```

**Polling Frequency:** Every 3-5 seconds (WebSocket maintains connection)

**Advantages:**
- Very responsive (WebSocket)
- Can subscribe to events (TV notifies us when state changes)
- Rich app ecosystem queries

---

### 5. Sony Bravia

**Protocol:** REST API port 80 (HTTP + IRCC)

#### Status Capabilities: ✅ **EXCELLENT**

Sony Bravia REST API uses JSON-RPC over HTTP.

**Available Status Queries:**

```python
import requests

# PSK authentication header
headers = {
    'X-Auth-PSK': '0000',  # Your PSK
    'Content-Type': 'application/json'
}

# Power State
response = requests.post(
    'http://192.168.1.50/sony/system',
    headers=headers,
    json={
        "method": "getPowerStatus",
        "version": "1.0",
        "id": 1,
        "params": []
    }
)
# Returns: {"result": [{"status": "active"}]}
# status: "active", "standby"

# Volume Level
response = requests.post(
    'http://192.168.1.50/sony/audio',
    headers=headers,
    json={
        "method": "getVolumeInformation",
        "version": "1.0",
        "id": 1,
        "params": []
    }
)
# Returns: {
#   "result": [[
#     {
#       "target": "speaker",
#       "volume": 15,
#       "mute": false,
#       "maxVolume": 100,
#       "minVolume": 0
#     }
#   ]]
# }

# Current Input
response = requests.post(
    'http://192.168.1.50/sony/avContent',
    headers=headers,
    json={
        "method": "getPlayingContentInfo",
        "version": "1.0",
        "id": 1,
        "params": []
    }
)
# Returns: {
#   "result": [{
#     "uri": "extInput:hdmi?port=1",
#     "title": "HDMI 1"
#   }]
# }

# Available Inputs
response = requests.post(
    'http://192.168.1.50/sony/avContent',
    headers=headers,
    json={
        "method": "getContentList",
        "version": "1.2",
        "id": 1,
        "params": [{"source": "extInput:hdmi"}]
    }
)
# Returns: List of all HDMI inputs

# Picture Mode
response = requests.post(
    'http://192.168.1.50/sony/video',
    headers=headers,
    json={
        "method": "getPictureQualitySettings",
        "version": "1.0",
        "id": 1,
        "params": []
    }
)
# Returns: Picture settings including mode
```

**Polling Frequency:** Every 5 seconds (HTTP polling)

**Limitations:**
- Current app detection limited (can see content playing, not app name)
- Polling-based (no WebSocket events)

---

### 6. Roku

**Protocol:** HTTP REST (ECP) port 8060

#### Status Capabilities: ⚠️ **MIXED**

Roku ECP provides good app/channel info but limited volume queries.

**Available Status Queries:**

```python
import requests

# Device Info (includes power state)
response = requests.get('http://192.168.1.50:8060/query/device-info')
# Returns XML:
# <device-info>
#   <power-mode>PowerOn</power-mode>  <!-- PowerOn, Headless, Ready -->
#   <model-name>Roku Ultra</model-name>
#   <vendor-name>Roku</vendor-name>
#   <network-type>wifi</network-type>
# </device-info>

# Current App
response = requests.get('http://192.168.1.50:8060/query/active-app')
# Returns XML:
# <active-app>
#   <app id="12">Netflix</app>
# </active-app>

# Available Apps
response = requests.get('http://192.168.1.50:8060/query/apps')
# Returns XML list of all installed apps

# Media Player Info (if media playing)
response = requests.get('http://192.168.1.50:8060/query/media-player')
# Returns XML:
# <player state="play">
#   <format>...video format...</format>
#   <duration>...</duration>
#   <position>...</position>
# </player>
```

**Polling Frequency:** Every 3 seconds (HTTP polling, very fast)

**Limitations:**
- ❌ **No volume query** - Cannot read current volume level
- ❌ **No mute status** - Cannot check if muted
- ❌ **No input query** - Roku devices don't have inputs (streaming only)
- ✅ Good for app/channel detection
- ✅ Very fast responses (~100-200ms)

---

### 7. Vizio SmartCast

**Protocol:** HTTPS REST port 7345/9000 (pyvizio library)

#### Status Capabilities: ✅ **GOOD**

Vizio REST API provides status after authentication.

**Available Status Queries:**

```python
from pyvizio import Vizio

tv = Vizio('192.168.1.50', 'YOUR_AUTH_TOKEN')

# Power State
power_state = tv.get_power_state()
# Returns: 1 (On) or 0 (Off)

# Volume Level
current_volume = tv.get_current_volume()
# Returns: 15 (0-100)

# Mute Status
# Included in some volume queries or separate method

# Current Input
current_input = tv.get_current_input()
# Returns: {"name": "HDMI-1", "type": "hdmi"}

# Available Inputs
all_inputs = tv.get_inputs_list()
# Returns: [
#   {"name": "HDMI-1", "type": "hdmi"},
#   {"name": "HDMI-2", "type": "hdmi"},
#   {"name": "Cast", "type": "cast"},
#   ...
# ]

# Current App (SmartCast apps)
current_app = tv.get_current_app()
# Returns: {"name": "Netflix", "id": "..."} (if SmartCast app active)
```

**Polling Frequency:** Every 5-7 seconds (HTTPS polling)

**Limitations:**
- Slower due to HTTPS overhead
- Some features vary by firmware version

---

### 8. Philips JointSpace (Android TV)

**Protocol:** HTTP/HTTPS port 1925/1926 (JointSpace API v6)

#### Status Capabilities: ✅ **GOOD**

Philips JointSpace API provides status queries.

**Available Status Queries:**

```python
import requests

# Power State
response = requests.get('http://192.168.1.50:1926/6/powerstate')
# Returns: {"powerstate": "On"}  # "On", "Standby"

# Volume Level
response = requests.get('http://192.168.1.50:1926/6/audio/volume')
# Returns: {"current": 15, "min": 0, "max": 60, "muted": false}

# Current Input
response = requests.get('http://192.168.1.50:1926/6/sources/current')
# Returns: {"id": "hdmi1", "name": "HDMI 1"}

# Available Inputs
response = requests.get('http://192.168.1.50:1926/6/sources')
# Returns: [
#   {"id": "hdmi1", "name": "HDMI 1"},
#   {"id": "hdmi2", "name": "HDMI 2"},
#   ...
# ]

# Current App (Android TV apps)
response = requests.get('http://192.168.1.50:1926/6/applications')
# Returns: List of running applications
```

**Polling Frequency:** Every 5 seconds (HTTP polling)

**Limitations:**
- Some models require digest authentication
- App queries may be limited on non-Android models

---

## Status Monitoring Architecture

### Recommended Polling Strategy

#### Tier 1: Fast Polling (3-5 seconds)
**Who:** LG webOS, Roku, Hisense (WebSocket/MQTT connections)
**Why:** Connection already open, minimal overhead
**Status:** Power, Volume, Input, App

#### Tier 2: Medium Polling (5-7 seconds)
**Who:** Sony Bravia, Philips, Vizio
**Why:** HTTP polling, balance between freshness and load
**Status:** Power, Volume, Input

#### Tier 3: No Polling (Manual Only)
**Who:** Samsung Legacy
**Why:** No status APIs available
**Strategy:** Track assumed state, refresh on user request

---

### Status Database Schema

**Add to `VirtualDevice` model:**

```python
class VirtualDevice(Base):
    # ... existing fields ...

    # Status cache (updated by polling)
    cached_power_state = Column(String, nullable=True)      # "on", "off", "standby"
    cached_volume_level = Column(Integer, nullable=True)    # 0-100
    cached_mute_status = Column(Boolean, nullable=True)     # true/false
    cached_current_input = Column(String, nullable=True)    # "HDMI 1", "HDMI 2", etc.
    cached_current_app = Column(String, nullable=True)      # "Netflix", "YouTube", etc.

    # Status metadata
    last_status_poll = Column(DateTime(timezone=True), nullable=True)
    status_poll_failures = Column(Integer, default=0)       # Consecutive failures
    status_available = Column(Boolean, default=False)       # Can this device provide status?
```

---

### Status Polling Service

**New service:** `app/services/tv_status_poller.py`

```python
class TVStatusPoller:
    """
    Background service to poll network TVs for status updates

    - Polls each TV based on tier (3s, 5s, or disabled)
    - Updates cached status in database
    - Emits WebSocket events when status changes
    - Handles failures gracefully
    """

    async def poll_device(self, device: VirtualDevice):
        """Poll a single device for status"""

        if device.protocol == "samsung_legacy":
            # No status available, skip
            return

        if device.protocol == "lg_webos":
            status = await self._poll_lg_webos(device)
        elif device.protocol == "hisense_vidaa":
            status = await self._poll_hisense(device)
        elif device.protocol == "sony_bravia":
            status = await self._poll_sony(device)
        # ... etc

        # Update database cache
        device.cached_power_state = status.get('power')
        device.cached_volume_level = status.get('volume')
        device.cached_current_input = status.get('input')
        device.last_status_poll = datetime.now()

        # Emit WebSocket event if changed
        if self._status_changed(device, status):
            await self._emit_status_update(device, status)
```

---

## UI Display Recommendations

### Device Card Status Display

```
┌────────────────────────────────────────────┐
│ 📺 Main Bar Samsung TV                     │
│ Samsung Legacy • 192.168.101.50            │
├────────────────────────────────────────────┤
│ Status: 🟢 Online (Network)                │
│ Volume: -- (Status not available)          │
│ Input: -- (Status not available)           │
│                                            │
│ ⚠️ This TV cannot report status            │
│    Status based on last command sent       │
└────────────────────────────────────────────┘

vs.

┌────────────────────────────────────────────┐
│ 📺 Lobby LG webOS TV                       │
│ LG webOS • 192.168.101.55                  │
├────────────────────────────────────────────┤
│ Status: 🟢 On (Active)                     │
│ Volume: 🔊 25 (Not muted)                  │
│ Input: 📡 HDMI 1                           │
│ App: Netflix                               │
│                                            │
│ Last updated: 2 seconds ago                │
└────────────────────────────────────────────┘
```

---

## Status Capabilities Summary

### What We Can Reliably Monitor:

✅ **Power State:** All brands except Samsung Legacy (7/8 brands)
✅ **Volume Level:** All brands except Samsung Legacy & Roku (6/8 brands)
✅ **Mute Status:** All brands except Samsung Legacy & Roku (6/8 brands)
✅ **Current Input:** All brands except Samsung Legacy & Roku (6/8 brands)
✅ **Current App:** LG, Sony (limited), Roku, Vizio, Hisense (limited) (5/8 brands)

### What We Cannot Monitor:

❌ **Content Playback State:** Most brands don't expose play/pause/position
❌ **Picture Settings:** Limited on most brands
❌ **Audio Settings (beyond volume):** Limited
❌ **Network Quality:** Not exposed by most APIs

---

## Implementation Priority

### Phase 1: Basic Status (1-2 days)
- ✅ Power state monitoring
- ✅ Volume level monitoring
- ✅ Update database cache every 5 seconds
- ✅ Display in UI

### Phase 2: Advanced Status (2-3 days)
- ✅ Current input monitoring
- ✅ Current app detection
- ✅ WebSocket event emission
- ✅ Status change notifications

### Phase 3: Analytics (1 week)
- ✅ Status history tracking
- ✅ Usage patterns (which inputs/apps most used)
- ✅ Uptime tracking
- ✅ Health monitoring

---

**End of Document**

**Next Steps:**
1. Implement status polling for Hisense, LG, Sony (we have libraries)
2. Add status cache to VirtualDevice model
3. Create background polling service
4. Update UI to display status
