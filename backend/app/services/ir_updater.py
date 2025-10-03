import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import aiohttp
from sqlalchemy.orm import Session

from ..models.ir_codes import IRImportLog
from ..db.database import get_db
from .ir_import import FlipperIRDBImporter

logger = logging.getLogger(__name__)


class IRCodeUpdater:
    """Check for and import updates from IR code repositories"""

    def __init__(self, db: Session):
        self.db = db

    async def check_for_updates(self) -> Optional[IRImportLog]:
        """Check if repository has updates and import if needed"""

        # Check when we last imported
        latest_import = (
            self.db.query(IRImportLog)
            .filter_by(source="flipper-irdb", status="completed")
            .order_by(IRImportLog.created_at.desc())
            .first()
        )

        # If never imported, do full import
        if not latest_import:
            logger.info("No previous import found, starting full import")
            return await self._do_full_import()

        # Check if we should check for updates (daily)
        time_since_last = datetime.now(timezone.utc) - latest_import.created_at
        if time_since_last < timedelta(days=1):
            logger.debug("Too soon since last import, skipping update check")
            return None

        # Check repository for updates
        repo_updated = await self._check_repository_updated(latest_import.source_commit)

        if repo_updated:
            logger.info("Repository has updates, starting incremental import")
            return await self._do_incremental_import()
        else:
            logger.debug("No repository updates found")
            return None

    async def _check_repository_updated(self, last_commit: Optional[str]) -> bool:
        """Check if the repository has new commits since last import"""

        try:
            async with aiohttp.ClientSession() as session:
                # Get latest commit from GitHub API
                url = "https://api.github.com/repos/Lucaslhm/Flipper-IRDB/commits/main"
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to check repository updates: {response.status}")
                        return False

                    data = await response.json()
                    latest_commit = data['sha']

                    # If we don't have a previous commit, assume updates
                    if not last_commit:
                        return True

                    # Check if commit is different
                    return latest_commit != last_commit

        except Exception as e:
            logger.error(f"Error checking repository updates: {str(e)}")
            return False

    async def _do_full_import(self) -> IRImportLog:
        """Perform full import of all IR codes"""

        async with FlipperIRDBImporter(self.db) as importer:
            return await importer.import_all_codes()

    async def _do_incremental_import(self) -> IRImportLog:
        """Perform incremental import (currently same as full import)"""

        # For now, incremental = full import since we need to check all files
        # In the future, we could optimize this by tracking file modification times
        async with FlipperIRDBImporter(self.db) as importer:
            import_log = await importer.import_all_codes()
            import_log.import_type = "incremental"
            self.db.commit()
            return import_log

    async def force_update(self) -> IRImportLog:
        """Force a full update regardless of timing"""

        logger.info("Starting forced IR code update")
        return await self._do_full_import()


# Scheduled update function
async def scheduled_ir_update():
    """Function to be called by scheduler for automatic updates"""

    logger.info("Starting scheduled IR code update check")

    try:
        # Get database session
        db = next(get_db())

        updater = IRCodeUpdater(db)
        result = await updater.check_for_updates()

        if result:
            logger.info(f"Scheduled update completed: {result.libraries_imported} libraries imported")
        else:
            logger.debug("No updates needed")

    except Exception as e:
        logger.error(f"Scheduled update failed: {str(e)}")

    finally:
        db.close()


# Manual update function for API endpoints
async def manual_ir_update(db: Session) -> IRImportLog:
    """Manually trigger IR code update"""

    updater = IRCodeUpdater(db)
    return await updater.force_update()


# Sync wrapper
def manual_ir_update_sync(db: Session) -> IRImportLog:
    """Synchronous wrapper for manual update"""
    return asyncio.run(manual_ir_update(db))