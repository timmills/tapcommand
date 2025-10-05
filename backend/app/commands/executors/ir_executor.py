"""
IR Command Executor

Executes commands for IR controllers (ESPHome-based devices)
"""

import asyncio
import time
from typing import Optional
from sqlalchemy.orm import Session

from .base import CommandExecutor
from ..models import Command, ExecutionResult
from ...models.device import ManagedDevice
from ...services.esphome import esphome_manager


class IRExecutor(CommandExecutor):
    """
    Executor for IR/ESP-based controllers

    Sends commands via ESPHome API to IR blaster devices
    """

    def can_execute(self, command: Command) -> bool:
        """Check if this is an IR controller"""
        return command.device_type in ["universal", "ir"]

    async def execute(self, command: Command) -> ExecutionResult:
        """
        Execute IR command via ESPHome

        Args:
            command: Command object with controller_id, command, parameters

        Returns:
            ExecutionResult with success status
        """
        start_time = time.time()

        try:
            # Get the managed device from database
            device = self.db.query(ManagedDevice).filter_by(
                hostname=command.controller_id
            ).first()

            if not device:
                return ExecutionResult(
                    success=False,
                    message=f"IR Controller {command.controller_id} not found",
                    error="DEVICE_NOT_FOUND"
                )

            # Extract parameters
            params = command.parameters or {}
            port = params.get("port", 1)
            channel = params.get("channel")
            digit = params.get("digit")

            # Send command via ESPHome
            success = await asyncio.wait_for(
                esphome_manager.send_tv_command(
                    hostname=device.hostname,
                    ip_address=device.current_ip_address,
                    command=command.command,
                    box=port,
                    channel=channel,
                    digit=digit,
                    api_key=device.api_key
                ),
                timeout=5.0  # 5 second timeout
            )

            execution_time_ms = int((time.time() - start_time) * 1000)

            if success:
                return ExecutionResult(
                    success=True,
                    message=f"IR command '{command.command}' sent successfully",
                    data={
                        "execution_time_ms": execution_time_ms,
                        "device": device.hostname,
                        "port": port
                    }
                )
            else:
                return ExecutionResult(
                    success=False,
                    message=f"IR command '{command.command}' failed",
                    error="COMMAND_FAILED",
                    data={"execution_time_ms": execution_time_ms}
                )

        except asyncio.TimeoutError:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                message=f"IR command '{command.command}' timed out",
                error="TIMEOUT",
                data={"execution_time_ms": execution_time_ms}
            )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                message=f"IR command '{command.command}' failed: {str(e)}",
                error=str(e),
                data={"execution_time_ms": execution_time_ms}
            )
