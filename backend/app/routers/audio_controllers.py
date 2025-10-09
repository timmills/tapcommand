"""
Audio Controller API Endpoints

Manage audio amplifiers (Bosch Praesensa, etc.) and their zones
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ..db.database import get_db
from ..models.virtual_controller import VirtualController, VirtualDevice
from ..services.aes70_discovery import AES70DiscoveryService, discover_and_create_audio_controller
from ..services.plena_matrix_discovery import PlenaMatrixDiscoveryService, discover_and_create_plena_matrix_controller
from ..services.command_queue import CommandQueueService

router = APIRouter(prefix="/api/audio", tags=["audio"])


# Pydantic models
class AudioControllerCreate(BaseModel):
    ip_address: str
    controller_name: str
    protocol: str = "bosch_aes70"  # "bosch_aes70" or "bosch_plena_matrix"
    port: Optional[int] = None  # Will default based on protocol
    total_zones: Optional[int] = None  # For Plena Matrix (default 4)
    venue_name: Optional[str] = None
    location: Optional[str] = None


class AudioZoneResponse(BaseModel):
    id: int
    controller_id: int
    controller_name: str
    zone_number: int
    zone_name: str
    device_type: str
    protocol: str
    volume_level: Optional[int]
    is_muted: Optional[bool]
    is_online: bool
    gain_range: Optional[List[float]]
    has_mute: bool

    class Config:
        from_attributes = True


class AudioControllerResponse(BaseModel):
    id: int
    controller_id: str
    controller_name: str
    controller_type: str
    ip_address: str
    port: int
    is_online: bool
    total_zones: int
    zones: List[AudioZoneResponse]

    class Config:
        from_attributes = True


class VolumeControl(BaseModel):
    volume: int  # 0-100


class MuteControl(BaseModel):
    mute: bool


@router.post("/controllers/discover", response_model=AudioControllerResponse)
async def discover_audio_controller(
    controller_data: AudioControllerCreate,
    db: Session = Depends(get_db)
):
    """
    Add an audio amplifier and discover zones

    Supports:
    - Bosch Praesensa (AES70/OMNEO) - port 65000
    - Bosch Plena Matrix (UDP API) - port 12128

    This will:
    1. Create a Virtual Controller for the amplifier
    2. Connect via appropriate protocol
    3. Discover all configured zones
    4. Create Virtual Devices for each zone
    """

    try:
        # Route to appropriate discovery service based on protocol
        if controller_data.protocol == "bosch_plena_matrix":
            # Plena Matrix discovery
            port = controller_data.port or 12128
            total_zones = controller_data.total_zones or 4

            controller, devices = await discover_and_create_plena_matrix_controller(
                ip_address=controller_data.ip_address,
                controller_name=controller_data.controller_name,
                port=port,
                total_zones=total_zones,
                venue_name=controller_data.venue_name,
                location=controller_data.location
            )

        elif controller_data.protocol == "bosch_aes70":
            # Praesensa AES70 discovery
            port = controller_data.port or 65000

            controller, devices = await discover_and_create_audio_controller(
                ip_address=controller_data.ip_address,
                controller_name=controller_data.controller_name,
                port=port,
                venue_name=controller_data.venue_name,
                location=controller_data.location
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported protocol: {controller_data.protocol}"
            )

        # Format response
        zones = []
        for device in devices:
            gain_range = device.connection_config.get("gain_range") if device.connection_config else None
            has_mute = device.connection_config.get("mute_path") is not None if device.connection_config else False

            zones.append(AudioZoneResponse(
                id=device.id,
                controller_id=device.controller_id,
                controller_name=controller.controller_name,
                zone_number=device.port_number,
                zone_name=device.device_name,
                device_type=device.device_type,
                protocol=device.protocol,
                volume_level=device.cached_volume_level,
                is_muted=device.cached_mute_status,
                is_online=device.is_online,
                gain_range=gain_range,
                has_mute=has_mute
            ))

        return AudioControllerResponse(
            id=controller.id,
            controller_id=controller.controller_id,
            controller_name=controller.controller_name,
            controller_type=controller.controller_type,
            ip_address=controller.ip_address,
            port=controller.port,
            is_online=controller.is_online,
            total_zones=len(devices),
            zones=zones
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to discover controller: {str(e)}")


@router.get("/controllers", response_model=List[AudioControllerResponse])
async def list_audio_controllers(db: Session = Depends(get_db)):
    """Get all audio controllers with their zones"""

    controllers = db.query(VirtualController).filter(
        VirtualController.controller_type == "audio"
    ).all()

    result = []
    for controller in controllers:
        zones = []
        for device in controller.virtual_devices:
            gain_range = device.connection_config.get("gain_range") if device.connection_config else None
            has_mute = device.connection_config.get("mute_path") is not None if device.connection_config else False

            zones.append(AudioZoneResponse(
                id=device.id,
                controller_id=device.controller_id,
                controller_name=controller.controller_name,
                zone_number=device.port_number,
                zone_name=device.device_name,
                device_type=device.device_type,
                protocol=device.protocol,
                volume_level=device.cached_volume_level,
                is_muted=device.cached_mute_status,
                is_online=device.is_online,
                gain_range=gain_range,
                has_mute=has_mute
            ))

        result.append(AudioControllerResponse(
            id=controller.id,
            controller_id=controller.controller_id,
            controller_name=controller.controller_name,
            controller_type=controller.controller_type,
            ip_address=controller.ip_address,
            port=controller.port,
            is_online=controller.is_online,
            total_zones=len(zones),
            zones=zones
        ))

    return result


@router.get("/zones", response_model=List[AudioZoneResponse])
async def list_audio_zones(
    controller_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all audio zones, optionally filtered by controller"""

    query = db.query(VirtualDevice).filter(
        VirtualDevice.device_type == "audio_zone"
    )

    if controller_id:
        controller = db.query(VirtualController).filter(
            VirtualController.controller_id == controller_id
        ).first()

        if not controller:
            raise HTTPException(status_code=404, detail="Controller not found")

        query = query.filter(VirtualDevice.controller_id == controller.id)

    zones = query.all()

    result = []
    for zone in zones:
        controller = db.query(VirtualController).get(zone.controller_id)
        gain_range = zone.connection_config.get("gain_range") if zone.connection_config else None
        has_mute = zone.connection_config.get("mute_path") is not None if zone.connection_config else False

        result.append(AudioZoneResponse(
            id=zone.id,
            controller_id=zone.controller_id,
            controller_name=controller.controller_name if controller else "Unknown",
            zone_number=zone.port_number,
            zone_name=zone.device_name,
            device_type=zone.device_type,
            protocol=zone.protocol,
            volume_level=zone.cached_volume_level,
            is_muted=zone.cached_mute_status,
            is_online=zone.is_online,
            gain_range=gain_range,
            has_mute=has_mute
        ))

    return result


