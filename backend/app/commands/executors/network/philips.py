"""
Philips Android TV Executor

For Philips Android TVs (2015+)
Uses JointSpace API on port 1925/1926
"""

import time
import requests
from requests.auth import HTTPDigestAuth
from typing import Optional
from sqlalchemy.orm import Session

from ..base import CommandExecutor
from ...models import Command, ExecutionResult
from ....models.virtual_controller import VirtualController, VirtualDevice


class PhilipsExecutor(CommandExecutor):
    """
    Executor for Philips Android TVs

    Protocol: JointSpace API (REST)
    Port: 1925 (non-Android) or 1926 (Android, HTTPS)
    Authentication: Digest auth (username/password) or API key
    Library: pylips (optional)
    """

    # Key mapping for Philips JointSpace
    KEY_MAP = {
        # Power
        "power": "Standby",
        "power_on": "Standby",  # Toggle
        "power_off": "Standby",

        # Volume
        "volume_up": "VolumeUp",
        "volume_down": "VolumeDown",
        "mute": "Mute",

        # Channels
        "channel_up": "ChannelStepUp",
        "channel_down": "ChannelStepDown",

        # Navigation
        "up": "CursorUp",
        "down": "CursorDown",
        "left": "CursorLeft",
        "right": "CursorRight",
        "ok": "Confirm",
        "enter": "Confirm",
        "select": "Confirm",

        # Menu/System
        "home": "Home",
        "menu": "Home",  # Android TVs use Home
        "back": "Back",
        "exit": "Back",
        "info": "Info",

        # Playback
        "play": "Play",
        "pause": "Pause",
        "stop": "Stop",
        "rewind": "Rewind",
        "fast_forward": "FastForward",

        # Numbers
        "0": "Digit0",
        "1": "Digit1",
        "2": "Digit2",
        "3": "Digit3",
        "4": "Digit4",
        "5": "Digit5",
        "6": "Digit6",
        "7": "Digit7",
        "8": "Digit8",
        "9": "Digit9",

        # Other
        "source": "Source",
        "options": "Options",
    }

    def can_execute(self, command: Command) -> bool:
        """Check if this is a Philips Android TV"""
        return (
            command.device_type == "network_tv" and
            command.protocol == "philips_jointspace"
        )

    async def execute(self, command: Command) -> ExecutionResult:
        """Execute command on Philips Android TV"""
        start_time = time.time()

        try:
            # Get Virtual Device from database
            device = self.db.query(VirtualDevice).join(VirtualController).filter(
                VirtualController.controller_id == command.controller_id
            ).first()

            if not device:
                return ExecutionResult(
                    success=False,
                    message=f"Philips Android TV {command.controller_id} not found",
                    error="DEVICE_NOT_FOUND"
                )

            # Send command via JointSpace API
            return await self._send_jointspace_command(device, command, start_time)

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                message=f"Philips command '{command.command}' failed: {str(e)}",
                error=str(e),
                data={"execution_time_ms": execution_time_ms}
            )

    async def _send_jointspace_command(
        self,
        device: VirtualDevice,
        command: Command,
        start_time: float
    ) -> ExecutionResult:
        """Send command to Philips TV using JointSpace API"""
        try:
            # Get key name
            key = self.KEY_MAP.get(command.command.lower())
            if not key:
                # Try direct key name
                key = command.command.title()

            # TODO: Get credentials from device
            # username = device.philips_username or "user"
            # password = device.philips_password or "password"
            username = None
            password = None

            # Detect if Android TV (port 1926, HTTPS) or older (port 1925, HTTP)
            # Try Android TV first (more common)
            port = 1926
            protocol = "https"

            # Build request
            url = f"{protocol}://{device.ip_address}:{port}/6/input/key"
            payload = {"key": key}

            # Prepare auth if credentials available
            auth = None
            if username and password:
                auth = HTTPDigestAuth(username, password)

            # Send request
            response = requests.post(
                url,
                json=payload,
                auth=auth,
                timeout=5,
                verify=False  # Self-signed cert
            )

            execution_time_ms = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                return ExecutionResult(
                    success=True,
                    message=f"Philips command '{command.command}' sent successfully",
                    data={
                        "execution_time_ms": execution_time_ms,
                        "device": device.device_name,
                        "ip": device.ip_address,
                        "key": key,
                        "protocol": "jointspace"
                    }
                )
            elif response.status_code == 401:
                return ExecutionResult(
                    success=False,
                    message="Philips TV requires authentication",
                    error="AUTH_REQUIRED",
                    data={
                        "execution_time_ms": execution_time_ms,
                        "note": "Configure digest auth credentials for this TV"
                    }
                )
            else:
                # Try non-Android port
                url = f"http://{device.ip_address}:1925/6/input/key"
                response = requests.post(
                    url,
                    json=payload,
                    auth=auth,
                    timeout=5
                )

                execution_time_ms = int((time.time() - start_time) * 1000)

                if response.status_code == 200:
                    return ExecutionResult(
                        success=True,
                        message=f"Philips command '{command.command}' sent successfully",
                        data={
                            "execution_time_ms": execution_time_ms,
                            "device": device.device_name,
                            "ip": device.ip_address,
                            "key": key,
                            "protocol": "jointspace_legacy"
                        }
                    )
                else:
                    return ExecutionResult(
                        success=False,
                        message=f"Philips TV returned status {response.status_code}",
                        error=f"HTTP_{response.status_code}",
                        data={"execution_time_ms": execution_time_ms}
                    )

        except requests.exceptions.Timeout:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                message="Philips TV connection timeout",
                error="TIMEOUT",
                data={"execution_time_ms": execution_time_ms}
            )
        except Exception as e:
            raise
