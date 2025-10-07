"""
Hybrid Device Management API

Endpoints for managing hybrid control devices (network TVs with IR fallback).
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..db.database import get_db
from ..models.virtual_controller import VirtualDevice

router = APIRouter(prefix="/api/hybrid-devices", tags=["hybrid-devices"])


class LinkIRFallbackRequest(BaseModel):
    ir_controller_hostname: str
    ir_port: int
    power_on_method: str = "hybrid"  # "network", "ir", or "hybrid"
    control_strategy: str = "hybrid_ir_fallback"  # or "ir_only", "network_only"


class HybridDeviceStatusResponse(BaseModel):
    device_id: int
    device_name: str
    network_available: bool
    ir_fallback_configured: bool
    power_on_method: Optional[str]
    control_strategy: Optional[str]
    ir_controller: Optional[str]
    ir_port: Optional[int]
    protocol: str


@router.post("/{device_id}/link-ir-fallback")
async def link_ir_fallback(
    device_id: int,
    request: LinkIRFallbackRequest,
    db: Session = Depends(get_db)
):
    """Link an IR controller as fallback for a network TV device"""

    # Get virtual device
    device = db.query(VirtualDevice).filter(VirtualDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Virtual device not found")

    # Update hybrid configuration
    device.fallback_ir_controller = request.ir_controller_hostname
    device.fallback_ir_port = request.ir_port
    device.power_on_method = request.power_on_method
    device.control_strategy = request.control_strategy

    db.commit()

    return {
        "success": True,
        "message": "IR fallback linked successfully",
        "device_id": device_id,
        "ir_controller": request.ir_controller_hostname,
        "ir_port": request.ir_port,
        "power_on_method": request.power_on_method
    }


@router.delete("/{device_id}/unlink-ir-fallback")
async def unlink_ir_fallback(
    device_id: int,
    db: Session = Depends(get_db)
):
    """Remove IR fallback from a network TV device"""

    # Get virtual device
    device = db.query(VirtualDevice).filter(VirtualDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Virtual device not found")

    # Remove hybrid configuration
    device.fallback_ir_controller = None
    device.fallback_ir_port = None
    device.power_on_method = "network"
    device.control_strategy = "network_only"

    db.commit()

    return {
        "success": True,
        "message": "IR fallback unlinked successfully",
        "device_id": device_id
    }


@router.get("/{device_id}/control-status", response_model=HybridDeviceStatusResponse)
async def get_control_status(
    device_id: int,
    db: Session = Depends(get_db)
):
    """Get hybrid control status for a device"""

    device = db.query(VirtualDevice).filter(VirtualDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Virtual device not found")

    return HybridDeviceStatusResponse(
        device_id=device.id,
        device_name=device.device_name or "Unknown",
        network_available=True,  # Network TVs always have network available
        ir_fallback_configured=device.fallback_ir_controller is not None,
        power_on_method=device.power_on_method,
        control_strategy=device.control_strategy,
        ir_controller=device.fallback_ir_controller,
        ir_port=device.fallback_ir_port,
        protocol=device.protocol or "unknown"
    )
