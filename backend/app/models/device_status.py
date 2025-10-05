"""
Device Status Model

Tracks real-time status of network devices
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func

from ..db.database import Base


class DeviceStatus(Base):
    """Device status tracking model"""
    __tablename__ = "device_status"

    id = Column(Integer, primary_key=True, index=True)

    # Device identification
    controller_id = Column(String, unique=True, nullable=False, index=True)
    device_type = Column(String, nullable=False, index=True)
    protocol = Column(String, nullable=True)

    # Status information
    is_online = Column(Boolean, default=False, index=True)
    power_state = Column(String, default="unknown", index=True)  # on, off, unknown
    current_channel = Column(String, nullable=True)
    current_input = Column(String, nullable=True)
    volume_level = Column(Integer, nullable=True)
    is_muted = Column(Boolean, nullable=True)

    # Additional metadata
    model_info = Column(String, nullable=True)
    firmware_version = Column(String, nullable=True)

    # Check method and timing
    check_method = Column(String, nullable=True)  # ping, api, query
    check_interval_seconds = Column(Integer, default=300)  # 5 minutes

    # Timestamps
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    last_changed_at = Column(DateTime(timezone=True), nullable=True)
    last_online_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<DeviceStatus(controller_id='{self.controller_id}', is_online={self.is_online}, power_state='{self.power_state}')>"
