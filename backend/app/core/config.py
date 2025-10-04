from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path

# Define the backend root directory (where this config file's parent/parent/parent is)
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "SmartVenue"
    PROJECT_VERSION: str = "1.0.0"

    # Database - using absolute path to ensure consistency
    DATABASE_URL: str = "sqlite:////home/coastal/smartvenue/backend/smartvenue.db"
    SQLITE_DATABASE_PATH: str = str(BACKEND_ROOT / "smartvenue.db")

    # ESPHome Discovery
    MDNS_SERVICE_TYPE: str = "_esphomelib._tcp.local."
    DEVICE_DISCOVERY_INTERVAL: int = 30  # seconds

    # ESPHome API
    ESPHOME_API_PORT: int = 6053
    ESPHOME_API_KEY: Optional[str] = None  # Set via environment variable for security

    # Network
    WIFI_SSID: str = "TV"

    # CORS Configuration
    CORS_ORIGINS: list[str] = ["*"]  # Allow all origins by default; tighten for production
    CORS_ALLOW_CREDENTIALS: bool = False

    # Scheduling
    SCHEDULER_TIMEZONE: str = "Australia/Sydney"

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
