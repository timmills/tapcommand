"""
Command Queue Models

Database models for the unified command queue system.
All commands (IR, Network, etc.) go through this queue.
"""

from sqlalchemy import Column, Integer, String, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel

from ..db.database import Base


class CommandStatus(str, Enum):
    """Command execution status"""
    QUEUED = "queued"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class CommandType(str, Enum):
    """Types of commands"""
    POWER = "power"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    MUTE = "mute"
    CHANNEL_UP = "channel_up"
    CHANNEL_DOWN = "channel_down"
    CHANNEL_DIRECT = "channel_direct"
    SOURCE = "source"
    MENU = "menu"
    BACK = "back"
    HOME = "home"
    OK = "ok"
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


class Command(Base):
    """Command queue table - stores all commands to be executed"""
    __tablename__ = "command_queue"

    id = Column(Integer, primary_key=True, index=True)
    command_id = Column(String, unique=True, index=True)  # UUID for tracking

    # Controller/Device info
    controller_id = Column(String, nullable=False, index=True)  # ir-dc4516 or nw-b85a97
    device_type = Column(String, nullable=False)  # "universal" or "network_tv"
    protocol = Column(String, nullable=True)  # "samsung_legacy", "lg_webos", etc.

    # Command details
    command = Column(String, nullable=False)  # CommandType value
    parameters = Column(JSON, nullable=True)  # {channel: "63", volume: 10, etc.}

    # Execution tracking
    status = Column(SQLEnum(CommandStatus), default=CommandStatus.QUEUED, index=True)
    priority = Column(Integer, default=5)  # 1-10, lower is higher priority

    # Results
    result_data = Column(JSON, nullable=True)  # Execution results
    error_message = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


# Pydantic models for API

class CommandRequest(BaseModel):
    """Request to execute a command"""
    controller_id: str
    command: str  # CommandType value
    parameters: Optional[Dict[str, Any]] = None
    priority: int = 5

    class Config:
        json_schema_extra = {
            "example": {
                "controller_id": "nw-b85a97",
                "command": "power",
                "parameters": None,
                "priority": 5
            }
        }


class CommandResponse(BaseModel):
    """Response after command execution"""
    command_id: str
    controller_id: str
    command: str
    status: CommandStatus
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExecutionResult(BaseModel):
    """Result of command execution"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
