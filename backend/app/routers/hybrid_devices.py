"""
Hybrid Device Management API
Endpoints for linking/unlinking IR fallback to network TVs
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..db.database import get_db
from ..models.virtual_controller import VirtualDevice
from ..models.device_management import ManagedDevice, IRPort
from ..commands.hybrid_router import HybridCommandRouter

router = APIRouter(prefix="/hybrid-devices", tags=["hybrid-devices"])


# ============================================================================
# Pydantic Models
# ============================================================================

class LinkIRRequest(BaseModel):
    ir_controller_hostname: str
    ir_port: int  # 0-4
    power_on_method: str = "hybrid"  # "network", "ir", "hybrid"
    control_strategy: str = "hybrid_ir_fallback"  # "network_only", "hybrid_ir_fallback", "ir_only"


class LinkIRResponse(BaseModel):
    success: bool
    message: str
    device_id: int
    ir_controller: str
    ir_port: int
    power_on_method: str


class UnlinkIRResponse(BaseModel):
    success: bool
    message: str
    device_id: int


class ControlStatusResponse(BaseModel):
    device_id: int
    device_name: str
    network_available: bool
    ir_fallback_configured: bool
    power_on_method: str
    control_strategy: str
    recommended_power_on: str
    status_available: bool
    protocol: Optional[str]
    ir_controller: Optional[str] = None
    ir_port: Optional[int] = None


class DeviceStatusResponse(BaseModel):
    device_id: int
    device_name: str
    is_online: bool
    power_state: Optional[str] = None
    volume_level: Optional[int] = None
    mute_status: Optional[bool] = None
    current_input: Optional[str] = None
    current_app: Optional[str] = None
    last_status_poll: Optional[str] = None
    status_available: bool


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/{device_id}/link-ir-fallback", response_model=LinkIRResponse)
async def link_ir_fallback(
    device_id: int,
    request: LinkIRRequest,
    db: Session = Depends(get_db)
):
    """
    Link an IR controller port as fallback for a network TV

    This enables hybrid control:
    - IR for power-on (reliable)
    - Network for everything else (fast, status feedback)
    """
    # Get virtual device
    device = db.query(VirtualDevice).filter(VirtualDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    # Validate IR controller exists
    ir_controller = db.query(ManagedDevice).filter(
        ManagedDevice.hostname == request.ir_controller_hostname
    ).first()

    if not ir_controller:
        raise HTTPException(
            status_code=404,
            detail=f"IR controller {request.ir_controller_hostname} not found"
        )

    # Validate IR port number
    if request.ir_port < 0 or request.ir_port >= (ir_controller.total_ir_ports or 5):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid IR port {request.ir_port}. Must be 0-{(ir_controller.total_ir_ports or 5) - 1}"
        )

    # Check if IR port is already in use
    existing_port = db.query(IRPort).filter(
        IRPort.device_id == ir_controller.id,
        IRPort.port_number == request.ir_port
    ).first()

    if existing_port:
        # Check if it's already linked to this device
        if existing_port.connected_device_name == device.device_name:
            pass  # OK, re-linking same device
        else:
            raise HTTPException(
                status_code=400,
                detail=f"IR port {request.ir_port} already in use by {existing_port.connected_device_name}"
            )

    # Validate power_on_method
    valid_power_on_methods = ["network", "ir", "hybrid"]
    if request.power_on_method not in valid_power_on_methods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid power_on_method. Must be one of {valid_power_on_methods}"
        )

    # Validate control_strategy
    valid_strategies = ["network_only", "hybrid_ir_fallback", "ir_only"]
    if request.control_strategy not in valid_strategies:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid control_strategy. Must be one of {valid_strategies}"
        )

    # Link IR fallback
    device.fallback_ir_controller = request.ir_controller_hostname
    device.fallback_ir_port = request.ir_port
    device.power_on_method = request.power_on_method
    device.control_strategy = request.control_strategy

    # Create or update IR port entry
    if not existing_port:
        ir_port_entry = IRPort(
            device_id=ir_controller.id,
            port_number=request.ir_port,
            port_id=f"{ir_controller.hostname}-{request.ir_port}",
            connected_device_name=device.device_name,
            installation_notes=f"Linked to network TV {device.device_name} as hybrid fallback"
        )
        db.add(ir_port_entry)
    else:
        existing_port.connected_device_name = device.device_name
        existing_port.installation_notes = f"Linked to network TV {device.device_name} as hybrid fallback"

    db.commit()

    return LinkIRResponse(
        success=True,
        message=f"IR fallback linked successfully",
        device_id=device.id,
        ir_controller=request.ir_controller_hostname,
        ir_port=request.ir_port,
        power_on_method=request.power_on_method
    )


@router.delete("/{device_id}/unlink-ir-fallback", response_model=UnlinkIRResponse)
async def unlink_ir_fallback(
    device_id: int,
    db: Session = Depends(get_db)
):
    """
    Unlink IR fallback from a network TV

    Device will return to network-only control
    """
    # Get virtual device
    device = db.query(VirtualDevice).filter(VirtualDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    if not device.fallback_ir_controller:
        raise HTTPException(status_code=400, detail="Device has no IR fallback linked")

    # Find and update IR port entry
    ir_controller = db.query(ManagedDevice).filter(
        ManagedDevice.hostname == device.fallback_ir_controller
    ).first()

    if ir_controller:
        ir_port_entry = db.query(IRPort).filter(
            IRPort.device_id == ir_controller.id,
            IRPort.port_number == device.fallback_ir_port
        ).first()

        if ir_port_entry:
            ir_port_entry.connected_device_name = None
            ir_port_entry.installation_notes = None

    # Unlink IR fallback
    device.fallback_ir_controller = None
    device.fallback_ir_port = None
    device.power_on_method = "network"
    device.control_strategy = "network_only"

    db.commit()

    return UnlinkIRResponse(
        success=True,
        message="IR fallback unlinked successfully",
        device_id=device.id
    )


@router.get("/{device_id}/control-status", response_model=ControlStatusResponse)
async def get_control_status(
    device_id: int,
    db: Session = Depends(get_db)
):
    """
    Get control status for a device

    Returns:
    - Network availability
    - IR fallback configuration
    - Power-on method
    - Control strategy
    - Recommended settings
    """
    # Get virtual device
    device = db.query(VirtualDevice).filter(VirtualDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    # Get control status from hybrid router
    router_instance = HybridCommandRouter(db)
    status = router_instance.get_device_control_status(device)

    return ControlStatusResponse(
        device_id=device.id,
        device_name=device.device_name,
        network_available=status["network_available"],
        ir_fallback_configured=status["ir_fallback_configured"],
        power_on_method=status["power_on_method"],
        control_strategy=status["control_strategy"],
        recommended_power_on=status["recommended_power_on"],
        status_available=status["status_available"],
        protocol=status["protocol"],
        ir_controller=device.fallback_ir_controller,
        ir_port=device.fallback_ir_port
    )


@router.get("/{device_id}/status", response_model=DeviceStatusResponse)
async def get_device_status(
    device_id: int,
    db: Session = Depends(get_db)
):
    """
    Get current status for a device

    Returns cached status from last poll (if status_available)
    """
    # Get virtual device
    device = db.query(VirtualDevice).filter(VirtualDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    return DeviceStatusResponse(
        device_id=device.id,
        device_name=device.device_name,
        is_online=device.is_online or False,
        power_state=device.cached_power_state,
        volume_level=device.cached_volume_level,
        mute_status=device.cached_mute_status,
        current_input=device.cached_current_input,
        current_app=device.cached_current_app,
        last_status_poll=device.last_status_poll.isoformat() if device.last_status_poll else None,
        status_available=device.status_available or False
    )


@router.post("/{device_id}/refresh-status")
async def refresh_status(
    device_id: int,
    db: Session = Depends(get_db)
):
    """
    Manually trigger a status refresh for a device

    Useful for immediate status check before polling service updates
    """
    # Get virtual device
    device = db.query(VirtualDevice).filter(VirtualDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    if not device.status_available:
        raise HTTPException(
            status_code=400,
            detail=f"Device {device.device_name} does not support status queries"
        )

    # Trigger immediate poll
    from ..services.tv_status_poller import tv_status_poller
    await tv_status_poller._poll_device(device, db)

    return {
        "success": True,
        "message": "Status refreshed",
        "device_id": device.id,
        "power_state": device.cached_power_state,
        "volume_level": device.cached_volume_level,
        "current_input": device.cached_current_input,
        "current_app": device.cached_current_app
    }
