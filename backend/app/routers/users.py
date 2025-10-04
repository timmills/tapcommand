"""
User Management Router

Provides endpoints for managing users:
- List users (with search and filtering)
- Create new users
- Get user details
- Update user profile
- Delete users
- Reset user password (admin)
- Activate/deactivate users
- Assign/remove roles

NOTE: These endpoints are standalone and do NOT enforce authentication
on other parts of the application yet. In the future, these will require
authentication and proper permissions.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

from ..db.database import get_db
from ..models.auth import User, Role, UserRole, UserSession
from ..core.security import (
    hash_password,
    validate_password_strength
)
from ..services.audit import audit_service
from ..routers.auth import get_current_user_from_token, RoleResponse

router = APIRouter(prefix="/users", tags=["User Management"])


# ==================== Pydantic Models ====================

class UserCreateRequest(BaseModel):
    """Request model for creating a new user"""
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    is_active: bool = True
    must_change_password: bool = True
    role_ids: List[int] = []

    class Config:
        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "email": "john@example.com",
                "password": "SecurePass123!",
                "full_name": "John Doe",
                "is_active": True,
                "must_change_password": True,
                "role_ids": [2]  # Assign Viewer role
            }
        }


class UserUpdateRequest(BaseModel):
    """Request model for updating a user"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "email": "newemail@example.com",
                "full_name": "John Doe Updated",
                "is_active": True
            }
        }


class PasswordResetRequest(BaseModel):
    """Request model for admin password reset"""
    new_password: str
    must_change_password: bool = True


class UserResponse(BaseModel):
    """Response model for user details"""
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    must_change_password: bool
    roles: List[RoleResponse] = []
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Response model for user list"""
    total: int
    users: List[UserResponse]


class AssignRoleRequest(BaseModel):
    """Request model for assigning a role to a user"""
    role_id: int
    expires_at: Optional[datetime] = None


# ==================== Endpoints ====================

@router.get("", response_model=UserListResponse, status_code=status.HTTP_200_OK)
def list_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
    search: Optional[str] = Query(None, description="Search by username, email, or full name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_superuser: Optional[bool] = Query(None, description="Filter by superuser status"),
    role_id: Optional[int] = Query(None, description="Filter by role ID"),
    current_user: Optional[User] = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """
    List all users with optional filtering and search.

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **search**: Search term for username, email, or full name
    - **is_active**: Filter by active status
    - **is_superuser**: Filter by superuser status
    - **role_id**: Filter by assigned role ID
    """
    query = db.query(User)

    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                User.username.ilike(search_term),
                User.email.ilike(search_term),
                User.full_name.ilike(search_term)
            )
        )

    # Apply status filters
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    if is_superuser is not None:
        query = query.filter(User.is_superuser == is_superuser)

    # Apply role filter
    if role_id is not None:
        query = query.join(UserRole).filter(UserRole.role_id == role_id)

    # Get total count
    total = query.count()

    # Apply pagination and get results
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()

    # Build response with roles
    user_responses = []
    for user in users:
        user_roles = db.query(Role).join(UserRole).filter(
            UserRole.user_id == user.id
        ).all()

        user_responses.append(UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            must_change_password=user.must_change_password,
            roles=[RoleResponse.model_validate(role) for role in user_roles],
            last_login=user.last_login,
            created_at=user.created_at,
            updated_at=user.updated_at,
            failed_login_attempts=user.failed_login_attempts,
            locked_until=user.locked_until
        ))

    return UserListResponse(
        total=total,
        users=user_responses
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreateRequest,
    current_user: Optional[User] = Depends(get_current_user_from_token),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Create a new user.

    - **username**: Unique username (min 3 characters)
    - **email**: Unique email address
    - **password**: Password (must meet strength requirements)
    - **full_name**: Full name (optional)
    - **is_active**: Whether the account is active
    - **must_change_password**: Require password change on first login
    - **role_ids**: List of role IDs to assign to the user
    """
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{user_data.username}' already exists"
        )

    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{user_data.email}' already exists"
        )

    # Validate password strength
    is_valid, error_message = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    # Validate role IDs
    if user_data.role_ids:
        roles = db.query(Role).filter(Role.id.in_(user_data.role_ids)).all()
        if len(roles) != len(user_data.role_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more role IDs are invalid"
            )

    # Create user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
        is_active=user_data.is_active,
        must_change_password=user_data.must_change_password,
        password_changed_at=datetime.utcnow(),
        created_by=current_user.id if current_user else None
    )
    db.add(new_user)
    db.flush()  # Get the user ID

    # Assign roles
    for role_id in user_data.role_ids:
        user_role = UserRole(
            user_id=new_user.id,
            role_id=role_id,
            assigned_by=current_user.id if current_user else None
        )
        db.add(user_role)

    db.commit()
    db.refresh(new_user)

    # Log user creation
    audit_service.log_action(
        db=db,
        user=current_user,
        action=audit_service.ACTION_TYPES['USER_CREATE'],
        resource_type='user',
        resource_id=new_user.id,
        resource_name=new_user.username,
        new_values={
            'username': new_user.username,
            'email': new_user.email,
            'is_active': new_user.is_active,
            'role_ids': user_data.role_ids
        },
        request=request
    )

    # Get roles for response
    user_roles = db.query(Role).join(UserRole).filter(
        UserRole.user_id == new_user.id
    ).all()

    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        full_name=new_user.full_name,
        is_active=new_user.is_active,
        is_superuser=new_user.is_superuser,
        must_change_password=new_user.must_change_password,
        roles=[RoleResponse.model_validate(role) for role in user_roles],
        last_login=new_user.last_login,
        created_at=new_user.created_at,
        updated_at=new_user.updated_at,
        failed_login_attempts=new_user.failed_login_attempts,
        locked_until=new_user.locked_until
    )


