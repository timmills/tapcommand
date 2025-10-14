# Sonos Integration Implementation Summary

**Date:** October 14, 2025
**Status:** Phase 1 Complete - Ready for Testing

## Overview

Successfully implemented Sonos speaker integration following the same architectural patterns as Bosch Plena Matrix audio integration. The implementation uses the SoCo Python library for UPnP/SOAP communication with Sonos speakers.

## Implementation Completed

### 1. Dependencies
- ✅ Installed `soco==0.30.12` library
- ✅ Added to `backend/requirements.txt`

### 2. Discovery Service (`backend/app/services/sonos_discovery.py`)
- ✅ `discover_sonos_speakers_on_network()` - Network-wide SSDP/mDNS discovery
- ✅ `discover_and_create_sonos_controller()` - Create VirtualController and VirtualDevice
- ✅ `test_sonos_connection()` - Pre-adoption connection testing
- ✅ `get_sonos_speaker_status()` - Query current speaker state

**Key Pattern:** Returns `(controller_id, num_devices)` tuple to match Plena Matrix pattern.

### 3. Command Executor (`backend/app/commands/executors/audio/sonos_upnp.py`)
- ✅ `SonosUPnPExecutor` class implementing `CommandExecutor` interface
- ✅ Supported commands:
  - `set_volume` - Set speaker volume (0-100)
  - `set_mute` - Mute/unmute speaker
  - `play` - Start playback
  - `pause` - Pause playback
  - `stop` - Stop playback
  - `next` - Skip to next track
  - `previous` - Go to previous track

**Key Patterns:**
- Caches `SoCo` speaker objects by IP address
- Uses `asyncio.get_event_loop().run_in_executor()` to wrap synchronous SoCo calls
- Implements cache-and-verify pattern (read back values after setting)
- Stores IP/port in `connection_config` JSON (not table columns)
- Uses `channel` field for volume values (historical pattern)

### 4. Executor Registration
- ✅ Registered in `backend/app/commands/executors/audio/__init__.py`
- ✅ Added to protocol router in `backend/app/commands/router.py`
- ✅ Routes commands with `device_type="audio_zone"` and `protocol="sonos_upnp"`

### 5. API Endpoints (`backend/app/routers/audio_controllers.py`)

#### General Audio Endpoints (Now Support Sonos)
- ✅ `POST /api/audio/controllers/discover` - Add Sonos speaker (protocol="sonos_upnp")
- ✅ `GET /api/audio/controllers` - List all audio controllers (includes Sonos)
- ✅ `GET /api/audio/zones` - List all audio zones (includes Sonos)
- ✅ `POST /api/audio/zones/{zone_id}/volume` - Set volume (queued command)
- ✅ `POST /api/audio/zones/{zone_id}/volume/up` - Increase volume
- ✅ `POST /api/audio/zones/{zone_id}/volume/down` - Decrease volume
- ✅ `POST /api/audio/zones/{zone_id}/mute` - Mute/unmute
- ✅ `DELETE /api/audio/controllers/{controller_id}` - Delete controller

#### Sonos-Specific Endpoints
- ✅ `GET /api/audio/sonos/discover` - Network-wide Sonos discovery
- ✅ `POST /api/audio/sonos/test-connection` - Test connection before adding
- ✅ `POST /api/audio/zones/{zone_id}/play` - Start playback
- ✅ `POST /api/audio/zones/{zone_id}/pause` - Pause playback
- ✅ `POST /api/audio/zones/{zone_id}/stop` - Stop playback
- ✅ `POST /api/audio/zones/{zone_id}/next` - Skip to next track
- ✅ `POST /api/audio/zones/{zone_id}/previous` - Go to previous track

### 6. Status Polling (`backend/app/services/tv_status_poller.py`)
- ✅ Added `_poll_sonos()` method
- ✅ Polls every 3 seconds (Tier 1 - fast polling)
- ✅ Queries volume, mute status, transport state, and current track info
- ✅ Updates `cached_volume_level`, `cached_mute_status`, `cached_current_app`
- ✅ Stores transport state and track info in `connection_config`

## Database Schema

