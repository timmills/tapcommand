"""
Database backup service with rotation strategy.

Implements a Grandfather-Father-Son (GFS) backup rotation:
- Daily: Keep last 7 days
- Weekly: Keep last 4 weeks (from Sunday's backup)
- Monthly: Keep last 6 months (from last day of month)
"""

import sqlite3
import shutil
import gzip
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ..core.config import settings
from .database_report_service import DatabaseReportService

logger = logging.getLogger(__name__)

# Backup configuration
BACKUP_ROOT = Path("/home/coastal/tapcommand/backups")
BACKUP_DAILY_DIR = BACKUP_ROOT / "daily"
BACKUP_WEEKLY_DIR = BACKUP_ROOT / "weekly"
BACKUP_MONTHLY_DIR = BACKUP_ROOT / "monthly"
METADATA_FILE = BACKUP_ROOT / ".backup_metadata.json"

# Retention policies
DAILY_RETENTION_DAYS = 14
WEEKLY_RETENTION_WEEKS = 4
MONTHLY_RETENTION_MONTHS = 6

# Disk space thresholds
DISK_WARNING_THRESHOLD = 0.80  # 80% usage
DISK_CRITICAL_THRESHOLD = 0.90  # 90% usage
BACKUP_FOLDER_MAX_SIZE_GB = 1.0  # 1GB max for backup folder


