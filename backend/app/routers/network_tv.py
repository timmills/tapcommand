"""
Network TV control endpoints
Supports Samsung legacy (port 55000) and modern (WebSocket) TVs
Now reads from network scan cache database
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
import samsungctl

from ..db.database import get_db
from ..models.network_discovery import NetworkScanCache
from ..services.device_scanner_config import get_ports_for_device_type
from ..services.tv_confidence_scorer import tv_confidence_scorer

router = APIRouter(prefix="/api/network-tv", tags=["network-tv"])


class TVInfo(BaseModel):
    ip: str
    name: str
    model: str
    mac: str
    protocol: str
    status: str
    device_type: Optional[str] = None
    vendor: Optional[str] = None
    ports: List[int] = []
    confidence_score: Optional[int] = None
    confidence_reason: Optional[str] = None
    adoptable: Optional[str] = None  # "ready", "needs_config", "unlikely"


class TVCommand(BaseModel):
    ip: str
    command: str


def get_tv_from_scan_cache(ip: str, db: Session):
    """Get TV info from scan cache"""
    device = db.query(NetworkScanCache).filter_by(ip_address=ip).first()
    if not device:
        return None

    # Determine protocol and port from device type
    protocol = "unknown"
    port = None

    if device.device_type_guess == "samsung_tv_legacy":
        protocol = "samsung_legacy"
        port = 55000
    elif device.device_type_guess == "samsung_tv_tizen":
        protocol = "samsung_websocket"
        port = 8001
    elif device.device_type_guess == "lg_webos":
        protocol = "lg_webos"
        port = 3000
    elif device.device_type_guess == "sony_bravia":
        protocol = "sony_bravia"
        port = 80
    elif device.device_type_guess == "hisense_vidaa":
        protocol = "hisense_vidaa"
        port = 36669
    elif device.device_type_guess == "philips_android":
        protocol = "philips_jointspace"
        port = 1925
    elif device.device_type_guess in ["tcl_roku", "roku"]:
        protocol = "roku_ecp"
        port = 8060
    elif device.device_type_guess == "vizio_smartcast":
        protocol = "vizio_smartcast"
        port = 7345
    elif device.device_type_guess == "apple_tv":
        protocol = "apple_airplay"
        port = 3689
    elif device.device_type_guess == "chromecast":
        protocol = "chromecast"
        port = 8008

    # Generate better display name
    display_name = device.hostname

    # If hostname is generic/unhelpful, create a better name
    if display_name:
        hostname_lower = display_name.lower()
        # Check if hostname is generic (laptop, desktop, etc.)
        generic_patterns = ['laptop', 'desktop', 'pc', 'computer', 'workstation']
        if any(pattern in hostname_lower for pattern in generic_patterns):
            # Use device type + IP instead
            if device.device_type_guess:
                type_name = device.device_type_guess.replace('_', ' ').title()
                display_name = f"{type_name} ({device.ip_address.split('.')[-1]})"
            else:
                display_name = f"{device.vendor or 'TV'} ({device.ip_address.split('.')[-1]})"
    else:
        # No hostname, use device type or vendor
        if device.device_type_guess:
            type_name = device.device_type_guess.replace('_', ' ').title()
            display_name = f"{type_name} ({device.ip_address.split('.')[-1]})"
        else:
            display_name = f"TV {device.ip_address.split('.')[-1]}"

    return {
        "ip": device.ip_address,
        "name": display_name,
        "model": "Unknown",  # Could be detected via protocol later
        "mac": device.mac_address,
        "protocol": protocol,
        "port": port,
        "device_type": device.device_type_guess,
        "vendor": device.vendor,
    }


@router.get("/discover", response_model=List[TVInfo])
async def discover_tvs(db: Session = Depends(get_db)):
    """
    Discover TVs from network scan cache
    Shows ALL TV vendor devices with adoptability status:
    - "ready": Has control ports open, ready to adopt
    - "needs_config": TV vendor but no control ports (needs remote control enabled)
    - "unlikely": Probably not a TV (tablet/phone)

    Excludes: PCs, ESPs, already adopted devices
    """
    import asyncio
    import socket

    # TV vendor patterns to look for
    tv_vendor_patterns = [
        'samsung', 'lg', 'sony', 'hisense', 'philips',
        'vizio', 'tcl', 'roku', 'apple', 'google'
    ]

    # Exclude types we don't want to show (PCs, ESPs, etc.)
    excluded_types = ['esphome_ir_controller', 'pc_workstation']

    # Get ALL non-adopted, non-hidden devices from TV vendors
    query = db.query(NetworkScanCache).filter(
        NetworkScanCache.is_adopted == False,
        NetworkScanCache.is_hidden == False
    )

    # Exclude unwanted device types
    if excluded_types:
        query = query.filter(
            (NetworkScanCache.device_type_guess == None) |
            (~NetworkScanCache.device_type_guess.in_(excluded_types))
        )

    all_devices = query.all()

    # Filter to TV vendor devices only
    tv_devices = []
    for device in all_devices:
        if device.vendor:
            vendor_lower = device.vendor.lower()
            if any(tv_vendor in vendor_lower for tv_vendor in tv_vendor_patterns):
                tv_devices.append(device)

    async def check_tv_status(device):
        """Check if TV is reachable with async timeout"""
        tv_info = get_tv_from_scan_cache(device.ip_address, db)
        if not tv_info or not tv_info.get('port'):
            return TVInfo(
                ip=device.ip_address,
                name=device.hostname or f"TV {device.ip_address.split('.')[-1]}",
                model="Unknown",
                mac=device.mac_address,
                protocol="unknown",
                status="unknown",
                device_type=device.device_type_guess,
                vendor=device.vendor,
                ports=[]
            )

        status = "offline"
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setblocking(False)
            try:
                await asyncio.wait_for(
                    asyncio.get_event_loop().sock_connect(sock, (tv_info["ip"], tv_info["port"])),
                    timeout=0.5
                )
                status = "online"
            except asyncio.TimeoutError:
                status = "offline"
            finally:
                sock.close()
        except:
            status = "offline"

        return TVInfo(
            ip=tv_info["ip"],
            name=tv_info["name"],
            model=tv_info["model"],
            mac=tv_info["mac"],
            protocol=tv_info["protocol"],
            status=status,
            device_type=tv_info["device_type"],
            vendor=tv_info["vendor"],
            ports=[tv_info["port"]] if tv_info["port"] else []
        )

    # Check all TVs in parallel and apply confidence scoring
    if tv_devices:
        results = await asyncio.gather(*[check_tv_status(device) for device in tv_devices])

        # Apply confidence scoring and adoptability status
        final_results = []
        for tv in results:
            # Get open ports for scoring
            open_ports = tv.ports if tv.ports else []

            # Score the device
            confidence = tv_confidence_scorer.score_device(
                vendor=tv.vendor,
                hostname=tv.name,
                open_ports=open_ports,
                device_type_guess=tv.device_type
            )

            # Add confidence info to response
            tv.confidence_score = confidence['confidence_score']
            tv.confidence_reason = confidence['reason']

            # Determine adoptability status
            if confidence['confidence_score'] < 40:
                # Very unlikely to be a TV (tablet, phone, etc.)
                tv.adoptable = "unlikely"
            elif len(open_ports) > 0 and tv.protocol != "unknown":
                # Has control ports open and protocol identified
                tv.adoptable = "ready"
            elif confidence['confidence_score'] >= 60:
                # Likely a TV but no control ports yet (needs remote access enabled)
                tv.adoptable = "needs_config"
            else:
                # Unsure
                tv.adoptable = "unlikely"

            # Include all devices (let frontend decide how to display based on adoptable status)
            final_results.append(tv)

        # Sort: ready first, then needs_config, then unlikely
        adoptable_priority = {"ready": 0, "needs_config": 1, "unlikely": 2}
        final_results.sort(key=lambda x: (adoptable_priority.get(x.adoptable, 3), -x.confidence_score))

        return final_results

    return []


@router.post("/command")
async def send_tv_command(command: TVCommand, db: Session = Depends(get_db)):
    """
    Send command to a Samsung TV
    Supports legacy and modern protocols
    """
    # Find TV in scan cache
    tv = get_tv_from_scan_cache(command.ip, db)
    if not tv:
        raise HTTPException(status_code=404, detail="TV not found in network scan cache. Run a network scan first.")

    # Legacy Samsung protocol (D/E/F series)
    if tv["protocol"] == "samsung_legacy":
        try:
            config = {
                "name": "SmartVenue",
                "description": "SmartVenue Control System",
                "id": "smartvenue",
                "host": tv["ip"],
                "port": tv["port"],
                "method": "legacy",
                "timeout": 3,
            }

            # Map common commands to KEY codes
            key_map = {
                "power": "KEY_POWER",
                "volume_up": "KEY_VOLUP",
                "volume_down": "KEY_VOLDOWN",
                "mute": "KEY_MUTE",
                "hdmi": "KEY_HDMI",
                "source": "KEY_SOURCE",
            }

            key = key_map.get(command.command.lower(), f"KEY_{command.command.upper()}")

            with samsungctl.Remote(config) as remote:
                remote.control(key)

            return {"success": True, "message": f"Command {command.command} sent to {tv['name']}"}

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to send command: {str(e)}")

    # Modern Samsung protocol (Tizen 2016+)
    elif tv["protocol"] == "samsung_websocket":
        raise HTTPException(
            status_code=501,
            detail="Modern Samsung WebSocket protocol not yet implemented. TV needs pairing first.",
        )

    else:
        raise HTTPException(status_code=400, detail=f"Unknown protocol: {tv['protocol']}")


@router.get("/test/{ip}")
async def test_tv(ip: str, db: Session = Depends(get_db)):
    """Test connection to a TV"""
    tv = get_tv_from_scan_cache(ip, db)
    if not tv:
        raise HTTPException(status_code=404, detail="TV not found in network scan cache. Run a network scan first.")

    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((tv["ip"], tv["port"]))
        sock.close()

        if result == 0:
            return {"reachable": True, "message": f"TV at {ip} is online"}
        else:
            return {"reachable": False, "message": f"TV at {ip} is offline or port {tv['port']} is closed"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/adopt/{ip}")
async def adopt_device(ip: str, db: Session = Depends(get_db)):
    """
    Adopt a device from the network scan cache

    This endpoint:
    1. Creates a Virtual Controller for the TV
    2. Maps the TV to port 1 of that Virtual Controller
    3. Marks the device as adopted in the scan cache

    Returns the created Virtual Controller and device mapping details
    """
    from ..models.virtual_controller import VirtualController, VirtualDevice
    import re

    try:
        # Get device from scan cache
        device = db.query(NetworkScanCache).filter_by(ip_address=ip).first()

        if not device:
            raise HTTPException(status_code=404, detail=f"Device {ip} not found in scan cache")

        if device.is_adopted:
            raise HTTPException(status_code=400, detail=f"Device {ip} is already adopted")

        # Get TV info (protocol, port, etc.)
        tv_info = get_tv_from_scan_cache(ip, db)
        if not tv_info:
            raise HTTPException(status_code=400, detail=f"Could not determine device protocol for {ip}")

        # Generate controller ID from MAC address (nw-{last_6_chars_of_mac})
        # Format: nw-b85a97 (from E4:E0:C5:B8:5A:97)
        mac_suffix = device.mac_address.replace(':', '').lower()[-6:] if device.mac_address else ip.split('.')[-1]
        controller_id = f"nw-{mac_suffix}"

        # Make sure controller_id is unique
        existing = db.query(VirtualController).filter_by(controller_id=controller_id).first()
        counter = 1
        base_controller_id = controller_id
        while existing:
            controller_id = f"{base_controller_id}-{counter}"
            existing = db.query(VirtualController).filter_by(controller_id=controller_id).first()
            counter += 1

        # Create controller name
        controller_name = f"{tv_info['name']} Controller"

        # Determine controller type
        controller_type = "network_tv"
        if device.device_type_guess in ["roku", "apple_tv", "chromecast", "fire_tv"]:
            controller_type = "streaming_device"

        # Determine brand from vendor for IR-like capabilities
        brand = "Unknown"
        if device.vendor:
            vendor_lower = device.vendor.lower()
            if "samsung" in vendor_lower:
                brand = "Samsung"
            elif "lg" in vendor_lower:
                brand = "LG"
            elif "sony" in vendor_lower:
                brand = "Sony"
            elif "panasonic" in vendor_lower:
                brand = "Panasonic"
            elif "philips" in vendor_lower:
                brand = "Philips"
            elif "toshiba" in vendor_lower:
                brand = "Toshiba"
            elif "vizio" in vendor_lower:
                brand = "Vizio"
            elif "tcl" in vendor_lower:
                brand = "TCL"
            elif "hisense" in vendor_lower:
                brand = "Hisense"

        # Create Virtual Controller with IR-like capabilities
        virtual_controller = VirtualController(
            controller_name=controller_name,
            controller_id=controller_id,
            controller_type=controller_type,
            protocol=tv_info['protocol'],
            total_ports=1,  # Virtual controllers have 1 port (the TV itself)
            is_active=True,
            is_online=(tv_info.get('port') is not None),
            capabilities={
                "power": True,
                "volume": tv_info['protocol'] != "unknown",
                "channels": tv_info['protocol'] != "unknown",
                "source_select": tv_info['protocol'] != "unknown",
                "ports": [{
                    "port": 1,
                    "brand": brand,
                    "description": f"{brand} Network TV"
                }]
            }
        )
        db.add(virtual_controller)
        db.flush()  # Get the controller ID

        # Create Virtual Device on port 1
        port_id = f"{controller_id}-1"

        virtual_device = VirtualDevice(
            controller_id=virtual_controller.id,
            port_number=1,
            port_id=port_id,
            device_name=tv_info['name'],
            device_type=tv_info['device_type'],
            ip_address=ip,
            mac_address=device.mac_address,
            port=tv_info.get('port'),
            protocol=tv_info['protocol'],
            connection_config={
                "ip": ip,
                "port": tv_info.get('port'),
                "protocol": tv_info['protocol'],
                "vendor": device.vendor,
                "model": tv_info.get('model', 'Unknown')
            },
            is_active=True,
            is_online=(tv_info.get('port') is not None),
            capabilities={
                "power": True,
                "volume": True,
                "channels": True,
                "source_select": True
            }
        )
        db.add(virtual_device)

        # Mark device as adopted in scan cache
        device.is_adopted = True

        db.commit()

        return {
            "success": True,
            "message": f"Device {ip} ({device.vendor or 'Unknown'}) has been adopted and mapped to Virtual Controller",
            "virtual_controller": {
                "id": virtual_controller.id,
                "controller_id": controller_id,
                "controller_name": controller_name,
                "controller_type": controller_type,
                "protocol": tv_info['protocol'],
                "total_ports": 5,
                "is_online": virtual_controller.is_online
            },
            "virtual_device": {
                "id": virtual_device.id,
                "port_number": 1,
                "port_id": port_id,
                "device_name": tv_info['name'],
                "ip_address": ip,
                "mac_address": device.mac_address,
                "protocol": tv_info['protocol'],
                "device_type": tv_info['device_type']
            },
            "scan_cache_device": {
                "ip": device.ip_address,
                "mac": device.mac_address,
                "vendor": device.vendor,
                "hostname": device.hostname,
                "device_type": device.device_type_guess,
                "is_adopted": True
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to adopt device: {str(e)}")


@router.delete("/adopt/{ip}")
async def unadopt_device(ip: str, db: Session = Depends(get_db)):
    """
    Un-adopt a device

    This endpoint:
    1. Finds and deletes the Virtual Controller for this device
    2. Deletes the Virtual Device mapping (cascade delete)
    3. Marks the device as not adopted in scan cache

    Makes it show up in discovery list again
    """
    from ..models.virtual_controller import VirtualController, VirtualDevice

    try:
        device = db.query(NetworkScanCache).filter_by(ip_address=ip).first()

        if not device:
            raise HTTPException(status_code=404, detail=f"Device {ip} not found in scan cache")

        # Find and delete Virtual Device and its Controller
        virtual_device = db.query(VirtualDevice).filter_by(ip_address=ip).first()

        deleted_controller = None
        deleted_device = None

        if virtual_device:
            # Get controller info before deletion
            virtual_controller = db.query(VirtualController).filter_by(id=virtual_device.controller_id).first()

            if virtual_controller:
                deleted_controller = {
                    "id": virtual_controller.id,
                    "controller_id": virtual_controller.controller_id,
                    "controller_name": virtual_controller.controller_name
                }
                # Delete controller (will cascade delete virtual_device)
                db.delete(virtual_controller)

            deleted_device = {
                "id": virtual_device.id,
                "port_number": virtual_device.port_number,
                "device_name": virtual_device.device_name
            }

        # Mark as not adopted
        device.is_adopted = False
        db.commit()

        return {
            "success": True,
            "message": f"Device {ip} has been un-adopted and Virtual Controller removed",
            "deleted_virtual_controller": deleted_controller,
            "deleted_virtual_device": deleted_device,
            "scan_cache_device": {
                "ip": device.ip_address,
                "is_adopted": False
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to un-adopt device: {str(e)}")


@router.post("/hide/{mac_address}")
async def hide_device(mac_address: str, db: Session = Depends(get_db)):
    """
    Hide a device by MAC address

    Hidden devices will not appear in the discovery list.
    The device can be unhidden later from the hidden devices list.
    """
    try:
        # Normalize MAC address format (uppercase with colons)
        mac = mac_address.upper().replace('-', ':')

        device = db.query(NetworkScanCache).filter_by(mac_address=mac).first()

        if not device:
            raise HTTPException(status_code=404, detail=f"Device with MAC {mac_address} not found in scan cache")

        if device.is_hidden:
            raise HTTPException(status_code=400, detail=f"Device {mac_address} is already hidden")

        device.is_hidden = True
        db.commit()

        return {
            "success": True,
            "message": f"Device {device.vendor or 'Unknown'} ({mac}) has been hidden from discovery",
            "device": {
                "ip": device.ip_address,
                "mac": device.mac_address,
                "vendor": device.vendor,
                "hostname": device.hostname,
                "is_hidden": True
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to hide device: {str(e)}")


@router.delete("/hide/{mac_address}")
async def unhide_device(mac_address: str, db: Session = Depends(get_db)):
    """
    Unhide a device by MAC address

    Device will reappear in the discovery list on next scan.
    """
    try:
        # Normalize MAC address format (uppercase with colons)
        mac = mac_address.upper().replace('-', ':')

        device = db.query(NetworkScanCache).filter_by(mac_address=mac).first()

        if not device:
            raise HTTPException(status_code=404, detail=f"Device with MAC {mac_address} not found in scan cache")

        if not device.is_hidden:
            raise HTTPException(status_code=400, detail=f"Device {mac_address} is not hidden")

        device.is_hidden = False
        db.commit()

        return {
            "success": True,
            "message": f"Device {device.vendor or 'Unknown'} ({mac}) has been unhidden",
            "device": {
                "ip": device.ip_address,
                "mac": device.mac_address,
                "vendor": device.vendor,
                "hostname": device.hostname,
                "is_hidden": False
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to unhide device: {str(e)}")


@router.get("/hidden", response_model=List[TVInfo])
async def list_hidden_devices(db: Session = Depends(get_db)):
    """
    List all hidden devices

    Returns all devices that have been hidden from discovery.
    """
    hidden_devices = db.query(NetworkScanCache).filter(
        NetworkScanCache.is_hidden == True
    ).all()

    result = []
    for device in hidden_devices:
        tv_info = get_tv_from_scan_cache(device.ip_address, db)

        if tv_info:
            result.append(TVInfo(
                ip=tv_info["ip"],
                name=tv_info["name"],
                model=tv_info["model"],
                mac=tv_info["mac"],
                protocol=tv_info["protocol"],
                status="hidden",
                device_type=tv_info["device_type"],
                vendor=tv_info["vendor"],
                ports=[tv_info["port"]] if tv_info["port"] else []
            ))

    return result
