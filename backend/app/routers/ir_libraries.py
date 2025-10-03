from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict
from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from ..db.database import get_db
from ..models.ir_codes import IRLibrary, IRCommand

router = APIRouter(prefix="/api/v1/ir-libraries", tags=["ir-libraries"])


class CreateGenericRequest(BaseModel):
    brand: str = Field(..., description="Brand name for the generic library (e.g., 'Generic Sony')")
    device_category: str = Field(default="TV", description="Device category")
    source_brand: str = Field(..., description="Source brand to analyze (e.g., 'Sony')")
    description: Optional[str] = Field(None, description="Custom description for the generic library")


class CreateGenericResponse(BaseModel):
    library_id: int
    brand: str
    name: str
    commands_created: int
    compatibility_scores_updated: int
    most_common_patterns: Dict[str, Any]


class CompatibilityScore(BaseModel):
    library_id: int
    model: str
    name: str
    score: int
    matching_commands: int
    total_commands: int
    compatibility_percentage: float


class IRLibrarySummary(BaseModel):
    id: int
    name: str
    brand: str
    device_category: str
    model: Optional[str]
    esp_native: bool
    hidden: bool
    source: str
    description: Optional[str]
    import_status: Optional[str]
    command_count: int
    protocols: List[str]
    updated_at: Optional[datetime]


class IRLibraryListResponse(BaseModel):
    items: List[IRLibrarySummary]
    total: int
    page: int
    page_size: int


class IRCommandSummary(BaseModel):
    id: int
    name: str
    protocol: str
    category: Optional[str]
    signal_data: Dict[str, Any]
    created_at: Optional[datetime]


class IRCommandListResponse(BaseModel):
    items: List[IRCommandSummary]
    total: int
    page: int
    page_size: int


class IRCommandLibrarySummary(BaseModel):
    id: int
    name: str
    brand: str
    device_category: str
    esp_native: bool


class IRCommandWithLibrarySummary(BaseModel):
    id: int
    name: str
    protocol: str
    category: Optional[str]
    signal_data: Dict[str, Any]
    created_at: Optional[datetime]
    library: IRCommandLibrarySummary


class IRCommandCatalogueResponse(BaseModel):
    items: List[IRCommandWithLibrarySummary]
    total: int
    page: int
    page_size: int


class IRLibraryFiltersResponse(BaseModel):
    brands: List[str]
    device_categories: List[str]
    protocols: List[str]


class IRLibraryVisibilityUpdate(BaseModel):
    hidden: bool


