"""
Schedules API Router

Endpoints for managing scheduled commands/actions
"""

from datetime import datetime
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from croniter import croniter

from ..db.database import get_db
from ..models.device import Schedule, ScheduleExecution
from ..models.device_management import ManagedDevice, IRPort, DeviceTag
from ..services.command_queue import CommandQueueService
from ..services.schedule_processor import schedule_processor


router = APIRouter(tags=["schedules"])


# === Pydantic Schemas ===


class ScheduleActionSchema(BaseModel):
    """Schema for a single action in a schedule"""

    type: str = Field(..., description="Action type: power, mute, volume_up, volume_down, channel, default_channel")
    value: Optional[str] = Field(None, description="Value for action (e.g., channel ID for channel action)")
    repeat: Optional[int] = Field(None, ge=1, le=10, description="Number of times to repeat (for volume actions)")
    wait_after: Optional[int] = Field(None, ge=0, description="Seconds to wait after this action")


class ScheduleTargetSchema(BaseModel):
    """Schema for schedule targets"""

    type: str = Field(..., description="Target type: all, selection, tag, location")
    device_ids: Optional[List[int]] = Field(None, description="List of IRPort IDs (for selection)")
    tag_ids: Optional[List[int]] = Field(None, description="List of tag IDs (for tag)")
    locations: Optional[List[str]] = Field(None, description="List of locations (for location)")


class CreateScheduleRequest(BaseModel):
    """Request schema for creating a schedule"""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    cron_expression: str = Field(..., description="Cron expression (e.g., '0 8 * * 1-5')")
    target_type: str = Field(..., description="all, selection, tag, or location")
    target_data: Optional[dict] = Field(None, description="Target data based on type")
    actions: List[ScheduleActionSchema] = Field(..., min_items=1, max_items=4)
    is_active: bool = True


class UpdateScheduleRequest(BaseModel):
    """Request schema for updating a schedule"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    cron_expression: Optional[str] = None
    target_type: Optional[str] = None
    target_data: Optional[dict] = None
    actions: Optional[List[ScheduleActionSchema]] = Field(None, min_items=1, max_items=4)
    is_active: Optional[bool] = None


class ScheduleResponse(BaseModel):
    """Response schema for a schedule"""

    id: int
    name: str
    description: Optional[str]
    cron_expression: str
    target_type: str
    target_data: Optional[dict]
    actions: List[dict]
    is_active: bool
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScheduleListResponse(BaseModel):
    """Response schema for list of schedules"""

    schedules: List[ScheduleResponse]
    total: int


class ScheduleExecutionResponse(BaseModel):
    """Response schema for a schedule execution"""

    id: int
    schedule_id: int
    batch_id: str
    executed_at: datetime
    total_commands: Optional[int]
    succeeded: Optional[int]
    failed: Optional[int]
    avg_execution_time_ms: Optional[int]

    class Config:
        from_attributes = True


class RunNowResponse(BaseModel):
    """Response schema for manual schedule trigger"""

    batch_id: str
    queued_count: int
    command_ids: List[int]


# === Helper Functions ===


def validate_cron_expression(cron_expr: str) -> bool:
    """Validate cron expression"""
    try:
        croniter(cron_expr)
        return True
    except Exception:
        return False


def calculate_next_run(cron_expr: str) -> datetime:
    """Calculate next run time from cron expression"""
    cron = croniter(cron_expr, datetime.now())
    return cron.get_next(datetime)


def resolve_targets(db: Session, schedule: Schedule) -> List[IRPort]:
    """Resolve target devices based on schedule target_type"""
    if schedule.target_type == "all":
        return db.query(IRPort).filter(IRPort.is_active == True).all()

    elif schedule.target_type == "selection":
        device_ids = schedule.target_data.get("device_ids", []) if schedule.target_data else []
        return db.query(IRPort).filter(IRPort.id.in_(device_ids)).all()

    elif schedule.target_type == "tag":
        tag_ids = schedule.target_data.get("tag_ids", []) if schedule.target_data else []
        # Find all IRPorts that have ANY of these tags
        ports = db.query(IRPort).filter(IRPort.is_active == True).all()
        matching_ports = []
        for port in ports:
            if port.tag_ids:
                port_tag_list = port.tag_ids if isinstance(port.tag_ids, list) else []
                if any(tag_id in port_tag_list for tag_id in tag_ids):
                    matching_ports.append(port)
        return matching_ports

    elif schedule.target_type == "location":
        locations = schedule.target_data.get("locations", []) if schedule.target_data else []
        return (
            db.query(IRPort)
            .join(ManagedDevice)
            .filter(ManagedDevice.location.in_(locations))
            .filter(IRPort.is_active == True)
            .all()
        )

    return []


# === API Endpoints ===


@router.post("/", response_model=ScheduleResponse, status_code=201)
async def create_schedule(request: CreateScheduleRequest, db: Session = Depends(get_db)):
    """Create a new schedule"""

    # Validate cron expression
    if not validate_cron_expression(request.cron_expression):
        raise HTTPException(status_code=400, detail="Invalid cron expression")

    # Validate actions
    valid_action_types = {"power", "mute", "volume_up", "volume_down", "channel", "default_channel"}
    for action in request.actions:
        if action.type not in valid_action_types:
            raise HTTPException(status_code=400, detail=f"Invalid action type: {action.type}")

    # Calculate next run
    next_run = calculate_next_run(request.cron_expression)

    # Create schedule
    schedule = Schedule(
        name=request.name,
        description=request.description,
        cron_expression=request.cron_expression,
        target_type=request.target_type,
        target_data=request.target_data,
        actions=[action.model_dump() for action in request.actions],
        is_active=request.is_active,
        next_run=next_run,
    )

    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    # Notify schedule processor to add this schedule
    if request.is_active:
        await schedule_processor.add_schedule(schedule)

    return schedule


@router.get("/", response_model=ScheduleListResponse)
def list_schedules(
    active_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List all schedules"""

    query = db.query(Schedule)

    if active_only:
        query = query.filter(Schedule.is_active == True)

    total = query.count()
    schedules = query.order_by(Schedule.created_at.desc()).limit(limit).offset(offset).all()

    return {"schedules": schedules, "total": total}


