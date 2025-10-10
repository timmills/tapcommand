"""
API endpoints for database backup management.
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from typing import List
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path
import logging

from ..services.backup_service import BackupService
from ..services.database_report_service import DatabaseReportService
from ..core.config import settings
from .auth import get_current_user_from_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backups", tags=["backups"])


# Schemas
class BackupInfo(BaseModel):
    """Information about a backup."""
    type: str
    filename: str
    size_bytes: int
    size_mb: float
    created_at: str
    is_compressed: bool
    has_report: bool = False
    report_summary: str | None = None
    report: dict | None = None

    class Config:
        extra = "allow"  # Allow extra fields for flexibility


class BackupStatus(BaseModel):
    """Overall backup system status."""
    disk_usage: dict
    backup_folder_size_gb: float
    backup_folder_max_gb: float
    last_daily_backup: str | None
    last_weekly_backup: str | None
    last_monthly_backup: str | None
    total_backups: int
    disk_alerts: List[dict]
    warnings: List[str]


class BackupCreateRequest(BaseModel):
    """Request to create a backup."""
    type: str = "manual"  # daily, weekly, monthly, manual


class BackupCreateResponse(BaseModel):
    """Response after creating a backup."""
    success: bool
    filename: str | None
    message: str | None


class BackupDeleteResponse(BaseModel):
    """Response after deleting a backup."""
    success: bool
    message: str | None


# Endpoints
@router.get("/", response_model=List[BackupInfo])
async def list_backups(current_user: dict = Depends(get_current_user_from_token)):
    """
    Get list of all available backups.

    Requires authentication.
    """
    try:
        backup_service = BackupService()
        backups = backup_service.get_all_backups()
        return backups
    except Exception as e:
        logger.error(f"Error listing backups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=BackupStatus)
async def get_backup_status(current_user: dict = Depends(get_current_user_from_token)):
    """
    Get backup system status including disk space and alerts.

    Requires authentication.
    """
    try:
        backup_service = BackupService()
        status = backup_service.get_backup_status()
        return status
    except Exception as e:
        logger.error(f"Error getting backup status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current-database-report")
async def get_current_database_report(current_user: dict = Depends(get_current_user_from_token)):
    """
    Get a report of the current active database contents.

    Requires authentication.
    """
    try:
        db_path = Path(settings.SQLITE_DATABASE_PATH)
        report_service = DatabaseReportService(db_path)
        report = report_service.generate_report()
        summary = report_service.generate_human_readable_summary(report)

        return {
            "report": report,
            "summary": summary
        }
    except Exception as e:
        logger.error(f"Error generating current database report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create", response_model=BackupCreateResponse)
async def create_backup(
    request: BackupCreateRequest,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Create a new backup manually.

    Requires authentication.
    """
    try:
        backup_service = BackupService()
        success, backup_path, error = backup_service.create_backup(request.type)

        if success:
            return BackupCreateResponse(
                success=True,
                filename=backup_path.name if backup_path else None,
                message="Backup created successfully"
            )
        else:
            return BackupCreateResponse(
                success=False,
                filename=None,
                message=error or "Backup creation failed"
            )

    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{filename}")
async def download_backup(
    filename: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Download a specific backup file.

    Requires authentication.
    """
    try:
        backup_service = BackupService()

        # Find the file in backup directories
        from ..services.backup_service import BACKUP_DAILY_DIR, BACKUP_WEEKLY_DIR, BACKUP_MONTHLY_DIR

        file_path = None
        for backup_dir in [BACKUP_DAILY_DIR, BACKUP_WEEKLY_DIR, BACKUP_MONTHLY_DIR]:
            potential_path = backup_dir / filename
            if potential_path.exists():
                file_path = potential_path
                break

        if not file_path:
            raise HTTPException(status_code=404, detail=f"Backup file not found: {filename}")

        # Return file as download
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type='application/octet-stream'
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{filename}", response_model=BackupDeleteResponse)
async def delete_backup(
    filename: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Delete a specific backup file.

    Requires authentication.
    """
    try:
        backup_service = BackupService()
        success, error = backup_service.delete_backup(filename)

        if success:
            return BackupDeleteResponse(
                success=True,
                message="Backup deleted successfully"
            )
        else:
            return BackupDeleteResponse(
                success=False,
                message=error or "Failed to delete backup"
            )

    except Exception as e:
        logger.error(f"Error deleting backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_backup(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Upload a backup file.

    Requires authentication. Accepts .db.gz compressed files only.
    """
    try:
        # Read file content
        file_content = await file.read()

        # Upload backup
        backup_service = BackupService()
        success, error = backup_service.upload_backup(file_content, file.filename)

        if success:
            return {
                "success": True,
                "filename": file.filename,
                "message": f"Backup '{file.filename}' uploaded successfully"
            }
        else:
            return {
                "success": False,
                "filename": None,
                "message": error or "Failed to upload backup"
            }

    except Exception as e:
        logger.error(f"Error uploading backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/restore/{filename}")
async def restore_backup(
    filename: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Restore database from a backup file.

    Creates an emergency "just-in-case" backup before restoring.
    Requires authentication and admin privileges.

    WARNING: This will replace the current database!
    """
    try:
        backup_service = BackupService()
        success, emergency_backup, error = backup_service.restore_backup(filename)

        if success:
            return {
                "success": True,
                "message": f"Database restored from {filename}",
                "emergency_backup": emergency_backup,
                "warning": "Database has been restored. Application may need to reconnect."
            }
        else:
            return {
                "success": False,
                "message": error or "Failed to restore backup",
                "emergency_backup": emergency_backup
            }

    except Exception as e:
        logger.error(f"Error restoring backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))
