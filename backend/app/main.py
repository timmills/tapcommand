import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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
from .routers.auth import router as auth_router
from .routers.users import router as users_router
from .routers.network_tv import router as network_tv_router
from .routers.network_discovery import router as network_discovery_router
from .routers.virtual_controllers import router as virtual_controllers_router
from .routers.device_status import router as device_status_router
from .api.hybrid_devices import router as hybrid_devices_router
from .commands.api import router as unified_commands_router
from .routers.audio_controllers import router as audio_controllers_router
from .routers.documentation import router as documentation_router
from .services.discovery import discovery_service
from .services.device_health import health_checker
from .services.queue_processor import start_queue_processor, stop_queue_processor
from .services.history_cleanup import start_history_cleanup, stop_history_cleanup
from .services.schedule_processor import start_schedule_processor, stop_schedule_processor
from .services.device_status_checker import status_checker
from .services.tv_status_poller import tv_status_poller

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Store the main event loop for use in sync callbacks
_main_loop = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    global _main_loop
    _main_loop = asyncio.get_running_loop()

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

    # Start device status monitoring
    await status_checker.start_status_monitoring()
    logger.info("Device status monitoring started")

    # Start TV status polling service
    await tv_status_poller.start()
    logger.info("TV status polling service started")

    yield

    # Shutdown
    logger.info("Shutting down SmartVenue backend...")
    await tv_status_poller.stop()
    logger.info("TV status polling service stopped")
    await status_checker.stop_status_monitoring()
    logger.info("Device status monitoring stopped")
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

    # Save to database for adoption
    from .db.database import SessionLocal
    from .models.device_management import DeviceDiscovery
    from .models.device import Device
    from .services.esphome_client import esphome_manager
    from .services.settings_service import settings_service
    from datetime import datetime

    db = SessionLocal()
    try:
        # Check if device already exists
        existing = db.query(DeviceDiscovery).filter(
            DeviceDiscovery.hostname == device.hostname
        ).first()

        if existing:
            # Update existing record
            existing.ip_address = device.ip_address
            existing.last_seen = datetime.now()
            existing.firmware_version = device.version
            existing.discovery_properties = device.properties
        else:
            # Create new discovery record
            discovery = DeviceDiscovery(
                hostname=device.hostname,
                mac_address=device.mac_address,
                ip_address=device.ip_address,
                friendly_name=device.friendly_name,
                device_type=device.device_type,
                firmware_version=device.version,
                discovery_properties=device.properties,
                is_managed=False
            )
            db.add(discovery)

        # Only fetch capabilities for IR controllers (ir-* prefix)
        # Skip network devices (nw-*) as they don't have ESPHome capabilities
        if device.hostname.startswith("ir-"):
            # Fetch capabilities asynchronously (fire and forget to not block mDNS callback)
            async def fetch_caps():
                try:
                    api_key = settings_service.get_setting("esphome_api_key")
                    capabilities = await esphome_manager.fetch_capabilities(
                        device.hostname,
                        device.ip_address,
                        api_key
                    )

                    # Update in a new session since this runs async
                    db_async = SessionLocal()
                    try:
                        dev_rec = db_async.query(Device).filter(Device.hostname == device.hostname).first()
                        if dev_rec:
                            dev_rec.capabilities = capabilities
                            dev_rec.last_seen = datetime.now()
                            dev_rec.is_online = True
                        else:
                            dev_rec = Device(
                                hostname=device.hostname,
                                mac_address=device.mac_address,
                                ip_address=device.ip_address,
                                friendly_name=device.friendly_name,
                                device_type=device.device_type,
                                firmware_version=device.version,
                                is_online=True,
                                capabilities=capabilities
                            )
                            db_async.add(dev_rec)
                        db_async.commit()
                        logger.info(f"Updated capabilities for {device.hostname}")
                    except Exception as e:
                        logger.error(f"Error updating capabilities in async task: {e}")
                        db_async.rollback()
                    finally:
                        db_async.close()
                except Exception as e:
                    logger.debug(f"Failed to fetch capabilities for {device.hostname}: {e}")

            # Schedule the async task in the main event loop
            if _main_loop is not None:
                asyncio.run_coroutine_threadsafe(fetch_caps(), _main_loop)
            else:
                logger.warning(f"Cannot schedule capability fetch for {device.hostname} - main loop not available")

        db.commit()
        logger.info(f"Saved {device.hostname} to DeviceDiscovery table")
    except Exception as e:
        logger.error(f"Error saving discovered device to database: {e}")
        db.rollback()
    finally:
        db.close()


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

# Include authentication router (standalone - does not enforce auth on other endpoints)
app.include_router(
    auth_router,
    prefix=f"{settings.API_V1_STR}"
)

# Include user management router (standalone - does not enforce auth on other endpoints)
app.include_router(
    users_router,
    prefix=f"{settings.API_V1_STR}"
)

# Include network TV control router
app.include_router(
    network_tv_router
)

# Include network discovery router
app.include_router(
    network_discovery_router
)

# Include virtual controllers router
app.include_router(
    virtual_controllers_router
)

# Include unified commands router (NEW - routes all commands through queue)
app.include_router(
    unified_commands_router
)

# Include device status router
app.include_router(
    device_status_router
)

# Include hybrid devices router
app.include_router(
    hybrid_devices_router,
    prefix=f"{settings.API_V1_STR}"
)

# Include audio controllers router
app.include_router(
    audio_controllers_router
)

# Include documentation router
app.include_router(
    documentation_router
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


@app.get("/install.sh")
async def get_install_script():
    """Serve the install script for wget deployment"""
    install_script = Path(__file__).parent.parent.parent / "install.sh"
    if install_script.exists():
        return FileResponse(
            path=install_script,
            media_type="text/x-shellscript",
            filename="install.sh",
            headers={
                "Content-Disposition": "attachment; filename=install.sh"
            }
        )
    return {"error": "Install script not found"}


@app.get("/install-fancy.sh")
async def get_fancy_install_script():
    """Serve the fancy Gum-enhanced install script for wget deployment"""
    install_script = Path(__file__).parent.parent.parent / "install-fancy.sh"
    if install_script.exists():
        return FileResponse(
            path=install_script,
            media_type="text/x-shellscript",
            filename="install-fancy.sh",
            headers={
                "Content-Disposition": "attachment; filename=install-fancy.sh"
            }
        )
    return {"error": "Fancy install script not found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
