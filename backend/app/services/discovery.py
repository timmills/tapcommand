import asyncio
import logging
from typing import List, Dict, Optional, Callable
from zeroconf import ServiceBrowser, Zeroconf, ServiceListener
from zeroconf.asyncio import AsyncZeroconf
import socket
from datetime import datetime

from ..core.config import settings

logger = logging.getLogger(__name__)


class ESPHomeDevice:
    def __init__(self, hostname: str, ip_address: str, port: int, mac_address: str, properties: Dict[str, any]):
        self.hostname = hostname
        self.ip_address = ip_address
        self.port = port
        self.mac_address = mac_address
        self.properties = properties
        self.discovered_at = datetime.now()

    @property
    def friendly_name(self) -> str:
        """Extract friendly name from mDNS properties"""
        return self.properties.get("friendly_name", self.hostname)

    @property
    def device_type(self) -> str:
        """All devices are universal - no special device type detection"""
        return "universal"

    @property
    def version(self) -> Optional[str]:
        """Extract firmware version from properties"""
        return self.properties.get("version")

    def to_dict(self) -> Dict:
        return {
            "hostname": self.hostname,
            "ip_address": self.ip_address,
            "port": self.port,
            "mac_address": self.mac_address,
            "friendly_name": self.friendly_name,
            "device_type": self.device_type,
            "version": self.version,
            "properties": self.properties,
            "discovered_at": self.discovered_at.isoformat()
        }


class ESPHomeDiscoveryService:
    def __init__(self):
        self.discovered_devices: Dict[str, ESPHomeDevice] = {}
        self.discovery_callbacks: List[Callable[[ESPHomeDevice], None]] = []
        self.removal_callbacks: List[Callable[[str], None]] = []
        self.zeroconf: Optional[AsyncZeroconf] = None
        self.browser: Optional[ServiceBrowser] = None
        self.running = False

    def add_discovery_callback(self, callback: Callable[[ESPHomeDevice], None]):
        """Add callback for when new devices are discovered"""
        self.discovery_callbacks.append(callback)

    def add_removal_callback(self, callback: Callable[[str], None]):
        """Add callback for when devices are removed"""
        self.removal_callbacks.append(callback)

    async def start_discovery(self):
        """Start the mDNS discovery service"""
        if self.running:
            logger.warning("Discovery service already running")
            return

        logger.info("Starting ESPHome device discovery...")
        self.zeroconf = AsyncZeroconf()

        listener = ESPHomeServiceListener(self)
        self.browser = ServiceBrowser(
            self.zeroconf.zeroconf,
            settings.MDNS_SERVICE_TYPE,
            listener
        )

        self.running = True
        logger.info("Device discovery started")

    async def stop_discovery(self):
        """Stop the mDNS discovery service"""
        if not self.running:
            return

        logger.info("Stopping device discovery...")
        if self.browser:
            self.browser.cancel()
        if self.zeroconf:
            await self.zeroconf.async_close()

        self.running = False
        logger.info("Device discovery stopped")

    def get_discovered_devices(self) -> List[ESPHomeDevice]:
        """Get all currently discovered devices"""
        return list(self.discovered_devices.values())

    def get_device_by_hostname(self, hostname: str) -> Optional[ESPHomeDevice]:
        """Get a specific device by hostname"""
        return self.discovered_devices.get(hostname)

    def is_running(self) -> bool:
        """Check if discovery service is currently running"""
        return self.running

    def mark_device_unadopted(self, hostname: str):
        """
        Mark a device as unadopted so it will appear in discovery again.
        This is called when a device is removed from management.
        """
        logger.info(f"Marking device {hostname} as unadopted - will be available for re-adoption")
        # The device should already be in discovered_devices from mDNS
        # This method is mainly for logging and potential future adoption tracking
        # The actual adoption state is managed in the database

    def _add_device(self, device: ESPHomeDevice):
        """Internal method to add a discovered device"""
        self.discovered_devices[device.hostname] = device
        logger.info(f"Discovered ESPHome device: {device.hostname} ({device.ip_address})")

        # Notify callbacks
        for callback in self.discovery_callbacks:
            try:
                callback(device)
            except Exception as e:
                logger.error(f"Error in discovery callback: {e}")

    def _remove_device(self, hostname: str):
        """Internal method to remove a device"""
        if hostname in self.discovered_devices:
            del self.discovered_devices[hostname]
            logger.info(f"Removed ESPHome device: {hostname}")

            # Notify callbacks
            for callback in self.removal_callbacks:
                try:
                    callback(hostname)
                except Exception as e:
                    logger.error(f"Error in removal callback: {e}")


class ESPHomeServiceListener(ServiceListener):
    def __init__(self, discovery_service: ESPHomeDiscoveryService):
        self.discovery_service = discovery_service

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a new ESPHome service is discovered"""
        logger.info(f"mDNS service discovered: {name}")
        info = zc.get_service_info(type_, name)
        if info:
            try:
                # Extract device info from mDNS service
                hostname = name.split('.')[0]  # Remove .local suffix
                ip_address = socket.inet_ntoa(info.addresses[0])
                port = info.port

                logger.info(f"Processing mDNS device: {hostname} at {ip_address}:{port}")

                # Extract properties from TXT records
                properties = {}
                if info.properties:
                    for key, value in info.properties.items():
                        try:
                            properties[key.decode('utf-8')] = value.decode('utf-8')
                        except UnicodeDecodeError:
                            properties[key.decode('utf-8')] = str(value)

                # Extract MAC address (ESPHome includes this in hostname)
                mac_address = hostname.split('-')[-1] if '-' in hostname else "unknown"

                # Accept all ESPHome devices (not just ir- prefixed ones)
                device = ESPHomeDevice(hostname, ip_address, port, mac_address, properties)
                self.discovery_service._add_device(device)

            except Exception as e:
                logger.error(f"Error processing discovered service {name}: {e}")

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when an ESPHome service is removed"""
        hostname = name.split('.')[0]
        if hostname.startswith("ir-"):
            self.discovery_service._remove_device(hostname)

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when an ESPHome service is updated"""
        # For simplicity, treat updates as add operations
        self.add_service(zc, type_, name)


# Global discovery service instance
discovery_service = ESPHomeDiscoveryService()