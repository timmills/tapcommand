"""
Hybrid Command Routing System

Implements class-based routing:
- Class A (Immediate): Direct only - diagnostic, health checks
- Class B (Interactive): Smart routing (direct first, queue fallback) - single device control
- Class C (Bulk): Queue only - multi-device operations
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import asyncio
import time

from ..db.database import get_db
from ..models.device import Device
from ..models.device_management import ManagedDevice
from ..models.virtual_controller import VirtualController
from ..services.esphome_client import esphome_manager
from ..services.command_queue import CommandQueueService
from ..services.settings_service import settings_service
from ..services.history_cleanup import get_cleanup_service

router = APIRouter(prefix="/commands", tags=["commands"])


# ============================================================================
# Pydantic Models
# ============================================================================

class CommandRequest(BaseModel):
    command: str
    box: Optional[int] = None
    port: Optional[int] = None  # Alias for box
    channel: Optional[str] = None
    digit: Optional[int] = None

    @property
    def effective_port(self) -> int:
        """Get the effective port number, preferring 'port' over 'box'"""
        return self.port if self.port is not None else (self.box if self.box is not None else 0)


class CommandResponse(BaseModel):
    success: bool
    method: str  # 'direct', 'queued', 'direct_failed_queued'
    message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    queue_id: Optional[int] = None


class BulkTarget(BaseModel):
    hostname: str
    port: int = 0


class BulkCommandRequest(BaseModel):
    targets: List[BulkTarget]
    command: str
    channel: Optional[str] = None
    digit: Optional[int] = None
    priority: Optional[int] = 5


class BulkCommandResponse(BaseModel):
    success: bool
    batch_id: str
    queued_count: int
    command_ids: List[int]


# ============================================================================
# Helper Functions
# ============================================================================

async def get_device_with_api_key(hostname: str, db: Session):
    """Get device and its API key"""
    device = db.query(Device).filter(Device.hostname == hostname).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {hostname} not found")

    api_key = None
    managed = db.query(ManagedDevice).filter(ManagedDevice.hostname == hostname).first()
    if managed and managed.api_key:
        api_key = managed.api_key
    if not api_key:
        api_key = settings_service.get_setting("esphome_api_key")

    return device, api_key


async def send_command_direct(
    hostname: str,
    ip_address: str,
    command: str,
    box: int,
    channel: Optional[str],
    digit: Optional[int],
    api_key: Optional[str],
    timeout: float = 5.0
) -> tuple[bool, int]:
    """
    Send command directly to device

    Returns:
        (success, execution_time_ms)
    """
    start_time = time.time()

    try:
        success = await asyncio.wait_for(
            esphome_manager.send_tv_command(
                hostname=hostname,
                ip_address=ip_address,
                command=command,
                box=box,
                channel=channel,
                digit=digit,
                api_key=api_key
            ),
            timeout=timeout
        )

        execution_time_ms = int((time.time() - start_time) * 1000)
        return success, execution_time_ms

    except asyncio.TimeoutError:
        execution_time_ms = int((time.time() - start_time) * 1000)
        return False, execution_time_ms


# ============================================================================
# Class A: IMMEDIATE (Direct Only)
# ============================================================================

@router.post("/{hostname}/diagnostic")
async def diagnostic_signal(hostname: str, db: Session = Depends(get_db)) -> CommandResponse:
    """
    Class A: Immediate - Diagnostic signal (ID button)

    Direct routing only, no queue fallback.
    User is waiting to see LED flash.
    """
    device, api_key = await get_device_with_api_key(hostname, db)

    success, execution_time_ms = await send_command_direct(
        hostname=device.hostname,
        ip_address=device.ip_address,
        command="diagnostic_signal",
        box=0,
        channel=None,
        digit=1,
        api_key=api_key,
        timeout=5.0
    )

    return CommandResponse(
        success=success,
        method="direct",
        message="Diagnostic signal sent" if success else "Failed to send diagnostic signal",
        execution_time_ms=execution_time_ms
    )


@router.get("/{hostname}/health")
async def health_check(hostname: str, db: Session = Depends(get_db)):
    """
    Class A: Immediate - Health check

    Direct routing only, no queue fallback.
    Quick connectivity test.
    """
    device, api_key = await get_device_with_api_key(hostname, db)

    client = esphome_manager.get_client(device.hostname, device.ip_address)
    if api_key:
        client.set_api_key(api_key)

    start_time = time.time()
    is_healthy = await client.health_check()
    execution_time_ms = int((time.time() - start_time) * 1000)

    return {
        "hostname": hostname,
        "healthy": is_healthy,
        "method": "direct",
        "execution_time_ms": execution_time_ms
    }


# ============================================================================
# Class B: INTERACTIVE (Smart Routing - Direct with Queue Fallback)
# ============================================================================

@router.post("/{hostname}/command")
async def send_command(
    hostname: str,
    command_request: CommandRequest,
    request: Request,
    db: Session = Depends(get_db)
) -> CommandResponse:
    """
    Class B: Interactive - Single device control

    Smart routing:
    1. Try direct execution first (fast path)
    2. If direct fails or times out, queue for retry

    Provides immediate feedback when possible, reliability when needed.
    """
    device, api_key = await get_device_with_api_key(hostname, db)

    # Try direct execution first (fast path)
    success, execution_time_ms = await send_command_direct(
        hostname=device.hostname,
        ip_address=device.ip_address,
        command=command_request.command,
        box=command_request.effective_port,
        channel=command_request.channel,
        digit=command_request.digit,
        api_key=api_key,
        timeout=3.0  # Short timeout for interactive commands
    )

    if success:
        # Direct execution succeeded - log to history and update port status
        port = command_request.effective_port

        # Update port status for channel changes (exclude port 0 - diagnostic only)
        if command_request.command == "channel" and command_request.channel and port != 0:
            CommandQueueService.update_port_status(
                db, device.hostname, port, channel=command_request.channel
            )

        # Update port status for power commands (exclude port 0 - diagnostic only)
        if command_request.command in ["power", "power_on", "power_off"] and port != 0:
            from ..models.command_queue import PortStatus
            from sqlalchemy import and_

            # Determine new power state
            if command_request.command == "power_on":
                new_state = 'on'
            elif command_request.command == "power_off":
                new_state = 'off'
            else:  # power (toggle)
                # Get current power state to toggle
                current_status = db.query(PortStatus).filter(
                    and_(
                        PortStatus.hostname == device.hostname,
                        PortStatus.port == port
                    )
                ).first()
                # Toggle: if currently 'on' -> 'off', else -> 'on'
                new_state = 'off' if (current_status and current_status.last_power_state == 'on') else 'on'

            CommandQueueService.update_port_status(
                db, device.hostname, port, power_state=new_state
            )

        # Log successful direct execution to history
        from ..models.command_queue import CommandHistory
        history = CommandHistory(
            queue_id=None,  # Not queued
            hostname=device.hostname,
            command=command_request.command,
            port=command_request.effective_port,
            channel=command_request.channel,
            success=True,
            execution_time_ms=execution_time_ms,
            routing_method="direct"
        )
        db.add(history)
        db.commit()

        return CommandResponse(
            success=True,
            method="direct",
            message=f"Command '{command_request.command}' executed successfully",
            execution_time_ms=execution_time_ms
        )

    # Direct failed - fallback to queue for retry
    queue_id = await CommandQueueService.enqueue(
        db=db,
        hostname=device.hostname,
        command=command_request.command,
        command_class="interactive",
        port=command_request.effective_port,
        channel=command_request.channel,
        digit=command_request.digit,
        priority=10,  # High priority for user-initiated commands
        max_attempts=3,
        user_ip=request.client.host if request.client else None,
        routing_method="direct_failed_queued"
    )

    return CommandResponse(
        success=True,
        method="direct_failed_queued",
        message=f"Device busy or offline. Command queued for retry (ID: {queue_id})",
        execution_time_ms=execution_time_ms,
        queue_id=queue_id
    )


# ============================================================================
# Class C: BULK (Queue Only)
# ============================================================================

@router.post("/bulk")
async def bulk_command(
    bulk_request: BulkCommandRequest,
    request: Request,
    db: Session = Depends(get_db)
) -> BulkCommandResponse:
    """
    Class C: Bulk - Multi-device operations

    Always queued. User expects progress tracking, not immediate completion.
    Provides reliability and coordination across multiple devices.
    """
    # Generate batch ID to group related commands
    batch_id = CommandQueueService.generate_batch_id()
    command_ids = []

    for target in bulk_request.targets:
        # Check if device exists in devices table or virtual_controllers table
        device = db.query(Device).filter(Device.hostname == target.hostname).first()

        # If not in devices table, check if it's a Virtual Controller
        if not device and target.hostname.startswith('nw-'):
            # Check virtual_controllers table
            vc = db.query(VirtualController).filter(
                VirtualController.controller_id == target.hostname
            ).first()

            if vc:
                # Create entry in devices table for tracking
                device = Device(
                    hostname=target.hostname,
                    mac_address=target.hostname,  # Use controller_id as placeholder
                    ip_address="0.0.0.0",  # Virtual controllers don't have single IP
                    device_type="network_tv",
                    friendly_name=vc.controller_name,
                    is_online=vc.is_online,
                    last_seen=vc.last_seen or datetime.now()
                )
                db.add(device)
                db.flush()

        if not device:
            # Skip non-existent devices but continue with others
            continue

        # Enqueue command
        queue_id = await CommandQueueService.enqueue(
            db=db,
            hostname=target.hostname,
            command=bulk_request.command,
            command_class="bulk",
            port=target.port,
            channel=bulk_request.channel,
            digit=bulk_request.digit,
            batch_id=batch_id,
            priority=bulk_request.priority or 5,
            max_attempts=3,
            user_ip=request.client.host if request.client else None,
            routing_method="queued"
        )
        command_ids.append(queue_id)

    return BulkCommandResponse(
        success=True,
        batch_id=batch_id,
        queued_count=len(command_ids),
        command_ids=command_ids
    )


@router.get("/bulk/{batch_id}/status")
async def bulk_status(batch_id: str, db: Session = Depends(get_db)):
    """
    Get status of a bulk operation

    Returns progress information for all commands in the batch.
    """
    status = CommandQueueService.get_batch_status(db, batch_id)
    return status


# ============================================================================
# Queue Status & Monitoring
# ============================================================================

@router.get("/queue/metrics")
async def queue_metrics(db: Session = Depends(get_db)):
    """Get queue health metrics"""
    metrics = CommandQueueService.get_queue_metrics(db)
    return metrics


@router.get("/{hostname}/port-status")
async def get_port_status(hostname: str, db: Session = Depends(get_db)):
    """
    Get last channel status for all ports of a device

    Returns format like: [{"port": 1, "last_channel": "500"}, ...]
    Displays as "1-500" in UI (port 1, channel 500)
    """
    device = db.query(Device).filter(Device.hostname == hostname).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    statuses = CommandQueueService.get_port_status(db, hostname)
    return {
        "hostname": hostname,
        "port_statuses": statuses
    }


@router.post("/maintenance/cleanup-history")
async def cleanup_history_now():
    """
    Manually trigger history cleanup

    Useful for testing or immediate cleanup needs.
    Normally runs automatically at 3:00 AM daily.
    """
    cleanup_service = get_cleanup_service()
    result = await cleanup_service.cleanup_now()

    return {
        "success": True,
        "message": "History cleanup completed",
        "history_deleted": result["history_deleted"],
        "queue_deleted": result["queue_deleted"]
    }


@router.get("/queue/all")
async def get_all_queue_data(
    status: Optional[str] = None,
    hostname: Optional[str] = None,
    command: Optional[str] = None,
    command_class: Optional[str] = None,
    limit: Optional[int] = 1000,
    db: Session = Depends(get_db)
):
    """
    Get all command queue data with optional filters for diagnostics

    Shows complete command lifecycle from command_queue table.

    Query parameters:
    - status: Filter by status (pending, processing, completed, failed)
    - hostname: Filter by device hostname
    - command: Filter by command type
    - command_class: Filter by command class (immediate, interactive, bulk, system)
    - limit: Maximum number of records to return (default 1000)
    """
    from ..models.command_queue import CommandQueue
    from ..models.device_management import IRPort
    from ..models.device import Channel
    from sqlalchemy import desc

    # Get device locations for enrichment
    devices = db.query(Device).all()
    device_map = {d.hostname: d for d in devices}

    managed_devices = db.query(ManagedDevice).all()
    managed_map = {md.hostname: md for md in managed_devices}

    # Get IR ports for port name lookup
    ir_ports = db.query(IRPort).all()
    # Create map: (device_id, port_number) -> port_name
    port_map = {}
    for ir_port in ir_ports:
        key = (ir_port.device_id, ir_port.port_number)
        port_map[key] = ir_port.connected_device_name

    # Get channels for channel name lookup
    channels = db.query(Channel).all()
    # Create map: lcn/foxtel_number -> channel_name
    channel_map = {}
    for ch in channels:
        # Map both LCN and Foxtel number to channel name
        if ch.lcn:
            channel_map[str(ch.lcn)] = ch.channel_name
        if ch.foxtel_number:
            channel_map[str(ch.foxtel_number)] = ch.channel_name

    # Query command_queue
    query = db.query(CommandQueue)

    # Apply filters
    if hostname:
        query = query.filter(CommandQueue.hostname == hostname)
    if command:
        query = query.filter(CommandQueue.command == command)
    if command_class:
        query = query.filter(CommandQueue.command_class == command_class)
    if status:
        query = query.filter(CommandQueue.status == status)

    # Order by most recent first and apply limit
    query = query.order_by(desc(CommandQueue.created_at))
    if limit:
        query = query.limit(limit)

    commands = query.all()

    # Format results
    results = []
    for cmd in commands:
        managed = managed_map.get(cmd.hostname)

        # Look up port name
        port_name = None
        if managed and cmd.port:
            port_key = (managed.id, cmd.port)
            port_name = port_map.get(port_key)

        # Look up channel name
        channel_name = None
        if cmd.channel:
            channel_name = channel_map.get(cmd.channel)

        results.append({
            "id": cmd.id,
            "source": "queue",
            "hostname": cmd.hostname,
            "device_name": managed.device_name if managed else cmd.hostname,
            "location": managed.location if managed else None,
            "command": cmd.command,
            "port": cmd.port,
            "port_name": port_name,
            "channel": cmd.channel,
            "channel_name": channel_name,
            "digit": cmd.digit,
            "command_class": cmd.command_class,
            "batch_id": cmd.batch_id,
            "status": cmd.status,
            "priority": cmd.priority,
            "scheduled_at": cmd.scheduled_at.isoformat() + 'Z' if cmd.scheduled_at else None,
            "attempts": cmd.attempts,
            "max_attempts": cmd.max_attempts,
            "last_attempt_at": cmd.last_attempt_at.isoformat() + 'Z' if cmd.last_attempt_at else None,
            "completed_at": cmd.completed_at.isoformat() + 'Z' if cmd.completed_at else None,
            "success": cmd.success,
            "error_message": cmd.error_message,
            "execution_time_ms": cmd.execution_time_ms,
            "routing_method": cmd.routing_method,
            "created_at": cmd.created_at.isoformat() + 'Z' if cmd.created_at else None,
            "created_by": cmd.created_by,
            "user_ip": cmd.user_ip,
            "notes": cmd.notes
        })

    return {
        "total": len(results),
        "commands": results
    }
