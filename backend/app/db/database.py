from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy import inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from ..core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Session:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables"""
    from ..models.device import Base as DeviceBase
    from ..models.device_management import Base as ManagementBase
    from ..models.ir_codes import Base as IRCodesBase
    from ..models.settings import ApplicationSetting
    from ..models.command_queue import Base as CommandQueueBase
    from ..models.ir_capture import Base as IRCaptureBase
    from ..models.network_discovery import Base as NetworkDiscoveryBase
    from ..models.virtual_controller import Base as VirtualControllerBase

    DeviceBase.metadata.create_all(bind=engine)
    ManagementBase.metadata.create_all(bind=engine)
    IRCodesBase.metadata.create_all(bind=engine)
    CommandQueueBase.metadata.create_all(bind=engine)  # Command queue system
    IRCaptureBase.metadata.create_all(bind=engine)  # IR capture system
    NetworkDiscoveryBase.metadata.create_all(bind=engine)  # Network discovery system
    VirtualControllerBase.metadata.create_all(bind=engine)  # Virtual controller system
    Base.metadata.create_all(bind=engine)  # This creates the ApplicationSetting table

    _ensure_ir_library_hidden_column(engine)


def init_database():
    """Initialize database with seed data"""
    from .seed_data import seed_database

    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()


def _ensure_ir_library_hidden_column(engine: Engine) -> None:
    inspector = inspect(engine)
    try:
        columns = {column['name'] for column in inspector.get_columns('ir_libraries')}
    except Exception:
        return

    if 'hidden' in columns:
        return

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE ir_libraries ADD COLUMN hidden INTEGER NOT NULL DEFAULT 0"))
        conn.execute(
            text(
                "UPDATE ir_libraries SET hidden = CASE WHEN device_category = 'TV' THEN 0 ELSE 1 END"
            )
        )
