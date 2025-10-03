# SmartVenue Dynamic ESPHome Migration Plan

## 1. Project Snapshot
- **Stack**: FastAPI backend (`backend/app`), React/Vite frontend (`frontend/`), SQLite via SQLAlchemy models (`backend/app/models`).
- **Important domains**: IR code libraries (`ir_libraries`, `ir_commands` tables), YAML Builder interface, stored ESPHome templates (`esp_templates` table).
- **Legacy reference**: `esp_multi` flat YAML shows desired dual-brand behaviour for Samsung + LG on a Wemos D1 Mini.

## 2. Existing YAML Builder Flow
1. **Frontend (App.tsx)**
   - Loads base template from `/api/v1/templates/base` and device hierarchy from `/device-hierarchy`.
   - Lets operator pick up to two libraries and map them onto five logical ports.
   - Submits assignments to `/preview` and renders the returned YAML/binary compile output.
2. **Backend (`routers/templates.py`)**
   - Fetches selected `IRLibrary` rows and swaps placeholders in the stored D1 Mini template:
     - `{{PORT_BLOCK}}` and `{{DEVICE_BLOCK}}` for human-readable comments.
     - `{{CAPABILITY_BRAND_LINES}}`, `{{CAPABILITY_COMMAND_LINES}}`, `{{CUSTOM_SCRIPT_BLOCK}}`, `{{BUTTON_SECTION}}` for auto-generated logic.
   - Current native support limited to Samsung + LG profiles defined in `NATIVE_IR_PROFILES`.
3. **Stored template (`esphome/templates/d1_mini_base.yaml`)**
   - Provides substitution hooks for Wi-Fi/API/OTA secrets and for builder-driven sections.
   - Contains single-transmitter setup (`remote_transmitter` on GPIO14) but no multi-brand scripts yet.

## 3. esp_multi Capability Breakdown
- Dual-sends Samsung + LG codes for core commands via scripted `remote_transmitter.transmit_*` sections.
- Exposes Home Assistant services (`tv_power`, `tv_channel_up`, `tv_channel`, etc.) and template buttons for manual triggering.
- Implements smart channel sequencing: stores requested channel digits in globals, iterates through digits with delay, and reuses the digit script (`dual_number`).
- Supplies diagnostics (logging, metadata text sensor) but relies on static YAML.

## 4. Migration Goal
Deliver the esp_multi feature set (per-port command routing, smart channel service, manual buttons, metadata reporting) using dynamically generated YAML from database-backed templates. Target device remains D1 Mini; the template must adapt to user-selected libraries and ports without manual editing.

## 5. Template Extension Strategy
1. **Template placeholders**
   - Add new anchors in the D1 Mini template (to be stored in DB):
     - `{{SERVICE_SECTION}}` – for API service definitions mirroring esp_multi (power, volume, mute, channel navigation, digit entry, smart channel).
     - `{{GLOBAL_SECTION}}` – for digit queue globals (`channel_digits`, `digit_index`).
     - `{{SCRIPT_SECTION}}` – for per-port transmit scripts (native + raw) and smart channel helpers (`smart_channel`, `send_next_channel_digit`).
   - Maintain existing `{{CUSTOM_SCRIPT_BLOCK}}` for additional helper scripts if needed.
2. **Per-port naming**
   - Generate IDs like `send_port1_power`, `send_port2_digit_5`, so Home Assistant services can dispatch commands via the selected port assignment.
   - Continue to derive friendly metadata for debugging comments.
3. **Service design**
   - Single `esphome:` service group with inputs `port` and `command` to route requests dynamically *or* replicate discrete services (`tv_power`, `tv_channel`, `tv_number`, etc.) as in esp_multi; decision: keep discrete names for backwards compatibility, but each delegates to the generic dispatcher script.

## 6. Native Command Handling
- When `IRLibrary.esp_native` is true:
  - Use `NATIVE_IR_PROFILES` as now to generate script bodies with `remote_transmitter.transmit_samsung` / `transmit_nec` calls.
  - For dual-brand scenarios (Samsung + LG simultaneously), create a composite script that fires both codes with 50 ms delay, matching the esp_multi timing.
