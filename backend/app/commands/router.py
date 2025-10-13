"""
Command Protocol Router

Determines which executor should handle a command based on
device type and protocol.
"""

from sqlalchemy.orm import Session
from typing import Optional

from .models import Command
from .executors.base import CommandExecutor
from .executors.ir_executor import IRExecutor
from .executors.network import (
    SamsungLegacyExecutor,
    LGWebOSExecutor,
    RokuExecutor,
    HisenseExecutor,
    SonyBraviaExecutor,
    VizioExecutor,
    PhilipsExecutor
)
from .executors.audio import BoschAES70Executor, BoschPlenaMatrixExecutor


class ProtocolRouter:
    """
    Routes commands to the appropriate executor

    Examines command's device_type and protocol to select
    the correct executor implementation.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_executor(self, command: Command) -> Optional[CommandExecutor]:
        """
        Get the appropriate executor for a command

        Args:
            command: Command to route

        Returns:
            CommandExecutor instance or None if no executor found
        """

        # IR Controllers (ESPHome-based)
        if command.device_type in ["universal", "ir"]:
            return IRExecutor(self.db)

        # Network TV Controllers
        if command.device_type == "network_tv":
            # Samsung TVs (both legacy and modern WebSocket)
            if command.protocol in ["samsung_legacy", "samsung_websocket"]:
                return SamsungLegacyExecutor(self.db)

            # LG webOS
            elif command.protocol == "lg_webos":
                return LGWebOSExecutor(self.db)

            # Sony Bravia
            elif command.protocol == "sony_bravia":
                return SonyBraviaExecutor(self.db)

            # Roku
            elif command.protocol == "roku":
                return RokuExecutor(self.db)

            # Hisense VIDAA
            elif command.protocol == "hisense_vidaa":
                return HisenseExecutor(self.db)

            # Android TV
            elif command.protocol == "android_tv":
                # TODO: Implement AndroidTVExecutor
                return None

            # Philips JointSpace
            elif command.protocol == "philips_jointspace":
                return PhilipsExecutor(self.db)

            # Vizio SmartCast
            elif command.protocol == "vizio_smartcast":
                return VizioExecutor(self.db)

        # Audio Zone Controllers and Audio Controllers (controller-level commands)
        if command.device_type in ["audio_zone", "audio"]:
            if command.protocol == "bosch_aes70":
                return BoschAES70Executor(self.db)
            elif command.protocol == "bosch_plena_matrix":
                return BoschPlenaMatrixExecutor(self.db)

        # No executor found
        return None

    def can_route(self, command: Command) -> bool:
        """Check if command can be routed to an executor"""
        executor = self.get_executor(command)
        return executor is not None and executor.can_execute(command)
