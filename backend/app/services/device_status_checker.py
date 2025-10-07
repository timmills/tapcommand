"""
Device Status Checker Service

Background service that periodically checks the status of network devices
"""

import asyncio
import logging
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

import requests

from ..db.database import SessionLocal
from ..models.device_status import DeviceStatus
from ..models.virtual_controller import VirtualDevice, VirtualController

logger = logging.getLogger(__name__)


class DeviceStatusChecker:
    """
    Background service for checking device status

    Supports different check methods based on protocol:
    - Roku: HTTP API status queries
    - LG webOS: WebSocket status queries
    - Samsung Legacy: Ping only (no status API)
    - Samsung Tizen: WebSocket status queries
    """

    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.check_interval = 300  # 5 minutes default

    async def start_status_monitoring(self):
        """Start the status monitoring background task"""
        if self.running:
            logger.warning("Status monitoring already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._monitoring_loop())
        logger.info("Device status monitoring started")

    async def stop_status_monitoring(self):
        """Stop the status monitoring background task"""
        if not self.running:
            return

        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Device status monitoring stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                await self._check_all_devices()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in status monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def _check_all_devices(self):
        """Check status of all network devices"""
        db = SessionLocal()
        try:
            # Get all virtual devices (network TVs)
            devices = db.query(VirtualDevice).join(VirtualController).all()

            logger.info(f"Checking status of {len(devices)} devices")

            for device in devices:
                try:
                    await self._check_device_status(db, device)
                except Exception as e:
                    logger.error(f"Error checking device {device.controller.controller_id}: {e}")

            db.commit()

        except Exception as e:
            logger.error(f"Error in check_all_devices: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()

    async def _check_device_status(self, db: Session, device: VirtualDevice):
        """
        Check status of a single device

        Args:
            db: Database session
            device: Virtual device to check
        """
        controller = device.controller
        controller_id = controller.controller_id
        protocol = controller.protocol

        # Get or create status record
        status = db.query(DeviceStatus).filter_by(
            controller_id=controller_id
        ).first()

        if not status:
            status = DeviceStatus(
                controller_id=controller_id,
                device_type="network_tv",
                protocol=protocol
            )
            db.add(status)

        # Perform protocol-specific status check
        old_power_state = status.power_state
        old_is_online = status.is_online

        if protocol == "roku":
            check_result = await self._check_roku_status(device)
        elif protocol == "lg_webos":
            check_result = await self._check_webos_status(device)
        elif protocol == "samsung_tizen":
            check_result = await self._check_samsung_tizen_status(device)
        elif protocol == "samsung_legacy":
            check_result = await self._check_ping_only(device)
        else:
            # Default to ping for unknown protocols
            check_result = await self._check_ping_only(device)

        # Update status record
        status.is_online = check_result.get("is_online", False)
        status.power_state = check_result.get("power_state", "unknown")
        status.current_channel = check_result.get("current_channel")
        status.current_input = check_result.get("current_input")
        status.model_info = check_result.get("model_info")
        status.firmware_version = check_result.get("firmware_version")
        status.check_method = check_result.get("check_method", "unknown")
        status.last_checked_at = datetime.now()

        # Track when online
        if status.is_online:
            status.last_online_at = datetime.now()

        # Track state changes
        if old_power_state != status.power_state or old_is_online != status.is_online:
            status.last_changed_at = datetime.now()
            logger.info(
                f"Device {controller_id} status changed: "
                f"online={status.is_online}, power={status.power_state}"
            )

    async def _check_roku_status(self, device: VirtualDevice) -> Dict[str, Any]:
        """
        Check Roku device status via HTTP API

        Roku provides rich HTTP APIs for querying device state
        """
        ip = device.ip_address
        result = {
            "is_online": False,
            "power_state": "unknown",
            "check_method": "roku_api"
        }

        try:
            # Check if device is reachable and get device info
            response = requests.get(
                f"http://{ip}:8060/query/device-info",
                timeout=3
            )

            if response.status_code == 200:
                result["is_online"] = True

                # Parse XML response for device info
                content = response.text

                # Extract power state (Roku doesn't explicitly report this, but we know it's on if responding)
                result["power_state"] = "on"

                # Extract model info
                if "<model-name>" in content:
                    model_start = content.find("<model-name>") + 12
                    model_end = content.find("</model-name>")
                    result["model_info"] = content[model_start:model_end]

                # Check active app to get current channel
                app_response = requests.get(
                    f"http://{ip}:8060/query/active-app",
                    timeout=2
                )
                if app_response.status_code == 200:
                    app_content = app_response.text
                    if "<app>" in app_content:
                        app_start = app_content.find('id="') + 4
                        app_end = app_content.find('"', app_start)
                        app_id = app_content[app_start:app_end]

                        # Get app name
                        name_start = app_content.find(">", app_end) + 1
                        name_end = app_content.find("</app>")
                        app_name = app_content[name_start:name_end]

                        result["current_channel"] = app_name
                        result["current_input"] = app_id

        except requests.RequestException as e:
            logger.debug(f"Roku device {ip} not reachable: {e}")
            result["is_online"] = False
            result["power_state"] = "off"

        return result

    async def _check_webos_status(self, device: VirtualDevice) -> Dict[str, Any]:
        """
        Check LG webOS device status

        webOS uses WebSocket for communication
        """
        # TODO: Implement WebSocket status check
        # For now, fall back to ping
        result = await self._check_ping_only(device)
        result["check_method"] = "webos_stub"
        return result

    async def _check_samsung_tizen_status(self, device: VirtualDevice) -> Dict[str, Any]:
        """
        Check Samsung Tizen (2016+) device status

        Tizen uses WebSocket for communication
        """
        # TODO: Implement WebSocket status check
        # For now, fall back to ping
        result = await self._check_ping_only(device)
        result["check_method"] = "tizen_stub"
        return result

    async def _check_ping_only(self, device: VirtualDevice) -> Dict[str, Any]:
        """
        Simple ping-based status check

        Used for devices without status API (like Samsung Legacy)
        """
        ip = device.ip_address
        result = {
            "is_online": False,
            "power_state": "unknown",
            "check_method": "ping"
        }

        try:
            # Ping the device (1 packet, 1 second timeout)
            response = subprocess.run(
                ["ping", "-c", "1", "-W", "1", ip],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2
            )

            if response.returncode == 0:
                result["is_online"] = True
                # We can't determine power state with just ping
                # Assume if online, it's probably on
                result["power_state"] = "on"
            else:
                result["is_online"] = False
                result["power_state"] = "off"

        except Exception as e:
            logger.debug(f"Ping failed for {ip}: {e}")
            result["is_online"] = False
            result["power_state"] = "unknown"

        return result

    async def check_device_now(self, controller_id: str) -> Optional[DeviceStatus]:
        """
        Immediately check a specific device (on-demand)

        Args:
            controller_id: Controller ID to check

        Returns:
            Updated DeviceStatus or None if not found
        """
        db = SessionLocal()
        try:
            device = db.query(VirtualDevice).join(VirtualController).filter(
                VirtualController.controller_id == controller_id
            ).first()

            if not device:
                logger.warning(f"Device {controller_id} not found")
                return None

            await self._check_device_status(db, device)
            db.commit()

            status = db.query(DeviceStatus).filter_by(
                controller_id=controller_id
            ).first()

            return status

        except Exception as e:
            logger.error(f"Error checking device {controller_id}: {e}", exc_info=True)
            db.rollback()
            return None
        finally:
            db.close()


# Global instance
status_checker = DeviceStatusChecker()
