import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from ..db.database import get_db
from ..models.device_management import ManagedDevice, IRPort, DeviceDiscovery, DeviceTag
from ..models.device import Device, Channel
from ..services.discovery import discovery_service
from ..services.esphome_client import esphome_manager
from ..services.device_health import health_checker

router = APIRouter()

logger = logging.getLogger(__name__)


def _normalize_mac(mac: Optional[str]) -> Optional[str]:
    """Normalize MAC address to last 6 hex digits format (e.g., 'DCF89F')"""
    if not mac:
        return None
    clean = ''.join(ch for ch in mac if ch.isalnum())
    if len(clean) == 12:
        # Return only the last 6 hex digits (last 3 bytes) in uppercase
        return clean[-6:].upper()
    elif len(clean) == 6:
        # Already in 6-digit format
        return clean.upper()
    return mac.upper()


def _extract_mac(capabilities: Optional[Dict[str, Any]]) -> Optional[str]:
    if not capabilities or not isinstance(capabilities, dict):
        return None

    metadata = capabilities.get("metadata")
    if isinstance(metadata, dict):
        mac = metadata.get("mac") or metadata.get("mac_address")
        if mac:
            return mac

    return capabilities.get("mac") or capabilities.get("mac_address")


def _sync_ports_from_capabilities(device: ManagedDevice, capabilities: Optional[Dict[str, Any]]):
    if not capabilities or not isinstance(capabilities, dict):
        return

    ports_payload = capabilities.get("ports")
    if not isinstance(ports_payload, list):
        return

    port_map: Dict[int, Dict[str, Any]] = {}
    for entry in ports_payload:
        try:
            port_number = int(entry.get("port"))
        except (TypeError, ValueError):
            continue
        port_map[port_number] = entry

    for port in device.ir_ports:
        entry = port_map.get(port.port_number)
        if entry:
            port.is_active = True
            description = entry.get("description")
            if description and not (port.connected_device_name and port.connected_device_name.strip()):
                port.connected_device_name = description
        else:
            port.is_active = False


def _normalize_tag_ids(tag_ids: Optional[List[int]]) -> Optional[List[int]]:
    """Ensure tag IDs are stored as a sorted list of unique integers or None."""
    if not tag_ids:
        return None

    normalized: List[int] = []
    seen = set()
    for tag_id in tag_ids:
        try:
            value = int(tag_id)
        except (TypeError, ValueError):
            continue
        if value not in seen:
            seen.add(value)
            normalized.append(value)

    normalized.sort()
    return normalized or None


def _normalize_default_channel(default_channel: Optional[str]) -> Optional[str]:
    if default_channel is None:
        return None
    cleaned = default_channel.strip()
    return cleaned or None


def _refresh_tag_usage_counts(db: Session) -> None:
    """Recalculate usage counts for every device tag based on IR port assignments."""
    tags = db.query(DeviceTag).all()
    port_rows = db.query(IRPort.tag_ids).all()

    for tag in tags:
        usage = 0
        for (tag_list,) in port_rows:
            if tag_list and tag.id in tag_list:
                usage += 1
        tag.usage_count = usage


class IRPortRequest(BaseModel):
    port_number: int
    connected_device_name: Optional[str] = None
    is_active: bool = True
    cable_length: Optional[str] = None
    installation_notes: Optional[str] = None
    tag_ids: Optional[List[int]] = None
    default_channel: Optional[str] = None
    device_number: Optional[int] = None


class IRPortResponse(BaseModel):
    id: int
    port_number: int
    port_id: Optional[str]
    gpio_pin: Optional[str]
    connected_device_name: Optional[str]
    is_active: bool
    cable_length: Optional[str]
    installation_notes: Optional[str]
    tag_ids: Optional[List[int]]
    default_channel: Optional[str]
    device_number: Optional[int]

    class Config:
        from_attributes = True


class ManagedDeviceRequest(BaseModel):
    device_name: Optional[str] = None
    api_key: Optional[str] = None
    venue_name: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    ir_ports: List[IRPortRequest] = []


