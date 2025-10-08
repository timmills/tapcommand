# Bosch Praesensa Research Findings

## Research Date
January 2025

## Overview
Bosch Praesensa is a professional IP-based Public Address (PA) and Voice Alarm System that uses OMNEO networking architecture. It's designed for large-scale installations with support for up to 250 devices and over 500 zones.

---

## Control Protocols & Integration Options

### 1. **OMNEO with AES70/OCA** (Primary Control Protocol)
**Status**: ⚠️ Complex but standardized

#### Protocol Details
- **Standard**: AES70 (Open Control Architecture)
- **Protocol Name**: OCP.1 (OCA Protocol 1)
- **Transport**: TCP, TCP/SSL, UDP, or WebSocket over IP
- **Default Port**: 65000 (TCP)
- **Architecture**: Object-oriented control model with 100+ control classes

#### Key Features
- Device discovery
- Object tree navigation
- Property get/set operations
- Event subscription
- Method invocation
- Built on open standards (AES67 for audio, AES70 for control)

#### Implementation Libraries

**JavaScript/Node.js - AES70.js**
- **Repository**: https://github.com/DeutscheSoft/AES70.js/
- **License**: GNU GPL v2
- **Status**: Mature, fully implements AES70-2018
- **Installation**: `npm i aes70`

**Example Connection**:
```javascript
import { TCPConnection, RemoteDevice } from 'aes70';

async function run() {
  const connection = await TCPConnection.connect({
    host: '192.168.1.100',
    port: 65000
  });

  const device = new RemoteDevice(connection);

  // Get device name
  const name = await device.DeviceManager.GetModelDescription();

  // Discover device tree
  const tree = await device.get_device_tree();

  // Control example (conceptual)
  // await device.Block.ObjectPath.Gain.SetGain(-20);
  // await device.Block.ObjectPath.Mute.SetState(true);
}
```

**Python - AES70py** ✅ **PRODUCTION READY**
- **Repository**: https://github.com/AES70py/aes70py
- **License**: MIT License
- **Status**: ✅ **Available NOW** - v1.0.2 released
- **Installation**: `pip install https://github.com/AES70py/aes70py/releases/download/1.0.2/aes70py-1.0.2-py3-none-any.whl`
- **Features**: 100 control classes, async/await, pure Python, no dependencies

**Example Usage** (from actual repository examples):
```python
import asyncio
from aes70 import tcp_connection, remote_device

async def connect_and_control():
    # Connect to Praesensa
    connection = await tcp_connection.connect(
        ip_address="192.168.1.100",
        port=65000
    )

    device = remote_device.RemoteDevice(connection)
    device.set_keepalive_interval(10)

    # Discover device tree
    tree = await device.get_device_tree()

    # Get role map (named objects)
    role_map = await device.get_role_map()

    # Control mute example
    mute_obj = role_map.get("Zone1/Mute")
    if mute_obj:
        from aes70.types import OcaMuteState
        current_state = await mute_obj.GetState()
        new_state = OcaMuteState.Muted if current_state == OcaMuteState.Unmuted else OcaMuteState.Unmuted
        await mute_obj.SetState(new_state)

    # Control gain/volume example (conceptual)
    gain_obj = role_map.get("Zone1/Gain")
    if gain_obj:
        await gain_obj.SetGain(-20.0)  # Set to -20dB

asyncio.run(connect_and_control())
```

#### Complexity Assessment
- **Learning Curve**: MEDIUM - Object model discoverable via API
- **Implementation**: MEDIUM - Python library ready, async/await familiar pattern
- **Documentation**: GOOD - Examples available, device self-describes via role map
- **Reliability**: HIGH - Professional audio standard, widely adopted

#### Advantages
✅ Open standard (no licensing fees, no Bosch-specific API keys needed)
✅ Python library production-ready (v1.0.2)
✅ Pure Python, async/await (matches our FastAPI backend)
✅ Self-discovery via role maps (zones/objects discoverable programmatically)
✅ Professional audio industry standard
✅ Future-proof (maintained by OCA Alliance)
✅ Supports complex multi-zone operations
✅ Event-driven updates available
✅ Compatible with other OMNEO/AES70 devices
✅ No dependencies, clean installation

