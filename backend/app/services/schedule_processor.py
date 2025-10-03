"""
Schedule Processor Service

Background service that executes scheduled commands using APScheduler
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from croniter import croniter
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..db.database import SessionLocal
from ..models.device import Schedule, ScheduleExecution
from ..models.device_management import ManagedDevice, IRPort
from ..services.command_queue import CommandQueueService

logger = logging.getLogger(__name__)


class ScheduleProcessor:
    """Background processor for executing scheduled commands"""

    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self._running = False

    async def start(self):
        """Initialize and start the schedule processor"""
        if self._running:
            logger.warning("Schedule processor already running")
            return

        logger.info("Starting schedule processor...")

        # Initialize APScheduler
        self.scheduler = AsyncIOScheduler()

        # Load all active schedules from database
        await self._load_schedules()

        # Start scheduler
        self.scheduler.start()
        self._running = True

        logger.info("✅ Schedule processor started successfully")

    async def stop(self):
        """Stop the schedule processor"""
        if not self._running:
            return

        logger.info("Stopping schedule processor...")

        if self.scheduler:
            self.scheduler.shutdown()

        self._running = False
        logger.info("✅ Schedule processor stopped")

    async def _load_schedules(self):
        """Load all active schedules from database and add to scheduler"""
        db = SessionLocal()
        try:
            schedules = db.query(Schedule).filter(Schedule.is_active == True).all()

            logger.info(f"Loading {len(schedules)} active schedules...")

            for schedule in schedules:
                self._add_schedule_to_processor(schedule)
                logger.info(f"  ✓ Loaded schedule: {schedule.name} (ID: {schedule.id})")

            logger.info(f"✅ Loaded {len(schedules)} schedules")

        except Exception as e:
            logger.error(f"Error loading schedules: {e}", exc_info=True)
        finally:
            db.close()

    def _add_schedule_to_processor(self, schedule: Schedule):
        """Add a single schedule to APScheduler"""
        try:
            # Create cron trigger
            trigger = CronTrigger.from_crontab(schedule.cron_expression)

            # Add job to scheduler
            self.scheduler.add_job(
                self._execute_schedule,
                trigger=trigger,
                id=f"schedule_{schedule.id}",
                args=[schedule.id],
                replace_existing=True,
                name=schedule.name,
            )

            logger.debug(f"Added schedule to processor: {schedule.name}")

        except Exception as e:
            logger.error(f"Error adding schedule {schedule.id} to processor: {e}", exc_info=True)

    async def _execute_schedule(self, schedule_id: int):
        """Execute a scheduled task"""
        db = SessionLocal()
        try:
            # Get schedule
            schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()

            if not schedule:
                logger.error(f"Schedule {schedule_id} not found")
                return

            if not schedule.is_active:
                logger.warning(f"Schedule {schedule_id} is inactive, skipping execution")
                return

            logger.info(f"⏰ Executing schedule: {schedule.name} (ID: {schedule_id})")

            # Resolve target devices
            targets = self._resolve_targets(db, schedule)

            if not targets:
                logger.warning(f"No targets found for schedule {schedule_id}")
                return

            logger.info(f"  📍 Found {len(targets)} target devices")

            # Generate batch ID
            batch_id = f"sched_{schedule_id}_{uuid.uuid4().hex[:8]}"

            # Execute actions sequentially with delays
            queued_count = 0

            for idx, action in enumerate(schedule.actions, 1):
                action_type = action.get("type")
                action_value = action.get("value")
                action_repeat = action.get("repeat", 1)
                wait_after = action.get("wait_after", 0)

                # Map power state to discrete commands
                command_type = action_type
                if action_type == "power" and action_value:
                    if action_value == "on":
                        command_type = "power_on"
                    elif action_value == "off":
                        command_type = "power_off"
                    # else: use "power" (toggle) as default

                logger.info(f"  🎬 Action {idx}/{len(schedule.actions)}: {command_type}")

                # Queue commands for all targets
                for target in targets:
                    # Get device hostname
                    device = db.query(ManagedDevice).filter(
                        ManagedDevice.id == target.device_id
                    ).first()

                    if not device:
                        logger.warning(f"Device not found for IRPort {target.id}")
                        continue

                    # Handle volume repeat
                    if command_type in ("volume_up", "volume_down") and action_repeat > 1:
                        for repeat_idx in range(action_repeat):
                            queue_id = await CommandQueueService.enqueue(
                                db,
                                device.hostname,
                                command_type,
                                "system",
                                port=target.port_number,
                                batch_id=batch_id,
                                priority=0,  # Normal priority for scheduled tasks
                                routing_method="scheduled",
                            )
                            queued_count += 1

                            logger.debug(
                                f"    Queued {command_type} for {target.connected_device_name or device.hostname}:{target.port_number} (repeat {repeat_idx + 1}/{action_repeat})"
                            )
                    else:
                        # Single command
                        queue_id = await CommandQueueService.enqueue(
                            db,
                            device.hostname,
                            command_type,
                            "system",
                            port=target.port_number,
                            channel=action_value if action_type == "channel" else None,
                            batch_id=batch_id,
                            priority=0,
                            routing_method="scheduled",
                        )
                        queued_count += 1

                        logger.debug(
                            f"    Queued {command_type} for {target.connected_device_name or device.hostname}:{target.port_number}"
                        )

                # Wait after action if specified
                if wait_after > 0 and idx < len(schedule.actions):
                    logger.info(f"  ⏱️  Waiting {wait_after}s before next action...")
                    await asyncio.sleep(wait_after)

            logger.info(f"  ✅ Queued {queued_count} commands in batch {batch_id}")

            # Update schedule
            schedule.last_run = datetime.now()
            schedule.next_run = self._calculate_next_run(schedule.cron_expression)
            db.commit()

            # Log execution
            execution = ScheduleExecution(
                schedule_id=schedule_id,
                batch_id=batch_id,
                executed_at=datetime.now(),
                total_commands=queued_count,
            )
            db.add(execution)
            db.commit()

            logger.info(f"✅ Schedule execution completed: {schedule.name}")
            logger.info(f"  Next run: {schedule.next_run}")

        except Exception as e:
            logger.error(f"Error executing schedule {schedule_id}: {e}", exc_info=True)
        finally:
            db.close()

    def _resolve_targets(self, db: Session, schedule: Schedule) -> list:
        """Resolve target devices based on schedule target_type"""
        try:
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

        except Exception as e:
            logger.error(f"Error resolving targets: {e}", exc_info=True)
            return []

    def _calculate_next_run(self, cron_expression: str) -> datetime:
        """Calculate next run time from cron expression"""
        try:
            cron = croniter(cron_expression, datetime.now())
            return cron.get_next(datetime)
        except Exception as e:
            logger.error(f"Error calculating next run: {e}", exc_info=True)
            return None

    async def add_schedule(self, schedule: Schedule):
        """Add new schedule to processor (called when schedule is created)"""
        if not self._running or not self.scheduler:
            logger.warning("Schedule processor not running, cannot add schedule")
            return

        self._add_schedule_to_processor(schedule)
        logger.info(f"Added new schedule: {schedule.name} (ID: {schedule.id})")

    async def remove_schedule(self, schedule_id: int):
        """Remove schedule from processor (called when schedule is deleted)"""
        if not self._running or not self.scheduler:
            return

        try:
            job_id = f"schedule_{schedule_id}"
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed schedule {schedule_id} from processor")
        except Exception as e:
            logger.warning(f"Could not remove schedule {schedule_id}: {e}")

    async def update_schedule(self, schedule: Schedule):
        """Update existing schedule in processor (called when schedule is updated)"""
        if not self._running or not self.scheduler:
            return

        # Remove old job and add new one (APScheduler will replace existing with same ID)
        self._add_schedule_to_processor(schedule)
        logger.info(f"Updated schedule: {schedule.name} (ID: {schedule.id})")


# Global instance
schedule_processor = ScheduleProcessor()


async def start_schedule_processor():
    """Start the global schedule processor"""
    await schedule_processor.start()


async def stop_schedule_processor():
    """Stop the global schedule processor"""
    await schedule_processor.stop()
