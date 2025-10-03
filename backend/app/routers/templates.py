from typing import List, Dict, Any, Optional, Set, Tuple
import re
from datetime import datetime
import json
from dataclasses import dataclass
from textwrap import dedent
from pathlib import Path
import os
import asyncio
import threading
import queue

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db.database import get_db, SessionLocal
from ..models.ir_codes import ESPTemplate, IRLibrary, IRCommand
from ..models.settings import ApplicationSetting
from ..models.device import Device
from ..models.device_management import ManagedDevice
from ..services.firmware_builder import get_firmware_builder
from ..services.esphome_client import esphome_manager
from ..services.settings_service import settings_service
from ..services.ota_uploader import run_ota_with_callback, run_http_ota_with_callback
from ..core.config import settings

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])


def _apply_database_settings(yaml_content: str, db: Session) -> str:
    """Apply database-backed settings to YAML content, replacing hardcoded values"""

    # Get WiFi settings from database
    wifi_ssid_setting = db.query(ApplicationSetting).filter(ApplicationSetting.key == "wifi_ssid").first()
    wifi_password_setting = db.query(ApplicationSetting).filter(ApplicationSetting.key == "wifi_password").first()
    wifi_hidden_setting = db.query(ApplicationSetting).filter(ApplicationSetting.key == "wifi_hidden").first()
    api_key_setting = db.query(ApplicationSetting).filter(ApplicationSetting.key == "esphome_api_key").first()

    # Use database values or fallback to defaults
    wifi_ssid = wifi_ssid_setting.get_typed_value() if wifi_ssid_setting else "TV"
    wifi_password = wifi_password_setting.get_typed_value() if wifi_password_setting else "changeme"
    wifi_hidden = wifi_hidden_setting.get_typed_value() if wifi_hidden_setting else True
    api_key = api_key_setting.get_typed_value() if api_key_setting else "uuPgF8JOAV/ZhFbDV4iS4Kwr1MV5H97p6Nk+HnpE0+g="

    # Replace substitution values in YAML
    yaml_content = re.sub(r'wifi_ssid:\s*"[^"]*"', f'wifi_ssid: "{wifi_ssid}"', yaml_content)
    yaml_content = re.sub(r'wifi_password:\s*"[^"]*"', f'wifi_password: "{wifi_password}"', yaml_content)
    yaml_content = re.sub(r'wifi_hidden:\s*(true|false)', f'wifi_hidden: {"true" if wifi_hidden else "false"}', yaml_content)
    yaml_content = re.sub(r'api_key:\s*"[^"]*"', f'api_key: "{api_key}"', yaml_content)

    return yaml_content


class ESPTemplateSummary(BaseModel):
    id: int
    name: str
    board: str
    description: Optional[str]
    version: str
    revision: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


def increment_version(current_version: str, increment_type: str) -> str:
    """Increment version number based on type (major, minor, patch)"""
    try:
        # Parse version in format "major.minor.patch"
        parts = current_version.split(".")
        if len(parts) != 3:
            # Default to 1.0.0 if invalid format
            parts = ["1", "0", "0"]

        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

        if increment_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif increment_type == "minor":
            minor += 1
            patch = 0
        else:  # patch (default)
            patch += 1

        return f"{major}.{minor}.{patch}"
    except (ValueError, IndexError):
        # Fallback to default version
        return "1.0.0"


def update_yaml_version_and_date(yaml_content: str, version: str) -> str:
    """Update version and date in YAML content"""
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Update version in project section
    yaml_content = re.sub(
        r'(\s+version:\s*")[^"]*(")',
        f'\\g<1>{version}\\g<2>',
        yaml_content
    )

    # Remove any existing version comments first
    lines = yaml_content.split('\n')
    cleaned_lines = []

    for line in lines:
        # Skip existing version comments
        if not re.match(r'\s*#\s*Version\s+\d+\.\d+\.\d+\s*-\s*Saved on', line):
            cleaned_lines.append(line)

    # Add new version comment right before project section
    updated_lines = []
    for line in cleaned_lines:
        if line.strip() == 'project:' and not any('Version' in prev_line for prev_line in updated_lines[-3:]):
            updated_lines.append(f'  # Version {version} - Saved on {current_date}')
        updated_lines.append(line)

    return '\n'.join(updated_lines)


COMMAND_LABELS = {
    'power': 'Power',
    'power_on': 'Power ON',
    'power_off': 'Power OFF',
    'volume_up': 'Volume Up',
    'volume_down': 'Volume Down',
    'mute': 'Mute',
    'channel_up': 'Channel Up',
    'channel_down': 'Channel Down',
    'number_0': '0',
    'number_1': '1',
    'number_2': '2',
    'number_3': '3',
    'number_4': '4',
    'number_5': '5',
    'number_6': '6',
    'number_7': '7',
    'number_8': '8',
    'number_9': '9',
}


CANONICAL_COMMANDS: Tuple[str, ...] = (
    'power',
    'mute',
    'volume_up',
    'volume_down',
    'channel_up',
    'channel_down',
    'number_0',
    'number_1',
    'number_2',
    'number_3',
    'number_4',
    'number_5',
    'number_6',
    'number_7',
    'number_8',
    'number_9',
)


PORT_FUNCTION_DISPLAY = {
    'power': 'Power',
    'mute': 'Mute',
    'volume_up': 'Volume Up',
    'volume_down': 'Volume Down',
    'channel_up': 'Channel Up',
    'channel_down': 'Channel Down',
    'number_0': 'Digit 0',
    'number_1': 'Digit 1',
    'number_2': 'Digit 2',
    'number_3': 'Digit 3',
    'number_4': 'Digit 4',
    'number_5': 'Digit 5',
    'number_6': 'Digit 6',
    'number_7': 'Digit 7',
    'number_8': 'Digit 8',
    'number_9': 'Digit 9',
}


@dataclass
class TransmissionSpec:
    protocol: str
    payload: Dict[str, Any]


@dataclass
class PortProfile:
    port_number: int
    library: Optional[IRLibrary]
    commands: Dict[str, TransmissionSpec]

    @property
    def brand(self) -> str:
        if not self.library:
            return "Unassigned"
        return (self.library.brand or "Unknown").strip() or "Unknown"

    @property
    def description(self) -> str:
        if not self.library:
            return "Unassigned"
        display_name = self.library.name or self.library.model or self.library.brand or "Unnamed"
        model = f" • {self.library.model}" if self.library.model else ""
        return f"{display_name} ({self.library.brand}{model})"


def _indent(lines: List[str], spaces: int) -> List[str]:
    prefix = " " * spaces
    return [f"{prefix}{line}" if line else "" for line in lines]


def _build_nested_if(entries: List[Tuple[str, List[str]]], error_message: str, error_arg: str) -> List[str]:
    if not entries:
        return [
            "- logger.log:",
            "    level: WARN",
            f"    format: \"{error_message}\"",
            f"    args: ['{error_arg}']",
        ]

    def helper(index: int) -> List[str]:
        condition, actions = entries[index]
        block: List[str] = [
            "- if:",
            "    condition:",
            f"      lambda: 'return {condition};'",
            "    then:",
        ]
        block.extend(_indent(actions, 6))

        if index < len(entries) - 1:
            block.append("    else:")
            block.extend(_indent(helper(index + 1), 6))
        else:
            block.append("    else:")
            block.extend(
                [
                    "      - logger.log:",
                    "          level: WARN",
                    f"          format: \"{error_message}\"",
                    f"          args: ['{error_arg}']",
                ]
            )

        return block

    return helper(0)


def _normalize_command_name(command: IRCommand) -> Optional[str]:
    name = (command.name or "").strip().lower()
    if not name:
        return None

    simple = re.sub(r"[^a-z0-9]", "", name)
    category = (command.category or "").lower()

    # Handle discrete power commands first
    if "power" in name or "pwr" in simple or simple in {"poweron", "poweroff", "onoff"}:
        # Check for discrete ON command
        if any(token in name for token in ["on", "start"]) and "off" not in name:
            if simple in {"poweron", "on"}:
                return "power_on"
        # Check for discrete OFF command
        if any(token in name for token in ["off", "standby"]) and "on" not in name:
            if simple in {"poweroff", "off"}:
                return "power_off"
        # Default to toggle power
        return "power"

    if "mute" in name or simple.endswith("mut"):
        return "mute"

    if "volume" in name or "vol" in name or category == "volume":
        if any(token in name for token in ["down", "-", "dec", "lower", "min", "dn"]):
            return "volume_down"
        return "volume_up"

    if any(token in name for token in ["channel", "ch", "prog", "prg"]):
        if any(token in name for token in ["down", "prev", "back", "-", "min"]):
            return "channel_down"
        return "channel_up"

    if category == "audio" and "mute" in name:
        return "mute"

    # Numeric buttons
    digit_match = re.search(r"(\d)", simple)
    if digit_match and category in {"number", "channel"} or simple.isdigit():
        digit = digit_match.group(1)
        return f"number_{digit}"

    if simple in {"ok", "enter"}:
        return None

    # Explicit name like "num1"
    num_match = re.match(r"num(\d)", simple)
    if num_match:
        return f"number_{num_match.group(1)}"

    return None




def _normalize_hex_literal(value: Any) -> Optional[str]:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    text = text.replace(" ", "").replace("_", "")
    if text.lower().startswith("0x"):
        text = text[2:]

    if not text:
        return None

    try:
        int(text, 16)
    except (TypeError, ValueError):
        return None

    if len(text) % 2 != 0:
        text = f"0{text}"

    return f"0x{text.upper()}"


def _normalize_mac_address(mac: Optional[str]) -> Optional[str]:
    if not mac:
        return None
    clean = ''.join(ch for ch in mac if ch.isalnum())
    if len(clean) == 12:
        parts = [clean[i:i + 2].upper() for i in range(0, 12, 2)]
        return ':'.join(parts)
    return mac.upper()


def _extract_capabilities_mac(capabilities: Optional[Dict[str, Any]]) -> Optional[str]:
    if not capabilities or not isinstance(capabilities, dict):
        return None
    metadata = capabilities.get("metadata")
    if isinstance(metadata, dict):
        mac = metadata.get("mac") or metadata.get("mac_address")
        if mac:
            return mac
    return capabilities.get("mac") or capabilities.get("mac_address")


