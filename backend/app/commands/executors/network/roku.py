"""
Roku Device Executor

For Roku streaming devices and Roku TVs
"""

import time
import requests
from ..base import CommandExecutor
from ...models import Command, ExecutionResult


class RokuExecutor(CommandExecutor):
    """
    Executor for Roku devices

    Protocol: ECP (External Control Protocol) - HTTP REST API
    Port: 8060
    Authentication: None
    Documentation: https://developer.roku.com/docs/developer-program/debugging/external-control-api.md
    """

    # Roku ECP key codes
    KEY_MAP = {
        "power": "Power",
        "power_on": "PowerOn",
        "power_off": "PowerOff",
        "volume_up": "VolumeUp",
        "volume_down": "VolumeDown",
        "mute": "VolumeMute",
        "home": "Home",
        "back": "Back",
        "ok": "Select",
        "up": "Up",
        "down": "Down",
        "left": "Left",
        "right": "Right",
        "play": "Play",
        "pause": "Pause",
        "rewind": "Rev",
        "fast_forward": "Fwd",
        "info": "Info",
        "menu": "Info",  # Roku uses * button for options
    }

    def can_execute(self, command: Command) -> bool:
        return (
            command.device_type == "network_tv" and
            command.protocol == "roku"
        )

    async def execute(self, command: Command) -> ExecutionResult:
        start_time = time.time()

        try:
            # Get device
            from ....models.virtual_controller import VirtualController, VirtualDevice

            device = self.db.query(VirtualDevice).join(VirtualController).filter(
                VirtualController.controller_id == command.controller_id
            ).first()

            if not device:
                return ExecutionResult(
                    success=False,
                    message=f"Roku device {command.controller_id} not found",
                    error="DEVICE_NOT_FOUND"
                )

            # Get Roku key code
            key = self.KEY_MAP.get(command.command.lower(), command.command.title())

            # Send HTTP POST to Roku
            url = f"http://{device.ip_address}:8060/keypress/{key}"
            response = requests.post(url, timeout=3)

            execution_time_ms = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                return ExecutionResult(
                    success=True,
                    message=f"Roku command '{command.command}' sent successfully",
                    data={
                        "execution_time_ms": execution_time_ms,
                        "device": device.device_name,
                        "ip": device.ip_address,
                        "key": key
                    }
                )
            else:
                return ExecutionResult(
                    success=False,
                    message=f"Roku command failed with status {response.status_code}",
                    error=f"HTTP_{response.status_code}",
                    data={"execution_time_ms": execution_time_ms}
                )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                message=f"Roku command failed: {str(e)}",
                error=str(e),
                data={"execution_time_ms": execution_time_ms}
            )
