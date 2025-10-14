"""
Sonos UPnP Command Executor

Handles command execution for Sonos speakers using UPnP/SOAP protocol via SoCo library.
Follows the same pattern as Bosch Plena Matrix executor.
"""

import asyncio
import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session

from soco import SoCo
from soco.exceptions import SoCoException

from app.commands.executors.base import CommandExecutor
from app.commands.models import Command, ExecutionResult
from app.models.virtual_controller import VirtualController, VirtualDevice


logger = logging.getLogger(__name__)


class SonosUPnPExecutor(CommandExecutor):
    """
    Command executor for Sonos speakers using UPnP/SOAP protocol.

    Supports commands:
    - set_volume: Set speaker volume (0-100)
    - set_mute: Mute/unmute speaker
    - play: Start playback
    - pause: Pause playback
    - stop: Stop playback
    - next: Skip to next track
    - previous: Go to previous track
    """

    def __init__(self, db: Session):
        super().__init__(db)
        # Cache SoCo speaker objects by IP address
        self._speakers: Dict[str, SoCo] = {}

    def can_execute(self, command: Command) -> bool:
        """
        Check if this executor can handle the command.

        Args:
            command: Command to check

        Returns:
            True if command is for a Sonos speaker
        """
        return (
            command.device_type == "audio_zone" and
            command.protocol == "sonos_upnp"
        )

    async def execute(self, command: Command) -> ExecutionResult:
        """
        Execute a Sonos command.

        Args:
            command: Command object from queue with:
                - controller_id: e.g., "sonos-192-168-1-100"
                - command: Command name (set_volume, play, etc.)
                - port: Speaker/zone number (always 1 for Sonos)
                - channel: Used for volume value (historical pattern)

        Returns:
            ExecutionResult with success status and data
        """
        try:
            # Step 1: Lookup VirtualController
            vc = self.db.query(VirtualController).filter(
                VirtualController.controller_id == command.controller_id
            ).first()

            if not vc:
                return ExecutionResult(
                    success=False,
                    message=f"Controller {command.controller_id} not found"
                )

            # Step 2: Get IP address from connection_config (CRITICAL!)
            connection_config = vc.connection_config or {}
            ip_address = connection_config.get("ip_address")

            if not ip_address:
                return ExecutionResult(
                    success=False,
                    message=f"No IP address in connection_config for {command.controller_id}"
                )

            # Step 3: Lookup VirtualDevice
            # Get parameters from command
            params = command.parameters or {}
            speaker_number = params.get('digit', 1)  # digit field contains zone number

            vd = self.db.query(VirtualDevice).filter(
                VirtualDevice.controller_id == vc.id,
                VirtualDevice.port_number == speaker_number
            ).first()

            if not vd:
                return ExecutionResult(
                    success=False,
                    message=f"Device not found: {command.controller_id} port {speaker_number}"
                )

            # Step 4: Get SoCo speaker object
            speaker = self._get_speaker(ip_address)

            # Step 5: Execute command
            cmd = command.command.lower()

            if cmd == "set_volume":
                # Volume value is stored in 'channel' parameter
                volume = int(params.get('channel', 50))
                return await self._set_volume(speaker, vd, volume)

            elif cmd == "set_mute":
                # channel contains "true" or "false" as string
                mute = params.get('channel') == "true" if params.get('channel') else True
                return await self._set_mute(speaker, vd, mute)

            elif cmd == "play":
                return await self._play(speaker, vd)

            elif cmd == "pause":
                return await self._pause(speaker, vd)

            elif cmd == "stop":
                return await self._stop(speaker, vd)

            elif cmd == "next":
                return await self._next_track(speaker, vd)

            elif cmd == "previous":
                return await self._previous_track(speaker, vd)

            else:
                return ExecutionResult(
                    success=False,
                    message=f"Unknown command: {cmd}"
                )

        except Exception as e:
            logger.error(f"Error executing Sonos command: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                message=f"Command execution failed: {str(e)}"
            )

    def _get_speaker(self, ip_address: str) -> SoCo:
        """
        Get or create SoCo speaker object (cached).

        Args:
            ip_address: Speaker IP address

        Returns:
            SoCo speaker object
        """
        if ip_address not in self._speakers:
            logger.info(f"Creating SoCo speaker object for {ip_address}")
            self._speakers[ip_address] = SoCo(ip_address)

        return self._speakers[ip_address]

    async def _set_volume(self, speaker: SoCo, zone: VirtualDevice, volume: int) -> ExecutionResult:
        """
        Set speaker volume.

        Args:
            speaker: SoCo speaker object
            zone: VirtualDevice database object
            volume: Target volume (0-100)

        Returns:
            ExecutionResult
        """
        try:
            # Validate volume
            if volume < 0 or volume > 100:
                return ExecutionResult(
                    success=False,
                    message=f"Volume must be 0-100, got {volume}"
                )

            logger.info(f"Setting {zone.device_name} volume to {volume}%")

            # Set volume (wrap sync call in executor)
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: setattr(speaker, 'volume', volume)
            )

            # Verify by reading back (cache-and-verify pattern)
            actual_volume = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: speaker.volume
            )

            # Update database cache
            zone.cached_volume_level = actual_volume
            zone.is_online = True
            self.db.commit()

            success = (actual_volume == volume)
            message = f"Set {zone.device_name} to {actual_volume}%"

            if not success:
                message += f" (requested {volume}%)"

            return ExecutionResult(
                success=True,  # Still success even if not exact
                message=message,
                data={
                    "volume": actual_volume,
                    "requested": volume,
                    "device_name": zone.device_name
                }
            )

        except SoCoException as e:
            logger.error(f"SoCo error setting volume: {e}")
            zone.is_online = False
            self.db.commit()
            return ExecutionResult(
                success=False,
                message=f"Failed to set volume: {str(e)}"
            )

        except Exception as e:
            logger.error(f"Error setting volume: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                message=f"Unexpected error: {str(e)}"
            )

    async def _set_mute(self, speaker: SoCo, zone: VirtualDevice, mute: bool) -> ExecutionResult:
        """
        Mute or unmute speaker.

        Args:
            speaker: SoCo speaker object
            zone: VirtualDevice database object
            mute: True to mute, False to unmute

        Returns:
            ExecutionResult
        """
        try:
            logger.info(f"{'Muting' if mute else 'Unmuting'} {zone.device_name}")

            # Set mute status
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: setattr(speaker, 'mute', mute)
            )

            # Verify by reading back
            actual_mute = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: speaker.mute
            )

            # Update database cache
            zone.cached_mute_status = actual_mute
            zone.is_online = True
            self.db.commit()

            return ExecutionResult(
                success=True,
                message=f"{zone.device_name} {'muted' if actual_mute else 'unmuted'}",
                data={
                    "mute": actual_mute,
                    "requested": mute,
                    "device_name": zone.device_name
                }
            )

        except SoCoException as e:
            logger.error(f"SoCo error setting mute: {e}")
            zone.is_online = False
            self.db.commit()
            return ExecutionResult(
                success=False,
                message=f"Failed to set mute: {str(e)}"
            )

        except Exception as e:
            logger.error(f"Error setting mute: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                message=f"Unexpected error: {str(e)}"
            )

    async def _play(self, speaker: SoCo, zone: VirtualDevice) -> ExecutionResult:
        """
        Start playback.

        Args:
            speaker: SoCo speaker object
            zone: VirtualDevice database object

        Returns:
            ExecutionResult
        """
        try:
            logger.info(f"Starting playback on {zone.device_name}")

            await asyncio.get_event_loop().run_in_executor(
                None,
                speaker.play
            )

            zone.is_online = True
            self.db.commit()

            return ExecutionResult(
                success=True,
                message=f"{zone.device_name} playing",
                data={"device_name": zone.device_name}
            )

        except SoCoException as e:
            logger.error(f"SoCo error starting playback: {e}")
            zone.is_online = False
            self.db.commit()
            return ExecutionResult(
                success=False,
                message=f"Failed to play: {str(e)}"
            )

    async def _pause(self, speaker: SoCo, zone: VirtualDevice) -> ExecutionResult:
        """
        Pause playback.

        Args:
            speaker: SoCo speaker object
            zone: VirtualDevice database object

        Returns:
            ExecutionResult
        """
        try:
            logger.info(f"Pausing playback on {zone.device_name}")

            await asyncio.get_event_loop().run_in_executor(
                None,
                speaker.pause
            )

            zone.is_online = True
            self.db.commit()

            return ExecutionResult(
                success=True,
                message=f"{zone.device_name} paused",
                data={"device_name": zone.device_name}
            )

        except SoCoException as e:
            logger.error(f"SoCo error pausing: {e}")
            zone.is_online = False
            self.db.commit()
            return ExecutionResult(
                success=False,
                message=f"Failed to pause: {str(e)}"
            )

    async def _stop(self, speaker: SoCo, zone: VirtualDevice) -> ExecutionResult:
        """
        Stop playback.

        Args:
            speaker: SoCo speaker object
            zone: VirtualDevice database object

        Returns:
            ExecutionResult
        """
        try:
            logger.info(f"Stopping playback on {zone.device_name}")

            await asyncio.get_event_loop().run_in_executor(
                None,
                speaker.stop
            )

            zone.is_online = True
            self.db.commit()

            return ExecutionResult(
                success=True,
                message=f"{zone.device_name} stopped",
                data={"device_name": zone.device_name}
            )

        except SoCoException as e:
            logger.error(f"SoCo error stopping: {e}")
            zone.is_online = False
            self.db.commit()
            return ExecutionResult(
                success=False,
                message=f"Failed to stop: {str(e)}"
            )

    async def _next_track(self, speaker: SoCo, zone: VirtualDevice) -> ExecutionResult:
        """
        Skip to next track.

        Args:
            speaker: SoCo speaker object
            zone: VirtualDevice database object

        Returns:
            ExecutionResult
        """
        try:
            logger.info(f"Skipping to next track on {zone.device_name}")

            await asyncio.get_event_loop().run_in_executor(
                None,
                speaker.next
            )

            zone.is_online = True
            self.db.commit()

            return ExecutionResult(
                success=True,
                message=f"{zone.device_name} skipped to next track",
                data={"device_name": zone.device_name}
            )

        except SoCoException as e:
            logger.error(f"SoCo error skipping track: {e}")
            zone.is_online = False
            self.db.commit()
            return ExecutionResult(
                success=False,
                message=f"Failed to skip track: {str(e)}"
            )

    async def _previous_track(self, speaker: SoCo, zone: VirtualDevice) -> ExecutionResult:
        """
        Go to previous track.

        Args:
            speaker: SoCo speaker object
            zone: VirtualDevice database object

        Returns:
            ExecutionResult
        """
        try:
            logger.info(f"Going to previous track on {zone.device_name}")

            await asyncio.get_event_loop().run_in_executor(
                None,
                speaker.previous
            )

            zone.is_online = True
            self.db.commit()

            return ExecutionResult(
                success=True,
                message=f"{zone.device_name} went to previous track",
                data={"device_name": zone.device_name}
            )

        except SoCoException as e:
            logger.error(f"SoCo error going to previous track: {e}")
            zone.is_online = False
            self.db.commit()
            return ExecutionResult(
                success=False,
                message=f"Failed to go to previous track: {str(e)}"
            )
