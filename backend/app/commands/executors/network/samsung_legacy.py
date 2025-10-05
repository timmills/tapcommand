"""
Samsung Legacy TV Executor

For older Samsung TVs (D/E/F series, pre-2016) using port 55000
"""

import time
from typing import Optional
from sqlalchemy.orm import Session

from ..base import CommandExecutor
from ...models import Command, ExecutionResult
from ....models.virtual_controller import VirtualController, VirtualDevice


class SamsungLegacyExecutor(CommandExecutor):
    """
    Executor for Samsung Legacy TVs (pre-2016)

    Protocol: Base64-encoded commands over TCP port 55000
    No authentication required
    """

    # Command mapping to Samsung KEY codes
    KEY_MAP = {
        "power": "KEY_POWER",
        "power_on": "KEY_POWERON",
        "power_off": "KEY_POWEROFF",
        "volume_up": "KEY_VOLUP",
        "volume_down": "KEY_VOLDOWN",
        "mute": "KEY_MUTE",
        "channel_up": "KEY_CHUP",
        "channel_down": "KEY_CHDOWN",
        "source": "KEY_SOURCE",
        "hdmi": "KEY_HDMI",
        "menu": "KEY_MENU",
        "home": "KEY_HOME",
        "back": "KEY_RETURN",
        "exit": "KEY_EXIT",
        "ok": "KEY_ENTER",
        "up": "KEY_UP",
        "down": "KEY_DOWN",
        "left": "KEY_LEFT",
        "right": "KEY_RIGHT",
        "info": "KEY_INFO",
        "guide": "KEY_GUIDE",
        # Digit keys
        "0": "KEY_0",
        "1": "KEY_1",
        "2": "KEY_2",
        "3": "KEY_3",
        "4": "KEY_4",
        "5": "KEY_5",
        "6": "KEY_6",
        "7": "KEY_7",
        "8": "KEY_8",
        "9": "KEY_9",
    }

    def can_execute(self, command: Command) -> bool:
        """Check if this is a Samsung Legacy TV"""
        return (
            command.device_type == "network_tv" and
            command.protocol == "samsung_legacy"
        )

    async def execute(self, command: Command) -> ExecutionResult:
        """Execute command on Samsung Legacy TV"""
        start_time = time.time()

        try:
            import samsungctl

            # Get Virtual Device from database
            device = self.db.query(VirtualDevice).join(VirtualController).filter(
                VirtualController.controller_id == command.controller_id
            ).first()

            if not device:
                return ExecutionResult(
                    success=False,
                    message=f"Samsung TV {command.controller_id} not found",
                    error="DEVICE_NOT_FOUND"
                )

            # Get the KEY code for this command
            key = self.KEY_MAP.get(command.command.lower())
            if not key:
                # Try direct KEY_ format
                key = f"KEY_{command.command.upper()}"

            # Configure Samsung remote
            config = {
                "name": "SmartVenue",
                "description": "SmartVenue Control System",
                "id": "smartvenue",
                "host": device.ip_address,
                "port": 55000,
                "method": "legacy",
                "timeout": 3,
            }

            # Send command
            with samsungctl.Remote(config) as remote:
                remote.control(key)

            execution_time_ms = int((time.time() - start_time) * 1000)

            return ExecutionResult(
                success=True,
                message=f"Samsung Legacy command '{command.command}' sent successfully",
                data={
                    "execution_time_ms": execution_time_ms,
                    "device": device.device_name,
                    "ip": device.ip_address,
                    "key": key
                }
            )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                message=f"Samsung Legacy command '{command.command}' failed: {str(e)}",
                error=str(e),
                data={"execution_time_ms": execution_time_ms}
            )
