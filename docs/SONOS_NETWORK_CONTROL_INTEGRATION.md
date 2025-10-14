# Sonos Network Control Integration Guide

## Document Overview

This technical specification documents the implementation requirements for integrating Sonos speakers into TapCommand's audio control system. Sonos speakers use UPnP/SOAP protocol for local network control, exposing multiple services for transport, rendering, and topology management.

**Protocol**: UPnP/SOAP over HTTP (Port 1400)
**Discovery**: SSDP multicast (Port 1900) and mDNS
**Status**: Unofficial API (not publicly supported by Sonos)
**Alternative**: Official Cloud API exists but has limited local control capabilities

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Device Discovery](#device-discovery)
3. [UPnP Service Architecture](#upnp-service-architecture)
4. [Core Services & Commands](#core-services--commands)
5. [Querying Sonos Speaker State](#querying-sonos-speaker-state)
6. [SOAP Request/Response Format](#soap-requestresponse-format)
7. [Zone Group Topology](#zone-group-topology)
8. [Event Subscriptions](#event-subscriptions)
9. [Metadata & DIDL-Lite](#metadata--didl-lite)
10. [Implementation Patterns](#implementation-patterns)
11. [Python Integration (SoCo Library)](#python-integration-soco-library)
12. [TapCommand Integration Architecture](#tapcommand-integration-architecture)
13. [Database Schema Requirements](#database-schema-requirements)
14. [Command Executor Implementation](#command-executor-implementation)
15. [API Endpoint Design](#api-endpoint-design)
16. [Challenges & Considerations](#challenges--considerations)
17. [Testing & Validation](#testing--validation)
18. [References](#references)

---

## Architecture Overview

### Sonos System Architecture

Sonos operates as a distributed multi-room audio system with the following characteristics:

- **Speaker Types**: Individual speakers and stereo pairs
- **Group Model**: Speakers can be grouped dynamically; one speaker acts as "group coordinator"
- **Network Communication**: All control via HTTP/SOAP on port 1400
- **Discovery**: SSDP/mDNS for device discovery on local network
- **Specifications**: Implements MediaServer:4 and MediaRenderer:3 from Open Connectivity Foundation

### Key Architectural Concepts

1. **Zone**: A single Sonos device or a stereo pair
2. **Group**: One or more zones playing synchronized audio
3. **Coordinator**: The zone that controls playback for a group
4. **Household**: All Sonos devices on the same network/account

### TapCommand Integration Model

Sonos will integrate as **Virtual Controllers** with the following properties:

- **Controller Type**: `audio` (consistent with Bosch Praesensa/Plena Matrix)
- **Protocol**: `sonos_upnp`
- **Device Type**: Individual speakers represented as `VirtualDevice` with `device_type="audio_zone"`
- **Hostname Prefix**: `sonos-*` (e.g., `sonos-192168118`)
- **Control Model**: Direct HTTP control + queue-based command routing

---

## Device Discovery

### SSDP Discovery Process

Sonos speakers respond to SSDP (Simple Service Discovery Protocol) discovery requests sent via UDP multicast.

#### Discovery Request

```python
# SSDP M-SEARCH Request
message = (
    'M-SEARCH * HTTP/1.1\r\n'
    'HOST: 239.255.255.250:1900\r\n'
    'MAN: "ssdp:discover"\r\n'
    'MX: 3\r\n'
    'ST: urn:schemas-upnp-org:device:ZonePlayer:1\r\n'
    '\r\n'
)
```

**Parameters:**
- `HOST`: Multicast address for SSDP
- `MAN`: Discovery request identifier
- `MX`: Maximum wait time (seconds) for responses
- `ST`: Search target (Sonos-specific device type)

#### Discovery Response

Speakers respond with HTTP headers including:

```
HTTP/1.1 200 OK
CACHE-CONTROL: max-age = 1800
EXT:
LOCATION: http://192.168.1.100:1400/xml/device_description.xml
SERVER: Linux UPnP/1.0 Sonos/70.3-50220 (ZPS9)
ST: urn:schemas-upnp-org:device:ZonePlayer:1
USN: uuid:RINCON_B8E93791AF5C01400::urn:schemas-upnp-org:device:ZonePlayer:1
```

**Key Fields:**
- `LOCATION`: URL to device description XML (contains all service definitions)
- `SERVER`: Device model and firmware version
- `USN`: Unique device identifier (contains MAC address)

### Device Description XML

Each speaker exposes a comprehensive device description at:
```
http://{ip_address}:1400/xml/device_description.xml
```

**Contains:**
- Device model and manufacturer information
- List of all available UPnP services with control/event URLs
- Service SCPDs (Service Control Protocol Descriptions)

**Example Device Info:**
```xml
<device>
    <deviceType>urn:schemas-upnp-org:device:ZonePlayer:1</deviceType>
    <friendlyName>Living Room - Sonos Beam</friendlyName>
    <manufacturer>Sonos, Inc.</manufacturer>
    <modelName>Sonos Beam</modelName>
    <modelNumber>S14</modelNumber>
    <serialNumber>00-11-22-33-44-55:7</serialNumber>
    <UDN>uuid:RINCON_B8E93791AF5C01400</UDN>
    <serviceList>
        <service>
            <serviceType>urn:schemas-upnp-org:service:AVTransport:1</serviceType>
            <serviceId>urn:upnp-org:serviceId:AVTransport</serviceId>
            <controlURL>/MediaRenderer/AVTransport/Control</controlURL>
            <eventSubURL>/MediaRenderer/AVTransport/Event</eventSubURL>
            <SCPDURL>/xml/AVTransport1.xml</SCPDURL>
        </service>
        <!-- More services... -->
    </serviceList>
</device>
```

### mDNS Discovery (Alternative)

Sonos also supports mDNS (Multicast DNS) discovery:

**Service Type**: `_sonos._tcp.local.`
**Port**: 1400

Note: Sonos officially moved to prefer mDNS over SSDP in 2024, though SSDP still works.

### Discovery Implementation Requirements

For TapCommand integration:

1. **Periodic SSDP Scans**: Run discovery every 5-10 minutes to detect new speakers
2. **Store in `network_discoveries` table**: Similar to network TV discovery
3. **Adoption Flow**: User manually adopts discovered speakers via UI
4. **Create Virtual Controller**: One controller per household with multiple zones (speakers)
5. **Health Monitoring**: Periodic HTTP requests to `/xml/device_description.xml` to verify online status

---

## UPnP Service Architecture

Sonos exposes 16+ UPnP services. The most critical services for audio control:

### Core Services

| Service | Control URL | Purpose |
|---------|-------------|---------|
| **AVTransport** | `/MediaRenderer/AVTransport/Control` | Playback control (play/pause/stop/seek/queue) |
| **RenderingControl** | `/MediaRenderer/RenderingControl/Control` | Volume, mute, EQ (bass/treble) |
| **GroupRenderingControl** | `/MediaRenderer/GroupRenderingControl/Control` | Group-level volume control |
| **ZoneGroupTopology** | `/ZoneGroupTopology/Control` | Zone group management and topology |
| **Queue** | `/MediaRenderer/Queue/Control` | Queue browsing and management |
| **ContentDirectory** | `/MediaServer/ContentDirectory/Control` | Browse local music library |
| **AlarmClock** | `/AlarmClock/Control` | Alarm management |
| **DeviceProperties** | `/DeviceProperties/Control` | Device settings and properties |
| **GroupManagement** | `/GroupManagement/Control` | Join/unjoin speakers |
| **MusicServices** | `/MusicServices/Control` | Access to streaming services |

### Service Structure

Each service exposes:
- **Actions**: Methods that can be invoked (e.g., `Play`, `SetVolume`)
- **State Variables**: Values that can change and trigger events (e.g., `CurrentVolume`, `TransportState`)

**Action Format:**
```
ServiceName.ActionName(Parameter1, Parameter2, ...)
```

**Example:**
```
RenderingControl.SetVolume(InstanceID=0, Channel="Master", DesiredVolume=50)
```

---

## Core Services & Commands

### AVTransport Service

Controls media playback and transport state.

**Control URL**: `/MediaRenderer/AVTransport/Control`
**Event URL**: `/MediaRenderer/AVTransport/Event`

#### Key Actions

| Action | Parameters | Description |
|--------|------------|-------------|
| `Play` | `InstanceID=0, Speed="1"` | Start playback |
| `Pause` | `InstanceID=0` | Pause playback |
| `Stop` | `InstanceID=0` | Stop playback |
| `Next` | `InstanceID=0` | Skip to next track |
| `Previous` | `InstanceID=0` | Skip to previous track |
| `Seek` | `InstanceID=0, Unit, Target` | Seek to position (REL_TIME, TRACK_NR, TIME_DELTA) |
| `SetAVTransportURI` | `InstanceID=0, CurrentURI, CurrentURIMetaData` | Set media source (song, stream, queue) |
| `AddURIToQueue` | `InstanceID=0, EnqueuedURI, EnqueuedURIMetaData, DesiredFirstTrackNumberEnqueued, EnqueueAsNext` | Add track to queue |
| `RemoveTrackFromQueue` | `InstanceID=0, ObjectID, UpdateID` | Remove track from queue |
| `RemoveAllTracksFromQueue` | `InstanceID=0` | Clear queue |
| `SaveQueue` | `InstanceID=0, Title, ObjectID` | Save queue as playlist |
| `SetPlayMode` | `InstanceID=0, NewPlayMode` | Set repeat/shuffle (NORMAL, REPEAT_ALL, REPEAT_ONE, SHUFFLE, etc.) |
| `GetTransportInfo` | `InstanceID=0` | Get current transport state |
| `GetPositionInfo` | `InstanceID=0` | Get current track and position |
| `GetMediaInfo` | `InstanceID=0` | Get current media info |

**Transport States:**
- `PLAYING`: Actively playing
- `PAUSED_PLAYBACK`: Paused
- `STOPPED`: Stopped
- `TRANSITIONING`: Changing state

#### InstanceID Parameter

Always set to `0` for Sonos speakers (required by UPnP spec but not used).

### RenderingControl Service

Controls audio rendering parameters (volume, mute, EQ).

**Control URL**: `/MediaRenderer/RenderingControl/Control`
**Event URL**: `/MediaRenderer/RenderingControl/Event`

#### Key Actions

| Action | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `GetVolume` | `InstanceID=0, Channel="Master"` | `CurrentVolume` (0-100) | Get volume level |
| `SetVolume` | `InstanceID=0, Channel="Master", DesiredVolume` | - | Set volume (0-100) |
| `SetRelativeVolume` | `InstanceID=0, Channel="Master", Adjustment` | `NewVolume` | Adjust volume by delta |
| `GetMute` | `InstanceID=0, Channel="Master"` | `CurrentMute` (bool) | Get mute state |
| `SetMute` | `InstanceID=0, Channel="Master", DesiredMute` | - | Set mute state |
| `GetBass` | `InstanceID=0` | `CurrentBass` (-10 to +10) | Get bass level |
| `SetBass` | `InstanceID=0, DesiredBass` | - | Set bass level |
| `GetTreble` | `InstanceID=0` | `CurrentTreble` (-10 to +10) | Get treble level |
| `SetTreble` | `InstanceID=0, DesiredTreble` | - | Set treble level |
| `GetLoudness` | `InstanceID=0, Channel="Master"` | `CurrentLoudness` (bool) | Get loudness state |
| `SetLoudness` | `InstanceID=0, Channel="Master", DesiredLoudness` | - | Set loudness on/off |
| `GetEQ` | `InstanceID=0, EQType` | `CurrentValue` | Get EQ setting (DialogLevel, NightMode, etc.) |
| `SetEQ` | `InstanceID=0, EQType, DesiredValue` | - | Set EQ setting |

**Channel Options:**
- `Master`: Main volume
- `LF`: Left front (for stereo pairs)
- `RF`: Right front (for stereo pairs)

**EQ Types:**
- `DialogLevel`: Speech enhancement (0-100)
- `NightMode`: Night mode (bool)
- `SurroundLevel`: Surround volume adjustment
- `MusicSurroundLevel`: Music surround level

### GroupRenderingControl Service

Controls group-level audio settings (volume for all grouped speakers simultaneously).

**Control URL**: `/MediaRenderer/GroupRenderingControl/Control`

#### Key Actions

| Action | Parameters | Description |
|--------|------------|-------------|
| `GetGroupVolume` | `InstanceID=0` | Get group volume |
| `SetGroupVolume` | `InstanceID=0, DesiredVolume` | Set volume for entire group |
| `SetRelativeGroupVolume` | `InstanceID=0, Adjustment` | Adjust group volume by delta |
| `GetGroupMute` | `InstanceID=0` | Get group mute state |
| `SetGroupMute` | `InstanceID=0, DesiredMute` | Mute/unmute entire group |
| `SnapshotGroupVolume` | `InstanceID=0` | Create volume ratio snapshot for relative changes |

**Important**: Group volume operations only work when multiple speakers are grouped together.

### ZoneGroupTopology Service

Manages zone group configuration and topology discovery.

**Control URL**: `/ZoneGroupTopology/Control`
**Event URL**: `/ZoneGroupTopology/Event`

#### Key Actions

| Action | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `GetZoneGroupState` | - | `ZoneGroupState` (XML) | Get current topology of all groups |
| `GetZoneGroupAttributes` | - | `CurrentZoneGroupName, CurrentZoneGroupID, CurrentZonePlayerUUIDsInGroup` | Get current zone group info |
| `BeginSoftwareUpdate` | `UpdateURL, Flags` | - | Software update control |
| `CheckForUpdate` | `UpdateType, CachedOnly` | `UpdateItem` | Check for firmware updates |

**ZoneGroupState XML Structure:**
```xml
<ZoneGroups>
    <ZoneGroup Coordinator="RINCON_xxx" ID="RINCON_xxx:46">
        <ZoneGroupMember
            UUID="RINCON_xxx"
            Location="http://192.168.1.100:1400/xml/device_description.xml"
            ZoneName="Living Room"
            Icon="x-rincon-roomicon:living"
            SoftwareVersion="70.3-50220"
            IsZoneBridge="0"
            IsCoordinator="true"
            ChannelMapSet="RINCON_xxx:LF,LF;RINCON_yyy:RF,RF"/>
        <ZoneGroupMember ... />
    </ZoneGroup>
    <ZoneGroup .../>
</ZoneGroups>
```

**Key Concepts:**
- **Coordinator**: Speaker that controls group playback (usually first speaker in group)
- **Group ID**: Unique identifier for the group
- **ZoneGroupMember**: Individual speakers in the group

### GroupManagement Service

Controls grouping/ungrouping of speakers.

**Control URL**: `/GroupManagement/Control`

#### Key Actions

| Action | Parameters | Description |
|--------|------------|-------------|
| `AddMember` | `MemberID` | Add speaker to group |
| `RemoveMember` | `MemberID` | Remove speaker from group |
| `SetSourceAreaIds` | `DesiredSourceAreaIds` | Set source area IDs |

**Note**: For most grouping operations, use the AVTransport service's `BecomeCoordinatorOfStandaloneGroup` action or `SetAVTransportURI` with group URIs.

### DeviceProperties Service

Queries device information and settings.

**Control URL**: `/DeviceProperties/Control`

#### Key Actions

| Action | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `GetZoneInfo` | - | `SerialNumber, SoftwareVersion, HardwareVersion, IPAddress, MACAddress, etc.` | Get comprehensive device information |
| `GetZoneAttributes` | - | `CurrentZoneName, CurrentIcon, CurrentConfiguration` | Get zone name and settings |
| `GetHouseholdID` | - | `CurrentHouseholdID` | Get household identifier |
| `GetButtonState` | - | `State` | Get device button state |
| `GetButtonLockState` | - | `CurrentButtonLockState` | Get button lock state (On/Off) |
| `GetLEDState` | - | `CurrentLEDState` | Get LED state (On/Off) |

**GetZoneInfo Response Example:**
```xml
<SerialNumber>00-11-22-33-44-55:7</SerialNumber>
<SoftwareVersion>70.3-50220</SoftwareVersion>
<DisplaySoftwareVersion>15.7</DisplaySoftwareVersion>
<HardwareVersion>1.20.1.7-2</HardwareVersion>
<IPAddress>192.168.1.100</IPAddress>
<MACAddress>00:11:22:33:44:55</MACAddress>
<CopyrightInfo>© 2004-2024 Sonos, Inc.</CopyrightInfo>
<ExtraInfo>OTP: 1.1.1(1-16-4-zp5s-0.5)</ExtraInfo>
<HTAudioIn>0</HTAudioIn>
<Flags>0</Flags>
```

---

## Querying Sonos Speaker State

Sonos speakers can be queried for current playback status, volume, track information, and device properties using various UPnP services.

### Transport State Queries (AVTransport Service)

#### GetTransportInfo

Returns current playback state.

**SOAP Action**: `GetTransportInfo`
**Parameters**: `InstanceID=0`

**Returns:**
- `CurrentTransportState`: Playback status (`PLAYING`, `PAUSED_PLAYBACK`, `STOPPED`, `TRANSITIONING`, `NO_MEDIA_PRESENT`)
- `CurrentTransportStatus`: Transport status (typically `OK`)
- `CurrentSpeed`: Playback speed (typically `1`)

**Example Request:**
```python
result = speaker.get_current_transport_info()
print(result['current_transport_state'])  # "PLAYING", "STOPPED", etc.
```

**Direct SOAP Call:**
```xml
<u:GetTransportInfo xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
    <InstanceID>0</InstanceID>
</u:GetTransportInfo>
```

#### GetPositionInfo

Returns detailed information about currently playing track and playback position.

**SOAP Action**: `GetPositionInfo`
**Parameters**: `InstanceID=0`

**Returns:**
- `Track`: Current track number in queue
- `TrackDuration`: Total track duration (HH:MM:SS format)
- `TrackMetaData`: DIDL-Lite XML with track metadata (title, artist, album, artwork)
- `TrackURI`: URI of current track
- `RelTime`: Current playback position (HH:MM:SS)
- `AbsTime`: Absolute time position
- `RelCount`: Relative position counter
- `AbsCount`: Absolute position counter

**Example (SoCo):**
```python
track_info = speaker.get_current_track_info()
print(f"Now playing: {track_info['title']} by {track_info['artist']}")
print(f"Album: {track_info['album']}")
print(f"Position: {track_info['position']} / {track_info['duration']}")
print(f"Track URI: {track_info['uri']}")
print(f"Album Art: {track_info['album_art']}")
print(f"Playlist position: {track_info['playlist_position']}")
```

**Response Structure:**
```python
{
    'title': 'Song Title',
    'artist': 'Artist Name',
    'album': 'Album Name',
    'album_art': 'http://192.168.1.100:1400/getaa?...',
    'position': '0:02:30',      # Current position
    'duration': '0:03:45',      # Total duration
    'uri': 'x-sonos-spotify:...',
    'playlist_position': '3',   # Position in queue
    'metadata': '...'           # Full DIDL-Lite XML
}
```

#### GetMediaInfo

Returns information about current media source.

**SOAP Action**: `GetMediaInfo`
**Parameters**: `InstanceID=0`

**Returns:**
- `NrTracks`: Total number of tracks in queue
- `MediaDuration`: Total media duration
- `CurrentURI`: Current media source URI
- `CurrentURIMetaData`: DIDL-Lite XML metadata for media
- `NextURI`: URI of next track (if available)
- `NextURIMetaData`: Metadata for next track
- `PlayMedium`: Media type (e.g., `NETWORK`, `NONE`)
- `RecordMedium`: Recording medium (typically `NOT_IMPLEMENTED`)
- `WriteStatus`: Write status (typically `NOT_IMPLEMENTED`)

**Example:**
```python
media_info = speaker.avTransport.GetMediaInfo([('InstanceID', 0)])
print(f"Total tracks: {media_info['NrTracks']}")
print(f"Current URI: {media_info['CurrentURI']}")
```

#### GetTransportSettings

Returns current playback mode settings.

**SOAP Action**: `GetTransportSettings`
**Parameters**: `InstanceID=0`

**Returns:**
- `PlayMode`: Current playback mode
  - `NORMAL`: Sequential playback
  - `REPEAT_ALL`: Repeat entire queue
  - `REPEAT_ONE`: Repeat current track
  - `SHUFFLE_NOREPEAT`: Shuffle without repeat
  - `SHUFFLE`: Shuffle with repeat
  - `SHUFFLE_REPEAT_ONE`: Shuffle and repeat current
- `RecQualityMode`: Recording quality mode (typically `NOT_IMPLEMENTED`)

**Example:**
```python
settings = speaker.avTransport.GetTransportSettings([('InstanceID', 0)])
print(f"Play mode: {settings['PlayMode']}")
```

### Volume & Audio State Queries (RenderingControl Service)

#### GetVolume

Returns current volume level for a speaker.

**SOAP Action**: `GetVolume`
**Parameters**:
- `InstanceID=0`
- `Channel="Master"` (or `"LF"`, `"RF"` for stereo pairs)

**Returns:**
- `CurrentVolume`: Integer 0-100

**Example (SoCo):**
```python
current_volume = speaker.volume
print(f"Current volume: {current_volume}%")

# Direct service call
volume = speaker.renderingControl.GetVolume([
    ('InstanceID', 0),
    ('Channel', 'Master')
])
print(f"Volume: {volume['CurrentVolume']}")
```

#### GetMute

Returns current mute state.

**SOAP Action**: `GetMute`
**Parameters**:
- `InstanceID=0`
- `Channel="Master"`

**Returns:**
- `CurrentMute`: Boolean (`1` = muted, `0` = unmuted)

**Example (SoCo):**
```python
is_muted = speaker.mute
print(f"Muted: {is_muted}")
```

#### GetBass

Returns current bass level.

**SOAP Action**: `GetBass`
**Parameters**: `InstanceID=0`

**Returns:**
- `CurrentBass`: Integer -10 to +10

**Example (SoCo):**
```python
bass_level = speaker.bass
print(f"Bass: {bass_level}")
```

#### GetTreble

Returns current treble level.

**SOAP Action**: `GetTreble`
**Parameters**: `InstanceID=0`

**Returns:**
- `CurrentTreble`: Integer -10 to +10

**Example (SoCo):**
```python
treble_level = speaker.treble
print(f"Treble: {treble_level}")
```

#### GetLoudness

Returns current loudness compensation state.

**SOAP Action**: `GetLoudness`
**Parameters**:
- `InstanceID=0`
- `Channel="Master"`

**Returns:**
- `CurrentLoudness`: Boolean (`1` = enabled, `0` = disabled)

**Example (SoCo):**
```python
loudness_enabled = speaker.loudness
print(f"Loudness: {loudness_enabled}")
```

#### GetEQ

Returns specific EQ setting value.

**SOAP Action**: `GetEQ`
**Parameters**:
- `InstanceID=0`
- `EQType`: Type of EQ setting (e.g., `NightMode`, `DialogLevel`, `SurroundLevel`)

**Returns:**
- `CurrentValue`: Value depends on EQ type

**Common EQ Types:**
- `NightMode`: Boolean (0/1)
- `DialogLevel`: Integer 0-100
- `SurroundLevel`: Integer
- `MusicSurroundLevel`: Integer
- `SubGain`: Integer (-10 to +10)

### Device Information Queries (DeviceProperties Service)

#### GetZoneInfo

Returns comprehensive device information.

**SOAP Action**: `GetZoneInfo`
**Parameters**: None

**Returns:**
```python
{
    'SerialNumber': '00-11-22-33-44-55:7',
    'SoftwareVersion': '70.3-50220',
    'DisplaySoftwareVersion': '15.7',
    'HardwareVersion': '1.20.1.7-2',
    'IPAddress': '192.168.1.100',
    'MACAddress': '00:11:22:33:44:55',
    'CopyrightInfo': '© 2004-2024 Sonos, Inc.',
    'ExtraInfo': 'OTP: 1.1.1(1-16-4-zp5s-0.5)',
    'HTAudioIn': '0',
    'Flags': '0'
}
```

**Example (SoCo):**
```python
# Get speaker info (includes zone info + more)
info = speaker.get_speaker_info()
print(f"Zone Name: {info['zone_name']}")
print(f"Model: {info['model_name']}")  # e.g., "Sonos Beam"
print(f"Software Version: {info['software_version']}")
print(f"Hardware Version: {info['hardware_version']}")
print(f"MAC Address: {info['mac_address']}")
print(f"Serial Number: {info['serial_number']}")
print(f"UID: {info['uid']}")  # UUID like RINCON_xxx
```

#### GetZoneAttributes

Returns zone name and configuration.

**SOAP Action**: `GetZoneAttributes`
**Parameters**: None

**Returns:**
- `CurrentZoneName`: Friendly name of zone (e.g., "Living Room")
- `CurrentIcon`: Icon identifier
- `CurrentConfiguration`: Configuration settings

**Example (SoCo):**
```python
zone_name = speaker.player_name
print(f"Zone Name: {zone_name}")

# Or direct service call
attrs = speaker.deviceProperties.GetZoneAttributes()
print(f"Zone: {attrs['CurrentZoneName']}")
print(f"Icon: {attrs['CurrentIcon']}")
```

#### GetHouseholdID

Returns household identifier (all speakers in same household share this ID).

**SOAP Action**: `GetHouseholdID`
**Parameters**: None

**Returns:**
- `CurrentHouseholdID`: Household UUID

**Example:**
```python
household_id = speaker.deviceProperties.GetHouseholdID()
print(f"Household ID: {household_id['CurrentHouseholdID']}")
```

### Group Topology Queries (ZoneGroupTopology Service)

#### GetZoneGroupState

Returns complete topology of all speaker groups in household.

**SOAP Action**: `GetZoneGroupState`
**Parameters**: None

**Returns:**
- `ZoneGroupState`: XML document describing all groups and members

**Example (SoCo):**
```python
# Get all groups in household
all_groups = speaker.all_groups
for group in all_groups:
    print(f"Group Coordinator: {group.coordinator.player_name}")
    print(f"Group Members:")
    for member in group.members:
        print(f"  - {member.player_name} ({member.ip_address})")

# Check if speaker is coordinator
is_coordinator = speaker.is_coordinator
print(f"Is Coordinator: {is_coordinator}")

# Get speaker's group
group = speaker.group
coordinator = group.coordinator
print(f"My coordinator: {coordinator.player_name}")
```

**ZoneGroupState XML Structure:**
```xml
<ZoneGroups>
    <ZoneGroup Coordinator="RINCON_xxx" ID="RINCON_xxx:46">
        <ZoneGroupMember
            UUID="RINCON_xxx"
            Location="http://192.168.1.100:1400/xml/device_description.xml"
            ZoneName="Living Room"
            Icon="x-rincon-roomicon:living"
            SoftwareVersion="70.3-50220"
            IsZoneBridge="0"
            IsCoordinator="true"
            ChannelMapSet="RINCON_xxx:LF,LF;RINCON_yyy:RF,RF"/>
        <ZoneGroupMember
            UUID="RINCON_yyy"
            Location="http://192.168.1.101:1400/xml/device_description.xml"
            ZoneName="Kitchen"
            Icon="x-rincon-roomicon:kitchen"
            SoftwareVersion="70.3-50220"
            IsZoneBridge="0"
            IsCoordinator="false"/>
    </ZoneGroup>
    <ZoneGroup Coordinator="RINCON_zzz" ID="RINCON_zzz:47">
        <ZoneGroupMember ... />
    </ZoneGroup>
</ZoneGroups>
```

#### GetZoneGroupAttributes

Returns current zone group name and member list.

**SOAP Action**: `GetZoneGroupAttributes`
**Parameters**: None

**Returns:**
- `CurrentZoneGroupName`: Name of current group
- `CurrentZoneGroupID`: Group identifier
- `CurrentZonePlayerUUIDsInGroup`: Comma-separated list of member UUIDs

### Additional Status Properties (SoCo Library)

The SoCo library exposes many additional properties for querying speaker state:

```python
from soco import SoCo

speaker = SoCo('192.168.1.100')

# Basic properties
print(f"Player Name: {speaker.player_name}")
print(f"IP Address: {speaker.ip_address}")
print(f"UID: {speaker.uid}")  # UUID like RINCON_xxx
print(f"Is Visible: {speaker.is_visible}")
print(f"Is Coordinator: {speaker.is_coordinator}")

# Playback state
print(f"Is Playing: {speaker.is_playing_radio}")
print(f"Is Playing TV: {speaker.is_playing_tv}")
print(f"Is Playing Line-In: {speaker.is_playing_line_in}")

# Audio properties
print(f"Volume: {speaker.volume}")
print(f"Muted: {speaker.mute}")
print(f"Bass: {speaker.bass}")
print(f"Treble: {speaker.treble}")
print(f"Loudness: {speaker.loudness}")

# Status light
print(f"Status Light: {speaker.status_light}")  # LED on/off

# Balance (for stereo pairs)
balance = speaker.balance
print(f"Balance: L={balance[0]}, R={balance[1]}")

# Battery info (for supported speakers like Roam, Move)
try:
    battery = speaker.get_battery_info()
    print(f"Battery: {battery['percentage']}%")
    print(f"Charging: {battery['is_charging']}")
    print(f"Power Source: {battery['power_source']}")
except Exception:
    print("Battery info not available")

# Music source
source = speaker.music_source
print(f"Music Source: {source}")  # 'LIBRARY', 'RADIO', 'TV', etc.

# Available actions (what commands can be sent)
actions = speaker.available_actions
print(f"Available Actions: {actions}")
```

### Status Polling Implementation

For TapCommand integration, implement periodic status polling to keep database cache up to date:

```python
async def poll_sonos_status(speaker: SoCo, zone: VirtualDevice, db: Session):
    """
    Poll Sonos speaker for current status and update database cache

    Should be called periodically (e.g., every 10-30 seconds)
    """
    try:
        # Get volume and mute status
        volume = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: speaker.volume
        )
        mute = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: speaker.mute
        )

        # Update database cache
        zone.cached_volume_level = volume
        zone.cached_mute_status = mute
        zone.is_online = True
        zone.last_seen = datetime.now()

        # Optionally get transport state
        transport_info = await asyncio.get_event_loop().run_in_executor(
            None,
            speaker.get_current_transport_info
        )
        transport_state = transport_info['current_transport_state']

        # Store in connection_config
        if zone.connection_config is None:
            zone.connection_config = {}
        zone.connection_config['transport_state'] = transport_state

        # Optionally get current track info
        if transport_state == 'PLAYING':
            track_info = await asyncio.get_event_loop().run_in_executor(
                None,
                speaker.get_current_track_info
            )
            zone.connection_config['current_track'] = {
                'title': track_info.get('title'),
                'artist': track_info.get('artist'),
                'album': track_info.get('album'),
                'position': track_info.get('position'),
                'duration': track_info.get('duration')
            }

        db.commit()
        logger.debug(f"Updated status for {zone.device_name}: vol={volume}, mute={mute}, state={transport_state}")

        return True

    except Exception as e:
        logger.error(f"Failed to poll status for {zone.device_name}: {e}")
        zone.is_online = False
        db.commit()
        return False


# Usage in background service
async def status_polling_service():
    """Background service to poll all Sonos speakers"""
    while True:
        try:
            db = SessionLocal()

            # Get all Sonos zones
            zones = db.query(VirtualDevice).join(VirtualController).filter(
                VirtualDevice.device_type == "audio_zone",
                VirtualDevice.protocol == "sonos_upnp",
                VirtualDevice.is_active == True
            ).all()

            # Poll each zone
            for zone in zones:
                try:
                    speaker = SoCo(zone.ip_address)
                    await poll_sonos_status(speaker, zone, db)
                except Exception as e:
                    logger.error(f"Failed to poll {zone.device_name}: {e}")

                # Small delay between speakers
                await asyncio.sleep(0.5)

            db.close()

            # Wait before next poll cycle (e.g., 15 seconds)
            await asyncio.sleep(15)

        except Exception as e:
            logger.error(f"Status polling service error: {e}")
            await asyncio.sleep(5)
```

### Query Response Caching Strategy

**Recommended caching approach:**

1. **Volume/Mute**: Cache in `VirtualDevice` table, poll every 15-30 seconds
2. **Transport State**: Cache in `connection_config` JSON, poll every 15-30 seconds
3. **Current Track**: Cache in `connection_config`, only poll when playing
4. **Device Info**: Cache on discovery, rarely changes
5. **Group Topology**: Cache and refresh every 30-60 seconds or on group change events

**Benefits:**
- Reduces network traffic to speakers
- Provides fast API responses from database
- Tolerates brief network interruptions
- Enables multi-user synchronization

**Trade-offs:**
- Status may be slightly stale (15-30 second delay)
- External changes (via Sonos app) take time to reflect
- Solution: Optional event subscriptions for real-time updates

---

## SOAP Request/Response Format

Sonos uses SOAP 1.1 protocol over HTTP for all control commands.

### Request Structure

**HTTP Method**: `POST`
**Content-Type**: `text/xml; charset="utf-8"`

**Required Headers:**
```http
POST /MediaRenderer/AVTransport/Control HTTP/1.1
HOST: 192.168.1.100:1400
Content-Type: text/xml; charset="utf-8"
Content-Length: [length]
SOAPACTION: "urn:schemas-upnp-org:service:AVTransport:1#Play"
```

**SOAP Body:**
```xml
<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
            s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
    <s:Body>
        <u:Play xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
            <InstanceID>0</InstanceID>
            <Speed>1</Speed>
        </u:Play>
    </s:Body>
</s:Envelope>
```

**Key Components:**
- `SOAPACTION` header: Service namespace + `#` + action name
- `s:Envelope`: SOAP envelope wrapper
- `u:ActionName`: Action element with service namespace
- Parameters as child XML elements

### Response Structure

**Success Response (HTTP 200):**
```xml
<?xml version="1.0"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
            s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
    <s:Body>
        <u:PlayResponse xmlns:u="urn:schemas-upnp-org:service:AVTransport:1"/>
    </s:Body>
</s:Envelope>
```

**Response with Return Values:**
```xml
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
            s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
    <s:Body>
        <u:GetVolumeResponse xmlns:u="urn:schemas-upnp-org:service:RenderingControl:1">
            <CurrentVolume>45</CurrentVolume>
        </u:GetVolumeResponse>
    </s:Body>
</s:Envelope>
```

### Error Response (HTTP 500)

```xml
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
            s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
    <s:Body>
        <s:Fault>
            <faultcode>s:Client</faultcode>
            <faultstring>UPnPError</faultstring>
            <detail>
                <UPnPError xmlns="urn:schemas-upnp-org:control-1-0">
                    <errorCode>501</errorCode>
                    <errorDescription>Action Failed</errorDescription>
                </UPnPError>
            </detail>
        </s:Fault>
    </s:Body>
</s:Envelope>
```

**Common UPnP Error Codes:**
- `400`: Bad Request
- `401`: Invalid Action
- `402`: Invalid Args
- `501`: Action Failed
- `600`: Argument Value Invalid
- `608`: Signature Missing
- `714`: Illegal MIDI Message

### SOAP Request Example (SetVolume)

```python
import requests

ip_address = "192.168.1.100"
url = f"http://{ip_address}:1400/MediaRenderer/RenderingControl/Control"

headers = {
    "Content-Type": "text/xml; charset=utf-8",
    "SOAPACTION": '"urn:schemas-upnp-org:service:RenderingControl:1#SetVolume"'
}

body = """<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
            s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
    <s:Body>
        <u:SetVolume xmlns:u="urn:schemas-upnp-org:service:RenderingControl:1">
            <InstanceID>0</InstanceID>
            <Channel>Master</Channel>
            <DesiredVolume>50</DesiredVolume>
        </u:SetVolume>
    </s:Body>
</s:Envelope>"""

response = requests.post(url, headers=headers, data=body, timeout=5)
print(response.status_code, response.text)
```

---

## Zone Group Topology

### Understanding Groups

Sonos speakers can be:
1. **Standalone**: Single speaker or stereo pair playing independently
2. **Grouped**: Multiple speakers playing synchronized audio
3. **Coordinator**: The speaker that controls playback for a group

### Group Coordinator Model

When speakers are grouped:
- One speaker is designated the **coordinator**
- All playback commands must be sent to the coordinator
- Volume/mute can be sent to individual speakers or the group coordinator

**Determining the Coordinator:**
```python
# Get zone group state
response = call_soap_action(
    ip_address="192.168.1.100",
    service="ZoneGroupTopology",
    action="GetZoneGroupState"
)

# Parse XML to find coordinator
# Coordinator="RINCON_xxx" attribute identifies coordinator
# Match against speaker UUID to find coordinator IP
```

### Group Operations

#### Join a Group

To join Speaker B to Speaker A's group:

```python
# On Speaker B, set AVTransport URI to Speaker A's group URI
uri = f"x-rincon:{speaker_a_uuid}"

call_soap_action(
    ip_address=speaker_b_ip,
    service="AVTransport",
    action="SetAVTransportURI",
    params={
        "InstanceID": "0",
        "CurrentURI": uri,
        "CurrentURIMetaData": ""
    }
)
```

#### Leave a Group (Unjoin)

To make a speaker standalone:

```python
call_soap_action(
    ip_address=speaker_ip,
    service="AVTransport",
    action="BecomeCoordinatorOfStandaloneGroup",
    params={"InstanceID": "0"}
)
```

### Party Mode (Group All Speakers)

To group all speakers in the household:

1. Get all speakers via `GetZoneGroupState`
2. Pick one speaker as target coordinator
3. Call `SetAVTransportURI` on each other speaker with coordinator's UUID

---

## Event Subscriptions

Sonos supports UPnP event subscriptions to receive real-time notifications when state variables change (volume, playback state, etc.).

### Subscription Process

1. **Create HTTP Callback Server**: Run HTTP server to receive NOTIFY requests
2. **Send SUBSCRIBE Request**: Subscribe to service events with callback URL
3. **Receive Initial State**: Immediate NOTIFY with current state
4. **Receive Updates**: NOTIFY requests when state variables change
5. **Renew Subscription**: Re-subscribe before timeout (typically 1800 seconds)

### Subscribe Request

**HTTP Method**: `SUBSCRIBE`
**URL**: Service event subscription URL (e.g., `/MediaRenderer/AVTransport/Event`)

```http
SUBSCRIBE /MediaRenderer/AVTransport/Event HTTP/1.1
HOST: 192.168.1.100:1400
CALLBACK: <http://192.168.1.50:3400/>
NT: upnp:event
TIMEOUT: Second-1800
```

**Headers:**
- `CALLBACK`: URL where Sonos will send NOTIFY requests (must be reachable by speaker)
- `NT`: Notification type (always `upnp:event`)
- `TIMEOUT`: Desired subscription duration in seconds

**Response:**
```http
HTTP/1.1 200 OK
SID: uuid:RINCON_xxx-1234567890
TIMEOUT: Second-1800
```

**Key Response Headers:**
- `SID`: Subscription ID (used for renewal and unsubscribe)
- `TIMEOUT`: Actual subscription duration granted

### NOTIFY Request Format

When a state variable changes, Sonos sends:

```http
NOTIFY / HTTP/1.1
HOST: 192.168.1.50:3400
CONTENT-TYPE: text/xml; charset="utf-8"
NT: upnp:event
NTS: upnp:propchange
SID: uuid:RINCON_xxx-1234567890
SEQ: 0

<?xml version="1.0"?>
<e:propertyset xmlns:e="urn:schemas-upnp-org:event-1-0">
    <e:property>
        <LastChange>
            &lt;Event xmlns="urn:schemas-upnp-org:metadata-1-0/AVT/"&gt;
                &lt;InstanceID val="0"&gt;
                    &lt;TransportState val="PLAYING"/&gt;
                    &lt;CurrentTrackURI val="x-sonos-spotify:..."/&gt;
                    &lt;CurrentTrackMetaData val="..."/&gt;
                &lt;/InstanceID&gt;
            &lt;/Event&gt;
        </LastChange>
    </e:property>
</e:propertyset>
```

**Important**: `LastChange` contains XML-encoded XML. Must decode twice to extract actual values.

### Renew Subscription

Before timeout expires, renew using SID:

```http
SUBSCRIBE /MediaRenderer/AVTransport/Event HTTP/1.1
HOST: 192.168.1.100:1400
SID: uuid:RINCON_xxx-1234567890
TIMEOUT: Second-1800
```

### Unsubscribe

```http
UNSUBSCRIBE /MediaRenderer/AVTransport/Event HTTP/1.1
HOST: 192.168.1.100:1400
SID: uuid:RINCON_xxx-1234567890
```

### Subscribable Services

Key services that emit useful events:

- **AVTransport**: Playback state, current track, position
- **RenderingControl**: Volume, mute, EQ changes
- **ZoneGroupTopology**: Group configuration changes
- **Queue**: Queue modifications

### Event Implementation Notes

For TapCommand:

1. **Optional Feature**: Events are useful but not required for basic control
2. **Callback Server**: Need to run HTTP server on backend to receive notifications
3. **Firewall**: Ensure Sonos speakers can reach backend IP
4. **Use Cases**: Real-time volume display, playback state monitoring, multi-user synchronization

---

## Metadata & DIDL-Lite

Sonos uses DIDL-Lite (Digital Item Declaration Language - Lite) XML format for track metadata.

### DIDL-Lite Overview

DIDL-Lite is a subset of the MPEG-21 DIDL specification, part of the UPnP ContentDirectory service standard.

**Purpose**: Describe media items (tracks, albums, playlists, radio stations)

**Structure**: XML with standard namespaces for metadata elements

### DIDL-Lite XML Format

```xml
<DIDL-Lite xmlns:dc="http://purl.org/dc/elements/1.1/"
           xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"
           xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/"
           xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/">
    <item id="..." parentID="..." restricted="true">
        <dc:title>Track Title</dc:title>
        <dc:creator>Artist Name</dc:creator>
        <upnp:album>Album Name</upnp:album>
        <upnp:albumArtURI>http://192.168.1.100:1400/getaa?...</upnp:albumArtURI>
        <upnp:class>object.item.audioItem.musicTrack</upnp:class>
        <res protocolInfo="http-get:*:audio/mpeg:*" duration="0:03:45">
            http://192.168.1.100:1400/path/to/track.mp3
        </res>
    </item>
</DIDL-Lite>
```

### Key Elements

| Element | Description |
|---------|-------------|
| `<dc:title>` | Track title |
| `<dc:creator>` | Artist/creator name |
| `<upnp:album>` | Album name |
| `<upnp:albumArtURI>` | Album artwork URL |
| `<upnp:class>` | Media class (musicTrack, audioStream, playlistContainer, etc.) |
| `<res>` | Resource URI (actual media location) |
| `duration` | Track duration (HH:MM:SS format) |
| `protocolInfo` | Media protocol and format |

### Common UPnP Classes

- `object.item.audioItem.musicTrack`: Music track
- `object.item.audioItem.audioBroadcast`: Radio station
- `object.container.album.musicAlbum`: Album
- `object.container.playlistContainer`: Playlist

### Minimal DIDL-Lite

For most operations, only URI and protocol info are required:

```xml
<DIDL-Lite xmlns:dc="http://purl.org/dc/elements/1.1/"
           xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"
           xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/">
    <item id="-1" parentID="-1" restricted="true">
        <dc:title></dc:title>
        <upnp:class>object.item.audioItem.audioBroadcast</upnp:class>
        <res protocolInfo="http-get:*:*:*">http://stream.url/radio.mp3</res>
    </item>
</DIDL-Lite>
```

### XML Encoding

DIDL-Lite metadata must be XML-escaped when passed as SOAP parameters:

```python
import xml.sax.saxutils as saxutils

metadata = """<DIDL-Lite xmlns="...">...</DIDL-Lite>"""
escaped_metadata = saxutils.escape(metadata)
```

**Example:**
```xml
<CurrentURIMetaData>&lt;DIDL-Lite xmlns=&quot;...&quot;&gt;...&lt;/DIDL-Lite&gt;</CurrentURIMetaData>
```

### Use Cases in TapCommand

For audio zone control, DIDL-Lite is primarily needed for:

1. **Setting Transport URI**: When playing specific tracks/streams
2. **Adding to Queue**: When enqueueing media
3. **Reading Current Track**: Parse metadata from `GetPositionInfo` response

For basic volume/playback control, metadata handling is **not required**.

---

## Implementation Patterns

### Pattern 1: Direct SOAP Calls (Low-Level)

Manually construct and send SOAP requests via HTTP.

**Advantages:**
- Full control over requests
- No external dependencies
- Lightweight

**Disadvantages:**
- Verbose boilerplate code
- Manual XML parsing
- Error-prone

**Example:**
```python
import requests

def set_volume(ip_address: str, volume: int):
    url = f"http://{ip_address}:1400/MediaRenderer/RenderingControl/Control"
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPACTION": '"urn:schemas-upnp-org:service:RenderingControl:1#SetVolume"'
    }
    body = f"""<?xml version="1.0"?>
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
                s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
        <s:Body>
            <u:SetVolume xmlns:u="urn:schemas-upnp-org:service:RenderingControl:1">
                <InstanceID>0</InstanceID>
                <Channel>Master</Channel>
                <DesiredVolume>{volume}</DesiredVolume>
            </u:SetVolume>
        </s:Body>
    </s:Envelope>"""

    response = requests.post(url, headers=headers, data=body, timeout=5)
    return response.status_code == 200
```

### Pattern 2: SoCo Library (Recommended)

Use the mature Python SoCo library for high-level control.

**Advantages:**
- Production-ready
- High-level API
- Active maintenance
- Event subscription handling
- Music service integration

**Disadvantages:**
- External dependency
- Opinionated API

**Example:**
```python
from soco import SoCo

# Create speaker object
speaker = SoCo('192.168.1.100')

# Playback control
speaker.play()
speaker.pause()
speaker.volume = 50

# Get current track
track = speaker.get_current_track_info()
print(track['title'], track['artist'])

# Queue management
speaker.add_uri_to_queue('http://stream.url/radio.mp3')
speaker.play_from_queue(0)

# Grouping
other_speaker = SoCo('192.168.1.101')
speaker.join(other_speaker)
```

### Pattern 3: Hybrid Approach (TapCommand Recommended)

Use SoCo library wrapped in TapCommand's command executor pattern.

**Advantages:**
- Leverage SoCo's robustness
- Integrate with TapCommand's queue/retry logic
- Consistent error handling
- Easy to test

**Implementation:**
```python
class SonosExecutor(CommandExecutor):
    def __init__(self, db: Session):
        self.db = db
        self._speakers: Dict[str, SoCo] = {}  # Cache speaker objects

    def can_execute(self, command: Command) -> bool:
        return (
            command.device_type == "audio_zone" and
            command.protocol == "sonos_upnp"
        )

    async def execute(self, command: Command) -> ExecutionResult:
        speaker = self._get_speaker(command.controller_id)

        if command.command == "set_volume":
            volume = command.parameters.get("volume", 50)
            speaker.volume = volume
            return ExecutionResult(success=True, message=f"Set volume to {volume}")

        elif command.command == "play":
            speaker.play()
            return ExecutionResult(success=True, message="Started playback")

        # ... more commands

    def _get_speaker(self, controller_id: str) -> SoCo:
        if controller_id not in self._speakers:
            # Get IP from database
            controller = self.db.query(VirtualController).filter(
                VirtualController.controller_id == controller_id
            ).first()
            self._speakers[controller_id] = SoCo(controller.ip_address)
        return self._speakers[controller_id]
```

---

## Python Integration (SoCo Library)

### Installation

```bash
pip install soco
```

**Requirements:**
- Python 3.6+
- Network access to Sonos speakers
- Dependencies: requests, xmltodict, appdirs

### Basic Usage

#### Discovery

```python
from soco import discover

# Discover all speakers on network
speakers = discover()
for speaker in speakers:
    print(f"{speaker.player_name} - {speaker.ip_address}")

# Get any speaker (useful for testing)
from soco.discovery import any_soco
speaker = any_soco()

# Get speaker by IP
from soco import SoCo
speaker = SoCo('192.168.1.100')
```

#### Playback Control

```python
speaker = SoCo('192.168.1.100')

# Basic transport controls
speaker.play()
speaker.pause()
speaker.stop()
speaker.next()
speaker.previous()

# Seek to position (HH:MM:SS format)
speaker.seek("0:02:30")

# Get transport info
info = speaker.get_current_transport_info()
print(info['current_transport_state'])  # PLAYING, PAUSED_PLAYBACK, STOPPED

# Get current track
track = speaker.get_current_track_info()
print(f"Now playing: {track['title']} by {track['artist']}")
print(f"Position: {track['position']} / {track['duration']}")
```

#### Volume Control

```python
# Get/set volume (0-100)
current_volume = speaker.volume
speaker.volume = 50
speaker.volume += 5  # Increase by 5

# Mute/unmute
speaker.mute = True
speaker.mute = False

# Bass and treble (-10 to +10)
speaker.bass = 3
speaker.treble = -2

# Loudness (night mode)
speaker.loudness = True
```

#### Queue Management

```python
# Get queue
queue = speaker.get_queue(start=0, max_items=100)
for item in queue:
    print(f"{item.title} - {item.creator}")

# Add to queue
speaker.add_uri_to_queue('http://stream.url/radio.mp3')
speaker.add_to_queue(track_object)

# Clear queue
speaker.clear_queue()

# Play from queue (0-indexed)
speaker.play_from_queue(0)
```

#### Grouping

```python
speaker_a = SoCo('192.168.1.100')
speaker_b = SoCo('192.168.1.101')

# Join speaker_b to speaker_a's group
speaker_b.join(speaker_a)

# Unjoin (make standalone)
speaker_b.unjoin()

# Party mode (join all speakers to this one)
speaker_a.partymode()

# Get group members
group = speaker_a.group
for member in group.members:
    print(member.player_name)

# Get group coordinator
coordinator = speaker_a.group.coordinator
print(f"Coordinator: {coordinator.player_name}")
```

#### Event Subscriptions

```python
from soco.events import event_listener

# Start event listener (runs HTTP server)
event_listener.start()

# Subscribe to AVTransport events
sub = speaker.avTransport.subscribe()

def on_event(event):
    print(f"Transport state changed: {event.variables}")

sub.callback = on_event

# ... events will trigger callback ...

# Unsubscribe
sub.unsubscribe()
```

### SoCo Service Classes

Access services directly for advanced control:

```python
# AVTransport service
speaker.avTransport.Play([('InstanceID', 0), ('Speed', '1')])

# RenderingControl service
speaker.renderingControl.SetVolume([
    ('InstanceID', 0),
    ('Channel', 'Master'),
    ('DesiredVolume', 50)
])

# ZoneGroupTopology service
topology = speaker.zoneGroupTopology.GetZoneGroupState()
print(topology['ZoneGroupState'])
```

### Error Handling

```python
from soco.exceptions import SoCoUPnPException

try:
    speaker.play()
except SoCoUPnPException as e:
    print(f"UPnP Error {e.error_code}: {e.error_description}")
except Exception as e:
    print(f"Network error: {e}")
```

**Common Exceptions:**
- `SoCoUPnPException`: UPnP protocol errors (501 Action Failed, etc.)
- `ConnectionError`: Network connectivity issues
- `Timeout`: Request timeout

---

## TapCommand Integration Architecture

### Overview

Sonos speakers will integrate as Virtual Controllers following the same pattern as Bosch Praesensa and Plena Matrix amplifiers.

### Component Architecture

```
┌─────────────────────────────────────────────────────┐
│  Frontend (React)                                    │
│  - Audio Controller Management UI                   │
│  - Speaker grouping controls                        │
│  - Individual zone volume sliders                   │
└───────────────────────┬─────────────────────────────┘
                        │ HTTP/REST
                        ↓
┌─────────────────────────────────────────────────────┐
│  FastAPI Backend                                     │
│  /api/audio/* endpoints                              │
└───────────────────────┬─────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        ↓                               ↓
┌────────────────────┐        ┌────────────────────┐
│ Sonos Discovery    │        │ Command Queue      │
│ Service            │        │ Processor          │
│ - SSDP scanning    │        │                    │
│ - Device adoption  │        │ - SonosExecutor    │
└──────────┬─────────┘        └────────────────────┘
           │                              │
           ↓                              ↓
┌─────────────────────────────────────────────────────┐
│  Database (SQLite)                                   │
│  - virtual_controllers (audio)                       │
│  - virtual_devices (audio_zone)                      │
│  - network_discoveries                               │
│  - command_queue                                     │
└───────────────────────┬─────────────────────────────┘
                        ↓
                   Direct SOAP/UPnP
                        ↓
┌─────────────────────────────────────────────────────┐
│  Sonos Speakers (Port 1400)                          │
│  - Living Room Beam                                  │
│  - Kitchen One SL                                    │
│  - Bedroom Play:5                                    │
└─────────────────────────────────────────────────────┘
```

### Data Flow

1. **Discovery**: SSDP scan → `network_discoveries` table
2. **Adoption**: User adopts speaker → Create `VirtualController` + `VirtualDevice` per speaker
3. **Command**: Frontend → `/api/audio/zones/{zone_id}/volume` → `CommandQueue` → `SonosExecutor` → SOAP/UPnP → Sonos speaker
4. **Status**: Periodic polling or event subscriptions → Update `cached_volume_level`, `cached_mute_status`

---

## Database Schema Requirements

### VirtualController Table

Represents a Sonos household (collection of speakers).

```sql
-- Example VirtualController for Sonos
INSERT INTO virtual_controllers (
    controller_id,        -- "sonos-192168110"
    controller_name,      -- "Living Room System"
    controller_type,      -- "audio"
    protocol,             -- "sonos_upnp"
    ip_address,           -- "192.168.1.100" (any speaker in household)
    port,                 -- 1400
    is_online,            -- true
    connection_config,    -- JSON: {"household_id": "...", "speakers": [...]}
    capabilities          -- JSON: {"volume": true, "mute": true, "grouping": true}
)
```

**Key Fields:**
- `controller_id`: `sonos-{ip_address_normalized}` (e.g., `sonos-192168110`)
- `controller_type`: `audio`
- `protocol`: `sonos_upnp`
- `connection_config`: Store household ID, list of speaker UUIDs
- `capabilities`: Features supported (volume, mute, grouping, playback)

### VirtualDevice Table

Represents individual Sonos speakers.

```sql
-- Example VirtualDevice for a speaker
INSERT INTO virtual_devices (
    controller_id,           -- FK to virtual_controllers.id
    port_number,             -- Zone number (1-N)
    port_id,                 -- "sonos-192168110-1"
    device_name,             -- "Living Room Beam"
    device_type,             -- "audio_zone"
    ip_address,              -- "192.168.1.100"
    port,                    -- 1400
    protocol,                -- "sonos_upnp"
    connection_config,       -- JSON: {"uuid": "RINCON_xxx", "model": "Beam"}
    cached_volume_level,     -- 50
    cached_mute_status,      -- false
    cached_power_state,      -- "on" (always on for Sonos)
    is_online,               -- true
    status_available         -- true
)
```

**Key Fields:**
- `port_number`: Zone number (1, 2, 3, ...)
- `device_name`: Friendly name from Sonos (e.g., "Living Room")
- `device_type`: `audio_zone`
- `protocol`: `sonos_upnp`
- `connection_config`: Store UUID, model, group membership
- `cached_volume_level`: Last known volume (0-100)
- `cached_mute_status`: Last known mute state

### NetworkDiscoveries Table

Store discovered speakers before adoption.

```sql
INSERT INTO network_discoveries (
    protocol,             -- "sonos"
    ip_address,           -- "192.168.1.100"
    port,                 -- 1400
    device_name,          -- "Sonos Beam"
    manufacturer,         -- "Sonos, Inc."
    model,                -- "Beam"
    serial_number,        -- "00-11-22-33-44-55:7"
    uuid,                 -- "RINCON_B8E93791AF5C01400"
    location_url,         -- "http://192.168.1.100:1400/xml/device_description.xml"
    discovered_at,        -- TIMESTAMP
    additional_info       -- JSON: Full device description
)
```

### CommandQueue Table

Standard command queue entries for Sonos commands.

```sql
INSERT INTO command_queue (
    hostname,             -- "sonos-192168110" (controller_id)
    command,              -- "set_volume"
    port,                 -- Zone number (1-N)
    parameters,           -- JSON: {"volume": 50, "zone_number": 1}
    priority,             -- 0 (interactive), 1 (bulk)
    status,               -- "pending"
    created_at            -- TIMESTAMP
)
```

**Command Types:**
- `set_volume`: Set volume level
- `volume_up`: Increase volume by 5%
- `volume_down`: Decrease volume by 5%
- `mute`: Mute speaker
- `unmute`: Unmute speaker
- `toggle_mute`: Toggle mute state
- `play`: Start playback
- `pause`: Pause playback
- `stop`: Stop playback
- `next`: Next track
- `previous`: Previous track
- `join_group`: Join speaker group
- `leave_group`: Leave group

---

## Command Executor Implementation

### SonosExecutor Class

Create `backend/app/commands/executors/audio/sonos_upnp.py`:

```python
"""
Sonos UPnP Executor

Execute commands on Sonos speakers via UPnP/SOAP protocol using SoCo library
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from soco import SoCo
from soco.exceptions import SoCoUPnPException

from ..base import CommandExecutor
from ...models import Command, ExecutionResult
from ....models.virtual_controller import VirtualController, VirtualDevice
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SonosExecutor(CommandExecutor):
    """Execute commands on Sonos speakers via SoCo library"""

    def __init__(self, db: Session):
        self.db = db
        self._speakers: Dict[str, SoCo] = {}  # Cache speaker objects by controller_id

    def can_execute(self, command: Command) -> bool:
        """Check if this executor can handle the command"""
        return (
            command.device_type == "audio_zone" and
            command.protocol == "sonos_upnp"
        )

    async def execute(self, command: Command) -> ExecutionResult:
        """Execute audio zone command"""

        # Get Virtual Controller
        vc = self.db.query(VirtualController).filter(
            VirtualController.controller_id == command.controller_id
        ).first()

        if not vc:
            return ExecutionResult(
                success=False,
                message=f"Sonos controller {command.controller_id} not found"
            )

        # Get zone number from parameters
        zone_number = command.parameters.get("zone_number", 1) if command.parameters else 1

        # Get Virtual Device (zone/speaker)
        vd = self.db.query(VirtualDevice).filter(
            VirtualDevice.controller_id == vc.id,
            VirtualDevice.port_number == zone_number
        ).first()

        if not vd:
            return ExecutionResult(
                success=False,
                message=f"Zone {zone_number} not found for controller {command.controller_id}"
            )

        # Get SoCo speaker object
        speaker = self._get_speaker(vd)

        if not speaker:
            return ExecutionResult(
                success=False,
                message=f"Failed to connect to {vd.device_name} at {vd.ip_address}"
            )

        # Execute command based on type
        try:
            if command.command == "volume_up":
                return await self._volume_up(speaker, vd)
            elif command.command == "volume_down":
                return await self._volume_down(speaker, vd)
            elif command.command == "set_volume":
                volume = command.parameters.get("volume", 50) if command.parameters else 50
                return await self._set_volume(speaker, vd, volume)
            elif command.command == "mute":
                return await self._mute(speaker, vd, True)
            elif command.command == "unmute":
                return await self._mute(speaker, vd, False)
            elif command.command == "toggle_mute":
                return await self._toggle_mute(speaker, vd)
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
        """Get or create SoCo speaker object"""

        device_id = device.port_id

        # Return cached speaker if exists
        if device_id in self._speakers:
            return self._speakers[device_id]

        try:
            # Create new SoCo object
            speaker = SoCo(device.ip_address)

            # Cache speaker
            self._speakers[device_id] = speaker

            logger.info(f"✓ Connected to {device.device_name} at {device.ip_address}")
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
        """Set volume (0-100 scale) on zone"""

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

        # Update cache
        zone.cached_volume_level = volume
        self.db.commit()

        logger.info(f"✓ Set {zone.device_name} to {volume}%")

        return ExecutionResult(
            success=True,
            message=f"Set {zone.device_name} to {volume}%"
        )

    async def _volume_up(
        self,
        speaker: SoCo,
        zone: VirtualDevice
    ) -> ExecutionResult:
        """Increase volume by 5%"""
        current_volume = zone.cached_volume_level or 50
        new_volume = min(100, current_volume + 5)
        return await self._set_volume(speaker, zone, new_volume)

    async def _volume_down(
        self,
        speaker: SoCo,
        zone: VirtualDevice
    ) -> ExecutionResult:
        """Decrease volume by 5%"""
        current_volume = zone.cached_volume_level or 50
        new_volume = max(0, current_volume - 5)
        return await self._set_volume(speaker, zone, new_volume)

    async def _mute(
        self,
        speaker: SoCo,
        zone: VirtualDevice,
        mute: bool
    ) -> ExecutionResult:
        """Mute/unmute zone"""

        # Set mute state
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: setattr(speaker, 'mute', mute)
        )

        # Update cache
        zone.cached_mute_status = mute
        self.db.commit()

        action = "Muted" if mute else "Unmuted"
        logger.info(f"✓ {action} {zone.device_name}")

        return ExecutionResult(
            success=True,
            message=f"{action} {zone.device_name}"
        )

    async def _toggle_mute(
        self,
        speaker: SoCo,
        zone: VirtualDevice
    ) -> ExecutionResult:
        """Toggle mute state"""
        current_mute = zone.cached_mute_status or False
        return await self._mute(speaker, zone, not current_mute)

    async def _play(
        self,
        speaker: SoCo,
        zone: VirtualDevice
    ) -> ExecutionResult:
        """Start playback"""
        await asyncio.get_event_loop().run_in_executor(
            None,
            speaker.play
        )

        logger.info(f"✓ Started playback on {zone.device_name}")
        return ExecutionResult(
            success=True,
            message=f"Started playback on {zone.device_name}"
        )

    async def _pause(
        self,
        speaker: SoCo,
        zone: VirtualDevice
    ) -> ExecutionResult:
        """Pause playback"""
        await asyncio.get_event_loop().run_in_executor(
            None,
            speaker.pause
        )

        logger.info(f"✓ Paused playback on {zone.device_name}")
        return ExecutionResult(
            success=True,
            message=f"Paused playback on {zone.device_name}"
        )

    async def _stop(
        self,
        speaker: SoCo,
        zone: VirtualDevice
    ) -> ExecutionResult:
        """Stop playback"""
        await asyncio.get_event_loop().run_in_executor(
            None,
            speaker.stop
        )

        logger.info(f"✓ Stopped playback on {zone.device_name}")
        return ExecutionResult(
            success=True,
            message=f"Stopped playback on {zone.device_name}"
        )

    async def _next(
        self,
        speaker: SoCo,
        zone: VirtualDevice
    ) -> ExecutionResult:
        """Next track"""
        await asyncio.get_event_loop().run_in_executor(
            None,
            speaker.next
        )

        logger.info(f"✓ Next track on {zone.device_name}")
        return ExecutionResult(
            success=True,
            message=f"Next track on {zone.device_name}"
        )

    async def _previous(
        self,
        speaker: SoCo,
        zone: VirtualDevice
    ) -> ExecutionResult:
        """Previous track"""
        await asyncio.get_event_loop().run_in_executor(
            None,
            speaker.previous
        )

        logger.info(f"✓ Previous track on {zone.device_name}")
        return ExecutionResult(
            success=True,
            message=f"Previous track on {zone.device_name}"
        )

    async def cleanup(self):
        """Clear speaker cache"""
        self._speakers.clear()
        logger.info("Cleared Sonos speaker cache")
```

### Executor Registration

Add to `backend/app/commands/executors/audio/__init__.py`:

```python
from .sonos_upnp import SonosExecutor

__all__ = [
    "BoschAES70Executor",
    "BoschPlenaMatrixExecutor",
    "SonosExecutor"
]
```

---

## API Endpoint Design

Reuse existing `/api/audio/*` endpoints from `backend/app/routers/audio_controllers.py`.

### Discovery and Adoption

**Endpoint**: `POST /api/audio/controllers/discover`

```json
{
  "ip_address": "192.168.1.100",
  "controller_name": "Living Room Sonos",
  "protocol": "sonos_upnp",
  "venue_name": "Main House",
  "location": "Living Room"
}
```

**Response**:
```json
{
  "id": 1,
  "controller_id": "sonos-192168110",
  "controller_name": "Living Room Sonos",
  "controller_type": "audio",
  "ip_address": "192.168.1.100",
  "port": 1400,
  "is_online": true,
  "total_zones": 3,
  "zones": [
    {
      "id": 1,
      "zone_number": 1,
      "zone_name": "Living Room",
      "device_type": "audio_zone",
      "protocol": "sonos_upnp",
      "volume_level": 50,
      "is_muted": false,
      "is_online": true
    }
  ]
}
```

### Volume Control

**Set Volume**: `POST /api/audio/zones/{zone_id}/volume`
```json
{
  "volume": 50
}
```

**Volume Up**: `POST /api/audio/zones/{zone_id}/volume/up`
**Volume Down**: `POST /api/audio/zones/{zone_id}/volume/down`

### Mute Control

**Toggle Mute**: `POST /api/audio/zones/{zone_id}/mute`
```json
{
  "mute": true  // Optional, toggles if omitted
}
```

### Playback Control

**Play**: `POST /api/audio/zones/{zone_id}/playback/play`
**Pause**: `POST /api/audio/zones/{zone_id}/playback/pause`
**Stop**: `POST /api/audio/zones/{zone_id}/playback/stop`
**Next**: `POST /api/audio/zones/{zone_id}/playback/next`
**Previous**: `POST /api/audio/zones/{zone_id}/playback/previous`

### Grouping (Future Enhancement)

**Join Group**: `POST /api/audio/zones/{zone_id}/group/join`
```json
{
  "target_zone_id": 2  // Zone to join
}
```

**Leave Group**: `POST /api/audio/zones/{zone_id}/group/leave`

---

## Challenges & Considerations

### 1. Group Coordinator Complexity

**Challenge**: Commands must be sent to the group coordinator, not individual speakers.

**Solution**:
- Cache group topology from `GetZoneGroupState`
- Update topology periodically or via events
- Route transport commands (play/pause) to coordinator
- Allow volume/mute commands to individual speakers or group

### 2. Speaker Discovery vs. Household Model

**Challenge**: Sonos speakers belong to a "household" and can be dynamically grouped.

**Solution Options**:

- **Option A**: One controller per speaker (simple but ignores groups)
- **Option B**: One controller per household with multiple zones (complex but accurate)
- **Option C (Recommended)**: Hybrid - one controller per speaker, track group membership in `connection_config`

### 3. Event Subscription Firewall Issues

**Challenge**: Sonos speakers must be able to reach backend IP for event callbacks.

**Solution**:
- Make event subscriptions optional
- Use periodic polling as fallback
- Document firewall requirements

### 4. SoCo Library Synchronous API

**Challenge**: SoCo is synchronous, TapCommand uses async/await.

**Solution**:
```python
await asyncio.get_event_loop().run_in_executor(
    None,
    speaker.play  # Blocking call runs in thread pool
)
```

### 5. Sonos API Unofficial Status

**Challenge**: Sonos does not officially support the UPnP API and may change it.

**Solution**:
- SoCo library actively maintained and adapts to changes
- Monitor SoCo GitHub for breaking changes
- Document in system that Sonos control is "best effort"

### 6. Music Service Authentication

**Challenge**: Playing content from Spotify/Apple Music requires service authentication.

**Solution**:
- Phase 1: Volume/playback control only (no service integration)
- Phase 2: Queue management with local files/URLs
- Phase 3: Music service integration (if needed)

### 7. Multi-User Conflicts

**Challenge**: Multiple users controlling same speaker simultaneously.

**Solution**:
- Use command queue to serialize requests
- Cache volume/mute state to avoid redundant commands
- Consider event subscriptions to detect external changes

### 8. Network Discovery Frequency

**Challenge**: Balance between discovery speed and network overhead.

**Solution**:
- Run SSDP discovery every 5-10 minutes
- Reduce frequency if no new speakers found for 1 hour
- Trigger manual discovery via UI button

---

## Testing & Validation

### Unit Tests

**Test Speaker Discovery:**
```python
async def test_discover_sonos_speaker():
    # Mock SSDP response
    discovery = SonosDiscoveryService()
    speakers = await discovery.discover()
    assert len(speakers) > 0
    assert speakers[0].ip_address is not None
```

**Test Volume Control:**
```python
async def test_set_volume():
    executor = SonosExecutor(db)
    command = Command(
        controller_id="sonos-192168110",
        command="set_volume",
        device_type="audio_zone",
        protocol="sonos_upnp",
        parameters={"volume": 50, "zone_number": 1}
    )
    result = await executor.execute(command)
    assert result.success is True
```

### Integration Tests

**Test Full Command Flow:**
```python
async def test_volume_command_flow():
    # 1. Discover speaker
    controller, zones = await discover_and_create_sonos_controller(
        ip_address="192.168.1.100",
        controller_name="Test Sonos"
    )

    # 2. Queue volume command
    cmd = CommandQueueService.queue_command(
        db=db,
        hostname=controller.controller_id,
        port=1,
        command="set_volume",
        parameters={"volume": 50, "zone_number": 1}
    )

    # 3. Process queue
    processor = QueueProcessor(db)
    await processor.process_pending_commands()

    # 4. Verify command executed
    db.refresh(cmd)
    assert cmd.status == "completed"
```

### Manual Testing

**Discovery Test:**
1. Run SSDP discovery: `python -m backend.test_sonos_discovery`
2. Verify all speakers found
3. Check device description XML parsing

**Playback Test:**
1. Adopt speaker via UI
2. Set volume to 50%
3. Press play button
4. Verify audio plays

**Group Test:**
1. Create speaker group in Sonos app
2. Send play command to non-coordinator
3. Verify command routed to coordinator

### Performance Benchmarks

**Latency Targets:**
- Volume change: < 500ms
- Playback control: < 300ms
- Discovery: < 5 seconds
- Group topology update: < 2 seconds

---

## References

### Official Sonos Resources

- **Sonos Cloud API**: https://developer.sonos.com/ (Official but limited to cloud control)
- **Control API Documentation**: https://developer.sonos.com/reference/control-api/

### Community Documentation

- **Sonos API Docs (svrooij)**: https://sonos.svrooij.io/
  - Comprehensive UPnP service documentation
  - Generated from device discovery
  - **Highly Recommended**

- **SoCo Python Library**: https://github.com/SoCo/SoCo
  - Official GitHub repository
  - Documentation: http://docs.python-soco.com/

- **SoCo Wiki**: https://github.com/SoCo/SoCo/wiki/Sonos-UPnP-Services-and-Functions
  - Service function reference

### Technical Specifications

- **UPnP Device Architecture**: http://upnp.org/specs/arch/UPnP-arch-DeviceArchitecture-v2.0.pdf
- **UPnP AV Architecture**: http://upnp.org/specs/av/UPnP-av-AVArchitecture-v3.pdf
- **DIDL-Lite Specification**: Part of UPnP ContentDirectory specification

### Blog Posts & Tutorials

- **TravelMarx - Exploring Sonos via UPnP**: https://blog.travelmarx.com/2010/06/exploring-sonos-via-upnp.html
  - Early exploration of Sonos UPnP API

- **Digging into UPnP by searching a Sonos API**: https://djboris.medium.com/digging-into-upnp-by-searching-a-sonos-api-5e10e080a232
  - Technical deep dive

### Related Projects

- **node-sonos-ts**: TypeScript Sonos library (https://github.com/svrooij/node-sonos-ts)
- **sonos2mqtt**: MQTT bridge for Sonos (https://github.com/svrooij/sonos2mqtt)
- **Home Assistant Sonos Integration**: https://www.home-assistant.io/integrations/sonos/

---

## Implementation Checklist

### Phase 1: Basic Volume Control

- [ ] Install SoCo library: `pip install soco`
- [ ] Create `SonosDiscoveryService` in `backend/app/services/sonos_discovery.py`
- [ ] Implement SSDP discovery and device description parsing
- [ ] Create `SonosExecutor` in `backend/app/commands/executors/audio/sonos_upnp.py`
- [ ] Implement volume commands: `set_volume`, `volume_up`, `volume_down`
- [ ] Implement mute commands: `mute`, `unmute`, `toggle_mute`
- [ ] Update `/api/audio/controllers/discover` endpoint to support `protocol="sonos_upnp"`
- [ ] Test volume control via API endpoints

### Phase 2: Playback Control

- [ ] Implement playback commands: `play`, `pause`, `stop`, `next`, `previous`
- [ ] Add playback control API endpoints
- [ ] Update frontend UI to show playback controls for Sonos zones
- [ ] Test playback control from UI

### Phase 3: Status Monitoring

- [ ] Implement periodic status polling (volume, mute, transport state)
- [ ] Update `cached_volume_level` and `cached_mute_status` in database
- [ ] Optional: Implement UPnP event subscriptions for real-time updates
- [ ] Display current playback info in UI (track title, artist)

### Phase 4: Advanced Features

- [ ] Implement speaker grouping commands
- [ ] Add group management UI
- [ ] Implement queue management (add to queue, clear queue)
- [ ] Add bass/treble/EQ controls
- [ ] Implement alarm management (optional)

### Phase 5: Production Hardening

- [ ] Add comprehensive error handling
- [ ] Implement retry logic for transient failures
- [ ] Add health monitoring for Sonos speakers
- [ ] Document user setup instructions
- [ ] Create troubleshooting guide

---

## Conclusion

This document provides a complete technical specification for integrating Sonos speakers into TapCommand's audio control system. The integration leverages the SoCo Python library to communicate with Sonos speakers via the UPnP/SOAP protocol, following the same Virtual Controller architecture used for Bosch Praesensa and Plena Matrix amplifiers.

Key implementation points:

1. **Use SoCo Library**: Mature, well-maintained, handles protocol complexity
2. **Virtual Controller Model**: One controller per household, multiple zones per speaker
3. **Async Wrapper**: Wrap SoCo's synchronous API in async executor pattern
4. **Queue Integration**: Route commands through TapCommand's command queue
5. **Incremental Rollout**: Start with volume control, add features progressively

The unofficial nature of the Sonos UPnP API is mitigated by using SoCo, which has proven stable across Sonos firmware updates and has an active community maintaining compatibility.

**Next Steps**: Follow the implementation checklist above, starting with Phase 1 (Basic Volume Control) to establish the foundation for Sonos integration.
