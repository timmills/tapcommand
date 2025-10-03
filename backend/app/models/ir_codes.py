from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, Dict, Any

from .device import Base


class IRLibrary(Base):
    """IR Code Libraries from external sources like Flipper-IRDB"""
    __tablename__ = "ir_libraries"

    id = Column(Integer, primary_key=True, index=True)

    # Library identification
    source = Column(String, nullable=False, index=True)  # "flipper-irdb", "custom", "broadlink"
    source_path = Column(String, nullable=False)  # "TVs/Samsung/Samsung_TV_Full.ir"
    source_url = Column(String, nullable=True)  # GitHub raw URL for updates

    # Device categorization
    device_category = Column(String, nullable=False, index=True)  # "TVs", "ACs", "Audio"
    brand = Column(String, nullable=False, index=True)  # "Samsung", "LG", "Sony"
    model = Column(String, nullable=True)  # "TV_Full", "UE32F4000", "Smart_Remote"

    # Library metadata
    name = Column(String, nullable=False)  # "Samsung TV Full"
    description = Column(Text, nullable=True)  # "Complete Samsung TV remote"
    version = Column(String, nullable=True)  # From IR file version field

    # ESPHome native flag
    esp_native = Column(Boolean, nullable=False, default=False)

    # Visibility flag
    hidden = Column(Boolean, nullable=False, default=False)

    # Import tracking
    file_hash = Column(String, nullable=False)  # MD5 hash for change detection
    last_updated = Column(DateTime(timezone=True), nullable=False)
    import_status = Column(String, nullable=False, default="pending")  # "pending", "imported", "failed"
    import_error = Column(Text, nullable=True)

    # Generic compatibility score (0-9 scale)
    generic_compatibility = Column(Integer, nullable=True)

    # Commands relationship
    commands = relationship("IRCommand", back_populates="library", cascade="all, delete-orphan")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IRCommand(Base):
    """Individual IR commands from libraries"""
    __tablename__ = "ir_commands"

    id = Column(Integer, primary_key=True, index=True)
    library_id = Column(Integer, ForeignKey("ir_libraries.id"), nullable=False, index=True)

    # Command identification
    name = Column(String, nullable=False, index=True)  # "Power", "Vol_up", "Ch_next"
    display_name = Column(String, nullable=True)  # "Power On/Off", "Volume Up"
    category = Column(String, nullable=True, index=True)  # "power", "volume", "navigation"

    # IR signal data - flexible to support multiple formats
    protocol = Column(String, nullable=False)  # "Samsung32", "NEC", "Sony", "RC5"

    # Protocol-specific data stored as JSON for flexibility
    signal_data = Column(JSON, nullable=False)
    # Examples:
    # Samsung: {"address": "07 00 00 00", "command": "02 00 00 00"}
    # NEC: {"address": "0x04", "command": "0x08"}
    # Sony: {"data": "0xA90", "nbits": 12}
    # Pronto: {"data": "0000 0073 0000 0012..."}

    # Additional metadata
    frequency = Column(Integer, nullable=True)  # Carrier frequency if specified
    duty_cycle = Column(Integer, nullable=True)  # Duty cycle percentage

    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime(timezone=True), nullable=True)

    # Relationship
    library = relationship("IRLibrary", back_populates="commands")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IRImportLog(Base):
    """Track imports and updates from external sources"""
    __tablename__ = "ir_import_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Import details
    source = Column(String, nullable=False, index=True)  # "flipper-irdb"
    source_commit = Column(String, nullable=True)  # Git commit hash for version tracking
    import_type = Column(String, nullable=False)  # "full", "update", "incremental"

    # Statistics
    libraries_processed = Column(Integer, default=0)
    libraries_imported = Column(Integer, default=0)
    libraries_updated = Column(Integer, default=0)
    libraries_failed = Column(Integer, default=0)
    commands_imported = Column(Integer, default=0)

    # Status
    status = Column(String, nullable=False)  # "running", "completed", "failed"
    error_message = Column(Text, nullable=True)

    # Performance
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Import details
    import_details = Column(JSON, nullable=True)  # {"errors": [], "warnings": [], "new_brands": []}

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ESPTemplate(Base):
    """Stored ESPHome templates for different hardware profiles"""
    __tablename__ = "esp_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    board = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    template_yaml = Column(Text, nullable=False)
    version = Column(String, nullable=False, default="1.0.0")
    revision = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PortAssignment(Base):
    """Assigns IR libraries to specific device ports"""
    __tablename__ = "port_assignments"

    id = Column(Integer, primary_key=True, index=True)

    # Device and port
    device_hostname = Column(String, nullable=False, index=True)
    port_number = Column(Integer, nullable=False)  # 1-5
    gpio_pin = Column(String, nullable=True)  # "GPIO14", "GPIO12"

    # Assigned library
    library_id = Column(Integer, ForeignKey("ir_libraries.id"), nullable=False)

    # Port configuration
    device_name = Column(String, nullable=True)  # "Main Bar TV"
    is_active = Column(Boolean, default=True)

    # Installation details
    installation_notes = Column(Text, nullable=True)
    cable_length = Column(String, nullable=True)
    ir_led_type = Column(String, nullable=True)  # "940nm", "950nm"

    # Usage tracking
    last_command_sent = Column(DateTime(timezone=True), nullable=True)
    total_commands_sent = Column(Integer, default=0)

    # Relationship
    library = relationship("IRLibrary")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