@router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_user(
    user_id: int,
    current_user: Optional[User] = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Get user details by ID.

    - **user_id**: User ID
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    # Get user's roles
    user_roles = db.query(Role).join(UserRole).filter(
        UserRole.user_id == user.id
    ).all()

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        must_change_password=user.must_change_password,
        roles=[RoleResponse.model_validate(role) for role in user_roles],
        last_login=user.last_login,
        created_at=user.created_at,
        updated_at=user.updated_at,
        failed_login_attempts=user.failed_login_attempts,
        locked_until=user.locked_until
    )


@router.patch("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def update_user(
    user_id: int,
    user_data: UserUpdateRequest,
    current_user: Optional[User] = Depends(get_current_user_from_token),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Update user details.

    - **user_id**: User ID
    - **email**: New email address (optional)
    - **full_name**: New full name (optional)
    - **is_active**: New active status (optional)
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    # Track old values for audit log
    old_values = {
        'email': user.email,
        'full_name': user.full_name,
        'is_active': user.is_active
    }

    # Check if new email already exists
    if user_data.email and user_data.email != user.email:
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{user_data.email}' already exists"
            )
        user.email = user_data.email

    # Update fields
    if user_data.full_name is not None:
        user.full_name = user_data.full_name

    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    # Track new values for audit log
    new_values = {
        'email': user.email,
        'full_name': user.full_name,
        'is_active': user.is_active
    }

    # Log user update
    audit_service.log_action(
        db=db,
        user=current_user,
        action=audit_service.ACTION_TYPES['USER_EDIT'],
        resource_type='user',
        resource_id=user.id,
        resource_name=user.username,
        old_values=old_values,
        new_values=new_values,
        request=request
    )

    # Get user's roles for response
    user_roles = db.query(Role).join(UserRole).filter(
        UserRole.user_id == user.id
    ).all()

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        must_change_password=user.must_change_password,
        roles=[RoleResponse.model_validate(role) for role in user_roles],
        last_login=user.last_login,
        created_at=user.created_at,
        updated_at=user.updated_at,
        failed_login_attempts=user.failed_login_attempts,
        locked_until=user.locked_until
    )


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(
    user_id: int,
    current_user: Optional[User] = Depends(get_current_user_from_token),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Delete a user.

    - **user_id**: User ID to delete

    Note: Cannot delete your own account or system admin account.
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    # Prevent deleting yourself
    if current_user and user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    # Prevent deleting the default admin user
    if user.username == 'admin' and user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the system admin account"
        )

    # Store username for audit log
    username = user.username

    # Delete user (cascade will delete related records)
    db.delete(user)
    db.commit()

    # Log user deletion
    audit_service.log_action(
        db=db,
        user=current_user,
        action=audit_service.ACTION_TYPES['USER_DELETE'],
        resource_type='user',
        resource_id=user_id,
        resource_name=username,
        request=request
    )

    return {"message": f"User '{username}' deleted successfully"}


