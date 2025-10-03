from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class CommandQueue(Base):
    """
    Command queue for reliable command execution with retry logic
    """
    __tablename__ = "command_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Command details
    hostname = Column(String, nullable=False, index=True)
    command = Column(String, nullable=False)
    port = Column(Integer, default=0)
    channel = Column(String, nullable=True)
    digit = Column(Integer, nullable=True)

    # Classification
    command_class = Column(String, nullable=False)  # 'immediate', 'interactive', 'bulk', 'system'
    batch_id = Column(String, nullable=True, index=True)  # Link related commands

    # Queue management
    status = Column(String, default='pending', index=True)  # 'pending', 'processing', 'completed', 'failed'
    priority = Column(Integer, default=0, index=True)  # Higher = more urgent
    scheduled_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Defer execution

    # Execution tracking
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Results
    success = Column(Boolean, nullable=True)
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)

    # Routing info
    routing_method = Column(String, nullable=True)  # 'direct_success', 'direct_failed_queued', 'queued'

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_by = Column(String, nullable=True)
    user_ip = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    # Define composite indexes for common queries
    __table_args__ = (
        Index('idx_status_priority', 'status', 'priority'),
        Index('idx_hostname_status', 'hostname', 'status'),
    )


class PortStatus(Base):
    """
    Track last successful channel command per port for UI display
    Lightweight table for frequently accessed data
    """
    __tablename__ = "port_status"

    hostname = Column(String, primary_key=True, nullable=False)
    port = Column(Integer, primary_key=True, nullable=False)
    last_channel = Column(String, nullable=True)  # e.g., "500"
    last_command = Column(String, nullable=True)
    last_command_at = Column(DateTime(timezone=True), nullable=True)
    last_power_state = Column(String, nullable=True)  # 'on', 'off', or null (unknown)
    last_power_command_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CommandHistory(Base):
    """
    Historical log of all commands (successful and failed)
    Rotated every 7 days to keep database manageable
    """
    __tablename__ = "command_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    queue_id = Column(Integer, nullable=True)  # Link to command_queue if queued
    hostname = Column(String, nullable=False, index=True)
    command = Column(String, nullable=False)
    port = Column(Integer, nullable=True)
    channel = Column(String, nullable=True)
    success = Column(Boolean, nullable=False)
    execution_time_ms = Column(Integer, nullable=True)
    routing_method = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Composite index for common queries
    __table_args__ = (
        Index('idx_hostname_created', 'hostname', 'created_at'),
    )
