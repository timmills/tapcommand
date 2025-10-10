# Adding ESPHome Native IR Libraries to Database

## Overview
This document provides precise step-by-step instructions for adding new ESPHome native IR protocol libraries to the TapCommand database. These libraries allow direct use of ESPHome's built-in IR transmit actions without requiring raw signal data.

## Prerequisites
- Access to `/home/coastal/tapcommand/backend/load_native_ir.py`
- Python virtual environment at `/home/coastal/tapcommand/backend/venv`
- Access to TapCommand database at `/home/coastal/tapcommand/backend/tapcommand.db`

## Step 1: Research IR Codes

### 1.1 Identify the ESPHome Protocol
First, determine which ESPHome native transmit action you're targeting. Common protocols:
- `transmit_samsung` - Samsung TVs (data parameter)
- `transmit_nec` - NEC protocol (address + command)
- `transmit_lg` - LG protocol (data + nbits)
- `transmit_panasonic` - Panasonic protocol (address + command)
- `transmit_sony` - Sony protocol (data + nbits)
- `transmit_rc5` - Philips RC5 (address + command)
- `transmit_rc6` - Philips RC6 (address + command)

**Reference**: https://esphome.io/components/remote_transmitter.html

### 1.2 Search for IR Codes

#### Primary Sources (in order of reliability):

**1. Tasmota IR Documentation**
- URL: https://tasmota.github.io/docs/Codes-for-IR-Remotes/
- Search method: Use browser find (Ctrl+F) for brand name
- Look for codes in format matching your ESPHome protocol
- Example search: "LG" → Found LG codes for transmit_lg

**2. ESPHome Community Forums**
- URL: https://community.home-assistant.io/c/esphome/
- Search: "[Brand name] IR codes ESPHome"
- Look for confirmed working codes with your specific protocol

**3. GitHub Gists and Repositories**
- Search: "site:github.com [brand] [protocol] IR codes"
- Example: "site:github.com LG transmit_lg"
- Found working codes at: https://gist.github.com/appden/42d5272bf128125b019c45bc2ed3311f

**4. Flipper Zero IR Database**
- URL: https://github.com/Lucaslhm/Flipper-IRDB
- Navigate to: TVs/[Brand]/
- Note: Flipper uses different format - requires conversion
- Used for Panasonic research but needed protocol translation

### 1.3 Verify Code Format

Each protocol has specific parameter requirements:

#### transmit_samsung
```yaml
signal_data: {"data": "0xE0E040BF"}
```
- Single hex data value
- No nbits parameter needed

#### transmit_nec (used for LG NEC protocol)
```yaml
signal_data: {"address": "0x04", "command": "0x08"}
```
- Separate address and command
- Both as hex strings

#### transmit_lg
```yaml
signal_data: {"data": "0x20DF10EF", "nbits": 32}
```
- Hex data value
- nbits parameter (typically 28 or 32)

#### transmit_panasonic
```yaml
signal_data: {"address": "0x4004", "command": "0x0100BCBD"}
```
- 16-bit address (4 hex digits)
- 32-bit command (8 hex digits)

### 1.4 Essential Commands to Find

Minimum command set for TV library:
1. **Power** (category: "power")
2. **Mute** (category: "audio")
3. **Volume Up** (category: "volume")
4. **Volume Down** (category: "volume")
5. **Channel Up** (category: "channel")
6. **Channel Down** (category: "channel")
7. **Number 0-9** (category: "number") - 10 commands

**Total: 16 commands minimum**

### 1.5 Document Your Sources

For each protocol researched, document:
- URL where codes were found
- Date accessed
- Any discrepancies between sources
- Confirmation method (if tested)

## Step 2: Format the Command Array

### 2.1 Create Command Dictionary List

Open `/home/coastal/tapcommand/backend/load_native_ir.py`

Add a new command array following this exact format:

```python
[BRAND]_TRANSMIT_COMMANDS: List[Dict[str, Any]] = [
    {"name": "Power", "category": "power", "signal_data": {[PROTOCOL_PARAMS]}},
    {"name": "Mute", "category": "audio", "signal_data": {[PROTOCOL_PARAMS]}},
    {"name": "Volume Up", "category": "volume", "signal_data": {[PROTOCOL_PARAMS]}},
    {"name": "Volume Down", "category": "volume", "signal_data": {[PROTOCOL_PARAMS]}},
    {"name": "Channel Up", "category": "channel", "signal_data": {[PROTOCOL_PARAMS]}},
    {"name": "Channel Down", "category": "channel", "signal_data": {[PROTOCOL_PARAMS]}},
    {"name": "Number 0", "category": "number", "signal_data": {[PROTOCOL_PARAMS]}},
    {"name": "Number 1", "category": "number", "signal_data": {[PROTOCOL_PARAMS]}},
    {"name": "Number 2", "category": "number", "signal_data": {[PROTOCOL_PARAMS]}},
    {"name": "Number 3", "category": "number", "signal_data": {[PROTOCOL_PARAMS]}},
    {"name": "Number 4", "category": "number", "signal_data": {[PROTOCOL_PARAMS]}},
    {"name": "Number 5", "category": "number", "signal_data": {[PROTOCOL_PARAMS]}},
    {"name": "Number 6", "category": "number", "signal_data": {[PROTOCOL_PARAMS]}},
    {"name": "Number 7", "category": "number", "signal_data": {[PROTOCOL_PARAMS]}},
    {"name": "Number 8", "category": "number", "signal_data": {[PROTOCOL_PARAMS]}},
    {"name": "Number 9", "category": "number", "signal_data": {[PROTOCOL_PARAMS]}},
]
```

### 2.2 Naming Convention

**Variable Name Format**: `[BRAND]_TRANSMIT_COMMANDS` or `[BRAND]_[PROTOCOL]_COMMANDS`

Examples:
- `LG_TRANSMIT_COMMANDS` (for transmit_lg)
- `PANASONIC_COMMANDS` (for transmit_panasonic)
- `SAMSUNG_COMMANDS` (for transmit_samsung)

**Important**:
- Use uppercase for constant name
- Use exact brand spelling (no abbreviations)
- Add after existing command arrays (before `NATIVE_LIBRARIES`)

### 2.3 Real Examples

#### Example 1: LG transmit_lg (completed)
```python
LG_TRANSMIT_COMMANDS: List[Dict[str, Any]] = [
    {"name": "Power", "category": "power", "signal_data": {"data": "0x20DF10EF", "nbits": 32}},
    {"name": "Mute", "category": "audio", "signal_data": {"data": "0x20DF906F", "nbits": 32}},
    {"name": "Volume Up", "category": "volume", "signal_data": {"data": "0x20DF40BF", "nbits": 32}},
    {"name": "Volume Down", "category": "volume", "signal_data": {"data": "0x20DFC03F", "nbits": 32}},
    {"name": "Channel Up", "category": "channel", "signal_data": {"data": "0x20DF00FF", "nbits": 32}},
    {"name": "Channel Down", "category": "channel", "signal_data": {"data": "0x20DF807F", "nbits": 32}},
    {"name": "Number 0", "category": "number", "signal_data": {"data": "0x20DF08F7", "nbits": 32}},
    {"name": "Number 1", "category": "number", "signal_data": {"data": "0x20DF8877", "nbits": 32}},
    {"name": "Number 2", "category": "number", "signal_data": {"data": "0x20DF48B7", "nbits": 32}},
    {"name": "Number 3", "category": "number", "signal_data": {"data": "0x20DFC837", "nbits": 32}},
    {"name": "Number 4", "category": "number", "signal_data": {"data": "0x20DF28D7", "nbits": 32}},
    {"name": "Number 5", "category": "number", "signal_data": {"data": "0x20DFA857", "nbits": 32}},
    {"name": "Number 6", "category": "number", "signal_data": {"data": "0x20DF6897", "nbits": 32}},
    {"name": "Number 7", "category": "number", "signal_data": {"data": "0x20DFE817", "nbits": 32}},
    {"name": "Number 8", "category": "number", "signal_data": {"data": "0x20DF18E7", "nbits": 32}},
    {"name": "Number 9", "category": "number", "signal_data": {"data": "0x20DF9867", "nbits": 32}},
]
```

**Sources**:
- Tasmota: https://tasmota.github.io/docs/Codes-for-IR-Remotes/#lg-tvs
- GitHub Gist: https://gist.github.com/appden/42d5272bf128125b019c45bc2ed3311f
- Both sources matched exactly, confirming accuracy