#### Disadvantages (Minor)
❌ Object structure varies by Bosch configuration (but discoverable)
❌ Need to understand dB levels for volume control
❌ Slightly more complex than simple HTTP REST APIs

---

### 2. **Praesensa Open Interface** (Alternative Control)
**Status**: ⚠️ Documentation access required

#### Protocol Details
- **Type**: TCP/IP-based (exact protocol type unclear without docs)
- **Purpose**: Third-party system integration
- **Security**: TLS 1.2/1.3 encryption
- **Target**: System controller IP address
- **Documentation**: "PRAESENSA Open Interface programming instructions" (Bosch proprietary)

#### Key Features
- Business-related function control
- Third-party application integration
- Building management system integration
- Optional emergency control
- Browser-based control interface

#### Implementation Status
⚠️ **Documentation Access Required**
- Official programming instructions PDF is access-protected
- Requires Bosch technical support contact or dealer access
- Likely requires NDA or professional installer status

#### Potential Advantages (Speculative)
✅ May be simpler than AES70/OMNEO
✅ Tailored specifically for Praesensa features
✅ Possibly REST-like or command/response based

#### Disadvantages
❌ Proprietary (Bosch-specific)
❌ Documentation not publicly accessible
❌ Unknown protocol structure without vendor access
❌ May require licensing or professional status

---

### 3. **Additional Control Options**

#### **GPIO Control Interface**
- **Hardware**: PRA-IM16C8 Control Interface Module
- **Type**: Physical GPIO inputs/outputs
- **Use Case**: Simple trigger-based control (not suitable for network integration)

#### **SIP/VoIP Interface**
- **Protocol**: Session Initiation Protocol
- **Use Case**: Telephony paging and audio routing
- **Limitation**: Not designed for general device control

#### **Web Browser Interface**
- **Type**: Built-in web server
- **Use Case**: Configuration and file management
- **Limitation**: Human interface, not API

---

## Recommended Integration Approach

### ✅ AES70/OMNEO with AES70py (RECOMMENDED - Production Ready!)
**Pros**:
- ✅ Python library ready NOW (v1.0.2)
- ✅ No licensing fees or API keys required
- ✅ Open standard, no vendor lock-in
- ✅ Professional-grade reliability
- ✅ Self-discovery of zones via role maps
- ✅ Async/await matches our FastAPI backend
- ✅ Pure Python, no Node.js bridge needed

**Cons**:
- Zone structure varies by Praesensa configuration (but auto-discoverable)
- Need to map dB values for user-friendly volume control

**Implementation Path**:
1. Install AES70py library in backend
2. Create discovery service to enumerate zones (role map)
3. Map zones to Virtual Devices (similar to network TVs)
4. Implement Bosch AES70 executor with volume/mute/preset commands
5. Build /audio frontend page for zone control
6. Test with Bosch Praesensa hardware

**Estimated Effort**: ✅ 3-4 weeks for initial implementation (down from 6-8 weeks!)

---

### Option B: Praesensa Open Interface (If Documentation Available)
**Pros**:
- Potentially simpler protocol
- Bosch-optimized for Praesensa features
- May have better performance

**Cons**:
- Documentation access required
- Vendor lock-in
- Unknown complexity until docs reviewed

**Implementation Path**:
1. Contact Bosch technical support: https://www.boschsecurity.com/
2. Request Open Interface programming documentation
3. May require dealer/installer credentials
4. Review protocol specification
5. Implement Python client based on protocol

**Estimated Effort**: Unknown until documentation reviewed (2-6 weeks estimated)

---

### Option C: Alternative Amplifier Brands (Easier Integration)
**Consider these alternatives if Bosch proves too complex:**

#### **Sonos Professional**
- **Protocol**: HTTP REST API
- **Documentation**: Public and well-documented
- **Python Library**: SoCo library (mature, active)
- **Effort**: 1-2 weeks

#### **AUDAC Consenso**
- **Protocol**: Dante/AES67 with web API
- **Documentation**: Available to integrators
- **Effort**: 2-3 weeks

#### **Powersoft Armonía**
- **Protocol**: Proprietary but documented
- **Documentation**: Available through Powersoft
- **Effort**: 2-3 weeks

---

## Technical Specifications

