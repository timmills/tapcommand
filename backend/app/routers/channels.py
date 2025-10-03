from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel

from ..db.database import get_db
from ..models.device import Channel

router = APIRouter()


class ChannelResponse(BaseModel):
    id: int
    platform: str
    broadcaster_network: str
    channel_name: str
    lcn: Optional[str] = None
    foxtel_number: Optional[str] = None
    broadcast_hours: Optional[str] = None
    format: Optional[str] = None
    programming_content: Optional[str] = None
    availability: Optional[str] = None
    logo_url: Optional[str] = None
    notes: Optional[str] = None
    internal: bool = False
    disabled: bool = True
    local_logo_path: Optional[str] = None

    class Config:
        from_attributes = True


class ChannelUpdateRequest(BaseModel):
    disabled: Optional[bool] = None
    internal: Optional[bool] = None


class InHouseChannelCreate(BaseModel):
    channel_name: str
    channel_number: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    disabled: bool = False


class InHouseChannelUpdate(BaseModel):
    channel_name: Optional[str] = None
    channel_number: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    disabled: Optional[bool] = None


class BulkChannelUpdateRequest(BaseModel):
    """Request model for bulk channel operations with JSON body"""
    channel_ids: List[int]
    update_data: ChannelUpdateRequest


class AreaChannelUpdateRequest(BaseModel):
    """Request model for area-based channel updates"""
    area_name: str
    update_data: ChannelUpdateRequest


class CityChannelUpdateRequest(BaseModel):
    """Request model for city-based channel updates"""
    city_name: str
    update_data: ChannelUpdateRequest


class ChannelStats(BaseModel):
    total_channels: int
    enabled_channels: int
    disabled_channels: int
    platforms: List[str]
    broadcasters: List[str]


class AreaInfo(BaseModel):
    name: str
    full_name: str
    type: str  # "nationwide", "national", "metro", "regional"
    state: Optional[str] = None
    cities: List[str] = []
    channel_count: int


class AreasResponse(BaseModel):
    areas: List[AreaInfo]


