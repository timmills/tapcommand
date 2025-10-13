import asyncio
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import aioesphomeapi
from aioesphomeapi import APIClient, APIConnectionError

from ..core.config import settings
from ..services.settings_service import settings_service

logger = logging.getLogger(__name__)


class ESPHomeClient:
    def __init__(self, hostname: str, ip_address: str, port: int = None, api_key: Optional[str] = None):
        self.hostname = hostname
        self.ip_address = ip_address
        self.port = port or settings.ESPHOME_API_PORT
        self.api_key = api_key or settings_service.get_setting("esphome_api_key")
        self.client: Optional[APIClient] = None
        self.connected = False
        self.last_connection_attempt = None

    def set_api_key(self, api_key: Optional[str]):
        if api_key:
            self.api_key = api_key
        elif not self.api_key:
            self.api_key = settings_service.get_setting("esphome_api_key")

    async def connect(self) -> bool:
        """Connect to the ESPHome device"""
        try:
            self.client = APIClient(
                address=self.ip_address,
                port=self.port,
                password="",
                noise_psk=self.api_key
            )

            await self.client.connect(login=True)
            self.connected = True
            self.last_connection_attempt = datetime.now()
            logger.info(f"Connected to ESPHome device: {self.hostname}")
            return True

        except (APIConnectionError, Exception) as e:
            logger.error(f"Failed to connect to {self.hostname}: {e}")
            self.connected = False
            self.last_connection_attempt = datetime.now()
            return False

    async def disconnect(self):
        """Disconnect from the ESPHome device"""
        if self.client:
            await self.client.disconnect()
            self.connected = False
            logger.info(f"Disconnected from ESPHome device: {self.hostname}")

    async def call_service(self, service_name: str, data: Dict[str, Any] = None) -> bool:
        """Call a service on the ESPHome device"""
        if not self.connected or not self.client:
            if not await self.connect():
                return False

        try:
            # Get device info and services
            device_info = await self.client.device_info()
            entities, services = await self.client.list_entities_services()

            # Find the service
            target_service = None
            for service in services:
                if service.name == service_name:
                    target_service = service
                    break

            if not target_service:
                logger.error(f"Service '{service_name}' not found on device {self.hostname}")
                return False

            # Prepare service data
            service_data = data or {}

            # Call the service
            result = self.client.execute_service(target_service, service_data)

            # Handle both coroutine and None returns from execute_service
            if result is not None:
                await result

            logger.info(f"Called service '{service_name}' on {self.hostname} with data: {service_data}")
            return True

        except Exception as e:
            logger.error(f"Error calling service '{service_name}' on {self.hostname}: {e}")
            self.connected = False
            return False

    async def get_device_info(self) -> Optional[Dict[str, Any]]:
        """Get device information"""
        if not self.connected or not self.client:
            if not await self.connect():
                return None

        try:
            device_info = await self.client.device_info()
            return {
                "name": device_info.name,
                "friendly_name": device_info.friendly_name,
                "esphome_version": device_info.esphome_version,
                "compilation_time": device_info.compilation_time,
                "model": device_info.model,
                "mac_address": device_info.mac_address,
                "manufacturer": device_info.manufacturer,
                "project_name": device_info.project_name,
                "project_version": device_info.project_version
            }

        except Exception as e:
            logger.error(f"Error getting device info from {self.hostname}: {e}")
            return None

    async def health_check(self) -> bool:
        """Perform a health check on the device"""
        try:
            if not self.connected:
                return await self.connect()

            # Try to get device info as a health check
            device_info = await self.client.device_info()
            return device_info is not None

        except Exception as e:
            logger.debug(f"Health check failed for {self.hostname}: {e}")
            self.connected = False
            return False

    async def device_info(self) -> Optional[Dict[str, Any]]:
        """Alias for get_device_info for consistency"""
        return await self.get_device_info()

    async def get_capabilities_snapshot(self) -> Optional[Dict[str, Any]]:
        """Request the IR capabilities payload from the device"""
        if not self.connected or not self.client:
            if not await self.connect():
                return None

        try:
            entities, services = await self.client.list_entities_services()

            text_sensor_key = None
            for entity in entities:
                if getattr(entity, "object_id", "") == "ir_capabilities_payload":
                    text_sensor_key = entity.key
                    break

            if text_sensor_key is None:
                logger.warning(f"IR capabilities text sensor not found on {self.hostname}")
                return None

            payload_future: asyncio.Future[str] = asyncio.get_running_loop().create_future()

            def state_callback(state):
                if getattr(state, "key", None) == text_sensor_key and not payload_future.done():
                    payload_future.set_result(state.state)

            # Handle both coroutine and None returns from subscribe_states
            subscribe_result = self.client.subscribe_states(state_callback)
            if subscribe_result is not None:
                unsubscribe = await subscribe_result
            else:
                unsubscribe = None

            report_service = next((svc for svc in services if svc.name == "report_capabilities"), None)
            if report_service:
                # Handle both coroutine and None returns from execute_service
                result = self.client.execute_service(report_service, {})
                if result is not None:
                    await result
            else:
                logger.warning(f"report_capabilities service not found on {self.hostname}")

            try:
                payload = await asyncio.wait_for(payload_future, timeout=5)
            except asyncio.TimeoutError:
                logger.warning(f"Timed out waiting for capabilities from {self.hostname}")
                return None
            finally:
                if callable(unsubscribe):
                    result = unsubscribe()
                    if asyncio.iscoroutine(result):
                        await result

            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                logger.error(f"Invalid capabilities payload received from {self.hostname}")
                return None

        except Exception as e:
            import traceback
            logger.error(f"Error retrieving capabilities from {self.hostname}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
        finally:
            await self.disconnect()


class ESPHomeManager:
    def __init__(self):
        self.clients: Dict[str, ESPHomeClient] = {}

    def get_client(self, hostname: str, ip_address: str, api_key: Optional[str] = None) -> ESPHomeClient:
        """Get or create an ESPHome client for a device"""
        if hostname not in self.clients:
            self.clients[hostname] = ESPHomeClient(hostname, ip_address, api_key=api_key)
        else:
            client = self.clients[hostname]
            client.ip_address = ip_address
            client.set_api_key(api_key)

        return self.clients[hostname]

    async def fetch_capabilities(self, hostname: str, ip_address: str, api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch capability snapshot for a device"""
        client = self.get_client(hostname, ip_address, api_key)
        return await client.get_capabilities_snapshot()

    async def send_tv_command(
        self,
        hostname: str,
        ip_address: str,
        command: str,
        box: int = 0,
        *,
        api_key: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """Send a TV command to a specific device (supports multi-box setups)"""
        client = self.get_client(hostname, ip_address, api_key)

        # Map command types to ESPHome service names
        service_map = {
            "power": "tv_power",
            "power_on": "tv_power_on",
            "power_off": "tv_power_off",
            "mute": "tv_mute",
            "volume_up": "tv_volume_up",
            "volume_down": "tv_volume_down",
            "channel_up": "tv_channel_up",
            "channel_down": "tv_channel_down",
            "channel": "tv_channel",
            "number": "tv_number",
            "diagnostic_signal": "diagnostic_signal"
        }

        service_name = service_map.get(command)
        if not service_name:
            logger.error(f"Unknown command: {command}")
            return False

        # Prepare service data
        service_data = {}

        # Add port parameter if specified (for multi-port setups)
        # ESPHome services expect 'port' parameter, not 'box'
        if box > 0:
            service_data["port"] = box

        if command == "channel":
            if "channel" in kwargs:
                # ESPHome tv_channel service expects separate port and channel parameters
                # Send channel as string to preserve leading zeros (e.g., "060")
                service_data["channel"] = str(kwargs["channel"])
                # Port is already added above if box > 0
            else:
                logger.error("Channel command requires 'channel' parameter")
                return False
        elif command == "number":
            if "digit" in kwargs:
                service_data["digit"] = kwargs["digit"]
            else:
                logger.error("Number command requires 'digit' parameter")
                return False
        elif command == "diagnostic_signal":
            # Handle diagnostic signal parameters
            # Accept either 'port' or 'box' parameter names
            port_param = kwargs.get("port", box)
            code_param = kwargs.get("code", kwargs.get("digit"))

            if code_param is not None:
                service_data["port"] = port_param
                service_data["code"] = code_param
            else:
                logger.error("Diagnostic signal command requires 'code' parameter")
                return False

        return await client.call_service(service_name, service_data)


    async def health_check_all(self) -> Dict[str, bool]:
        """Perform health checks on all connected devices"""
        results = {}
        for hostname, client in self.clients.items():
            results[hostname] = await client.health_check()
        return results

    async def disconnect_all(self):
        """Disconnect all clients"""
        for client in self.clients.values():
            await client.disconnect()


# Global ESPHome manager instance
esphome_manager = ESPHomeManager()
