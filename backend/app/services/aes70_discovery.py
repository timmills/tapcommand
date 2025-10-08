"""
AES70 Audio Zone Discovery Service

Discovers audio zones from Bosch Praesensa and other AES70-compatible amplifiers
and creates Virtual Devices for each zone.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

# AES70 imports
try:
    from aes70.controller import tcp_connection
    from aes70.controller.remote_device import RemoteDevice
    AES70_AVAILABLE = True
except ImportError:
    AES70_AVAILABLE = False
    logging.warning("AES70py not installed - audio control will not be available")

from ..models.virtual_controller import VirtualController, VirtualDevice
from ..db.database import SessionLocal

logger = logging.getLogger(__name__)


class AES70DiscoveryService:
    """
    Discover AES70 audio zones and create Virtual Devices

    This service connects to AES70-compatible amplifiers (like Bosch Praesensa)
    and discovers all configured zones via the role map.
    """

    def __init__(self):
        if not AES70_AVAILABLE:
            raise RuntimeError("AES70py library not installed")

    async def discover_praesensa_zones(
        self,
        controller_id: str,
        ip_address: str,
        port: int = 65000,
        username: Optional[str] = None,
        password: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Connect to Praesensa and discover all zones via role map

        Args:
            controller_id: Unique ID for this controller
            ip_address: IP address of Praesensa controller
            port: AES70 port (default 65000)
            username: Optional authentication username
            password: Optional authentication password

        Returns:
            List of zone configurations ready for VirtualDevice creation
        """

        logger.info(f"🔍 Discovering zones on {ip_address}:{port}")

        try:
            # Connect to AES70 device
            connection = await tcp_connection.connect(
                ip_address=ip_address,
                port=port
            )

            device = RemoteDevice(connection)
            device.set_keepalive_interval(10)

            # Get device info
            try:
                model = await device.DeviceManager.GetModelDescription()
                logger.info(f"📡 Connected to: {model}")
            except Exception as e:
                logger.warning(f"Could not get model description: {e}")
                model = "Unknown AES70 Device"

            # Get role map (named objects)
            logger.info("📋 Fetching role map...")
            role_map = await device.get_role_map()
            logger.info(f"📋 Role map has {len(role_map)} objects")

            # Find zone objects
            zones = []
            zone_number = 1

            # Look for gain/volume controls
            # Common patterns:
            # - "Zones/Lobby/Gain"
            # - "Zone1/Volume"
            # - "Output/Zone1/Gain"
            for role_path, obj in role_map.items():
                # Look for gain controls (volume objects)
                if self._is_zone_gain(role_path):
                    # Extract zone name from path
                    zone_name = self._extract_zone_name(role_path)

                    # Check if there's a mute object nearby
                    mute_path = self._find_mute_path(role_path, role_map)
                    has_mute = mute_path is not None

                    # Get gain range if available
                    min_gain, max_gain = await self._get_gain_range(obj)

                    zones.append({
                        "zone_number": zone_number,
                        "zone_name": zone_name,
                        "role_path": role_path,
                        "mute_path": mute_path,
                        "gain_range": [min_gain, max_gain],
                        "has_mute": has_mute,
                        "object_type": str(type(obj).__name__)
                    })

                    logger.info(
                        f"✓ Found zone {zone_number}: {zone_name} "
                        f"(Gain: {min_gain} to {max_gain}dB, Mute: {has_mute})"
                    )

                    zone_number += 1

            # Close connection
            await connection.close()

            logger.info(f"✅ Discovered {len(zones)} zones")
            return zones

        except Exception as e:
            logger.error(f"❌ Failed to discover zones: {e}", exc_info=True)
            raise

    def _is_zone_gain(self, role_path: str) -> bool:
        """Check if role path represents a zone gain/volume control"""
        path_lower = role_path.lower()

        # Look for gain or volume keywords
        if "gain" not in path_lower and "volume" not in path_lower:
            return False

        # Look for zone indicators
        zone_keywords = ["zone", "output", "channel", "area"]
        return any(keyword in path_lower for keyword in zone_keywords)

    def _extract_zone_name(self, role_path: str) -> str:
        """Extract a human-readable zone name from role path"""
        # Split by "/" and find meaningful parts
        parts = role_path.split("/")

        # Remove "Gain", "Volume", etc. from the end
        parts = [p for p in parts if p.lower() not in ["gain", "volume", "level"]]

        # If we have at least 2 parts, use the second-to-last (zone name)
        if len(parts) >= 2:
            return parts[-1]  # e.g., "Zones/Lobby" -> "Lobby"
        elif len(parts) == 1:
            return parts[0]
        else:
            return "Unknown Zone"

    def _find_mute_path(self, gain_path: str, role_map: Dict[str, Any]) -> Optional[str]:
        """Find corresponding mute control for a gain object"""
        # Try common mute path patterns
        patterns = [
            gain_path.replace("Gain", "Mute"),
            gain_path.replace("gain", "mute"),
            gain_path.replace("Volume", "Mute"),
            gain_path.replace("volume", "mute"),
            gain_path.replace("Level", "Mute"),
            gain_path.replace("level", "mute"),
        ]

        for pattern in patterns:
            if pattern in role_map:
                return pattern

        # Try looking in the same parent path
        parent = "/".join(gain_path.split("/")[:-1])
        for path in role_map.keys():
            if path.startswith(parent) and "mute" in path.lower():
                return path

        return None

    async def _get_gain_range(self, gain_obj: Any) -> tuple[float, float]:
        """Get min/max gain range from gain object"""
        try:
            # Try to get min/max gain
            if hasattr(gain_obj, 'GetMinGain'):
                min_gain = await gain_obj.GetMinGain()
            else:
                min_gain = -80.0

            if hasattr(gain_obj, 'GetMaxGain'):
                max_gain = await gain_obj.GetMaxGain()
            else:
                max_gain = 10.0

            return (min_gain, max_gain)

        except Exception as e:
            logger.warning(f"Could not get gain range: {e}, using defaults")
            return (-80.0, 10.0)

    def create_virtual_devices_from_zones(
        self,
        db: Session,
        controller: VirtualController,
        zones: List[Dict[str, Any]]
    ) -> List[VirtualDevice]:
        """
        Create VirtualDevice entries for discovered zones

        Args:
            db: Database session
            controller: Parent VirtualController
            zones: List of zone configurations from discover_praesensa_zones()

        Returns:
            List of created VirtualDevice objects
        """

        created_devices = []

        for zone in zones:
            # Check if device already exists
            existing = db.query(VirtualDevice).filter(
                VirtualDevice.controller_id == controller.id,
                VirtualDevice.port_number == zone["zone_number"]
            ).first()

            if existing:
                logger.info(f"⏭️  Zone {zone['zone_name']} already exists, skipping")
                continue

            # Create new Virtual Device for zone
            virtual_device = VirtualDevice(
                controller_id=controller.id,
                port_number=zone["zone_number"],
                port_id=f"{controller.controller_id}-{zone['zone_number']}",
                device_name=zone["zone_name"],
                device_type="audio_zone",
                ip_address=controller.ip_address,  # Same as controller
                port=controller.port,
                protocol="bosch_aes70",
                connection_config={
                    "role_path": zone["role_path"],
                    "mute_path": zone["mute_path"],
                    "gain_range": zone["gain_range"],
                    "default_volume": -20,
                    "object_type": zone["object_type"]
                },
                capabilities={
                    "volume": True,
                    "mute": zone["has_mute"],
                    "power": False  # Zones don't have power control
                },
                cached_power_state="on",  # Zones are always "on"
                cached_volume_level=50,  # Default 50% (middle of range)
                cached_mute_status=False,
                is_online=True,
                status_available=True,
                is_active=True
            )

            db.add(virtual_device)
            created_devices.append(virtual_device)

            logger.info(f"✅ Created Virtual Device: {zone['zone_name']}")

        db.commit()

        logger.info(f"🎉 Created {len(created_devices)} new audio zones")
        return created_devices