@router.post("/{user_id}/reset-password", status_code=status.HTTP_200_OK)
def reset_user_password(
    user_id: int,
    password_data: PasswordResetRequest,
    current_user: Optional[User] = Depends(get_current_user_from_token),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Reset a user's password (admin function).

    - **user_id**: User ID
    - **new_password**: New password for the user
    - **must_change_password**: Require password change on next login
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    # Validate password strength
    is_valid, error_message = validate_password_strength(password_data.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    # Reset password
    user.password_hash = hash_password(password_data.new_password)
    user.password_changed_at = datetime.utcnow()
    user.must_change_password = password_data.must_change_password
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    # Log password reset
    audit_service.log_authentication_event(
        db=db,
        username=user.username,
        action=audit_service.ACTION_TYPES['AUTH_PASSWORD_RESET'],
        success=True,
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
        details={'reset_by': current_user.username if current_user else 'system'}
    )

    return {"message": f"Password reset successfully for user '{user.username}'"}


@router.post("/{user_id}/activate", status_code=status.HTTP_200_OK)
def activate_user(
    user_id: int,
    current_user: Optional[User] = Depends(get_current_user_from_token),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Activate a user account.

    - **user_id**: User ID to activate
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{user.username}' is already active"
        )

    user.is_active = True
    user.updated_at = datetime.utcnow()
    db.commit()

    # Log user activation
    audit_service.log_action(
        db=db,
        user=current_user,
        action=audit_service.ACTION_TYPES['USER_ACTIVATE'],
        resource_type='user',
        resource_id=user.id,
        resource_name=user.username,
        request=request
    )

    return {"message": f"User '{user.username}' activated successfully"}


@router.post("/{user_id}/deactivate", status_code=status.HTTP_200_OK)
def deactivate_user(
    user_id: int,
    current_user: Optional[User] = Depends(get_current_user_from_token),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Deactivate a user account.

    - **user_id**: User ID to deactivate

    Note: Cannot deactivate your own account or system admin account.
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    # Prevent deactivating yourself
    if current_user and user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )

    # Prevent deactivating the default admin user
    if user.username == 'admin' and user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate the system admin account"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{user.username}' is already inactive"
        )

    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.commit()

    # Revoke all active sessions
    db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.is_revoked == False
    ).update({
        'is_revoked': True,
        'revoked_at': datetime.utcnow(),
        'revoked_by': current_user.id if current_user else None
    })
    db.commit()

    # Log user deactivation
    audit_service.log_action(
        db=db,
        user=current_user,
        action=audit_service.ACTION_TYPES['USER_DEACTIVATE'],
        resource_type='user',
        resource_id=user.id,
        resource_name=user.username,
        request=request
    )

    return {"message": f"User '{user.username}' deactivated successfully"}


@router.post("/{user_id}/roles", status_code=status.HTTP_200_OK)
def assign_role_to_user(
    user_id: int,
    role_data: AssignRoleRequest,
    current_user: Optional[User] = Depends(get_current_user_from_token),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Assign a role to a user.

    - **user_id**: User ID
    - **role_id**: Role ID to assign
    - **expires_at**: Optional expiration date for temporary role assignment
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    role = db.query(Role).filter(Role.id == role_data.role_id).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_data.role_id} not found"
        )

    # Check if user already has this role
    existing = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == role_data.role_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{user.username}' already has role '{role.name}'"
        )

    # Assign role
    user_role = UserRole(
        user_id=user_id,
        role_id=role_data.role_id,
        assigned_by=current_user.id if current_user else None,
        expires_at=role_data.expires_at
    )
    db.add(user_role)
    db.commit()

    # Log role assignment
    audit_service.log_permission_change(
        db=db,
        user=current_user,
        action=audit_service.ACTION_TYPES['USER_ROLE_ASSIGN'],
        target_user_id=user.id,
        target_username=user.username,
        role_name=role.name,
        request=request
    )

    return {"message": f"Role '{role.name}' assigned to user '{user.username}' successfully"}


@router.delete("/{user_id}/roles/{role_id}", status_code=status.HTTP_200_OK)
def remove_role_from_user(
    user_id: int,
    role_id: int,
    current_user: Optional[User] = Depends(get_current_user_from_token),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Remove a role from a user.

    - **user_id**: User ID
    - **role_id**: Role ID to remove
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    role = db.query(Role).filter(Role.id == role_id).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found"
        )

    # Check if user has this role
    user_role = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == role_id
    ).first()

    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{user.username}' does not have role '{role.name}'"
        )

    # Remove role
    db.delete(user_role)
    db.commit()

    # Log role removal
    audit_service.log_permission_change(
        db=db,
        user=current_user,
        action=audit_service.ACTION_TYPES['USER_ROLE_REMOVE'],
        target_user_id=user.id,
        target_username=user.username,
        role_name=role.name,
        request=request
    )

    return {"message": f"Role '{role.name}' removed from user '{user.username}' successfully"}


# Export
__all__ = ['router']
