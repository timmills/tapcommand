import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core.config import settings
from .db.database import create_tables, init_database
from .api.devices import router as devices_router
from .api.device_management import router as management_router
from .api.admin import router as admin_router
from .routers.ir_codes import router as ir_codes_router
from .routers.templates import router as templates_router
from .routers.settings import router as settings_router
from .routers.channels import router as channels_router
from .routers.ir_libraries import router as ir_libraries_router
from .routers.commands import router as commands_router
from .routers.ir_capture import router as ir_capture_router
from .routers.schedules import router as schedules_router
from .services.discovery import discovery_service
from .services.device_health import health_checker
from .services.queue_processor import start_queue_processor, stop_queue_processor
from .services.history_cleanup import start_history_cleanup, stop_history_cleanup
from .services.schedule_processor import start_schedule_processor, stop_schedule_processor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting SmartVenue backend...")

    # Create database tables
    create_tables()
    logger.info("Database tables created")

    # Initialize database with seed data
    init_database()
    logger.info("Database initialized with seed data")

    # Start device discovery
    await discovery_service.start_discovery()
    logger.info("Device discovery started")

    # Register discovery callbacks to update database
    discovery_service.add_discovery_callback(on_device_discovered)
    discovery_service.add_removal_callback(on_device_removed)

    # Start device health monitoring
    await health_checker.start_health_monitoring()
    logger.info("Device health monitoring started")

    # Start command queue processor
    await start_queue_processor()
    logger.info("Command queue processor started")

    # Start history cleanup service
    await start_history_cleanup()
    logger.info("History cleanup service started")

    # Start schedule processor
    await start_schedule_processor()
    logger.info("Schedule processor started")

    yield

    # Shutdown
    logger.info("Shutting down SmartVenue backend...")
    await stop_schedule_processor()
    logger.info("Schedule processor stopped")
    await stop_history_cleanup()
    logger.info("History cleanup service stopped")
    await stop_queue_processor()
    logger.info("Command queue processor stopped")
    await health_checker.stop_health_monitoring()
    logger.info("Device health monitoring stopped")
    await discovery_service.stop_discovery()
    logger.info("Device discovery stopped")


def on_device_discovered(device):
    """Callback when a new device is discovered"""
    logger.info(f"New device discovered: {device.hostname} ({device.ip_address})")
    # Here you could automatically register the device or update its status
    # For now, we just log it


def on_device_removed(hostname):
    """Callback when a device is removed"""
    logger.info(f"Device removed: {hostname}")
    # Here you could update the device status in the database


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Commercial hospitality display management system",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    devices_router,
    prefix=f"{settings.API_V1_STR}/devices",
    tags=["devices"]
)

app.include_router(
    management_router,
    prefix=f"{settings.API_V1_STR}/management",
    tags=["device-management"]
)

app.include_router(
    admin_router,
    prefix=f"{settings.API_V1_STR}/admin",
    tags=["admin"]
)

app.include_router(
    ir_codes_router,
    tags=["ir-codes"]
)

app.include_router(
    templates_router
)

app.include_router(
    settings_router
)

app.include_router(
    channels_router,
    prefix=f"{settings.API_V1_STR}/channels",
    tags=["channels"]
)

app.include_router(
    ir_libraries_router
)

app.include_router(
    commands_router,
    prefix=f"{settings.API_V1_STR}"
)

app.include_router(
    ir_capture_router
)

app.include_router(
    schedules_router,
    prefix=f"{settings.API_V1_STR}/schedules",
    tags=["schedules"]
)

# Mount static files for channel icons
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "SmartVenue API",
        "version": settings.PROJECT_VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