### VirtualController (Sonos Speaker)
```python
{
    "controller_id": "sonos-192-168-1-100",
    "controller_name": "Living Room Sonos",
    "controller_type": "audio",
    "protocol": "sonos_upnp",
    "total_ports": 1,  # One speaker = one port
    "connection_config": {
        "ip_address": "192.168.1.100",
        "port": 1400,
        "uid": "RINCON_B8E93790BFAA01400",
        "model_name": "Sonos One",
        "model_number": "S18",
        "zone_name": "Living Room",
        "software_version": "13.4",
        "mac_address": "B8:E9:37:90:BF:AA",
        "hardware_version": "1.20.4.10-1"
    },
    "capabilities": {
        "volume": True,
        "mute": True,
        "play": True,
        "pause": True,
        "stop": True,
        "next": True,
        "previous": True,
        "seek": True,
        "queue": True,
        "grouping": True,
        "eq": True
    }
}
```

### VirtualDevice (Speaker Port)
```python
{
    "controller_id": <VirtualController.id>,
    "port_number": 1,  # Always 1 for Sonos (one controller per speaker)
    "port_id": "sonos-192-168-1-100-1",
    "device_name": "Living Room",
    "device_type": "audio_zone",
    "ip_address": "192.168.1.100",
    "port": 1400,
    "protocol": "sonos_upnp",
    "connection_config": {
        "uid": "RINCON_B8E93790BFAA01400",
        "transport_state": "PLAYING",  # Updated by poller
        "current_track": {  # Updated by poller
            "title": "Bohemian Rhapsody",
            "artist": "Queen",
            "album": "A Night at the Opera",
            "position": "0:02:15",
            "duration": "0:05:55"
        }
    },
    "cached_volume_level": 45,  # Updated by poller
    "cached_mute_status": False,  # Updated by poller
    "status_available": True
}
```

## Command Queue Pattern

### Set Volume Command
```python
CommandQueue(
    hostname="sonos-192-168-1-100",  # controller_id, not IP!
    command="set_volume",
    port=1,  # Speaker/zone number
    channel="75",  # Volume value stored here (historical pattern)
    digit=1,  # Redundant zone number
    command_class="interactive",
    status="pending",
    priority=0,
    max_attempts=3,
    routing_method="queued"
)
```

### Playback Command
```python
CommandQueue(
    hostname="sonos-192-168-1-100",
    command="play",  # or "pause", "stop", "next", "previous"
    port=1,
    command_class="interactive",
    status="pending",
    priority=0,
    max_attempts=3,
    routing_method="queued"
)
```

## Testing Guide

### 1. Network Discovery
```bash
curl http://localhost:8000/api/audio/sonos/discover
```

Expected response:
```json
{
  "success": true,
  "total_found": 2,
  "speakers": [
    {
      "ip_address": "192.168.1.100",
      "uid": "RINCON_B8E93790BFAA01400",
      "model_name": "Sonos One",
      "zone_name": "Living Room",
      "software_version": "13.4",
      "mac_address": "B8:E9:37:90:BF:AA"
    }
  ]
}
```

### 2. Test Connection
```bash
curl -X POST "http://localhost:8000/api/audio/sonos/test-connection?ip_address=192.168.1.100"
```

### 3. Add Sonos Speaker
```bash
curl -X POST http://localhost:8000/api/audio/controllers/discover \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "192.168.1.100",
    "controller_name": "Living Room Sonos",
    "protocol": "sonos_upnp",
    "venue_name": "Home",
    "location": "Living Room"
  }'
```

### 4. List Audio Controllers
```bash
curl http://localhost:8000/api/audio/controllers
```

### 5. Set Volume
```bash
curl -X POST http://localhost:8000/api/audio/zones/{zone_id}/volume \
  -H "Content-Type: application/json" \
  -d '{"volume": 50}'
```

### 6. Playback Control
```bash
# Play
curl -X POST http://localhost:8000/api/audio/zones/{zone_id}/play

# Pause
curl -X POST http://localhost:8000/api/audio/zones/{zone_id}/pause

# Stop
curl -X POST http://localhost:8000/api/audio/zones/{zone_id}/stop

# Next track
curl -X POST http://localhost:8000/api/audio/zones/{zone_id}/next

# Previous track
curl -X POST http://localhost:8000/api/audio/zones/{zone_id}/previous
```

