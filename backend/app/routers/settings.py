import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Any, Dict, Tuple
from sqlalchemy import func, case
from pydantic import BaseModel
from datetime import datetime

from ..db.database import get_db
from ..models.device_management import DeviceTag, IRPort
from ..models.device import Channel
from ..models.settings import ApplicationSetting
from ..services.settings_service import settings_service

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

logger = logging.getLogger(__name__)

_CHANNEL_LOCATION_SETTING_KEY = "channel_preferred_availability"

class ApplicationSettingRequest(BaseModel):
    key: str
    value: Any
    description: Optional[str] = None
    setting_type: str = "string"  # string, boolean, json, integer
    is_public: bool = False


class ApplicationSettingResponse(BaseModel):
    key: str
    value: Any
    description: Optional[str]
    setting_type: str
    is_public: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeviceTagRequest(BaseModel):
    name: str
    color: Optional[str] = None
    description: Optional[str] = None


class DeviceTagResponse(BaseModel):
    id: int
    name: str
    color: Optional[str]
    description: Optional[str]
    usage_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChannelLocationResponse(BaseModel):
    availability: str
    display_name: str
    total_channels: int
    enabled_channels: int


class ChannelRecordResponse(BaseModel):
    id: int
    platform: str
    broadcaster_network: Optional[str]
    channel_name: str
    lcn: Optional[str]
    foxtel_number: Optional[str]
    availability: Optional[str]
    disabled: bool
    is_recommended: bool = False


class ChannelGroupsResponse(BaseModel):
    availability: Optional[str]
    recommended: List[ChannelRecordResponse]
    other_fta: List[ChannelRecordResponse]
    foxtel: List[ChannelRecordResponse]
    inhouse: List[ChannelRecordResponse]


class ChannelVisibilityUpdateRequest(BaseModel):
    enable_ids: List[int] = []
    disable_ids: List[int] = []


class ChannelLocationListResponse(BaseModel):
    selected: Optional[str]
    locations: List[ChannelLocationResponse]


class ChannelLocationSelectRequest(BaseModel):
    availability: str


@router.get("/tags", response_model=List[DeviceTagResponse])
async def get_device_tags(db: Session = Depends(get_db)):
    """Get all device tags"""
    return db.query(DeviceTag).order_by(DeviceTag.name).all()


