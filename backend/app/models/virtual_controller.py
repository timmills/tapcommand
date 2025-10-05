"""
Virtual Controller Models
Software representation of TV/device controllers for network-based devices
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class VirtualController(Base):
    """
    Virtual Controller - Software representation of a TV/device controller

    Unlike physical IR controllers, these are software-based controllers for:
    - Network TVs (Samsung, LG, Sony, etc.)
    - Streaming devices (Roku, Apple TV, Chromecast)
    - Any IP-controllable device

    Each Virtual Controller can have multiple "virtual ports" (devices mapped to it)
    """
    __tablename__ = "virtual_controllers"

    id = Column(Integer, primary_key=True, index=True)

    # Controller identification
    controller_name = Column(String, nullable=False, index=True)  # "Living Room TV Controller"
    controller_id = Column(String, unique=True, index=True, nullable=False)  # "vc-samsung-50" (unique identifier)

    # Controller type
    controller_type = Column(String, nullable=False)  # "network_tv", "streaming_device", "generic"
    protocol = Column(String, nullable=True)  # "samsung_legacy", "samsung_websocket", "lg_webos", etc.

    # Location/venue info
    venue_name = Column(String, nullable=True)  # "The Crown Hotel"
    location = Column(String, nullable=True)  # "Main Bar"

    # Controller capabilities
    total_ports = Column(Integer, default=5)  # How many devices can be mapped (default 5, like physical controllers)
    capabilities = Column(JSON, nullable=True)  # {"power": true, "volume": true, "channels": true}

    # Status
    is_active = Column(Boolean, default=True)
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    virtual_devices = relationship("VirtualDevice", back_populates="controller", cascade="all, delete-orphan")


class VirtualDevice(Base):
    """
    Virtual Device - A device mapped to a specific port on a Virtual Controller

    This represents the actual TV/device connected to the virtual controller.
    Similar to IRPort, but for network devices.
    """
    __tablename__ = "virtual_devices"

    id = Column(Integer, primary_key=True, index=True)
    controller_id = Column(Integer, ForeignKey("virtual_controllers.id"), nullable=False)

    # Port identification (1-5, like physical controllers)
    port_number = Column(Integer, nullable=False)  # 1-5
    port_id = Column(String, nullable=True, index=True)  # "vc-samsung-50-1" (controller_id + port_number)

    # Device information
    device_name = Column(String, nullable=False)  # "Main Bar Samsung TV"
    device_type = Column(String, nullable=True)  # "samsung_tv_legacy", "lg_webos", etc.

    # Network connection details
    ip_address = Column(String, nullable=False)
    mac_address = Column(String, nullable=True)
    port = Column(Integer, nullable=True)  # Control port (55000, 8001, etc.)
    protocol = Column(String, nullable=True)  # "samsung_legacy", "samsung_websocket", etc.

    # Device configuration
    connection_config = Column(JSON, nullable=True)  # Protocol-specific config (API keys, tokens, etc.)
    default_channel = Column(String, nullable=True)  # Default channel for this device

    # Device capabilities
    capabilities = Column(JSON, nullable=True)  # {"power": true, "volume": true, "hdmi_input": true}

    # Status
    is_active = Column(Boolean, default=True)
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime(timezone=True), nullable=True)

    # Device categorization (tags)
    tag_ids = Column(JSON, nullable=True)  # Array of DeviceTag IDs

    # Installation notes
    installation_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    controller = relationship("VirtualController", back_populates="virtual_devices")

    # Unique constraint: one port number per controller
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )
