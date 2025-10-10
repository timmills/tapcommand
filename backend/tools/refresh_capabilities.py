"""Refresh ESPHome capability snapshots for managed devices.

Run from the project root with the backend virtualenv (or ensure the
environment can import the backend package and its dependencies):

    DATABASE_URL=sqlite:///backend/tapcommand.db \
    backend/venv/bin/python3 backend/tools/refresh_capabilities.py

The script queries managed devices, attempts to fetch their capability
payloads using the familiar fallback order (device override first,
otherwise the global application key), and persists any snapshots under
`devices.capabilities`.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

import sys


# Allow `import app.services.*` while keeping the script alongside other tools.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT))

from app.services.esphome_client import esphome_manager  # type: ignore  # noqa: E402
from app.services.settings_service import settings_service  # type: ignore  # noqa: E402


DB_PATH = REPO_ROOT / "tapcommand.db"


async def refresh_capabilities() -> None:
    print(f"Opening database at {DB_PATH}…")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT hostname, current_ip_address, api_key FROM managed_devices")
    managed_devices = cur.fetchall()

    if not managed_devices:
        print("No managed devices found.")
        return

    for device in managed_devices:
        hostname = device["hostname"]
        ip_address = device["current_ip_address"]
        override_key = device["api_key"]
        app_key = settings_service.get_setting("esphome_api_key")
        api_key = override_key or app_key

        print(f"Fetching capabilities for {hostname} ({ip_address})…")

        if not api_key:
            print("  Skipping: no API key available (override or global).")
            continue

        try:
            snapshot = await esphome_manager.fetch_capabilities(hostname, ip_address, api_key)
        except Exception as exc:  # pragma: no cover - network dependent
            print(f"  Error: {exc}")
            continue

        if not snapshot:
            print("  No capabilities returned.")
            continue

        now_iso = datetime.now(timezone.utc).isoformat()

        print("  Snapshot received, storing in database.")
        firmware_version = snapshot.get("firmware_version")

        cur.execute(
            "UPDATE devices SET capabilities = ?, last_seen = ?, ip_address = COALESCE(?, ip_address), firmware_version = COALESCE(?, firmware_version) WHERE hostname = ?",
            (
                json.dumps(snapshot),
                now_iso,
                ip_address,
                firmware_version,
                hostname,
            ),
        )

        # Update managed devices (if present) with the latest snapshot
        cur.execute(
            "SELECT id, current_ip_address, last_ip_address FROM managed_devices WHERE hostname = ?",
            (hostname,),
        )
        managed_row = cur.fetchone()
        if managed_row:
            managed_id = managed_row["id"]
            previous_ip = managed_row["current_ip_address"]
            previous_last_ip = managed_row["last_ip_address"]

            # Update last_ip only when the address changes, otherwise retain the existing value
            new_last_ip = previous_ip if previous_ip and previous_ip != ip_address else previous_last_ip

            cur.execute(
                "UPDATE managed_devices SET current_ip_address = ?, last_ip_address = ?, firmware_version = COALESCE(?, firmware_version), is_online = 1, last_seen = ? WHERE id = ?",
                (
                    ip_address,
                    new_last_ip,
                    firmware_version,
                    now_iso,
                    managed_id,
                ),
            )

            # Synchronise IR port metadata based on the snapshot payload
            ports_payload = snapshot.get("ports")
            port_map = {}
            if isinstance(ports_payload, list):
                for entry in ports_payload:
                    if not isinstance(entry, dict):
                        continue
                    raw_port = entry.get("port") or entry.get("port_number")
                    try:
                        port_number = int(raw_port)
                    except (TypeError, ValueError):
                        continue
                    port_map[port_number] = entry

            cur.execute(
                "SELECT id, port_number FROM ir_ports WHERE device_id = ?",
                (managed_id,),
            )
            port_rows = cur.fetchall()
            for port_row in port_rows:
                entry = port_map.get(port_row["port_number"])
                if entry:
                    cur.execute(
                        "UPDATE ir_ports SET is_active = 1 WHERE id = ?",
                        (port_row["id"],),
                    )
                else:
                    cur.execute(
                        "UPDATE ir_ports SET is_active = 0 WHERE id = ?",
                        (port_row["id"],),
                    )

        conn.commit()

    await esphome_manager.disconnect_all()
    conn.close()


def main() -> None:
    asyncio.run(refresh_capabilities())


if __name__ == "__main__":
    main()