@router.get("/upcoming", response_model=List[ScheduleResponse])
def get_upcoming_schedules(limit: int = 5, db: Session = Depends(get_db)):
    """Get upcoming schedules ordered by next_run"""

    schedules = (
        db.query(Schedule)
        .filter(Schedule.is_active == True)
        .filter(Schedule.next_run.isnot(None))
        .order_by(Schedule.next_run.asc())
        .limit(limit)
        .all()
    )

    return schedules


@router.get("/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Get a specific schedule"""

    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return schedule


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(schedule_id: int, request: UpdateScheduleRequest, db: Session = Depends(get_db)):
    """Update a schedule"""

    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Update fields
    if request.name is not None:
        schedule.name = request.name

    if request.description is not None:
        schedule.description = request.description

    if request.cron_expression is not None:
        if not validate_cron_expression(request.cron_expression):
            raise HTTPException(status_code=400, detail="Invalid cron expression")
        schedule.cron_expression = request.cron_expression
        schedule.next_run = calculate_next_run(request.cron_expression)

    if request.target_type is not None:
        schedule.target_type = request.target_type

    if request.target_data is not None:
        schedule.target_data = request.target_data

    if request.actions is not None:
        # Validate actions
        valid_action_types = {"power", "mute", "volume_up", "volume_down", "channel", "default_channel"}
        for action in request.actions:
            if action.type not in valid_action_types:
                raise HTTPException(status_code=400, detail=f"Invalid action type: {action.type}")
        schedule.actions = [action.model_dump() for action in request.actions]

    if request.is_active is not None:
        schedule.is_active = request.is_active

    db.commit()
    db.refresh(schedule)

    # Notify schedule processor to update this schedule
    if schedule.is_active:
        await schedule_processor.update_schedule(schedule)
    else:
        await schedule_processor.remove_schedule(schedule_id)

    return schedule


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Delete a schedule"""

    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Remove from schedule processor
    await schedule_processor.remove_schedule(schedule_id)

    db.delete(schedule)
    db.commit()

    return {"success": True, "message": "Schedule deleted"}


@router.patch("/{schedule_id}/toggle", response_model=ScheduleResponse)
async def toggle_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Toggle schedule active status"""

    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    schedule.is_active = not schedule.is_active
    db.commit()
    db.refresh(schedule)

    # Update schedule processor
    if schedule.is_active:
        await schedule_processor.add_schedule(schedule)
    else:
        await schedule_processor.remove_schedule(schedule_id)

    return schedule


@router.post("/{schedule_id}/run", response_model=RunNowResponse)
async def run_schedule_now(schedule_id: int, db: Session = Depends(get_db)):
    """Manually trigger a schedule to run now"""

    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Resolve targets
    targets = resolve_targets(db, schedule)

    if not targets:
        raise HTTPException(status_code=400, detail="No target devices found for this schedule")

    # Generate batch ID
    batch_id = f"manual_{schedule_id}_{uuid.uuid4().hex[:8]}"

    # Enqueue actions
    queued_count = 0
    command_ids = []

    for action in schedule.actions:
        action_type = action.get("type")
        action_value = action.get("value")
        action_repeat = action.get("repeat", 1)

        for target in targets:
            # Get device hostname
            device = db.query(ManagedDevice).filter(ManagedDevice.id == target.device_id).first()
            if not device:
                continue

            # Handle volume repeat
            if action_type in ("volume_up", "volume_down") and action_repeat > 1:
                for _ in range(action_repeat):
                    queue_id = await CommandQueueService.enqueue(
                        db,
                        device.hostname,
                        action_type,
                        "system",
                        port=target.port_number,
                        batch_id=batch_id,
                        priority=5,  # Medium priority for manual runs
                        routing_method="manual_schedule",
                    )
                    command_ids.append(queue_id)
                    queued_count += 1
            else:
                # Single command
                queue_id = await CommandQueueService.enqueue(
                    db,
                    device.hostname,
                    action_type,
                    "system",
                    port=target.port_number,
                    channel=action_value if action_type == "channel" else None,
                    batch_id=batch_id,
                    priority=5,
                    routing_method="manual_schedule",
                )
                command_ids.append(queue_id)
                queued_count += 1

    # Log execution
    execution = ScheduleExecution(
        schedule_id=schedule_id,
        batch_id=batch_id,
        total_commands=queued_count,
    )
    db.add(execution)
    db.commit()

    return {"batch_id": batch_id, "queued_count": queued_count, "command_ids": command_ids}


@router.get("/{schedule_id}/history", response_model=List[ScheduleExecutionResponse])
def get_schedule_history(schedule_id: int, limit: int = 10, offset: int = 0, db: Session = Depends(get_db)):
    """Get execution history for a schedule"""

    executions = (
        db.query(ScheduleExecution)
        .filter(ScheduleExecution.schedule_id == schedule_id)
        .order_by(ScheduleExecution.executed_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return executions
