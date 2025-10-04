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

    # Get ALL non-adopted devices from TV vendors
    query = db.query(NetworkScanCache).filter(
        NetworkScanCache.is_adopted == False
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
    Marks it as adopted so it won't show in discovery list
    """
    try:
        device = db.query(NetworkScanCache).filter_by(ip_address=ip).first()

        if not device:
            raise HTTPException(status_code=404, detail=f"Device {ip} not found in scan cache")

        if device.is_adopted:
            raise HTTPException(status_code=400, detail=f"Device {ip} is already adopted")

        # Mark as adopted
        device.is_adopted = True
        db.commit()

        return {
            "success": True,
            "message": f"Device {ip} ({device.vendor or 'Unknown'}) has been adopted",
            "device": {
                "ip": device.ip_address,
                "mac": device.mac_address,
                "vendor": device.vendor,
                "hostname": device.hostname,
                "device_type": device.device_type_guess
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
    Un-adopt a device (mark as not adopted)
    Makes it show up in discovery list again
    """
    try:
        device = db.query(NetworkScanCache).filter_by(ip_address=ip).first()

        if not device:
            raise HTTPException(status_code=404, detail=f"Device {ip} not found in scan cache")

        # Mark as not adopted
        device.is_adopted = False
        db.commit()

        return {
            "success": True,
            "message": f"Device {ip} has been un-adopted"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to un-adopt device: {str(e)}")
