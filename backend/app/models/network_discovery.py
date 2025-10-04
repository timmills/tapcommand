"""
Network Discovery Models
Manages network scanning, device discovery, and MAC vendor lookup
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class MACVendor(Base):
    """MAC address vendor lookup table"""
    __tablename__ = "mac_vendors"

    id = Column(Integer, primary_key=True, index=True)
    mac_prefix = Column(String, unique=True, index=True, nullable=False)  # "E4:E0:C5"
    vendor_name = Column(String, nullable=False)  # "Samsung Electronics Co.,Ltd"
    is_private = Column(Boolean, default=False)
    block_type = Column(String, nullable=True)  # "MA-L", "IAB", etc.
    last_update = Column(String, nullable=True)  # Date from vendor database

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class NetworkScanCache(Base):
    """Cache of network scan results"""
    __tablename__ = "network_scan_cache"

    id = Column(Integer, primary_key=True, index=True)

    # Network details
    ip_address = Column(String, nullable=False, index=True)
    mac_address = Column(String, nullable=True, index=True)
    hostname = Column(String, nullable=True)
    vendor = Column(String, nullable=True)  # Looked up from MAC

    # Discovery metadata
    is_online = Column(Boolean, default=True)
    last_seen = Column(DateTime(timezone=True), server_default=func.now())
    response_time_ms = Column(Float, nullable=True)

    # Device identification
    device_type_guess = Column(String, nullable=True)  # "samsung_tv", "lg_tv", etc.
    open_ports = Column(JSON, nullable=True)  # [55000, 8001, etc.]

    # Adoption status
    is_adopted = Column(Boolean, default=False)  # Whether it's in devices table
    adopted_hostname = Column(String, nullable=True)  # Link to devices.hostname

    # Scan metadata
    scan_id = Column(String, nullable=True, index=True)  # UUID for batch scans

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class NetworkTVCredentials(Base):
    """Network TV connection credentials and protocol settings"""
    __tablename__ = "network_tv_credentials"

    id = Column(Integer, primary_key=True, index=True)

    # Link to device
    device_hostname = Column(String, unique=True, nullable=False, index=True)  # Links to devices.hostname

    # Network protocol
    protocol = Column(String, nullable=False)  # "samsung_legacy", "samsung_websocket", "lg_webos", "sony_ircc", etc.
    host = Column(String, nullable=False)  # IP address
    port = Column(Integer, nullable=False)  # 55000, 8001, 3000, etc.

    # Authentication
    token = Column(String, nullable=True)  # For modern protocols that need auth tokens
    api_key = Column(String, nullable=True)  # Some protocols use API keys
    pairing_key = Column(String, nullable=True)  # Pairing keys for some protocols

    # Protocol-specific settings
    method = Column(String, nullable=True)  # "legacy", "websocket", "rest", etc.
    ssl_enabled = Column(Boolean, default=False)

    # Additional config (protocol-specific)
    extra_config = Column(JSON, nullable=True)  # {"name": "SmartVenue", "timeout": 3, etc.}

    # Status
    is_paired = Column(Boolean, default=False)
    last_connected = Column(DateTime(timezone=True), nullable=True)
    connection_status = Column(String, default="unpaired")  # "unpaired", "paired", "error"
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SupportedNetworkDevice(Base):
    """Registry of network-controllable device types we support"""
    __tablename__ = "supported_network_devices"

    id = Column(Integer, primary_key=True, index=True)

    # Device brand/type
    brand = Column(String, nullable=False, index=True)  # "Samsung", "LG", "Sony", etc.
    device_category = Column(String, nullable=False)  # "TV", "Display", "Projector", etc.

    # Detection criteria
    mac_prefixes = Column(JSON, nullable=True)  # ["E4:E0:C5", "00:E0:64", ...]
    discovery_ports = Column(JSON, nullable=False)  # [55000, 8001] for Samsung
    protocol_name = Column(String, nullable=False)  # "samsung_legacy", "lg_webos", etc.

    # Capabilities
    requires_pairing = Column(Boolean, default=True)
    supports_power_on = Column(Boolean, default=False)
    supports_status_query = Column(Boolean, default=False)

    # Documentation
    setup_guide_url = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)  # Can we currently support this?
    implementation_status = Column(String, default="planned")  # "working", "testing", "planned"

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
