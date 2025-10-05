"""
Virtual Controller Management API
Endpoints for managing virtual controllers and their devices
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime

from ..db.database import get_db
from ..models.virtual_controller import VirtualController, VirtualDevice

router = APIRouter(prefix="/api/virtual-controllers", tags=["virtual-controllers"])


class VirtualControllerInfo(BaseModel):
    id: int
    controller_id: str
    controller_name: str
    controller_type: str
    protocol: Optional[str]
    total_ports: int
    is_active: bool
    is_online: bool
    venue_name: Optional[str]
    location: Optional[str]
    created_at: datetime
    device_count: int = 0

    class Config:
        from_attributes = True


class VirtualDeviceInfo(BaseModel):
    id: int
    controller_id: int
    port_number: int
    port_id: Optional[str]
    device_name: str
    device_type: Optional[str]
    ip_address: str
    mac_address: Optional[str]
    port: Optional[int]
    protocol: Optional[str]
    is_active: bool
    is_online: bool

    class Config:
        from_attributes = True


class VirtualControllerWithDevices(BaseModel):
    controller: VirtualControllerInfo
    devices: List[VirtualDeviceInfo]


@router.get("/", response_model=List[VirtualControllerInfo])
async def list_virtual_controllers(
    controller_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    List all Virtual Controllers

    Query params:
    - controller_type: Filter by type (network_tv, streaming_device, etc.)
    - is_active: Filter by active status
    """
    try:
        query = db.query(VirtualController)

        if controller_type:
            query = query.filter(VirtualController.controller_type == controller_type)

        if is_active is not None:
            query = query.filter(VirtualController.is_active == is_active)

        controllers = query.order_by(VirtualController.created_at.desc()).all()

        # Add device count to each controller
        result = []
        for controller in controllers:
            controller_info = VirtualControllerInfo.from_orm(controller)
            controller_info.device_count = len(controller.virtual_devices)
            result.append(controller_info)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list controllers: {str(e)}")


@router.get("/{controller_id}", response_model=VirtualControllerWithDevices)
async def get_virtual_controller(
    controller_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific Virtual Controller with all its devices"""
    try:
        controller = db.query(VirtualController).filter_by(controller_id=controller_id).first()

        if not controller:
            raise HTTPException(status_code=404, detail=f"Virtual Controller {controller_id} not found")

        controller_info = VirtualControllerInfo.from_orm(controller)
        controller_info.device_count = len(controller.virtual_devices)

        devices = [VirtualDeviceInfo.from_orm(d) for d in controller.virtual_devices]

        return {
            "controller": controller_info,
            "devices": devices
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get controller: {str(e)}")


@router.get("/{controller_id}/devices", response_model=List[VirtualDeviceInfo])
async def list_controller_devices(
    controller_id: str,
    db: Session = Depends(get_db)
):
    """List all devices for a specific Virtual Controller"""
    try:
        controller = db.query(VirtualController).filter_by(controller_id=controller_id).first()

        if not controller:
            raise HTTPException(status_code=404, detail=f"Virtual Controller {controller_id} not found")

        devices = db.query(VirtualDevice).filter_by(controller_id=controller.id).order_by(VirtualDevice.port_number).all()

        return [VirtualDeviceInfo.from_orm(d) for d in devices]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list devices: {str(e)}")


@router.get("/{controller_id}/port/{port_number}", response_model=VirtualDeviceInfo)
async def get_device_on_port(
    controller_id: str,
    port_number: int,
    db: Session = Depends(get_db)
):
    """Get the device on a specific port of a Virtual Controller"""
    try:
        controller = db.query(VirtualController).filter_by(controller_id=controller_id).first()

        if not controller:
            raise HTTPException(status_code=404, detail=f"Virtual Controller {controller_id} not found")

        device = db.query(VirtualDevice).filter_by(
            controller_id=controller.id,
            port_number=port_number
        ).first()

        if not device:
            raise HTTPException(
                status_code=404,
                detail=f"No device found on port {port_number} of controller {controller_id}"
            )

        return VirtualDeviceInfo.from_orm(device)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get device: {str(e)}")


@router.delete("/{controller_id}")
async def delete_virtual_controller(
    controller_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a Virtual Controller and all its devices

    This will cascade delete all virtual devices on this controller
    and reset the is_adopted flag in network_scan_cache
    """
    try:
        from ..models.network_discovery import NetworkScanCache

        controller = db.query(VirtualController).filter_by(controller_id=controller_id).first()

        if not controller:
            raise HTTPException(status_code=404, detail=f"Virtual Controller {controller_id} not found")

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

        db.delete(controller)
        db.commit()

        return {
            "success": True,
            "message": f"Virtual Controller {controller_id} deleted. Devices returned to discovery pool.",
            "deleted_controller": {
                "controller_id": controller_id,
                "controller_name": controller.controller_name,
                "device_count": device_count
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete controller: {str(e)}")


@router.get("/devices/all", response_model=List[VirtualDeviceInfo])
async def list_all_virtual_devices(
    device_type: Optional[str] = None,
    is_online: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    List all Virtual Devices across all controllers

    Query params:
    - device_type: Filter by device type
    - is_online: Filter by online status
    """
    try:
        query = db.query(VirtualDevice)

        if device_type:
            query = query.filter(VirtualDevice.device_type == device_type)

        if is_online is not None:
            query = query.filter(VirtualDevice.is_online == is_online)

        devices = query.order_by(VirtualDevice.created_at.desc()).all()

        return [VirtualDeviceInfo.from_orm(d) for d in devices]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list devices: {str(e)}")


@router.get("/stats/summary")
async def get_virtual_controller_stats(db: Session = Depends(get_db)):
    """Get statistics about Virtual Controllers"""
    try:
        total_controllers = db.query(VirtualController).count()
        active_controllers = db.query(VirtualController).filter_by(is_active=True).count()
        online_controllers = db.query(VirtualController).filter_by(is_online=True).count()

        total_devices = db.query(VirtualDevice).count()
        active_devices = db.query(VirtualDevice).filter_by(is_active=True).count()
        online_devices = db.query(VirtualDevice).filter_by(is_online=True).count()

        # Count by controller type
        network_tv_count = db.query(VirtualController).filter_by(controller_type="network_tv").count()
        streaming_device_count = db.query(VirtualController).filter_by(controller_type="streaming_device").count()

        # Count by device type
        device_type_counts = {}
        device_types = db.query(VirtualDevice.device_type).distinct().all()
        for (device_type,) in device_types:
            if device_type:
                count = db.query(VirtualDevice).filter_by(device_type=device_type).count()
                device_type_counts[device_type] = count

        return {
            "success": True,
            "controllers": {
                "total": total_controllers,
                "active": active_controllers,
                "online": online_controllers,
                "by_type": {
                    "network_tv": network_tv_count,
                    "streaming_device": streaming_device_count
                }
            },
            "devices": {
                "total": total_devices,
                "active": active_devices,
                "online": online_devices,
                "by_type": device_type_counts
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