#### Example 2: Panasonic transmit_panasonic (completed)
```python
PANASONIC_COMMANDS: List[Dict[str, Any]] = [
    {"name": "Power", "category": "power", "signal_data": {"address": "0x4004", "command": "0x0100BCBD"}},
    {"name": "Mute", "category": "audio", "signal_data": {"address": "0x4004", "command": "0x01004C4D"}},
    {"name": "Volume Up", "category": "volume", "signal_data": {"address": "0x4004", "command": "0x01000405"}},
    {"name": "Volume Down", "category": "volume", "signal_data": {"address": "0x4004", "command": "0x01008485"}},
    {"name": "Channel Up", "category": "channel", "signal_data": {"address": "0x4004", "command": "0x01002C2D"}},
    {"name": "Channel Down", "category": "channel", "signal_data": {"address": "0x4004", "command": "0x0100ACAD"}},
    {"name": "Number 0", "category": "number", "signal_data": {"address": "0x4004", "command": "0x01009899"}},
    {"name": "Number 1", "category": "number", "signal_data": {"address": "0x4004", "command": "0x01000809"}},
    {"name": "Number 2", "category": "number", "signal_data": {"address": "0x4004", "command": "0x01008889"}},
    {"name": "Number 3", "category": "number", "signal_data": {"address": "0x4004", "command": "0x01004849"}},
    {"name": "Number 4", "category": "number", "signal_data": {"address": "0x4004", "command": "0x0100C8C9"}},
    {"name": "Number 5", "category": "number", "signal_data": {"address": "0x4004", "command": "0x01002829"}},
    {"name": "Number 6", "category": "number", "signal_data": {"address": "0x4004", "command": "0x0100A8A9"}},
    {"name": "Number 7", "category": "number", "signal_data": {"address": "0x4004", "command": "0x01006869"}},
    {"name": "Number 8", "category": "number", "signal_data": {"address": "0x4004", "command": "0x0100E8E9"}},
    {"name": "Number 9", "category": "number", "signal_data": {"address": "0x4004", "command": "0x01001819"}},
]
```

**Sources**:
- Tasmota: https://tasmota.github.io/docs/Codes-for-IR-Remotes/#panasonic
- Note: All Panasonic commands use same address (0x4004)

## Step 3: Add Library to NATIVE_LIBRARIES Array

### 3.1 Library Entry Format

Locate the `NATIVE_LIBRARIES` array in `/home/coastal/tapcommand/backend/load_native_ir.py`

Add a new dictionary entry at the end (before the closing `]`):

```python
{
    "brand": "[Brand Name]",
    "model": "Generic [Brand Name]",
    "name": "[Brand Name] TV [Protocol] (ESPHome Native)",
    "device_category": "TVs",
    "protocol": "[protocol_identifier]",
    "commands": [COMMAND_ARRAY_NAME],
    "source_path": "native/[brand]_[protocol]_tv.json",
    "description": "Core [Brand] TV commands mapped to ESPHome native [transmit_action] action",
},
```

### 3.2 Field Definitions

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `brand` | string | Manufacturer name (proper case) | `"LG"`, `"Panasonic"` |
| `model` | string | Model identifier (use "Generic [Brand]") | `"Generic LG"` |
| `name` | string | Display name in UI | `"LG TV transmit_lg (ESPHome Native)"` |
| `device_category` | string | Device type (always "TVs" for TV remotes) | `"TVs"` |
| `protocol` | string | Protocol identifier for YAML generation | `"lg_esp"`, `"panasonic_esp"` |
| `commands` | reference | Python variable name of command array | `LG_TRANSMIT_COMMANDS` |
| `source_path` | string | Virtual path (for reference only) | `"native/lg_transmit_tv.json"` |
| `description` | string | Human-readable description | `"Core LG TV commands mapped to ESPHome native transmit_lg action"` |

### 3.3 Protocol Identifier Naming Convention

**Format**: `[brand]_esp` or `[protocol]_esp`

**Important**: This identifier is used in YAML generation and must be unique.

Examples:
- `samsung_esp` → transmit_samsung
- `lg_esp` → transmit_lg (for LG protocol, NOT NEC)
- `NEC` → transmit_nec (existing LG NEC library)
- `panasonic_esp` → transmit_panasonic

**Avoid Conflicts**: Check existing entries in `NATIVE_LIBRARIES` before choosing identifier.

### 3.4 Real Example: LG transmit_lg

```python
{
    "brand": "LG",
    "model": "Generic LG",
    "name": "LG TV transmit_lg (ESPHome Native)",
    "device_category": "TVs",
    "protocol": "lg_esp",
    "commands": LG_TRANSMIT_COMMANDS,
    "source_path": "native/lg_transmit_tv.json",
    "description": "Core LG TV commands mapped to ESPHome native transmit_lg action",
},
```

### 3.5 Insertion Point

Add the new entry **after** the last existing library but **before** the closing `]` of `NATIVE_LIBRARIES`.

