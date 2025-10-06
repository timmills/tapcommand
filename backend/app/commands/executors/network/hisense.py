"""
Hisense TV Executor

For Hisense TVs with VIDAA OS using MQTT protocol on port 36669
Supports both network commands and Wake-on-LAN for power-on
"""

import time
import ssl
from typing import Optional
from sqlalchemy.orm import Session

from ..base import CommandExecutor
from ...models import Command, ExecutionResult
from ....models.virtual_controller import VirtualController, VirtualDevice


class HisenseExecutor(CommandExecutor):
    """
    Executor for Hisense TVs (VIDAA OS)

    Protocol: MQTT over TCP port 36669
    Authentication: Username/password (hisenseservice/multimqttservice)
    Notes:
    - Some models require SSL, others require --no-ssl
    - First-time use requires authorization on TV screen
    - Power-on requires Wake-on-LAN (WOL) as TV enters deep sleep
    """

    # Command mapping to Hisense KEY codes
    KEY_MAP = {
        # Power
        "power": "KEY_POWER",
        "power_on": "KEY_POWER",  # WOL will be used first
        "power_off": "KEY_POWER",

        # Volume
        "volume_up": "KEY_VOLUMEUP",
        "volume_down": "KEY_VOLUMEDOWN",
        "mute": "KEY_MUTE",

        # Channels
        "channel_up": "KEY_CHANNELUP",
        "channel_down": "KEY_CHANNELDOWN",

        # Navigation
        "up": "KEY_UP",
        "down": "KEY_DOWN",
        "left": "KEY_LEFT",
        "right": "KEY_RIGHT",
        "ok": "KEY_OK",
        "enter": "KEY_OK",
        "select": "KEY_OK",

        # Menu/System
        "menu": "KEY_MENU",
        "home": "KEY_HOME",
        "back": "KEY_RETURNS",
        "return": "KEY_RETURNS",
        "exit": "KEY_EXIT",

        # Playback
        "play": "KEY_PLAY",
        "pause": "KEY_PAUSE",
        "stop": "KEY_STOP",
        "fast_forward": "KEY_FORWARDS",
        "rewind": "KEY_BACK",
        "subtitle": "KEY_SUBTITLE",

        # Number keys
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

        # Sources (direct input selection)
        "source_0": "SOURCE_0",
        "source_1": "SOURCE_1",
        "source_2": "SOURCE_2",
        "source_3": "SOURCE_3",
        "source_4": "SOURCE_4",
        "source_5": "SOURCE_5",
        "source_6": "SOURCE_6",
        "source_7": "SOURCE_7",
    }

    def can_execute(self, command: Command) -> bool:
        """Check if this is a Hisense TV"""
        return (
            command.device_type == "network_tv" and
            command.protocol == "hisense_vidaa"
        )

    async def execute(self, command: Command) -> ExecutionResult:
        """Execute command on Hisense TV"""
        start_time = time.time()

        try:
            # Get Virtual Device from database
            device = self.db.query(VirtualDevice).join(VirtualController).filter(
                VirtualController.controller_id == command.controller_id
            ).first()

            if not device:
                return ExecutionResult(
                    success=False,
                    message=f"Hisense TV {command.controller_id} not found",
                    error="DEVICE_NOT_FOUND"
                )

            # Special handling for power_on: Try WOL first
            if command.command.lower() in ["power_on", "poweron"]:
                wol_result = await self._try_wake_on_lan(device, start_time)
                if wol_result:
                    return wol_result
                # If WOL not available, fall through to regular power command

            # Send command via MQTT
            return await self._send_mqtt_command(device, command, start_time)

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                message=f"Hisense command '{command.command}' failed: {str(e)}",
                error=str(e),
                data={"execution_time_ms": execution_time_ms}
            )

    async def _send_mqtt_command(
        self,
        device: VirtualDevice,
        command: Command,
        start_time: float
    ) -> ExecutionResult:
        """Send command to Hisense TV via MQTT"""
        try:
            import hisensetv

            # Get the KEY code for this command
            key = self.KEY_MAP.get(command.command.lower())
            if not key:
                # Try direct KEY_ format
                key = f"KEY_{command.command.upper()}"

            # Check if we should use SSL
            # Some models require SSL, others need no-ssl
            # Default to trying without SSL first (more reliable)
            ssl_context = None  # Try without SSL first

            # Connect to TV
            tv = hisensetv.HisenseTv(
                hostname=device.ip_address,
                port=36669,
                username="hisenseservice",
                password="multimqttservice",
                timeout=5.0,
                ssl_context=ssl_context
            )

            # Context manager handles connection
            with tv:
                # Handle special commands
                if key.startswith("SOURCE_"):
                    # Direct source selection
                    source_num = key.split("_")[1]
                    tv._change_source(source_num)
                else:
                    # Regular key press
                    tv.send_key(key)

            execution_time_ms = int((time.time() - start_time) * 1000)

            return ExecutionResult(
                success=True,
                message=f"Hisense command '{command.command}' sent successfully",
                data={
                    "execution_time_ms": execution_time_ms,
                    "device": device.device_name,
                    "ip": device.ip_address,
                    "key": key,
                    "protocol": "mqtt"
                }
            )

        except Exception as e:
            # If SSL error, could retry with SSL enabled
            error_str = str(e).lower()
            if "ssl" in error_str or "certificate" in error_str:
                # Try with SSL
                try:
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE

                    tv = hisensetv.HisenseTv(
                        hostname=device.ip_address,
                        port=36669,
                        username="hisenseservice",
                        password="multimqttservice",
                        timeout=5.0,
                        ssl_context=ssl_context
                    )

                    with tv:
                        if key.startswith("SOURCE_"):
                            source_num = key.split("_")[1]
                            tv._change_source(source_num)
                        else:
                            tv.send_key(key)

                    execution_time_ms = int((time.time() - start_time) * 1000)

                    return ExecutionResult(
                        success=True,
                        message=f"Hisense command '{command.command}' sent successfully (SSL)",
                        data={
                            "execution_time_ms": execution_time_ms,
                            "device": device.device_name,
                            "ip": device.ip_address,
                            "key": key,
                            "protocol": "mqtt_ssl"
                        }
                    )
                except Exception as ssl_error:
                    raise ssl_error

            # Re-raise original error if not SSL related
            raise

    async def _try_wake_on_lan(
        self,
        device: VirtualDevice,
        start_time: float
    ) -> Optional[ExecutionResult]:
        """
        Try to wake Hisense TV using Wake-on-LAN

        Returns ExecutionResult if WOL was attempted, None if MAC not configured
        """
        if not device.mac_address:
            # No MAC address configured, can't use WOL
            return None

        try:
            from wakeonlan import send_magic_packet

            # Hisense TVs may need multiple WOL packets
            # Send 16 packets for reliability
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
                    "note": "Hisense WOL may be unreliable. TV may take 5-15 seconds to boot. "
                            "Ensure WOL is enabled in TV network settings."
                }
            )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                message=f"Failed to send WOL packets: {str(e)}",
                error=str(e),
                data={
                    "execution_time_ms": execution_time_ms,
                    "recommendation": "Use IR control for reliable power-on, or enable WOL in TV settings"
                }
            )
