# IR Database Integration Analysis

## Current State

### What We've Done
1. **Added ESPHome Native Commands to Database**
   - Samsung: 16 commands (Samsung32 protocol, `{"data": "0xE0E040BF"}` format)
   - LG: 16 commands (NEC protocol, `{"address": "0x04", "command": "0x08"}` format)
   - Hisense: 16 commands (NEC protocol, `{"data": "0xFDB04F"}` format)

### Current Architecture Problem
**Two-Path System:**
```python
# Line 1065-1071 in templates.py
if getattr(library, 'esp_native', 0):
    transmissions = _build_native_transmissions(library)  # Uses NATIVE_IR_PROFILES dict
else:
    transmissions = _build_command_transmissions(library, commands)  # Uses database
```

**Hardcoded Native Profiles (lines 92-136):**
```python
NATIVE_IR_PROFILES = {
    '*Samsung': {
        'protocol': 'samsung',
        'commands': {
            'power': {'data': '0xE0E040BF', 'label': 'Power'},
            # ... more commands
        }
    },
    '*LG': {
        'protocol': 'nec',
        'address': '0x04',
        'commands': {
            'power': {'command': '0x08', 'label': 'Power'},
            # ... more commands
        }
    }
}
```

## Database Format Analysis

### ESPHome Native (Our Added Records)
```json
Samsung32 -> {"data": "0xE0E040BF"}           // Direct data format
NEC -> {"address": "0x04", "command": "0x08"} // Address/command format
NEC -> {"data": "0xFDB04F"}                   // Direct data format
```

### Flipper-IRDB (Imported Records)
```json
Samsung32 -> {"address": "07 00 00 00", "command": "E6 00 00 00"} // Space-separated bytes
NEC -> {"address": "20 00 00 00", "command": "02 00 00 00"}       // Space-separated bytes
```

## YAML Generation Analysis

### Current ESPHome Native Output
```yaml
- remote_transmitter.transmit_samsung:
    transmitter_id: ir_transmitter_port1
    data: 0xE0E040BF
```

### Required Format Conversions for Database Integration

#### 1. Samsung Protocol
- **ESPHome Native**: `{"data": "0xE0E040BF"}` ✅ Works
- **Flipper-IRDB**: `{"address": "07 00 00 00", "command": "E6 00 00 00"}` ❌ Needs conversion

#### 2. NEC Protocol
- **ESPHome Native**: `{"address": "0x04", "command": "0x08"}` ✅ Works
- **Flipper-IRDB**: `{"address": "20 00 00 00", "command": "02 00 00 00"}` ✅ Already handled (lines 398-412)

## Complexity Assessment

### Format Conversion Challenges
1. **Multiple Samsung Formats**: Direct data vs address/command
2. **Byte Order Conversions**: Space-separated to hex values
3. **Protocol Variations**: Different manufacturers use different encodings
4. **Raw Signal Data**: Some commands are raw timing data, not protocol-specific

### Current Handler Support
- ✅ NEC with space-separated bytes (lines 398-422)
- ✅ Samsung with direct data (lines 382-390)
- ✅ Pronto hex codes (lines 424-431)
- ✅ Raw signal data (lines 289-330)
- ❌ Samsung with address/command format

## Test Results
- **API Endpoint**: `/api/v1/templates/preview` ✅ Working
- **Samsung Native**: Generates 19,107 char YAML ✅ Working
- **Database Records**: 4,245 total commands ✅ Populated
- **Format Issue**: Samsung address/command not handled ❌ Problem identified

## Proposed Solutions

### Option 1: Extend Current System
- Add Samsung address/command conversion to `_render_transmit_lines()`
- Handle all format variations in conversion logic
- Keep two-path architecture but make database path more robust

### Option 2: Alternative Approach
- [User mentioned having another idea - waiting for input]

## Files Modified
- `/home/coastal/tapcommand/backend/tapcommand.db` - Added ESPHome native commands
- Analysis of `/home/coastal/tapcommand/backend/app/routers/templates.py`

## Key Functions
- `_build_native_transmissions()` - Hardcoded path (line 274)
- `_build_command_transmissions()` - Database path (line 332)
- `_render_transmit_lines()` - YAML generation (line 378)
- `convert_hex_value()` - NEC format conversion (line 399)

## Next Steps
- Awaiting user's alternative idea
- Consider complexity of full format conversion vs other approaches