- If multiple native libraries are assigned (e.g., Samsung on Port 1, LG on Port 2), each port’s script references its own brand profile while shared services decide which port to address.

## 7. Raw Command Handling (Flipper imports)
- `ir_commands` rows contain `protocol`, `signal_data`, optional `frequency`, `duty_cycle`.
- For allowed commands (power, mute, volume up/down, channel up/down, digits 0–9):
  - Convert `signal_data` into ESPHome-compatible fields:
    - `type == "raw"`: transform the comma/space-separated durations into `[int, -int, ...]` lists; set `carrier_frequency` and `carrier_duty_percent` if present.
    - `protocol` in {`NEC`, `Samsung32`, `RC5`, etc.}: prefer protocol-specific transmitter call if we map the data (address/command); otherwise fall back to raw conversion.
    - `protocol == "Pronto"`/Pronto-like: supply `transmit_pronto` with the stored hex.
- Embed raw transmit blocks inside the same per-port script structure so services call them identically to native ones.

## 8. YAML Prototype & Validation Plan
1. **Prototype file**: `esphome/prototypes/ir_dynamic_test.yaml` combining
   - Port 1: native Samsung commands.
   - Port 2: raw-only brand using Flipper pulse data.
   - API services mirroring esp_multi behaviour.
   - Smart channel scripts/globals.
2. **Compile loop**: run `esphome compile esphome/prototypes/ir_dynamic_test.yaml` (via FirmwareBuilder or direct CLI) until syntax, indentation, and command usage are correct.
3. **Manual inspection**: ensure service payloads reference correct script IDs and per-port scripts call the expected transmitter instructions.
4. **Capture learnings**: note required YAML nuances (indentation under `remote_transmitter.transmit_raw`, necessary delays, etc.) and transfer them to the template generator.

## 9. Backend Implementation Steps
1. **Update stored base template**
   - Modify the D1 Mini entry inside `esp_templates` (likely via PUT through settings UI or migration script) to include new placeholders and service stubs.
2. **Extend builder helpers (`routers/templates.py`)**
   - Replace `_build_native_script_block` and `_build_native_button_block` with generalized builders that:
     - Iterate active ports, fetch all qualifying commands for each `library_id`.
     - Produce combined script YAML for native or raw commands based on stored metadata.
     - Emit shared dispatcher scripts (`execute_ir_command`, `send_next_channel_digit`).
   - Generate `{{SERVICE_SECTION}}`, `{{GLOBAL_SECTION}}`, `{{BUTTON_SECTION}}` text.
   - Keep comment rendering and capability reporting updated with brand/command lists.
3. **Limit command set**
   - Filter `IRCommand` list to the allowed names; map variations (e.g., `Vol Up`, `Volume+`) onto canonical keys.
4. **Return preview**
   - Confirm `/preview` still supports `include_comments` stripping.

## 10. Frontend Considerations
- Minimal changes: ensure the builder still populates `yamlPreview` from `/preview`; optionally surface new service names in UI copy.
- (Optional) Add a per-command toggle UI later; not required for migration.

## 11. Testing & Rollout
- **Unit tests**: add backend tests that mock libraries with native and raw commands, call `/preview`, and assert the generated YAML contains correct script/service snippets.
- **Smoke test**: compile generated YAML via `/compile-stream` and confirm binary output.
- **Device validation**: flash to a lab D1 Mini, trigger services through Home Assistant or ESPHome dashboard, and verify IR transmissions on each port.

## 12. Future Enhancements
- Expand command coverage beyond the core set once stable.
- Support multiple transmitters (if hardware adds more GPIOs).
- Cache rendered YAML/compile artifacts per assignment to accelerate repeated builds.
- Add UI-level simulation or command testing directly from the builder.

## 13. Working Checklist
1. Draft prototype YAML (native + raw) and obtain successful compile.
2. Update base template with new placeholders.
3. Implement generalized builder functions and regeneration logic.
4. Add tests for preview output (native-only, raw-only, mixed).
5. Verify end-to-end from builder selection → preview → compile.
6. Document deployment steps and sample Home Assistant service calls.

---
This file summarizes the current architecture, the esp_multi behaviour we are porting, and the concrete plan for migrating to dynamic ESPHome generation while preparing for raw IR command support.
