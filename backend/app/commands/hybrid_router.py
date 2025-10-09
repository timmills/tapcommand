"""
Hybrid Command Router
Implements hybrid IR + Network control strategy
"""

import asyncio
import time
from typing import Optional
from sqlalchemy.orm import Session

from .models import Command, ExecutionResult
from .executors.base import CommandExecutor
from .router import ProtocolRouter
from ..models.virtual_controller import VirtualDevice, VirtualController
from ..models.device_management import ManagedDevice
from ..services.esphome_client import esphome_manager


class HybridCommandRouter:
    """
    Routes commands using hybrid strategy:
    - Power-on: Use IR (if linked), fallback to network if no IR
    - Power-off: Prefer network (faster, status confirmation)
    - All other: Prefer network, fallback to IR if network fails

    This provides best of both worlds:
    - Reliable power-on (IR)
    - Fast network commands (volume, channels, etc.)
    - Status feedback (network)
    - Automatic fallback (IR if network fails)
    """

    def __init__(self, db: Session):
        self.db = db
        self.protocol_router = ProtocolRouter(db)

    async def execute_hybrid_command(
        self,
        device: VirtualDevice,
        command: str,
        **kwargs
    ) -> ExecutionResult:
        """
        Execute command using hybrid strategy

        Args:
            device: VirtualDevice instance
            command: Command to execute (e.g., "power_on", "volume_up")
            **kwargs: Additional command parameters

        Returns:
            ExecutionResult with success status and metadata
        """
        start_time = time.time()

        # Determine strategy based on command and device configuration
        if command in ["power", "power_on"]:
            return await self._execute_power_on(device, start_time, **kwargs)
        elif command == "power_off":
            return await self._execute_power_off(device, start_time, **kwargs)
        else:
            return await self._execute_standard_command(device, command, start_time, **kwargs)

    async def _execute_power_on(
        self,
        device: VirtualDevice,
        start_time: float,
        **kwargs
    ) -> ExecutionResult:
        """
        Execute power-on command using strategy defined in device.power_on_method

        Strategy priority:
        1. ir: Always use IR
        2. network: Try network only
        3. hybrid: Try network, fallback to IR
        """
        power_on_method = device.power_on_method or "network"

        if power_on_method == "ir":
            # Always use IR
            return await self._power_on_via_ir(device, start_time)

        elif power_on_method == "network":
            # Network only (no fallback)
            return await self._power_on_via_network(device, start_time)

        else:  # hybrid
            # Try network first, fallback to IR
            network_result = await self._power_on_via_network(device, start_time)

            if network_result.success:
                return network_result

            # Network failed, try IR
            if device.fallback_ir_controller:
                return await self._power_on_via_ir(device, start_time)
            else:
                # No IR fallback configured
                return ExecutionResult(
                    success=False,
                    message=f"Network power-on failed and no IR fallback configured",
                    error="NO_IR_FALLBACK",
                    data={
                        "execution_time_ms": int((time.time() - start_time) * 1000),
                        "device": device.device_name,
                        "attempted_methods": ["network"]
                    }
                )

    async def _execute_power_off(
        self,
        device: VirtualDevice,
        start_time: float,
        **kwargs
    ) -> ExecutionResult:
        """
        Execute power-off command

        Always prefer network (faster, status confirmation)
        Fallback to IR if network fails and hybrid enabled
        """
        # Try network first
        network_result = await self._send_network_command(device, "power_off", start_time)

        if network_result.success:
            return network_result

        # Network failed, try IR if hybrid enabled
        if device.control_strategy == "hybrid_ir_fallback" and device.fallback_ir_controller:
            return await self._send_ir_command(device, "power_off", start_time)

        return network_result  # Return network failure

    async def _execute_standard_command(
        self,
        device: VirtualDevice,
        command: str,
        start_time: float,
        **kwargs
    ) -> ExecutionResult:
        """
        Execute standard command (volume, channels, navigation, etc.)

        Strategy:
        - network_only: Network only, fail if doesn't work
        - hybrid_ir_fallback: Try network, fallback to IR
        - ir_only: IR only
        """
        control_strategy = device.control_strategy or "network_only"

        if control_strategy == "ir_only":
            return await self._send_ir_command(device, command, start_time, **kwargs)

        # Try network first
        network_result = await self._send_network_command(device, command, start_time, **kwargs)

        if network_result.success:
            return network_result

        # Network failed
        if control_strategy == "hybrid_ir_fallback" and device.fallback_ir_controller:
            # Fallback to IR
            return await self._send_ir_command(device, command, start_time, **kwargs)

        return network_result  # Return network failure

    async def _power_on_via_network(
        self,
        device: VirtualDevice,
        start_time: float
    ) -> ExecutionResult:
        """
        Attempt power-on via network (WOL or protocol-specific power-on)
        """
        # Get VirtualController to get controller_id
        vc = self.db.query(VirtualController).filter(VirtualController.id == device.controller_id).first()
        if not vc:
            return ExecutionResult(
                success=False,
                message=f"Virtual controller not found for device {device.device_name}",
                error="CONTROLLER_NOT_FOUND",
                data={"execution_time_ms": int((time.time() - start_time) * 1000)}
            )

        # Create command object for network executor
        cmd = Command(
            controller_id=vc.controller_id,
            device_type="network_tv",
            protocol=device.protocol,
            command="power_on",
            parameters=None
        )

        # Get appropriate executor
        executor = self.protocol_router.get_executor(cmd)

        if not executor:
            return ExecutionResult(
                success=False,
                message=f"No executor found for protocol {device.protocol}",
                error="NO_EXECUTOR",
                data={"execution_time_ms": int((time.time() - start_time) * 1000)}
            )

        # Execute command
        result = await executor.execute(cmd)

        # Add method used
        if result.data:
            result.data["method"] = "network"
        else:
            result.data = {"method": "network"}

        return result

    async def _power_on_via_ir(
        self,
        device: VirtualDevice,
        start_time: float
    ) -> ExecutionResult:
        """
        Power-on via IR controller
        """
        if not device.fallback_ir_controller or device.fallback_ir_port is None:
            return ExecutionResult(
                success=False,
                message="IR fallback not configured",
                error="NO_IR_FALLBACK",
                data={"execution_time_ms": int((time.time() - start_time) * 1000)}
            )

        return await self._send_ir_command(device, "power", start_time)

    async def _send_network_command(
        self,
        device: VirtualDevice,
        command: str,
        start_time: float,
        **kwargs
    ) -> ExecutionResult:
        """Send command via network executor"""

        # Get VirtualController to get controller_id
        vc = self.db.query(VirtualController).filter(VirtualController.id == device.controller_id).first()
        if not vc:
            return ExecutionResult(
                success=False,
                message=f"Virtual controller not found for device {device.device_name}",
                error="CONTROLLER_NOT_FOUND",
                data={"execution_time_ms": int((time.time() - start_time) * 1000)}
            )

        # Create command object
        cmd = Command(
            controller_id=vc.controller_id,
            device_type="network_tv",
            protocol=device.protocol,
            command=command,
            parameters=kwargs if kwargs else None
        )

        # Get executor
        executor = self.protocol_router.get_executor(cmd)

        if not executor:
            return ExecutionResult(
                success=False,
                message=f"No network executor for protocol {device.protocol}",
                error="NO_EXECUTOR",
                data={"execution_time_ms": int((time.time() - start_time) * 1000)}
            )

        # Execute
        result = await executor.execute(cmd)

        # Tag with method
        if result.data:
            result.data["method"] = "network"
            result.data["protocol"] = device.protocol
        else:
            result.data = {"method": "network", "protocol": device.protocol}

        return result

    async def _send_ir_command(
        self,
        device: VirtualDevice,
        command: str,
        start_time: float,
        **kwargs
    ) -> ExecutionResult:
        """Send command via IR controller"""

        if not device.fallback_ir_controller or device.fallback_ir_port is None:
            return ExecutionResult(
                success=False,
                message="IR fallback not configured",
                error="NO_IR_FALLBACK",
                data={"execution_time_ms": int((time.time() - start_time) * 1000)}
            )

        # Get IR controller details
        ir_controller = self.db.query(ManagedDevice).filter(
            ManagedDevice.hostname == device.fallback_ir_controller
        ).first()

        if not ir_controller:
            return ExecutionResult(
                success=False,
                message=f"IR controller {device.fallback_ir_controller} not found",
                error="IR_CONTROLLER_NOT_FOUND",
                data={"execution_time_ms": int((time.time() - start_time) * 1000)}
            )

        # Send IR command via ESPHome
        try:
            success = await asyncio.wait_for(
                esphome_manager.send_tv_command(
                    hostname=ir_controller.hostname,
                    ip_address=ir_controller.current_ip_address,
                    command=command,
                    box=device.fallback_ir_port,
                    channel=kwargs.get('channel'),
                    digit=kwargs.get('digit'),
                    api_key=ir_controller.api_key
                ),
                timeout=5.0
            )

            execution_time_ms = int((time.time() - start_time) * 1000)

            if success:
                return ExecutionResult(
                    success=True,
                    message=f"IR command {command} sent via {ir_controller.hostname} port {device.fallback_ir_port}",
                    data={
                        "execution_time_ms": execution_time_ms,
                        "method": "ir_fallback",
                        "ir_controller": ir_controller.hostname,
                        "ir_port": device.fallback_ir_port,
                        "device": device.device_name
                    }
                )
            else:
                return ExecutionResult(
                    success=False,
                    message=f"IR command failed",
                    error="IR_COMMAND_FAILED",
                    data={
                        "execution_time_ms": execution_time_ms,
                        "method": "ir_fallback",
                        "ir_controller": ir_controller.hostname,
                        "ir_port": device.fallback_ir_port
                    }
                )

        except asyncio.TimeoutError:
            return ExecutionResult(
                success=False,
                message="IR command timeout",
                error="IR_TIMEOUT",
                data={
                    "execution_time_ms": int((time.time() - start_time) * 1000),
                    "method": "ir_fallback"
                }
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"IR command error: {str(e)}",
                error="IR_ERROR",
                data={
                    "execution_time_ms": int((time.time() - start_time) * 1000),
                    "method": "ir_fallback",
                    "error_detail": str(e)
                }
            )

    def get_device_control_status(self, device: VirtualDevice) -> dict:
        """
        Get control status for a device

        Returns dict with:
        - network_available: bool
        - ir_fallback_configured: bool
        - power_on_method: str
        - control_strategy: str
        - recommended_power_on: str
        """
        # Check if network control available
        network_available = device.protocol is not None

        # Check IR fallback
        ir_fallback_configured = (
            device.fallback_ir_controller is not None and
            device.fallback_ir_port is not None
        )

        # Determine recommended power-on based on protocol
        recommended_power_on = "ir"  # Default recommendation

        if device.protocol == "roku":
            recommended_power_on = "network"  # Roku supports network power-on
        elif device.protocol in ["lg_webos", "hisense_vidaa"]:
            recommended_power_on = "hybrid"  # WOL may work
        elif device.protocol == "samsung_legacy":
            recommended_power_on = "ir"  # WOL doesn't work

        return {
            "network_available": network_available,
            "ir_fallback_configured": ir_fallback_configured,
            "power_on_method": device.power_on_method or "network",
            "control_strategy": device.control_strategy or "network_only",
            "recommended_power_on": recommended_power_on,
            "status_available": device.status_available or False,
            "protocol": device.protocol
        }
