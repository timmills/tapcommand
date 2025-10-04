"""
Audit Logging Service

Provides comprehensive audit logging for all user actions in SmartVenue.
Logs authentication events, resource modifications, permission changes, and errors.

This is a standalone service that can be used by endpoints but is NOT
automatically applied to all endpoints yet.

Usage:
    from app.services.audit import audit_service

    # Log a successful action
    audit_service.log_action(
        db=db,
        user=current_user,
        action="device.edit",
        resource_type="device",
        resource_id=device_id,
        resource_name=device_name,
        old_values={"channel": 10},
        new_values={"channel": 15},
        request=request
    )

    # Log a failed action
    audit_service.log_failed_action(
        db=db,
        user=current_user,
        action="device.delete",
        resource_type="device",
        resource_id=device_id,
        error_message="Permission denied",
        request=request
    )
"""

import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import Request

from ..models.auth import User, AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """
    Service for logging user actions to the audit log.

    Provides methods to log successful actions, failed actions, authentication events,
    and automatically captures request metadata.
    """

    # Action types for common operations
    ACTION_TYPES = {
        # Authentication
        'AUTH_LOGIN': 'auth.login',
        'AUTH_LOGOUT': 'auth.logout',
        'AUTH_FAILED': 'auth.failed',
        'AUTH_LOCKED': 'auth.locked',
        'AUTH_PASSWORD_CHANGE': 'auth.password_change',
        'AUTH_PASSWORD_RESET': 'auth.password_reset',

        # Users
        'USER_CREATE': 'user.create',
        'USER_VIEW': 'user.view',
        'USER_EDIT': 'user.edit',
        'USER_DELETE': 'user.delete',
        'USER_ACTIVATE': 'user.activate',
        'USER_DEACTIVATE': 'user.deactivate',
        'USER_ROLE_ASSIGN': 'user.role_assign',
        'USER_ROLE_REMOVE': 'user.role_remove',

        # Roles
        'ROLE_CREATE': 'role.create',
        'ROLE_EDIT': 'role.edit',
        'ROLE_DELETE': 'role.delete',
        'ROLE_PERMISSION_ADD': 'role.permission_add',
        'ROLE_PERMISSION_REMOVE': 'role.permission_remove',

        # Devices
        'DEVICE_VIEW': 'device.view',
        'DEVICE_EDIT': 'device.edit',
        'DEVICE_CONFIGURE': 'device.configure',
        'DEVICE_DELETE': 'device.delete',
        'DEVICE_COMMAND': 'device.command',

        # IR Senders
        'IR_SENDER_ADD': 'ir_sender.add',
        'IR_SENDER_EDIT': 'ir_sender.edit',
        'IR_SENDER_CONFIGURE': 'ir_sender.configure',
        'IR_SENDER_DELETE': 'ir_sender.delete',
        'IR_SENDER_HEALTH_CHECK': 'ir_sender.health_check',

        # Templates
        'TEMPLATE_VIEW': 'template.view',
        'TEMPLATE_EDIT': 'template.edit',
        'TEMPLATE_COMPILE': 'template.compile',
        'TEMPLATE_DEPLOY': 'template.deploy',

        # Channels
        'CHANNEL_EDIT': 'channel.edit',
        'CHANNEL_ENABLE': 'channel.enable',
        'CHANNEL_DISABLE': 'channel.disable',
        'CHANNEL_CREATE': 'channel.create',
        'CHANNEL_DELETE': 'channel.delete',

        # Schedules
        'SCHEDULE_CREATE': 'schedule.create',
        'SCHEDULE_EDIT': 'schedule.edit',
        'SCHEDULE_DELETE': 'schedule.delete',
        'SCHEDULE_RUN': 'schedule.run',

        # Settings
        'SETTINGS_EDIT_WIFI': 'settings.edit_wifi',
        'SETTINGS_EDIT_OTA': 'settings.edit_ota',
        'SETTINGS_EDIT_API_KEY': 'settings.edit_api_key',

        # IR Capture
        'IR_CAPTURE': 'ir_capture.capture',
        'IR_SAVE': 'ir_capture.save',
        'IR_IMPORT': 'ir_capture.import',
    }

    def log_action(
        self,
        db: Session,
        user: Optional[User],
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        resource_name: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
        success: bool = True
    ) -> AuditLog:
        """
        Log a user action to the audit log.

        Args:
            db: Database session
            user: User performing the action (None for anonymous actions)
            action: Action type (e.g., "device.edit", "user.create")
            resource_type: Type of resource (e.g., "device", "user")
            resource_id: ID of the resource affected
            resource_name: Human-readable resource identifier
            old_values: Previous state of the resource (as dict)
            new_values: New state of the resource (as dict)
            details: Additional context (as dict)
            request: FastAPI request object for metadata
            success: Whether the action succeeded

        Returns:
            Created AuditLog entry
        """
        try:
            # Create audit log entry
            audit_entry = AuditLog(
                user_id=user.id if user else None,
                username=user.username if user else 'anonymous',
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name=resource_name,
                old_values=json.dumps(old_values) if old_values else None,
                new_values=json.dumps(new_values) if new_values else None,
                details=json.dumps(details) if details else None,
                ip_address=request.client.host if request and request.client else None,
                user_agent=request.headers.get('user-agent') if request else None,
                success=success,
                timestamp=datetime.utcnow()
            )

            db.add(audit_entry)
            db.commit()

            # Log to application log as well
            log_msg = f"AUDIT: {user.username if user else 'anonymous'} - {action}"
            if resource_name:
                log_msg += f" - {resource_name}"
            logger.info(log_msg)

            return audit_entry

        except Exception as e:
            logger.error(f"Failed to create audit log entry: {e}")
            db.rollback()
            raise

    def log_failed_action(
        self,
        db: Session,
        user: Optional[User],
        action: str,
        error_message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        resource_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ) -> AuditLog:
        """
        Log a failed action attempt.

        Args:
            db: Database session
            user: User attempting the action
            action: Action type that was attempted
            error_message: Error message describing the failure
            resource_type: Type of resource
            resource_id: ID of the resource
            resource_name: Human-readable resource identifier
            details: Additional context
            request: FastAPI request object

        Returns:
            Created AuditLog entry
        """
        return self.log_action(
            db=db,
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            details=details,
            request=request,
            success=False
        )

    def log_authentication_event(
        self,
        db: Session,
        username: str,
        action: str,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log an authentication-related event (login, logout, failed login, etc.).

        Args:
            db: Database session
            username: Username attempting authentication
            action: Action type (e.g., "auth.login", "auth.failed")
            success: Whether the authentication succeeded
            ip_address: IP address of the request
            user_agent: User agent string
            error_message: Error message if failed
            details: Additional context

        Returns:
            Created AuditLog entry
        """
        try:
            # Get user if they exist
            user = db.query(User).filter_by(username=username).first()

            # Create audit log entry
            audit_entry = AuditLog(
                user_id=user.id if user else None,
                username=username,
                action=action,
                resource_type='auth',
                success=success,
                error_message=error_message,
                details=json.dumps(details) if details else None,
                ip_address=ip_address,
                user_agent=user_agent,
                timestamp=datetime.utcnow()
            )

            db.add(audit_entry)
            db.commit()

            # Log to application log
            status = "SUCCESS" if success else "FAILED"
            log_msg = f"AUDIT: {username} - {action} - {status}"
            if error_message:
                log_msg += f" - {error_message}"

            if success:
                logger.info(log_msg)
            else:
                logger.warning(log_msg)

            return audit_entry

        except Exception as e:
            logger.error(f"Failed to create audit log entry for authentication: {e}")
            db.rollback()
            raise

    def log_permission_change(
        self,
        db: Session,
        user: User,
        action: str,
        target_user_id: Optional[int] = None,
        target_username: Optional[str] = None,
        role_name: Optional[str] = None,
        permission_string: Optional[str] = None,
        request: Optional[Request] = None
    ) -> AuditLog:
        """
        Log a permission or role change.

        Args:
            db: Database session
            user: User making the change
            action: Action type (e.g., "user.role_assign", "role.permission_add")
            target_user_id: ID of user affected
            target_username: Username of user affected
            role_name: Name of role involved
            permission_string: Permission string (e.g., "devices:edit")
            request: FastAPI request object

        Returns:
            Created AuditLog entry
        """
        details = {
            'target_user_id': target_user_id,
            'target_username': target_username,
            'role_name': role_name,
            'permission': permission_string
        }

        resource_name = target_username or role_name

        return self.log_action(
            db=db,
            user=user,
            action=action,
            resource_type='permission',
            resource_name=resource_name,
            details=details,
            request=request
        )

    def log_resource_modification(
        self,
        db: Session,
        user: User,
        action: str,
        resource_type: str,
        resource_id: int,
        resource_name: str,
        old_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ) -> AuditLog:
        """
        Log a resource modification (create, update, delete).

        Args:
            db: Database session
            user: User making the modification
            action: Action type (e.g., "device.edit", "schedule.create")
            resource_type: Type of resource (e.g., "device", "schedule")
            resource_id: ID of the resource
            resource_name: Human-readable resource name
            old_state: Previous state before modification
            new_state: New state after modification
            request: FastAPI request object

        Returns:
            Created AuditLog entry
        """
        return self.log_action(
            db=db,
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            old_values=old_state,
            new_values=new_state,
            request=request
        )

    def get_user_activity(
        self,
        db: Session,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        limit: int = 100
    ) -> list[AuditLog]:
        """
        Get recent activity for a specific user.

        Args:
            db: Database session
            user_id: User ID to filter by
            username: Username to filter by
            limit: Maximum number of entries to return

        Returns:
            List of AuditLog entries
        """
        query = db.query(AuditLog)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        elif username:
            query = query.filter(AuditLog.username == username)

        return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

    def get_resource_history(
        self,
        db: Session,
        resource_type: str,
        resource_id: int,
        limit: int = 100
    ) -> list[AuditLog]:
        """
        Get change history for a specific resource.

        Args:
            db: Database session
            resource_type: Type of resource (e.g., "device", "user")
            resource_id: ID of the resource
            limit: Maximum number of entries to return

        Returns:
            List of AuditLog entries
        """
        return db.query(AuditLog).filter(
            AuditLog.resource_type == resource_type,
            AuditLog.resource_id == resource_id
        ).order_by(AuditLog.timestamp.desc()).limit(limit).all()

    def get_failed_actions(
        self,
        db: Session,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        hours: int = 24,
        limit: int = 100
    ) -> list[AuditLog]:
        """
        Get recent failed actions for security monitoring.

        Args:
            db: Database session
            user_id: Filter by specific user
            action: Filter by action type
            hours: Number of hours to look back
            limit: Maximum number of entries to return

        Returns:
            List of failed AuditLog entries
        """
        from datetime import timedelta

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        query = db.query(AuditLog).filter(
            AuditLog.success == False,
            AuditLog.timestamp >= cutoff_time
        )

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        if action:
            query = query.filter(AuditLog.action == action)

        return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

    def cleanup_old_logs(
        self,
        db: Session,
        days_to_keep: int = 90
    ) -> int:
        """
        Clean up old audit log entries.

        Args:
            db: Database session
            days_to_keep: Number of days of logs to retain

        Returns:
            Number of entries deleted
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        deleted_count = db.query(AuditLog).filter(
            AuditLog.timestamp < cutoff_date
        ).delete()

        db.commit()

        logger.info(f"Cleaned up {deleted_count} audit log entries older than {days_to_keep} days")

        return deleted_count


# Global instance
audit_service = AuditService()


# Export
__all__ = ['audit_service', 'AuditService']
