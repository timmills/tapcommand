"""
Sony Bravia TV Executor

For Sony Bravia TVs (2013+) with network control
Uses REST API and IRCC (IR over IP) protocol
"""

import time
import requests
from typing import Optional
from sqlalchemy.orm import Session

from ..base import CommandExecutor
from ...models import Command, ExecutionResult
from ....models.virtual_controller import VirtualController, VirtualDevice


class SonyBraviaExecutor(CommandExecutor):
    """
    Executor for Sony Bravia TVs

    Protocol: REST API + IRCC (IR over IP)
    Port: 80 (HTTP) or 50001/50002 for newer models
    Authentication: Pre-Shared Key (PSK) or PIN code
    Library: pybravia or braviarc
    """

    # IRCC codes for Sony Bravia TVs
    IRCC_MAP = {
        # Power
        "power": "AAAAAQAAAAEAAAAVAw==",  # Power toggle
        "power_on": "AAAAAQAAAAEAAAAuAw==",  # Power on
        "power_off": "AAAAAQAAAAEAAAAvAw==",  # Power off

        # Volume
        "volume_up": "AAAAAQAAAAEAAAASAw==",
        "volume_down": "AAAAAQAAAAEAAAATAw==",
        "mute": "AAAAAQAAAAEAAAAUAw==",

        # Channels
        "channel_up": "AAAAAQAAAAEAAAAQAw==",
        "channel_down": "AAAAAQAAAAEAAAARAw==",

        # Navigation
        "up": "AAAAAQAAAAEAAAB0Aw==",
        "down": "AAAAAQAAAAEAAAB1Aw==",
        "left": "AAAAAQAAAAEAAAA0Aw==",
        "right": "AAAAAQAAAAEAAAAzAw==",
        "ok": "AAAAAQAAAAEAAABlAw==",
        "enter": "AAAAAQAAAAEAAABlAw==",
        "select": "AAAAAQAAAAEAAABlAw==",

        # Menu/System
        "home": "AAAAAQAAAAEAAABgAw==",
        "menu": "AAAAAQAAAAEAAAAOAw==",
        "back": "AAAAAgAAAJcAAAAjAw==",
        "exit": "AAAAAQAAAAEAAABjAw==",
        "info": "AAAAAQAAAAEAAAA6Aw==",

        # Playback
        "play": "AAAAAgAAAJcAAAAaAw==",
        "pause": "AAAAAgAAAJcAAAAZAw==",
        "stop": "AAAAAgAAAJcAAAAYAw==",
        "rewind": "AAAAAgAAAJcAAAAbAw==",
        "fast_forward": "AAAAAgAAAJcAAAAcAw==",

        # Numbers
        "0": "AAAAAQAAAAEAAAAJAw==",
        "1": "AAAAAQAAAAEAAAAAAw==",
        "2": "AAAAAQAAAAEAAAABAw==",
        "3": "AAAAAQAAAAEAAAACAw==",
        "4": "AAAAAQAAAAEAAAADAw==",
        "5": "AAAAAQAAAAEAAAAEAw==",
        "6": "AAAAAQAAAAEAAAAFAw==",
        "7": "AAAAAQAAAAEAAAAGAw==",
        "8": "AAAAAQAAAAEAAAAHAw==",
        "9": "AAAAAQAAAAEAAAAIAw==",

        # Input
        "input": "AAAAAQAAAAEAAAAlAw==",
        "hdmi1": "AAAAAgAAABoAAABaAw==",
        "hdmi2": "AAAAAgAAABoAAABbAw==",
        "hdmi3": "AAAAAgAAABoAAABcAw==",
        "hdmi4": "AAAAAgAAABoAAABdAw==",

        # Netflix
        "netflix": "AAAAAgAAABoAAAB8Aw==",
    }

    def can_execute(self, command: Command) -> bool:
        """Check if this is a Sony Bravia TV"""
        return (
            command.device_type == "network_tv" and
            command.protocol == "sony_bravia"
        )

    async def execute(self, command: Command) -> ExecutionResult:
        """Execute command on Sony Bravia TV"""
        start_time = time.time()

        try:
            # Get Virtual Device from database
            device = self.db.query(VirtualDevice).join(VirtualController).filter(
                VirtualController.controller_id == command.controller_id
            ).first()

            if not device:
                return ExecutionResult(
                    success=False,
                    message=f"Sony Bravia TV {command.controller_id} not found",
                    error="DEVICE_NOT_FOUND"
                )

            # Special handling for power_on: Try WOL first
            if command.command.lower() in ["power_on", "poweron"]:
                wol_result = await self._try_wake_on_lan(device, start_time)
                if wol_result and wol_result.success:
                    return wol_result
                # If WOL fails or not available, try IRCC power command

            # Send command via IRCC
            return await self._send_ircc_command(device, command, start_time)

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                message=f"Sony Bravia command '{command.command}' failed: {str(e)}",
                error=str(e),
                data={"execution_time_ms": execution_time_ms}
            )

    async def _send_ircc_command(
        self,
        device: VirtualDevice,
        command: Command,
        start_time: float
    ) -> ExecutionResult:
        """Send IRCC command to Sony Bravia TV"""
        try:
            # Get IRCC code for command
            ircc_code = self.IRCC_MAP.get(command.command.lower())
            if not ircc_code:
                return ExecutionResult(
                    success=False,
                    message=f"Unknown command: {command.command}",
                    error="UNKNOWN_COMMAND"
                )

            # TODO: Get PSK from device credentials
            # For now, try without authentication (works on some models)
            psk = None  # device.sony_psk

            # Build IRCC request
            headers = {
                "Content-Type": "text/xml; charset=UTF-8",
                "SOAPACTION": '"urn:schemas-sony-com:service:IRCC:1#X_SendIRCC"',
            }

            if psk:
                headers["X-Auth-PSK"] = psk

            # SOAP envelope for IRCC command
            body = f'''<?xml version="1.0"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
    <s:Body>
        <u:X_SendIRCC xmlns:u="urn:schemas-sony-com:service:IRCC:1">
            <IRCCCode>{ircc_code}</IRCCCode>
        </u:X_SendIRCC>
    </s:Body>
</s:Envelope>'''

            # Send to TV
            url = f"http://{device.ip_address}/sony/IRCC"
            response = requests.post(url, headers=headers, data=body, timeout=5)

            execution_time_ms = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                return ExecutionResult(
                    success=True,
                    message=f"Sony Bravia command '{command.command}' sent successfully",
                    data={
                        "execution_time_ms": execution_time_ms,
                        "device": device.device_name,
                        "ip": device.ip_address,
                        "ircc_code": ircc_code,
                        "protocol": "ircc"
                    }
                )
            elif response.status_code == 401:
                return ExecutionResult(
                    success=False,
                    message="Sony TV requires PSK authentication",
                    error="PSK_REQUIRED",
                    data={
                        "execution_time_ms": execution_time_ms,
                        "note": "Configure PSK in TV settings: Network > IP Control > Pre-Shared Key"
                    }
                )
            else:
                return ExecutionResult(
                    success=False,
                    message=f"Sony TV returned status {response.status_code}",
                    error=f"HTTP_{response.status_code}",
                    data={"execution_time_ms": execution_time_ms}
                )

        except requests.exceptions.Timeout:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                message="Sony TV connection timeout",
                error="TIMEOUT",
                data={
                    "execution_time_ms": execution_time_ms,
                    "note": "Ensure TV is powered on and IP control is enabled"
                }
            )
        except Exception as e:
            raise

    async def _try_wake_on_lan(
        self,
        device: VirtualDevice,
        start_time: float
    ) -> Optional[ExecutionResult]:
        """
        Try to wake Sony Bravia TV using Wake-on-LAN

        Some Sony TVs support WOL, but it must be enabled in network settings
        """
        if not device.mac_address:
            return None  # No MAC, skip WOL attempt

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
                    "note": "Sony WOL support varies by model. TV may take 5-15 seconds to boot."
                }
            )

        except Exception as e:
            # WOL failed, but don't return error - let caller try IRCC
            return None
