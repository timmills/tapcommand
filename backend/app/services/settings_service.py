import logging
from typing import Optional, Any, List
from sqlalchemy.orm import Session
from ..models.settings import ApplicationSetting
from ..db.database import get_db

logger = logging.getLogger(__name__)


class SettingsService:
    """Service for managing database-backed application settings"""

    def __init__(self):
        self._cache = {}
        self._cache_initialized = False

    def _get_db(self) -> Session:
        """Get database session"""
        return next(get_db())

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value, with optional default"""
        try:
            db = self._get_db()
            setting = db.query(ApplicationSetting).filter(ApplicationSetting.key == key).first()
            if setting:
                return setting.get_typed_value()
            return default
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}")
            return default

    def set_setting(self, key: str, value: Any, description: str = None, setting_type: str = "string", is_public: bool = False) -> bool:
        """Set a setting value"""
        try:
            db = self._get_db()
            setting = db.query(ApplicationSetting).filter(ApplicationSetting.key == key).first()

            if setting:
                setting.set_typed_value(value)
                if description:
                    setting.description = description
                setting.setting_type = setting_type
                setting.is_public = is_public
            else:
                setting = ApplicationSetting(
                    key=key,
                    description=description,
                    setting_type=setting_type,
                    is_public=is_public
                )
                setting.set_typed_value(value)
                db.add(setting)

            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting {key}: {e}")
            return False

    def get_cors_origins(self) -> List[str]:
        """Get CORS origins from database settings"""
        origins = self.get_setting("cors_origins", [])
        if not origins:
            # Default to safe development origins if not configured
            return ["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"]
        return origins

    def initialize_default_settings(self):
        """Initialize default settings if they don't exist"""
        defaults = [
            {
                "key": "cors_origins",
                "value": ["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"],
                "description": "Allowed CORS origins for frontend applications",
                "setting_type": "json",
                "is_public": False
            },
            {
                "key": "wifi_ssid",
                "value": "TV",
                "description": "Default WiFi SSID for device configuration",
                "setting_type": "string",
                "is_public": True
            },
            {
                "key": "device_discovery_interval",
                "value": 30,
                "description": "Device discovery interval in seconds",
                "setting_type": "integer",
                "is_public": True
            },
            {
                "key": "cors_allow_credentials",
                "value": True,
                "description": "Allow credentials in CORS requests",
                "setting_type": "boolean",
                "is_public": False
            }
        ]

        for default in defaults:
            existing = self.get_setting(default["key"])
            if existing is None:
                self.set_setting(
                    default["key"],
                    default["value"],
                    default["description"],
                    default["setting_type"],
                    default["is_public"]
                )
                logger.info(f"Initialized default setting: {default['key']}")


# Global settings service instance
settings_service = SettingsService()