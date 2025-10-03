#!/usr/bin/env python3
"""
Import all TV brands from local Flipper-IRDB copy
"""
import sys
import logging
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent))

from app.db.database import SessionLocal
from app.services.ir_import import import_flipper_irdb_sync

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Import all brands from Flipper-IRDB"""

    logger.info("Starting FULL import from local Flipper-IRDB...")
    logger.info("This will import ALL device categories and brands (TVs, ACs, Audio, etc.)")

    # Get database session
    db = SessionLocal()

    try:
        # Import everything from Flipper-IRDB
        logger.info("Importing all devices from local Flipper-IRDB copy...")
        logger.info("This may take several minutes...")

        import_log = import_flipper_irdb_sync(db)

        logger.info(f"Import completed!")
        logger.info(f"Status: {import_log.status}")
        logger.info(f"Libraries processed: {import_log.libraries_processed}")
        logger.info(f"Libraries imported: {import_log.libraries_imported}")
        logger.info(f"Libraries failed: {import_log.libraries_failed}")
        logger.info(f"Total commands imported: {import_log.commands_imported}")
        logger.info(f"Duration: {import_log.duration_seconds} seconds")

        if import_log.error_message:
            logger.error(f"Error: {import_log.error_message}")

    except Exception as e:
        logger.error(f"Import failed: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()