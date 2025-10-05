"""
Command Queue Manager

Processes commands from the database queue, routes them to executors,
and updates command status.
"""

import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .models import Command, CommandStatus, CommandRequest, CommandResponse, ExecutionResult
from .router import ProtocolRouter


class QueueManager:
    """
    Manages the command queue

    Handles:
    - Creating new commands
    - Executing commands synchronously
    - Updating command status
    - Retrieving command results
    """

    def __init__(self, db: Session):
        self.db = db
        self.router = ProtocolRouter(db)

    async def enqueue_command(
        self,
        request: CommandRequest
    ) -> CommandResponse:
        """
        Enqueue and execute a command synchronously

        Args:
            request: CommandRequest with controller_id, command, parameters

        Returns:
            CommandResponse with execution results
        """

        # Generate unique command ID
        command_id = str(uuid.uuid4())

        # Look up controller to determine device_type and protocol
        device_info = await self._get_device_info(request.controller_id)

        if not device_info:
            # Create a failed command record
            failed_command = Command(
                command_id=command_id,
                controller_id=request.controller_id,
                device_type="unknown",
                protocol=None,
                command=request.command,
                parameters=request.parameters,
                status=CommandStatus.FAILED,
                priority=request.priority,
                error_message=f"Controller {request.controller_id} not found"
            )
            self.db.add(failed_command)
            self.db.commit()
            self.db.refresh(failed_command)

            return CommandResponse.model_validate(failed_command)

        # Create command in database
        command = Command(
            command_id=command_id,
            controller_id=request.controller_id,
            device_type=device_info["device_type"],
            protocol=device_info.get("protocol"),
            command=request.command,
            parameters=request.parameters,
            status=CommandStatus.QUEUED,
            priority=request.priority
        )

        self.db.add(command)
        self.db.commit()
        self.db.refresh(command)

        # Execute command synchronously
        result = await self._execute_command(command)

        # Update command with results
        command.status = CommandStatus.COMPLETED if result.success else CommandStatus.FAILED
        command.started_at = datetime.now()
        command.completed_at = datetime.now()
        command.result_data = result.data
        command.error_message = result.error if not result.success else None

        self.db.commit()
        self.db.refresh(command)

        return CommandResponse.model_validate(command)

    async def _execute_command(self, command: Command) -> ExecutionResult:
        """
        Execute a command using the appropriate executor

        Args:
            command: Command to execute

        Returns:
            ExecutionResult with success status and data
        """

        # Update status to EXECUTING
        command.status = CommandStatus.EXECUTING
        command.started_at = datetime.now()
        self.db.commit()

        # Get executor from router
        executor = self.router.get_executor(command)

        if not executor:
            return ExecutionResult(
                success=False,
                message=f"No executor found for device_type={command.device_type}, protocol={command.protocol}",
                error="NO_EXECUTOR"
            )

        # Execute command
        try:
            result = await executor.execute(command)
            return result
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Executor error: {str(e)}",
                error=str(e)
            )

    async def _get_device_info(self, controller_id: str) -> Optional[dict]:
        """
        Get device type and protocol for a controller

        Args:
            controller_id: Controller ID (e.g., 'ir-dc4516' or 'nw-b85a97')

        Returns:
            Dict with device_type and protocol, or None if not found
        """

        # Check if it's an IR controller (managed device)
        if controller_id.startswith("ir-") or not controller_id.startswith("nw-"):
            from ..models.device import Device

            device = self.db.query(Device).filter_by(
                hostname=controller_id
            ).first()

            if device:
                return {
                    "device_type": "universal",  # or "ir"
                    "protocol": None  # IR doesn't need protocol specification
                }

        # Check if it's a Virtual Controller (network TV)
        if controller_id.startswith("nw-"):
            from ..models.virtual_controller import VirtualController

            controller = self.db.query(VirtualController).filter_by(
                controller_id=controller_id
            ).first()

            if controller:
                return {
                    "device_type": "network_tv",
                    "protocol": controller.protocol  # samsung_legacy, roku, etc.
                }

        return None

    def get_command(self, command_id: str) -> Optional[CommandResponse]:
        """
        Get a command by ID

        Args:
            command_id: UUID of the command

        Returns:
            CommandResponse or None if not found
        """

        command = self.db.query(Command).filter_by(
            command_id=command_id
        ).first()

        if command:
            return CommandResponse.model_validate(command)
        return None

    def get_recent_commands(
        self,
        controller_id: Optional[str] = None,
        limit: int = 50
    ) -> List[CommandResponse]:
        """
        Get recent commands

        Args:
            controller_id: Optional filter by controller
            limit: Max number of commands to return

        Returns:
            List of CommandResponse objects
        """

        query = self.db.query(Command)

        if controller_id:
            query = query.filter_by(controller_id=controller_id)

        commands = query.order_by(
            Command.created_at.desc()
        ).limit(limit).all()

        return [CommandResponse.model_validate(cmd) for cmd in commands]

    def get_failed_commands(
        self,
        controller_id: Optional[str] = None,
        limit: int = 50
    ) -> List[CommandResponse]:
        """
        Get failed commands for troubleshooting

        Args:
            controller_id: Optional filter by controller
            limit: Max number of commands to return

        Returns:
            List of failed CommandResponse objects
        """

        query = self.db.query(Command).filter_by(
            status=CommandStatus.FAILED
        )

        if controller_id:
            query = query.filter_by(controller_id=controller_id)

        commands = query.order_by(
            Command.created_at.desc()
        ).limit(limit).all()

        return [CommandResponse.model_validate(cmd) for cmd in commands]
