from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from ..db.database import get_db
from ..models.device import Device, CommandLog
from ..models.device_management import ManagedDevice
from ..services.settings_service import settings_service
from ..services.discovery import discovery_service
from ..services.esphome_client import esphome_manager

router = APIRouter()


# Pydantic models for API
class DeviceResponse(BaseModel):
    id: int
    hostname: str
    mac_address: str
    ip_address: str
    friendly_name: Optional[str]
    device_type: str
    firmware_version: Optional[str]
    venue_name: Optional[str]
    location: Optional[str]
    is_online: bool
    last_seen: datetime
    capabilities: Optional[Dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeviceUpdate(BaseModel):
    friendly_name: Optional[str] = None
    venue_name: Optional[str] = None
    location: Optional[str] = None


class CommandRequest(BaseModel):
    command: str  # "power", "mute", "channel", etc.
    box: Optional[int] = 0  # For multi-device setups
    channel: Optional[str] = None  # For channel commands
    digit: Optional[int] = None  # For number commands


class CommandResponse(BaseModel):
    success: bool
    message: str
    execution_time_ms: Optional[int] = None


class BulkCommandRequest(BaseModel):
    devices: List[str]  # List of hostnames
    command: str
    box: Optional[int] = 0
    channel: Optional[str] = None
    digit: Optional[int] = None


@router.post("/discovery/start")
async def start_discovery():
    """Start device discovery (idempotent)"""
    if discovery_service.is_running():
        return {"message": "Device discovery already running", "status": "already_started"}

    await discovery_service.start_discovery()
    return {"message": "Device discovery started", "status": "started"}


@router.post("/discovery/stop")
async def stop_discovery():
    """Stop device discovery (idempotent)"""
    if not discovery_service.is_running():
        return {"message": "Device discovery already stopped", "status": "already_stopped"}

    await discovery_service.stop_discovery()
    return {"message": "Device discovery stopped", "status": "stopped"}


@router.get("/discovery/status")
async def get_discovery_status():
    """Get current discovery service status"""
    return {
        "running": discovery_service.is_running(),
        "device_count": len(discovery_service.get_discovered_devices()),
        "service_type": "ESPHome mDNS Discovery"
    }


@router.get("/discovery/devices")
async def get_discovered_devices(db: Session = Depends(get_db)):
    """Get all currently discovered devices (excluding managed ones)"""
    devices = discovery_service.get_discovered_devices()

    # Build a set of hostnames that are already managed so we can filter them out
    managed_hosts = {
        row[0]
        for row in db.query(ManagedDevice.hostname).all()
    }

    filtered = [device for device in devices if device.hostname not in managed_hosts]
    return {"devices": [device.to_dict() for device in filtered]}


@router.get("/", response_model=List[DeviceResponse])
async def get_devices(db: Session = Depends(get_db)):
    """Get all registered devices"""
    devices = db.query(Device).all()
    return devices


@router.get("/{hostname}", response_model=DeviceResponse)
async def get_device(hostname: str, db: Session = Depends(get_db)):
    """Get a specific device by hostname"""
    device = db.query(Device).filter(Device.hostname == hostname).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.post("/register/{hostname}")
async def register_device(hostname: str, device_update: DeviceUpdate, db: Session = Depends(get_db)):
    """Register a discovered device"""
    # Check if device was discovered
    discovered_device = discovery_service.get_device_by_hostname(hostname)
    if not discovered_device:
        raise HTTPException(status_code=404, detail="Device not found in discovery")

    # Check if already registered
    existing_device = db.query(Device).filter(Device.hostname == hostname).first()
    if existing_device:
        # Update existing device
        existing_device.ip_address = discovered_device.ip_address
        existing_device.is_online = True
        existing_device.last_seen = datetime.now()
        if device_update.friendly_name:
            existing_device.friendly_name = device_update.friendly_name
        if device_update.venue_name:
            existing_device.venue_name = device_update.venue_name
        if device_update.location:
            existing_device.location = device_update.location
        db.commit()
        return existing_device

    # Create new device
    device = Device(
        hostname=discovered_device.hostname,
        mac_address=discovered_device.mac_address,
        ip_address=discovered_device.ip_address,
        friendly_name=device_update.friendly_name or discovered_device.friendly_name,
        device_type=discovered_device.device_type,
        firmware_version=discovered_device.version,
        venue_name=device_update.venue_name,
        location=device_update.location,
        is_online=True,
        capabilities={"outputs": 5}  # All devices have 5 IR outputs
    )

    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.put("/{hostname}", response_model=DeviceResponse)
async def update_device(hostname: str, device_update: DeviceUpdate, db: Session = Depends(get_db)):
    """Update device information"""
    device = db.query(Device).filter(Device.hostname == hostname).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if device_update.friendly_name is not None:
        device.friendly_name = device_update.friendly_name
    if device_update.venue_name is not None:
        device.venue_name = device_update.venue_name
    if device_update.location is not None:
        device.location = device_update.location

    db.commit()
    db.refresh(device)
    return device


@router.post("/{hostname}/command", response_model=CommandResponse)
async def send_command(hostname: str, command_request: CommandRequest, db: Session = Depends(get_db)):
    """Send a command to a specific device"""
    # Get device from database
    device = db.query(Device).filter(Device.hostname == hostname).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    start_time = datetime.now()
    success = False
    error_message = None

    try:
        api_key = None
        managed = db.query(ManagedDevice).filter(ManagedDevice.hostname == hostname).first()
        if managed and managed.api_key:
            api_key = managed.api_key
        if not api_key:
            api_key = settings_service.get_setting("esphome_api_key")

        # Send universal TV command (supports multi-device setups)
        success = await esphome_manager.send_tv_command(
            hostname=device.hostname,
            ip_address=device.ip_address,
            command=command_request.command,
            box=command_request.box or 0,
            channel=command_request.channel,
            digit=command_request.digit,
            api_key=api_key,
        )

        if success:
            message = f"Command '{command_request.command}' sent successfully"
        else:
            message = f"Failed to send command '{command_request.command}'"
            error_message = "Command execution failed"

    except Exception as e:
        success = False
        message = f"Error sending command: {str(e)}"
        error_message = str(e)

    # Calculate execution time
    execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

    # Log the command
    command_log = CommandLog(
        device_hostname=hostname,
        command_type=command_request.command,
        command_data=command_request.dict(),
        status="success" if success else "failed",
        error_message=error_message,
        execution_time_ms=execution_time,
        source="api"
    )
    db.add(command_log)
    db.commit()

    return CommandResponse(
        success=success,
        message=message,
        execution_time_ms=execution_time
    )


@router.post("/bulk-command")
async def send_bulk_command(bulk_request: BulkCommandRequest, db: Session = Depends(get_db)):
    """Send a command to multiple devices"""
    results = {}

    for hostname in bulk_request.devices:
        command_request = CommandRequest(
            command=bulk_request.command,
            box=bulk_request.box,
            channel=bulk_request.channel,
            digit=bulk_request.digit
        )

        try:
            result = await send_command(hostname, command_request, db)
            results[hostname] = result.dict()
        except HTTPException as e:
            results[hostname] = {"success": False, "message": str(e.detail)}
        except Exception as e:
            results[hostname] = {"success": False, "message": str(e)}

    return {"results": results}


@router.get("/{hostname}/health")
async def health_check(hostname: str, db: Session = Depends(get_db)):
    """Perform health check on a device"""
    device = db.query(Device).filter(Device.hostname == hostname).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    client = esphome_manager.get_client(device.hostname, device.ip_address)
    is_healthy = await client.health_check()

    # Update device status
    device.is_online = is_healthy
    device.last_seen = datetime.now()
    db.commit()

    return {
        "hostname": hostname,
        "is_healthy": is_healthy,
        "last_checked": datetime.now()
    }


@router.get("/{hostname}/logs")
async def get_device_logs(hostname: str, limit: int = 50, db: Session = Depends(get_db)):
    """Get command logs for a device"""
    logs = (
        db.query(CommandLog)
        .filter(CommandLog.device_hostname == hostname)
        .order_by(CommandLog.created_at.desc())
        .limit(limit)
        .all()
    )

    return {"logs": logs}
