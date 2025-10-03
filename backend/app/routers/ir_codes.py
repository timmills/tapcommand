from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional, Dict, Any
import logging

from ..db.database import get_db
from ..models.ir_codes import IRLibrary, IRCommand, IRImportLog, PortAssignment
from ..services.ir_import import import_flipper_irdb
from ..services.ir_updater import manual_ir_update

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ir-codes", tags=["IR Codes"])


@router.post("/import/flipper-irdb")
async def import_flipper_irdb_endpoint(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Import all IR codes from Flipper-IRDB repository"""

    # Check if import is already running
    running_import = db.query(IRImportLog).filter_by(status="running").first()
    if running_import:
        raise HTTPException(
            status_code=409,
            detail="Import already running"
        )

    # Start background import
    background_tasks.add_task(import_flipper_irdb, db)

    return {"message": "Import started in background"}


@router.post("/update")
async def update_ir_codes_endpoint(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Check for and import updates from IR code repositories"""

    # Check if import is already running
    running_import = db.query(IRImportLog).filter_by(status="running").first()
    if running_import:
        raise HTTPException(
            status_code=409,
            detail="Import already running"
        )

    # Start background update
    background_tasks.add_task(manual_ir_update, db)

    return {"message": "Update check started in background"}


@router.get("/import/status")
def get_import_status(db: Session = Depends(get_db)):
    """Get status of latest import"""

    latest_import = db.query(IRImportLog).order_by(desc(IRImportLog.created_at)).first()

    if not latest_import:
        return {"status": "none", "message": "No imports found"}

    return {
        "status": latest_import.status,
        "import_type": latest_import.import_type,
        "libraries_processed": latest_import.libraries_processed,
        "libraries_imported": latest_import.libraries_imported,
        "libraries_failed": latest_import.libraries_failed,
        "commands_imported": latest_import.commands_imported,
        "start_time": latest_import.start_time,
        "end_time": latest_import.end_time,
        "duration_seconds": latest_import.duration_seconds,
        "error_message": latest_import.error_message
    }


@router.get("/libraries")
def get_libraries(
    category: Optional[str] = None,
    brand: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get IR libraries with filtering"""

    query = db.query(IRLibrary).filter_by(import_status="imported")

    if category:
        query = query.filter(IRLibrary.device_category == category)

    if brand:
        query = query.filter(IRLibrary.brand == brand)

    if search:
        query = query.filter(IRLibrary.name.ilike(f"%{search}%"))

    total = query.count()
    libraries = query.offset(offset).limit(limit).all()

    return {
        "libraries": [
            {
                "id": lib.id,
                "name": lib.name,
                "device_category": lib.device_category,
                "brand": lib.brand,
                "model": lib.model,
                "description": lib.description,
                "command_count": len(lib.commands)
            }
            for lib in libraries
        ],
        "total": total,
        "offset": offset,
        "limit": limit
    }


@router.get("/libraries/{library_id}/commands")
def get_library_commands(
    library_id: int,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get commands for a specific library"""

    library = db.query(IRLibrary).filter_by(id=library_id).first()
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")

    query = db.query(IRCommand).filter_by(library_id=library_id)

    if category:
        query = query.filter(IRCommand.category == category)

    commands = query.all()

    return {
        "library": {
            "id": library.id,
            "name": library.name,
            "brand": library.brand,
            "model": library.model
        },
        "commands": [
            {
                "id": cmd.id,
                "name": cmd.name,
                "display_name": cmd.display_name,
                "category": cmd.category,
                "protocol": cmd.protocol,
                "signal_data": cmd.signal_data
            }
            for cmd in commands
        ]
    }


@router.get("/categories")
def get_device_categories(db: Session = Depends(get_db)):
    """Get all device categories"""

    categories = db.query(IRLibrary.device_category).distinct().all()
    return [cat[0] for cat in categories]


@router.get("/brands")
def get_brands(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all brands, optionally filtered by category"""

    query = db.query(IRLibrary.brand).distinct()

    if category:
        query = query.filter(IRLibrary.device_category == category)

    brands = query.all()
    return [brand[0] for brand in brands]


@router.get("/search")
def search_ir_codes(
    q: str,
    category: Optional[str] = None,
    brand: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Search IR codes by command name or library name"""

    # Search in libraries
    lib_query = db.query(IRLibrary).filter(
        IRLibrary.name.ilike(f"%{q}%")
    )

    if category:
        lib_query = lib_query.filter(IRLibrary.device_category == category)
    if brand:
        lib_query = lib_query.filter(IRLibrary.brand == brand)

    libraries = lib_query.limit(limit).all()

    # Search in commands
    cmd_query = db.query(IRCommand).join(IRLibrary).filter(
        IRCommand.name.ilike(f"%{q}%") | IRCommand.display_name.ilike(f"%{q}%")
    )

    if category:
        cmd_query = cmd_query.filter(IRLibrary.device_category == category)
    if brand:
        cmd_query = cmd_query.filter(IRLibrary.brand == brand)

    commands = cmd_query.limit(limit).all()

    return {
        "libraries": [
            {
                "id": lib.id,
                "name": lib.name,
                "brand": lib.brand,
                "category": lib.device_category,
                "command_count": len(lib.commands)
            }
            for lib in libraries
        ],
        "commands": [
            {
                "id": cmd.id,
                "name": cmd.name,
                "display_name": cmd.display_name,
                "category": cmd.category,
                "protocol": cmd.protocol,
                "library": {
                    "id": cmd.library.id,
                    "name": cmd.library.name,
                    "brand": cmd.library.brand
                }
            }
            for cmd in commands
        ]
    }


@router.get("/stats")
def get_ir_stats(db: Session = Depends(get_db)):
    """Get IR code database statistics"""

    stats = {
        "total_libraries": db.query(func.count(IRLibrary.id)).scalar(),
        "total_commands": db.query(func.count(IRCommand.id)).scalar(),
        "categories": db.query(func.count(func.distinct(IRLibrary.device_category))).scalar(),
        "brands": db.query(func.count(func.distinct(IRLibrary.brand))).scalar(),
    }

    # Top categories by library count
    top_categories = db.query(
        IRLibrary.device_category,
        func.count(IRLibrary.id).label('count')
    ).group_by(IRLibrary.device_category).order_by(desc('count')).limit(10).all()

    stats["top_categories"] = [
        {"category": cat[0], "count": cat[1]}
        for cat in top_categories
    ]

    # Top brands by library count
    top_brands = db.query(
        IRLibrary.brand,
        func.count(IRLibrary.id).label('count')
    ).group_by(IRLibrary.brand).order_by(desc('count')).limit(10).all()

    stats["top_brands"] = [
        {"brand": brand[0], "count": brand[1]}
        for brand in top_brands
    ]

    return stats


# Port assignment endpoints
@router.post("/port-assignments")
def create_port_assignment(
    assignment_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Assign an IR library to a device port"""

    # Validate library exists
    library = db.query(IRLibrary).filter_by(id=assignment_data["library_id"]).first()
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")

    # Check if port already assigned
    existing = db.query(PortAssignment).filter_by(
        device_hostname=assignment_data["device_hostname"],
        port_number=assignment_data["port_number"]
    ).first()

    if existing:
        # Update existing assignment
        existing.library_id = assignment_data["library_id"]
        existing.device_name = assignment_data.get("device_name")
        existing.is_active = assignment_data.get("is_active", True)
        existing.installation_notes = assignment_data.get("installation_notes")
        assignment = existing
    else:
        # Create new assignment
        assignment = PortAssignment(**assignment_data)
        db.add(assignment)

    db.commit()
    db.refresh(assignment)

    return {
        "id": assignment.id,
        "device_hostname": assignment.device_hostname,
        "port_number": assignment.port_number,
        "library": {
            "id": library.id,
            "name": library.name,
            "brand": library.brand
        },
        "device_name": assignment.device_name,
        "is_active": assignment.is_active
    }


@router.get("/port-assignments/{device_hostname}")
def get_device_port_assignments(
    device_hostname: str,
    db: Session = Depends(get_db)
):
    """Get port assignments for a device"""

    assignments = db.query(PortAssignment).filter_by(
        device_hostname=device_hostname
    ).all()

    return [
        {
            "id": assignment.id,
            "port_number": assignment.port_number,
            "library": {
                "id": assignment.library.id,
                "name": assignment.library.name,
                "brand": assignment.library.brand,
                "command_count": len(assignment.library.commands)
            },
            "device_name": assignment.device_name,
            "is_active": assignment.is_active,
            "last_command_sent": assignment.last_command_sent,
            "total_commands_sent": assignment.total_commands_sent
        }
        for assignment in assignments
    ]