@router.post("/zones/{zone_id}/volume")
async def set_zone_volume(
    zone_id: int,
    volume_data: VolumeControl,
    db: Session = Depends(get_db)
):
    """Set zone volume (0-100)"""

    zone = db.query(VirtualDevice).get(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    controller = db.query(VirtualController).get(zone.controller_id)
    if not controller:
        raise HTTPException(status_code=404, detail="Controller not found")

    # Queue command
    cmd = CommandQueueService.queue_command(
        db=db,
        hostname=controller.controller_id,
        port=zone.port_number,
        command="set_volume",
        parameters={"volume": volume_data.volume, "zone_number": zone.port_number}
    )

    return {
        "success": True,
        "message": f"Queued volume change for {zone.device_name}",
        "command_id": cmd.id,
        "volume": volume_data.volume
    }


@router.post("/zones/{zone_id}/volume/up")
async def volume_up(zone_id: int, db: Session = Depends(get_db)):
    """Increase zone volume by 5%"""

    zone = db.query(VirtualDevice).get(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    controller = db.query(VirtualController).get(zone.controller_id)

    cmd = CommandQueueService.queue_command(
        db=db,
        hostname=controller.controller_id,
        port=zone.port_number,
        command="volume_up",
        parameters={"zone_number": zone.port_number}
    )

    return {
        "success": True,
        "message": f"Queued volume up for {zone.device_name}",
        "command_id": cmd.id
    }


@router.post("/zones/{zone_id}/volume/down")
async def volume_down(zone_id: int, db: Session = Depends(get_db)):
    """Decrease zone volume by 5%"""

    zone = db.query(VirtualDevice).get(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    controller = db.query(VirtualController).get(zone.controller_id)

    cmd = CommandQueueService.queue_command(
        db=db,
        hostname=controller.controller_id,
        port=zone.port_number,
        command="volume_down",
        parameters={"zone_number": zone.port_number}
    )

    return {
        "success": True,
        "message": f"Queued volume down for {zone.device_name}",
        "command_id": cmd.id
    }


@router.post("/zones/{zone_id}/mute")
async def toggle_mute(
    zone_id: int,
    mute_data: Optional[MuteControl] = None,
    db: Session = Depends(get_db)
):
    """Mute/unmute zone or toggle if no mute parameter provided"""

    zone = db.query(VirtualDevice).get(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    controller = db.query(VirtualController).get(zone.controller_id)

    # Determine command
    if mute_data is not None:
        command = "mute" if mute_data.mute else "unmute"
    else:
        command = "toggle_mute"

    cmd = CommandQueueService.queue_command(
        db=db,
        hostname=controller.controller_id,
        port=zone.port_number,
        command=command,
        parameters={"zone_number": zone.port_number}
    )

    return {
        "success": True,
        "message": f"Queued mute command for {zone.device_name}",
        "command_id": cmd.id
    }


@router.delete("/controllers/{controller_id}")
async def delete_audio_controller(
    controller_id: str,
    db: Session = Depends(get_db)
):
    """Delete an audio controller and all its zones"""

    controller = db.query(VirtualController).filter(
        VirtualController.controller_id == controller_id,
        VirtualController.controller_type == "audio"
    ).first()

    if not controller:
        raise HTTPException(status_code=404, detail="Audio controller not found")

    # Delete controller (cascade will delete zones)
    db.delete(controller)
    db.commit()

    return {
        "success": True,
        "message": f"Deleted audio controller {controller.controller_name}"
    }


@router.post("/controllers/{controller_id}/rediscover")
async def rediscover_zones(
    controller_id: str,
    db: Session = Depends(get_db)
):
    """Re-discover zones for an existing controller"""

    controller = db.query(VirtualController).filter(
        VirtualController.controller_id == controller_id,
        VirtualController.controller_type == "audio"
    ).first()

    if not controller:
        raise HTTPException(status_code=404, detail="Audio controller not found")

    try:
        # Discover zones
        discovery = AES70DiscoveryService()
        zones = await discovery.discover_praesensa_zones(
            controller_id=controller.controller_id,
            ip_address=controller.ip_address,
            port=controller.port or 65000
        )

        # Create Virtual Devices for new zones
        devices = discovery.create_virtual_devices_from_zones(db, controller, zones)

        return {
            "success": True,
            "message": f"Re-discovered zones for {controller.controller_name}",
            "total_zones": len(zones),
            "new_zones": len(devices)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rediscover zones: {str(e)}")