@router.get("/", response_model=List[ChannelResponse])
def get_channels(
    platform: Optional[str] = None,
    broadcaster: Optional[str] = None,
    enabled_only: bool = False,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get channels with optional filtering"""
    query = db.query(Channel)

    # Apply filters
    if platform:
        query = query.filter(Channel.platform == platform)

    if broadcaster:
        query = query.filter(Channel.broadcaster_network == broadcaster)

    if enabled_only:
        query = query.filter(Channel.disabled == False)

    if search:
        query = query.filter(
            Channel.channel_name.ilike(f"%{search}%") |
            Channel.broadcaster_network.ilike(f"%{search}%")
        )

    # Order by platform, then broadcaster, then channel name
    query = query.order_by(
        Channel.platform,
        Channel.broadcaster_network,
        Channel.channel_name
    )

    # Apply pagination
    channels = query.offset(offset).limit(limit).all()

    return channels


@router.get("/stats", response_model=ChannelStats)
def get_channel_stats(db: Session = Depends(get_db)):
    """Get channel statistics"""
    total_channels = db.query(func.count(Channel.id)).scalar()
    enabled_channels = db.query(func.count(Channel.id)).filter(Channel.disabled == False).scalar()
    disabled_channels = total_channels - enabled_channels

    # Get distinct platforms
    platforms = db.query(Channel.platform).distinct().all()
    platforms = [p[0] for p in platforms if p[0]]

    # Get distinct broadcasters
    broadcasters = db.query(Channel.broadcaster_network).distinct().all()
    broadcasters = [b[0] for b in broadcasters if b[0]]

    return ChannelStats(
        total_channels=total_channels,
        enabled_channels=enabled_channels,
        disabled_channels=disabled_channels,
        platforms=sorted(platforms),
        broadcasters=sorted(broadcasters)
    )


@router.patch("/bulk-update")
def bulk_update_channels(
    request: BulkChannelUpdateRequest,
    db: Session = Depends(get_db)
):
    """Bulk update multiple channels with JSON body"""
    channels = db.query(Channel).filter(Channel.id.in_(request.channel_ids)).all()

    if not channels:
        raise HTTPException(status_code=404, detail="No channels found")

    updated_count = 0
    for channel in channels:
        if request.update_data.disabled is not None:
            channel.disabled = request.update_data.disabled
            updated_count += 1

        if request.update_data.internal is not None:
            channel.internal = request.update_data.internal
            updated_count += 1

    db.commit()

    return {
        "message": f"Updated {len(channels)} channels",
        "updated_count": updated_count,
        "channel_ids": request.channel_ids
    }


@router.get("/{channel_id}", response_model=ChannelResponse)
def get_channel(channel_id: int, db: Session = Depends(get_db)):
    """Get a specific channel by ID"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@router.patch("/{channel_id}")
def update_channel(
    channel_id: int,
    update_data: ChannelUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update a channel's settings"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Update fields that were provided
    if update_data.disabled is not None:
        channel.disabled = update_data.disabled

    if update_data.internal is not None:
        channel.internal = update_data.internal

    db.commit()
    db.refresh(channel)

    return {"message": "Channel updated successfully", "channel": channel}


@router.patch("/platform/{platform}")
def update_platform_channels(
    platform: str,
    update_data: ChannelUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update all channels for a specific platform"""
    channels = db.query(Channel).filter(Channel.platform == platform).all()

    if not channels:
        raise HTTPException(status_code=404, detail=f"No channels found for platform: {platform}")

    for channel in channels:
        if update_data.disabled is not None:
            channel.disabled = update_data.disabled

        if update_data.internal is not None:
            channel.internal = update_data.internal

    db.commit()

    return {
        "message": f"Updated {len(channels)} channels for platform {platform}",
        "platform": platform,
        "updated_count": len(channels)
    }


def parse_availability_to_areas(availability: str) -> tuple:
    """Parse availability string to extract area info and cities"""
    if not availability:
        return None, []

    if availability == "Nationwide":
        return "Nationwide", []

    if availability == "National (Foxtel)":
        return "National (Foxtel)", []

    # Handle regional/metro format: "Regional NSW – Far South Coast: Batemans Bay, Moruya, Narooma..."
    if ":" in availability:
        area_part, cities_part = availability.split(":", 1)
        cities = [city.strip() for city in cities_part.split(",") if city.strip()]
        return area_part.strip(), cities

    return availability.strip(), []


@router.get("/areas", response_model=AreasResponse)
def get_areas(db: Session = Depends(get_db)):
    """Get all available areas with channel counts"""
    # Get all distinct availability values
    areas_data = db.query(Channel.availability, func.count(Channel.id)).filter(
        Channel.availability.isnot(None),
        Channel.availability != ""
    ).group_by(Channel.availability).all()

    areas = []

    for availability, count in areas_data:
        area_name, cities = parse_availability_to_areas(availability)

        if not area_name:
            continue

        # Determine area type and state
        area_type = "other"
        state = None

        if area_name == "Nationwide":
            area_type = "nationwide"
        elif area_name == "National (Foxtel)":
            area_type = "national"
        elif area_name.startswith("Metro NSW"):
            area_type = "metro"
            state = "NSW"
            area_name = area_name.replace("Metro NSW – ", "")
        elif area_name.startswith("Metro VIC"):
            area_type = "metro"
            state = "VIC"
            area_name = area_name.replace("Metro VIC – ", "")
        elif area_name.startswith("Regional NSW"):
            area_type = "regional"
            state = "NSW"
            area_name = area_name.replace("Regional NSW – ", "")
        elif area_name.startswith("Regional VIC"):
            area_type = "regional"
            state = "VIC"
            area_name = area_name.replace("Regional VIC – ", "")

        areas.append(AreaInfo(
            name=area_name,
            full_name=availability,
            type=area_type,
            state=state,
            cities=cities,
            channel_count=count
        ))

    # Sort areas by type and name
    areas.sort(key=lambda x: (x.type, x.state or "", x.name))

    return AreasResponse(areas=areas)


@router.patch("/area/{area_name}")
def update_area_channels(
    area_name: str,
    update_data: ChannelUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update all channels for a specific area"""
    # Find channels matching the area
    channels = db.query(Channel).filter(
        Channel.availability.like(f"%{area_name}%")
    ).all()

    if not channels:
        raise HTTPException(status_code=404, detail=f"No channels found for area: {area_name}")

    for channel in channels:
        if update_data.disabled is not None:
            channel.disabled = update_data.disabled

        if update_data.internal is not None:
            channel.internal = update_data.internal

    db.commit()

    return {
        "message": f"Updated {len(channels)} channels for area {area_name}",
        "area": area_name,
        "updated_count": len(channels)
    }


@router.patch("/city/{city_name}")
def update_city_channels(
    city_name: str,
    update_data: ChannelUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update all channels available in a specific city"""
    # Find channels that include this city in their availability
    channels = db.query(Channel).filter(
        Channel.availability.like(f"%{city_name}%")
    ).all()

    if not channels:
        raise HTTPException(status_code=404, detail=f"No channels found for city: {city_name}")

    for channel in channels:
        if update_data.disabled is not None:
            channel.disabled = update_data.disabled

        if update_data.internal is not None:
            channel.internal = update_data.internal

    db.commit()

    return {
        "message": f"Updated {len(channels)} channels for city {city_name}",
        "city": city_name,
        "updated_count": len(channels)
    }


# Alternative POST endpoints with JSON bodies for better frontend integration

@router.post("/bulk-update")
def bulk_update_channels_alt(
    request: BulkChannelUpdateRequest,
    db: Session = Depends(get_db)
):
    """Alternative POST endpoint for bulk channel updates with JSON body"""
    return bulk_update_channels(request, db)


@router.post("/area-update")
def update_area_channels_by_body(
    request: AreaChannelUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update all channels for a specific area using JSON body"""
    # Find channels matching the area
    channels = db.query(Channel).filter(
        Channel.availability.like(f"%{request.area_name}%")
    ).all()

    if not channels:
        raise HTTPException(status_code=404, detail=f"No channels found for area: {request.area_name}")

    updated_count = 0
    for channel in channels:
        if request.update_data.disabled is not None:
            channel.disabled = request.update_data.disabled
            updated_count += 1

        if request.update_data.internal is not None:
            channel.internal = request.update_data.internal
            updated_count += 1

    db.commit()

    return {
        "message": f"Updated {len(channels)} channels for area {request.area_name}",
        "area": request.area_name,
        "updated_count": updated_count,
        "affected_channels": len(channels)
    }


@router.post("/city-update")
def update_city_channels_by_body(
    request: CityChannelUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update all channels for a specific city using JSON body"""
    # Find channels that include this city in their availability
    channels = db.query(Channel).filter(
        Channel.availability.like(f"%{request.city_name}%")
    ).all()

    if not channels:
        raise HTTPException(status_code=404, detail=f"No channels found for city: {request.city_name}")

    updated_count = 0
    for channel in channels:
        if request.update_data.disabled is not None:
            channel.disabled = request.update_data.disabled
            updated_count += 1

        if request.update_data.internal is not None:
            channel.internal = request.update_data.internal
            updated_count += 1

    db.commit()

    return {
        "message": f"Updated {len(channels)} channels for city {request.city_name}",
        "city": request.city_name,
        "updated_count": updated_count,
        "affected_channels": len(channels)
    }


@router.get("/inhouse", response_model=List[ChannelResponse])
def get_inhouse_channels(db: Session = Depends(get_db)):
    """Get all InHouse channels"""
    channels = db.query(Channel).filter(Channel.internal == True).order_by(Channel.channel_name).all()
    return channels


@router.post("/inhouse", response_model=ChannelResponse)
def create_inhouse_channel(
    channel_data: InHouseChannelCreate,
    db: Session = Depends(get_db)
):
    """Create a new InHouse channel"""
    channel = Channel(
        platform="InHouse",
        broadcaster_network="InHouse",
        channel_name=channel_data.channel_name,
        lcn=channel_data.channel_number,
        programming_content=channel_data.description,
        logo_url=channel_data.logo_url,
        disabled=channel_data.disabled,
        internal=True,
        availability="Venue Only"
    )

    db.add(channel)
    db.commit()
    db.refresh(channel)

    return channel


@router.put("/inhouse/{channel_id}", response_model=ChannelResponse)
def update_inhouse_channel(
    channel_id: int,
    channel_data: InHouseChannelUpdate,
    db: Session = Depends(get_db)
):
    """Update an InHouse channel"""
    channel = db.query(Channel).filter(
        Channel.id == channel_id,
        Channel.internal == True
    ).first()

    if not channel:
        raise HTTPException(status_code=404, detail="InHouse channel not found")

    # Update provided fields
    if channel_data.channel_name is not None:
        channel.channel_name = channel_data.channel_name

    if channel_data.channel_number is not None:
        channel.lcn = channel_data.channel_number

    if channel_data.description is not None:
        channel.programming_content = channel_data.description

    if channel_data.logo_url is not None:
        channel.logo_url = channel_data.logo_url

    if channel_data.disabled is not None:
        channel.disabled = channel_data.disabled

    db.commit()
    db.refresh(channel)

    return channel


@router.delete("/inhouse/{channel_id}")
def delete_inhouse_channel(
    channel_id: int,
    db: Session = Depends(get_db)
):
    """Delete an InHouse channel"""
    channel = db.query(Channel).filter(
        Channel.id == channel_id,
        Channel.internal == True
    ).first()

    if not channel:
        raise HTTPException(status_code=404, detail="InHouse channel not found")

    db.delete(channel)
    db.commit()

    return {"message": "InHouse channel deleted successfully", "channel_id": channel_id}