**Correct position**:
```python
NATIVE_LIBRARIES = [
    {...},  # Samsung
    {...},  # LG NEC
    {...},  # Panasonic
    {
        # NEW ENTRY HERE
        "brand": "Sony",
        ...
    },
]  # <- Before this bracket
```

## Step 4: Handle Duplicate Libraries (If Applicable)

### 4.1 Check for Existing Libraries

Before running the script, check if a library with the same brand/name already exists:

```bash
cd /home/coastal/tapcommand/backend
source venv/bin/activate
python3 << 'EOF'
from app.db.database import SessionLocal
from app.models.ir_codes import IRLibrary

session = SessionLocal()
libraries = session.query(IRLibrary).filter(
    IRLibrary.source == "esphome-native",
    IRLibrary.brand == "LG"  # Change brand name as needed
).all()

for lib in libraries:
    print(f"ID: {lib.id}, Name: {lib.name}, Protocol: {lib.protocol}")

session.close()
EOF
```

### 4.2 Delete Duplicate if Found

If a duplicate exists with different protocol (e.g., old LG library):

```bash
cd /home/coastal/tapcommand/backend
source venv/bin/activate
python3 << 'EOF'
from app.db.database import SessionLocal
from app.models.ir_codes import IRLibrary, IRCommand

session = SessionLocal()

# Delete library by ID (found in previous step)
library = session.query(IRLibrary).filter(IRLibrary.id == 1800).one_or_none()
if library:
    session.query(IRCommand).filter(IRCommand.library_id == library.id).delete()
    session.delete(library)
    session.commit()
    print(f"Deleted library ID {library.id}")
else:
    print("Library not found")

session.close()
EOF
```

**Warning**: Only delete if you're certain it's a duplicate. The upsert logic will update existing libraries if brand/name match.

## Step 5: Run the Import Script

### 5.1 Activate Virtual Environment and Run

```bash
cd /home/coastal/tapcommand/backend
source venv/bin/activate
python load_native_ir.py
```

### 5.2 Expected Output

Success message:
```
ESPHome native libraries ensured
```

### 5.3 Verify Database Entry

Check the library was created:

```bash
python3 << 'EOF'
from app.db.database import SessionLocal
from app.models.ir_codes import IRLibrary, IRCommand

session = SessionLocal()

# Find the new library (adjust brand/name as needed)
library = session.query(IRLibrary).filter(
    IRLibrary.source == "esphome-native",
    IRLibrary.brand == "LG",
    IRLibrary.name.like("%transmit_lg%")
).one_or_none()

if library:
    print(f"Library ID: {library.id}")
    print(f"Name: {library.name}")
    print(f"Protocol: {library.protocol}")

    commands = session.query(IRCommand).filter(IRCommand.library_id == library.id).all()
    print(f"Commands: {len(commands)}")

    for cmd in commands:
        print(f"  - {cmd.name} ({cmd.category}): {cmd.signal_data}")
else:
    print("Library not found")

session.close()
EOF
```

### 5.4 Expected Results

- Library ID assigned (auto-increment)
- Protocol matches your identifier
- 16 commands created (power, mute, volume, channel, numbers 0-9)
- Each command has correct signal_data format

## Step 6: YAML Generation Integration

The protocol identifier you chose in Step 3.2 must be mapped in the YAML generation code.

### 6.1 Locate YAML Template Logic

File: `/home/coastal/tapcommand/backend/app/routers/templates.py`

Search for protocol mapping logic (around line 800-900)

### 6.2 Add Protocol Mapping

Find the section that generates remote_transmitter actions. Add mapping for your new protocol:

```python
if protocol == "lg_esp":
    # transmit_lg action
    action_yaml = f"""
        - remote_transmitter.transmit_lg:
            data: {signal_data['data']}
            nbits: {signal_data.get('nbits', 28)}
    """
elif protocol == "panasonic_esp":
    # transmit_panasonic action
    action_yaml = f"""
        - remote_transmitter.transmit_panasonic:
            address: {signal_data['address']}
            command: {signal_data['command']}
    """
```

**Note**: The exact location and format depends on current template implementation. Search for existing protocol mappings (e.g., "samsung_esp") to find the correct insertion point.

## Complete Examples

### Example 1: Sony TV (transmit_sony)

#### Step 1: Research
- Protocol: transmit_sony (data + nbits)
- Source: Tasmota IR codes
- URL: https://tasmota.github.io/docs/Codes-for-IR-Remotes/#sony

