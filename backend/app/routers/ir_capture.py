"""
IR Remote Code Capture API - MVP Version

Simple API for manual IR code capture workflow:
1. Create capture session
2. User manually pastes codes from ESP logs
3. Save complete remote profile

Full automated capture will be added in Phase 2.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import json
import logging
import httpx

from ..db.database import get_db
from ..models.ir_capture import CaptureSession, CapturedIRCode, CapturedRemote, CapturedRemoteButton

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ir-capture", tags=["IR Capture"])


# ==================== REQUEST/RESPONSE MODELS ====================

class CreateSessionRequest(BaseModel):
    session_name: str = Field(..., description="Name for this remote (e.g., 'Living Room TV')")
    device_type: str = Field(default="TV", description="Device type: TV, Projector, AC, Audio")
    brand: Optional[str] = Field(None, description="Brand name (optional)")
    model: Optional[str] = Field(None, description="Model number (optional)")
    notes: Optional[str] = Field(None, description="Additional notes")


class SessionResponse(BaseModel):
    id: int
    session_name: str
    device_type: str
    brand: Optional[str]
    model: Optional[str]
    status: str
    code_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class AddCodeRequest(BaseModel):
    button_name: str = Field(..., description="Button name (e.g., 'Power', 'Volume Up')")
    button_category: Optional[str] = Field(None, description="Category: power, volume, channel, number, menu")
    protocol: str = Field(default="RAW", description="Protocol: RAW, NEC, Samsung, LG, etc.")
    raw_data: str = Field(..., description="Raw timing data as comma-separated string or JSON array")
    decoded_address: Optional[str] = Field(None, description="Decoded address (if protocol detected)")
    decoded_command: Optional[str] = Field(None, description="Decoded command (if protocol detected)")
    decoded_data: Optional[str] = Field(None, description="Decoded data (for LG/Sony protocols)")


class CodeResponse(BaseModel):
    id: int
    button_name: str
    button_category: Optional[str]
    protocol: str
    has_raw_data: bool
    capture_timestamp: datetime

    class Config:
        from_attributes = True


class CreateRemoteRequest(BaseModel):
    session_id: int = Field(..., description="Capture session ID")
    name: str = Field(..., description="Name for this remote")
    description: Optional[str] = Field(None, description="Optional description")
    is_favorite: bool = Field(default=False, description="Mark as favorite")


class RemoteResponse(BaseModel):
    id: int
    name: str
    device_type: str
    brand: Optional[str]
    model: Optional[str]
    button_count: int
    is_favorite: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RemoteDetailResponse(BaseModel):
    id: int
    name: str
    device_type: str
    brand: Optional[str]
    model: Optional[str]
    description: Optional[str]
    button_count: int
    is_favorite: bool
    buttons: List[dict]
    created_at: datetime


# ==================== ENDPOINTS ====================

@router.post("/sessions", response_model=SessionResponse)
async def create_capture_session(
    request: CreateSessionRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new IR code capture session.

    This starts a new workflow for capturing codes from a remote control.
    """

    session = CaptureSession(
        device_hostname="manual",  # MVP: no ESP device integration yet
        session_name=request.session_name,
        device_type=request.device_type,
        brand=request.brand,
        model=request.model,
        capture_mode="manual",
        status="active",
        notes=request.notes,
        captured_buttons=json.dumps([])
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    logger.info(f"Created capture session {session.id}: {session.session_name}")

    return SessionResponse(
        id=session.id,
        session_name=session.session_name,
        device_type=session.device_type,
        brand=session.brand,
        model=session.model,
        status=session.status,
        code_count=0,
        created_at=session.created_at
    )


@router.get("/sessions", response_model=List[SessionResponse])
async def list_capture_sessions(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all capture sessions.

    Optionally filter by status: active, completed, cancelled
    """

    query = db.query(CaptureSession)

    if status:
        query = query.filter(CaptureSession.status == status)

    sessions = query.order_by(desc(CaptureSession.created_at)).all()

    # Get code counts for each session
    result = []
    for session in sessions:
        code_count = db.query(CapturedIRCode).filter(
            CapturedIRCode.session_id == session.id,
            CapturedIRCode.is_valid == True
        ).count()

        result.append(SessionResponse(
            id=session.id,
            session_name=session.session_name,
            device_type=session.device_type,
            brand=session.brand,
            model=session.model,
            status=session.status,
            code_count=code_count,
            created_at=session.created_at
        ))

    return result


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_capture_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Get details for a specific capture session"""

    session = db.query(CaptureSession).filter(CaptureSession.id == session_id).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    code_count = db.query(CapturedIRCode).filter(
        CapturedIRCode.session_id == session.id,
        CapturedIRCode.is_valid == True
    ).count()

    return SessionResponse(
        id=session.id,
        session_name=session.session_name,
        device_type=session.device_type,
        brand=session.brand,
        model=session.model,
        status=session.status,
        code_count=code_count,
        created_at=session.created_at
    )


@router.post("/sessions/{session_id}/codes", response_model=CodeResponse)
async def add_code_to_session(
    session_id: int,
    request: AddCodeRequest,
    db: Session = Depends(get_db)
):
    """
    Add a captured IR code to a session (MVP: manual paste from logs).

    User copies code from ESP device logs and pastes here.
    Supports both raw timing data and decoded protocols.
    """

    # Verify session exists
    session = db.query(CaptureSession).filter(CaptureSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Parse raw_data (handle both comma-separated string and JSON array)
    try:
        if request.raw_data.startswith('['):
            # Already JSON array format
            raw_data_json = request.raw_data
        else:
            # Comma-separated string - convert to JSON array
            values = [int(v.strip()) for v in request.raw_data.split(',') if v.strip()]
            raw_data_json = json.dumps(values)
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid raw_data format: {e}")

    # Create code record
    code = CapturedIRCode(
        session_id=session_id,
        button_name=request.button_name,
        button_category=request.button_category,
        protocol=request.protocol,
        raw_data=raw_data_json,
        decoded_address=request.decoded_address,
        decoded_command=request.decoded_command,
        decoded_data=request.decoded_data,
        is_valid=True
    )

    db.add(code)

    # Update session's captured_buttons list
    captured_buttons = json.loads(session.captured_buttons) if session.captured_buttons else []
    if request.button_name not in captured_buttons:
        captured_buttons.append(request.button_name)
        session.captured_buttons = json.dumps(captured_buttons)

    session.updated_at = datetime.now()

    db.commit()
    db.refresh(code)

    logger.info(f"Added code '{request.button_name}' to session {session_id}")

    return CodeResponse(
        id=code.id,
        button_name=code.button_name,
        button_category=code.button_category,
        protocol=code.protocol,
        has_raw_data=bool(code.raw_data),
        capture_timestamp=code.capture_timestamp
    )


@router.get("/sessions/{session_id}/codes", response_model=List[CodeResponse])
async def list_session_codes(
    session_id: int,
    db: Session = Depends(get_db)
):
    """List all codes captured in a session"""

    codes = db.query(CapturedIRCode).filter(
        CapturedIRCode.session_id == session_id,
        CapturedIRCode.is_valid == True
    ).order_by(CapturedIRCode.created_at).all()

    return [
        CodeResponse(
            id=code.id,
            button_name=code.button_name,
            button_category=code.button_category,
            protocol=code.protocol,
            has_raw_data=bool(code.raw_data),
            capture_timestamp=code.capture_timestamp
        )
        for code in codes
    ]


@router.delete("/sessions/{session_id}/codes/{code_id}")
async def delete_code(
    session_id: int,
    code_id: int,
    db: Session = Depends(get_db)
):
    """Delete a captured code (in case of mistakes)"""

    code = db.query(CapturedIRCode).filter(
        CapturedIRCode.id == code_id,
        CapturedIRCode.session_id == session_id
    ).first()

    if not code:
        raise HTTPException(status_code=404, detail="Code not found")

    db.delete(code)
    db.commit()

    return {"message": "Code deleted", "code_id": code_id}


@router.post("/sessions/{session_id}/complete")
async def complete_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Mark capture session as complete"""

    session = db.query(CaptureSession).filter(CaptureSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.status = "completed"
    session.completed_at = datetime.now()
    db.commit()

    return {"message": "Session completed", "session_id": session_id}


@router.post("/remotes", response_model=RemoteResponse)
async def create_captured_remote(
    request: CreateRemoteRequest,
    db: Session = Depends(get_db)
):
    """
    Create a custom remote profile from a completed capture session.

    This converts the captured codes into a usable remote profile.
    """

    # Verify session exists
    session = db.query(CaptureSession).filter(CaptureSession.id == request.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get all captured codes
    codes = db.query(CapturedIRCode).filter(
        CapturedIRCode.session_id == request.session_id,
        CapturedIRCode.is_valid == True
    ).all()

    if not codes:
        raise HTTPException(status_code=400, detail="No codes captured in this session")

    # Create remote
    remote = CapturedRemote(
        name=request.name,
        device_type=session.device_type,
        brand=session.brand,
        model=session.model,
        source_session_id=session.id,
        description=request.description,
        button_count=len(codes),
        is_favorite=request.is_favorite
    )

    db.add(remote)
    db.flush()  # Get remote.id

    # Create button mappings
    for code in codes:
        button = CapturedRemoteButton(
            remote_id=remote.id,
            code_id=code.id,
            button_name=code.button_name,
            button_label=code.button_name,
            button_category=code.button_category
        )
        db.add(button)

    db.commit()
    db.refresh(remote)

    logger.info(f"Created custom remote '{remote.name}' with {len(codes)} buttons")

    return RemoteResponse(
        id=remote.id,
        name=remote.name,
        device_type=remote.device_type,
        brand=remote.brand,
        model=remote.model,
        button_count=remote.button_count,
        is_favorite=remote.is_favorite,
        created_at=remote.created_at
    )


@router.get("/remotes", response_model=List[RemoteResponse])
async def list_captured_remotes(
    device_type: Optional[str] = None,
    favorites_only: bool = False,
    db: Session = Depends(get_db)
):
    """List all captured remote profiles"""

    query = db.query(CapturedRemote)

    if device_type:
        query = query.filter(CapturedRemote.device_type == device_type)

    if favorites_only:
        query = query.filter(CapturedRemote.is_favorite == True)

    remotes = query.order_by(desc(CapturedRemote.created_at)).all()

    return [
        RemoteResponse(
            id=remote.id,
            name=remote.name,
            device_type=remote.device_type,
            brand=remote.brand,
            model=remote.model,
            button_count=remote.button_count,
            is_favorite=remote.is_favorite,
            created_at=remote.created_at
        )
        for remote in remotes
    ]


@router.get("/remotes/{remote_id}", response_model=RemoteDetailResponse)
async def get_remote_detail(
    remote_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed information about a captured remote including all buttons"""

    remote = db.query(CapturedRemote).filter(CapturedRemote.id == remote_id).first()
    if not remote:
        raise HTTPException(status_code=404, detail="Remote not found")

    # Get all buttons with their codes
    buttons_query = db.query(CapturedRemoteButton, CapturedIRCode).join(
        CapturedIRCode,
        CapturedRemoteButton.code_id == CapturedIRCode.id
    ).filter(
        CapturedRemoteButton.remote_id == remote_id
    ).all()

    buttons = [
        {
            "button_name": button.button_name,
            "button_label": button.button_label,
            "button_category": button.button_category,
            "protocol": code.protocol,
            "has_raw_data": bool(code.raw_data)
        }
        for button, code in buttons_query
    ]

    return RemoteDetailResponse(
        id=remote.id,
        name=remote.name,
        device_type=remote.device_type,
        brand=remote.brand,
        model=remote.model,
        description=remote.description,
        button_count=remote.button_count,
        is_favorite=remote.is_favorite,
        buttons=buttons,
        created_at=remote.created_at
    )


@router.delete("/remotes/{remote_id}")
async def delete_remote(
    remote_id: int,
    db: Session = Depends(get_db)
):
    """Delete a captured remote profile"""

    remote = db.query(CapturedRemote).filter(CapturedRemote.id == remote_id).first()
    if not remote:
        raise HTTPException(status_code=404, detail="Remote not found")

    db.delete(remote)
    db.commit()

    return {"message": "Remote deleted", "remote_id": remote_id}


# ==================== ESP DEVICE INTEGRATION ====================

@router.get("/device/status")
async def get_device_status():
    """Get IR capture device status and info"""

    device_ip = "192.168.101.126"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Get device info
            ip_response = await client.get(f"http://{device_ip}/text_sensor/ir_capture_device_ip_address")
            wifi_response = await client.get(f"http://{device_ip}/sensor/ir_capture_device_wifi_signal")
            status_response = await client.get(f"http://{device_ip}/binary_sensor/ir_capture_device_status")

            return {
                "online": True,
                "ip_address": device_ip,
                "ip_info": ip_response.json() if ip_response.status_code == 200 else None,
                "wifi_signal": wifi_response.json() if wifi_response.status_code == 200 else None,
                "status": status_response.json() if status_response.status_code == 200 else None,
            }
    except Exception as e:
        logger.error(f"Failed to get device status: {e}")
        return {
            "online": False,
            "ip_address": device_ip,
            "error": str(e)
        }


@router.get("/device/last-code")
async def get_last_captured_code():
    """Get the last IR code captured by the ESP32 device"""

    device_ip = "192.168.101.126"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"http://{device_ip}/text_sensor/ir_capture_device_last_ir_code"
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "raw_data": data.get("value", ""),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch code from device")

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Device timeout - is it online?")
    except Exception as e:
        logger.error(f"Failed to get last code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class TestCodeRequest(BaseModel):
    raw_data: str = Field(..., description="Raw IR timing data as JSON array or comma-separated string")


@router.post("/device/test-code")
async def test_ir_code(request: TestCodeRequest):
    """Test transmitting an IR code via the ESP32 device"""

    device_ip = "192.168.101.126"

    # Parse raw data
    try:
        if request.raw_data.startswith("["):
            raw_array = json.loads(request.raw_data)
        else:
            raw_array = [int(x.strip()) for x in request.raw_data.split(",")]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid raw_data format: {e}")

    try:
        # Call ESPHome button to transmit the code
        async with httpx.AsyncClient(timeout=10.0) as client:
            # For now, just return success - actual IR transmission would require
            # a button or service on the ESP device
            return {
                "success": True,
                "message": "Code transmission not yet implemented",
                "raw_data": raw_array
            }

    except Exception as e:
        logger.error(f"Failed to test code: {e}")
        raise HTTPException(status_code=500, detail=str(e))