@router.get("", response_model=IRLibraryListResponse)
async def list_ir_libraries(
    page: int = 1,
    page_size: int = 25,
    search: Optional[str] = None,
    brand: Optional[str] = None,
    device_category: Optional[str] = None,
    protocol: Optional[str] = None,
    esp_native: Optional[bool] = None,
    include_hidden: bool = False,
    db: Session = Depends(get_db),
):
    if page < 1:
        page = 1
    if page_size < 5:
        page_size = 5
    if page_size > 200:
        page_size = 200

    query = db.query(IRLibrary)

    if search:
        pattern = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(IRLibrary.name).like(pattern),
                func.lower(IRLibrary.brand).like(pattern),
                func.lower(IRLibrary.device_category).like(pattern),
                func.lower(func.coalesce(IRLibrary.model, '')).like(pattern),
            )
        )

    if brand:
        query = query.filter(IRLibrary.brand == brand)

    if device_category:
        query = query.filter(IRLibrary.device_category == device_category)

    if esp_native is not None:
        query = query.filter(IRLibrary.esp_native == esp_native)

    if protocol:
        proto_pattern = f"%{protocol.lower()}%"
        protocol_subquery = (
            db.query(IRCommand.library_id)
            .filter(func.lower(IRCommand.protocol).like(proto_pattern))
            .distinct()
            .subquery()
        )
        query = query.filter(IRLibrary.id.in_(protocol_subquery))

    if not include_hidden:
        query = query.filter(IRLibrary.hidden.is_(False))

    total = query.count()
    libraries = (
        query.order_by(IRLibrary.brand.asc(), IRLibrary.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    library_ids = [library.id for library in libraries]
    command_counts: Dict[int, int] = {ident: 0 for ident in library_ids}
    protocols_map: Dict[int, set[str]] = {ident: set() for ident in library_ids}

    if library_ids:
        count_rows = (
            db.query(IRCommand.library_id, func.count(IRCommand.id))
            .filter(IRCommand.library_id.in_(library_ids))
            .group_by(IRCommand.library_id)
            .all()
        )
        for library_id, command_count in count_rows:
            command_counts[library_id] = command_count

        protocol_rows = (
            db.query(IRCommand.library_id, func.coalesce(IRCommand.protocol, ''))
            .filter(IRCommand.library_id.in_(library_ids))
            .distinct()
            .all()
        )
        for library_id, proto in protocol_rows:
            if proto:
                protocols_map[library_id].add(proto)

    items = [
        IRLibrarySummary(
            id=library.id,
            name=library.name,
            brand=library.brand,
            device_category=library.device_category,
            model=library.model,
            esp_native=bool(library.esp_native),
            hidden=bool(library.hidden),
            source=library.source_path,
            description=library.description,
            import_status=library.import_status,
            command_count=command_counts.get(library.id, 0),
            protocols=sorted(proto.lower() for proto in protocols_map.get(library.id, set()) if proto),
            updated_at=library.updated_at,
        )
        for library in libraries
    ]

    return IRLibraryListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/filters", response_model=IRLibraryFiltersResponse)
async def list_ir_library_filters(db: Session = Depends(get_db)):
    brands = [
        row[0]
        for row in db.query(IRLibrary.brand)
        .filter(IRLibrary.brand != '', IRLibrary.hidden.is_(False))
        .distinct()
        .order_by(IRLibrary.brand.asc())
        .all()
    ]
    device_categories = [
        row[0]
        for row in db.query(IRLibrary.device_category)
        .filter(IRLibrary.device_category != '', IRLibrary.hidden.is_(False))
        .distinct()
        .order_by(IRLibrary.device_category.asc())
        .all()
    ]
    protocols = [
        row[0]
        for row in db.query(func.coalesce(IRCommand.protocol, ''))
        .join(IRLibrary, IRLibrary.id == IRCommand.library_id)
        .filter(IRLibrary.hidden.is_(False))
        .distinct()
        .order_by(func.coalesce(IRCommand.protocol, '').asc())
        .all()
        if row[0]
    ]

    return IRLibraryFiltersResponse(
        brands=brands,
        device_categories=device_categories,
        protocols=[protocol.lower() for protocol in protocols if protocol],
    )


@router.get("/{library_id:int}/commands", response_model=IRCommandListResponse)
async def list_ir_library_commands(
    library_id: int,
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None,
    protocol: Optional[str] = None,
    db: Session = Depends(get_db),
):
    if page < 1:
        page = 1
    if page_size < 10:
        page_size = 10
    if page_size > 200:
        page_size = 200

    library = db.query(IRLibrary).filter(IRLibrary.id == library_id).first()
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")

    query = db.query(IRCommand).filter(IRCommand.library_id == library_id)

    if search:
        pattern = f"%{search.lower()}%"
        query = query.filter(func.lower(IRCommand.name).like(pattern))

    if protocol:
        proto_pattern = f"%{protocol.lower()}%"
        query = query.filter(func.lower(IRCommand.protocol).like(proto_pattern))

    total = query.count()
    commands = (
        query.order_by(IRCommand.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        IRCommandSummary(
            id=command.id,
            name=command.name,
            protocol=command.protocol or '',
            category=command.category,
            signal_data=command.signal_data or {},
            created_at=command.created_at,
        )
        for command in commands
    ]

    return IRCommandListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/{library_id:int}/visibility", response_model=IRLibrarySummary)
async def update_library_visibility(
    library_id: int,
    payload: IRLibraryVisibilityUpdate,
    db: Session = Depends(get_db),
):
    library = db.query(IRLibrary).filter(IRLibrary.id == library_id).first()
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")

    library.hidden = bool(payload.hidden)
    db.add(library)
    db.commit()
    db.refresh(library)

    command_count = db.query(IRCommand).filter(IRCommand.library_id == library.id).count()
    protocols = [
        row[0]
        for row in db.query(func.coalesce(IRCommand.protocol, ''))
        .filter(IRCommand.library_id == library.id)
        .distinct()
        .all()
        if row[0]
    ]

    return IRLibrarySummary(
        id=library.id,
        name=library.name,
        brand=library.brand,
        device_category=library.device_category,
        model=library.model,
        esp_native=bool(library.esp_native),
        hidden=bool(library.hidden),
        source=library.source_path,
        description=library.description,
        import_status=library.import_status,
        command_count=command_count,
        protocols=[protocol.lower() for protocol in protocols if protocol],
        updated_at=library.updated_at,
    )


@router.get("/commands", response_model=IRCommandCatalogueResponse)
async def list_ir_commands(
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None,
    brand: Optional[str] = None,
    device_category: Optional[str] = None,
    protocol: Optional[str] = None,
    esp_native: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    if page < 1:
        page = 1
    if page_size < 10:
        page_size = 10
    if page_size > 200:
        page_size = 200

    query = db.query(IRCommand, IRLibrary).join(IRLibrary, IRCommand.library_id == IRLibrary.id)
    query = query.filter(IRLibrary.hidden.is_(False))

    if search:
        pattern = f"%{search.lower()}%"
        query = query.filter(func.lower(IRCommand.name).like(pattern))

    if brand:
        query = query.filter(IRLibrary.brand == brand)

    if device_category:
        query = query.filter(IRLibrary.device_category == device_category)

    if protocol:
        proto_pattern = f"%{protocol.lower()}%"
        query = query.filter(func.lower(IRCommand.protocol).like(proto_pattern))

    if esp_native is not None:
        query = query.filter(IRLibrary.esp_native == esp_native)

    total = query.count()

    rows = (
        query.order_by(IRLibrary.brand.asc(), IRCommand.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        IRCommandWithLibrarySummary(
            id=command.id,
            name=command.name,
            protocol=command.protocol or '',
            category=command.category,
            signal_data=command.signal_data or {},
            created_at=command.created_at,
            library=IRCommandLibrarySummary(
                id=library.id,
                name=library.name,
                brand=library.brand,
                device_category=library.device_category,
                esp_native=bool(library.esp_native),
            ),
        )
        for command, library in rows
    ]

    return IRCommandCatalogueResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


def _calculate_command_compatibility(generic_commands: Dict[str, Dict], model_commands: List[IRCommand]) -> Dict[str, Any]:
    """Calculate compatibility between generic commands and a specific model's commands"""

    # Command name mapping (same as in _analyze_brand_patterns)
    command_map = {
        # Power variations
        'Power': 'power', 'power_on': 'power', 'power_off': 'power', 'Power on': 'power', 'Power off': 'power',
        'Power_on': 'power', 'Power_off': 'power', 'Power_off_only': 'power',

        # Mute variations
        'Mute': 'mute',

        # Volume variations
        'vol_up': 'volume_up', 'vol_dn': 'volume_down', 'Vol_up': 'volume_up', 'Vol_dn': 'volume_down',
        'VOL_UP': 'volume_up', 'VOL_DWN': 'volume_down', 'VOL +': 'volume_up', 'VOL -': 'volume_down',
        'Volume up': 'volume_up', 'Volume down': 'volume_down', 'Volup': 'volume_up', 'Voldown': 'volume_down',
        'Right/vol+': 'volume_up', 'Left/vol-': 'volume_down',

        # Channel variations
        'ch_next': 'channel_up', 'ch_prev': 'channel_down', 'Ch_next': 'channel_up', 'Ch_prev': 'channel_down',
        'CH_UP': 'channel_up', 'CH_DWN': 'channel_down', 'Channel up': 'channel_up', 'Channel down': 'channel_down',
        'Up/ch+': 'channel_up', 'Down/ch-': 'channel_down',

        # Number variations (direct digits)
        '0': 'number_0', '1': 'number_1', '2': 'number_2', '3': 'number_3', '4': 'number_4',
        '5': 'number_5', '6': 'number_6', '7': 'number_7', '8': 'number_8', '9': 'number_9'
    }

    # Build model command lookup with normalized names
    model_lookup = {}
    for cmd in model_commands:
        try:
            signal_data = cmd.signal_data if cmd.signal_data else {}
            protocol = (cmd.protocol or '').lower()

            # Normalize command name (try direct mapping first, then lowercase)
            cmd_name = command_map.get(cmd.name, cmd.name.lower())
            cmd_name = command_map.get(cmd_name, cmd_name)

            # Create signature for comparison
            if protocol.startswith('samsung') and 'address' in signal_data and 'command' in signal_data:
                signature = f"{signal_data['address']}|{signal_data['command']}"
            elif protocol.startswith('nec') and 'address' in signal_data and 'command' in signal_data:
                signature = f"{signal_data['address']}|{signal_data['command']}"
            elif 'data' in signal_data:
                signature = signal_data['data']
            else:
                continue

            model_lookup[cmd_name] = {
                'signature': signature,
                'protocol': protocol
            }
        except:
            continue

    # Compare with generic commands
    matches = 0
    total_generic = len(generic_commands)
    matching_commands = []

    for cmd_name, generic_pattern in generic_commands.items():
        if cmd_name in model_lookup:
            model_cmd = model_lookup[cmd_name]
            generic_sig = generic_pattern['signature']

            if model_cmd['signature'] == generic_sig:
                matches += 1
                matching_commands.append(cmd_name)

    compatibility_percentage = (matches / total_generic * 100) if total_generic > 0 else 0

    # Convert percentage to 0-9 score
    if compatibility_percentage >= 95:
        score = 9
    elif compatibility_percentage >= 85:
        score = 8
    elif compatibility_percentage >= 75:
        score = 7
    elif compatibility_percentage >= 65:
        score = 6
    elif compatibility_percentage >= 55:
        score = 5
    elif compatibility_percentage >= 45:
        score = 4
    elif compatibility_percentage >= 35:
        score = 3
    elif compatibility_percentage >= 25:
        score = 2
    elif compatibility_percentage >= 15:
        score = 1
    else:
        score = 0

    return {
        'score': score,
        'matching_commands': matches,
        'total_commands': len(model_commands),
        'compatibility_percentage': compatibility_percentage,
        'matching_command_names': matching_commands
    }


def _analyze_brand_patterns(db: Session, source_brand: str, device_category: str) -> Dict[str, Any]:
    """Analyze all models of a brand to find most common command patterns"""

    # Get all libraries for this brand (excluding any generic ones we created)
    libraries = db.query(IRLibrary).filter(
        IRLibrary.brand == source_brand,
        IRLibrary.device_category == device_category,
        IRLibrary.esp_native == False,
        ~IRLibrary.brand.like('Generic %')  # Exclude our generic creations
    ).all()

    if not libraries:
        raise HTTPException(status_code=404, detail=f"No {source_brand} {device_category} libraries found")

    # Define basic commands we care about
    basic_commands = ['power', 'mute', 'volume_up', 'volume_down', 'channel_up', 'channel_down',
                     'number_0', 'number_1', 'number_2', 'number_3', 'number_4', 'number_5',
                     'number_6', 'number_7', 'number_8', 'number_9']

    # Normalize command names (handle both cases and Flipper-IRDB variations)
    command_map = {
        # Power variations
        'Power': 'power', 'power_on': 'power', 'power_off': 'power', 'Power on': 'power', 'Power off': 'power',
        'Power_on': 'power', 'Power_off': 'power', 'Power_off_only': 'power',

        # Mute variations
        'Mute': 'mute',

        # Volume variations
        'vol_up': 'volume_up', 'vol_dn': 'volume_down', 'Vol_up': 'volume_up', 'Vol_dn': 'volume_down',
        'VOL_UP': 'volume_up', 'VOL_DWN': 'volume_down', 'VOL +': 'volume_up', 'VOL -': 'volume_down',
        'Volume up': 'volume_up', 'Volume down': 'volume_down', 'Volup': 'volume_up', 'Voldown': 'volume_down',
        'Right/vol+': 'volume_up', 'Left/vol-': 'volume_down',

        # Channel variations
        'ch_next': 'channel_up', 'ch_prev': 'channel_down', 'Ch_next': 'channel_up', 'Ch_prev': 'channel_down',
        'CH_UP': 'channel_up', 'CH_DWN': 'channel_down', 'Channel up': 'channel_up', 'Channel down': 'channel_down',
        'Up/ch+': 'channel_up', 'Down/ch-': 'channel_down',

        # Number variations (direct digits)
        '0': 'number_0', '1': 'number_1', '2': 'number_2', '3': 'number_3', '4': 'number_4',
        '5': 'number_5', '6': 'number_6', '7': 'number_7', '8': 'number_8', '9': 'number_9'
    }

    # Track patterns across all models
    command_patterns = defaultdict(Counter)
    protocol_usage = Counter()
    debug_info = {"total_commands": 0, "processed_commands": 0, "skipped_reasons": Counter()}

    for library in libraries:
        commands = db.query(IRCommand).filter(IRCommand.library_id == library.id).all()
        debug_info["total_commands"] += len(commands)

        for command in commands:
            # Normalize command name (try direct mapping first, then lowercase)
            cmd_name = command_map.get(command.name, command.name.lower())
            cmd_name = command_map.get(cmd_name, cmd_name)

            if cmd_name not in basic_commands:
                debug_info["skipped_reasons"]["not_basic_command"] += 1
                continue

            try:
                signal_data = command.signal_data if command.signal_data else {}
                protocol = (command.protocol or '').lower()

                # Debug logging
                if not signal_data:
                    debug_info["skipped_reasons"]["no_signal_data"] += 1
                    continue

                # Only process commands with recognizable formats (skip raw/unknown)
                signature = None
                if 'address' in signal_data and 'command' in signal_data:
                    # Standard address/command format (Samsung32, NEC, etc.)
                    signature = f"{signal_data['address']}|{signal_data['command']}"
                    protocol_usage[protocol] += 1
                    debug_info["processed_commands"] += 1
                elif 'data' in signal_data and 'type' not in signal_data:
                    # Direct data format (not raw timing data)
                    signature = signal_data['data']
                    protocol_usage[protocol] += 1
                    debug_info["processed_commands"] += 1
                else:
                    debug_info["skipped_reasons"]["unrecognized_format"] += 1
                    # Debug: log what we're skipping
                    if 'type' in signal_data:
                        debug_info["skipped_reasons"]["has_type_field"] += 1
                    if 'data' not in signal_data and 'address' not in signal_data:
                        debug_info["skipped_reasons"]["no_data_or_address"] += 1
                    continue

                command_patterns[cmd_name][signature] += 1
            except Exception as e:
                debug_info["skipped_reasons"]["json_parse_error"] += 1
                # Store the first few parse errors for debugging
                if "parse_errors" not in debug_info:
                    debug_info["parse_errors"] = []
                if len(debug_info["parse_errors"]) < 5:
                    debug_info["parse_errors"].append({
                        "command_name": command.name,
                        "signal_data": str(command.signal_data)[:200],  # First 200 chars
                        "error": str(e)
                    })
                continue

    # Find most common pattern for each command
    most_common_patterns = {}
    for cmd_name in basic_commands:
        if cmd_name in command_patterns and command_patterns[cmd_name]:
            top_pattern = command_patterns[cmd_name].most_common(1)[0]
            signature = top_pattern[0]
            count = top_pattern[1]
            total_models = sum(command_patterns[cmd_name].values())

            # Parse signature back to address/command or data
            if '|' in signature:
                address, command = signature.split('|')
                most_common_patterns[cmd_name] = {
                    'signature': signature,
                    'address': address,
                    'command': command,
                    'models_count': count,
                    'total_models': total_models,
                    'percentage': (count / total_models * 100) if total_models > 0 else 0
                }
            else:
                most_common_patterns[cmd_name] = {
                    'signature': signature,
                    'data': signature,
                    'models_count': count,
                    'total_models': total_models,
                    'percentage': (count / total_models * 100) if total_models > 0 else 0
                }

    # Determine most common protocol
    most_common_protocol = protocol_usage.most_common(1)[0][0] if protocol_usage else 'unknown'

    return {
        'patterns': most_common_patterns,
        'protocol': most_common_protocol,
        'total_models_analyzed': len(libraries),
        'protocol_usage': dict(protocol_usage),
        'debug_info': debug_info
    }


@router.post("/create-generic", response_model=CreateGenericResponse)
async def create_generic_library(request: CreateGenericRequest, db: Session = Depends(get_db)):
    """Create a generic IR library based on most common patterns from existing models"""

    # Analyze brand patterns
    analysis = _analyze_brand_patterns(db, request.source_brand, request.device_category)
    patterns = analysis['patterns']
    protocol = analysis['protocol']

    if not patterns:
        # Debug information from analysis
        debug_details = analysis.get('debug_info', {})
        debug_info = {
            "models_analyzed": analysis.get('total_models_analyzed', 0),
            "total_commands": debug_details.get('total_commands', 0),
            "processed_commands": debug_details.get('processed_commands', 0),
            "skipped_reasons": dict(debug_details.get('skipped_reasons', {})),
            "protocol_usage": analysis.get('protocol_usage', {}),
            "parse_errors": debug_details.get('parse_errors', [])
        }
        raise HTTPException(status_code=400, detail=f"No common patterns found for {request.source_brand} {request.device_category}. Debug: {debug_info}")

    # Create the generic library
    description = request.description or f"Most common {request.source_brand} {request.device_category} IR codes (auto-generated from {analysis['total_models_analyzed']} models)"

    generic_library = IRLibrary(
        source="generic_analysis",
        source_path=f"generic/{request.source_brand.lower().replace(' ', '_')}_{request.device_category.lower()}",
        device_category=request.device_category,
        brand=request.brand,
        model=request.device_category,
        name=f"{request.brand} {request.device_category}",
        description=description,
        version="1.0.0",
        file_hash=f"generic_{request.brand.lower().replace(' ', '_')}_{request.device_category.lower()}",
        last_updated=datetime.now(),
        import_status="imported",
        esp_native=False,
        generic_compatibility=None,  # Generic entries don't have compatibility scores
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    db.add(generic_library)
    db.flush()  # Get the ID

    # Create commands for the generic library
    commands_created = 0
    for cmd_name, pattern in patterns.items():
        # Determine display name and category
        display_name = cmd_name.replace('_', ' ').title()
        if cmd_name.startswith('number_'):
            display_name = cmd_name.split('_')[1]
            category = 'number'
        elif cmd_name in ['volume_up', 'volume_down', 'mute']:
            category = 'volume'
        elif cmd_name in ['channel_up', 'channel_down']:
            category = 'navigation'
        else:
            category = 'power'

        # Create signal_data
        if 'address' in pattern and 'command' in pattern:
            signal_data = {
                'address': pattern['address'],
                'command': pattern['command']
            }
        else:
            signal_data = {
                'data': pattern['data']
            }

        command = IRCommand(
            library_id=generic_library.id,
            name=cmd_name,
            display_name=display_name,
            category=category,
            protocol=protocol.title(),  # Samsung32, NEC, etc.
            signal_data=signal_data,  # Let SQLAlchemy JSON column handle serialization
            usage_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        db.add(command)
        commands_created += 1

    # Calculate compatibility scores for all existing models of this brand
    existing_libraries = db.query(IRLibrary).filter(
        IRLibrary.brand == request.source_brand,
        IRLibrary.device_category == request.device_category,
        IRLibrary.esp_native == False
    ).all()

    scores_updated = 0
    for library in existing_libraries:
        library_commands = db.query(IRCommand).filter(IRCommand.library_id == library.id).all()
        compatibility = _calculate_command_compatibility(patterns, library_commands)

        library.generic_compatibility = compatibility['score']
        scores_updated += 1

    db.commit()

    return CreateGenericResponse(
        library_id=generic_library.id,
        brand=generic_library.brand,
        name=generic_library.name,
        commands_created=commands_created,
        compatibility_scores_updated=scores_updated,
        most_common_patterns=analysis
    )


@router.get("/compatibility-scores/{brand}")
async def get_compatibility_scores(brand: str, db: Session = Depends(get_db)) -> List[CompatibilityScore]:
    """Get compatibility scores for all models of a specific brand"""

    libraries = db.query(IRLibrary).filter(
        IRLibrary.brand == brand,
        IRLibrary.generic_compatibility.isnot(None)
    ).order_by(IRLibrary.generic_compatibility.desc()).all()

    scores = []
    for library in libraries:
        # Get command count for this library
        command_count = db.query(IRCommand).filter(IRCommand.library_id == library.id).count()

        scores.append(CompatibilityScore(
            library_id=library.id,
            model=library.model or "Unknown",
            name=library.name,
            score=library.generic_compatibility,
            matching_commands=0,  # Could calculate this if needed
            total_commands=command_count,
            compatibility_percentage=library.generic_compatibility * 10 + 5  # Approximate
        ))

    return scores