### Bosch Praesensa System Capabilities
- **Max Devices**: 250 devices per system
- **Max Zones**: 500+ zones
- **Network**: Gigabit Ethernet
- **Audio**: AES67, Dante compatible
- **Control**: OMNEO (AES70/OCA)
- **Redundancy**: Network redundancy support
- **Integration**: Open Interface, GPIO, SIP

### Network Requirements
- **Bandwidth**: Varies by zone count and audio streams
- **Latency**: <10ms for audio (control latency depends on command type)
- **Ports**:
  - TCP 65000 (AES70/OCP.1)
  - Various OMNEO ports for audio/discovery
  - TLS encrypted connections available

---

## Next Steps

### Immediate Actions
1. **Decision Point**: Choose integration approach (AES70 vs Open Interface vs alternative brand)

2. **If pursuing Bosch Praesensa**:
   - [ ] Contact Bosch technical support for Open Interface documentation
   - [ ] Request access to developer resources
   - [ ] Determine if dealer/installer credentials needed
   - [ ] Evaluate AES70.js + Node.js bridge as interim solution
   - [ ] Monitor AES70py release status

3. **If pursuing AES70/OMNEO**:
   - [ ] Set up Node.js development environment
   - [ ] Install AES70.js library
   - [ ] Test connection to Praesensa system (requires hardware/simulator)
   - [ ] Explore device object tree
   - [ ] Document Bosch-specific object paths
   - [ ] Create Python wrapper for Node.js client

4. **Alternative Evaluation**:
   - [ ] Compare total cost of ownership (Bosch vs alternatives)
   - [ ] Evaluate Sonos Professional as simpler option
   - [ ] Consider AUDAC Consenso for professional PA needs
   - [ ] Review feature requirements vs ease of integration

### Questions to Answer
1. Do we have access to Bosch Praesensa hardware for testing?
2. Can we obtain Bosch Open Interface documentation?
3. Is professional audio PA system required, or would Sonos-level suffice?
4. What is the priority: feature richness vs ease of implementation?
5. Budget for Node.js subprocess vs waiting for Python library?

---

## Resources

### AES70/OCA Resources
- **OCA Alliance**: https://ocaalliance.com/
- **AES70 Standard**: Open standard, freely available
- **AES70.js GitHub**: https://github.com/DeutscheSoft/AES70.js/
- **AES70py**: https://aes70py.org/ (pre-release)
- **AES70 Explorer**: https://aes70explorer.com/try/ (development utility)

### Bosch Resources
- **Praesensa Product Page**: https://www.boschsecurity.com/us/en/solutions/public-address-systems/mass-notification-systems/ip-pa-system-praesensa/
- **Technical Support**: Contact through Bosch Security Systems
- **System Activation Portal**: https://licensing.boschsecurity.com/

### Alternative Brands
- **Sonos SoCo Library**: https://github.com/SoCo/SoCo
- **AUDAC**: https://www.audac.eu/
- **Powersoft**: https://www.powersoft.com/

---

## Conclusion

**✅ Bosch Praesensa integration is FEASIBLE and RECOMMENDED!** The AES70py Python library makes this much easier than initially expected.

**Recommended Path**:
1. **✅ IMMEDIATE**: Use AES70py (production-ready Python library)
2. **Week 1-2**: Install library, create discovery service, map zones to Virtual Devices
3. **Week 3-4**: Implement executor, build frontend, test with hardware

**Complexity Rating**: 🟡 MEDIUM (similar to TV network control)
**Implementation Estimate**: ✅ 3-4 weeks for Bosch Praesensa
**Expertise Required**: Python async/await (already have), basic audio concepts (dB levels)

**No licensing fees. No API keys. No Node.js bridge. Just pure Python!** 🎉

## License & Access Summary

### ✅ What's FREE:
- AES70 protocol (open standard)
- AES70py library (MIT license)
- OCA Alliance resources
- Connection to Bosch Praesensa (built-in AES70 support)

### ❌ What You DON'T Need:
- No Bosch API license
- No OCA Alliance membership
- No special developer access
- No documentation access requests
- No Node.js bridge

### ✅ What You DO Need:
- Bosch Praesensa hardware (amplifier/controller)
- Network IP address of the controller
- Python 3 + AES70py library (free)
- Login credentials (if authentication enabled on controller)

---

## Document Version
- **Created**: January 2025
- **Last Updated**: January 2025
- **Status**: Research phase - pending vendor documentation access