class ManagedDeviceResponse(BaseModel):
    id: int
    hostname: str
    mac_address: str
    current_ip_address: str
    device_name: Optional[str]
    api_key: Optional[str]
    venue_name: Optional[str]
    location: Optional[str]
    total_ir_ports: int
    firmware_version: Optional[str]
    device_type: str
    is_online: bool
    last_seen: datetime
    last_ip_address: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    ir_ports: List[IRPortResponse]
    capabilities: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


def _managed_device_to_response(device: ManagedDevice, db: Session) -> ManagedDeviceResponse:
    device_capabilities = None
    base_device = db.query(Device).filter(Device.hostname == device.hostname).first()
    if base_device and base_device.capabilities:
        device_capabilities = base_device.capabilities

    return ManagedDeviceResponse(
        id=device.id,
        hostname=device.hostname,
        mac_address=device.mac_address,
        current_ip_address=device.current_ip_address,
        device_name=device.device_name,
        api_key=device.api_key,
        venue_name=device.venue_name,
        location=device.location,
        total_ir_ports=device.total_ir_ports,
        firmware_version=device.firmware_version,
        device_type=device.device_type,
        is_online=device.is_online,
        last_seen=device.last_seen,
        last_ip_address=device.last_ip_address,
        notes=device.notes,
        created_at=device.created_at,
        updated_at=device.updated_at,
        ir_ports=device.ir_ports,
        capabilities=device_capabilities,
    )


class DiscoveredDeviceResponse(BaseModel):
    id: int
    hostname: str
    mac_address: str
    ip_address: str
    friendly_name: Optional[str]
    device_type: Optional[str]
    firmware_version: Optional[str]
    discovery_properties: Optional[Dict[str, Any]] = None
    is_managed: bool
    first_discovered: datetime
    last_seen: datetime

    class Config:
        from_attributes = True


class ChannelOption(BaseModel):
    id: int
    channel_name: str
    lcn: Optional[str]
    foxtel_number: Optional[str]
    platform: Optional[str]
    broadcaster_network: Optional[str]

    class Config:
        from_attributes = True


# Discovered devices endpoints
@router.get("/discovered", response_model=List[DiscoveredDeviceResponse])
async def get_discovered_devices(db: Session = Depends(get_db)):
    """Get all discovered devices (including unmanaged ones)"""
    return db.query(DeviceDiscovery).filter(DeviceDiscovery.is_managed == False).all()  # noqa: E712


@router.get("/available-channels", response_model=List[ChannelOption])
async def get_available_channels(db: Session = Depends(get_db)):
    """Return the list of visible channels that can be assigned as defaults."""

    channels = (
        db.query(Channel)
        .filter(Channel.disabled == False)  # noqa: E712
        .order_by(Channel.channel_name, Channel.id)
        .all()
    )

    return [ChannelOption.model_validate(channel) for channel in channels]


@router.post("/sync-discovered")
async def sync_discovered_devices(db: Session = Depends(get_db)):
    """Sync current discovery service data with database"""
    discovered_devices = discovery_service.get_discovered_devices()

    for device in discovered_devices:
        # Check if device already exists in discovery table
        existing = db.query(DeviceDiscovery).filter(
            DeviceDiscovery.hostname == device.hostname
        ).first()

        if existing:
            # Update existing entry
            existing.ip_address = device.ip_address
            existing.last_seen = datetime.now()
            existing.firmware_version = device.version
            existing.discovery_properties = device.properties
        else:
            # Create new entry
            discovery_entry = DeviceDiscovery(
                hostname=device.hostname,
                mac_address=device.mac_address,
                ip_address=device.ip_address,
                friendly_name=device.friendly_name,
                device_type=device.device_type,
                firmware_version=device.version,
                discovery_properties=device.properties,
                is_managed=False
            )
            db.add(discovery_entry)

    db.commit()
    return {"message": f"Synced {len(discovered_devices)} discovered devices"}


# Managed devices endpoints
@router.get("/managed", response_model=List[ManagedDeviceResponse])
async def get_managed_devices(db: Session = Depends(get_db)):
    """Get all managed devices"""
    devices = db.query(ManagedDevice).all()
    return [_managed_device_to_response(device, db) for device in devices]


