"""
Bosch Praesensa AES70 Executor

Execute commands on Bosch Praesensa amplifiers via AES70/OMNEO protocol
"""

import asyncio
import logging
from typing import Optional, Dict, Any

# AES70 imports
try:
    from aes70 import tcp_connection, remote_device
    from aes70.types import OcaMuteState
    AES70_AVAILABLE = True
except ImportError:
    AES70_AVAILABLE = False
    logging.warning("AES70py not installed - audio control will not be available")

from ..base import CommandExecutor
from ...models import Command, CommandResult
from ....models.virtual_controller import VirtualController, VirtualDevice
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class BoschAES70Executor(CommandExecutor):
    """Execute commands on Bosch Praesensa via AES70 protocol"""

    def __init__(self, db: Session):
        self.db = db
        self._connections: Dict[str, remote_device.RemoteDevice] = {}  # Cache connections per controller

        if not AES70_AVAILABLE:
            logger.error("AES70py not installed - cannot create BoschAES70Executor")

    def can_execute(self, command: Command) -> bool:
        """Check if this executor can handle the command"""
        return (
            AES70_AVAILABLE and
            command.device_type == "audio_zone" and
            command.protocol == "bosch_aes70"
        )

    async def execute(self, command: Command) -> CommandResult:
        """Execute audio zone command"""

        if not AES70_AVAILABLE:
            return CommandResult(
                success=False,
                message="AES70py library not installed"
            )

        # Get Virtual Controller
        vc = self.db.query(VirtualController).filter(
            VirtualController.controller_id == command.controller_id
        ).first()

        if not vc:
            return CommandResult(
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
            return CommandResult(
                success=False,
                message=f"Zone {zone_number} not found for controller {command.controller_id}"
            )

        # Get or create AES70 connection
        device = await self._get_connection(vc)

        if not device:
            return CommandResult(
                success=False,
                message=f"Failed to connect to {vc.controller_name} at {vc.ip_address}"
            )

        # Execute command based on type
        try:
            if command.command == "volume_up":
                return await self._volume_up(device, vd)
            elif command.command == "volume_down":
                return await self._volume_down(device, vd)
            elif command.command == "set_volume":
                volume = command.parameters.get("volume", 50) if command.parameters else 50
                return await self._set_volume(device, vd, volume)
            elif command.command == "mute":
                return await self._mute(device, vd, True)
            elif command.command == "unmute":
                return await self._mute(device, vd, False)
            elif command.command == "toggle_mute":
                return await self._toggle_mute(device, vd)
            else:
                return CommandResult(
                    success=False,
                    message=f"Unknown command: {command.command}"
                )

        except Exception as e:
            logger.error(f"AES70 command error: {e}", exc_info=True)
            return CommandResult(
                success=False,
                message=f"AES70 error: {str(e)}"
            )

    async def _get_connection(self, controller: VirtualController) -> Optional[remote_device.RemoteDevice]:
        """Get or create AES70 connection to controller"""

        controller_id = controller.controller_id

        # Return cached connection if exists and is alive
        if controller_id in self._connections:
            try:
                # Test connection with a ping/keepalive
                device = self._connections[controller_id]
                # If device is still connected, return it
                return device
            except:
                # Connection dead, remove from cache
                logger.info(f"Cached connection to {controller_id} is dead, reconnecting...")
                del self._connections[controller_id]

        try:
            # Connect
            logger.info(f"Connecting to {controller.ip_address}:{controller.port or 65000}")
            connection = await tcp_connection.connect(
                ip_address=controller.ip_address,
                port=controller.port or 65000
            )

            device = remote_device.RemoteDevice(connection)
            device.set_keepalive_interval(10)

            # Cache connection
            self._connections[controller_id] = device

            logger.info(f"✓ Connected to {controller.controller_name}")
            return device

        except Exception as e:
            logger.error(f"Failed to connect to {controller.controller_name}: {e}")
            return None

    async def _set_volume(
        self,
        device: remote_device.RemoteDevice,
        zone: VirtualDevice,
        volume: int
    ) -> CommandResult:
        """Set volume (0-100 scale) on zone"""

        # Validate volume range
        if volume < 0 or volume > 100:
            return CommandResult(
                success=False,
                message=f"Volume must be 0-100, got {volume}"
            )

        # Get role map
        role_map = await device.get_role_map()

        # Get gain object from zone config
        role_path = zone.connection_config.get("role_path") if zone.connection_config else None
        if not role_path:
            return CommandResult(
                success=False,
                message=f"Zone {zone.device_name} has no role_path configured"
            )

        gain_obj = role_map.get(role_path)

        if not gain_obj:
            return CommandResult(
                success=False,
                message=f"Gain object not found at {role_path}"
            )

        # Convert 0-100 volume to dB
        gain_range = zone.connection_config.get("gain_range", [-80, 10]) if zone.connection_config else [-80, 10]
        min_db, max_db = gain_range
        db_value = min_db + (volume / 100.0) * (max_db - min_db)

        # Set gain
        await gain_obj.SetGain(db_value)

        # Update cache
        zone.cached_volume_level = volume
        self.db.commit()

        logger.info(f"✓ Set {zone.device_name} to {volume}% ({db_value:.1f}dB)")

        return CommandResult(
            success=True,
            message=f"Set {zone.device_name} to {volume}% ({db_value:.1f}dB)"
        )

    async def _volume_up(
        self,
        device: remote_device.RemoteDevice,
        zone: VirtualDevice
    ) -> CommandResult:
        """Increase volume by 5%"""
        current_volume = zone.cached_volume_level or 50
        new_volume = min(100, current_volume + 5)
        return await self._set_volume(device, zone, new_volume)

    async def _volume_down(
        self,
        device: remote_device.RemoteDevice,
        zone: VirtualDevice
    ) -> CommandResult:
        """Decrease volume by 5%"""
        current_volume = zone.cached_volume_level or 50
        new_volume = max(0, current_volume - 5)
        return await self._set_volume(device, zone, new_volume)

    async def _mute(
        self,
        device: remote_device.RemoteDevice,
        zone: VirtualDevice,
        mute: bool
    ) -> CommandResult:
        """Mute/unmute zone"""

        # Get role map
        role_map = await device.get_role_map()

        # Get mute object from zone config
        mute_path = zone.connection_config.get("mute_path") if zone.connection_config else None
        if not mute_path:
            return CommandResult(
                success=False,
                message=f"Zone {zone.device_name} does not support mute (no mute_path)"
            )

        mute_obj = role_map.get(mute_path)
        if not mute_obj:
            return CommandResult(
                success=False,
                message=f"Mute object not found at {mute_path}"
            )

        # Set mute state
        new_state = OcaMuteState.Muted if mute else OcaMuteState.Unmuted
        await mute_obj.SetState(new_state)

        # Update cache
        zone.cached_mute_status = mute
        self.db.commit()

        action = "Muted" if mute else "Unmuted"
        logger.info(f"✓ {action} {zone.device_name}")

        return CommandResult(
            success=True,
            message=f"{action} {zone.device_name}"
        )

    async def _toggle_mute(
        self,
        device: remote_device.RemoteDevice,
        zone: VirtualDevice
    ) -> CommandResult:
        """Toggle mute state"""
        current_mute = zone.cached_mute_status or False
        return await self._mute(device, zone, not current_mute)

    async def cleanup(self):
        """Close all connections"""
        for controller_id, device in self._connections.items():
            try:
                await device.connection.close()
                logger.info(f"Closed connection to {controller_id}")
            except:
                pass
        self._connections.clear()
