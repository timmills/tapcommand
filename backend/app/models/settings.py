from sqlalchemy import Column, String, Text, Boolean, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

from ..db.database import Base


class ApplicationSetting(Base):
    """Database-backed application settings"""
    __tablename__ = "application_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    setting_type = Column(String(20), default="string")  # string, boolean, json, integer
    is_public = Column(Boolean, default=False)  # Can be exposed to frontend
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def get_typed_value(self):
        """Return the value in the correct type"""
        if self.value is None:
            return None

        if self.setting_type == "boolean":
            return self.value.lower() in ("true", "1", "yes", "on")
        elif self.setting_type == "integer":
            try:
                return int(self.value)
            except (ValueError, TypeError):
                return 0
        elif self.setting_type == "json":
            import json
            try:
                return json.loads(self.value)
            except (json.JSONDecodeError, TypeError):
                return {}
        else:  # string or default
            return self.value

    def set_typed_value(self, value):
        """Set the value with automatic type conversion"""
        if value is None:
            self.value = None
        elif self.setting_type == "boolean":
            self.value = "true" if value else "false"
        elif self.setting_type == "integer":
            self.value = str(value)
        elif self.setting_type == "json":
            import json
            self.value = json.dumps(value)
        else:  # string or default
            self.value = str(value)