@router.post("/tags", response_model=DeviceTagResponse)
async def create_device_tag(tag_request: DeviceTagRequest, db: Session = Depends(get_db)):
    """Create a new device tag"""

    # Check if tag name already exists
    existing = db.query(DeviceTag).filter(DeviceTag.name == tag_request.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tag name already exists")

    # Create new tag
    tag = DeviceTag(
        name=tag_request.name.strip(),
        color=tag_request.color,
        description=tag_request.description,
        usage_count=0
    )

    db.add(tag)
    db.commit()
    db.refresh(tag)

    return tag


@router.put("/tags/{tag_id}", response_model=DeviceTagResponse)
async def update_device_tag(
    tag_id: int,
    tag_request: DeviceTagRequest,
    db: Session = Depends(get_db)
):
    """Update an existing device tag"""

    tag = db.query(DeviceTag).filter(DeviceTag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    # Check if new name conflicts with existing tag (if name is being changed)
    if tag_request.name != tag.name:
        existing = db.query(DeviceTag).filter(
            DeviceTag.name == tag_request.name,
            DeviceTag.id != tag_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Tag name already exists")

    # Update tag
    tag.name = tag_request.name.strip()
    tag.color = tag_request.color
    tag.description = tag_request.description

    db.commit()
    db.refresh(tag)

    return tag


@router.delete("/tags/{tag_id}")
async def delete_device_tag(tag_id: int, db: Session = Depends(get_db)):
    """Delete a device tag and remove it from all devices"""

    tag = db.query(DeviceTag).filter(DeviceTag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    # Remove this tag from all IR ports that use it
    ports_with_tag = db.query(IRPort).filter(IRPort.tag_ids.isnot(None)).all()

    for port in ports_with_tag:
        if port.tag_ids and tag_id in port.tag_ids:
            port.tag_ids = [tid for tid in port.tag_ids if tid != tag_id]
            if not port.tag_ids:  # If no tags left, set to None
                port.tag_ids = None

    # Delete the tag
    db.delete(tag)
    db.commit()

    return {"message": f"Tag '{tag.name}' deleted successfully"}


@router.post("/tags/refresh-usage-counts")
async def refresh_tag_usage_counts(db: Session = Depends(get_db)):
    """Refresh usage counts for all tags"""

    tags = db.query(DeviceTag).all()

    for tag in tags:
        # Count how many IR ports use this tag
        count = db.query(IRPort).filter(
            IRPort.tag_ids.isnot(None),
            IRPort.tag_ids.contains([tag.id])
        ).count()

        tag.usage_count = count

    db.commit()

    return {"message": "Tag usage counts refreshed"}


# ---------------------------------------------------------------------------
# Channel visibility & locations
# ---------------------------------------------------------------------------


def _get_channel_location_rows(db: Session) -> List[Tuple[str, int, int]]:
    rows = (
        db.query(
            Channel.availability,
            func.count(Channel.id),
            func.sum(case((Channel.disabled == False, 1), else_=0)),  # noqa: E712
        )
        .filter(
            Channel.platform == "FTA",
            Channel.availability.isnot(None),
            Channel.availability != "",
        )
        .group_by(Channel.availability)
        .order_by(Channel.availability)
        .all()
    )
    return [
        (
            availability,
            int(total or 0),
            int(enabled or 0),
        )
        for availability, total, enabled in rows
    ]


def _resolve_selected_availability(db: Session, available_locations: List[Tuple[str, int, int]]) -> Optional[str]:
    configured = settings_service.get_setting(_CHANNEL_LOCATION_SETTING_KEY)
    locations = [loc for loc, *_ in available_locations]

    if configured and configured in locations:
        return configured

    return locations[0] if locations else None


def _channel_to_response(channel: Channel, recommended: bool = False) -> ChannelRecordResponse:
    return ChannelRecordResponse(
        id=channel.id,
        platform=channel.platform,
        broadcaster_network=channel.broadcaster_network,
        channel_name=channel.channel_name,
        lcn=channel.lcn,
        foxtel_number=channel.foxtel_number,
        availability=channel.availability,
        disabled=bool(channel.disabled),
        is_recommended=recommended,
    )


@router.get("/channel-locations", response_model=ChannelLocationListResponse)
async def get_channel_locations(db: Session = Depends(get_db)):
    rows = _get_channel_location_rows(db)
    selected = _resolve_selected_availability(db, rows)

    locations = [
        ChannelLocationResponse(
            availability=availability,
            display_name=availability,
            total_channels=total,
            enabled_channels=enabled,
        )
        for availability, total, enabled in rows
    ]

    return ChannelLocationListResponse(selected=selected, locations=locations)


@router.post("/channel-locations/select", response_model=ChannelLocationListResponse)
async def select_channel_location(
    payload: ChannelLocationSelectRequest,
    db: Session = Depends(get_db)
):
    rows = _get_channel_location_rows(db)
    availability_values = {loc for loc, *_ in rows}

    if payload.availability not in availability_values:
        raise HTTPException(status_code=404, detail="Availability not recognised")

    settings_service.set_setting(
        _CHANNEL_LOCATION_SETTING_KEY,
        payload.availability,
        description="Preferred broadcast availability for channel visibility",
        setting_type="string",
        is_public=False,
    )

    locations = [
        ChannelLocationResponse(
            availability=availability,
            display_name=availability,
            total_channels=total,
            enabled_channels=enabled,
        )
        for availability, total, enabled in rows
    ]

    return ChannelLocationListResponse(selected=payload.availability, locations=locations)


@router.get("/channels", response_model=ChannelGroupsResponse)
async def get_channels_for_location(
    availability: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    rows = _get_channel_location_rows(db)
    selected = availability or _resolve_selected_availability(db, rows)

    if availability and availability not in {loc for loc, *_ in rows}:
        raise HTTPException(status_code=404, detail="Availability not recognised")

    recommended_channels: List[Channel] = []
    if selected:
        recommended_channels = (
            db.query(Channel)
            .filter(Channel.platform == "FTA", Channel.availability == selected)
            .order_by(Channel.channel_name)
            .all()
        )
    recommended_ids = {channel.id for channel in recommended_channels}

    other_fta_query = db.query(Channel).filter(Channel.platform == "FTA")
    if recommended_ids:
        other_fta_query = other_fta_query.filter(Channel.id.notin_(recommended_ids))
    other_fta = other_fta_query.order_by(Channel.channel_name).all()

    foxtel_channels = (
        db.query(Channel)
        .filter(Channel.platform == "Foxtel")
        .order_by(Channel.foxtel_number, Channel.channel_name)
        .all()
    )

    inhouse_channels = (
        db.query(Channel)
        .filter((Channel.platform == "InHouse") | (Channel.internal == True))  # noqa: E712
        .order_by(Channel.channel_name)
        .all()
    )

    return ChannelGroupsResponse(
        availability=selected,
        recommended=[_channel_to_response(ch, recommended=True) for ch in recommended_channels],
        other_fta=[_channel_to_response(ch) for ch in other_fta],
        foxtel=[_channel_to_response(ch) for ch in foxtel_channels],
        inhouse=[_channel_to_response(ch) for ch in inhouse_channels],
    )


@router.patch("/channels")
async def update_channel_visibility(
    payload: ChannelVisibilityUpdateRequest,
    db: Session = Depends(get_db)
):
    enable_ids = set(payload.enable_ids or [])
    disable_ids = set(payload.disable_ids or [])

    if enable_ids:
        db.query(Channel).filter(Channel.id.in_(enable_ids)).update({Channel.disabled: False}, synchronize_session=False)

    if disable_ids:
        db.query(Channel).filter(Channel.id.in_(disable_ids)).update({Channel.disabled: True}, synchronize_session=False)

    db.commit()

    return {
        "enabled": len(enable_ids),
        "disabled": len(disable_ids),
    }


# Application Settings Endpoints

@router.get("/app")
async def get_all_application_settings(include_private: bool = False, db: Session = Depends(get_db)):
    """Get all application settings"""
    query = db.query(ApplicationSetting)

    if not include_private:
        query = query.filter(ApplicationSetting.is_public == True)

    settings = query.all()

    result = {}
    for setting in settings:
        result[setting.key] = {
            "value": setting.get_typed_value(),
            "description": setting.description,
            "setting_type": setting.setting_type,
            "is_public": setting.is_public,
            "updated_at": setting.updated_at
        }

    return result


@router.get("/app/{setting_key}")
async def get_application_setting(setting_key: str, db: Session = Depends(get_db)):
    """Get a specific application setting"""
    setting = db.query(ApplicationSetting).filter(ApplicationSetting.key == setting_key).first()

    if not setting:
        # Return default values for known settings
        defaults = {
            "wifi_ssid": "TV",
            "wifi_password": "changeme",
            "wifi_hidden": True,
            "cors_origins": ["http://localhost:3000", "http://localhost:5173"]
        }

        if setting_key in defaults:
            return {"value": defaults[setting_key], "description": f"Default value for {setting_key}"}

        raise HTTPException(status_code=404, detail="Setting not found")

    return {
        "value": setting.get_typed_value(),
        "description": setting.description,
        "setting_type": setting.setting_type,
        "is_public": setting.is_public,
        "updated_at": setting.updated_at
    }


@router.put("/app/{setting_key}")
async def update_application_setting(
    setting_key: str,
    request: ApplicationSettingRequest,
    db: Session = Depends(get_db)
):
    """Update or create an application setting"""
    setting = db.query(ApplicationSetting).filter(ApplicationSetting.key == setting_key).first()

    if setting:
        setting.set_typed_value(request.value)
        if request.description:
            setting.description = request.description
        setting.setting_type = request.setting_type
        setting.is_public = request.is_public
    else:
        setting = ApplicationSetting(
            key=setting_key,
            description=request.description,
            setting_type=request.setting_type,
            is_public=request.is_public
        )
        setting.set_typed_value(request.value)
        db.add(setting)

    db.commit()
    db.refresh(setting)

    return {
        "message": f"Setting '{setting_key}' updated successfully",
        "setting": {
            "key": setting.key,
            "value": setting.get_typed_value(),
            "description": setting.description,
            "setting_type": setting.setting_type,
            "is_public": setting.is_public
        }
    }


@router.delete("/app/{setting_key}")
async def delete_application_setting(setting_key: str, db: Session = Depends(get_db)):
    """Delete an application setting"""
    setting = db.query(ApplicationSetting).filter(ApplicationSetting.key == setting_key).first()

    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    db.delete(setting)
    db.commit()

    return {"message": f"Setting '{setting_key}' deleted successfully"}


# ---------------------------------------------------------------------------
# Network Scanning Subnet Configuration
# ---------------------------------------------------------------------------

class SubnetConfigRequest(BaseModel):
    subnets: List[str]
    enabled: Optional[List[bool]] = None  # Optional per-subnet enable/disable


class SubnetInfo(BaseModel):
    subnet: str
    enabled: bool
    interface: Optional[str] = None
    ip: Optional[str] = None
    cidr: Optional[str] = None
    state: Optional[str] = None


class SubnetConfigResponse(BaseModel):
    configured_subnets: List[SubnetInfo]
    detected_subnets: List[str]
    auto_detect_enabled: bool


@router.get("/network/subnets", response_model=SubnetConfigResponse)
async def get_network_subnets(db: Session = Depends(get_db)):
    """
    Get configured and detected network subnets for scanning

    Returns:
        - configured_subnets: User-configured subnets with enable/disable state
        - detected_subnets: Auto-detected subnets from network interfaces
        - auto_detect_enabled: Whether auto-detection is enabled
    """
    from ..utils.network_utils import get_all_local_subnets, get_interface_info

    # Get auto-detected subnets
    detected_subnets = get_all_local_subnets()
    interface_info = get_interface_info()

    # Create interface lookup map
    interface_map = {iface['subnet']: iface for iface in interface_info}

    # Get configured subnets from database
    configured = settings_service.get_setting("network_scan_subnets")
    auto_detect = settings_service.get_setting("network_scan_auto_detect")

    if auto_detect is None:
        auto_detect = True  # Default to enabled

    if configured is None:
        # First run - initialize with detected subnets (all enabled)
        configured_list = [
            SubnetInfo(
                subnet=subnet,
                enabled=True,
                interface=interface_map.get(subnet, {}).get('interface'),
                ip=interface_map.get(subnet, {}).get('ip'),
                cidr=interface_map.get(subnet, {}).get('cidr'),
                state=interface_map.get(subnet, {}).get('state')
            )
            for subnet in detected_subnets
        ]

        # Save to database for next time
        settings_service.set_setting(
            "network_scan_subnets",
            [{"subnet": s, "enabled": True} for s in detected_subnets],
            description="Configured subnets for network scanning",
            setting_type="json",
            is_public=False
        )
    else:
        # Parse configured subnets
        configured_list = []

        # Handle both old format (list of strings) and new format (list of dicts)
        if isinstance(configured, list) and len(configured) > 0:
            if isinstance(configured[0], str):
                # Old format - convert to new format
                configured = [{"subnet": s, "enabled": True} for s in configured]

            for item in configured:
                subnet = item.get('subnet') if isinstance(item, dict) else item
                enabled = item.get('enabled', True) if isinstance(item, dict) else True

                configured_list.append(SubnetInfo(
                    subnet=subnet,
                    enabled=enabled,
                    interface=interface_map.get(subnet, {}).get('interface'),
                    ip=interface_map.get(subnet, {}).get('ip'),
                    cidr=interface_map.get(subnet, {}).get('cidr'),
                    state=interface_map.get(subnet, {}).get('state')
                ))

    return SubnetConfigResponse(
        configured_subnets=configured_list,
        detected_subnets=detected_subnets,
        auto_detect_enabled=auto_detect
    )


@router.post("/network/subnets", response_model=SubnetConfigResponse)
async def update_network_subnets(
    request: SubnetConfigRequest,
    db: Session = Depends(get_db)
):
    """
    Update network subnet configuration for scanning

    Args:
        request: List of subnets with optional enabled flags

    Returns:
        Updated configuration
    """
    from ..utils.network_utils import validate_subnet, get_all_local_subnets, get_interface_info

    # Validate all subnets
    for subnet in request.subnets:
        if not validate_subnet(subnet):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid subnet format: {subnet}. Expected format: '192.168.1' or '10.0.0'"
            )

    # Build subnet config
    if request.enabled and len(request.enabled) == len(request.subnets):
        subnet_config = [
            {"subnet": subnet, "enabled": enabled}
            for subnet, enabled in zip(request.subnets, request.enabled)
        ]
    else:
        # All enabled by default
        subnet_config = [{"subnet": subnet, "enabled": True} for subnet in request.subnets]

    # Save to database
    settings_service.set_setting(
        "network_scan_subnets",
        subnet_config,
        description="Configured subnets for network scanning",
        setting_type="json",
        is_public=False
    )

    # Return updated config
    detected_subnets = get_all_local_subnets()
    interface_info = get_interface_info()
    interface_map = {iface['subnet']: iface for iface in interface_info}

    configured_list = [
        SubnetInfo(
            subnet=item['subnet'],
            enabled=item['enabled'],
            interface=interface_map.get(item['subnet'], {}).get('interface'),
            ip=interface_map.get(item['subnet'], {}).get('ip'),
            cidr=interface_map.get(item['subnet'], {}).get('cidr'),
            state=interface_map.get(item['subnet'], {}).get('state')
        )
        for item in subnet_config
    ]

    auto_detect = settings_service.get_setting("network_scan_auto_detect")
    if auto_detect is None:
        auto_detect = True

    return SubnetConfigResponse(
        configured_subnets=configured_list,
        detected_subnets=detected_subnets,
        auto_detect_enabled=auto_detect
    )


@router.post("/network/subnets/auto-detect")
async def trigger_subnet_auto_detect(db: Session = Depends(get_db)):
    """
    Trigger auto-detection of network subnets and update configuration

    Detects all active network interfaces and adds new subnets to config
    (preserves existing subnet enable/disable states)
    """
    from ..utils.network_utils import get_all_local_subnets, get_interface_info

    # Get currently configured subnets
    configured = settings_service.get_setting("network_scan_subnets") or []

    # Parse to dict for easy lookup
    configured_map = {}
    if isinstance(configured, list):
        for item in configured:
            if isinstance(item, dict):
                configured_map[item['subnet']] = item['enabled']
            else:
                configured_map[item] = True

    # Detect all subnets
    detected_subnets = get_all_local_subnets()

    # Merge: keep existing configs, add new ones as enabled
    merged = {}
    for subnet in detected_subnets:
        if subnet in configured_map:
            merged[subnet] = configured_map[subnet]  # Preserve existing state
        else:
            merged[subnet] = True  # New subnet - enable by default

    # Convert back to list format
    subnet_config = [
        {"subnet": subnet, "enabled": enabled}
        for subnet, enabled in merged.items()
    ]

    # Save to database
    settings_service.set_setting(
        "network_scan_subnets",
        subnet_config,
        description="Configured subnets for network scanning (auto-detected)",
        setting_type="json",
        is_public=False
    )

    # Return response
    interface_info = get_interface_info()
    interface_map = {iface['subnet']: iface for iface in interface_info}

    configured_list = [
        SubnetInfo(
            subnet=item['subnet'],
            enabled=item['enabled'],
            interface=interface_map.get(item['subnet'], {}).get('interface'),
            ip=interface_map.get(item['subnet'], {}).get('ip'),
            cidr=interface_map.get(item['subnet'], {}).get('cidr'),
            state=interface_map.get(item['subnet'], {}).get('state')
        )
        for item in subnet_config
    ]

    auto_detect = settings_service.get_setting("network_scan_auto_detect")
    if auto_detect is None:
        auto_detect = True

    return {
        "success": True,
        "message": f"Auto-detected {len(detected_subnets)} subnets, merged with existing configuration",
        "config": SubnetConfigResponse(
            configured_subnets=configured_list,
            detected_subnets=detected_subnets,
            auto_detect_enabled=auto_detect
        )
    }


@router.put("/network/subnets/auto-detect")
async def set_subnet_auto_detect(enabled: bool = True, db: Session = Depends(get_db)):
    """
    Enable or disable automatic subnet detection

    Args:
        enabled: True to enable auto-detection, False to disable
    """
    settings_service.set_setting(
        "network_scan_auto_detect",
        enabled,
        description="Enable automatic network subnet detection",
        setting_type="boolean",
        is_public=False
    )

    return {
        "success": True,
        "auto_detect_enabled": enabled,
        "message": f"Auto-detection {'enabled' if enabled else 'disabled'}"
    }
