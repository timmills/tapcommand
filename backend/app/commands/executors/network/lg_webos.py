"""
LG webOS TV Executor

For LG Smart TVs with webOS (2014+)
Uses WebSocket communication on port 3000
"""

import time
import json
from typing import Optional
from sqlalchemy.orm import Session

from ..base import CommandExecutor
from ...models import Command, ExecutionResult
from ....models.virtual_controller import VirtualController, VirtualDevice


class LGWebOSExecutor(CommandExecutor):
    """
    Executor for LG webOS TVs

    Protocol: WebSocket on port 3000 (or 3001 for SSL)
    Authentication: Pairing key (stored after first pairing)
    Library: aiowebostv (async) or pywebostv (sync)
    """

    # Command mapping to LG webOS methods
    KEY_MAP = {
        # Power
        "power": "system/turnOff",  # Can only turn off via network
        "power_off": "system/turnOff",
        # power_on requires WOL - TV must be on to receive network commands

        # Volume
        "volume_up": "audio/volumeUp",
        "volume_down": "audio/volumeDown",
        "mute": "audio/setMute",

        # Channels
        "channel_up": "tv/channelUp",
        "channel_down": "tv/channelDown",

        # Navigation
        "up": "com.webos.service.ime/sendEnterKey",  # Special handling needed
        "down": "com.webos.service.ime/sendEnterKey",
        "left": "com.webos.service.ime/sendEnterKey",
        "right": "com.webos.service.ime/sendEnterKey",
        "ok": "com.webos.service.ime/sendEnterKey",
        "enter": "com.webos.service.ime/sendEnterKey",

        # Menu/System
        "home": "system.launcher/home",
        "back": "com.webos.service.ime/sendEnterKey",
        "exit": "system.launcher/close",
        "menu": "com.webos.service.ime/sendEnterKey",

        # Playback
        "play": "media.controls/play",
        "pause": "media.controls/pause",
        "stop": "media.controls/stop",
        "rewind": "media.controls/rewind",
        "fast_forward": "media.controls/fastForward",
    }

    def can_execute(self, command: Command) -> bool:
        """Check if this is an LG webOS TV"""
        return (
            command.device_type == "network_tv" and
            command.protocol == "lg_webos"
        )

    async def execute(self, command: Command) -> ExecutionResult:
        """Execute command on LG webOS TV"""
        start_time = time.time()

        try:
            # Get Virtual Device from database
            device = self.db.query(VirtualDevice).join(VirtualController).filter(
                VirtualController.controller_id == command.controller_id
            ).first()

            if not device:
                return ExecutionResult(
                    success=False,
                    message=f"LG webOS TV {command.controller_id} not found",
                    error="DEVICE_NOT_FOUND"
                )

            # Special handling for power_on: Use Wake-on-LAN
            if command.command.lower() in ["power_on", "poweron"]:
                wol_result = await self._try_wake_on_lan(device, start_time)
                if wol_result:
                    return wol_result

            # Send command via webOS client
            return await self._send_webos_command(device, command, start_time)

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                message=f"LG webOS command '{command.command}' failed: {str(e)}",
                error=str(e),
                data={"execution_time_ms": execution_time_ms}
            )

    async def _send_webos_command(
        self,
        device: VirtualDevice,
        command: Command,
        start_time: float
    ) -> ExecutionResult:
        """Send command to LG webOS TV"""
        try:
            from pywebostv.discovery import discover
            from pywebostv.connection import WebOSClient
            from pywebostv.controls import InputControl, MediaControl, SystemControl, TVControl

            # Get stored pairing key (if any)
            # TODO: Retrieve from database - device.webos_pairing_key
            store = {}  # Simple dict storage for now

            # Connect to TV
            client = WebOSClient(device.ip_address, secure=False)
            client.connect()

            # Create control objects
            system = SystemControl(client)
            media = MediaControl(client)
            tv = TVControl(client)
            inp = InputControl(client)

            cmd_lower = command.command.lower()

            # Execute command
            if cmd_lower in ["power", "power_off", "poweroff"]:
                system.power_off()

            elif cmd_lower == "volume_up":
                system.volume_up()

            elif cmd_lower == "volume_down":
                system.volume_down()

            elif cmd_lower == "mute":
                system.mute(True)

            elif cmd_lower == "channel_up":
                tv.channel_up()

            elif cmd_lower == "channel_down":
                tv.channel_down()

            elif cmd_lower in ["play"]:
                media.play()

            elif cmd_lower in ["pause"]:
                media.pause()

            elif cmd_lower in ["stop"]:
                media.stop()

            elif cmd_lower in ["rewind"]:
                media.rewind()

            elif cmd_lower in ["fast_forward", "fastforward"]:
                media.fast_forward()

            elif cmd_lower in ["home"]:
                system.notify("SmartVenue - Home")  # Placeholder

            # Navigation keys
            elif cmd_lower == "up":
                inp.up()
            elif cmd_lower == "down":
                inp.down()
            elif cmd_lower == "left":
                inp.left()
            elif cmd_lower == "right":
                inp.right()
            elif cmd_lower in ["ok", "enter", "select"]:
                inp.enter()
            elif cmd_lower == "back":
                inp.back()

            else:
                # Try direct button name
                inp.enter()  # Fallback

            client.close()

            execution_time_ms = int((time.time() - start_time) * 1000)

            return ExecutionResult(
                success=True,
                message=f"LG webOS command '{command.command}' sent successfully",
                data={
                    "execution_time_ms": execution_time_ms,
                    "device": device.device_name,
                    "ip": device.ip_address,
                    "protocol": "webos"
                }
            )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_str = str(e).lower()

            if "pairing" in error_str or "key" in error_str:
                return ExecutionResult(
                    success=False,
                    message=f"LG TV requires pairing: {str(e)}",
                    error="PAIRING_REQUIRED",
                    data={
                        "execution_time_ms": execution_time_ms,
                        "note": "Accept pairing request on TV screen to get pairing key"
                    }
                )

            raise

    async def _try_wake_on_lan(
        self,
        device: VirtualDevice,
        start_time: float
    ) -> Optional[ExecutionResult]:
        """
        Try to wake LG TV using Wake-on-LAN

        LG webOS TVs cannot be turned on via network command - WOL is required
        """
        if not device.mac_address:
            return ExecutionResult(
                success=False,
                message=f"Cannot power on {device.device_name}: MAC address not configured",
                error="MAC_ADDRESS_REQUIRED",
                data={
                    "note": "LG webOS TVs cannot be turned on via network. WOL or IR required."
                }
            )

        try:
            from wakeonlan import send_magic_packet

            # Send WOL packets
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
                    "note": "TV may take 5-15 seconds to fully boot. Ensure WOL enabled in TV network settings."
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
