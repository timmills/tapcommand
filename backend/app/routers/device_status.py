"""
Device Status API Router

Endpoints for querying device status information
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from ..db.database import get_db
from ..models.device_status import DeviceStatus
from ..services.device_status_checker import status_checker

router = APIRouter(prefix="/api/v1/device-status", tags=["device-status"])


class DeviceStatusResponse(BaseModel):
    """Device status response model"""
    controller_id: str
    device_type: str
    protocol: Optional[str]
    is_online: bool
    power_state: str
    current_channel: Optional[str]
    current_input: Optional[str]
    volume_level: Optional[int]
    is_muted: Optional[bool]
    model_info: Optional[str]
    firmware_version: Optional[str]
    check_method: Optional[str]
    check_interval_seconds: int
    last_checked_at: Optional[datetime]
    last_changed_at: Optional[datetime]
    last_online_at: Optional[datetime]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[DeviceStatusResponse])
async def get_all_device_status(
    db: Session = Depends(get_db)
):
    """
    Get status for all devices

    Returns list of device status records
    """
    statuses = db.query(DeviceStatus).all()
    return statuses


@router.get("/{controller_id}", response_model=DeviceStatusResponse)
async def get_device_status(
    controller_id: str,
    db: Session = Depends(get_db)
):
    """
    Get status for a specific device

    Args:
        controller_id: Controller ID (e.g., 'nw-b85a97')

    Returns:
        Device status information
    """
    status = db.query(DeviceStatus).filter_by(
        controller_id=controller_id
    ).first()

    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"Device status not found for {controller_id}"
        )

    return status


@router.post("/{controller_id}/check", response_model=DeviceStatusResponse)
async def check_device_status_now(
    controller_id: str,
    db: Session = Depends(get_db)
):
    """
    Immediately check device status (on-demand)

    Args:
        controller_id: Controller ID to check

    Returns:
        Updated device status
    """
    status = await status_checker.check_device_now(controller_id)

    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"Device {controller_id} not found or check failed"
        )

    return status


@router.get("/online/count")
async def get_online_count(
    db: Session = Depends(get_db)
):
    """
    Get count of online devices

    Returns:
        Count of online devices by type
    """
    online_count = db.query(DeviceStatus).filter_by(is_online=True).count()
    total_count = db.query(DeviceStatus).count()

    return {
        "online": online_count,
        "total": total_count,
        "offline": total_count - online_count
    }


@router.get("/power/on", response_model=List[DeviceStatusResponse])
async def get_powered_on_devices(
    db: Session = Depends(get_db)
):
    """
    Get all devices that are powered on

    Returns:
        List of devices with power_state='on'
    """
    statuses = db.query(DeviceStatus).filter_by(power_state="on").all()
    return statuses


@router.get("/power/off", response_model=List[DeviceStatusResponse])
async def get_powered_off_devices(
    db: Session = Depends(get_db)
):
    """
    Get all devices that are powered off

    Returns:
        List of devices with power_state='off'
    """
    statuses = db.query(DeviceStatus).filter_by(power_state="off").all()
    return statuses