@router.get("/managed/{device_id}", response_model=ManagedDeviceResponse)
async def get_managed_device(device_id: int, db: Session = Depends(get_db)):
    """Get a specific managed device"""
    device = db.query(ManagedDevice).filter(ManagedDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return _managed_device_to_response(device, db)


@router.post("/manage/{hostname}")
async def manage_device(
    hostname: str,
    device_request: ManagedDeviceRequest,
    db: Session = Depends(get_db)
):
    """Convert a discovered device to a managed device"""

    # Check if device exists in discovery
    discovered = db.query(DeviceDiscovery).filter(
        DeviceDiscovery.hostname == hostname
    ).first()

    if not discovered:
        realtime = discovery_service.get_device_by_hostname(hostname)
        if not realtime:
            raise HTTPException(status_code=404, detail="Device not found in discovery")

        discovered = DeviceDiscovery(
            hostname=realtime.hostname,
            mac_address=realtime.mac_address,
            ip_address=realtime.ip_address,
            friendly_name=realtime.friendly_name,
            device_type=realtime.device_type,
            firmware_version=realtime.version,
            discovery_properties=realtime.properties,
            is_managed=False,
        )
        db.add(discovered)
        db.flush()

    # Check if already managed
    existing_managed = db.query(ManagedDevice).filter(
        ManagedDevice.hostname == hostname
    ).first()

    if existing_managed:
        raise HTTPException(status_code=400, detail="Device is already managed")

    capabilities_snapshot: Optional[Dict[str, Any]] = None
    try:
        capabilities_snapshot = await esphome_manager.fetch_capabilities(
            discovered.hostname,
            discovered.ip_address
        )
    except Exception as exc:
        logger.warning(f"Failed to retrieve capabilities from {discovered.hostname}: {exc}")

    if capabilities_snapshot:
        merged_properties = discovered.discovery_properties or {}
        merged_properties["capabilities"] = capabilities_snapshot
        discovered.discovery_properties = merged_properties
        if capabilities_snapshot.get("firmware_version"):
            discovered.firmware_version = capabilities_snapshot["firmware_version"]

    canonical_mac = _normalize_mac(_extract_mac(capabilities_snapshot) or discovered.mac_address)
    if canonical_mac:
        discovered.mac_address = canonical_mac

    # Create managed device
    managed_device = ManagedDevice(
        hostname=discovered.hostname,
        mac_address=canonical_mac or discovered.mac_address,
        current_ip_address=discovered.ip_address,
        device_name=device_request.device_name or discovered.friendly_name,
        api_key=device_request.api_key,
        venue_name=device_request.venue_name,
        location=device_request.location,
        total_ir_ports=5,  # All ESPHome devices have 5 IR ports with new firmware
        firmware_version=discovered.firmware_version,
        device_type=discovered.device_type or "universal",
        is_online=True,
        notes=device_request.notes
    )

    db.add(managed_device)
    db.flush()  # Get the ID and allow port relationship usage

    # Update base device record if already registered
    device_record = db.query(Device).filter(Device.hostname == discovered.hostname).first()
    if device_record:
        device_record.mac_address = canonical_mac or device_record.mac_address
        device_record.ip_address = discovered.ip_address
        device_record.is_online = True
        device_record.last_seen = datetime.now()
        device_record.firmware_version = discovered.firmware_version
        device_record.friendly_name = discovered.friendly_name or device_record.friendly_name
        if capabilities_snapshot:
            device_record.capabilities = capabilities_snapshot
    else:
        device_record = Device(
            hostname=discovered.hostname,
            mac_address=canonical_mac or discovered.mac_address,
            ip_address=discovered.ip_address,
            friendly_name=discovered.friendly_name,
            device_type=discovered.device_type or "universal",
            firmware_version=discovered.firmware_version,
            venue_name=device_request.venue_name,
            location=device_request.location,
            is_online=True,
            capabilities=capabilities_snapshot or {"outputs": managed_device.total_ir_ports},
        )
        db.add(device_record)

    # Create IR ports
    port_prefix = (managed_device.mac_address or managed_device.hostname or "").replace(":", "").lower() or managed_device.hostname

    if device_request.ir_ports:
        for port_req in device_request.ir_ports:
            # Map port numbers to GPIO pins (1-based, matching template system)
            gpio_map = {
                1: "GPIO13",  # D7
                2: "GPIO15",  # D8
                3: "GPIO12",  # D6
                4: "GPIO16",  # D0
                5: "GPIO5"    # D1
            }

            ir_port = IRPort(
                device_id=managed_device.id,
                port_number=port_req.port_number,
                port_id=f"{port_prefix}-{port_req.port_number}",
                gpio_pin=gpio_map.get(port_req.port_number),
                connected_device_name=port_req.connected_device_name,
                is_active=port_req.is_active,
                cable_length=port_req.cable_length,
                installation_notes=port_req.installation_notes,
                tag_ids=_normalize_tag_ids(port_req.tag_ids),
                default_channel=_normalize_default_channel(port_req.default_channel),
                device_number=port_req.device_number
            )
            db.add(ir_port)
        db.flush()
    else:
        # Create default IR ports
        gpio_map = {
            1: "GPIO13",  # D7
            2: "GPIO15",  # D8
            3: "GPIO12",  # D6
            4: "GPIO16",  # D0
            5: "GPIO5"    # D1
        }

        port_count = managed_device.total_ir_ports
        for i in range(port_count):
            port_number = i + 1  # Port numbers are 1-based
            ir_port = IRPort(
                device_id=managed_device.id,
                port_number=port_number,
                port_id=f"{port_prefix}-{port_number}",
                gpio_pin=gpio_map.get(port_number),
                is_active=True,
                device_number=i
            )
            db.add(ir_port)
        db.flush()

    db.refresh(managed_device)
    _sync_ports_from_capabilities(managed_device, capabilities_snapshot)

    _refresh_tag_usage_counts(db)

    # Mark as managed in discovery
    discovered.is_managed = True

    db.commit()
    db.refresh(managed_device)

    db.refresh(managed_device)
    return _managed_device_to_response(managed_device, db)


@router.put("/managed/{device_id}", response_model=ManagedDeviceResponse)
async def update_managed_device(
    device_id: int,
    device_request: ManagedDeviceRequest,
    db: Session = Depends(get_db)
):
    """Update a managed device"""
    device = db.query(ManagedDevice).filter(ManagedDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Update device fields
    if device_request.device_name is not None:
        device.device_name = device_request.device_name
    if device_request.api_key is not None:
        device.api_key = device_request.api_key
    if device_request.venue_name is not None:
        device.venue_name = device_request.venue_name
    if device_request.location is not None:
        device.location = device_request.location
    if device_request.notes is not None:
        device.notes = device_request.notes

    # Update IR ports if provided
    if device_request.ir_ports:
        # Delete existing ports
        db.query(IRPort).filter(IRPort.device_id == device_id).delete()

        # Create new ports
        gpio_map = {
            1: "GPIO13",  # D7
            2: "GPIO15",  # D8
            3: "GPIO12",  # D6
            4: "GPIO16",  # D0
            5: "GPIO5",   # D1
        }

        for port_req in device_request.ir_ports:
            ir_port = IRPort(
                device_id=device_id,
                port_number=port_req.port_number,
                port_id=f"{device.mac_address}-{port_req.port_number}",
                gpio_pin=gpio_map.get(port_req.port_number),
                connected_device_name=port_req.connected_device_name,
                is_active=port_req.is_active,
                cable_length=port_req.cable_length,
                installation_notes=port_req.installation_notes,
                tag_ids=_normalize_tag_ids(port_req.tag_ids),
                default_channel=_normalize_default_channel(port_req.default_channel),
                device_number=port_req.device_number
            )
            db.add(ir_port)

    _refresh_tag_usage_counts(db)

    db.commit()
    db.refresh(device)
    return _managed_device_to_response(device, db)


@router.delete("/managed/{device_id}")
async def unmanage_device(device_id: int, db: Session = Depends(get_db)):
    """Remove a device from management (but keep in discovery)"""
    device = db.query(ManagedDevice).filter(ManagedDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    hostname = device.hostname

    # Delete the managed device (will cascade delete IR ports)
    db.delete(device)

    # Remove cached device info
    device_record = db.query(Device).filter(Device.hostname == hostname).first()
    if device_record:
        db.delete(device_record)

    # Remove discovery entry so it will be rediscovered fresh
    discovered = db.query(DeviceDiscovery).filter(DeviceDiscovery.hostname == hostname).first()
    if discovered:
        db.delete(discovered)

    _refresh_tag_usage_counts(db)

    db.commit()
    return {"message": f"Device {hostname} removed from management"}


@router.post("/managed/{device_id}/health-check")
async def check_device_health(device_id: int, db: Session = Depends(get_db)):
    """Perform comprehensive health check on a specific device"""
    try:
        result = await health_checker.check_single_device(device_id, db)

        if not result:
            raise HTTPException(status_code=404, detail="Device not found")

        # Update last_seen to now for clarity
        device = db.query(ManagedDevice).filter(ManagedDevice.id == device_id).first()
        if device:
            device.last_seen = datetime.now()
            device.is_online = result.is_online
            db.commit()

        return {
            "hostname": result.hostname,
            "is_online": result.is_online,
            "current_ip": result.ip_address,
            "mac_address": result.mac_address,
            "api_reachable": result.api_reachable,
            "response_time_ms": result.response_time_ms,
            "error_message": result.error_message,
            "check_timestamp": result.check_timestamp.isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed for device {device_id}: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@router.post("/managed/health-check-all")
async def check_all_devices_health(db: Session = Depends(get_db)):
    """Perform health check on all managed devices"""
    try:
        results = await health_checker.check_all_devices(db)

        return {
            "total_devices": len(results),
            "online_devices": sum(1 for r in results.values() if r.is_online),
            "offline_devices": sum(1 for r in results.values() if not r.is_online),
            "check_timestamp": datetime.now().isoformat(),
            "devices": [
                {
                    "hostname": result.hostname,
                    "is_online": result.is_online,
                    "current_ip": result.ip_address,
                    "mac_address": result.mac_address,
                    "api_reachable": result.api_reachable,
                    "response_time_ms": result.response_time_ms,
                    "error_message": result.error_message
                }
                for result in results.values()
            ]
        }
    except Exception as e:
        logger.error(f"Bulk health check failed: {e}")
        raise HTTPException(status_code=500, detail="Bulk health check failed")


@router.get("/health-status")
async def get_health_status():
    """Get health monitoring service status"""
    return {
        "service_running": health_checker.running,
        "check_interval_seconds": health_checker.check_interval,
        "last_full_check": health_checker.last_full_check.isoformat() if health_checker.last_full_check else None,
        "max_concurrent_checks": health_checker.max_concurrent_checks
    }


@router.delete("/discovered/{hostname}")
async def forget_discovered_device(hostname: str, db: Session = Depends(get_db)):
    """Remove a device from the discovered devices database"""
    # Check if device exists in discovery
    discovered = db.query(DeviceDiscovery).filter(
        DeviceDiscovery.hostname == hostname
    ).first()

    if not discovered:
        raise HTTPException(status_code=404, detail="Device not found in discovery")

    # Check if device is currently managed
    if discovered.is_managed:
        raise HTTPException(
            status_code=400,
            detail="Cannot forget a managed device. Unmanage it first."
        )

    # Delete the discovered device
    db.delete(discovered)
    db.commit()

    return {"message": f"Device {hostname} removed from discovery"}


@router.delete("/ir-port/{port_id}")
async def delete_ir_port(port_id: int, db: Session = Depends(get_db)):
    """Delete an IR port if it's inactive and unconfigured"""
    port = db.query(IRPort).filter(IRPort.id == port_id).first()
    if not port:
        raise HTTPException(status_code=404, detail="Port not found")

    # Only allow deletion if port is inactive and has no connected device
    if port.is_active or port.connected_device_name:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete active port or port with connected device"
        )

    db.delete(port)
    db.commit()
    return {"message": f"Port {port.port_id} deleted successfully"}
