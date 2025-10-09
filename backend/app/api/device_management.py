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


class AllDevicesResponse(BaseModel):
    """Combined response for both ESPHome and network-scanned devices"""
    source: str  # "esphome" or "network_scan"
    id: int
    hostname: Optional[str]
    mac_address: str
    ip_address: str
    friendly_name: Optional[str]
    device_type: Optional[str]
    vendor: Optional[str] = None
    is_online: bool = True
    is_managed: bool = False
    firmware_version: Optional[str] = None
    response_time_ms: Optional[float] = None
    last_seen: datetime

    class Config:
        from_attributes = True


@router.get("/all-devices")
async def get_all_devices(
    show_esphome: bool = True,
    show_network: bool = False,
    show_managed: bool = False,
    db: Session = Depends(get_db)
) -> List[AllDevicesResponse]:
    """
    Get all devices from both ESPHome discovery and network scan

    Args:
        show_esphome: Include ESPHome discovered devices (default: True)
        show_network: Include network scanned devices (default: False)
        show_managed: Include managed devices in results (default: False)
    """
    from ..models.network_discovery import NetworkScanCache

    all_devices = []

    # Get ESPHome devices
    if show_esphome:
        esphome_filter = DeviceDiscovery.is_managed == False if not show_managed else True  # noqa: E712
        esphome_devices = db.query(DeviceDiscovery).filter(esphome_filter).all()

        for device in esphome_devices:
            all_devices.append(AllDevicesResponse(
                source="esphome",
                id=device.id,
                hostname=device.hostname,
                mac_address=device.mac_address,
                ip_address=device.ip_address,
                friendly_name=device.friendly_name,
                device_type=device.device_type,
                vendor=None,
                is_online=True,
                is_managed=device.is_managed,
                firmware_version=device.firmware_version,
                last_seen=device.last_seen
            ))

    # Get network scanned devices
    if show_network:
        network_devices = db.query(NetworkScanCache).filter(NetworkScanCache.is_online == True).all()  # noqa: E712

        # Get managed device MAC addresses to filter if needed
        managed_macs = set()
        if not show_managed:
            managed_devices = db.query(ManagedDevice.mac_address).all()
            managed_macs = {mac for (mac,) in managed_devices if mac}

            # Also get virtual device MACs
            from ..models.virtual_controller import VirtualDevice
            virtual_macs = db.query(VirtualDevice.mac_address).all()
            managed_macs.update({mac for (mac,) in virtual_macs if mac})

        for device in network_devices:
            # Skip if managed and we're not showing managed
            if not show_managed and device.mac_address in managed_macs:
                continue

            all_devices.append(AllDevicesResponse(
                source="network_scan",
                id=device.id,
                hostname=device.hostname,
                mac_address=device.mac_address,
                ip_address=device.ip_address,
                friendly_name=device.hostname,  # Use hostname as friendly name
                device_type=device.device_type_guess,
                vendor=device.vendor,
                is_online=device.is_online,
                is_managed=False,  # Network scan doesn't track managed status
                firmware_version=None,
                response_time_ms=device.response_time_ms,
                last_seen=device.last_seen
            ))

    return all_devices


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
def _virtual_controller_to_managed_response(vc, db: Session) -> ManagedDeviceResponse:
    """Transform a Virtual Controller into ManagedDeviceResponse format"""
    from ..models.virtual_controller import VirtualController, VirtualDevice

    # Get virtual devices for this controller
    virtual_devices = db.query(VirtualDevice).filter_by(controller_id=vc.id).all()

    # Transform virtual_devices into IRPortResponse format
    # Virtual Controllers only have the ports defined in their capabilities
    ir_ports_data = []
    for vd in virtual_devices:
        ir_port = IRPortResponse(
            id=vd.id,
            port_number=vd.port_number,
            port_id=vd.port_id,
            gpio_pin=None,  # Network TVs don't have GPIO
            connected_device_name=vd.device_name,
            is_active=vd.is_active,
            cable_length=None,
            installation_notes=vd.installation_notes,
            tag_ids=vd.tag_ids if vd.tag_ids else None,
            default_channel=vd.default_channel,
            device_number=vd.port_number - 1,  # 0-indexed
            created_at=vd.created_at,
            updated_at=vd.updated_at
        )
        ir_ports_data.append(ir_port)

    # For Virtual Controllers, only fill ports that are in capabilities.ports
    # (typically just port 1 for the TV itself)
    ports_in_capabilities = set()
    if isinstance(vc.capabilities, dict) and "ports" in vc.capabilities:
        for port_def in vc.capabilities["ports"]:
            if isinstance(port_def, dict) and "port" in port_def:
                ports_in_capabilities.add(port_def["port"])

    # Fill only the ports defined in capabilities
    for port_num in ports_in_capabilities:
        if not any(p.port_number == port_num for p in ir_ports_data):
            ir_ports_data.append(IRPortResponse(
                id=-(vc.id * 100 + port_num),  # Negative ID to avoid conflicts
                port_number=port_num,
                port_id=f"{vc.controller_id}-{port_num}",
                gpio_pin=None,
                connected_device_name=None,
                is_active=False,
                cable_length=None,
                installation_notes=None,
                tag_ids=None,
                default_channel=None,
                device_number=port_num - 1,
                created_at=vc.created_at,
                updated_at=vc.updated_at
            ))

    # Sort by port number
    ir_ports_data.sort(key=lambda x: x.port_number)

    # Get first device's MAC or use controller ID
    mac_address = virtual_devices[0].mac_address if virtual_devices else vc.controller_id

    # Use capabilities from Virtual Controller (already has ports array with brand info)
    capabilities = vc.capabilities.copy() if isinstance(vc.capabilities, dict) else {}

    # Ensure ports array exists (for older VCs that don't have it)
    if "ports" not in capabilities:
        capabilities["ports"] = [{"port": i} for i in range(1, vc.total_ports + 1)]

    return ManagedDeviceResponse(
        id=-(vc.id + 10000),  # Negative ID to differentiate from IR controllers
        hostname=vc.controller_id,  # Use controller_id as hostname
        mac_address=mac_address,
        current_ip_address=virtual_devices[0].ip_address if virtual_devices else "0.0.0.0",
        device_name=vc.controller_name,
        api_key=None,
        venue_name=vc.venue_name,
        location=vc.location,
        total_ir_ports=vc.total_ports,
        firmware_version=vc.protocol,  # Use protocol as firmware version
        device_type="network_tv",
        is_online=vc.is_online,
        last_seen=vc.last_seen or vc.updated_at,
        last_ip_address=virtual_devices[0].ip_address if virtual_devices else None,
        notes=vc.notes,
        created_at=vc.created_at,
        updated_at=vc.updated_at,
        ir_ports=ir_ports_data,
        capabilities=capabilities
    )


