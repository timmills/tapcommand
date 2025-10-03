"""
Database migration to add IR capture tables for custom remote programming

This migration adds 4 new tables:
- capture_sessions: Track IR code capture sessions
- captured_ir_codes: Store raw IR signal data
- captured_remotes: User-created custom remote profiles
- captured_remote_buttons: Button-to-code mappings

Migration can be run standalone or integrated into main migration system.
"""

from sqlalchemy import create_engine, text
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings

logger = logging.getLogger(__name__)


def upgrade(engine):
    """Add IR capture tables"""

    with engine.begin() as conn:
        logger.info("Creating capture_sessions table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS capture_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                -- Session identification
                device_hostname VARCHAR NOT NULL,
                session_name VARCHAR NOT NULL,
                device_type VARCHAR NOT NULL DEFAULT 'TV',
                brand VARCHAR,
                model VARCHAR,

                -- Session status
                status VARCHAR NOT NULL DEFAULT 'active',
                capture_mode VARCHAR NOT NULL DEFAULT 'manual',

                -- Progress tracking (for guided mode)
                expected_buttons TEXT,
                captured_buttons TEXT,
                current_button_index INTEGER DEFAULT 0,

                -- Session metadata
                notes TEXT,
                created_by VARCHAR,

                -- Timestamps
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME
            )
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_capture_sessions_hostname
            ON capture_sessions(device_hostname)
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_capture_sessions_status
            ON capture_sessions(status)
        """))

        logger.info("Creating captured_ir_codes table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS captured_ir_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                -- Session reference
                session_id INTEGER NOT NULL,

                -- Code identification
                button_name VARCHAR NOT NULL,
                button_category VARCHAR,
                sequence_order INTEGER DEFAULT 0,

                -- IR signal data (RAW FORMAT - most reliable)
                protocol VARCHAR,
                carrier_frequency INTEGER DEFAULT 38000,

                -- Raw timing data (JSON array of microseconds)
                raw_data TEXT NOT NULL,

                -- Decoded data (if protocol recognized by ESPHome)
                decoded_address VARCHAR,
                decoded_command VARCHAR,
                decoded_data VARCHAR,

                -- Capture metadata
                signal_strength INTEGER,
                capture_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_valid INTEGER DEFAULT 1,
                notes TEXT,

                -- Timestamps
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (session_id) REFERENCES capture_sessions(id) ON DELETE CASCADE
            )
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_captured_ir_codes_session
            ON captured_ir_codes(session_id)
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_captured_ir_codes_button
            ON captured_ir_codes(button_name)
        """))

        logger.info("Creating captured_remotes table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS captured_remotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                -- Remote identification
                name VARCHAR NOT NULL,
                device_type VARCHAR NOT NULL DEFAULT 'TV',
                brand VARCHAR,
                model VARCHAR,

                -- Source session
                source_session_id INTEGER,

                -- Remote metadata
                description TEXT,
                icon VARCHAR,
                button_count INTEGER DEFAULT 0,

                -- Usage tracking
                usage_count INTEGER DEFAULT 0,
                last_used_at DATETIME,

                -- Organization
                is_favorite INTEGER DEFAULT 0,
                tags TEXT,

                -- Sharing/visibility
                is_public INTEGER DEFAULT 0,
                created_by VARCHAR,

                -- Timestamps
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (source_session_id) REFERENCES capture_sessions(id) ON DELETE SET NULL
            )
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_captured_remotes_device_type
            ON captured_remotes(device_type)
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_captured_remotes_brand
            ON captured_remotes(brand)
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_captured_remotes_favorite
            ON captured_remotes(is_favorite)
        """))

        logger.info("Creating captured_remote_buttons table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS captured_remote_buttons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                -- Remote reference
                remote_id INTEGER NOT NULL,

                -- Code reference
                code_id INTEGER NOT NULL,

                -- Button configuration
                button_name VARCHAR NOT NULL,
                button_label VARCHAR,
                button_category VARCHAR,

                -- UI layout (optional - for advanced UI)
                grid_position TEXT,
                button_size VARCHAR DEFAULT 'normal',
                button_color VARCHAR,

                -- Button metadata
                is_macro INTEGER DEFAULT 0,
                sequence_order INTEGER DEFAULT 0,

                -- Timestamps
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (remote_id) REFERENCES captured_remotes(id) ON DELETE CASCADE,
                FOREIGN KEY (code_id) REFERENCES captured_ir_codes(id) ON DELETE CASCADE
            )
        """))

        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_remote_buttons_unique
            ON captured_remote_buttons(remote_id, button_name)
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_remote_buttons_remote
            ON captured_remote_buttons(remote_id)
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_remote_buttons_code
            ON captured_remote_buttons(code_id)
        """))

        logger.info("✅ IR capture tables created successfully")


def downgrade(engine):
    """Remove IR capture tables"""

    with engine.begin() as conn:
        logger.info("Dropping IR capture tables...")

        # Drop in reverse order due to foreign keys
        conn.execute(text("DROP TABLE IF EXISTS captured_remote_buttons"))
        conn.execute(text("DROP TABLE IF EXISTS captured_remotes"))
        conn.execute(text("DROP TABLE IF EXISTS captured_ir_codes"))
        conn.execute(text("DROP TABLE IF EXISTS capture_sessions"))

        logger.info("✅ IR capture tables removed")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create engine
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    )

    print("=" * 60)
    print("IR CAPTURE TABLES MIGRATION")
    print("=" * 60)
    print()

    # Run migration
    try:
        upgrade(engine)
        print()
        print("✅ Migration completed successfully!")
        print()
        print("New tables created:")
        print("  - capture_sessions")
        print("  - captured_ir_codes")
        print("  - captured_remotes")
        print("  - captured_remote_buttons")
        print()
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        print()
        print(f"❌ Migration failed: {e}")
        print()
        sys.exit(1)