### 7. Check Command Queue Status
```bash
curl http://localhost:8000/api/commands/queue/metrics
```

## Architecture Decisions

### One Controller Per Speaker (Chosen)
- **Why:** Simpler, consistent with Plena Matrix pattern
- Each Sonos speaker = One VirtualController + One VirtualDevice (port 1)
- Easier to manage in UI, clear ownership

### Alternative: One Controller Per Household (Rejected)
- Would support multiple speakers per controller
- More complex discovery and zone management
- Inconsistent with existing audio patterns

### IP Address Storage
- ✅ **DO THIS:** Store in `connection_config` JSON
  ```python
  controller.connection_config = {"ip_address": "192.168.1.100", "port": 1400}
  ```
- ❌ **DON'T DO THIS:** Use table columns directly (may be empty)
  ```python
  ip_address = controller.ip_address  # May be empty!
  ```

### Command Queue Field Usage
- `hostname` = `controller_id` (e.g., "sonos-192-168-1-100"), NOT an IP address
- `port` = zone/speaker number (always 1 for Sonos)
- `channel` = volume value for set_volume commands (historical pattern)
- `digit` = redundant zone number

## Implementation Notes

### Critical Patterns Followed
1. ✅ IP/port stored in `connection_config` JSON (not table columns)
2. ✅ Discovery service returns `(controller_id, num_devices)` tuple
3. ✅ Executor caches connection objects (SoCo speakers by IP)
4. ✅ Commands routed through queue processor (not direct execution)
5. ✅ Cache-and-verify pattern: read back actual values after setting
6. ✅ Async wrappers for synchronous SoCo library calls

### SoCo Library Integration
- SoCo is **synchronous** - must wrap all calls in `asyncio.get_event_loop().run_in_executor()`
- Speaker objects cached by IP address to avoid reconnection overhead
- Properties accessed as attributes: `speaker.volume`, `speaker.mute`
- Methods called directly: `speaker.play()`, `speaker.pause()`

### Status Polling Behavior
- Polls every 3 seconds (Tier 1 - fast polling)
- Only polls devices with `status_available=True`
- Marks offline after 3 consecutive failures
- Stores transport state and track info in `connection_config`

## Next Steps (Future Enhancements)

### Phase 2: Advanced Playback
- [ ] Seek position control
- [ ] Queue management (add/remove tracks)
- [ ] Playlist support
- [ ] Radio station support

### Phase 3: Grouping
- [ ] Zone group discovery
- [ ] Create/modify groups
- [ ] Group volume control
- [ ] Stereo pair support

### Phase 4: Audio Settings
- [ ] EQ controls (bass, treble, loudness)
- [ ] Night mode / Speech enhancement
- [ ] Crossfade settings

### Phase 5: UI Integration
- [ ] Sonos speaker cards in frontend
- [ ] Playback controls UI
- [ ] Now playing display
- [ ] Group management UI

## Files Created/Modified

### Created
- `backend/app/services/sonos_discovery.py` (413 lines)
- `backend/app/commands/executors/audio/sonos_upnp.py` (465 lines)
- `docs/SONOS_IMPLEMENTATION_SUMMARY.md` (this file)

### Modified
- `backend/requirements.txt` - Added `soco==0.30.12`
- `backend/app/commands/executors/audio/__init__.py` - Exported `SonosUPnPExecutor`
- `backend/app/commands/router.py` - Added Sonos routing logic
- `backend/app/routers/audio_controllers.py` - Added Sonos endpoints (~300 lines added)
- `backend/app/services/tv_status_poller.py` - Added `_poll_sonos()` method

## Documentation References

For detailed technical information, see:
- `/docs/SONOS_NETWORK_CONTROL_INTEGRATION.md` - Comprehensive UPnP/SOAP protocol documentation
- `/docs/SONOS_INTEGRATION_STRATEGY.md` - Deep architectural analysis and Plena Matrix pattern mapping

## Conclusion

The Sonos integration is now **fully implemented** and follows all established patterns from the Bosch Plena Matrix integration. The system is ready for testing with actual Sonos hardware.

All commands are properly queued, status polling is active, and the API is complete for basic volume control and playback management.
