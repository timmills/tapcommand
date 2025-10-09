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
        """Check if this is a Samsung TV (legacy or websocket)"""
        return (
            command.device_type == "network_tv" and
            command.protocol in ["samsung_legacy", "samsung_websocket"]
        )

    async def execute(self, command: Command) -> ExecutionResult:
        """Execute command on Samsung Legacy TV"""
        start_time = time.time()

        try:
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

            # Special handling for power_on: Use Wake-on-LAN instead of Samsung protocol
            # Samsung Legacy protocol (port 55000) doesn't work when TV is OFF
            if command.command.lower() in ["power_on", "poweron"]:
                return await self._wake_on_lan(device, start_time)

            # Get the KEY code for this command
            key = self.KEY_MAP.get(command.command.lower())
            if not key:
                # Try direct KEY_ format
                key = f"KEY_{command.command.upper()}"

            # Check if device uses WebSocket (newer Samsung TVs)
            if command.protocol == "samsung_websocket":
                return await self._execute_websocket(device, key, command, start_time)

            # Legacy method (port 55000)
            import samsungctl

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

    async def _execute_websocket(self, device: VirtualDevice, key: str, command: Command, start_time: float) -> ExecutionResult:
        """
        Execute command on Samsung TV using WebSocket (2016+ models with TokenAuthSupport)
        """
        try:
            import json
            from samsungtvws import SamsungTVWS

            # Get auth token from connection_config
            # Note: connection_config is a JSON column, already deserialized as dict
            connection_config = device.connection_config if device.connection_config else {}
            auth_token = connection_config.get('auth_token')  # May be None for 2016 TVs
            port = connection_config.get('port', 8002)

            # Create WebSocket connection
            # Note: auth_token may be None for 2016 TVs (no TokenAuthSupport)
            # Pass token directly (not token_file) to ensure it's used in the URL if present
            tv = SamsungTVWS(
                host=device.ip_address,
                port=port,
                token=auth_token,  # None is valid for 2016 TVs, required for 2017+
                name='SmartVenue',
                timeout=5
            )

            # Send the key command via remote control
            # Note: samsungtvws uses shortcuts for common commands, remote.control for raw keys
            shortcuts = tv.shortcuts()

            # Map command to shortcut method if available
            if hasattr(shortcuts, command.command.lower()):
                # Use shortcut method (mute(), volume_up(), etc.)
                method = getattr(shortcuts, command.command.lower())
                method()
            else:
                # Fall back to sending raw key code
                tv.remote.control(key)

            execution_time_ms = int((time.time() - start_time) * 1000)

            return ExecutionResult(
                success=True,
                message=f"Samsung WebSocket command '{command.command}' sent successfully",
                data={
                    "execution_time_ms": execution_time_ms,
                    "device": device.device_name,
                    "ip": device.ip_address,
                    "key": key,
                    "method": "websocket"
                }
            )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                message=f"Samsung WebSocket command '{command.command}' failed: {str(e)}",
                error=str(e),
                data={"execution_time_ms": execution_time_ms}
            )

    async def _wake_on_lan(self, device: VirtualDevice, start_time: float) -> ExecutionResult:
        """
        Turn on Samsung Legacy TV using Wake-on-LAN

        Samsung Legacy protocol (port 55000) doesn't work when TV is OFF because
        the network interface is unpowered. Must use WOL magic packets instead.
        """
        if not device.mac_address:
            return ExecutionResult(
                success=False,
                message=f"Cannot power on {device.device_name}: MAC address not configured",
                error="MAC_ADDRESS_REQUIRED"
            )

        try:
            from wakeonlan import send_magic_packet

            # Send multiple WOL packets for reliability (recommended: 16 packets)
            packet_count = 16
            for _ in range(packet_count):
                send_magic_packet(device.mac_address)

            execution_time_ms = int((time.time() - start_time) * 1000)

            return ExecutionResult(
                success=True,
                message=f"Wake-on-LAN packets sent to {device.device_name}",
                data={
                    "execution_time_ms": execution_time_ms,
                    "device": device.device_name,
                    "ip": device.ip_address,
                    "mac_address": device.mac_address,
                    "method": "wake_on_lan",
                    "packets_sent": packet_count,
                    "note": "TV may take 5-15 seconds to fully boot"
                }
            )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                message=f"Failed to send WOL packets: {str(e)}",
                error=str(e),
                data={"execution_time_ms": execution_time_ms}
            )
