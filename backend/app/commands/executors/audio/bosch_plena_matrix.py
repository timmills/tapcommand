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
            elif command.command == "get_active_preset":
                return await self.get_active_preset(vc)
            # NOTE: PLM-4Px2x has NO hardware master volume/mute
            # Master volume commands removed - use individual zone controls only

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
                logger.info(f"DEBUG: set_volume - parameters={command.parameters}, volume={volume}")
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

    def _lut_index_to_db(self, lut_index: int) -> Optional[float]:
        """
        Convert DSP Volume LUT index to dB value

        DSP Volume LUT Block format (2 bytes):
        - Byte 1: LUT Index (0-249) where 0 = MUTE, 1-249 = -100.0dB to +24.0dB in 0.5dB steps
        - Byte 2: Flags (0x00 = unmuted, 0x01 = muted)

        Formula: dB = (lut_index - 1) * 0.5 - 100.0
        """
        if lut_index == 0:
            return None  # Mute
        return (lut_index - 1) * 0.5 - 100.0

    def _db_to_lut_index(self, db_value: float) -> int:
        """
        Convert dB value to DSP Volume LUT index

        Formula: lut_index = (dB + 100.0) / 0.5 + 1
        Range: 1-249 (0 is reserved for MUTE)
        """
        lut_index = int((db_value + 100.0) / 0.5 + 1)
        return max(1, min(249, lut_index))  # Clamp to valid range

    def _db_to_percent(self, db_value: Optional[float], gain_range: List[float] = [-80.0, 10.0]) -> int:
        """Convert dB to 0-100% scale"""
        if db_value is None:
            return 0
        min_db, max_db = gain_range
        return int(((db_value - min_db) / (max_db - min_db)) * 100)

    async def read_zone_volumes(self, controller: VirtualController) -> Dict[int, Dict[str, Any]]:
        """
        Read actual volume levels and mute states from device using SYNC Type 102

        SYNC Type 102 contains DSP parameters for all 4 zones.
        Zone output levels are located at fixed offsets with 15-byte spacing:
        - Zone 1 (BAR):     Offset 17 (bytes 17-18)
        - Zone 2 (POKIES):  Offset 32 (bytes 32-33)
        - Zone 3 (OUTSIDE): Offset 47 (bytes 47-48)
        - Zone 4 (BISTRO):  Offset 62 (bytes 62-63)

        Each output level is a 2-byte DSP Volume LUT Block:
        - Byte 1: LUT Index (volume)
        - Byte 2: Flags (mute state: 0x00=unmuted, 0x01=muted)

        Returns:
            Dict mapping zone_number (1-4) to {"volume_db", "volume_pct", "muted", "lut_index"}
        """
        # Send SYNC Type 102 command
        response = await self._send_command(controller, b'SYNC', struct.pack('B', 102))

        if not response or len(response) < 64:
            logger.error(f"Failed to read SYNC Type 102 from {controller.controller_name}")
            return {}

        # Parse output levels at fixed offsets
        zone_offsets = {
            1: 17,  # BAR (Ch1)
            2: 32,  # POKIES (Ch2)
            3: 47,  # OUTSIDE (Ch3)
            4: 62,  # BISTRO (Ch4)
        }

        volumes = {}
        for zone_number, offset in zone_offsets.items():
            if offset + 1 < len(response):
                lut_index = response[offset]
                flags = response[offset + 1]

                db_value = self._lut_index_to_db(lut_index)
                muted = (flags != 0x00)

                if db_value is not None:
                    volume_pct = self._db_to_percent(db_value)

                    volumes[zone_number] = {
                        "volume_db": round(db_value, 1),
                        "volume_pct": volume_pct,
                        "muted": muted,
                        "lut_index": lut_index,
                        "flags": flags
                    }

                    mute_str = " [MUTED]" if muted else ""
                    logger.debug(f"Zone {zone_number}: {db_value:.1f}dB ({volume_pct}%){mute_str}")
                else:
                    # LUT index 0 = MUTE
                    volumes[zone_number] = {
                        "volume_db": -100.0,
                        "volume_pct": 0,
                        "muted": True,
                        "lut_index": 0,
                        "flags": flags
                    }
                    logger.debug(f"Zone {zone_number}: MUTED (LUT=0)")

        return volumes

    async def sync_zone_volumes_from_device(self, controller: VirtualController) -> ExecutionResult:
        """
        Read actual volumes from device and update database cache

        This syncs the cached_volume_level and cached_mute_status in the database
        with the actual state on the device.
        """
        volumes = await self.read_zone_volumes(controller)

        if not volumes:
            return ExecutionResult(
                success=False,
                message=f"Failed to read volumes from {controller.controller_name}"
            )

        # Update database for each zone
        updated_zones = []
        for zone_number, volume_data in volumes.items():
            vd = self.db.query(VirtualDevice).filter(
                VirtualDevice.controller_id == controller.id,
                VirtualDevice.port_number == zone_number
            ).first()

            if vd:
                vd.cached_volume_level = volume_data["volume_pct"]
                vd.cached_mute_status = volume_data["muted"]
                updated_zones.append(f"{vd.device_name}: {volume_data['volume_pct']}% ({volume_data['volume_db']}dB)")

        self.db.commit()

        logger.info(f"✓ Synced volumes from device: {', '.join(updated_zones)}")

        return ExecutionResult(
            success=True,
            message=f"Synced {len(updated_zones)} zone volumes from device",
            data={"volumes": volumes, "updated_zones": updated_zones}
        )

    async def _set_volume(
        self,
        controller: VirtualController,
        zone: VirtualDevice,
        volume: int
    ) -> ExecutionResult:
        """
        Set volume (0-100 scale) on zone using POBJ command

        POBJ format:
        [POBJ][IsRead:1][PresetNumber:1][PresetObjectID:2][NV:1][Data:2][Checksum:1]
        """

        # Validate volume range
        if volume < 0 or volume > 100:
            return ExecutionResult(
                success=False,
                message=f"Volume must be 0-100, got {volume}"
            )

        # Get zone configuration
        zone_config = zone.connection_config or {}

        # Convert 0-100 volume to dB
        # Plena Matrix typical range: -80dB to +10dB
        gain_range = zone_config.get("gain_range", [-80.0, 10.0])
        min_db, max_db = gain_range
        db_value = min_db + (volume / 100.0) * (max_db - min_db)

        # Convert dB to LUT index
        lut_index = self._db_to_lut_index(db_value)

        # Zone to POBJ Object ID mapping
        zone_object_ids = {
            1: 26,   # POBJ_AMPCH1_CB_OUTPUTLEVEL (BAR)
            2: 52,   # POBJ_AMPCH2_CB_OUTPUTLEVEL (POKIES)
            3: 78,   # POBJ_AMPCH3_CB_OUTPUTLEVEL (OUTSIDE)
            4: 104   # POBJ_AMPCH4_CB_OUTPUTLEVEL (BISTRO)
        }

        preset_object_id = zone_object_ids[zone.port_number]

        logger.info(
            f"Setting {zone.device_name} to {volume}% ({db_value:.1f}dB, LUT={lut_index})"
        )

        # Build POBJ command with checksum
        command_data = (
            b'POBJ' +
            struct.pack('B', 0x00) +              # IsRead = write
            struct.pack('B', 0x00) +              # PresetNumber = live (0)
            struct.pack('>H', preset_object_id) + # Object ID (2 bytes big-endian)
            struct.pack('B', 0x00) +              # NV commit (RAM only)
            struct.pack('BB', lut_index, 0x00) +  # Data: LUT index + flags (unmuted)
            struct.pack('B', 0x00)                # Checksum
        )

        # Build UDP packet
        sock = self._get_socket(controller)
        seq = self._get_next_sequence(controller.controller_id)

        connection_config = controller.connection_config or {}
        ip_address = connection_config.get("ip_address")

        if not ip_address:
            return ExecutionResult(
                success=False,
                message=f"No IP address configured for {controller.controller_name}"
            )

        header = self._build_packet_header(seq, len(command_data))
        packet = header + command_data

        try:
            sock.sendto(packet, (ip_address, self.RECEIVE_PORT))
            response, _ = sock.recvfrom(1024)

            if len(response) >= 14:
                cmd = response[10:14]
                resp_data = response[14:]

                if cmd in [b'POBJ', b'ACKN']:
                    # Wait briefly for device to apply change
                    await asyncio.sleep(0.1)

                    # Verify the change by reading back
                    volumes = await self.read_zone_volumes(controller)
                    actual_volume = volumes.get(zone.port_number, {}).get("volume_pct", volume)

                    # Update cache with actual state
                    zone.cached_volume_level = actual_volume
                    self.db.commit()

                    verify_str = "" if abs(actual_volume - volume) <= 2 else f" (device shows: {actual_volume}%)"
                    logger.info(f"✓ Set {zone.device_name} to {volume}% ({db_value:.1f}dB){verify_str}")

                    return ExecutionResult(
                        success=True,
                        message=f"Set {zone.device_name} to {volume}% ({db_value:.1f}dB)",
                        data={
                            "volume": actual_volume,
                            "requested_volume": volume,
                            "db_value": round(db_value, 1),
                            "zone": zone.device_name
                        }
                    )
                elif cmd == b'NACK':
                    nack_code = struct.unpack('>I', resp_data[:4])[0] if len(resp_data) >= 4 else 0
                    logger.error(f"NACK received: 0x{nack_code:08x}")
                    return ExecutionResult(
                        success=False,
                        message=f"Device rejected volume change (NACK: 0x{nack_code:08x})"
                    )

            return ExecutionResult(
                success=False,
                message=f"No valid response from device"
            )

        except socket.timeout:
            return ExecutionResult(
                success=False,
                message=f"Timeout waiting for response from {zone.device_name}"
            )
        except Exception as e:
            logger.error(f"Volume set error: {e}")
            return ExecutionResult(
                success=False,
                message=f"Failed to set volume: {str(e)}"
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
        """
        Mute/unmute zone using POBJ command

        IMPORTANT: Must preserve current volume LUT when muting.
        First reads current volume via SYNC Type 102, then sends POBJ with
        preserved LUT + mute flag.

        POBJ format:
        [POBJ][IsRead:1][PresetNumber:1][PresetObjectID:2][NV:1][Data:2][Checksum:1]
        """

        # Step 1: Read current volume to preserve LUT
        volumes = await self.read_zone_volumes(controller)

        if not volumes or zone.port_number not in volumes:
            logger.error(f"Failed to read current volume for {zone.device_name}")
            return ExecutionResult(
                success=False,
                message=f"Failed to read current volume for {zone.device_name}"
            )

        current_lut = volumes[zone.port_number]["lut_index"]

        # Zone to POBJ Object ID mapping
        zone_object_ids = {
            1: 26,   # POBJ_AMPCH1_CB_OUTPUTLEVEL (BAR)
            2: 52,   # POBJ_AMPCH2_CB_OUTPUTLEVEL (POKIES)
            3: 78,   # POBJ_AMPCH3_CB_OUTPUTLEVEL (OUTSIDE)
            4: 104   # POBJ_AMPCH4_CB_OUTPUTLEVEL (BISTRO)
        }

        preset_object_id = zone_object_ids[zone.port_number]
        mute_flag = 0x01 if mute else 0x00

        logger.info(
            f"{'Muting' if mute else 'Unmuting'} {zone.device_name} (preserving LUT={current_lut})"
        )

        # Build POBJ command with checksum
        command_data = (
            b'POBJ' +
            struct.pack('B', 0x00) +              # IsRead = write
            struct.pack('B', 0x00) +              # PresetNumber = live (0)
            struct.pack('>H', preset_object_id) + # Object ID (2 bytes big-endian)
            struct.pack('B', 0x00) +              # NV commit (RAM only)
            struct.pack('BB', current_lut, mute_flag) +  # Data: LUT index + mute flag
            struct.pack('B', 0x00)                # Checksum
        )

        # Build UDP packet
        sock = self._get_socket(controller)
        seq = self._get_next_sequence(controller.controller_id)

        connection_config = controller.connection_config or {}
        ip_address = connection_config.get("ip_address")

        if not ip_address:
            return ExecutionResult(
                success=False,
                message=f"No IP address configured for {controller.controller_name}"
            )

        header = self._build_packet_header(seq, len(command_data))
        packet = header + command_data

        try:
            sock.sendto(packet, (ip_address, self.RECEIVE_PORT))
            response, _ = sock.recvfrom(1024)

            if len(response) >= 14:
                cmd = response[10:14]
                resp_data = response[14:]

                if cmd in [b'POBJ', b'ACKN']:
                    # Wait briefly for device to apply change
                    await asyncio.sleep(0.1)

                    # Verify the change by reading back
                    volumes = await self.read_zone_volumes(controller)
                    actual_mute = volumes.get(zone.port_number, {}).get("muted", mute)

                    # Update cache with actual state
                    zone.cached_mute_status = actual_mute
                    self.db.commit()

                    action = "Muted" if mute else "Unmuted"
                    verify_str = "" if actual_mute == mute else f" (device shows: {'muted' if actual_mute else 'unmuted'})"
                    logger.info(f"✓ {action} {zone.device_name}{verify_str}")

                    return ExecutionResult(
                        success=True,
                        message=f"{action} {zone.device_name}",
                        data={
                            "muted": actual_mute,
                            "requested_mute": mute,
                            "zone": zone.device_name
                        }
                    )
                elif cmd == b'NACK':
                    nack_code = struct.unpack('>I', resp_data[:4])[0] if len(resp_data) >= 4 else 0
                    logger.error(f"NACK received: 0x{nack_code:08x}")
                    return ExecutionResult(
                        success=False,
                        message=f"Device rejected mute change (NACK: 0x{nack_code:08x})"
                    )

            return ExecutionResult(
                success=False,
                message=f"No valid response from device"
            )

        except socket.timeout:
            return ExecutionResult(
                success=False,
                message=f"Timeout waiting for response from {zone.device_name}"
            )
        except Exception as e:
            logger.error(f"Mute set error: {e}")
            return ExecutionResult(
                success=False,
                message=f"Failed to set mute: {str(e)}"
            )

    async def _toggle_mute(
        self,
        controller: VirtualController,
        zone: VirtualDevice
    ) -> ExecutionResult:
        """Toggle mute state"""
        current_mute = zone.cached_mute_status or False
        return await self._set_mute(controller, zone, not current_mute)

    async def get_active_preset(
        self,
        controller: VirtualController
    ) -> ExecutionResult:
        """
        Read the currently active preset using GOBJ ID 10

        GOBJ_SYSTEM_CB_ACTIVEPRESET (Object ID 10):
        Returns the number of the currently active preset.

        Format:
        [GOBJ][IsRead:1][ObjectID:2]

        Returns:
            ExecutionResult with preset_number in data
        """
        logger.info(f"Reading active preset from {controller.controller_name}")

        # Build GOBJ command to read active preset (Object ID 10)
        command_data = (
            b'GOBJ' +
            struct.pack('B', 0x01) +    # IsRead = read
            struct.pack('<H', 10)       # Object ID 10 (little-endian)
        )

        # Build UDP packet
        sock = self._get_socket(controller)
        seq = self._get_next_sequence(controller.controller_id)

        connection_config = controller.connection_config or {}
        ip_address = connection_config.get("ip_address")

        if not ip_address:
            return ExecutionResult(
                success=False,
                message=f"No IP address configured for {controller.controller_name}"
            )

        header = self._build_packet_header(seq, len(command_data))
        packet = header + command_data

        try:
            sock.sendto(packet, (ip_address, self.RECEIVE_PORT))
            response, _ = sock.recvfrom(1024)

            if len(response) >= 14:
                cmd = response[10:14]
                resp_data = response[14:]

                if cmd == b'GOBJ' and len(resp_data) >= 1:
                    active_preset = resp_data[0]

                    # Get preset info from controller config
                    connection_config = controller.connection_config or {}
                    presets = connection_config.get("presets", [])

                    preset_name = f"Preset {active_preset}"
                    for preset in presets:
                        if preset.get("preset_number") == active_preset:
                            preset_name = preset.get("preset_name", preset_name)
                            break

                    logger.info(f"✓ Active preset: {preset_name} ({active_preset})")

                    return ExecutionResult(
                        success=True,
                        message=f"Active preset: {preset_name}",
                        data={
                            "preset_number": active_preset,
                            "preset_name": preset_name
                        }
                    )
                elif cmd == b'NACK':
                    nack_code = struct.unpack('>I', resp_data[:4])[0] if len(resp_data) >= 4 else 0
                    logger.error(f"NACK received: 0x{nack_code:08x}")
                    return ExecutionResult(
                        success=False,
                        message=f"Device rejected request (NACK: 0x{nack_code:08x})"
                    )

            return ExecutionResult(
                success=False,
                message=f"No valid response from device"
            )

        except socket.timeout:
            return ExecutionResult(
                success=False,
                message=f"Timeout waiting for response from {controller.controller_name}"
            )
        except Exception as e:
            logger.error(f"Get active preset error: {e}")
            return ExecutionResult(
                success=False,
                message=f"Failed to get active preset: {str(e)}"
            )

    async def recall_preset(
        self,
        controller: VirtualController,
        preset_number: int
    ) -> ExecutionResult:
        """
        Recall a saved preset on the controller using GOBJ ID 9

        GOBJ_SYSTEM_CB_RECALLPRESET (Object ID 9):
        Tells the PLENA Matrix to load all POBJ values stored in that preset
        into the "Live" preset area.

        Format:
        [GOBJ][IsRead:1][ObjectID:2][Data:1][Checksum:1]

        Args:
            controller: Virtual controller (amplifier)
            preset_number: Preset number (1-50)

        Returns:
            ExecutionResult with success/failure
        """
        # Validate preset number (1-50 per PLM-4Px2x spec)
        if preset_number < 1 or preset_number > 50:
            return ExecutionResult(
                success=False,
                message=f"Preset number must be 1-50, got {preset_number}"
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

        logger.info(f"Recalling preset {preset_number} on {controller.controller_name}")

        # Build GOBJ command to recall preset (Object ID 9)
        command_data = (
            b'GOBJ' +
            struct.pack('B', 0x00) +              # IsRead = write
            struct.pack('<H', 9) +                # Object ID 9 (little-endian)
            struct.pack('B', preset_number) +     # Preset number to recall (1-50)
            struct.pack('B', 0x00)                # Checksum
        )

        # Build UDP packet
        sock = self._get_socket(controller)
        seq = self._get_next_sequence(controller.controller_id)

        connection_config = controller.connection_config or {}
        ip_address = connection_config.get("ip_address")

        if not ip_address:
            return ExecutionResult(
                success=False,
                message=f"No IP address configured for {controller.controller_name}"
            )

        header = self._build_packet_header(seq, len(command_data))
        packet = header + command_data

        try:
            sock.sendto(packet, (ip_address, self.RECEIVE_PORT))
            response, _ = sock.recvfrom(1024)

            if len(response) >= 14:
                cmd = response[10:14]
                resp_data = response[14:]

                if cmd in [b'GOBJ', b'ACKN']:
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
                elif cmd == b'NACK':
                    nack_code = struct.unpack('>I', resp_data[:4])[0] if len(resp_data) >= 4 else 0
                    logger.error(f"NACK received: 0x{nack_code:08x}")
                    return ExecutionResult(
                        success=False,
                        message=f"Device rejected preset recall (NACK: 0x{nack_code:08x})"
                    )

            return ExecutionResult(
                success=False,
                message=f"No valid response from device"
            )

        except socket.timeout:
            return ExecutionResult(
                success=False,
                message=f"Timeout waiting for response from {controller.controller_name}"
            )
        except Exception as e:
            logger.error(f"Preset recall error: {e}")
            return ExecutionResult(
                success=False,
                message=f"Failed to recall preset: {str(e)}"
            )


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
