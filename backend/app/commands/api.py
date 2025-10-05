"""
Unified Command API

Single endpoint for all device commands (IR and Network)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from ..db.database import get_db
from .models import CommandRequest, CommandResponse
from .queue import QueueManager

router = APIRouter(prefix="/api/commands", tags=["commands"])


@router.post("/execute", response_model=CommandResponse)
async def execute_command(
    request: CommandRequest,
    db: Session = Depends(get_db)
):
    """
    Execute a command on any device (IR or Network)

    This is the unified endpoint that routes commands to the appropriate
    executor based on the controller_id.

    Examples:
        IR Controller:
            POST /api/commands/execute
            {
                "controller_id": "ir-dc4516",
                "command": "power",
                "parameters": {"port": 1}
            }

        Network TV (Samsung):
            POST /api/commands/execute
            {
                "controller_id": "nw-b85a97",
                "command": "volume_up"
            }

        Network TV (Roku):
            POST /api/commands/execute
            {
                "controller_id": "nw-a1b2c3",
                "command": "home"
            }
    """

    queue_manager = QueueManager(db)

    try:
        result = await queue_manager.enqueue_command(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Command execution failed: {str(e)}"
        )


@router.get("/{command_id}", response_model=CommandResponse)
async def get_command(
    command_id: str,
    db: Session = Depends(get_db)
):
    """
    Get command details by ID

    Args:
        command_id: UUID of the command

    Returns:
        CommandResponse with execution results
    """

    queue_manager = QueueManager(db)
    command = queue_manager.get_command(command_id)

    if not command:
        raise HTTPException(
            status_code=404,
            detail=f"Command {command_id} not found"
        )

    return command


@router.get("/recent/{controller_id}", response_model=List[CommandResponse])
async def get_recent_commands(
    controller_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get recent commands for a controller

    Args:
        controller_id: Controller ID to filter by
        limit: Maximum number of commands to return (default 50)

    Returns:
        List of CommandResponse objects
    """

    queue_manager = QueueManager(db)
    commands = queue_manager.get_recent_commands(
        controller_id=controller_id,
        limit=limit
    )

    return commands


@router.get("/recent", response_model=List[CommandResponse])
async def get_all_recent_commands(
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get recent commands across all controllers

    Args:
        limit: Maximum number of commands to return (default 100)

    Returns:
        List of CommandResponse objects
    """

    queue_manager = QueueManager(db)
    commands = queue_manager.get_recent_commands(limit=limit)

    return commands


@router.get("/failed", response_model=List[CommandResponse])
async def get_failed_commands(
    controller_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get failed commands for troubleshooting

    Args:
        controller_id: Optional controller ID to filter by
        limit: Maximum number of commands to return (default 50)

    Returns:
        List of failed CommandResponse objects
    """

    queue_manager = QueueManager(db)
    commands = queue_manager.get_failed_commands(
        controller_id=controller_id,
        limit=limit
    )

    return commands