class BackupMetadata:
    """Manages backup metadata storage."""

    def __init__(self):
        self.metadata_file = METADATA_FILE
        self._ensure_metadata_file()

    def _ensure_metadata_file(self):
        """Ensure metadata file exists."""
        if not self.metadata_file.exists():
            self._write_metadata({
                "last_daily_backup": None,
                "last_weekly_backup": None,
                "last_monthly_backup": None,
                "backups": [],
                "disk_alerts": []
            })

    def _read_metadata(self) -> dict:
        """Read metadata from file."""
        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading metadata: {e}")
            return {
                "last_daily_backup": None,
                "last_weekly_backup": None,
                "last_monthly_backup": None,
                "backups": [],
                "disk_alerts": []
            }

    def _write_metadata(self, data: dict):
        """Write metadata to file."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing metadata: {e}")

    def add_backup(self, backup_type: str, filename: str, size_bytes: int):
        """Add a backup record to metadata."""
        metadata = self._read_metadata()
        metadata["backups"].append({
            "type": backup_type,
            "filename": filename,
            "created_at": datetime.now().isoformat(),
            "size_bytes": size_bytes
        })

        # Update last backup timestamps
        if backup_type == "daily":
            metadata["last_daily_backup"] = datetime.now().isoformat()
        elif backup_type == "weekly":
            metadata["last_weekly_backup"] = datetime.now().isoformat()
        elif backup_type == "monthly":
            metadata["last_monthly_backup"] = datetime.now().isoformat()

        self._write_metadata(metadata)

    def remove_backup(self, filename: str):
        """Remove a backup record from metadata."""
        metadata = self._read_metadata()
        metadata["backups"] = [b for b in metadata["backups"] if b["filename"] != filename]
        self._write_metadata(metadata)

    def get_all_backups(self) -> List[dict]:
        """Get all backup records."""
        metadata = self._read_metadata()
        return metadata.get("backups", [])

    def get_last_backup_time(self, backup_type: str) -> Optional[datetime]:
        """Get the last backup time for a specific type."""
        metadata = self._read_metadata()
        key = f"last_{backup_type}_backup"
        timestamp = metadata.get(key)
        if timestamp:
            return datetime.fromisoformat(timestamp)
        return None

    def add_disk_alert(self, alert_type: str, message: str):
        """Add a disk space alert."""
        metadata = self._read_metadata()
        metadata["disk_alerts"].append({
            "type": alert_type,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        # Keep only last 10 alerts
        metadata["disk_alerts"] = metadata["disk_alerts"][-10:]
        self._write_metadata(metadata)

    def get_disk_alerts(self) -> List[dict]:
        """Get recent disk alerts."""
        metadata = self._read_metadata()
        return metadata.get("disk_alerts", [])


class BackupService:
    """Service for managing database backups."""

    def __init__(self):
        self.db_path = Path(settings.SQLITE_DATABASE_PATH)
        self.metadata = BackupMetadata()
        self._ensure_backup_dirs()

    def _ensure_backup_dirs(self):
        """Ensure all backup directories exist."""
        for dir_path in [BACKUP_DAILY_DIR, BACKUP_WEEKLY_DIR, BACKUP_MONTHLY_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def get_disk_usage(self) -> Tuple[float, float, float]:
        """
        Get disk usage information.

        Returns:
            Tuple of (used_gb, total_gb, usage_percent)
        """
        import shutil
        stat = shutil.disk_usage(self.db_path.parent)
        total_gb = stat.total / (1024**3)
        used_gb = stat.used / (1024**3)
        usage_percent = stat.used / stat.total
        return used_gb, total_gb, usage_percent

    def get_backup_folder_size(self) -> float:
        """
        Get total size of backup folder in GB.

        Returns:
            Size in GB
        """
        total_size = 0
        for dir_path in [BACKUP_DAILY_DIR, BACKUP_WEEKLY_DIR, BACKUP_MONTHLY_DIR]:
            for file_path in dir_path.glob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        return total_size / (1024**3)

    def check_disk_space(self) -> Tuple[bool, Optional[str]]:
        """
        Check if there's enough disk space for backup.

        Returns:
            Tuple of (can_backup, warning_message)
        """
        used_gb, total_gb, usage_percent = self.get_disk_usage()
        backup_size = self.get_backup_folder_size()

        # Check disk usage
        if usage_percent >= DISK_CRITICAL_THRESHOLD:
            msg = f"Critical: Disk usage at {usage_percent*100:.1f}%. Backup halted."
            logger.error(msg)
            self.metadata.add_disk_alert("critical", msg)
            return False, msg

        if usage_percent >= DISK_WARNING_THRESHOLD:
            msg = f"Warning: Disk usage at {usage_percent*100:.1f}%."
            logger.warning(msg)
            self.metadata.add_disk_alert("warning", msg)

        # Check backup folder size
        if backup_size >= BACKUP_FOLDER_MAX_SIZE_GB:
            msg = f"Warning: Backup folder size {backup_size:.2f}GB exceeds limit."
            logger.warning(msg)
            self.metadata.add_disk_alert("warning", msg)

        # Need at least 2x DB size free
        db_size_gb = self.db_path.stat().st_size / (1024**3)
        free_gb = total_gb - used_gb
        if free_gb < (db_size_gb * 2):
            msg = f"Insufficient space: {free_gb:.2f}GB free, need {db_size_gb*2:.2f}GB"
            logger.error(msg)
            self.metadata.add_disk_alert("critical", msg)
            return False, msg

        return True, None

    def verify_database_integrity(self, db_file: Path) -> bool:
        """
        Verify database integrity.

        Args:
            db_file: Path to database file

        Returns:
            True if database is valid
        """
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()
            return result[0] == "ok"
        except Exception as e:
            logger.error(f"Database integrity check failed: {e}")
            return False

    def create_backup(self, backup_type: str = "manual") -> Tuple[bool, Optional[Path], Optional[str]]:
        """
        Create a database backup.

        Args:
            backup_type: Type of backup (daily, weekly, monthly, manual)

        Returns:
            Tuple of (success, backup_path, error_message)
        """
        try:
            # Check disk space
            can_backup, warning = self.check_disk_space()
            if not can_backup:
                return False, None, warning

            # Verify source database
            if not self.verify_database_integrity(self.db_path):
                msg = "Source database integrity check failed"
                logger.error(msg)
                return False, None, msg

            # Determine backup directory and filename (always .gz compressed)
            if backup_type == "daily":
                backup_dir = BACKUP_DAILY_DIR
                filename = f"tapcommand_daily_{datetime.now().strftime('%Y-%m-%d')}.db.gz"
            elif backup_type == "weekly":
                backup_dir = BACKUP_WEEKLY_DIR
                week_num = datetime.now().isocalendar()[1]
                filename = f"tapcommand_weekly_{datetime.now().strftime('%Y')}-W{week_num:02d}.db.gz"
            elif backup_type == "monthly":
                backup_dir = BACKUP_MONTHLY_DIR
                filename = f"tapcommand_monthly_{datetime.now().strftime('%Y-%m')}.db.gz"
            elif backup_type == "emergency":
                backup_dir = BACKUP_DAILY_DIR
                filename = f"tapcommand_emergency_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.db.gz"
            else:  # manual
                backup_dir = BACKUP_DAILY_DIR
                filename = f"tapcommand_manual_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.db.gz"

            # Create temporary uncompressed backup first
            temp_backup = backup_dir / filename.replace('.gz', '')

            # Perform backup using SQLite's backup API (safe for live database)
            logger.info(f"Creating {backup_type} backup: {filename}")
            source_conn = sqlite3.connect(str(self.db_path))
            backup_conn = sqlite3.connect(str(temp_backup))

            with backup_conn:
                source_conn.backup(backup_conn)

            source_conn.close()
            backup_conn.close()

            # Verify backup integrity
            if not self.verify_database_integrity(temp_backup):
                msg = "Backup integrity check failed"
                logger.error(msg)
                temp_backup.unlink()  # Delete corrupted backup
                return False, None, msg

            # Compress the backup
            backup_path = backup_dir / filename
            logger.info(f"Compressing backup: {filename}")
            with open(temp_backup, 'rb') as f_in:
                with gzip.open(backup_path, 'wb', compresslevel=6) as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Remove uncompressed temp file
            temp_backup.unlink()

            # Get compressed backup size
            backup_size = backup_path.stat().st_size

            # Generate database content report
            logger.info(f"Generating database content report for backup: {filename}")
            report_service = DatabaseReportService(self.db_path)
            report = report_service.generate_report()

            # Save report as hidden .json file alongside backup
            report_filename = f".{filename}.report.json"
            report_path = backup_dir / report_filename
            report_service.save_report(report, report_path)
            logger.info(f"Database report saved: {report_filename}")

            # Update metadata
            self.metadata.add_backup(backup_type, filename, backup_size)

            logger.info(f"Backup created successfully: {backup_path} ({backup_size / 1024**2:.2f} MB)")
            return True, backup_path, None

        except Exception as e:
            msg = f"Backup creation failed: {str(e)}"
            logger.error(msg)
            return False, None, msg

    def rotate_backups(self):
        """Remove old backups according to retention policy."""
        now = datetime.now()

        # Rotate daily backups (keep last 7 days)
        cutoff_date = now - timedelta(days=DAILY_RETENTION_DAYS)
        self._rotate_directory(BACKUP_DAILY_DIR, cutoff_date, "daily")

        # Rotate weekly backups (keep last 4 weeks)
        cutoff_date = now - timedelta(weeks=WEEKLY_RETENTION_WEEKS)
        self._rotate_directory(BACKUP_WEEKLY_DIR, cutoff_date, "weekly")

        # Rotate monthly backups (keep last 6 months)
        cutoff_date = now - timedelta(days=MONTHLY_RETENTION_MONTHS * 30)
        self._rotate_directory(BACKUP_MONTHLY_DIR, cutoff_date, "monthly")

    def _rotate_directory(self, directory: Path, cutoff_date: datetime, backup_type: str):
        """Remove backups older than cutoff date from directory."""
        for file_path in directory.glob("*.db.gz"):
            try:
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_mtime < cutoff_date:
                    logger.info(f"Removing old {backup_type} backup: {file_path.name}")
                    file_path.unlink()
                    self.metadata.remove_backup(file_path.name)
            except Exception as e:
                logger.error(f"Error removing old backup {file_path}: {e}")


    def get_all_backups(self) -> List[dict]:
        """
        Get list of all available backups with details.

        Returns:
            List of backup information dictionaries
        """
        backups = []
        report_service = DatabaseReportService(self.db_path)

        for backup_type, backup_dir in [
            ("daily", BACKUP_DAILY_DIR),
            ("weekly", BACKUP_WEEKLY_DIR),
            ("monthly", BACKUP_MONTHLY_DIR)
        ]:
            # Only look for .db.gz files now
            for file_path in sorted(backup_dir.glob("*.db.gz"), reverse=True):
                try:
                    stat = file_path.stat()

                    # Try to load associated report
                    report_path = backup_dir / f".{file_path.name}.report.json"
                    report = report_service.load_report(report_path)

                    backup_info = {
                        "type": backup_type,
                        "filename": file_path.name,
                        "path": str(file_path),
                        "size_bytes": stat.st_size,
                        "size_mb": stat.st_size / (1024**2),
                        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "is_compressed": True,  # All backups are now compressed
                        "has_report": report is not None
                    }

                    # Add report summary if available
                    if report:
                        backup_info["report_summary"] = report_service.generate_human_readable_summary(report)
                        backup_info["report"] = report

                    backups.append(backup_info)
                except Exception as e:
                    logger.error(f"Error reading backup file {file_path}: {e}")

        return backups

    def delete_backup(self, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Delete a specific backup file and its associated report.

        Args:
            filename: Name of the backup file

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Search for file in all backup directories
            for backup_dir in [BACKUP_DAILY_DIR, BACKUP_WEEKLY_DIR, BACKUP_MONTHLY_DIR]:
                file_path = backup_dir / filename
                if file_path.exists():
                    logger.info(f"Deleting backup: {filename}")
                    file_path.unlink()

                    # Also delete associated report file if it exists
                    report_path = backup_dir / f".{filename}.report.json"
                    if report_path.exists():
                        report_path.unlink()
                        logger.info(f"Deleted associated report: {report_path.name}")

                    self.metadata.remove_backup(filename)
                    return True, None

            return False, f"Backup file not found: {filename}"

        except Exception as e:
            msg = f"Error deleting backup: {str(e)}"
            logger.error(msg)
            return False, msg

    def get_backup_status(self) -> dict:
        """
        Get overall backup system status.

        Returns:
            Dictionary with status information
        """
        used_gb, total_gb, usage_percent = self.get_disk_usage()
        backup_size_gb = self.get_backup_folder_size()

        return {
            "disk_usage": {
                "used_gb": round(used_gb, 2),
                "total_gb": round(total_gb, 2),
                "usage_percent": round(usage_percent * 100, 1),
                "free_gb": round(total_gb - used_gb, 2)
            },
            "backup_folder_size_gb": round(backup_size_gb, 2),
            "backup_folder_max_gb": BACKUP_FOLDER_MAX_SIZE_GB,
            "last_daily_backup": self.metadata.get_last_backup_time("daily").isoformat() if self.metadata.get_last_backup_time("daily") else None,
            "last_weekly_backup": self.metadata.get_last_backup_time("weekly").isoformat() if self.metadata.get_last_backup_time("weekly") else None,
            "last_monthly_backup": self.metadata.get_last_backup_time("monthly").isoformat() if self.metadata.get_last_backup_time("monthly") else None,
            "total_backups": len(self.get_all_backups()),
            "disk_alerts": self.metadata.get_disk_alerts(),
            "warnings": self._get_warnings(usage_percent, backup_size_gb)
        }

    def _get_warnings(self, usage_percent: float, backup_size_gb: float) -> List[str]:
        """Generate warning messages based on current status."""
        warnings = []

        if usage_percent >= DISK_CRITICAL_THRESHOLD:
            warnings.append(f"CRITICAL: Disk usage at {usage_percent*100:.1f}%. Backups are halted.")
        elif usage_percent >= DISK_WARNING_THRESHOLD:
            warnings.append(f"WARNING: Disk usage at {usage_percent*100:.1f}%.")

        if backup_size_gb >= BACKUP_FOLDER_MAX_SIZE_GB:
            warnings.append(f"WARNING: Backup folder size {backup_size_gb:.2f}GB exceeds recommended limit.")

        return warnings

    def upload_backup(self, file_content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Upload a backup file to the backup directory.

        Args:
            file_content: Binary content of the backup file
            filename: Name of the backup file (.db.gz only)

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Validate filename - only accept compressed backups
            if not filename.endswith('.db.gz'):
                return False, "Invalid file type. Only .db.gz compressed backup files are allowed."

            # Determine backup directory (uploaded files go to daily)
            backup_path = BACKUP_DAILY_DIR / filename

            # Check if file already exists
            if backup_path.exists():
                return False, f"Backup file {filename} already exists."

            # Write compressed file
            logger.info(f"Uploading compressed backup: {filename}")
            with open(backup_path, 'wb') as f:
                f.write(file_content)

            # Verify integrity by decompressing and checking
            temp_file = BACKUP_DAILY_DIR / f"temp_verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            try:
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(temp_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)

                # Verify decompressed database
                if not self.verify_database_integrity(temp_file):
                    temp_file.unlink()
                    backup_path.unlink()
                    return False, "Uploaded file failed integrity check. Not a valid compressed SQLite database."

                # Clean up temp file
                temp_file.unlink()

            except gzip.BadGzipFile:
                if temp_file.exists():
                    temp_file.unlink()
                backup_path.unlink()
                return False, "Invalid gzip file. File is not properly compressed."

            # Get file size and update metadata
            file_size = backup_path.stat().st_size
            self.metadata.add_backup("uploaded", filename, file_size)

            logger.info(f"Backup uploaded successfully: {filename} ({file_size / 1024**2:.2f} MB)")
            return True, None

        except Exception as e:
            msg = f"Error uploading backup: {str(e)}"
            logger.error(msg)
            return False, msg

    def restore_backup(self, filename: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Restore database from a backup file.

        Creates a "just-in-case" backup before restoring.

        Args:
            filename: Name of the backup file to restore from (.db.gz)

        Returns:
            Tuple of (success, emergency_backup_filename, error_message)
        """
        try:
            # Find the backup file
            backup_file = None
            for backup_dir in [BACKUP_DAILY_DIR, BACKUP_WEEKLY_DIR, BACKUP_MONTHLY_DIR]:
                potential_path = backup_dir / filename
                if potential_path.exists():
                    backup_file = potential_path
                    break

            if not backup_file:
                return False, None, f"Backup file not found: {filename}"

            # All backups are compressed - decompress to temp file
            logger.info(f"Decompressing backup: {filename}")
            temp_file = BACKUP_DAILY_DIR / f"temp_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

            with gzip.open(backup_file, 'rb') as f_in:
                with open(temp_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Verify backup integrity
            if not self.verify_database_integrity(temp_file):
                temp_file.unlink()  # Clean up temp file
                return False, None, "Backup file failed integrity check. Cannot restore from corrupted backup."

            # Create "just-in-case" emergency backup before restore (compressed)
            logger.info("Creating emergency 'just-in-case' backup before restore...")
            success, emergency_path, error = self.create_backup("emergency")

            if not success:
                temp_file.unlink()
                return False, None, f"Failed to create emergency backup: {error}"

            emergency_filename = emergency_path.name if emergency_path else None

            # Perform restore - copy decompressed backup over current database
            logger.info(f"Restoring database from: {filename}")
            shutil.copy2(temp_file, self.db_path)

            # Clean up temp file
            temp_file.unlink()

            # Verify restored database
            if not self.verify_database_integrity(self.db_path):
                logger.error("Restored database failed integrity check!")
                # Try to restore from emergency backup
                if emergency_path and emergency_path.exists():
                    with gzip.open(emergency_path, 'rb') as f_in:
                        with open(self.db_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                return False, emergency_filename, "Restored database failed integrity check. Rolled back to emergency backup."

            logger.info(f"Database successfully restored from: {filename}")
            return True, emergency_filename, None

        except Exception as e:
            msg = f"Error restoring backup: {str(e)}"
            logger.error(msg)
            return False, None, msg


# Scheduled backup task
async def scheduled_daily_backup():
    """Scheduled task to create daily backups."""
    logger.info("Running scheduled daily backup...")
    backup_service = BackupService()

    # Create daily backup
    success, backup_path, error = backup_service.create_backup("daily")
    if not success:
        logger.error(f"Scheduled daily backup failed: {error}")
        return

    # Check if we need to create weekly backup (on Sundays)
    if datetime.now().weekday() == 6:  # Sunday
        logger.info("Creating weekly backup...")
        success, backup_path, error = backup_service.create_backup("weekly")
        if not success:
            logger.error(f"Weekly backup failed: {error}")

    # Check if we need to create monthly backup (last day of month)
    tomorrow = datetime.now() + timedelta(days=1)
    if tomorrow.day == 1:  # Last day of month
        logger.info("Creating monthly backup...")
        success, backup_path, error = backup_service.create_backup("monthly")
        if not success:
            logger.error(f"Monthly backup failed: {error}")

    # Rotate old backups
    logger.info("Rotating old backups...")
    backup_service.rotate_backups()

    logger.info("Scheduled backup completed.")


def setup_backup_scheduler(scheduler: AsyncIOScheduler):
    """
    Setup scheduled backup tasks.

    Args:
        scheduler: APScheduler instance
    """
    # Schedule daily backup at 2 AM
    scheduler.add_job(
        scheduled_daily_backup,
        'cron',
        hour=2,
        minute=0,
        id='daily_backup',
        replace_existing=True
    )
    logger.info("Backup scheduler configured: Daily backups at 2:00 AM")
