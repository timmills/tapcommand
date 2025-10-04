"""
SQLAlchemy models for user management and access control.

This module defines the database models for:
- User accounts
- Roles and permissions
- Role-based access control (RBAC)
- Session tracking
- Audit logging
- Location-based restrictions
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, List
from .device import Base


class User(Base):
    """
    User account model.

    Stores user credentials, profile information, and account status.
    Supports account locking, password expiration, and session tracking.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Authentication credentials
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Profile information
    full_name = Column(String(255), nullable=True)

    # Account status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_superuser = Column(Boolean, default=False, nullable=False, index=True)

    # Password management
    must_change_password = Column(Boolean, default=False, nullable=False)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Login tracking
    last_login = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(50), nullable=True)

    # Account security
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    # Audit trail
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Relationships
    roles = relationship("UserRole", back_populates="user", foreign_keys="UserRole.user_id", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", foreign_keys="UserSession.user_id", cascade="all, delete-orphan")
    location_restrictions = relationship("UserLocationRestriction", back_populates="user", foreign_keys="UserLocationRestriction.user_id", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint('LENGTH(username) >= 3', name='username_min_length'),
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


class Role(Base):
    """
    Role model for RBAC.

    Defines user roles (e.g., Super Admin, Administrator, Operator, Viewer).
    System roles cannot be deleted. Custom roles can be created by administrators.
    """
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)

    # Role details
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # System role flag (cannot be deleted)
    is_system_role = Column(Boolean, default=False, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Audit trail
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Relationships
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    users = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}', system={self.is_system_role})>"


class Permission(Base):
    """
    Permission model.

    Defines granular permissions following the resource:action pattern.
    Examples: devices:view, devices:edit, schedules:create, users:delete
    """
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)

    # Permission definition
    resource = Column(String(50), nullable=False, index=True)  # e.g., "devices", "schedules", "users"
    action = Column(String(50), nullable=False)  # e.g., "view", "edit", "delete", "create"
    description = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    roles = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint('resource', 'action', name='unique_resource_action'),
    )

    def __repr__(self):
        return f"<Permission(id={self.id}, resource='{self.resource}', action='{self.action}')>"

    @property
    def permission_string(self) -> str:
        """Return permission in resource:action format"""
        return f"{self.resource}:{self.action}"


class RolePermission(Base):
    """
    Many-to-many relationship between Roles and Permissions.

    Tracks which permissions are granted to which roles,
    including who granted them and when.
    """
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, index=True)

    # Relationship IDs
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False, index=True)

    # Audit trail
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    granted_by = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Relationships
    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")

    # Constraints
    __table_args__ = (
        UniqueConstraint('role_id', 'permission_id', name='unique_role_permission'),
    )

    def __repr__(self):
        return f"<RolePermission(role_id={self.role_id}, permission_id={self.permission_id})>"


class UserRole(Base):
    """
    Many-to-many relationship between Users and Roles.

    Tracks which roles are assigned to which users,
    with support for temporary role assignments (expires_at).
    """
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)

    # Relationship IDs
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, index=True)

    # Audit trail
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Temporary role assignment
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Relationships
    user = relationship("User", back_populates="roles", foreign_keys=[user_id])
    role = relationship("Role", back_populates="users")

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', name='unique_user_role'),
    )

    def __repr__(self):
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"

    @property
    def is_expired(self) -> bool:
        """Check if the role assignment has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class UserLocationRestriction(Base):
    """
    Location-based access restrictions for users.

    Optional feature to restrict user access to specific locations/venues.
    If a user has restrictions, they can only access devices in those locations.
    """
    __tablename__ = "user_location_restrictions"

    id = Column(Integer, primary_key=True, index=True)

    # Relationship
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Location restriction
    location = Column(String(255), nullable=False, index=True)

    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Relationships
    user = relationship("User", back_populates="location_restrictions", foreign_keys=[user_id])

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'location', name='unique_user_location'),
    )

    def __repr__(self):
        return f"<UserLocationRestriction(user_id={self.user_id}, location='{self.location}')>"


class UserSession(Base):
    """
    User session tracking for JWT tokens.

    Tracks active sessions with support for token revocation.
    Stores both access and refresh tokens (hashed).
    """
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # User relationship
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Token hashes (never store actual tokens)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token_hash = Column(String(255), unique=True, nullable=True, index=True)

    # Token expiration
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    refresh_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Session metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Revocation support
    is_revoked = Column(Boolean, default=False, nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Relationships
    user = relationship("User", back_populates="sessions", foreign_keys=[user_id])

    # Indexes for session queries
    __table_args__ = (
        # Composite index for checking active sessions
        # Index('idx_sessions_active', 'user_id', 'is_revoked'),
    )

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, revoked={self.is_revoked})>"

    @property
    def is_expired(self) -> bool:
        """Check if the session has expired"""
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the session is valid (not revoked and not expired)"""
        return not self.is_revoked and not self.is_expired


class AuditLog(Base):
    """
    Comprehensive audit trail for all user actions.

    Logs all state-changing operations including:
    - User authentication events
    - Resource modifications (create, update, delete)
    - Permission changes
    - Failed authorization attempts
    """
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)

    # User information (denormalized for deleted users)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    username = Column(String(100), nullable=True, index=True)

    # Action details
    action = Column(String(100), nullable=False, index=True)  # e.g., "device.edit", "user.create"
    resource_type = Column(String(50), nullable=True, index=True)  # e.g., "device", "user", "role"
    resource_id = Column(Integer, nullable=True)
    resource_name = Column(String(255), nullable=True)  # Human-readable resource identifier

    # State tracking (stored as JSON strings)
    old_values = Column(Text, nullable=True)  # JSON string of previous state
    new_values = Column(Text, nullable=True)  # JSON string of new state
    details = Column(Text, nullable=True)  # Additional context (JSON string)

    # Request metadata
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Success tracking
    success = Column(Boolean, default=True, nullable=False, index=True)
    error_message = Column(Text, nullable=True)

    # Indexes for common queries
    __table_args__ = (
        # Composite index for resource queries
        # Index('idx_audit_resource', 'resource_type', 'resource_id'),
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', user='{self.username}', success={self.success})>"


# Export all models
__all__ = [
    "User",
    "Role",
    "Permission",
    "RolePermission",
    "UserRole",
    "UserLocationRestriction",
    "UserSession",
    "AuditLog",
]
