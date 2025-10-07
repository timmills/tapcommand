"""
Command Queue Processor

Background worker that processes queued commands with retry logic
"""

import asyncio
import logging
import time
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from ..db.database import SessionLocal
from ..models.command_queue import CommandQueue
from ..models.device import Device
from ..models.virtual_controller import VirtualController, VirtualDevice
from .command_queue import CommandQueueService
from .esphome_client import ESPHomeClient
from ..commands.router import ProtocolRouter
from ..commands.models import Command as ExecutorCommand

logger = logging.getLogger(__name__)


class CommandQueueProcessor:
    """
    Background worker for processing command queue
    Runs multiple concurrent workers
    """

    def __init__(self, worker_count: int = 3, poll_interval: float = 0.5):
        """
        Args:
            worker_count: Number of concurrent workers
            poll_interval: Seconds to wait between queue checks
        """
        self.worker_count = worker_count
        self.poll_interval = poll_interval
        self.running = False
        self.workers = []
        self.clients_cache: dict[str, ESPHomeClient] = {}

    async def start(self):
        """Start the queue processor with multiple workers"""
        if self.running:
            logger.warning("Queue processor already running")
            return

        self.running = True
        logger.info(f"Starting queue processor with {self.worker_count} workers...")

        # Start worker coroutines
        self.workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.worker_count)
        ]

        logger.info(f"✓ Queue processor started with {self.worker_count} workers")

    async def stop(self):
        """Stop the queue processor"""
        if not self.running:
            return

        logger.info("Stopping queue processor...")
        self.running = False

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to complete
        await asyncio.gather(*self.workers, return_exceptions=True)

        # Disconnect all cached clients
        for client in self.clients_cache.values():
            await client.disconnect()
        self.clients_cache.clear()

        logger.info("✓ Queue processor stopped")

    async def _worker(self, worker_id: int):
        """Individual worker coroutine"""
        logger.info(f"Worker {worker_id} started")

        while self.running:
            try:
                # Get next command ID from queue
                cmd_id = self._get_next_command()

                if cmd_id:
                    await self._execute_command(cmd_id, worker_id)
                else:
                    # No work available, sleep briefly
                    await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                logger.info(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}", exc_info=True)
                await asyncio.sleep(1.0)

        logger.info(f"Worker {worker_id} stopped")

    def _get_next_command(self) -> Optional[int]:
        """Get next command ID to execute (using separate DB session)"""
        db = SessionLocal()
        try:
            cmd = CommandQueueService.get_next_command(db)
            return cmd.id if cmd else None
        finally:
            db.close()

    async def _execute_command(self, cmd_id: int, worker_id: int):
        """Execute a queued command using protocol router"""
        db = SessionLocal()
        try:
            # Re-fetch the command in this session
            cmd = db.query(CommandQueue).filter(CommandQueue.id == cmd_id).first()
            if not cmd:
                logger.warning(f"Worker {worker_id}: Command {cmd_id} not found")
                return

            logger.info(
                f"Worker {worker_id} executing command {cmd.id}: "
                f"{cmd.command} on {cmd.hostname} port {cmd.port} (attempt {cmd.attempts})"
            )

            # Determine device type and protocol
            device_type = None
            protocol = None
            controller_id = cmd.hostname

            # Check if it's a Virtual Controller (network TV)
            if cmd.hostname.startswith('nw-'):
                vc = db.query(VirtualController).filter(
                    VirtualController.controller_id == cmd.hostname
                ).first()

                if vc:
                    # Get the Virtual Device for this port
                    vd = db.query(VirtualDevice).filter(
                        VirtualDevice.controller_id == vc.id,
                        VirtualDevice.port_number == cmd.port
                    ).first()

                    if vd:
                        # All network TVs use device_type="network_tv"
                        # Protocol field determines the specific executor
                        device_type = "network_tv"
                        protocol = vd.protocol
                    else:
                        CommandQueueService.mark_failed(
                            db, cmd.id, f"Virtual device port {cmd.port} not found", retry=False
                        )
                        return
                else:
                    CommandQueueService.mark_failed(
                        db, cmd.id, f"Virtual controller {cmd.hostname} not found", retry=False
                    )
                    return
            else:
                # IR Controller (ESPHome-based)
                device = db.query(Device).filter(Device.hostname == cmd.hostname).first()
                if not device:
                    CommandQueueService.mark_failed(
                        db, cmd.id, f"Device {cmd.hostname} not found", retry=False
                    )
                    return
                device_type = device.device_type or "universal"
                protocol = None  # IR doesn't use protocol

            # Create ExecutorCommand from queue command
            # Note: Network TVs don't use ports - each Virtual Device is a single device
            # Only IR controllers use ports (physical IR blaster ports 1-5)
            parameters = {}
            if cmd.channel:
                parameters['channel'] = cmd.channel
            if cmd.digit is not None:
                parameters['digit'] = cmd.digit

            executor_cmd = ExecutorCommand(
                controller_id=controller_id,
                command=cmd.command,
                device_type=device_type,
                protocol=protocol,
                parameters=parameters if parameters else None
            )

            # Get appropriate executor via protocol router
            router = ProtocolRouter(db)
            executor = router.get_executor(executor_cmd)

            if not executor:
                CommandQueueService.mark_failed(
                    db, cmd.id,
                    f"No executor found for device_type={device_type}, protocol={protocol}",
                    retry=False
                )
                logger.error(f"No executor for {device_type}/{protocol}")
                return

            # Execute command
            start_time = time.time()
            result = await executor.execute(executor_cmd)
            execution_time_ms = int((time.time() - start_time) * 1000)

            if result.success:
                # Mark as completed
                CommandQueueService.mark_completed(
                    db, cmd.id, True, execution_time_ms
                )
                logger.info(
                    f"✓ Worker {worker_id} completed command {cmd.id} "
                    f"in {execution_time_ms}ms via {executor.__class__.__name__}"
                )
            else:
                # Command failed
                error_msg = f"{result.message} (attempt {cmd.attempts})"
                CommandQueueService.mark_failed(db, cmd.id, error_msg, retry=True)
                logger.warning(
                    f"✗ Worker {worker_id} failed command {cmd.id}: {error_msg}"
                )

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(
                f"✗ Worker {worker_id} error executing command {cmd.id}: {e}",
                exc_info=True
            )
            CommandQueueService.mark_failed(db, cmd.id, error_msg, retry=True)

        finally:
            db.close()

    async def _get_client(self, hostname: str, ip_address: str) -> ESPHomeClient:
        """Get or create cached ESPHome client"""
        if hostname not in self.clients_cache:
            client = ESPHomeClient(hostname, ip_address)
            self.clients_cache[hostname] = client
        return self.clients_cache[hostname]

    async def _send_command(self, client: ESPHomeClient, cmd: CommandQueue) -> bool:
        """Send command to device via ESPHome client"""
        try:
            # Use the existing ESPHomeManager.send_tv_command which knows the correct service names
            from ..services.esphome_client import esphome_manager
            from ..models.device_management import ManagedDevice

            # Get managed device to get IP address and API key
            db = SessionLocal()
            try:
                device = db.query(ManagedDevice).filter(ManagedDevice.hostname == cmd.hostname).first()
                if not device:
                    return False

                # Build kwargs based on command type
                kwargs = {}
                if cmd.channel:
                    kwargs['channel'] = cmd.channel
                if cmd.digit is not None:
                    kwargs['digit'] = cmd.digit

                # Use the existing send_tv_command method with device-specific API key
                success = await esphome_manager.send_tv_command(
                    hostname=cmd.hostname,
                    ip_address=device.current_ip_address,
                    command=cmd.command,
                    box=cmd.port,
                    api_key=device.api_key,  # Pass device-specific API key
                    **kwargs
                )
                return success
            finally:
                db.close()

        except asyncio.TimeoutError:
            logger.error(f"Timeout executing command {cmd.id} on {cmd.hostname}")
            return False
        except Exception as e:
            logger.error(f"Error executing command {cmd.id}: {e}")
            return False


# Global processor instance
_processor: Optional[CommandQueueProcessor] = None


def get_processor() -> CommandQueueProcessor:
    """Get or create the global queue processor"""
    global _processor
    if _processor is None:
        _processor = CommandQueueProcessor(worker_count=3, poll_interval=0.5)
    return _processor


async def start_queue_processor():
    """Start the global queue processor"""
    processor = get_processor()
    await processor.start()


async def stop_queue_processor():
    """Stop the global queue processor"""
    processor = get_processor()
    await processor.stop()