#### Step 2: Format Commands
```python
SONY_TRANSMIT_COMMANDS: List[Dict[str, Any]] = [
    {"name": "Power", "category": "power", "signal_data": {"data": "0xA90", "nbits": 12}},
    {"name": "Mute", "category": "audio", "signal_data": {"data": "0x290", "nbits": 12}},
    # ... etc
]
```

#### Step 3: Add to NATIVE_LIBRARIES
```python
{
    "brand": "Sony",
    "model": "Generic Sony",
    "name": "Sony TV (ESPHome Native)",
    "device_category": "TVs",
    "protocol": "sony_esp",
    "commands": SONY_TRANSMIT_COMMANDS,
    "source_path": "native/sony_tv.json",
    "description": "Core Sony TV commands mapped to ESPHome native transmit_sony action",
},
```

#### Step 4: Run Script
```bash
cd /home/coastal/tapcommand/backend
source venv/bin/activate
python load_native_ir.py
```

### Example 2: Philips RC5 (transmit_rc5)

#### Step 1: Research
- Protocol: transmit_rc5 (address + command)
- Source: ESPHome community forums
- Codes found and verified

#### Step 2: Format Commands
```python
PHILIPS_RC5_COMMANDS: List[Dict[str, Any]] = [
    {"name": "Power", "category": "power", "signal_data": {"address": "0x00", "command": "0x0C"}},
    {"name": "Mute", "category": "audio", "signal_data": {"address": "0x00", "command": "0x0D"}},
    # ... etc
]
```

#### Step 3: Add to NATIVE_LIBRARIES
```python
{
    "brand": "Philips",
    "model": "Generic Philips RC5",
    "name": "Philips TV RC5 (ESPHome Native)",
    "device_category": "TVs",
    "protocol": "rc5_esp",
    "commands": PHILIPS_RC5_COMMANDS,
    "source_path": "native/philips_rc5_tv.json",
    "description": "Core Philips TV commands mapped to ESPHome native transmit_rc5 action",
},
```

## Troubleshooting

### Error: Multiple rows found
**Cause**: Duplicate library exists in database
**Solution**: Follow Step 4 to delete duplicate or modify the library name to be unique

### Error: Import fails with validation error
**Cause**: Signal data format doesn't match protocol requirements
**Solution**: Verify signal_data dictionary has correct keys for the protocol (see Step 1.3)

### Error: Library not appearing in UI
**Cause**: Protocol not mapped in YAML generation
**Solution**: Add protocol mapping in templates.py (see Step 6)

### Error: YAML compilation fails
**Cause**: Incorrect ESPHome action syntax
**Solution**: Verify ESPHome documentation for correct parameter names and format

## Summary Checklist

- [ ] Identified ESPHome native protocol (transmit_*)
- [ ] Researched and found IR codes from reliable sources
- [ ] Verified code format matches protocol requirements
- [ ] Found all 16 essential commands (power, mute, volume, channel, numbers)
- [ ] Created command array in load_native_ir.py with proper format
- [ ] Added library entry to NATIVE_LIBRARIES with unique protocol identifier
- [ ] Checked for and handled any duplicate libraries
- [ ] Ran load_native_ir.py script successfully
- [ ] Verified database entry created with correct command count
- [ ] Added protocol mapping to YAML generation (if needed)
- [ ] Tested YAML generation produces valid ESPHome config

## Reference Files

### load_native_ir.py Location
```
/home/coastal/tapcommand/backend/load_native_ir.py
```

### Database Location
```
/home/coastal/tapcommand/backend/tapcommand.db
```

### Python Virtual Environment
```
/home/coastal/tapcommand/backend/venv
```

### YAML Template Router
```
/home/coastal/tapcommand/backend/app/routers/templates.py
```

## Additional Resources

- ESPHome Remote Transmitter: https://esphome.io/components/remote_transmitter.html
- Tasmota IR Codes: https://tasmota.github.io/docs/Codes-for-IR-Remotes/
- Flipper IRDB: https://github.com/Lucaslhm/Flipper-IRDB
- ESPHome Community: https://community.home-assistant.io/c/esphome/

## Notes

- The `source_path` field is virtual and not used to read actual files
- The `file_hash` is auto-generated from brand, name, protocol, and commands
- The `import_status` is automatically set to "imported"
- The `esp_native` flag is automatically set to True
- The `last_updated` timestamp is automatically set to current UTC time
- Library upsert logic updates existing entries if brand+name match
- All existing commands are deleted and recreated on update to ensure consistency
