"""
History Cleanup Service

Background task that runs daily to clean up old command history (7+ days old)
"""

import asyncio
import logging
from datetime import datetime, time, timedelta

from ..db.database import SessionLocal
from .command_queue import CommandQueueService

logger = logging.getLogger(__name__)


class HistoryCleanupService:
    """Service for cleaning up old command history"""

    def __init__(self, retention_days: int = 7, cleanup_time: time = time(3, 0)):
        """
        Args:
            retention_days: Number of days to keep history (default 7)
            cleanup_time: Time of day to run cleanup (default 3:00 AM)
        """
        self.retention_days = retention_days
        self.cleanup_time = cleanup_time
        self.running = False
        self.task = None

    async def start(self):
        """Start the cleanup service"""
        if self.running:
            logger.warning("History cleanup service already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._cleanup_loop())
        logger.info(
            f"History cleanup service started "
            f"(retention: {self.retention_days} days, "
            f"cleanup time: {self.cleanup_time})"
        )

    async def stop(self):
        """Stop the cleanup service"""
        if not self.running:
            return

        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        logger.info("History cleanup service stopped")

    async def _cleanup_loop(self):
        """Main cleanup loop - runs daily at specified time"""
        while self.running:
            try:
                # Calculate time until next cleanup
                now = datetime.now()
                next_cleanup = datetime.combine(now.date(), self.cleanup_time)

                # If cleanup time has passed today, schedule for tomorrow
                if now.time() >= self.cleanup_time:
                    next_cleanup = datetime.combine(
                        now.date() + timedelta(days=1),
                        self.cleanup_time
                    )

                wait_seconds = (next_cleanup - now).total_seconds()

                logger.info(
                    f"Next history cleanup scheduled for {next_cleanup} "
                    f"(in {wait_seconds/3600:.1f} hours)"
                )

                # Wait until cleanup time
                await asyncio.sleep(wait_seconds)

                # Perform cleanup
                await self.cleanup_history()

            except asyncio.CancelledError:
                logger.info("History cleanup loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)
                # Wait 1 hour before retrying on error
                await asyncio.sleep(3600)

    async def cleanup_history(self):
        """Run the cleanup operation"""
        logger.info(f"Starting history cleanup (retention: {self.retention_days} days)")

        db = SessionLocal()
        try:
            result = CommandQueueService.cleanup_old_history(db, days=self.retention_days)

            logger.info(
                f"History cleanup complete: "
                f"{result['history_deleted']} history entries deleted, "
                f"{result['queue_deleted']} completed queue entries deleted"
            )

            return result

        except Exception as e:
            logger.error(f"Error during history cleanup: {e}", exc_info=True)
            raise
        finally:
            db.close()

    async def cleanup_now(self):
        """Trigger an immediate cleanup (for manual/testing purposes)"""
        logger.info("Manual history cleanup triggered")
        return await self.cleanup_history()


# Global service instance
_cleanup_service: HistoryCleanupService = None


def get_cleanup_service() -> HistoryCleanupService:
    """Get or create the global cleanup service"""
    global _cleanup_service
    if _cleanup_service is None:
        _cleanup_service = HistoryCleanupService(
            retention_days=7,
            cleanup_time=time(3, 0)  # 3:00 AM
        )
    return _cleanup_service


async def start_history_cleanup():
    """Start the global history cleanup service"""
    service = get_cleanup_service()
    await service.start()


async def stop_history_cleanup():
    """Stop the global history cleanup service"""
    service = get_cleanup_service()
    await service.stop()
