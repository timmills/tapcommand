"""
SQLAlchemy models for IR remote code capture system

Models:
- CaptureSession: Tracks IR code capture workflows
- CapturedIRCode: Stores individual IR signal data
- CapturedRemote: User-created custom remote profiles
- CapturedRemoteButton: Button-to-code mappings for remotes
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from ..db.database import Base


class CaptureSession(Base):
    """Track IR code capture sessions"""
    __tablename__ = "capture_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # Session identification
    device_hostname = Column(String, nullable=False, index=True)
    session_name = Column(String, nullable=False)
    device_type = Column(String, nullable=False, default="TV")
    brand = Column(String, nullable=True)
    model = Column(String, nullable=True)

    # Session status
    status = Column(String, nullable=False, default="active")  # active, completed, cancelled
    capture_mode = Column(String, nullable=False, default="manual")  # manual, guided

    # Progress tracking (JSON stored as text for SQLite compatibility)
    expected_buttons = Column(Text, nullable=True)  # JSON array of button names
    captured_buttons = Column(Text, nullable=True)  # JSON array of captured button names
    current_button_index = Column(Integer, default=0)

    # Session metadata
    notes = Column(Text, nullable=True)
    created_by = Column(String, nullable=True)

    # Relationships
    codes = relationship("CapturedIRCode", back_populates="session", cascade="all, delete-orphan")
    remotes = relationship("CapturedRemote", back_populates="source_session")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class CapturedIRCode(Base):
    """Store individual captured IR codes"""
    __tablename__ = "captured_ir_codes"

    id = Column(Integer, primary_key=True, index=True)

    # Session reference
    session_id = Column(Integer, ForeignKey("capture_sessions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Code identification
    button_name = Column(String, nullable=False, index=True)
    button_category = Column(String, nullable=True)  # power, volume, channel, number, menu
    sequence_order = Column(Integer, default=0)

    # IR signal data (RAW FORMAT - most reliable)
    protocol = Column(String, nullable=True)  # "NEC", "Samsung32", "RAW", "Unknown"
    carrier_frequency = Column(Integer, default=38000)  # Hz

    # Raw timing data (JSON array stored as text)
    raw_data = Column(Text, nullable=False)  # JSON: [4500, 4500, 560, 1690, ...]

    # Decoded data (if protocol recognized)
    decoded_address = Column(String, nullable=True)
    decoded_command = Column(String, nullable=True)
    decoded_data = Column(String, nullable=True)

    # Capture metadata
    signal_strength = Column(Integer, nullable=True)
    capture_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    is_valid = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)

    # Relationships
    session = relationship("CaptureSession", back_populates="codes")
    remote_buttons = relationship("CapturedRemoteButton", back_populates="code")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CapturedRemote(Base):
    """User-created custom remote profiles"""
    __tablename__ = "captured_remotes"

    id = Column(Integer, primary_key=True, index=True)

    # Remote identification
    name = Column(String, nullable=False)
    device_type = Column(String, nullable=False, default="TV", index=True)
    brand = Column(String, nullable=True, index=True)
    model = Column(String, nullable=True)

    # Source session
    source_session_id = Column(Integer, ForeignKey("capture_sessions.id", ondelete="SET NULL"), nullable=True)

    # Remote metadata
    description = Column(Text, nullable=True)
    icon = Column(String, nullable=True)
    button_count = Column(Integer, default=0)

    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Organization
    is_favorite = Column(Boolean, default=False, index=True)
    tags = Column(Text, nullable=True)  # JSON array

    # Sharing/visibility
    is_public = Column(Boolean, default=False)
    created_by = Column(String, nullable=True)

    # Relationships
    source_session = relationship("CaptureSession", back_populates="remotes")
    buttons = relationship("CapturedRemoteButton", back_populates="remote", cascade="all, delete-orphan")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CapturedRemoteButton(Base):
    """Map buttons to IR codes for custom remotes"""
    __tablename__ = "captured_remote_buttons"

    id = Column(Integer, primary_key=True, index=True)

    # Remote reference
    remote_id = Column(Integer, ForeignKey("captured_remotes.id", ondelete="CASCADE"), nullable=False, index=True)

    # Code reference
    code_id = Column(Integer, ForeignKey("captured_ir_codes.id", ondelete="CASCADE"), nullable=False, index=True)

    # Button configuration
    button_name = Column(String, nullable=False)
    button_label = Column(String, nullable=True)
    button_category = Column(String, nullable=True)

    # UI layout (optional - for advanced UI)
    grid_position = Column(Text, nullable=True)  # JSON: {"row": 1, "col": 2}
    button_size = Column(String, default="normal")  # small, normal, large
    button_color = Column(String, nullable=True)

    # Button metadata
    is_macro = Column(Boolean, default=False)
    sequence_order = Column(Integer, default=0)

    # Relationships
    remote = relationship("CapturedRemote", back_populates="buttons")
    code = relationship("CapturedIRCode", back_populates="remote_buttons")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
