"""
Sonos Speaker Discovery and Management Service

Handles discovery, adoption, and connection management for Sonos speakers using UPnP/SOAP protocol.
Based on the same patterns as Bosch Plena Matrix integration.
"""

import asyncio
import logging
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from soco import SoCo
from soco.discovery import discover

from app.db.database import SessionLocal
from app.models.virtual_controller import VirtualController, VirtualDevice


logger = logging.getLogger(__name__)


async def discover_sonos_speakers_on_network() -> list[Dict[str, Any]]:
    """
    Discover all Sonos speakers on the network using SSDP/mDNS.

    Returns:
        List of discovered speaker information dicts with:
        - ip_address: Speaker IP address
        - uid: Unique speaker ID
        - model_name: Speaker model
        - zone_name: Friendly name
        - software_version: Firmware version
        - mac_address: MAC address
        - household_id: Sonos household ID
    """
    logger.info("Starting Sonos speaker discovery...")

    try:
        # Run SoCo discovery in executor (it's synchronous)
        speakers = await asyncio.get_event_loop().run_in_executor(
            None,
            discover,
            2  # Timeout in seconds
        )

        if not speakers:
            logger.info("No Sonos speakers found on network")
            return []

        discovered = []
        for speaker in speakers:
            try:
                # Get speaker info
                info = await asyncio.get_event_loop().run_in_executor(
                    None,
                    speaker.get_speaker_info
                )

                discovered.append({
                    "ip_address": speaker.ip_address,
                    "uid": info.get("uid"),
                    "model_name": info.get("model_name"),
                    "model_number": info.get("model_number"),
                    "zone_name": info.get("zone_name"),
                    "software_version": info.get("software_version"),
                    "mac_address": info.get("mac_address"),
                    "hardware_version": info.get("hardware_version"),
                    "display_version": info.get("display_version"),
                })

                logger.info(f"Discovered Sonos speaker: {info.get('zone_name')} ({info.get('model_name')}) at {speaker.ip_address}")

            except Exception as e:
                logger.error(f"Failed to get info for speaker at {speaker.ip_address}: {e}")
                continue

        logger.info(f"Discovery complete: found {len(discovered)} Sonos speaker(s)")
        return discovered

    except Exception as e:
        logger.error(f"Sonos discovery failed: {e}")
        return []


async def discover_and_create_sonos_controller(
    ip_address: str,
    controller_name: str,
    venue_name: Optional[str] = None,
    location: Optional[str] = None
) -> Tuple[str, int]:
    """
    Create a VirtualController and VirtualDevice for a discovered Sonos speaker.

    This follows the exact pattern used by Bosch Plena Matrix:
    - One VirtualController per speaker
    - One VirtualDevice (port 1) representing the speaker itself
    - IP/port stored in connection_config JSON
    - Returns tuple of (controller_id, num_devices)

    Args:
        ip_address: IP address of Sonos speaker
        controller_name: Friendly name for the controller
        venue_name: Optional venue name
        location: Optional location description

    Returns:
        Tuple of (controller_id, number_of_devices_created)

    Raises:
        Exception: If speaker cannot be reached or controller creation fails
    """
    db = SessionLocal()

    try:
        logger.info(f"Creating Sonos controller for speaker at {ip_address}")

        # Connect to speaker
        speaker = SoCo(ip_address)

        # Query speaker information
        speaker_info = await asyncio.get_event_loop().run_in_executor(
            None,
            speaker.get_speaker_info
        )

        # Get current volume and mute status for cache
        volume = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: speaker.volume
        )
        mute = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: speaker.mute
        )

        # Generate controller_id (following pattern: sonos-192-168-1-100)
        controller_id = f"sonos-{ip_address.replace('.', '-')}"

        # Check if controller already exists
        existing = db.query(VirtualController).filter(
            VirtualController.controller_id == controller_id
        ).first()

        if existing:
            logger.warning(f"Controller {controller_id} already exists, updating...")
            controller = existing
            controller.is_online = True
            controller.last_seen = datetime.now()
            # Update connection_config with latest info
            controller.connection_config = {
                "ip_address": ip_address,
                "port": 1400,
                "uid": speaker_info.get("uid"),
                "model_name": speaker_info.get("model_name"),
                "model_number": speaker_info.get("model_number"),
                "zone_name": speaker_info.get("zone_name"),
                "software_version": speaker_info.get("software_version"),
                "mac_address": speaker_info.get("mac_address"),
                "hardware_version": speaker_info.get("hardware_version"),
            }
        else:
            # Create new VirtualController
            controller = VirtualController(
                controller_id=controller_id,
                controller_name=controller_name or speaker_info.get("zone_name", "Sonos Speaker"),
                controller_type="audio",
                protocol="sonos_upnp",
                venue_name=venue_name,
                location=location,
                total_ports=1,  # One speaker = one port
                capabilities={
                    "volume": True,
                    "mute": True,
                    "play": True,
                    "pause": True,
                    "stop": True,
                    "next": True,
                    "previous": True,
                    "seek": True,
                    "queue": True,
                    "grouping": True,
                    "eq": True,
                },
                is_active=True,
                is_online=True,
                last_seen=datetime.now(),
                connection_config={
                    "ip_address": ip_address,
                    "port": 1400,
                    "uid": speaker_info.get("uid"),
                    "model_name": speaker_info.get("model_name"),
                    "model_number": speaker_info.get("model_number"),
                    "zone_name": speaker_info.get("zone_name"),
                    "software_version": speaker_info.get("software_version"),
                    "mac_address": speaker_info.get("mac_address"),
                    "hardware_version": speaker_info.get("hardware_version"),
                }
            )
            db.add(controller)
            db.flush()  # Get the controller.id

            logger.info(f"Created VirtualController: {controller_id}")

        # Check if device already exists
        existing_device = db.query(VirtualDevice).filter(
            VirtualDevice.controller_id == controller.id,
            VirtualDevice.port_number == 1
        ).first()

        if existing_device:
            logger.info(f"Device already exists for controller {controller_id}, updating...")
            device = existing_device
            device.is_online = True
            device.last_seen = datetime.now()
            device.cached_volume_level = volume
            device.cached_mute_status = mute
            device.ip_address = ip_address
        else:
            # Create VirtualDevice (port 1)
            device = VirtualDevice(
                controller_id=controller.id,
                port_number=1,
                port_id=f"{controller_id}-1",
                device_name=speaker_info.get("zone_name", "Sonos Speaker"),
                device_type="audio_zone",
                ip_address=ip_address,
                port=1400,
                mac_address=speaker_info.get("mac_address"),
                protocol="sonos_upnp",
                connection_config={
                    "uid": speaker_info.get("uid"),
                },
                capabilities={
                    "volume": True,
                    "mute": True,
                    "play": True,
                    "pause": True,
                    "stop": True,
                },
                cached_volume_level=volume,
                cached_mute_status=mute,
                is_active=True,
                is_online=True,
                last_seen=datetime.now(),
                status_available=True,
            )
            db.add(device)

            logger.info(f"Created VirtualDevice: {device.device_name} (port 1)")

        db.commit()

        logger.info(f"Successfully created/updated Sonos controller {controller_id}")
        return (controller_id, 1)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create Sonos controller for {ip_address}: {e}")
        raise

    finally:
        db.close()


