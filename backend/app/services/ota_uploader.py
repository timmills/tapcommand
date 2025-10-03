"""Utilities for streaming OTA uploads to ESPHome devices."""

from __future__ import annotations

import logging
import threading
import aiohttp
import asyncio
from pathlib import Path
from typing import Callable, Optional

from esphome import espota2


OTAEventCallback = Callable[[str, object], None]


class _CallbackProgress:
    """Patchable replacement for ``espota2.ProgressBar`` that relays progress."""

    def __init__(self, emitter: OTAEventCallback) -> None:
        self._emit = emitter
        self._last_percentage: Optional[int] = None

    def update(self, progress: float) -> None:  # pragma: no cover - thin wrapper
        percentage = max(0, min(100, int(progress * 100)))
        if percentage == self._last_percentage:
            return
        self._last_percentage = percentage
        self._emit("progress", percentage)

    def done(self) -> None:  # pragma: no cover - thin wrapper
        self._emit("progress", 100)


_patch_lock = threading.Lock()


def run_ota_with_callback(
    host: str,
    port: int,
    password: str,
    binary_path: Path,
    emitter: OTAEventCallback,
) -> tuple[bool, Optional[str]]:
    """Execute an OTA upload while emitting structured events.

    Args:
        host: Target hostname or IP.
        port: OTA port (typically 3232 for ESPHome OTA v2, 8266 for legacy).
        password: OTA password (may be empty).
        binary_path: Path to the compiled firmware binary.
        emitter: Callback invoked with (event_type, payload) tuples. Expected
            event types: ``log``, ``progress``.

    Returns:
        Tuple of (success flag, resolved IP address or ``None``).
    """

    binary_path = Path(binary_path)
    if not binary_path.exists():
        raise FileNotFoundError(f"Firmware binary not found: {binary_path}")

    # Ensure only one caller patches espota2 internals at a time.
    with _patch_lock:
        original_progress = espota2.ProgressBar

        class _PatchedProgress(_CallbackProgress):
            def __init__(self) -> None:
                super().__init__(emitter)

        espota2.ProgressBar = _PatchedProgress  # type: ignore[assignment]

        logger = espota2._LOGGER
        handler = _CallbackLogHandler(emitter)
        previous_level = logger.level
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        try:
            exit_code, resolved_ip = espota2.run_ota(host, port, password, str(binary_path))
            success = exit_code == 0
        finally:
            logger.removeHandler(handler)
            logger.setLevel(previous_level)
            espota2.ProgressBar = original_progress  # type: ignore[assignment]

    return success, resolved_ip


class _CallbackLogHandler(logging.Handler):
    """Forward OTA logs to the provided emitter."""

    def __init__(self, emitter: OTAEventCallback) -> None:
        super().__init__()
        self._emit = emitter
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - thin wrapper
        try:
            message = self.format(record)
        except Exception:  # pragma: no cover - defensive
            message = record.getMessage()
        self._emit("log", message)


async def run_http_ota_with_callback(
    host: str,
    port: int,
    password: str,
    binary_path: Path,
    emitter: OTAEventCallback,
) -> tuple[bool, Optional[str]]:
    """Execute an HTTP OTA upload via web interface.

    Args:
        host: Target hostname or IP.
        port: HTTP port (typically 80).
        password: OTA password (may be empty).
        binary_path: Path to the compiled firmware binary.
        emitter: Callback invoked with (event_type, payload) tuples.

    Returns:
        Tuple of (success flag, resolved IP address or None).
    """
    binary_path = Path(binary_path)
    if not binary_path.exists():
        raise FileNotFoundError(f"Firmware binary not found: {binary_path}")

    url = f"http://{host}:{port}/update"

    try:
        emitter("log", f"Starting HTTP OTA upload to {url}")

        async with aiohttp.ClientSession() as session:
            with open(binary_path, 'rb') as f:
                file_size = binary_path.stat().st_size

                # Create form data
                data = aiohttp.FormData()
                data.add_field('update', f, filename='firmware.bin', content_type='application/octet-stream')

                # Add password if provided
                if password:
                    data.add_field('password', password)

                emitter("log", f"Uploading {file_size} bytes...")
                emitter("progress", 0)

                async with session.post(url, data=data, timeout=300) as response:
                    if response.status == 200:
                        emitter("progress", 100)
                        emitter("log", "Upload completed successfully")
                        return True, host
                    else:
                        error_text = await response.text()
                        emitter("log", f"Upload failed: HTTP {response.status} - {error_text}")
                        return False, None

    except asyncio.TimeoutError:
        emitter("log", "Upload timed out")
        return False, None
    except Exception as e:
        emitter("log", f"Upload failed: {str(e)}")
        return False, None
