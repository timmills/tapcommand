#!/usr/bin/env python3
"""Ensure ESPHome native IR command libraries exist in the database."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.db.database import SessionLocal
from app.models.ir_codes import IRLibrary, IRCommand


SAMSUNG_COMMANDS: List[Dict[str, Any]] = [
    {"name": "Power", "category": "power", "signal_data": {"data": "0xE0E040BF"}},
    {"name": "Mute", "category": "audio", "signal_data": {"data": "0xE0E0F00F"}},
    {"name": "Volume Up", "category": "volume", "signal_data": {"data": "0xE0E0E01F"}},
    {"name": "Volume Down", "category": "volume", "signal_data": {"data": "0xE0E0D02F"}},
    {"name": "Channel Up", "category": "channel", "signal_data": {"data": "0xE0E048B7"}},
    {"name": "Channel Down", "category": "channel", "signal_data": {"data": "0xE0E008F7"}},
    {"name": "Number 0", "category": "number", "signal_data": {"data": "0xE0E08877"}},
    {"name": "Number 1", "category": "number", "signal_data": {"data": "0xE0E020DF"}},
    {"name": "Number 2", "category": "number", "signal_data": {"data": "0xE0E0A05F"}},
    {"name": "Number 3", "category": "number", "signal_data": {"data": "0xE0E0609F"}},
    {"name": "Number 4", "category": "number", "signal_data": {"data": "0xE0E010EF"}},
    {"name": "Number 5", "category": "number", "signal_data": {"data": "0xE0E0906F"}},
    {"name": "Number 6", "category": "number", "signal_data": {"data": "0xE0E050AF"}},
    {"name": "Number 7", "category": "number", "signal_data": {"data": "0xE0E030CF"}},
    {"name": "Number 8", "category": "number", "signal_data": {"data": "0xE0E0B04F"}},
    {"name": "Number 9", "category": "number", "signal_data": {"data": "0xE0E0708F"}},
]

LG_COMMANDS: List[Dict[str, Any]] = [
    {"name": "Power", "category": "power", "signal_data": {"address": "0x04", "command": "0x08"}},
    {"name": "Mute", "category": "audio", "signal_data": {"address": "0x04", "command": "0x09"}},
    {"name": "Volume Up", "category": "volume", "signal_data": {"address": "0x04", "command": "0x02"}},
    {"name": "Volume Down", "category": "volume", "signal_data": {"address": "0x04", "command": "0x03"}},
    {"name": "Channel Up", "category": "channel", "signal_data": {"address": "0x04", "command": "0x00"}},
    {"name": "Channel Down", "category": "channel", "signal_data": {"address": "0x04", "command": "0x01"}},
    {"name": "Number 0", "category": "number", "signal_data": {"address": "0x04", "command": "0x10"}},
    {"name": "Number 1", "category": "number", "signal_data": {"address": "0x04", "command": "0x11"}},
    {"name": "Number 2", "category": "number", "signal_data": {"address": "0x04", "command": "0x12"}},
    {"name": "Number 3", "category": "number", "signal_data": {"address": "0x04", "command": "0x13"}},
    {"name": "Number 4", "category": "number", "signal_data": {"address": "0x04", "command": "0x14"}},
    {"name": "Number 5", "category": "number", "signal_data": {"address": "0x04", "command": "0x15"}},
    {"name": "Number 6", "category": "number", "signal_data": {"address": "0x04", "command": "0x16"}},
    {"name": "Number 7", "category": "number", "signal_data": {"address": "0x04", "command": "0x17"}},
    {"name": "Number 8", "category": "number", "signal_data": {"address": "0x04", "command": "0x18"}},
    {"name": "Number 9", "category": "number", "signal_data": {"address": "0x04", "command": "0x19"}},
]

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

SONY_COMMANDS: List[Dict[str, Any]] = [
    {"name": "Power", "category": "power", "signal_data": {"data": "0x750", "nbits": 12}},
    {"name": "Mute", "category": "audio", "signal_data": {"data": "0x290", "nbits": 12}},
    {"name": "Volume Up", "category": "volume", "signal_data": {"data": "0x490", "nbits": 12}},
    {"name": "Volume Down", "category": "volume", "signal_data": {"data": "0xC90", "nbits": 12}},
    {"name": "Channel Up", "category": "channel", "signal_data": {"data": "0x090", "nbits": 12}},
    {"name": "Channel Down", "category": "channel", "signal_data": {"data": "0x890", "nbits": 12}},
    {"name": "Number 0", "category": "number", "signal_data": {"data": "0x090", "nbits": 12}},
    {"name": "Number 1", "category": "number", "signal_data": {"data": "0x010", "nbits": 12}},
    {"name": "Number 2", "category": "number", "signal_data": {"data": "0x810", "nbits": 12}},
    {"name": "Number 3", "category": "number", "signal_data": {"data": "0x410", "nbits": 12}},
    {"name": "Number 4", "category": "number", "signal_data": {"data": "0xC10", "nbits": 12}},
    {"name": "Number 5", "category": "number", "signal_data": {"data": "0x210", "nbits": 12}},
    {"name": "Number 6", "category": "number", "signal_data": {"data": "0xA10", "nbits": 12}},
    {"name": "Number 7", "category": "number", "signal_data": {"data": "0x610", "nbits": 12}},
    {"name": "Number 8", "category": "number", "signal_data": {"data": "0xE10", "nbits": 12}},
    {"name": "Number 9", "category": "number", "signal_data": {"data": "0x110", "nbits": 12}},
]

NATIVE_LIBRARIES = [
    {
        "brand": "Samsung",
        "model": "Generic Samsung",
        "name": "Samsung TV (ESPHome Native)",
        "device_category": "TVs",
        "protocol": "samsung_esp",
        "commands": SAMSUNG_COMMANDS,
        "source_path": "native/samsung_tv.json",
        "description": "Core Samsung TV commands mapped to ESPHome native transmit_samsung action",
    },
    {
        "brand": "LG",
        "model": "Generic LG",
        "name": "LG TV (ESPHome Native)",
        "device_category": "TVs",
        "protocol": "NEC",
        "commands": LG_COMMANDS,
        "source_path": "native/lg_tv.json",
        "description": "Core LG TV commands mapped to ESPHome native transmit_nec action",
    },
    {
        "brand": "Panasonic",
        "model": "Generic Panasonic",
        "name": "Panasonic TV (ESPHome Native)",
        "device_category": "TVs",
        "protocol": "panasonic_esp",
        "commands": PANASONIC_COMMANDS,
        "source_path": "native/panasonic_tv.json",
        "description": "Core Panasonic TV commands mapped to ESPHome native transmit_panasonic action",
    },
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
    {
        "brand": "Sony",
        "model": "Generic Sony",
        "name": "Sony TV (ESPHome Native)",
        "device_category": "TVs",
        "protocol": "sony_esp",
        "commands": SONY_COMMANDS,
        "source_path": "native/sony_tv.json",
        "description": "Core Sony TV commands mapped to ESPHome native transmit_sony action",
    },
]


def _hash_payload(payload: Dict[str, Any]) -> str:
    return hashlib.md5(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _upsert_library(session, spec: Dict[str, Any]) -> None:
    now = datetime.now(timezone.utc)
    fingerprint = {
        "brand": spec["brand"],
        "name": spec["name"],
        "protocol": spec["protocol"],
        "commands": spec["commands"],
    }
    file_hash = _hash_payload(fingerprint)

    library = (
        session.query(IRLibrary)
        .filter(
            IRLibrary.source == "esphome-native",
            IRLibrary.brand == spec["brand"],
            IRLibrary.name == spec["name"],
        )
        .one_or_none()
    )

    if library is None:
        library = IRLibrary(
            source="esphome-native",
            source_path=spec.get("source_path", f"native/{spec['brand'].lower()}.json"),
            source_url="https://esphome.io/components/remote_transmitter.html",
            device_category=spec["device_category"],
            brand=spec["brand"],
            model=spec.get("model"),
            name=spec["name"],
            description=spec.get("description"),
            version=spec.get("version", "1.0"),
            esp_native=True,
            hidden=spec.get("hidden", False),
            file_hash=file_hash,
            last_updated=now,
            import_status="imported",
            generic_compatibility=spec.get("generic_compatibility"),
        )
        session.add(library)
        session.flush()
    else:
        library.source_path = spec.get("source_path", library.source_path)
        library.source_url = spec.get("source_url", library.source_url)
        library.device_category = spec["device_category"]
        library.brand = spec["brand"]
        library.model = spec.get("model")
        library.name = spec["name"]
        library.description = spec.get("description")
        library.version = spec.get("version", library.version)
        library.esp_native = True
        library.hidden = spec.get("hidden", library.hidden)
        library.file_hash = file_hash
        library.last_updated = now
        library.import_status = "imported"
        library.generic_compatibility = spec.get("generic_compatibility")

        session.query(IRCommand).filter(IRCommand.library_id == library.id).delete()

    for command in spec["commands"]:
        session.add(
            IRCommand(
                library_id=library.id,
                name=command["name"],
                display_name=command.get("display_name", command["name"]),
                category=command.get("category"),
                protocol=spec["protocol"],
                signal_data=command["signal_data"],
            )
        )


def main() -> None:
    session = SessionLocal()
    try:
        for spec in NATIVE_LIBRARIES:
            _upsert_library(session, spec)
        session.commit()
        print("ESPHome native libraries ensured")
    finally:
        session.close()


if __name__ == "__main__":
    main()
