"""
Command Queue Service

Handles enqueue/dequeue operations and queue management for command execution
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import uuid

from ..models.command_queue import CommandQueue, PortStatus, CommandHistory


class CommandQueueService:
    """Service for managing command queue operations"""

    @staticmethod
    async def enqueue(
        db: Session,
        hostname: str,
        command: str,
        command_class: str,
        port: int = 0,
        channel: Optional[str] = None,
        digit: Optional[int] = None,
        batch_id: Optional[str] = None,
        priority: int = 0,
        max_attempts: int = 3,
        scheduled_at: Optional[datetime] = None,
        user_ip: Optional[str] = None,
        routing_method: str = "queued"
    ) -> int:
        """
        Enqueue a command for execution

        Args:
            db: Database session
            hostname: Device hostname
            command: Command to execute
            command_class: 'immediate', 'interactive', 'bulk', or 'system'
            port: Port/box number (0-5)
            channel: Channel number (for channel commands)
            digit: Digit (for digit dispatch)
            batch_id: Batch ID for grouping related commands
            priority: Priority (higher = more urgent)
            max_attempts: Maximum retry attempts
            scheduled_at: Schedule for future execution
            user_ip: User IP for audit
            routing_method: How command was routed

        Returns:
            Command queue ID
        """
        queue_entry = CommandQueue(
            hostname=hostname,
            command=command,
            port=port,
            channel=channel,
            digit=digit,
            command_class=command_class,
            batch_id=batch_id,
            status='pending',
            priority=priority,
            max_attempts=max_attempts,
            scheduled_at=scheduled_at,
            user_ip=user_ip,
            routing_method=routing_method
        )

        db.add(queue_entry)
        db.commit()
        db.refresh(queue_entry)

        return queue_entry.id

    @staticmethod
    def get_next_command(db: Session) -> Optional[CommandQueue]:
        """
        Get next pending command to execute (priority-based)

        Returns command with:
        - status = 'pending'
        - attempts < max_attempts
        - scheduled_at is None or in the past
        - Ordered by priority (desc), then created_at (asc)
        """
        now = datetime.now()

        cmd = db.query(CommandQueue).filter(
            and_(
                CommandQueue.status == 'pending',
                CommandQueue.attempts < CommandQueue.max_attempts,
                or_(
                    CommandQueue.scheduled_at == None,
                    CommandQueue.scheduled_at <= now
                )
            )
        ).order_by(
            CommandQueue.priority.desc(),
            CommandQueue.created_at.asc()
        ).with_for_update(skip_locked=True).first()

        if cmd:
            # Mark as processing
            cmd.status = 'processing'
            cmd.attempts += 1
            cmd.last_attempt_at = now
            db.commit()

        return cmd

    @staticmethod
    def mark_completed(
        db: Session,
        command_id: int,
        success: bool,
        execution_time_ms: int,
        error_message: Optional[str] = None
    ):
        """Mark command as completed"""
        cmd = db.query(CommandQueue).filter(CommandQueue.id == command_id).first()
        if not cmd:
            return

        cmd.status = 'completed'
        cmd.completed_at = datetime.now()
        cmd.success = success
        cmd.execution_time_ms = execution_time_ms
        cmd.error_message = error_message

        # Log to history
        CommandQueueService._log_to_history(db, cmd)

        # Update port status if channel command (exclude port 0 - diagnostic only)
        if success and cmd.command == "channel" and cmd.channel and cmd.port != 0:
            CommandQueueService.update_port_status(
                db, cmd.hostname, cmd.port, channel=cmd.channel
            )

        # Update port status if power command (exclude port 0 - diagnostic only)
        if success and cmd.command == "power" and cmd.port != 0:
            # Get current power state to toggle
            current_status = db.query(PortStatus).filter(
                and_(
                    PortStatus.hostname == cmd.hostname,
                    PortStatus.port == cmd.port
                )
            ).first()

            # Toggle: if currently 'on' -> 'off', else -> 'on'
            new_state = 'off' if (current_status and current_status.last_power_state == 'on') else 'on'

            CommandQueueService.update_port_status(
                db, cmd.hostname, cmd.port, power_state=new_state
            )

        db.commit()

    @staticmethod
    def mark_failed(
        db: Session,
        command_id: int,
        error_message: str,
        retry: bool = True
    ):
        """
        Mark command as failed

        Args:
            retry: If True and attempts < max_attempts, reschedule with backoff
        """
        cmd = db.query(CommandQueue).filter(CommandQueue.id == command_id).first()
        if not cmd:
            return

        if retry and cmd.attempts < cmd.max_attempts:
            # Retry with exponential backoff
            backoff_seconds = 2 ** cmd.attempts  # 2, 4, 8 seconds
            cmd.status = 'pending'
            cmd.scheduled_at = datetime.now() + timedelta(seconds=backoff_seconds)
            cmd.error_message = f"{error_message} (attempt {cmd.attempts}/{cmd.max_attempts})"
        else:
            # Max attempts reached or no retry
            cmd.status = 'failed'
            cmd.completed_at = datetime.now()
            cmd.success = False
            cmd.error_message = error_message

            # Log to history
            CommandQueueService._log_to_history(db, cmd)

        db.commit()

    @staticmethod
    def update_port_status(
        db: Session,
        hostname: str,
        port: int,
        channel: Optional[str] = None,
        power_state: Optional[str] = None
    ):
        """Update port status with last successful channel and/or power state"""
        now = datetime.now()

        # Try to find existing record
        status = db.query(PortStatus).filter(
            and_(
                PortStatus.hostname == hostname,
                PortStatus.port == port
            )
        ).first()

        if status:
            # Update channel if provided
            if channel:
                status.last_channel = channel
                status.last_command = "channel"
                status.last_command_at = now
            # Update power state if provided
            if power_state:
                status.last_power_state = power_state
                status.last_power_command_at = now
                if not channel:  # Only update last_command if channel wasn't updated
                    status.last_command = "power"
                    status.last_command_at = now
            status.updated_at = now
        else:
            status = PortStatus(
                hostname=hostname,
                port=port,
                last_channel=channel,
                last_command="channel" if channel else ("power" if power_state else None),
                last_command_at=now,
                last_power_state=power_state,
                last_power_command_at=now if power_state else None,
                updated_at=now
            )
            db.add(status)

        db.commit()

    @staticmethod
    def get_port_status(db: Session, hostname: str) -> List[Dict[str, Any]]:
        """Get port status for all ports of a device"""
        statuses = db.query(PortStatus).filter(
            PortStatus.hostname == hostname
        ).all()

        return [
            {
                "port": s.port,
                "last_channel": s.last_channel,
                "last_command": s.last_command,
                "last_command_at": s.last_command_at.isoformat() if s.last_command_at else None,
                "last_power_state": s.last_power_state,
                "last_power_command_at": s.last_power_command_at.isoformat() if s.last_power_command_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None
            }
            for s in statuses
        ]

    @staticmethod
    def get_batch_status(db: Session, batch_id: str) -> Dict[str, Any]:
        """Get status of all commands in a batch"""
        commands = db.query(CommandQueue).filter(
            CommandQueue.batch_id == batch_id
        ).all()

        return {
            "batch_id": batch_id,
            "total": len(commands),
            "completed": sum(1 for c in commands if c.status == 'completed'),
            "failed": sum(1 for c in commands if c.status == 'failed'),
            "pending": sum(1 for c in commands if c.status in ('pending', 'processing')),
            "commands": [
                {
                    "id": c.id,
                    "hostname": c.hostname,
                    "command": c.command,
                    "port": c.port,
                    "channel": c.channel,
                    "status": c.status,
                    "success": c.success,
                    "attempts": c.attempts,
                    "error_message": c.error_message
                }
                for c in commands
            ]
        }

    @staticmethod
    def get_queue_metrics(db: Session) -> Dict[str, Any]:
        """Get queue health metrics"""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)

        pending_count = db.query(CommandQueue).filter(
            CommandQueue.status == 'pending'
        ).count()

        processing_count = db.query(CommandQueue).filter(
            CommandQueue.status == 'processing'
        ).count()

        completed_last_hour = db.query(CommandQueue).filter(
            and_(
                CommandQueue.status == 'completed',
                CommandQueue.completed_at >= one_hour_ago
            )
        ).count()

        failed_last_hour = db.query(CommandQueue).filter(
            and_(
                CommandQueue.status == 'failed',
                CommandQueue.completed_at >= one_hour_ago
            )
        ).count()

        # Check for stuck commands (processing > 5 minutes)
        stuck_threshold = now - timedelta(minutes=5)
        stuck_count = db.query(CommandQueue).filter(
            and_(
                CommandQueue.status == 'processing',
                CommandQueue.last_attempt_at < stuck_threshold
            )
        ).count()

        return {
            "pending_count": pending_count,
            "processing_count": processing_count,
            "completed_last_hour": completed_last_hour,
            "failed_last_hour": failed_last_hour,
            "stuck_commands": stuck_count,
            "healthy": stuck_count == 0 and pending_count < 1000
        }

    @staticmethod
    def cleanup_old_history(db: Session, days: int = 7):
        """Delete command history older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)

        deleted = db.query(CommandHistory).filter(
            CommandHistory.created_at < cutoff_date
        ).delete()

        # Also cleanup completed/failed queue entries older than 7 days
        deleted_queue = db.query(CommandQueue).filter(
            and_(
                CommandQueue.status.in_(['completed', 'failed']),
                CommandQueue.completed_at < cutoff_date
            )
        ).delete()

        db.commit()

        return {
            "history_deleted": deleted,
            "queue_deleted": deleted_queue
        }

    @staticmethod
    def _log_to_history(db: Session, cmd: CommandQueue):
        """Log completed/failed command to history"""
        history = CommandHistory(
            queue_id=cmd.id,
            hostname=cmd.hostname,
            command=cmd.command,
            port=cmd.port,
            channel=cmd.channel,
            success=cmd.success or False,
            execution_time_ms=cmd.execution_time_ms,
            routing_method=cmd.routing_method
        )
        db.add(history)

    @staticmethod
    def generate_batch_id() -> str:
        """Generate a unique batch ID"""
        return f"batch_{uuid.uuid4().hex[:8]}"
