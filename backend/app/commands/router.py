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
from .executors.network import SamsungLegacyExecutor, LGWebOSExecutor, RokuExecutor


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
            # Samsung Legacy (pre-2016)
            if command.protocol == "samsung_legacy":
                return SamsungLegacyExecutor(self.db)

            # Samsung Modern (2016+ Tizen)
            elif command.protocol == "samsung_websocket":
                # TODO: Implement SamsungWebSocketExecutor
                return None

            # LG webOS
            elif command.protocol == "lg_webos":
                return LGWebOSExecutor(self.db)

            # Sony Bravia
            elif command.protocol == "sony_bravia":
                # TODO: Implement SonyBraviaExecutor
                return None

            # Roku
            elif command.protocol == "roku":
                return RokuExecutor(self.db)

            # Android TV
            elif command.protocol == "android_tv":
                # TODO: Implement AndroidTVExecutor
                return None

            # Philips JointSpace
            elif command.protocol == "philips_jointspace":
                # TODO: Implement PhilipsExecutor
                return None

            # Vizio SmartCast
            elif command.protocol == "vizio_smartcast":
                # TODO: Implement VizioExecutor
                return None

        # No executor found
        return None

    def can_route(self, command: Command) -> bool:
        """Check if command can be routed to an executor"""
        executor = self.get_executor(command)
        return executor is not None and executor.can_execute(command)