def _sync_ports_from_capabilities(managed_device: ManagedDevice, capabilities: Optional[Dict[str, Any]]):
    if not capabilities or not isinstance(capabilities, dict):
        return

    ports_payload = capabilities.get("ports")
    if not isinstance(ports_payload, list):
        return

    port_map: Dict[int, Dict[str, Any]] = {}
    for entry in ports_payload:
        try:
            port_number = int(entry.get("port"))
        except (TypeError, ValueError):
            continue
        port_map[port_number] = entry

    for port in managed_device.ir_ports:
        entry = port_map.get(port.port_number)
        if entry:
            port.is_active = True
            description = entry.get("description")
            if description and not (port.connected_device_name and port.connected_device_name.strip()):
                port.connected_device_name = description
        else:
            port.is_active = False


def _parse_raw_signal(signal_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    data = signal_data.get('data') or signal_data.get('code')
    if not data:
        return None

    if isinstance(data, list):
        values = data
    else:
        # Split on whitespace and commas
        chunks = re.split(r"[\s,]+", str(data).strip())
        values = []
        for chunk in chunks:
            if not chunk:
                continue
            try:
                values.append(int(float(chunk)))
            except ValueError:
                try:
                    values.append(int(chunk, 16))
                except ValueError:
                    return None

    if not values:
        return None

    # Ensure alternating positive/negative durations
    formatted: List[int] = []
    for idx, value in enumerate(values):
        if idx % 2 == 0:
            formatted.append(int(value))
        else:
            formatted.append(-int(value))

    frequency = signal_data.get('frequency')
    duty_cycle = signal_data.get('duty_cycle')

    return {
        'code': formatted,
        'frequency': frequency,
        'duty_cycle': duty_cycle,
    }


def _build_command_transmissions(library: IRLibrary, commands: List[IRCommand]) -> Dict[str, TransmissionSpec]:
    transmissions: Dict[str, TransmissionSpec] = {}

    for command in commands:
        canonical = _normalize_command_name(command)
        if not canonical:
            continue

        protocol = (command.protocol or '').lower()
        signal = command.signal_data or {}
        existing = transmissions.get(canonical)

        if protocol == 'samsung_esp':
            direct_data = _normalize_hex_literal(signal.get('data'))
            if not direct_data:
                continue
            transmissions[canonical] = TransmissionSpec(
                protocol='samsung',
                payload={'data': direct_data}
            )
            continue

        if protocol == 'lg_esp':
            direct_data = _normalize_hex_literal(signal.get('data'))
            nbits = signal.get('nbits')
            if direct_data and nbits is not None:
                transmissions[canonical] = TransmissionSpec(
                    protocol='lg',
                    payload={'data': direct_data, 'nbits': int(nbits)}
                )
            continue

        if protocol == 'panasonic_esp':
            address = _normalize_hex_literal(signal.get('address'))
            command = _normalize_hex_literal(signal.get('command'))
            if address and command:
                transmissions[canonical] = TransmissionSpec(
                    protocol='panasonic',
                    payload={'address': address, 'command': command}
                )
            continue

        if protocol == 'sony_esp':
            direct_data = _normalize_hex_literal(signal.get('data'))
            nbits = signal.get('nbits')
            if direct_data and nbits is not None:
                transmissions[canonical] = TransmissionSpec(
                    protocol='sony',
                    payload={'data': direct_data, 'nbits': int(nbits)}
                )
            continue

        if protocol.startswith('samsung'):
            address = signal.get('address')
            cmd = signal.get('command')
            if address and cmd and not existing:
                transmissions[canonical] = TransmissionSpec(
                    protocol='nec',
                    payload={'address': address, 'command': cmd}
                )
            continue

        if protocol.startswith('nec'):
            address = signal.get('address')
            cmd = signal.get('command')
            if address and cmd and not existing:
                transmissions[canonical] = TransmissionSpec(
                    protocol='nec',
                    payload={'address': address, 'command': cmd}
                )
            continue

        if protocol.startswith('pronto'):
            pronto_data = signal.get('data')
            if pronto_data:
                transmissions[canonical] = TransmissionSpec(
                    protocol='pronto',
                    payload={'data': pronto_data}
                )
            continue

        raw_payload = _parse_raw_signal(signal)
        if raw_payload and not existing:
            transmissions[canonical] = TransmissionSpec(
                protocol='raw',
                payload=raw_payload
            )

    return transmissions


def _escape_cpp_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')




def _render_transmit_lines(spec: TransmissionSpec, port_number: int) -> List[str]:
    protocol = spec.protocol
    payload = spec.payload

    if protocol == 'samsung':
        # Check for direct data format first
        data = payload.get('data')
        if data:
            normalized = _normalize_hex_literal(data) or data
            return [
                "- remote_transmitter.transmit_samsung:",
                f"    transmitter_id: ir_transmitter_port{port_number}",
                f"    data: {normalized}",
            ]
        return []

    if protocol == 'lg':
        data = payload.get('data')
        nbits = payload.get('nbits')
        if data and nbits is not None:
            normalized = _normalize_hex_literal(data) or data
            return [
                "- remote_transmitter.transmit_lg:",
                f"    transmitter_id: ir_transmitter_port{port_number}",
                f"    data: {normalized}",
                f"    nbits: {int(nbits)}",
            ]
        return []

    if protocol == 'panasonic':
        address = payload.get('address')
        command = payload.get('command')
        if address and command:
            normalized_address = _normalize_hex_literal(address) or address
            normalized_command = _normalize_hex_literal(command) or command
            return [
                "- remote_transmitter.transmit_panasonic:",
                f"    transmitter_id: ir_transmitter_port{port_number}",
                f"    address: {normalized_address}",
                f"    command: {normalized_command}",
            ]
        return []

    if protocol == 'sony':
        data = payload.get('data')
        nbits = payload.get('nbits')
        if data and nbits is not None:
            normalized = _normalize_hex_literal(data) or data
            return [
                "- remote_transmitter.transmit_sony:",
                f"    transmitter_id: ir_transmitter_port{port_number}",
                f"    data: {normalized}",
                f"    nbits: {int(nbits)}",
            ]
        return []

    if protocol == 'nec':
        address = payload.get('address')
        command = payload.get('command')
        if not address or not command:
            return []

        # Convert Flipper-style "07 00 00 00" into single-byte hex literals
        def convert_hex_value(hex_str):
            if isinstance(hex_str, str):
                first = hex_str.strip().split()
                if first:
                    token = first[0]
                    if token.lower().startswith('0x'):
                        return token
                    return f"0x{token.upper()}"
            return hex_str

        formatted_address = convert_hex_value(address)
        formatted_command = convert_hex_value(command)

        return [
            "- remote_transmitter.transmit_nec:",
            f"    transmitter_id: ir_transmitter_port{port_number}",
            f"    address: {formatted_address}",
            f"    command: {formatted_command}",
        ]

    if protocol == 'pronto':
        data = payload.get('data')
        if not data:
            return []
        return [
            "- remote_transmitter.transmit_pronto:",
            f"    transmitter_id: ir_transmitter_port{port_number}",
            f"    data: \"{_escape_cpp_string(str(data))}\"",
        ]

    if protocol == 'raw':
        code = payload.get('code') or []
        if not code:
            return []

        def _format_frequency(freq: Any) -> Optional[str]:
            if freq is None:
                return None
            try:
                value = float(freq)
            except (TypeError, ValueError):
                return None
            if value >= 1000 and abs(value % 1000) < 1e-6:
                return f"{int(value / 1000)}kHz"
            return str(int(value))

        frequency = _format_frequency(payload.get('frequency'))
        duty_cycle = payload.get('duty_cycle')
        if duty_cycle is not None:
            try:
                duty_cycle = float(duty_cycle) * 100
            except (TypeError, ValueError):
                duty_cycle = None

        code_literal = ', '.join(str(int(v)) for v in code)

        lines = [
            "- remote_transmitter.transmit_raw:",
            f"    transmitter_id: ir_transmitter_port{port_number}",
        ]

        if frequency:
            lines.append(f"    carrier_frequency: {frequency}")
        if duty_cycle is not None:
            lines.append(f"    duty_percent: {round(duty_cycle, 1)}")
        lines.append(f"    code: [{code_literal}]")
        return lines

    return []


def generate_single_command_yaml(library_id: int, command_name: str, port_number: int, db: Session) -> Optional[List[str]]:
    """
    Generate YAML lines for a single IR command from a specific library

    Args:
        library_id: Database ID of the IR library
        command_name: Name of the command (e.g., 'power', 'volume_up', 'number_1')
        port_number: Physical port number (1-5)
        db: Database session

    Returns:
        List of YAML lines or None if command not found
    """
    # Get the specific command from the library
    command = db.query(IRCommand).filter(
        IRCommand.library_id == library_id,
        IRCommand.name == command_name
    ).first()

    if not command:
        return None

    # Create transmission spec
    protocol = (command.protocol or '').lower()
    signal_data = command.signal_data or {}

    # Build transmission spec based on protocol
    if protocol.startswith('samsung'):
        if 'address' in signal_data and 'command' in signal_data:
            spec = TransmissionSpec(
                protocol='samsung',
                payload={'address': signal_data['address'], 'command': signal_data['command']}
            )
        elif 'data' in signal_data:
            spec = TransmissionSpec(
                protocol='samsung',
                payload={'data': signal_data['data']}
            )
        else:
            return None
    elif protocol.startswith('nec'):
        if 'address' in signal_data and 'command' in signal_data:
            spec = TransmissionSpec(
                protocol='nec',
                payload={'address': signal_data['address'], 'command': signal_data['command']}
            )
        else:
            return None
    elif protocol == 'raw' and 'data' in signal_data:
        spec = TransmissionSpec(
            protocol='raw',
            payload={
                'code': signal_data['data'].split() if isinstance(signal_data['data'], str) else signal_data['data'],
                'frequency': signal_data.get('frequency'),
                'duty_cycle': signal_data.get('duty_cycle')
            }
        )
    else:
        return None

    # Generate YAML lines using existing render function
    return _render_transmit_lines(spec, port_number)


def generate_selected_commands_yaml(command_selections: Dict[str, Tuple[int, str]], port_number: int, db: Session) -> List[str]:
    """
    Generate YAML lines for user-selected commands from various libraries

    Args:
        command_selections: Dict mapping command_name -> (library_id, command_name_in_db)
                          e.g., {'power': (123, 'Power'), 'volume_up': (124, 'Vol_up')}
        port_number: Physical port number (1-5)
        db: Database session

    Returns:
        List of YAML lines for all selected commands
    """
    yaml_lines = []

    # Basic TV commands that users typically want
    basic_commands = [
        'power', 'power_on', 'power_off', 'mute', 'volume_up', 'volume_down',
        'channel_up', 'channel_down',
        'number_0', 'number_1', 'number_2', 'number_3', 'number_4',
        'number_5', 'number_6', 'number_7', 'number_8', 'number_9'
    ]

    for command_key in basic_commands:
        if command_key in command_selections:
            library_id, db_command_name = command_selections[command_key]
            command_yaml = generate_single_command_yaml(library_id, db_command_name, port_number, db)

            if command_yaml:
                yaml_lines.extend(command_yaml)
            else:
                # Add missing command warning
                yaml_lines.extend(_render_missing_command_lines(port_number, command_key))

        # Fallback: if power_on or power_off is missing, try using power toggle
        elif command_key in ('power_on', 'power_off') and 'power' in command_selections:
            library_id, db_command_name = command_selections['power']
            command_yaml = generate_single_command_yaml(library_id, db_command_name, port_number, db)

            if command_yaml:
                # Replace 'power:' with 'power_on:' or 'power_off:' in the YAML
                modified_yaml = []
                for line in command_yaml:
                    if line.strip().startswith('- button.press:'):
                        # Replace the button press action name
                        modified_yaml.append(line.replace(f'ir_port_{port_number}_power', f'ir_port_{port_number}_{command_key}'))
                    else:
                        modified_yaml.append(line)
                yaml_lines.extend(modified_yaml)

    return yaml_lines


def _render_missing_command_lines(port_number: int, command_key: str) -> List[str]:
    label = COMMAND_LABELS.get(command_key, command_key.replace('_', ' ').title())
    return [
        "- logger.log:",
        "    level: WARN",
        f"    format: \"Port {port_number} is missing command '{label}'\"",
    ]


def _build_capabilities_payload_lines(
    port_profiles: List[PortProfile],
    *,
    template: Optional[ESPTemplate] = None,
) -> List[str]:
    """Create static C++ lines that publish a pre-rendered JSON payload."""

    ports_payload: List[Dict[str, Any]] = []
    library_ids: Set[int] = set()

    for profile in port_profiles:
        if not profile.library:
            continue

        entry: Dict[str, Any] = {
            "port": profile.port_number,
            "lib": profile.library.id,  # Shortened from library_id to save RAM
        }

        if profile.brand and profile.brand.lower() not in {"unassigned", "unknown"}:
            entry["brand"] = profile.brand

        # Removed description field to reduce JSON payload size (~60% reduction)
        # description = profile.description
        # if description and description.lower() not in {"unassigned", "unknown"}:
        #     entry["description"] = description

        ports_payload.append(entry)
        library_ids.add(profile.library.id)

    capabilities: Dict[str, Any] = {
        "project": "smartvenue.dynamic_ir",
        "schema": 1,
        "ports": ports_payload,
    }

    if library_ids:
        capabilities["libs"] = sorted(library_ids)  # Shortened from library_ids

    if template is not None:
        template_info: Dict[str, Any] = {}
        if template.id is not None:
            template_info["id"] = template.id
        if getattr(template, "revision", None) is not None:
            template_info["revision"] = template.revision
        if getattr(template, "version", None):
            template_info["version"] = template.version
        if template_info:
            capabilities["template"] = template_info

    payload_json = json.dumps(capabilities, separators=(",", ":"), ensure_ascii=True)

    return [
        f'static const char *kCapabilitiesPayload = R"json({payload_json})json";',
        "id(ir_capabilities_payload).publish_state(kCapabilitiesPayload);",
        'id(device_hostname).publish_state(App.get_name().c_str());',
    ]


def _inject_capabilities_payload(rendered_yaml: str, capability_lines: List[str]) -> str:
    """Ensure the publish_capabilities lambda publishes the static payload."""

    if not capability_lines:
        return rendered_yaml

    payload_block = "\n".join(" " * 10 + line for line in capability_lines)

    if "{{CAPABILITY_PAYLOAD_LINES}}" in rendered_yaml:
        rendered_yaml = rendered_yaml.replace("{{CAPABILITY_PAYLOAD_LINES}}", payload_block)
    else:
        lines = rendered_yaml.splitlines()
        replaced = False
        for idx, line in enumerate(lines):
            if line.strip() == "- id: publish_capabilities":
                lambda_index = None
                for j in range(idx + 1, len(lines)):
                    if lines[j].strip() == "- lambda: |-":
                        lambda_index = j
                        break
                if lambda_index is None:
                    continue

                body_start = lambda_index + 1
                body_end = body_start
                while body_end < len(lines):
                    stripped = lines[body_end].strip()
                    if stripped.startswith("id(ir_capabilities_payload).publish_state"):
                        break
                    body_end += 1

                if body_end < len(lines):
                    lines[body_start:body_end + 1] = [" " * 10 + line for line in capability_lines]
                    rendered_yaml = "\n".join(lines)
                    replaced = True
                break

        if not replaced:
            rendered_yaml = "\n".join(lines)

    lines = rendered_yaml.splitlines()
    esphome_index = next((i for i, text in enumerate(lines) if text.strip() == "esphome:"), None)
    if esphome_index is not None:
        block_end = esphome_index + 1
        while block_end < len(lines):
            current = lines[block_end]
            if current.startswith("  ") or current.strip() == "":
                block_end += 1
                continue
            break

        on_boot_exists = any(
            lines[i].lstrip().startswith("on_boot:")
            for i in range(esphome_index + 1, block_end)
        )

        if not on_boot_exists:
            insertion = [
                "  on_boot:",
                "    priority: -10",
                "    then:",
                "      - script.execute: publish_capabilities",
            ]

            lines[block_end:block_end] = insertion + [""]
            rendered_yaml = "\n".join(lines)

    return rendered_yaml


def _generate_capability_brand_cpp(port_capabilities) -> str:
    """Generate C++ code to populate the brands array in capabilities JSON"""
    if not port_capabilities:
        return "          // No brands configured"

    lines = []
    brands_seen = set()

    for port_cap in port_capabilities:
        brand = port_cap['brand']
        if brand not in brands_seen:
            brands_seen.add(brand)
            # Escape brand name for C++ string literal
            escaped_brand = _escape_cpp_string(brand)
            lines.append(f'          brands.add("{escaped_brand}");')

    return "\n".join(lines)


def _generate_capability_command_cpp(port_capabilities) -> str:
    """Generate C++ code to populate the commands array in capabilities JSON"""
    if not port_capabilities:
        return "          // No commands configured"

    lines = []
    all_commands = set()

    # Collect all unique commands across all ports
    for port_cap in port_capabilities:
        all_commands.update(port_cap['commands'])

    # Sort commands for consistent output
    sorted_commands = sorted(all_commands)

    for command in sorted_commands:
        # Escape command name for C++ string literal
        escaped_command = _escape_cpp_string(command)
        lines.append(f'          commands.add("{escaped_command}");')

    return "\n".join(lines)



def _build_shared_scripts(port_profiles: List[PortProfile]) -> List[str]:
    lines: List[str] = []

    # No port switching needed - using 5 separate IR transmitters
    # Get assigned port numbers (only ports with actual device assignments)
    assigned_port_profiles = [p for p in port_profiles if p.library is not None]
    assigned_port_map = {profile.port_number: profile for profile in assigned_port_profiles}
    assigned_ports = sorted(assigned_port_map.keys())

    def _build_command_dispatch(script_name: str, command_key: str) -> List[str]:
        block: List[str] = [
            f"- id: {script_name}",
            "  parameters:",
            "    target_port: int",
            "  then:",
        ]

        if not assigned_ports:
            block.extend([
                "    - logger.log:",
                "        level: WARN",
                f"        format: \"No ports configured for {command_key}\"",
            ])
            return block

        entries: List[Tuple[str, List[str]]] = []
        for port in assigned_ports:
            profile = assigned_port_map[port]
            spec = profile.commands.get(command_key)
            if spec:
                actions = _render_transmit_lines(spec, port)
            else:
                actions = _render_missing_command_lines(port, command_key)
            entries.append((f"target_port == {port}", actions))

        nested = _build_nested_if(entries, f"Port %d unsupported for {command_key}", "target_port")
        block.extend(_indent(nested, 4))
        return block

    def _build_digit_dispatch() -> List[str]:
        """
        Array-based optimized dispatch_digit implementation.
        Uses static arrays for O(1) lookup instead of nested if/else pyramid.
        88% smaller and faster than the original nested approach.
        """
        block: List[str] = [
            "- id: dispatch_digit",
            "  parameters:",
            "    target_port: int",
            "    digit: int",
            "  then:",
            "    - lambda: |-",
        ]

        if not assigned_ports:
            block.extend([
                "        ESP_LOGW(\"dispatch\", \"No ports configured for digit command\");",
            ])
            return block

        # Build static arrays for each port
        lambda_lines: List[str] = []

        for port in assigned_ports:
            profile = assigned_port_map[port]
            protocol = profile.commands.get('power', profile.commands.get('number_0'))
            if not protocol:
                continue

            protocol_name = protocol.protocol

            # Collect all 10 digit codes
            digit_codes = []
            for digit in range(10):
                spec = profile.commands.get(f'number_{digit}')
                if spec and spec.payload:
                    digit_codes.append(spec.payload)
                else:
                    digit_codes.append(None)

            # Generate array definitions based on protocol
            lambda_lines.append(f"        // Port {port} - {protocol_name.title()}")

            if protocol_name == 'samsung':
                # Samsung: single data array
                data_values = [_normalize_hex_literal(d.get('data')) if d else '0x0' for d in digit_codes]
                lambda_lines.append(f"        static const uint32_t port{port}_digits[] = {{")
                lambda_lines.append(f"          {', '.join(data_values)}")
                lambda_lines.append("        };")

            elif protocol_name == 'panasonic':
                # Panasonic: address (constant) + command array
                address = _normalize_hex_literal(digit_codes[0].get('address')) if digit_codes[0] else '0x0'
                command_values = [_normalize_hex_literal(d.get('command')) if d else '0x0' for d in digit_codes]
                lambda_lines.append(f"        static const uint32_t port{port}_commands[] = {{")
                lambda_lines.append(f"          {', '.join(command_values)}")
                lambda_lines.append("        };")
                lambda_lines.append(f"        static const uint32_t port{port}_address = {address};")

            elif protocol_name == 'lg':
                # LG: data array + nbits (constant)
                data_values = [_normalize_hex_literal(d.get('data')) if d else '0x0' for d in digit_codes]
                nbits = digit_codes[0].get('nbits', 32) if digit_codes[0] else 32
                lambda_lines.append(f"        static const uint32_t port{port}_digits[] = {{")
                lambda_lines.append(f"          {', '.join(data_values)}")
                lambda_lines.append("        };")
                lambda_lines.append(f"        static const uint8_t port{port}_nbits = {nbits};")

            elif protocol_name == 'sony':
                # Sony: data array + nbits (constant)
                data_values = [_normalize_hex_literal(d.get('data')) if d else '0x0' for d in digit_codes]
                nbits = digit_codes[0].get('nbits', 12) if digit_codes[0] else 12
                lambda_lines.append(f"        static const uint32_t port{port}_digits[] = {{")
                lambda_lines.append(f"          {', '.join(data_values)}")
                lambda_lines.append("        };")
                lambda_lines.append(f"        static const uint8_t port{port}_nbits = {nbits};")

            lambda_lines.append("")

        # Add validation
        lambda_lines.extend([
            "        // Validation",
            "        if (digit < 0 || digit > 9) {",
            "          ESP_LOGW(\"dispatch\", \"Invalid digit: %d\", digit);",
            "          return;",
            "        }",
            "",
            "        // Port routing with array lookup",
        ])

        # Generate port routing with array lookups
        first_port = True
        for port in assigned_ports:
            profile = assigned_port_map[port]
            protocol = profile.commands.get('power', profile.commands.get('number_0'))
            if not protocol:
                continue

            protocol_name = protocol.protocol
            condition = "if" if first_port else "else if"
            first_port = False

            lambda_lines.append(f"        {condition} (target_port == {port}) {{")
            lambda_lines.append(f"          auto call = id(ir_transmitter_port{port}).transmit();")

            if protocol_name == 'samsung':
                lambda_lines.extend([
                    "          esphome::remote_base::SamsungData data;",
                    f"          data.data = port{port}_digits[digit];",
                    "          esphome::remote_base::SamsungProtocol().encode(call.get_data(), data);",
                ])

            elif protocol_name == 'panasonic':
                lambda_lines.extend([
                    "          esphome::remote_base::PanasonicData data;",
                    f"          data.address = port{port}_address;",
                    f"          data.command = port{port}_commands[digit];",
                    "          esphome::remote_base::PanasonicProtocol().encode(call.get_data(), data);",
                ])

            elif protocol_name == 'lg':
                lambda_lines.extend([
                    "          esphome::remote_base::LGData data;",
                    f"          data.data = port{port}_digits[digit];",
                    f"          data.nbits = port{port}_nbits;",
                    "          esphome::remote_base::LGProtocol().encode(call.get_data(), data);",
                ])

            elif protocol_name == 'sony':
                lambda_lines.extend([
                    "          esphome::remote_base::SonyData data;",
                    f"          data.data = port{port}_digits[digit];",
                    f"          data.nbits = port{port}_nbits;",
                    "          esphome::remote_base::SonyProtocol().encode(call.get_data(), data);",
                ])

            lambda_lines.extend([
                "          call.perform();",
                "        }",
            ])

        # Add final else for invalid port
        lambda_lines.extend([
            "        else {",
            "          ESP_LOGW(\"dispatch\", \"Invalid port: %d\", target_port);",
            "        }",
        ])

        block.extend(lambda_lines)
        return block

    command_dispatches = [
        ("dispatch_power", "power"),
        ("dispatch_power_on", "power_on"),
        ("dispatch_power_off", "power_off"),
        ("dispatch_mute", "mute"),
        ("dispatch_volume_up", "volume_up"),
        ("dispatch_volume_down", "volume_down"),
        ("dispatch_channel_up", "channel_up"),
        ("dispatch_channel_down", "channel_down"),
    ]

    for script_name, command_key in command_dispatches:
        lines.extend(_build_command_dispatch(script_name, command_key))

    # Only include the digit dispatcher if any port actually exposes digit commands
    has_digits = any(
        any(key.startswith('number_') for key in profile.commands)
        for profile in assigned_port_profiles
    )
    if has_digits:
        lines.extend(_build_digit_dispatch())

    if assigned_ports:
        lines.append("- id: dispatch_channel")
        lines.append("  parameters:")
        lines.append("    target_port: int")
        lines.append("    channel_number: string")
        lines.append("  mode: queued")
        lines.append("  then:")
        lines.append("    - script.execute:")
        lines.append("        id: smart_channel")
        lines.append("        target_port: !lambda 'return target_port;'")
        lines.append("        channel: !lambda 'return channel_number.c_str();'")

    # Smart channel scripts
    lines.extend(
        [
            "- id: smart_channel",
            "  parameters:",
            "    target_port: int",
            "    channel: string",
            "  then:",
            "    - lambda: |-",
            "        id(target_port_store) = target_port;",
            "        id(channel_digits) = channel;",
            "        id(digit_index) = 0;",
            "    - script.execute: send_next_channel_digit",
            "",
            "- id: send_next_channel_digit",
            "  mode: restart",
            "  then:",
            "    - lambda: |-",
            "        if (id(digit_index) < id(channel_digits).length()) {",
            "          int digit = id(channel_digits)[id(digit_index)] - '0';",
            "          int port = id(target_port_store);",
            "          ESP_LOGI(\"smart_channel\", \"Sending digit %d (index %d)\", digit, id(digit_index));",
            "          ",
            "          // Send the digit immediately via inline transmission",
            "          static const uint32_t samsung_digits[] = {",
            "            0xE0E08877, 0xE0E020DF, 0xE0E0A05F, 0xE0E0609F, 0xE0E010EF,",
            "            0xE0E0906F, 0xE0E050AF, 0xE0E030CF, 0xE0E0B04F, 0xE0E0708F",
            "          };",
            "          ",
            "          if (digit >= 0 && digit <= 9 && port == 1) {",
            "            auto call = id(ir_transmitter_port1).transmit();",
            "            esphome::remote_base::SamsungData data;",
            "            data.data = samsung_digits[digit];",
            "            esphome::remote_base::SamsungProtocol().encode(call.get_data(), data);",
            "            call.perform();",
            "          }",
            "          ",
            "          id(digit_index)++;",
            "          ",
            "          if (id(digit_index) >= id(channel_digits).length()) {",
            "            ESP_LOGI(\"smart_channel\", \"Channel sequence complete\");",
            "          }",
            "        }",
            "    - if:",
            "        condition:",
            "          lambda: 'return id(digit_index) < id(channel_digits).length();'",
            "        then:",
            "          - delay: 700ms",
            "          - script.execute: send_next_channel_digit",
            "",
        ]
    )

    # Add diagnostic LED control scripts
    lines.extend([
        "",
        "# Diagnostic LED Control Scripts",
        "- id: diagnostic_alert_start",
        "  mode: restart",
        "  then:",
        "    - script.stop: diagnostic_alert_running",
        "    - script.execute: diagnostic_alert_running",
        "",
        "- id: diagnostic_alert_running",
        "  mode: restart",
        "  then:",
        "    - lambda: |-",
        "        ESP_LOGI(\"diagnostic\", \"Starting LED diagnostic alert - 3Hz for 2 minutes\");",
        "    - repeat:",
        "        count: 360  # 3 flashes/sec × 120 seconds = 360 flashes",
        "        then:",
        "          - output.turn_on: diagnostic_led",
        "          - delay: 166ms  # On for 166ms (3Hz = 333ms cycle)",
        "          - output.turn_off: diagnostic_led",
        "          - delay: 167ms  # Off for 167ms",
        "    - script.execute: diagnostic_alert_end",
        "",
        "- id: diagnostic_alert_end",
        "  then:",
        "    - lambda: |-",
        "        ESP_LOGI(\"diagnostic\", \"Diagnostic alert completed - resuming normal LED behavior\");",
        "    - output.turn_on: diagnostic_led",
        "",
    ])

    return lines


def _build_web_handler_lambda(port_profiles: List[PortProfile]) -> List[str]:
    lines: List[str] = []
    lines.append("          auto *web = esphome::web_server_base::global_web_server_base;")
    lines.append("          if (web == nullptr) {")
    lines.append("            ESP_LOGW(\"web_ui\", \"Web server base not initialised; skipping custom UI setup\");")
    lines.append("            return;")
    lines.append("          }")
    lines.append("          auto make_home_html = []() {")
    lines.append("            std::string html;")
    lines.append("            html.reserve(4096);")
    lines.append("            html += \"<!DOCTYPE html><html lang=\\\"en\\\"><head><meta charset=\\\"utf-8\\\"><meta name=\\\"viewport\\\" content=\\\"width=device-width, initial-scale=1\\\"><title>SmartVenue IR Prototype</title>\";")
    lines.append("            html += \"<style>body{font-family:Segoe UI,Roboto,Arial,sans-serif;margin:0;padding:2.5rem;background:#0b172a;color:#f5f8ff;}h1,h2{margin:0;font-weight:600;}h1{font-size:2rem;margin-bottom:0.75rem;}h2{font-size:1.2rem;margin-top:2rem;}ul{margin:0.75rem 0 0 1.5rem;}pre{background:#0c192f;border-radius:10px;padding:1rem;overflow:auto;}a.button{display:inline-block;margin-top:1rem;padding:0.6rem 1rem;border-radius:30px;background:#2563ff;color:#fff;text-decoration:none;font-weight:600;}</style></head><body>\";")
    lines.append("            html += \"<h1>SmartVenue Dynamic IR</h1>\";")
    lines.append("            html += \"<p>Latest capability payload published from the IR template builder.</p>\";")
    lines.append("            html += \"<h2>Port Assignments</h2><ul>\";")

    for profile in port_profiles:
        description = _escape_cpp_string(profile.description)
        functions = [PORT_FUNCTION_DISPLAY[key] for key in CANONICAL_COMMANDS if key in profile.commands]
        function_text = ', '.join(functions) if functions else 'No supported commands'
        function_text = _escape_cpp_string(function_text)
        lines.append(
            f"            html += \"<li>Port {profile.port_number}: {description} — {function_text}</li>\";"
        )

    lines.append("            html += \"</ul>\";")
    lines.append("            html += \"<h2>Capability Payload</h2><pre>\";")
    lines.append("            html += id(ir_capabilities_payload).state.c_str();")
    lines.append("            html += \"</pre>\";")
    lines.append("            html += \"<a class=\\\"button\\\" href=\\\"/report\\\">Publish Capabilities</a>\";")
    lines.append("            html += \"</body></html>\";")
    lines.append("            return html;")
    lines.append("          };")
    lines.append("          auto *root_handler = new AsyncCallbackWebHandler();")
    lines.append("          root_handler->setUri(\"/\");")
    lines.append("          root_handler->onRequest([make_home_html](AsyncWebServerRequest *request) {")
    lines.append("            std::string html = make_home_html();")
    lines.append("            request->send(200, \"text/html\", html.c_str());")
    lines.append("          });")
    lines.append("          web->add_handler(root_handler);")
    lines.append("          auto *report_handler = new AsyncCallbackWebHandler();")
    lines.append("          report_handler->setUri(\"/report\");")
    lines.append("          report_handler->onRequest([](AsyncWebServerRequest *request) {")
    lines.append("            id(publish_capabilities).execute();")
    lines.append("            request->send(200, \"text/plain\", \"Capabilities publish queued\");")
    lines.append("          });")
    lines.append("          web->add_handler(report_handler);")
    return lines


def _build_button_section(port_profiles: List[PortProfile]) -> str:
    assigned = [profile.port_number for profile in port_profiles if profile.library is not None]

    lines: List[str] = ["button:"]

    # Always add the ID/Diagnostic button first
    lines.extend([
        "  - platform: template",
        "    name: \"Identify Device\"",
        "    id: identify_device_button",
        "    icon: \"mdi:led-on\"",
        "    entity_category: diagnostic",
        "    on_press:",
        "      - script.execute: diagnostic_alert_start",
        "",
    ])

    # Add port-specific buttons if there are assigned ports
    for port in sorted(assigned):
        prefix = f"Port {port}"
        lines.extend(
            [
                "  - platform: template",
                f"    name: \"{prefix} Power\"",
                "    on_press:",
                "      - script.execute:",
                "          id: dispatch_power",
                f"          target_port: {port}",
                "",
                "  - platform: template",
                f"    name: \"{prefix} Mute\"",
                "    on_press:",
                "      - script.execute:",
                "          id: dispatch_mute",
                f"          target_port: {port}",
                "",
            ]
        )

    return "\n".join(lines).rstrip()


def _build_globals_section() -> str:
    lines = [
        "globals:",
        "  - id: channel_digits",
        "    type: std::string",
        "    initial_value: '\"\"'",
        "    restore_value: false",
        "  - id: digit_index",
        "    type: int",
        "    initial_value: '0'",
        "    restore_value: false",
        "  - id: target_port_store",
        "    type: int",
        "    initial_value: '1'",
        "    restore_value: false",
        "  - id: current_digit",
        "    type: int",
        "    initial_value: '0'",
        "    restore_value: false",
    ]
    return "\n".join(lines)


def _render_dynamic_yaml(
    template: ESPTemplate,
    port_profiles: List[PortProfile],
    include_comments: bool,
    port_block: str,
    device_block: str,
    hostname: Optional[str] = None,
) -> str:
    """
    Render dynamic YAML using the stored template as a base and replacing placeholders
    """
    # Get the base template YAML
    base_yaml = template.template_yaml

    # Use the stored template as base and replace placeholders
    rendered_yaml = base_yaml


    # Build dynamic content for placeholders
    shared_script_lines = _build_shared_scripts(port_profiles)
    script_section = "\n".join(_indent(shared_script_lines, 2)).rstrip()
    custom_script_block = f"\n{script_section}\n" if script_section else ""

    # Build static capability payload lines for the lambda block
    capability_lines = _build_capabilities_payload_lines(port_profiles, template=template)

    # Replace placeholders in the base template
    rendered_yaml = _inject_capabilities_payload(rendered_yaml, capability_lines)
    rendered_yaml = rendered_yaml.replace("{{CAPABILITY_BRAND_LINES}}", "")
    rendered_yaml = rendered_yaml.replace("{{CAPABILITY_COMMAND_LINES}}", "")
    rendered_yaml = rendered_yaml.replace("{{CUSTOM_SCRIPT_BLOCK}}", custom_script_block)
    rendered_yaml = rendered_yaml.replace("{{PORT_BLOCK}}", port_block if include_comments else "")
    rendered_yaml = rendered_yaml.replace("{{DEVICE_BLOCK}}", device_block if include_comments else "")
    button_section = _build_button_section(port_profiles)
    rendered_yaml = rendered_yaml.replace("{{BUTTON_SECTION}}", button_section)

    # Replace legacy tv_channel service (dispatch_channel) with smart_channel version
    legacy_tv_channel_block = (
        "    - service: tv_channel\n"
        "      variables:\n"
        "        port: int\n"
        "        channel: int\n"
        "      then:\n"
        "        - script.execute:\n"
        "            id: dispatch_channel\n"
        "            target_port: !lambda 'return port;'\n"
        "            channel_number: !lambda 'return channel;'\n"
    )
    if legacy_tv_channel_block in rendered_yaml:
        rendered_yaml = rendered_yaml.replace(legacy_tv_channel_block, "")

    # Build additional services for API section, avoiding duplicates
    service_blocks: Dict[str, List[str]] = {
        "tv_power": [
            "    - service: tv_power",
            "      variables:",
            "        port: int",
            "      then:",
            "        - script.execute:",
            "            id: dispatch_power",
            "            target_port: !lambda 'return port;'",
        ],
        "tv_power_on": [
            "    - service: tv_power_on",
            "      variables:",
            "        port: int",
            "      then:",
            "        - script.execute:",
            "            id: dispatch_power_on",
            "            target_port: !lambda 'return port;'",
        ],
        "tv_power_off": [
            "    - service: tv_power_off",
            "      variables:",
            "        port: int",
            "      then:",
            "        - script.execute:",
            "            id: dispatch_power_off",
            "            target_port: !lambda 'return port;'",
        ],
        "tv_mute": [
            "    - service: tv_mute",
            "      variables:",
            "        port: int",
            "      then:",
            "        - script.execute:",
            "            id: dispatch_mute",
            "            target_port: !lambda 'return port;'",
        ],
        "tv_volume_up": [
            "    - service: tv_volume_up",
            "      variables:",
            "        port: int",
            "      then:",
            "        - script.execute:",
            "            id: dispatch_volume_up",
            "            target_port: !lambda 'return port;'",
        ],
        "tv_volume_down": [
            "    - service: tv_volume_down",
            "      variables:",
            "        port: int",
            "      then:",
            "        - script.execute:",
            "            id: dispatch_volume_down",
            "            target_port: !lambda 'return port;'",
        ],
        "tv_channel_up": [
            "    - service: tv_channel_up",
            "      variables:",
            "        port: int",
            "      then:",
            "        - script.execute:",
            "            id: dispatch_channel_up",
            "            target_port: !lambda 'return port;'",
        ],
        "tv_channel_down": [
            "    - service: tv_channel_down",
            "      variables:",
            "        port: int",
            "      then:",
            "        - script.execute:",
            "            id: dispatch_channel_down",
            "            target_port: !lambda 'return port;'",
        ],
        "tv_number": [
            "    - service: tv_number",
            "      variables:",
            "        port: int",
            "        digit: int",
            "      then:",
            "        - script.execute:",
            "            id: dispatch_digit",
            "            target_port: !lambda 'return port;'",
            "            digit: !lambda 'return digit;'",
        ],
        "tv_channel": [
            "    - service: tv_channel",
            "      variables:",
            "        port: int",
            "        channel: string",
            "      then:",
            "        - script.execute:",
            "            id: smart_channel",
            "            target_port: !lambda 'return port;'",
            "            channel: !lambda 'return channel.c_str();'",
        ],
        "diagnostic_signal": [
            "    - service: diagnostic_signal",
            "      variables:",
            "        port: int",
            "        code: int",
            "      then:",
            "        - lambda: |-",
            "            ESP_LOGI(\"diagnostic\", \"Received diagnostic signal - Port: %d, Code: %d\", port, code);",
            "            if (port == 0 && code == 1) {",
            "              id(diagnostic_alert_start).execute();",
            "            }",
        ],
    }

    if "api:" in rendered_yaml and "services:" in rendered_yaml:
        existing_services = {
            match.group(1)
            for match in re.finditer(r"^\s*-\s+service:\s+([a-zA-Z0-9_]+)", rendered_yaml, flags=re.MULTILINE)
        }

        services_to_add: List[str] = []
        for name, block_lines in service_blocks.items():
            if name not in existing_services:
                services_to_add.extend(block_lines)

        if services_to_add:
            services_text = "\n".join(services_to_add)
            rendered_yaml = rendered_yaml.replace(
                "        - script.execute: publish_capabilities",
                f"        - script.execute: publish_capabilities\n{services_text}"
            )

    # Update project name to dynamic_ir
    rendered_yaml = rendered_yaml.replace("smartvenue.universal_ir", "smartvenue.dynamic_ir")

    # Remove ArduinoJson.h include if present (causes compilation issues)
    rendered_yaml = rendered_yaml.replace("\n  includes:\n    - ArduinoJson.h", "")

    # No output section needed - using 5 separate IR transmitters
    output_section = ""

    # Add globals section before text_sensor section
    globals_section = _build_globals_section()
    if "text_sensor:" in rendered_yaml:
        rendered_yaml = rendered_yaml.replace(
            "text_sensor:",
            f"{output_section}{globals_section}\n\ntext_sensor:"
        )

    # Fix OTA section formatting
    rendered_yaml = rendered_yaml.replace(
        " ota:\n  - platform: esphome",
        "ota:\n  - platform: esphome"
    )

    return rendered_yaml


class TemplateLibrary(BaseModel):
    id: int
    name: str
    device_category: str
    brand: str
    model: Optional[str]
    source_path: str
    esp_native: bool


class TemplateBrand(BaseModel):
    name: str
    libraries: List[TemplateLibrary]


class TemplateCategory(BaseModel):
    name: str
    brands: List[TemplateBrand]


class PortAssignmentInput(BaseModel):
    port_number: int = Field(ge=1, le=5)
    library_id: Optional[int] = None


class CommandSelection(BaseModel):
    """User selection of specific commands for a port"""
    command_name: str = Field(..., description="Standardized command name (e.g., 'power', 'volume_up')")
    library_id: int = Field(..., description="Library ID containing the command")
    db_command_name: str = Field(..., description="Actual command name in database (e.g., 'Power', 'Vol_up')")


class PortCommandAssignment(BaseModel):
    """Port assignment with specific command selections"""
    port_number: int = Field(ge=1, le=5)
    commands: List[CommandSelection] = Field(default_factory=list, description="Selected commands for this port")


class CommandPreviewRequest(BaseModel):
    """Request for generating YAML with specific command selections"""
    template_id: int = Field(default=1, description="ESP template ID")
    assignments: List[PortCommandAssignment] = Field(..., description="Port assignments with command selections")


def _collect_port_profiles(
    assignments: List[PortAssignmentInput],
    libraries: Dict[int, IRLibrary],
    commands_by_library: Dict[int, List[IRCommand]]
) -> List[PortProfile]:
    profiles: List[PortProfile] = []

    for assignment in assignments:
        library = libraries.get(assignment.library_id) if assignment.library_id else None
        transmissions: Dict[str, TransmissionSpec] = {}

        if library:
            transmissions = _build_command_transmissions(
                library,
                commands_by_library.get(library.id, [])
            )

        profiles.append(
            PortProfile(
                port_number=assignment.port_number,
                library=library,
                commands=transmissions
            )
        )

    return profiles


class TemplatePreviewRequest(BaseModel):
    template_id: int
    assignments: List[PortAssignmentInput]
    include_comments: bool = True


class SelectedDevicePreview(BaseModel):
    library_id: int
    display_name: str
    device_category: str
    brand: str
    model: Optional[str]
    source_path: str


class TemplatePreviewResponse(BaseModel):
    yaml: str
    char_count: int
    selected_devices: List[SelectedDevicePreview]


class ESPTemplateUpdateRequest(BaseModel):
    template_yaml: str
    test_compile: bool = False
    version_increment: str = "patch"  # "major", "minor", "patch"


class FirmwareCompileRequest(BaseModel):
    yaml: str


class FirmwareCompileResponse(BaseModel):
    success: bool
    log: str
    binary_path: Optional[str]
    binary_filename: Optional[str]


class FirmwareOTARequest(BaseModel):
    binary_path: str
    hostnames: List[str] = Field(..., min_length=1)
    ota_port: Optional[int] = None
    reboot_wait_seconds: int = Field(default=20, ge=5, le=300)


class SaveYamlRequest(BaseModel):
    yaml: str
    filename: Optional[str] = None


class SaveYamlResponse(BaseModel):
    success: bool
    filename: str
    path: str


class ESPTemplateResponse(BaseModel):
    id: int
    name: str
    board: str
    description: Optional[str]
    template_yaml: str
    version: str
    revision: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


def _generate_remote_transmitters(assignments: List[PortAssignmentInput]) -> str:
    """Generate remote_transmitter section dynamically based on actual port assignments"""
    if not assignments:
        return "# No ports assigned"

    # D1 Mini GPIO pin mapping for IR transmitters
    port_gpio_map = {
        1: ("GPIO13", "D7"),
        2: ("GPIO15", "D8"),
        3: ("GPIO12", "D6"),
        4: ("GPIO16", "D0"),
        5: ("GPIO5", "D1")
    }

    lines = ["remote_transmitter:"]

    # Only generate transmitters for ports that have assignments
    assigned_ports = set()
    for assignment in assignments:
        if assignment.library_id:  # Only include ports with actual library assignments
            assigned_ports.add(assignment.port_number)

    # Sort ports for consistent output
    for port_number in sorted(assigned_ports):
        gpio_pin, d_pin = port_gpio_map.get(port_number, ("GPIO14", "D5"))  # Default fallback
        lines.extend([
            f"  - id: ir_transmitter_port{port_number}",
            f"    pin: {gpio_pin}  # {d_pin}",
            "    carrier_duty_percent: 50%"
        ])

    return "\n".join(lines)


def _generate_capability_brands(assignments: List[PortAssignmentInput], db: Session) -> str:
    """Generate C++ code to populate brands array based on actual port assignments"""
    if not assignments:
        return "          // No brands - no ports assigned"

    # Get unique library IDs
    library_ids = set()
    for assignment in assignments:
        if assignment.library_id:
            library_ids.add(assignment.library_id)

    if not library_ids:
        return "          // No brands - no active ports"

    # Get library details
    libraries = db.query(IRLibrary).filter(IRLibrary.id.in_(library_ids)).all()
    brands = set()
    for lib in libraries:
        if lib.brand:
            brands.add(lib.brand)

    # Generate C++ code
    lines = []
    for brand in sorted(brands):
        lines.append(f'          brands.add("{brand}");')

    return "\n".join(lines)


def _generate_capability_commands(assignments: List[PortAssignmentInput], db: Session) -> str:
    """Generate C++ code to populate commands array based on actual port assignments"""
    if not assignments:
        return "          // No commands - no ports assigned"

    # Get unique library IDs
    library_ids = set()
    for assignment in assignments:
        if assignment.library_id:
            library_ids.add(assignment.library_id)

    if not library_ids:
        return "          // No commands - no active ports"

    # Get all commands from assigned libraries
    commands = db.query(IRCommand).filter(IRCommand.library_id.in_(library_ids)).all()
    command_names = set()
    for cmd in commands:
        if cmd.name:
            command_names.add(cmd.name)

    # Generate C++ code
    lines = []
    for cmd_name in sorted(command_names):
        lines.append(f'          commands.add("{cmd_name}");')

    return "\n".join(lines)


def _generate_readable_sensors(assignments: List[PortAssignmentInput], db: Session) -> str:
    """Generate text sensors for human-readable display on ESPHome web UI"""
    if not assignments:
        return '''
  - platform: template
    id: port_assignments_display
    name: "Port Assignments"
    icon: "mdi:port"
    lambda: |-
      return std::string("No ports assigned");

  - platform: template
    id: device_info_display
    name: "Connected Devices"
    icon: "mdi:devices"
    lambda: |-
      return std::string("No devices configured");'''

    # Get library details
    library_ids = [a.library_id for a in assignments if a.library_id]
    if not library_ids:
        return _generate_readable_sensors([], db)

    libraries = db.query(IRLibrary).filter(IRLibrary.id.in_(library_ids)).all()
    lib_map = {lib.id: lib for lib in libraries}

    # Get commands for each library
    commands = db.query(IRCommand).filter(IRCommand.library_id.in_(library_ids)).all()
    cmd_map = {}
    for cmd in commands:
        if cmd.library_id not in cmd_map:
            cmd_map[cmd.library_id] = []
        cmd_map[cmd.library_id].append(cmd.name)

    # Build port assignments display
    port_lines = []
    device_lines = []

    for assignment in sorted(assignments, key=lambda a: a.port_number):
        if assignment.library_id and assignment.library_id in lib_map:
            lib = lib_map[assignment.library_id]
            port_lines.append(f"Port {assignment.port_number}: {lib.brand} {lib.name}")

            # Build device info
            cmd_count = len(cmd_map.get(assignment.library_id, []))
            device_lines.append(f"{lib.brand} {lib.name} ({cmd_count} commands)")

    port_display = "; ".join(port_lines) if port_lines else "No active ports"
    device_display = "; ".join(device_lines) if device_lines else "No devices"

    return f'''
  - platform: template
    id: port_assignments_display
    name: "Port Assignments"
    icon: "mdi:port"
    lambda: |-
      return std::string("{port_display}");

  - platform: template
    id: device_info_display
    name: "Connected Devices"
    icon: "mdi:devices"
    lambda: |-
      return std::string("{device_display}");'''


def _generate_dynamic_channel_dispatch(assignments: List[PortAssignmentInput]) -> str:
    """Generate dynamic channel dispatch logic for all assigned ports using correct script names"""
    if not assignments:
        return "            // No channel dispatch - no ports assigned"

    # Only generate dispatch for ports that have assignments
    assigned_ports = set()
    for assignment in assignments:
        if assignment.library_id:
            assigned_ports.add(assignment.port_number)

    if not assigned_ports:
        return "            // No channel dispatch - no active ports"

    # Generate dynamic if/else chain for all assigned ports
    lines = []

    for i, port_number in enumerate(sorted(assigned_ports)):
        if i == 0:
            lines.append(f"            if (port == {port_number}) {{")
        else:
            lines.append(f"            }} else if (port == {port_number}) {{")

        lines.append("              switch(digit) {")
        # Use script naming that matches generated digit scripts
        for digit in range(10):
            lines.append(f"                case {digit}: id(send_port{port_number}_digit_{digit}).execute(); break;")
        lines.append("              }")

    # Close the final if block
    if assigned_ports:
        lines.extend([
            "            } else {",
            "              ESP_LOGW(\"IR\", \"Port %d not configured for digit commands\", port);",
            "            }"
        ])

    return "\n".join(lines)


def _sse_event(payload: Dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _keepalive_event() -> str:
    return "data: {\"type\": \"keepalive\"}\n\n"


async def _fetch_device_metadata(hostname: str, ip_address: str, api_key: Optional[str]) -> Optional[Dict[str, Any]]:
    client = esphome_manager.get_client(hostname, ip_address, api_key=api_key)
    try:
        info = await client.get_device_info()
        if info:
            info = dict(info)
            info.setdefault("ip_address", ip_address)
        await client.disconnect()
        return info
    except Exception:
        return None


async def _wait_for_device_metadata(
    hostname: str,
    ip_address: str,
    api_key: Optional[str],
    *,
    retries: int,
    delay: float,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    delay = max(1.0, delay)
    for attempt in range(max(1, retries)):
        info = await _fetch_device_metadata(hostname, ip_address, api_key)
        capabilities: Optional[Dict[str, Any]] = None
        if info:
            try:
                capabilities = await esphome_manager.fetch_capabilities(hostname, ip_address, api_key)
            except Exception:
                capabilities = None
            return info, capabilities
        await asyncio.sleep(delay)
    return None, None


@router.get("", response_model=List[ESPTemplateSummary])
async def list_templates(db: Session = Depends(get_db)):
    templates = db.query(ESPTemplate).order_by(ESPTemplate.name).all()
    return templates


@router.get("/base", response_model=ESPTemplateResponse)
async def get_base_template(db: Session = Depends(get_db)):
    # Get the latest version of the first template (by highest revision)
    template = db.query(ESPTemplate).order_by(ESPTemplate.id.asc(), ESPTemplate.revision.desc()).first()
    if not template:
        raise HTTPException(status_code=404, detail="No ESP templates available")
    return template


@router.get("/{template_id:int}", response_model=ESPTemplateResponse)
async def get_template(template_id: int, db: Session = Depends(get_db)):
    template = db.query(ESPTemplate).filter(ESPTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.put("/{template_id:int}", response_model=ESPTemplateResponse)
async def update_template(
    template_id: int,
    payload: ESPTemplateUpdateRequest,
    db: Session = Depends(get_db),
):
    template = db.query(ESPTemplate).filter(ESPTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if not payload.template_yaml.strip():
        raise HTTPException(status_code=400, detail="Template YAML cannot be empty")

    # Test compilation if requested
    if payload.test_compile:
        builder = get_firmware_builder()
        result = await builder.compile_yaml(payload.template_yaml)
        if not result.success:
            raise HTTPException(status_code=400, detail=f"Template compilation failed: {result.log}")

    # Increment version
    new_version = increment_version(template.version, payload.version_increment)

    # Update YAML content with new version and date
    updated_yaml = update_yaml_version_and_date(payload.template_yaml, new_version)

    # Update template
    template.template_yaml = updated_yaml
    template.version = new_version
    template.revision += 1

    db.add(template)
    db.commit()
    db.refresh(template)

    return template


@router.get("/device-hierarchy", response_model=List[TemplateCategory])
async def get_device_hierarchy(db: Session = Depends(get_db)):
    libraries = (
        db.query(IRLibrary)
        .filter(IRLibrary.hidden == False)  # noqa: E712
        .order_by(IRLibrary.device_category, IRLibrary.brand, IRLibrary.name)
        .all()
    )

    hierarchy: Dict[str, Dict[str, List[TemplateLibrary]]] = {}

    for lib in libraries:
        category = (lib.device_category or "Uncategorized").strip() or "Uncategorized"
        brand = (lib.brand or "Unknown").strip() or "Unknown"
        name = (lib.name or lib.model or brand or "Unnamed Library").strip() or "Unnamed Library"
        source_path = (lib.source_path or "").strip()

        hierarchy.setdefault(category, {}).setdefault(brand, []).append(
            TemplateLibrary(
                id=lib.id,
                name=name,
                device_category=category,
                brand=brand,
                model=lib.model,
                source_path=source_path,
                esp_native=bool(getattr(lib, "esp_native", 0)),
            )
        )

    response: List[TemplateCategory] = []
    for category_name, brands in hierarchy.items():
        brand_entries = [TemplateBrand(name=brand_name, libraries=libs) for brand_name, libs in brands.items()]
        response.append(TemplateCategory(name=category_name, brands=brand_entries))

    response.sort(key=lambda c: c.name.lower())
    for category in response:
        category.brands.sort(key=lambda b: b.name.lower())
        for brand in category.brands:
            brand.libraries.sort(key=lambda l: l.name.lower())

    return response


@router.post("/compile", response_model=FirmwareCompileResponse)
async def compile_firmware(payload: FirmwareCompileRequest):
    builder = get_firmware_builder()
    result = await builder.compile_yaml(payload.yaml)
    return FirmwareCompileResponse(
        success=result.success,
        log=result.log,
        binary_path=result.binary_path,
        binary_filename=result.binary_filename,
    )


@router.post("/compile-stream")
async def compile_firmware_stream(payload: FirmwareCompileRequest):
    """Stream compilation output in real-time via Server-Sent Events."""
    import queue
    import asyncio
    import threading

    async def event_stream():
        builder = get_firmware_builder()

        # Send initial status
        yield f"data: {json.dumps({'type': 'status', 'message': 'Starting compilation...'})}\n\n"

        # Create a queue for streaming output
        output_queue = queue.Queue()
        compilation_complete = threading.Event()
        result_holder = {"result": None}

        def stream_callback(line: str):
            output_queue.put(('output', line))

        # Run compilation in background thread
        def run_compilation():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    builder.compile_yaml_streaming(payload.yaml, stream_callback)
                )
                result_holder["result"] = result
                output_queue.put(('complete', result))
            except Exception as e:
                output_queue.put(('error', str(e)))
            finally:
                compilation_complete.set()

        compilation_thread = threading.Thread(target=run_compilation)
        compilation_thread.start()

        # Stream output as it becomes available
        while not compilation_complete.is_set() or not output_queue.empty():
            try:
                # Non-blocking get with timeout
                event_type, data = output_queue.get(timeout=0.1)

                if event_type == 'output':
                    yield f"data: {json.dumps({'type': 'output', 'message': data})}\n\n"
                elif event_type == 'complete':
                    final_data = {
                        'type': 'complete',
                        'success': data.success,
                        'binary_filename': data.binary_filename,
                        'binary_path': data.binary_path
                    }
                    yield f"data: {json.dumps(final_data)}\n\n"
                elif event_type == 'error':
                    error_data = {
                        'type': 'error',
                        'message': f"Compilation error: {data}"
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"

            except queue.Empty:
                # Send keepalive
                yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
                continue

        compilation_thread.join()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.post("/ota-stream")
async def ota_firmware_stream(payload: FirmwareOTARequest):
    """Stream OTA uploads to one or more devices via Server-Sent Events."""

    builder = get_firmware_builder()
    binary_path = Path(payload.binary_path).resolve()
    builds_root = builder.builds_dir.resolve()

    if not binary_path.exists():
        raise HTTPException(status_code=404, detail="Binary file not found")

    try:
        binary_path.relative_to(builds_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Binary path is outside the build directory") from exc

    ota_port = payload.ota_port or 3232

    async def event_stream():
        session = SessionLocal()
        try:
            devices = {
                device.hostname: device
                for device in session.query(Device).filter(Device.hostname.in_(payload.hostnames)).all()
            }

            for hostname in payload.hostnames:
                yield _sse_event(
                    {
                        "type": "device_start",
                        "hostname": hostname,
                        "binary": binary_path.name,
                    }
                )

                db_device = devices.get(hostname)
                if not db_device:
                    yield _sse_event(
                        {
                            "type": "device_complete",
                            "hostname": hostname,
                            "success": False,
                            "error": "Device not registered in database",
                        }
                    )
                    continue

                ota_password = settings_service.get_setting("ota_password", "") or ""

                api_key = None
                managed = session.query(ManagedDevice).filter(ManagedDevice.hostname == hostname).first()
                if managed and managed.api_key:
                    api_key = managed.api_key
                if not api_key:
                    api_key = settings_service.get_setting("esphome_api_key")

                device_ip = db_device.ip_address or hostname

                pre_info = await _fetch_device_metadata(hostname, device_ip, api_key)
                if pre_info:
                    yield _sse_event(
                        {
                            "type": "device_info",
                            "stage": "before",
                            "hostname": hostname,
                            "firmware": pre_info.get("firmware_version"),
                            "project": pre_info.get("project_version"),
                            "ip": pre_info.get("ip_address"),
                        }
                    )

                output_queue: "queue.Queue[tuple[str, object]]" = queue.Queue()
                completion = threading.Event()
                resolved_ip_holder: Dict[str, Optional[str]] = {"value": None}
                upload_success = {"value": False}

                def emitter(event_type: str, payload: object) -> None:
                    output_queue.put((event_type, payload))

                async def async_worker() -> None:
                    try:
                        # Try the specified port first
                        success, resolved_ip = run_ota_with_callback(
                            host=device_ip,
                            port=ota_port,
                            password=ota_password or "",
                            binary_path=binary_path,
                            emitter=emitter,
                        )

                        # If that fails and we're using default port 3232, try fallback sequence
                        if not success and ota_port == 3232:
                            # Try ESP8266 legacy OTA port first
                            output_queue.put(("log", "Port 3232 failed, trying ESP8266 OTA on port 8266..."))
                            success, resolved_ip = run_ota_with_callback(
                                host=device_ip,
                                port=8266,
                                password=ota_password or "",
                                binary_path=binary_path,
                                emitter=emitter,
                            )

                            # If that also fails, try HTTP OTA on port 80
                            if not success:
                                output_queue.put(("log", "Port 8266 failed, trying HTTP OTA on port 80..."))
                                success, resolved_ip = await run_http_ota_with_callback(
                                    host=device_ip,
                                    port=80,
                                    password=ota_password or "",
                                    binary_path=binary_path,
                                    emitter=emitter,
                                )

                        upload_success["value"] = success
                        resolved_ip_holder["value"] = resolved_ip
                    except Exception as exc:  # pragma: no cover - network/hardware errors
                        output_queue.put(("log", f"OTA failed: {exc}"))
                        upload_success["value"] = False
                    finally:
                        output_queue.put(("complete", upload_success["value"]))
                        completion.set()

                def worker() -> None:
                    asyncio.run(async_worker())

                thread = threading.Thread(target=worker, daemon=True)
                thread.start()

                while not completion.is_set() or not output_queue.empty():
                    try:
                        event_type, data = output_queue.get(timeout=0.1)
                    except queue.Empty:
                        yield _keepalive_event()
                        continue

                    if event_type == "log":
                        yield _sse_event(
                            {
                                "type": "log",
                                "hostname": hostname,
                                "message": data,
                            }
                        )
                    elif event_type == "progress":
                        yield _sse_event(
                            {
                                "type": "progress",
                                "hostname": hostname,
                                "value": data,
                            }
                        )
                    elif event_type == "complete":
                        upload_success["value"] = bool(data)

                thread.join()

                if not upload_success["value"]:
                    yield _sse_event(
                        {
                            "type": "device_complete",
                            "hostname": hostname,
                            "success": False,
                            "error": "OTA upload failed",
                        }
                    )
                    continue

                # Wait for the device to reboot and report new info
                effective_ip = resolved_ip_holder["value"] or device_ip

                new_info, capabilities = await _wait_for_device_metadata(
                    hostname,
                    effective_ip,
                    api_key,
                    retries=8,
                    delay=payload.reboot_wait_seconds / 8,
                )

                managed_entry = session.query(ManagedDevice).filter(ManagedDevice.hostname == hostname).first()

                if new_info:
                    new_ip = new_info.get("ip_address") or effective_ip
                    db_device.firmware_version = new_info.get("firmware_version")
                    db_device.ip_address = new_ip
                    db_device.is_online = True
                    db_device.last_seen = datetime.now()

                    if managed_entry:
                        managed_entry.firmware_version = new_info.get("firmware_version")
                        managed_entry.current_ip_address = new_ip
                        managed_entry.is_online = True
                        managed_entry.last_seen = datetime.now()

                canonical_mac = None
                if capabilities:
                    db_device.capabilities = capabilities
                    canonical_mac = _normalize_mac_address(_extract_capabilities_mac(capabilities))
                    if canonical_mac:
                        db_device.mac_address = canonical_mac

                if managed_entry:
                    if canonical_mac and canonical_mac != managed_entry.mac_address:
                        managed_entry.mac_address = canonical_mac
                    session.flush()
                    session.refresh(managed_entry)
                    _sync_ports_from_capabilities(managed_entry, capabilities)
                    session.add(managed_entry)
                session.add(db_device)
                session.commit()

                yield _sse_event(
                    {
                        "type": "device_complete",
                        "hostname": hostname,
                        "success": True,
                        "previous_firmware": pre_info.get("firmware_version") if pre_info else None,
                        "new_firmware": new_info.get("firmware_version") if new_info else None,
                        "resolved_ip": effective_ip,
                        "capabilities": capabilities,
                        "metadata_available": new_info is not None,
                    }
                )
        finally:
            session.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "X-Accel-Buffering": "no",
        },
    )
@router.get("/download/{filename}")
async def download_binary(filename: str):
    """Download a compiled binary file."""
    builder = get_firmware_builder()
    binary_path = builder.builds_dir / filename

    if not binary_path.exists():
        raise HTTPException(status_code=404, detail="Binary file not found")

    return FileResponse(
        path=str(binary_path),
        media_type="application/octet-stream",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def _build_port_block(assignments: List[PortAssignmentInput], libraries: Dict[int, IRLibrary]) -> str:
    lines: List[str] = []
    ports_by_number = {assignment.port_number: assignment for assignment in assignments}

    for port_number in range(1, 6):
        assignment = ports_by_number.get(port_number)
        lib = libraries.get(assignment.library_id) if assignment and assignment.library_id else None

        if lib:
            display_name = lib.name or lib.model or lib.brand
            details = f"{display_name} ({lib.brand}{f' • {lib.model}' if lib.model else ''})"
        elif assignment and assignment.library_id and assignment.library_id not in libraries:
            details = f"Unknown library #{assignment.library_id}"
        else:
            details = "Unassigned"

        lines.append(f"#   Port {port_number}: {details}")

    if not lines:
        return "#   No port assignments"

    return "\n".join(lines)


def _build_device_block(selected_libraries: List[IRLibrary]) -> str:
    if not selected_libraries:
        return "#   No devices selected"

    lines: List[str] = []
    for lib in selected_libraries:
        display_name = lib.name or lib.model or lib.brand
        metadata = f"{lib.device_category} → {lib.brand}{f' → {lib.model}' if lib.model else ''}"
        lines.append(f"#   • {display_name} [{metadata}] ({lib.source_path})")

    return "\n".join(lines)




def _remove_comments(yaml_text: str) -> str:
    filtered = [line for line in yaml_text.splitlines() if not line.lstrip().startswith("#")]
    cleaned: List[str] = []
    for line in filtered:
        if cleaned and not line.strip() and not cleaned[-1].strip():
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip("\n") + "\n"


@router.post("/preview", response_model=TemplatePreviewResponse)
async def generate_preview(payload: TemplatePreviewRequest, db: Session = Depends(get_db)):
    template = db.query(ESPTemplate).filter(ESPTemplate.id == payload.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Normalize assignments (ensure exactly 5 ports)
    assignments_map: Dict[int, PortAssignmentInput] = {a.port_number: a for a in payload.assignments}
    normalized_assignments = [assignments_map.get(i, PortAssignmentInput(port_number=i)) for i in range(1, 6)]

    selected_library_ids = [a.library_id for a in normalized_assignments if a.library_id]
    unique_library_ids = sorted(set(selected_library_ids))

    # Get libraries for preview info
    libraries: Dict[int, IRLibrary] = {}
    if unique_library_ids:
        rows = db.query(IRLibrary).filter(IRLibrary.id.in_(unique_library_ids)).all()
        libraries = {row.id: row for row in rows}

    selected_libraries = [libraries[lid] for lid in unique_library_ids if lid in libraries]

    # Generate YAML using the new command selection approach
    # Create command selections for each port with essential TV commands
    essential_commands = ['power', 'mute', 'volume_up', 'volume_down', 'channel_up', 'channel_down', 'number_0', 'number_1', 'number_2', 'number_3', 'number_4', 'number_5', 'number_6', 'number_7', 'number_8', 'number_9']

    commands_by_library: Dict[int, List[IRCommand]] = {}
    for assignment in normalized_assignments:
        if assignment.library_id:
            commands_by_library[assignment.library_id] = db.query(IRCommand).filter(
                IRCommand.library_id == assignment.library_id
            ).all()

    port_profiles = _collect_port_profiles(normalized_assignments, libraries, commands_by_library)
    port_block = _build_port_block(normalized_assignments, libraries)
    device_block = _build_device_block(selected_libraries)

    rendered_yaml = _render_dynamic_yaml(
        template,
        port_profiles,
        payload.include_comments,
        port_block,
        device_block,
        hostname=payload.hostname if hasattr(payload, 'hostname') else None,
    )

    # Fill dynamic placeholders
    dynamic_transmitters = _generate_remote_transmitters(normalized_assignments)
    rendered_yaml = rendered_yaml.replace("{{TRANSMITTER_BLOCK}}", dynamic_transmitters)

    dynamic_dispatch = _generate_dynamic_channel_dispatch(normalized_assignments)
    rendered_yaml = rendered_yaml.replace("{{CHANNEL_DISPATCH_BLOCK}}", dynamic_dispatch)

    readable_sensors = _generate_readable_sensors(normalized_assignments, db)
    rendered_yaml = rendered_yaml.replace("{{READABLE_SENSORS}}", readable_sensors)

    rendered_yaml = _apply_database_settings(rendered_yaml, db)

    preview_devices = [
        SelectedDevicePreview(
            library_id=lib.id,
            display_name=lib.name or lib.model or lib.brand,
            device_category=lib.device_category,
            brand=lib.brand,
            model=lib.model,
            source_path=lib.source_path,
        )
        for lib in selected_libraries
    ]

    return TemplatePreviewResponse(
        yaml=rendered_yaml,
        char_count=len(rendered_yaml),
        selected_devices=preview_devices,
    )


@router.post("/save-yaml", response_model=SaveYamlResponse)
async def save_yaml_to_file(payload: SaveYamlRequest):
    """Save YAML content to a file on the server with timestamp."""
    try:
        # Create the esphome directory if it doesn't exist
        esphome_dir = Path("/home/coastal/smartvenue/esphome")
        esphome_dir.mkdir(exist_ok=True)

        # Generate filename with timestamp if not provided
        if payload.filename:
            filename = payload.filename
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"smartvenue-ir-{timestamp}.yaml"

        # Ensure .yaml extension
        if not filename.endswith('.yaml'):
            filename += '.yaml'

        # Full path to save the file
        file_path = esphome_dir / filename

        # Write the YAML content to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(payload.yaml)

        return SaveYamlResponse(
            success=True,
            filename=filename,
            path=str(file_path)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save YAML file: {str(e)}")


@router.post("/preview-commands", response_model=TemplatePreviewResponse)
async def generate_command_preview(payload: CommandPreviewRequest, db: Session = Depends(get_db)):
    """
    Generate YAML preview with user-selected specific commands

    This endpoint allows users to select exactly which commands they want
    for each port, rather than importing entire IR libraries.
    """
    template = db.query(ESPTemplate).filter(ESPTemplate.id == payload.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Get the base template YAML
    base_yaml = template.template_yaml

    # Build command-specific transmitter sections
    script_lines = []

    for assignment in payload.assignments:
        port_number = assignment.port_number

        if not assignment.commands:
            continue

        # Generate YAML for each selected command
        for command_sel in assignment.commands:
            command_yaml = generate_single_command_yaml(
                library_id=command_sel.library_id,
                command_name=command_sel.db_command_name,
                port_number=port_number,
                db=db
            )

            if command_yaml:
                # Create script block for this command
                script_name = f"send_port{port_number}_{command_sel.command_name}"
                script_lines.extend([
                    f"  - id: {script_name}",
                    "    then:"
                ])
                # Add indented YAML lines
                for line in command_yaml:
                    script_lines.append(f"      {line}")

    # Replace the script placeholder in the base template
    if script_lines:
        script_section = "\n".join(script_lines)
        # Replace the placeholder - we need to find where scripts go in the base template
        final_yaml = base_yaml.replace(
            "script:",
            f"script:\n{script_section}"
        )
    else:
        final_yaml = base_yaml

    # Generate dynamic transmitters based on port assignments
    # Convert CommandPreviewRequest assignments to PortAssignmentInput format
    port_assignments = []
    for assignment in payload.assignments:
        if assignment.commands:  # Only include ports that have commands assigned
            # Use the first command's library_id as the port's library
            port_assignments.append(PortAssignmentInput(
                port_number=assignment.port_number,
                library_id=assignment.commands[0].library_id
            ))

    dynamic_transmitters = _generate_remote_transmitters(port_assignments)
    final_yaml = final_yaml.replace("{{TRANSMITTER_BLOCK}}", dynamic_transmitters)

    # Generate dynamic channel dispatch for all assigned ports
    dynamic_dispatch = _generate_dynamic_channel_dispatch(port_assignments)
    final_yaml = final_yaml.replace("{{CHANNEL_DISPATCH_BLOCK}}", dynamic_dispatch)

    # Replace all remaining placeholders with appropriate content or comments
    final_yaml = final_yaml.replace("{{CUSTOM_SCRIPT_BLOCK}}", "# Custom scripts would go here")
    final_yaml = final_yaml.replace("{{PORT_BLOCK}}", "# Port assignments (auto-generated)")
    final_yaml = final_yaml.replace("{{DEVICE_BLOCK}}", "# Selected devices (auto-generated)")
    final_yaml = final_yaml.replace("{{BUTTON_SECTION}}", "# Button actions (auto-generated)")

    # Build static capabilities payload for the preview YAML
    preview_library_ids = sorted({cmd.library_id for assignment in payload.assignments for cmd in assignment.commands})
    libraries: Dict[int, IRLibrary] = {}
    if preview_library_ids:
        lib_rows = db.query(IRLibrary).filter(IRLibrary.id.in_(preview_library_ids)).all()
        libraries = {lib.id: lib for lib in lib_rows}

    preview_profiles: List[PortProfile] = []
    for assignment in port_assignments:
        library = libraries.get(assignment.library_id) if assignment.library_id else None
        preview_profiles.append(PortProfile(port_number=assignment.port_number, library=library, commands={}))

    capability_lines = _build_capabilities_payload_lines(preview_profiles, template=template)
    final_yaml = _inject_capabilities_payload(final_yaml, capability_lines)
    final_yaml = final_yaml.replace("{{CAPABILITY_BRAND_LINES}}", "")
    final_yaml = final_yaml.replace("{{CAPABILITY_COMMAND_LINES}}", "")

    # Generate readable sensors for ESP web UI
    readable_sensors = _generate_readable_sensors(port_assignments, db)
    final_yaml = final_yaml.replace("{{READABLE_SENSORS}}", readable_sensors)

    # Return the generated YAML
    return TemplatePreviewResponse(
        yaml=final_yaml,
        size_bytes=len(final_yaml.encode('utf-8')),
        estimated_compile_time_seconds=max(30, len(final_yaml) // 1000 * 5)
    )
