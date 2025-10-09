"""
Bosch Plena Matrix UDP Executor

Execute commands on Bosch Plena Matrix amplifiers via UDP API
PLM-4Px2x series: PLM-4P220, PLM-4P120, etc.

Protocol: UDP
- Receive port: 12128
- Transmit port: 12129

Reference: PLENA matrix API Operation Manual
"""

import asyncio
import logging
import struct
import socket
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from ..base import CommandExecutor
from ...models import Command, ExecutionResult
from ....models.virtual_controller import VirtualController, VirtualDevice
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class PlenaMatrixCommand:
    """Plena Matrix UDP command packet"""
    command_type: str
    sequence_number: int = 0
    data: bytes = b''


class BoschPlenaMatrixExecutor(CommandExecutor):
    """Execute commands on Bosch Plena Matrix via UDP API"""

    # UDP Ports
    RECEIVE_PORT = 12128
    TRANSMIT_PORT = 12129

    # Command packet types
    CMD_PING = b'PING'
    CMD_WHAT = b'WHAT'
    CMD_GOBJ = b'GOBJ'  # Global Object Read/Write
    CMD_POBJ = b'POBJ'  # Preset Object Read/Write
    CMD_SMON = b'SMON'  # Signal Monitoring

    # Object types for gain/volume control
    OBJ_TYPE_INPUT_GAIN = 0x01
    OBJ_TYPE_OUTPUT_GAIN = 0x02
    OBJ_TYPE_ZONE_GAIN = 0x03
    OBJ_TYPE_MUTE = 0x10

    def __init__(self, db: Session):
        self.db = db
        self._sockets: Dict[str, socket.socket] = {}  # Cache UDP sockets per controller
        self._sequence_numbers: Dict[str, int] = {}  # Track sequence numbers per controller

    def can_execute(self, command: Command) -> bool:
        """Check if this executor can handle the command"""
        return (
            command.device_type == "audio_zone" and
            command.protocol == "bosch_plena_matrix"
        )

    async def execute(self, command: Command) -> ExecutionResult:
        """Execute audio zone command"""

        # Get Virtual Controller
        vc = self.db.query(VirtualController).filter(
            VirtualController.controller_id == command.controller_id
        ).first()

        if not vc:
            return ExecutionResult(
                success=False,
                message=f"Audio controller {command.controller_id} not found"
            )

        # Get zone number from parameters
        zone_number = command.parameters.get("zone_number", 1) if command.parameters else 1

        # Get Virtual Device (zone)
        vd = self.db.query(VirtualDevice).filter(
            VirtualDevice.controller_id == vc.id,
            VirtualDevice.port_number == zone_number
        ).first()

        if not vd:
            return ExecutionResult(
                success=False,
                message=f"Zone {zone_number} not found for controller {command.controller_id}"
            )

        # Execute command based on type
        try:
            if command.command == "volume_up":
                return await self._volume_up(vc, vd)
            elif command.command == "volume_down":
                return await self._volume_down(vc, vd)
            elif command.command == "set_volume":
                volume = command.parameters.get("volume", 50) if command.parameters else 50
                return await self._set_volume(vc, vd, volume)
            elif command.command == "mute":
                return await self._set_mute(vc, vd, True)
            elif command.command == "unmute":
                return await self._set_mute(vc, vd, False)
            elif command.command == "toggle_mute":
                return await self._toggle_mute(vc, vd)
            else:
                return ExecutionResult(
                    success=False,
                    message=f"Unknown command: {command.command}"
                )

        except Exception as e:
            logger.error(f"Plena Matrix command error: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                message=f"Plena Matrix error: {str(e)}"
            )

    def _get_socket(self, controller: VirtualController) -> socket.socket:
        """Get or create UDP socket for controller"""

        controller_id = controller.controller_id

        if controller_id not in self._sockets:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)  # 2 second timeout
            self._sockets[controller_id] = sock
            self._sequence_numbers[controller_id] = 0
            logger.info(f"Created UDP socket for {controller.controller_name}")

        return self._sockets[controller_id]

    def _get_next_sequence(self, controller_id: str) -> int:
        """Get next sequence number for controller"""
        seq = self._sequence_numbers.get(controller_id, 0)
        self._sequence_numbers[controller_id] = (seq + 1) % 65536
        return seq

    async def _send_command(
        self,
        controller: VirtualController,
        cmd_type: bytes,
        data: bytes = b''
    ) -> Optional[bytes]:
        """Send UDP command and wait for response"""

        sock = self._get_socket(controller)
        seq = self._get_next_sequence(controller.controller_id)

        # Build packet: [CMD_TYPE(4)][SEQ(2)][LENGTH(2)][DATA]
        length = len(data)
        packet = cmd_type + struct.pack('>HH', seq, length) + data

        try:
            # Send packet
            sock.sendto(packet, (controller.ip_address, self.RECEIVE_PORT))
            logger.debug(f"Sent {cmd_type.decode()} to {controller.ip_address}:{self.RECEIVE_PORT}")

            # Wait for response
            response, addr = sock.recvfrom(1024)
            logger.debug(f"Received {len(response)} bytes from {addr}")

            return response

        except socket.timeout:
            logger.warning(f"Timeout waiting for response from {controller.controller_name}")
            return None
        except Exception as e:
            logger.error(f"UDP communication error: {e}")
            return None

    async def _ping(self, controller: VirtualController) -> bool:
        """Ping controller to check if alive"""
        response = await self._send_command(controller, self.CMD_PING)
        return response is not None

    async def _set_volume(
        self,
        controller: VirtualController,
        zone: VirtualDevice,
        volume: int
    ) -> ExecutionResult:
        """Set volume (0-100 scale) on zone"""

        # Validate volume range
        if volume < 0 or volume > 100:
            return ExecutionResult(
                success=False,
                message=f"Volume must be 0-100, got {volume}"
            )

        # Get zone configuration
        zone_config = zone.connection_config or {}
        zone_index = zone_config.get("zone_index", zone.port_number - 1)

        # Convert 0-100 volume to dB
        # Plena Matrix typical range: -80dB to +10dB
        gain_range = zone_config.get("gain_range", [-80.0, 10.0])
        min_db, max_db = gain_range
        db_value = min_db + (volume / 100.0) * (max_db - min_db)

        # Build GOBJ command to set zone gain
        # Format: [OBJECT_TYPE(1)][OBJECT_INDEX(2)][VALUE(4 bytes float)]
        data = struct.pack('>BHf', self.OBJ_TYPE_ZONE_GAIN, zone_index, db_value)

        response = await self._send_command(controller, self.CMD_GOBJ, data)

        if not response:
            return ExecutionResult(
                success=False,
                message=f"Failed to set volume on {zone.device_name}"
            )

        # Update cache
        zone.cached_volume_level = volume
        self.db.commit()

        logger.info(f"✓ Set {zone.device_name} to {volume}% ({db_value:.1f}dB)")

        return ExecutionResult(
            success=True,
            message=f"Set {zone.device_name} to {volume}% ({db_value:.1f}dB)",
            data={
                "volume": volume,
                "db_value": round(db_value, 1),
                "zone": zone.device_name
            }
        )

    async def _volume_up(
        self,
        controller: VirtualController,
        zone: VirtualDevice
    ) -> ExecutionResult:
        """Increase volume by 5%"""
        current_volume = zone.cached_volume_level or 50
        new_volume = min(100, current_volume + 5)
        return await self._set_volume(controller, zone, new_volume)

    async def _volume_down(
        self,
        controller: VirtualController,
        zone: VirtualDevice
    ) -> ExecutionResult:
        """Decrease volume by 5%"""
        current_volume = zone.cached_volume_level or 50
        new_volume = max(0, current_volume - 5)
        return await self._set_volume(controller, zone, new_volume)

    async def _set_mute(
        self,
        controller: VirtualController,
        zone: VirtualDevice,
        mute: bool
    ) -> ExecutionResult:
        """Mute/unmute zone"""

        # Get zone configuration
        zone_config = zone.connection_config or {}
        zone_index = zone_config.get("zone_index", zone.port_number - 1)

        # Build GOBJ command to set mute state
        # Format: [OBJECT_TYPE(1)][OBJECT_INDEX(2)][VALUE(1 byte bool)]
        mute_value = 1 if mute else 0
        data = struct.pack('>BHB', self.OBJ_TYPE_MUTE, zone_index, mute_value)

        response = await self._send_command(controller, self.CMD_GOBJ, data)

        if not response:
            return ExecutionResult(
                success=False,
                message=f"Failed to set mute on {zone.device_name}"
            )

        # Update cache
        zone.cached_mute_status = mute
        self.db.commit()

        action = "Muted" if mute else "Unmuted"
        logger.info(f"✓ {action} {zone.device_name}")

        return ExecutionResult(
            success=True,
            message=f"{action} {zone.device_name}",
            data={
                "muted": mute,
                "zone": zone.device_name
            }
        )

    async def _toggle_mute(
        self,
        controller: VirtualController,
        zone: VirtualDevice
    ) -> ExecutionResult:
        """Toggle mute state"""
        current_mute = zone.cached_mute_status or False
        return await self._set_mute(controller, zone, not current_mute)

    async def cleanup(self):
        """Close all UDP sockets"""
        for controller_id, sock in self._sockets.items():
            try:
                sock.close()
                logger.info(f"Closed UDP socket for {controller_id}")
            except:
                pass
        self._sockets.clear()
        self._sequence_numbers.clear()