@router.get("/managed", response_model=List[ManagedDeviceResponse])
async def get_managed_devices(db: Session = Depends(get_db)):
    """Get all managed devices (IR controllers + Virtual Controllers)"""
    from ..models.virtual_controller import VirtualController

    # Get IR controllers
    ir_devices = db.query(ManagedDevice).all()
    ir_responses = [_managed_device_to_response(device, db) for device in ir_devices]

    # Get Virtual Controllers
    virtual_controllers = db.query(VirtualController).all()
    vc_responses = [_virtual_controller_to_managed_response(vc, db) for vc in virtual_controllers]

    # Combine and return
    return ir_responses + vc_responses


@router.get("/managed/{device_id}")
async def get_managed_device(device_id: int, db: Session = Depends(get_db)):
    """Get a specific managed device (IR device or Virtual Controller)"""

    # Check if it's a Virtual Controller (negative ID)
    if device_id < 0:
        from ..models.virtual_controller import VirtualController

        # Extract real Virtual Controller ID
        vc_id = abs(device_id) - 10000
        controller = db.query(VirtualController).filter(VirtualController.id == vc_id).first()
        if not controller:
            raise HTTPException(status_code=404, detail="Virtual Controller not found")

        # Return Virtual Controller details in a format compatible with frontend
        return {
            "id": controller.id,
            "hostname": controller.controller_name,
            "friendly_name": controller.controller_name,
            "device_type": "network_tv",
            "protocol": controller.protocol,
            "is_online": True,  # Virtual controllers are always "available"
            "controller_id": controller.controller_id,
            "device_count": len(controller.virtual_devices),
            "virtual_devices": [
                {
                    "id": vd.id,
                    "ip_address": vd.ip_address,
                    "mac_address": vd.mac_address,
                    "model": vd.model,
                    "manufacturer": vd.manufacturer
                } for vd in controller.virtual_devices
            ]
        }

    # Otherwise it's an IR ManagedDevice (positive ID)
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
    """Update a managed device (IR Controller or Virtual Controller)"""
    from ..models.virtual_controller import VirtualController, VirtualDevice

    # Check if this is a Virtual Controller (negative ID)
    if device_id < 0:
        # Extract real Virtual Controller ID
        vc_id = abs(device_id) - 10000
        vc = db.query(VirtualController).filter(VirtualController.id == vc_id).first()
        if not vc:
            raise HTTPException(status_code=404, detail="Virtual Controller not found")

        # Update Virtual Controller fields
        if device_request.device_name is not None:
            vc.controller_name = device_request.device_name
        if device_request.venue_name is not None:
            vc.venue_name = device_request.venue_name
        if device_request.location is not None:
            vc.location = device_request.location
        if device_request.notes is not None:
            vc.notes = device_request.notes

        # Update Virtual Devices (ports) if provided
        if device_request.ir_ports:
            for port_req in device_request.ir_ports:
                # Find or create virtual device for this port
                vd = db.query(VirtualDevice).filter(
                    VirtualDevice.controller_id == vc.id,
                    VirtualDevice.port_number == port_req.port_number
                ).first()

                if vd:
                    # Update existing virtual device
                    if port_req.connected_device_name:
                        vd.device_name = port_req.connected_device_name
                    vd.is_active = port_req.is_active
                    vd.installation_notes = port_req.installation_notes
                    vd.tag_ids = _normalize_tag_ids(port_req.tag_ids)
                    vd.default_channel = _normalize_default_channel(port_req.default_channel)
                elif port_req.connected_device_name and port_req.is_active:
                    # Only create new virtual device if it has a name and is active
                    # Get first virtual device to copy network details
                    first_vd = db.query(VirtualDevice).filter(VirtualDevice.controller_id == vc.id).first()
                    if first_vd:
                        new_vd = VirtualDevice(
                            controller_id=vc.id,
                            port_number=port_req.port_number,
                            port_id=f"{vc.controller_id}-{port_req.port_number}",
                            device_name=port_req.connected_device_name,
                            ip_address=first_vd.ip_address,
                            mac_address=first_vd.mac_address,
                            is_active=port_req.is_active,
                            installation_notes=port_req.installation_notes,
                            tag_ids=_normalize_tag_ids(port_req.tag_ids),
                            default_channel=_normalize_default_channel(port_req.default_channel)
                        )
                        db.add(new_vd)

        _refresh_tag_usage_counts(db)
        db.commit()
        db.refresh(vc)
        return _virtual_controller_to_managed_response(vc, db)

    # Handle IR Controllers (positive ID)
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
    """Remove a device from management (IR device or Virtual Controller)"""

    # Check if it's a Virtual Controller (negative ID)
    if device_id < 0:
        from ..models.virtual_controller import VirtualController
        from ..models.network_discovery import NetworkScanCache

        # Extract real Virtual Controller ID
        vc_id = abs(device_id) - 10000
        controller = db.query(VirtualController).filter(VirtualController.id == vc_id).first()

        if not controller:
            raise HTTPException(status_code=404, detail="Virtual Controller not found")

        controller_id = controller.controller_id
        controller_name = controller.controller_name

        # Get device count and MAC addresses before deletion
        device_count = len(controller.virtual_devices)
        mac_addresses = [vd.mac_address for vd in controller.virtual_devices if vd.mac_address]

        # Reset is_adopted flag for all devices associated with this controller
        if mac_addresses:
            db.query(NetworkScanCache).filter(
                NetworkScanCache.mac_address.in_(mac_addresses)
            ).update({
                'is_adopted': False,
                'adopted_hostname': None
            }, synchronize_session=False)

        # Delete the controller (cascade deletes virtual devices)
        db.delete(controller)
        db.commit()

        return {
            "message": f"Virtual Controller {controller_name} removed. {device_count} device(s) returned to discovery pool.",
            "controller_id": controller_id
        }

    # Otherwise it's an IR ManagedDevice (positive ID)
    device = db.query(ManagedDevice).filter(ManagedDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    hostname = device.hostname

    # Delete the managed device (will cascade delete IR ports)
    db.delete(device)

    # Keep cached device info but mark as offline
    # For IR controllers, clear capabilities to force fresh scan on next adoption
    # Skip clearing for network devices (they don't have ESPHome capabilities)
    device_record = db.query(Device).filter(Device.hostname == hostname).first()
    if device_record:
        device_record.is_adopted = False
        if hostname.startswith("ir-"):
            device_record.capabilities = None  # Clear stale capabilities for IR controllers

    # Mark discovery entry as not managed so it reappears in discovery list
    discovered = db.query(DeviceDiscovery).filter(DeviceDiscovery.hostname == hostname).first()
    if discovered:
        discovered.is_managed = False

    _refresh_tag_usage_counts(db)

    db.commit()

    # Mark device as not adopted in discovery service's in-memory cache
    from ..services.discovery import discovery_service
    discovery_service.mark_device_unadopted(hostname)

    return {"message": f"Device {hostname} removed from management and returned to discovery pool"}


@router.post("/managed/{device_id}/health-check")
async def check_device_health(device_id: int, db: Session = Depends(get_db)):
    """Perform comprehensive health check on a specific device (IR device or Virtual Controller)"""
    try:
        # Check if it's a Virtual Controller (negative ID)
        if device_id < 0:
            from ..models.virtual_controller import VirtualController
            from ..services.device_status_checker import status_checker

            # Extract real Virtual Controller ID
            vc_id = abs(device_id) - 10000
            controller = db.query(VirtualController).filter(VirtualController.id == vc_id).first()
            if not controller:
                raise HTTPException(status_code=404, detail="Virtual Controller not found")

            # Use device status checker for Virtual Controllers
            status = await status_checker.check_device_now(controller.controller_id)

            if not status:
                raise HTTPException(status_code=404, detail="Status check failed")

            return {
                "hostname": controller.controller_name,
                "is_online": status.is_online,
                "current_ip": controller.virtual_devices[0].ip_address if controller.virtual_devices else None,
                "mac_address": controller.virtual_devices[0].mac_address if controller.virtual_devices else None,
                "api_reachable": status.is_online,
                "power_state": status.power_state,
                "check_method": status.check_method,
                "current_channel": status.current_channel,
                "response_time_ms": None,
                "error_message": None if status.is_online else "Device offline",
                "check_timestamp": status.last_checked_at.isoformat()
            }

        # Otherwise it's an IR ManagedDevice (positive ID)
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
