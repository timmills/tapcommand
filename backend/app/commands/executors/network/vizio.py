"""
Vizio SmartCast TV Executor

For Vizio SmartCast TVs (2016+)
Uses HTTPS REST API on port 7345 (or 9000 for older firmware)
"""

import time
import requests
from typing import Optional
from sqlalchemy.orm import Session

from ..base import CommandExecutor
from ...models import Command, ExecutionResult
from ....models.virtual_controller import VirtualController, VirtualDevice


class VizioExecutor(CommandExecutor):
    """
    Executor for Vizio SmartCast TVs

    Protocol: HTTPS REST API
    Port: 7345 (firmware 4.0+) or 9000 (older firmware)
    Authentication: Auth token (from pairing process)
    Library: pyvizio
    """

    # Command mapping to Vizio codeset/key codes
    KEY_MAP = {
        # Power
        "power": (5, 0),  # Power toggle
        "power_on": (11, 1),  # Discrete on
        "power_off": (11, 0),  # Discrete off

        # Volume
        "volume_up": (5, 1),
        "volume_down": (5, 2),
        "mute": (5, 4),

        # Channels
        "channel_up": (8, 0),
        "channel_down": (8, 1),

        # Navigation
        "up": (3, 8),
        "down": (3, 0),
        "left": (3, 1),
        "right": (3, 7),
        "ok": (3, 2),
        "enter": (3, 2),
        "select": (3, 2),

        # Menu/System
        "menu": (4, 8),
        "back": (4, 3),
        "exit": (4, 0),
        "home": (4, 15),
        "info": (4, 6),

        # Playback
        "play": (2, 3),
        "pause": (2, 2),

        # Numbers
        "0": (3, 48),
        "1": (3, 49),
        "2": (3, 50),
        "3": (3, 51),
        "4": (3, 52),
        "5": (3, 53),
        "6": (3, 54),
        "7": (3, 55),
        "8": (3, 56),
        "9": (3, 57),

        # Input
        "input": (7, 1),
        "hdmi1": "HDMI-1",
        "hdmi2": "HDMI-2",
        "hdmi3": "HDMI-3",
        "hdmi4": "HDMI-4",
    }

    def can_execute(self, command: Command) -> bool:
        """Check if this is a Vizio SmartCast TV"""
        return (
            command.device_type == "network_tv" and
            command.protocol == "vizio_smartcast"
        )

    async def execute(self, command: Command) -> ExecutionResult:
        """Execute command on Vizio SmartCast TV"""
        start_time = time.time()

        try:
            # Get Virtual Device from database
            device = self.db.query(VirtualDevice).join(VirtualController).filter(
                VirtualController.controller_id == command.controller_id
            ).first()

            if not device:
                return ExecutionResult(
                    success=False,
                    message=f"Vizio SmartCast TV {command.controller_id} not found",
                    error="DEVICE_NOT_FOUND"
                )

            # Send command
            return await self._send_vizio_command(device, command, start_time)

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                message=f"Vizio command '{command.command}' failed: {str(e)}",
                error=str(e),
                data={"execution_time_ms": execution_time_ms}
            )

    async def _send_vizio_command(
        self,
        device: VirtualDevice,
        command: Command,
        start_time: float
    ) -> ExecutionResult:
        """Send command to Vizio SmartCast TV using simplified approach"""
        try:
            # Get command mapping
            key_data = self.KEY_MAP.get(command.command.lower())
            if not key_data:
                return ExecutionResult(
                    success=False,
                    message=f"Unknown command: {command.command}",
                    error="UNKNOWN_COMMAND"
                )

            # TODO: Get auth token from device credentials
            # auth_token = device.vizio_auth_token
            auth_token = None  # Will need pairing first

            # Detect port (7345 for new firmware, 9000 for old)
            # Try 7345 first
            port = 7345

            # Build request
            if isinstance(key_data, tuple):
                # Key press command
                codeset, code = key_data
                url = f"https://{device.ip_address}:{port}/key_command/"
                payload = {
                    "KEYLIST": [{
                        "CODESET": codeset,
                        "CODE": code,
                        "ACTION": "KEYPRESS"
                    }]
                }
            else:
                # Input change command (HDMI)
                url = f"https://{device.ip_address}:{port}/menu_native/dynamic/tv_settings/devices/name_input"
                payload = {
                    "REQUEST": "MODIFY",
                    "VALUE": key_data,
                    "HASHVAL": 0
                }

            headers = {"Content-Type": "application/json"}
            if auth_token:
                headers["AUTH"] = auth_token

            # Send request (disable SSL verification for self-signed cert)
            response = requests.put(
                url,
                json=payload,
                headers=headers,
                timeout=5,
                verify=False
            )

            execution_time_ms = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                return ExecutionResult(
                    success=True,
                    message=f"Vizio command '{command.command}' sent successfully",
                    data={
                        "execution_time_ms": execution_time_ms,
                        "device": device.device_name,
                        "ip": device.ip_address,
                        "protocol": "smartcast"
                    }
                )
            elif response.status_code == 401 or response.status_code == 403:
                return ExecutionResult(
                    success=False,
                    message="Vizio TV requires pairing/authentication",
                    error="AUTH_REQUIRED",
                    data={
                        "execution_time_ms": execution_time_ms,
                        "note": "Use pyvizio CLI to pair and get auth token"
                    }
                )
            else:
                return ExecutionResult(
                    success=False,
                    message=f"Vizio TV returned status {response.status_code}",
                    error=f"HTTP_{response.status_code}",
                    data={"execution_time_ms": execution_time_ms}
                )

        except requests.exceptions.SSLError:
            # Try older port
            # Could retry with port 9000
            execution_time_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                message="SSL error connecting to Vizio TV",
                error="SSL_ERROR",
                data={
                    "execution_time_ms": execution_time_ms,
                    "note": "Try pairing with TV first using pyvizio"
                }
            )
        except requests.exceptions.Timeout:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                message="Vizio TV connection timeout",
                error="TIMEOUT",
                data={"execution_time_ms": execution_time_ms}
            )
        except Exception as e:
            raise