async def discover_and_create_audio_controller(
    ip_address: str,
    controller_name: str,
    port: int = 65000,
    venue_name: Optional[str] = None,
    location: Optional[str] = None
) -> tuple[VirtualController, List[VirtualDevice]]:
    """
    Convenience function to add a Praesensa controller and discover zones

    Args:
        ip_address: IP address of Praesensa controller
        controller_name: Friendly name for the controller
        port: AES70 port (default 65000)
        venue_name: Optional venue name
        location: Optional location

    Returns:
        Tuple of (VirtualController, List[VirtualDevice])
    """

    db = SessionLocal()

    try:
        # Generate unique controller ID
        controller_id = f"aud-praesensa-{ip_address.replace('.', '')}"

        # Check if controller already exists
        existing = db.query(VirtualController).filter(
            VirtualController.controller_id == controller_id
        ).first()

        if existing:
            logger.warning(f"Controller {controller_id} already exists")
            return existing, []

        # Create Virtual Controller
        controller = VirtualController(
            controller_id=controller_id,
            controller_name=controller_name,
            controller_type="audio",
            protocol="aes70",
            venue_name=venue_name,
            location=location,
            ip_address=ip_address,
            port=port,
            total_ports=50,  # Audio can have many zones
            connection_config={
                "protocol": "aes70",
                "port": port
            },
            capabilities={
                "volume": True,
                "mute": True,
                "zones": True
            },
            is_active=True,
            is_online=True,
            last_seen=datetime.now()
        )

        db.add(controller)
        db.commit()
        db.refresh(controller)

        logger.info(f"✅ Created Virtual Controller: {controller_name}")

        # Discover zones
        discovery = AES70DiscoveryService()
        zones = await discovery.discover_praesensa_zones(
            controller_id=controller.controller_id,
            ip_address=ip_address,
            port=port
        )

        # Create Virtual Devices for zones
        devices = discovery.create_virtual_devices_from_zones(db, controller, zones)

        return controller, devices

    finally:
        db.close()


# Example usage
if __name__ == "__main__":
    async def test():
        controller, devices = await discover_and_create_audio_controller(
            ip_address="192.168.1.100",
            controller_name="Office Audio System",
            venue_name="Main Office",
            location="AV Rack"
        )

        print(f"Created controller: {controller.controller_name}")
        print(f"Discovered {len(devices)} zones:")
        for device in devices:
            print(f"  - {device.device_name}")

    asyncio.run(test())
