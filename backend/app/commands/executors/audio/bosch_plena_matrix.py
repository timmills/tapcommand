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

    # Protocol IDs (from official API manual)
    PROTOCOL_ID_AMPLIFIER = 0x5E41  # PLM-4Px2x amplifiers
    PROTOCOL_ID_MATRIX = 0x5E40     # PLM-8M8 matrix mixer

    # Sub types
    SUBTYPE_MASTER = 0x0001   # Packets from master (us)
    SUBTYPE_SLAVE = 0x0100    # Packets from slave (device)

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
        """Execute audio zone or controller command"""

        # Get Virtual Controller
        vc = self.db.query(VirtualController).filter(
            VirtualController.controller_id == command.controller_id
        ).first()

        if not vc:
            return ExecutionResult(
                success=False,
                message=f"Audio controller {command.controller_id} not found"
            )

        # Execute command based on type
        try:
            # Controller-level commands
            if command.command == "recall_preset":
                preset_number = command.parameters.get("preset_number", 1) if command.parameters else 1
                return await self.recall_preset(vc, preset_number)
            elif command.command == "set_master_volume":
                volume = command.parameters.get("volume", 50) if command.parameters else 50
                return await self.set_master_volume(vc, volume)
            elif command.command == "master_volume_up":
                return await self.master_volume_up(vc)
            elif command.command == "master_volume_down":
                return await self.master_volume_down(vc)

            # Zone-level commands require a zone
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
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', self.TRANSMIT_PORT))  # Bind to port 12129 for receiving responses
            sock.settimeout(2.0)  # 2 second timeout
            self._sockets[controller_id] = sock
            self._sequence_numbers[controller_id] = 0
            logger.info(f"Created UDP socket for {controller.controller_name} (bound to port {self.TRANSMIT_PORT})")

        return self._sockets[controller_id]

    def _get_next_sequence(self, controller_id: str) -> int:
        """Get next sequence number for controller (1-65535, never 0)"""
        seq = self._sequence_numbers.get(controller_id, 0)
        seq = (seq + 1) % 65536
        if seq == 0:
            seq = 1
        self._sequence_numbers[controller_id] = seq
        return seq

    def _build_packet_header(self, sequence: int, chunk_length: int) -> bytes:
        """
        Build the 10-byte UDP packet header per Plena Matrix API spec

        Returns: [Protocol ID: 2][Sub Type: 2][Sequence: 2][Reserved: 2][Chunk Length: 2]
        """
        return struct.pack(
            '>HHHHH',
            self.PROTOCOL_ID_AMPLIFIER,  # Protocol ID for PLM-4Px2x
            self.SUBTYPE_MASTER,         # We are the master
            sequence,                     # Sequence number
            0x0000,                       # Reserved (always 0)
            chunk_length                  # Length of data after header
        )

    async def _send_command(
        self,
        controller: VirtualController,
        cmd_type: bytes,
        data: bytes = b''
    ) -> Optional[bytes]:
        """Send UDP command and wait for response"""

        sock = self._get_socket(controller)
        seq = self._get_next_sequence(controller.controller_id)

        # Get IP address from connection_config
        connection_config = controller.connection_config or {}
        ip_address = connection_config.get("ip_address")

        if not ip_address:
            logger.error(f"No IP address in connection_config for {controller.controller_name}")
            return None

        # Build packet: [10-byte header][4-byte command][data]
        command_data = cmd_type + data
        chunk_length = len(command_data)

        header = self._build_packet_header(seq, chunk_length)
        packet = header + command_data

        try:
            # Send packet to RECEIVE_PORT (12128)
            sock.sendto(packet, (ip_address, self.RECEIVE_PORT))
            logger.debug(f"Sent {cmd_type.decode()} to {ip_address}:{self.RECEIVE_PORT} ({len(packet)} bytes)")

            # Wait for response on TRANSMIT_PORT (12129)
            response, addr = sock.recvfrom(1024)
            logger.debug(f"Received {len(response)} bytes from {addr}")

            # Parse response header
            if len(response) >= 14:
                protocol_id, sub_type, seq_resp, reserved, resp_chunk_length = struct.unpack('>HHHHH', response[0:10])
                resp_cmd = response[10:14]
                resp_data = response[14:] if resp_chunk_length > 4 else b''

                logger.debug(f"Response: cmd={resp_cmd}, sub_type={hex(sub_type)}, data_len={len(resp_data)}")

                # Return just the data portion for convenience
                return resp_data

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
        """Set volume (0-100 scale) on zone using POBJ command"""

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

        # Build POBJ command to set preset volume
        # Format per API manual: [Preset Index: 1][Block ID: 1][Block Data Length: 1][Block Data]
        # For Volume LUT (Look-Up Table) block:
        # Block ID = 0x02, Data = 4-byte float (dB value)
        preset_index = zone_index  # Each zone maps to a preset
        block_id = 0x02  # Volume LUT block
        block_data = struct.pack('>f', db_value)  # 4-byte float dB value
        block_length = len(block_data)

        data = struct.pack('>BBB', preset_index, block_id, block_length) + block_data

        response = await self._send_command(controller, self.CMD_POBJ, data)

        if response is None:
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
        """Mute/unmute zone using POBJ command"""

        # Get zone configuration
        zone_config = zone.connection_config or {}
        zone_index = zone_config.get("zone_index", zone.port_number - 1)

        # Build POBJ command to set mute state
        # Format per API manual: [Preset Index: 1][Block ID: 1][Block Data Length: 1][Block Data]
        # For Mute block:
        # Block ID = 0x03, Data = 1 byte (0=unmuted, 1=muted)
        preset_index = zone_index  # Each zone maps to a preset
        block_id = 0x03  # Mute block
        mute_value = 1 if mute else 0
        block_data = struct.pack('B', mute_value)
        block_length = len(block_data)

        data = struct.pack('>BBB', preset_index, block_id, block_length) + block_data

        response = await self._send_command(controller, self.CMD_POBJ, data)

        if response is None:
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

    async def recall_preset(
        self,
        controller: VirtualController,
        preset_number: int
    ) -> ExecutionResult:
        """
        Recall a saved preset on the controller

        Args:
            controller: Virtual controller (amplifier)
            preset_number: Preset number (1-8 typically)

        Returns:
            ExecutionResult with success/failure
        """
        # Validate preset number
        if preset_number < 1 or preset_number > 8:
            return ExecutionResult(
                success=False,
                message=f"Preset number must be 1-8, got {preset_number}"
            )

        # Get preset info from controller config
        connection_config = controller.connection_config or {}
        presets = connection_config.get("presets", [])

        # Find the preset
        preset_info = None
        for preset in presets:
            if preset.get("preset_number") == preset_number:
                preset_info = preset
                break

        # Check if preset is valid
        if preset_info and not preset_info.get("is_valid", True):
            return ExecutionResult(
                success=False,
                message=f"Preset {preset_number} ({preset_info.get('preset_name', 'Unknown')}) is not active"
            )

        # Build POBJ command to recall preset
        # Format: [Preset Index: 1][Block ID: 1][Block Data Length: 1][Block Data]
        # For Preset Recall block:
        # Block ID = 0x01 (Preset Recall), Data = 1 byte (preset index)
        preset_index = preset_number - 1  # Convert to 0-based index
        block_id = 0x01  # Preset Recall block
        block_data = struct.pack('B', preset_index)
        block_length = len(block_data)

        data = struct.pack('>BBB', preset_index, block_id, block_length) + block_data

        response = await self._send_command(controller, self.CMD_POBJ, data)

        if response is None:
            return ExecutionResult(
                success=False,
                message=f"Failed to recall preset {preset_number}"
            )

        preset_name = preset_info.get("preset_name", f"Preset {preset_number}") if preset_info else f"Preset {preset_number}"
        logger.info(f"✓ Recalled preset: {preset_name}")

        return ExecutionResult(
            success=True,
            message=f"Recalled preset: {preset_name}",
            data={
                "preset_number": preset_number,
                "preset_name": preset_name
            }
        )

    async def set_master_volume(
        self,
        controller: VirtualController,
        volume: int
    ) -> ExecutionResult:
        """
        Set master volume on all zones simultaneously

        Args:
            controller: Virtual controller (amplifier)
            volume: Volume level 0-100

        Returns:
            ExecutionResult with success/failure
        """
        if volume < 0 or volume > 100:
            return ExecutionResult(
                success=False,
                message=f"Volume must be 0-100, got {volume}"
            )

        # Get all zones for this controller
        zones = self.db.query(VirtualDevice).filter(
            VirtualDevice.controller_id == controller.id,
            VirtualDevice.device_type == "audio_zone"
        ).all()

        if not zones:
            return ExecutionResult(
                success=False,
                message=f"No zones found for controller {controller.controller_name}"
            )

        # Set volume on each zone
        success_count = 0
        failed_zones = []

        for zone in zones:
            result = await self._set_volume(controller, zone, volume)
            if result.success:
                success_count += 1
            else:
                failed_zones.append(zone.device_name)

        if failed_zones:
            return ExecutionResult(
                success=False,
                message=f"Master volume partially set: {success_count}/{len(zones)} zones succeeded. Failed: {', '.join(failed_zones)}"
            )

        logger.info(f"✓ Set master volume to {volume}% on all {len(zones)} zones")

        return ExecutionResult(
            success=True,
            message=f"Set master volume to {volume}% on all {len(zones)} zones",
            data={
                "volume": volume,
                "zones_affected": len(zones)
            }
        )

    async def master_volume_up(self, controller: VirtualController) -> ExecutionResult:
        """Increase master volume on all zones by 5%"""

        # Get first zone to determine current volume (as a reference)
        first_zone = self.db.query(VirtualDevice).filter(
            VirtualDevice.controller_id == controller.id,
            VirtualDevice.device_type == "audio_zone"
        ).first()

        if not first_zone:
            return ExecutionResult(
                success=False,
                message=f"No zones found for controller {controller.controller_name}"
            )

        current_volume = first_zone.cached_volume_level or 50
        new_volume = min(100, current_volume + 5)

        return await self.set_master_volume(controller, new_volume)

    async def master_volume_down(self, controller: VirtualController) -> ExecutionResult:
        """Decrease master volume on all zones by 5%"""

        # Get first zone to determine current volume (as a reference)
        first_zone = self.db.query(VirtualDevice).filter(
            VirtualDevice.controller_id == controller.id,
            VirtualDevice.device_type == "audio_zone"
        ).first()

        if not first_zone:
            return ExecutionResult(
                success=False,
                message=f"No zones found for controller {controller.controller_name}"
            )

        current_volume = first_zone.cached_volume_level or 50
        new_volume = max(0, current_volume - 5)

        return await self.set_master_volume(controller, new_volume)

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
