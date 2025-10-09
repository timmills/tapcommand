"""
Bosch Plena Matrix Discovery Service

Discover and configure Bosch Plena Matrix amplifiers (PLM-4Px2x series)
via UDP API
"""

import asyncio
import logging
import socket
import struct
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session

from ..models.virtual_controller import VirtualController, VirtualDevice
from ..db.database import SessionLocal

logger = logging.getLogger(__name__)


@dataclass
class PlenaMatrixInfo:
    """Information about a Plena Matrix device"""
    device_name: str
    model: str
    firmware_version: str
    total_zones: int
    zones: List[Dict[str, Any]]


class PlenaMatrixDiscoveryService:
    """Discover and configure Plena Matrix amplifiers"""

    # UDP Ports
    RECEIVE_PORT = 12128
    TRANSMIT_PORT = 12129

    # Command types
    CMD_PING = b'PING'
    CMD_WHAT = b'WHAT'  # Get device info
    CMD_EXPL = b'EXPL'  # Get extended info

    def __init__(self):
        self._sequence_number = 0

    def _get_next_sequence(self) -> int:
        """Get next sequence number"""
        seq = self._sequence_number
        self._sequence_number = (seq + 1) % 65536
        return seq

    async def ping_device(self, ip_address: str, port: int = RECEIVE_PORT, timeout: float = 2.0) -> bool:
        """
        Ping a Plena Matrix device to check if it's reachable

        Returns:
            True if device responds, False otherwise
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)

            # Build PING packet
            seq = self._get_next_sequence()
            packet = self.CMD_PING + struct.pack('>HH', seq, 0)  # No data

            # Send ping
            sock.sendto(packet, (ip_address, port))
            logger.debug(f"Sent PING to {ip_address}:{port}")

            # Wait for response
            response, addr = sock.recvfrom(1024)
            sock.close()

            logger.info(f"✓ Plena Matrix device responded from {addr}")
            return True

        except socket.timeout:
            logger.debug(f"Ping timeout for {ip_address}")
            return False
        except Exception as e:
            logger.error(f"Ping error for {ip_address}: {e}")
            return False

    async def get_device_info(self, ip_address: str, port: int = RECEIVE_PORT) -> Optional[Dict[str, Any]]:
        """
        Get device information from Plena Matrix

        Returns:
            Dictionary with device info or None if failed
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3.0)

            # Build WHAT packet
            seq = self._get_next_sequence()
            packet = self.CMD_WHAT + struct.pack('>HH', seq, 0)

            # Send command
            sock.sendto(packet, (ip_address, port))
            logger.debug(f"Sent WHAT to {ip_address}:{port}")

            # Wait for response
            response, addr = sock.recvfrom(1024)
            sock.close()

            # Parse response
            # Format: [CMD(4)][SEQ(2)][LEN(2)][DATA]
            if len(response) < 8:
                logger.warning(f"Invalid response from {ip_address}")
                return None

            cmd = response[0:4]
            seq_resp = struct.unpack('>H', response[4:6])[0]
            length = struct.unpack('>H', response[6:8])[0]
            data = response[8:8+length]

            # Parse device info from data
            # Simplified parsing - actual format depends on Plena Matrix protocol
            device_info = {
                "ip_address": ip_address,
                "model": "PLM-4P220",  # Default, should be parsed from response
                "firmware_version": "1.0.0",  # Should be parsed from response
                "total_zones": 4,  # Default for PLM-4P220
                "raw_response": data.hex()
            }

            logger.info(f"✓ Retrieved device info from {ip_address}")
            return device_info

        except Exception as e:
            logger.error(f"Failed to get device info from {ip_address}: {e}")
            return None

    async def discover_zones(
        self,
        ip_address: str,
        total_zones: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Discover zones on a Plena Matrix amplifier

        For now, creates default zones based on total_zones count.
        In a full implementation, this would query the device for actual zone configuration.

        Args:
            ip_address: Amplifier IP address
            total_zones: Number of zones (4 for PLM-4P220/120, 2 for bridged mode)

        Returns:
            List of zone dictionaries
        """
        zones = []

        for zone_num in range(1, total_zones + 1):
            zone = {
                "zone_number": zone_num,
                "zone_name": f"Zone {zone_num}",
                "zone_index": zone_num - 1,  # 0-indexed for API
                "gain_range": [-80.0, 10.0],  # Typical Plena Matrix range
                "supports_mute": True,
                "is_active": True
            }
            zones.append(zone)

        logger.info(f"Discovered {len(zones)} zones on {ip_address}")
        return zones

    def create_virtual_devices_from_zones(
        self,
        db: Session,
        controller: VirtualController,
        zones: List[Dict[str, Any]]
    ) -> List[VirtualDevice]:
        """
        Create VirtualDevice entries for each zone

        Args:
            db: Database session
            controller: Parent VirtualController
            zones: List of zone dictionaries from discover_zones()

        Returns:
            List of created VirtualDevice objects
        """
        devices = []

        for zone in zones:
            # Check if zone already exists
            existing = db.query(VirtualDevice).filter(
                VirtualDevice.controller_id == controller.id,
                VirtualDevice.port_number == zone["zone_number"]
            ).first()

            if existing:
                logger.info(f"Zone {zone['zone_name']} already exists, skipping")
                devices.append(existing)
                continue

            # Create new VirtualDevice for this zone
            device = VirtualDevice(
                controller_id=controller.id,
                port_number=zone["zone_number"],
                device_name=zone["zone_name"],
                device_type="audio_zone",
                protocol="bosch_plena_matrix",
                ip_address=controller.ip_address,
                port=controller.port,
                is_active=zone.get("is_active", True),
                is_online=True,
                connection_config={
                    "zone_index": zone["zone_index"],
                    "gain_range": zone["gain_range"],
                    "supports_mute": zone["supports_mute"]
                },
                cached_volume_level=50,  # Default to 50%
                cached_mute_status=False
            )

            db.add(device)
            devices.append(device)
            logger.info(f"✓ Created zone: {zone['zone_name']}")

        db.commit()
        return devices


async def discover_and_create_plena_matrix_controller(
    ip_address: str,
    controller_name: str,
    port: int = 12128,
    total_zones: int = 4,
    venue_name: Optional[str] = None,
    location: Optional[str] = None
) -> Tuple[VirtualController, List[VirtualDevice]]:
    """
    Discover a Plena Matrix amplifier and create controller + zones

    Args:
        ip_address: Amplifier IP address
        controller_name: Friendly name for the controller
        port: UDP port (default 12128)
        total_zones: Number of zones (4 for PLM-4P220/120)
        venue_name: Optional venue name
        location: Optional location tag

    Returns:
        Tuple of (VirtualController, List[VirtualDevice])

    Raises:
        Exception if discovery or creation fails
    """
    db = SessionLocal()
    discovery = PlenaMatrixDiscoveryService()

    try:
        # Step 1: Ping device
        logger.info(f"Pinging Plena Matrix at {ip_address}...")
        if not await discovery.ping_device(ip_address, port):
            raise Exception(f"Plena Matrix at {ip_address} not responding")

        # Step 2: Get device info
        logger.info(f"Getting device info from {ip_address}...")
        device_info = await discovery.get_device_info(ip_address, port)

        if not device_info:
            logger.warning(f"Could not get device info, using defaults")
            device_info = {
                "model": "PLM-4P220",
                "firmware_version": "Unknown"
            }

        # Step 3: Create Virtual Controller
        controller_id = f"plm-{ip_address.replace('.', '-')}"

        # Check if controller already exists
        existing_controller = db.query(VirtualController).filter(
            VirtualController.controller_id == controller_id
        ).first()

        if existing_controller:
            logger.info(f"Controller {controller_id} already exists, using existing")
            controller = existing_controller
        else:
            controller = VirtualController(
                controller_id=controller_id,
                controller_name=controller_name,
                controller_type="audio",
                protocol="bosch_plena_matrix",
                ip_address=ip_address,
                port=port,
                venue_name=venue_name,
                location=location,
                is_online=True,
                device_model=device_info.get("model", "PLM-4P220"),
                firmware_version=device_info.get("firmware_version", "Unknown")
            )
            db.add(controller)
            db.commit()
            db.refresh(controller)
            logger.info(f"✓ Created controller: {controller_name}")

        # Step 4: Discover zones
        logger.info(f"Discovering zones on {controller_name}...")
        zones = await discovery.discover_zones(ip_address, total_zones)

        # Step 5: Create Virtual Devices for zones
        devices = discovery.create_virtual_devices_from_zones(db, controller, zones)

        logger.info(f"✅ Successfully configured {controller_name} with {len(devices)} zones")
        return (controller, devices)

    except Exception as e:
        logger.error(f"Failed to discover Plena Matrix: {e}", exc_info=True)
        db.rollback()
        raise

    finally:
        db.close()