async def test_sonos_connection(ip_address: str) -> Dict[str, Any]:
    """
    Test connection to a Sonos speaker and retrieve basic info.

    Args:
        ip_address: IP address of Sonos speaker

    Returns:
        Dict with connection test results and speaker info
    """
    try:
        logger.info(f"Testing connection to Sonos speaker at {ip_address}")

        speaker = SoCo(ip_address)

        # Get speaker info
        info = await asyncio.get_event_loop().run_in_executor(
            None,
            speaker.get_speaker_info
        )

        # Get current state
        volume = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: speaker.volume
        )
        mute = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: speaker.mute
        )

        # Get transport info
        transport_info = await asyncio.get_event_loop().run_in_executor(
            None,
            speaker.get_current_transport_info
        )

        return {
            "success": True,
            "ip_address": ip_address,
            "speaker_info": info,
            "current_state": {
                "volume": volume,
                "mute": mute,
                "transport_state": transport_info.get("current_transport_state"),
            }
        }

    except Exception as e:
        logger.error(f"Failed to test connection to {ip_address}: {e}")
        return {
            "success": False,
            "ip_address": ip_address,
            "error": str(e)
        }


async def get_sonos_speaker_status(controller_id: str, db: Session) -> Optional[Dict[str, Any]]:
    """
    Query current status of a Sonos speaker.

    Args:
        controller_id: Controller ID (e.g., "sonos-192-168-1-100")
        db: Database session

    Returns:
        Dict with current speaker status or None if offline
    """
    try:
        # Lookup controller
        controller = db.query(VirtualController).filter(
            VirtualController.controller_id == controller_id
        ).first()

        if not controller:
            logger.error(f"Controller {controller_id} not found")
            return None

        # Get IP from connection_config
        connection_config = controller.connection_config or {}
        ip_address = connection_config.get("ip_address")

        if not ip_address:
            logger.error(f"No IP address in connection_config for {controller_id}")
            return None

        # Connect to speaker
        speaker = SoCo(ip_address)

        # Query status (run in executor)
        volume = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: speaker.volume
        )
        mute = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: speaker.mute
        )
        transport_info = await asyncio.get_event_loop().run_in_executor(
            None,
            speaker.get_current_transport_info
        )

        status = {
            "controller_id": controller_id,
            "ip_address": ip_address,
            "volume": volume,
            "mute": mute,
            "transport_state": transport_info.get("current_transport_state"),
            "is_online": True,
        }

        # Update database cache
        device = db.query(VirtualDevice).filter(
            VirtualDevice.controller_id == controller.id,
            VirtualDevice.port_number == 1
        ).first()

        if device:
            device.cached_volume_level = volume
            device.cached_mute_status = mute
            device.is_online = True
            device.last_seen = datetime.now()
            db.commit()

        return status

    except Exception as e:
        logger.error(f"Failed to get status for {controller_id}: {e}")
        return None
