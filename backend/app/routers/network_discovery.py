"""
Network Discovery API
Endpoints for network scanning, device discovery, and adoption
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
import asyncio
import logging

from ..db.database import get_db
from ..services.network_sweep import network_sweep_service
from ..models.network_discovery import NetworkScanCache
from ..utils.network_utils import get_default_subnet

router = APIRouter(prefix="/api/network", tags=["network-discovery"])
logger = logging.getLogger(__name__)

# Track active scans
active_scans = {}


class ScanRequest(BaseModel):
    subnet: Optional[str] = None  # Will auto-detect if not provided
    start: Optional[int] = 1
    end: Optional[int] = 254


class BrandScanRequest(BaseModel):
    brand: str  # "Samsung", "LG", "Sony", "Philips"
    subnet: Optional[str] = None  # Will auto-detect if not provided


class DeviceInfo(BaseModel):
    ip_address: str
    mac_address: str
    vendor: Optional[str]
    hostname: Optional[str]
    is_online: bool
    response_time_ms: Optional[float]
    device_type_guess: Optional[str]
    is_adopted: bool = False

    class Config:
        from_attributes = True


@router.post("/scan/trigger")
async def trigger_network_scan(
    request: ScanRequest = ScanRequest(),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Trigger immediate network scan (manual button trigger)

    This performs a scan immediately and returns results when complete.
    Auto-detects local subnet if not specified.
    """
    try:
        # Auto-detect subnet if not provided
        subnet = request.subnet if request.subnet else get_default_subnet()

        logger.info(f"Manual scan triggered: {subnet}.{request.start}-{request.end}")

        devices = await network_sweep_service.scan_subnet(
            subnet=subnet,
            start=request.start,
            end=request.end,
            db_session=db
        )

        return {
            "success": True,
            "message": f"Network scan completed",
            "devices_found": len(devices),
            "subnet": subnet,
            "range": f"{request.start}-{request.end}",
            "auto_detected": request.subnet is None,
            "note": "Scan cache has been updated. Use GET /api/network/scan-cache to retrieve results"
        }

    except Exception as e:
        logger.error(f"Failed to trigger scan: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger scan: {str(e)}")


@router.get("/scan-status/{scan_id}")
async def get_scan_status(scan_id: str):
    """
    Check status of a background scan
    """
    if scan_id not in active_scans:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")

    return {
        "success": True,
        "scan_id": scan_id,
        **active_scans[scan_id]
    }


