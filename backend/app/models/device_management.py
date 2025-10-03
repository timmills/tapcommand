from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class DeviceTag(Base):
    """Global device tags for categorizing and organizing connected devices"""
    __tablename__ = "device_tags"

    id = Column(Integer, primary_key=True, index=True)

    # Tag properties
    name = Column(String, nullable=False, unique=True, index=True)  # "Sports TVs", "Main Area", "Background Music"
    color = Column(String, nullable=True)  # Hex color code for UI display
    description = Column(Text, nullable=True)  # Optional description

    # Usage tracking
    usage_count = Column(Integer, default=0)  # How many devices use this tag

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ManagedDevice(Base):
    """Enhanced device management with IR port mapping"""
    __tablename__ = "managed_devices"

    id = Column(Integer, primary_key=True, index=True)

    # Core device identification
    hostname = Column(String, unique=True, index=True, nullable=False)  # ir-dc4516
    mac_address = Column(String, unique=True, index=True, nullable=False)
    current_ip_address = Column(String, nullable=False)

    # User-configurable settings
    device_name = Column(String, nullable=True)  # "Main Bar IR Controller"
    api_key = Column(String, nullable=True)  # ESPHome API encryption key
    venue_name = Column(String, nullable=True)  # "The Crown Hotel"
    location = Column(String, nullable=True)  # "Main Bar"

    # Device capabilities
    total_ir_ports = Column(Integer, default=5)
    firmware_version = Column(String, nullable=True)
    device_type = Column(String, nullable=False, default="universal")  # All devices are universal

    # Network status
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_ip_address = Column(String, nullable=True)  # Previous IP for tracking

    # Metadata
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    ir_ports = relationship("IRPort", back_populates="device", cascade="all, delete-orphan")


class IRPort(Base):
    """Individual IR port configuration on each device"""
    __tablename__ = "ir_ports"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("managed_devices.id"), nullable=False)

    # Port identification
    port_number = Column(Integer, nullable=False)  # 0-4 for 5-port devices
    port_id = Column(String, nullable=True, index=True)  # "dc4516-1", "dc4516-2", etc. - unique identifier using last 6 digits of MAC + port number
    gpio_pin = Column(String, nullable=True)  # "GPIO14", "GPIO12", etc.

    # Connected device information
    connected_device_name = Column(String, nullable=True)  # "Main Bar TV", "Set-top Box 2"
    # Physical connection
    is_active = Column(Boolean, default=True)
    cable_length = Column(String, nullable=True)  # "2m", "5m"
    installation_notes = Column(Text, nullable=True)

    # Device categorization
    tag_ids = Column(JSON, nullable=True)  # Array of DeviceTag IDs for this device

    # Device configuration
    default_channel = Column(String, nullable=True)  # Default channel for this device (e.g., "501", "BBC1")

    # For multi-device setups - which device/box number this port controls
    device_number = Column(Integer, nullable=True)  # 0-4 for set-top boxes, etc.

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    device = relationship("ManagedDevice", back_populates="ir_ports")

    # Unique constraint: one port number per device
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )


class DeviceDiscovery(Base):
    """Track discovered devices that haven't been added to management yet"""
    __tablename__ = "device_discoveries"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String, unique=True, index=True, nullable=False)
    mac_address = Column(String, nullable=False)
    ip_address = Column(String, nullable=False)

    # Discovery information
    friendly_name = Column(String, nullable=True)
    device_type = Column(String, nullable=True)
    firmware_version = Column(String, nullable=True)
    discovery_properties = Column(JSON, nullable=True)

    # Status
    is_managed = Column(Boolean, default=False)  # True if added to managed_devices
    first_discovered = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now())

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