@router.post("/scan/tvs")
async def scan_tvs(
    request: ScanRequest = ScanRequest(),
    db: Session = Depends(get_db)
):
    """
    Quick scan for TV devices only

    Returns only devices that match known TV vendor MACs.
    Auto-detects local subnet if not specified.
    """
    try:
        # Auto-detect subnet if not provided
        subnet = request.subnet if request.subnet else get_default_subnet()

        tv_devices = await network_sweep_service.scan_for_tvs(
            subnet=subnet,
            db_session=db
        )

        return {
            "success": True,
            "total_found": len(tv_devices),
            "subnet": subnet,
            "auto_detected": request.subnet is None,
            "devices": tv_devices
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TV scan failed: {str(e)}")


@router.post("/scan/brand/{brand}")
async def scan_brand(
    brand: str,
    request: ScanRequest = ScanRequest(),
    db: Session = Depends(get_db)
):
    """
    Scan for specific brand devices

    Brands: Samsung, LG, Sony, Philips.
    Auto-detects local subnet if not specified.
    """
    try:
        # Auto-detect subnet if not provided
        subnet = request.subnet if request.subnet else get_default_subnet()

        brand_devices = await network_sweep_service.scan_for_brand(
            brand=brand,
            subnet=subnet,
            db_session=db
        )

        return {
            "success": True,
            "brand": brand,
            "total_found": len(brand_devices),
            "subnet": subnet,
            "auto_detected": request.subnet is None,
            "devices": brand_devices
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{brand} scan failed: {str(e)}")


@router.get("/scan-cache")
async def get_scan_cache(
    adopted: Optional[bool] = None,
    brand: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get cached scan results

    Query params:
    - adopted: Filter by adoption status (true/false)
    - brand: Filter by vendor brand name
    """
    try:
        query = db.query(NetworkScanCache)

        if adopted is not None:
            query = query.filter(NetworkScanCache.is_adopted == adopted)

        if brand:
            query = query.filter(NetworkScanCache.vendor.like(f"%{brand}%"))

        devices = query.order_by(NetworkScanCache.last_seen.desc()).all()

        return {
            "success": True,
            "total": len(devices),
            "devices": [DeviceInfo.from_orm(d) for d in devices]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cache: {str(e)}")


@router.get("/scan-cache/tvs")
async def get_tv_cache(db: Session = Depends(get_db)):
    """
    Get only TV devices from scan cache
    """
    try:
        tv_types = ['samsung_tv', 'lg_tv', 'sony_tv', 'philips_tv', 'roku', 'apple_tv']

        devices = db.query(NetworkScanCache).filter(
            NetworkScanCache.device_type_guess.in_(tv_types)
        ).order_by(NetworkScanCache.last_seen.desc()).all()

        return {
            "success": True,
            "total": len(devices),
            "devices": [DeviceInfo.from_orm(d) for d in devices]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get TV cache: {str(e)}")


@router.delete("/scan-cache")
async def clear_scan_cache(db: Session = Depends(get_db)):
    """Clear all scan cache entries"""
    try:
        count = db.query(NetworkScanCache).delete()
        db.commit()

        return {
            "success": True,
            "message": f"Cleared {count} cache entries"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


@router.get("/vendors/search/{query}")
async def search_vendors(query: str, db: Session = Depends(get_db)):
    """
    Search MAC vendors

    Useful for finding all MAC prefixes for a brand
    """
    from ..models.network_discovery import MACVendor

    try:
        vendors = db.query(MACVendor).filter(
            MACVendor.vendor_name.like(f"%{query}%")
        ).limit(50).all()

        return {
            "success": True,
            "query": query,
            "total": len(vendors),
            "vendors": [
                {
                    "mac_prefix": v.mac_prefix,
                    "vendor_name": v.vendor_name,
                    "block_type": v.block_type
                }
                for v in vendors
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/last-scan-time")
async def get_last_scan_time(db: Session = Depends(get_db)):
    """
    Get timestamp of the last network scan
    Returns the most recent last_seen timestamp from the scan cache
    """
    try:
        latest_device = db.query(NetworkScanCache).order_by(
            NetworkScanCache.last_seen.desc()
        ).first()

        if latest_device:
            return {
                "success": True,
                "last_scan_time": latest_device.last_seen.isoformat() if latest_device.last_seen else None,
                "devices_in_cache": db.query(NetworkScanCache).count()
            }
        else:
            return {
                "success": True,
                "last_scan_time": None,
                "devices_in_cache": 0,
                "message": "No scans performed yet"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get last scan time: {str(e)}")


@router.get("/stats")
async def get_network_stats(db: Session = Depends(get_db)):
    """
    Get network discovery statistics
    """
    from ..models.network_discovery import MACVendor
    from ..utils.network_utils import get_local_ip_and_subnet

    try:
        total_cached = db.query(NetworkScanCache).count()
        online_count = db.query(NetworkScanCache).filter_by(is_online=True).count()
        adopted_count = db.query(NetworkScanCache).filter_by(is_adopted=True).count()

        tv_count = db.query(NetworkScanCache).filter(
            NetworkScanCache.device_type_guess.in_([
                'samsung_tv', 'lg_tv', 'sony_tv', 'philips_tv'
            ])
        ).count()

        # Vendor stats
        samsung_vendors = db.query(MACVendor).filter(
            MACVendor.vendor_name.like('%Samsung%')
        ).count()
        lg_vendors = db.query(MACVendor).filter(
            MACVendor.vendor_name.like('%LG %')
        ).count()
        sony_vendors = db.query(MACVendor).filter(
            MACVendor.vendor_name.like('%Sony%')
        ).count()

        # Network detection info
        local_ip, subnet = get_local_ip_and_subnet()

        return {
            "success": True,
            "scan_cache": {
                "total": total_cached,
                "online": online_count,
                "adopted": adopted_count,
                "potential_tvs": tv_count
            },
            "vendor_database": {
                "samsung_prefixes": samsung_vendors,
                "lg_prefixes": lg_vendors,
                "sony_prefixes": sony_vendors
            },
            "network_info": {
                "local_ip": local_ip,
                "detected_subnet": subnet,
                "scan_range": f"{subnet}.1-254" if subnet else None
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
