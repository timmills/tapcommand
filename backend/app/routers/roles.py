"""
Role and Permission Management Router

Provides endpoints for managing roles and permissions:
- List all roles
- Get role details with permissions
- Create new roles
- Update roles
- Delete roles
- Assign/remove permissions from roles
- List all permissions
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from ..db.database import get_db
from ..models.auth import User, Role, Permission, RolePermission
from ..services.audit import audit_service
from ..routers.auth import get_current_user_from_token

router = APIRouter(prefix="/auth/roles", tags=["Roles & Permissions"])


# ==================== Pydantic Models ====================

class PermissionResponse(BaseModel):
    """Response model for permission"""
    id: int
    resource: str
    action: str
    description: str

    class Config:
        from_attributes = True


class RoleResponse(BaseModel):
    """Response model for role"""
    id: int
    name: str
    description: Optional[str] = None
    is_system_role: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RoleWithPermissionsResponse(RoleResponse):
    """Response model for role with permissions"""
    permissions: List[PermissionResponse] = []


class RoleListResponse(BaseModel):
    """Response model for role list"""
    roles: List[RoleResponse]


class PermissionListResponse(BaseModel):
    """Response model for permission list"""
    permissions: List[PermissionResponse]


class CreateRoleRequest(BaseModel):
    """Request model for creating a role"""
    name: str
    description: Optional[str] = None
    permission_ids: List[int] = []

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Content Manager",
                "description": "Can manage templates and schedules",
                "permission_ids": [1, 2, 3]
            }
        }


class UpdateRoleRequest(BaseModel):
    """Request model for updating a role"""
    name: Optional[str] = None
    description: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Role Name",
                "description": "Updated description"
            }
        }


# ==================== Endpoints ====================

@router.get("", response_model=RoleListResponse, status_code=status.HTTP_200_OK)
def list_roles(
    current_user: Optional[User] = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """
    List all roles.

    Returns all roles in the system, including system roles and custom roles.
    """
    roles = db.query(Role).order_by(Role.name).all()

    return RoleListResponse(
        roles=[RoleResponse.model_validate(role) for role in roles]
    )


@router.get("/{role_id}", response_model=RoleWithPermissionsResponse, status_code=status.HTTP_200_OK)
def get_role(
    role_id: int,
    current_user: Optional[User] = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Get role details with permissions.

    - **role_id**: Role ID

    Returns the role information along with all assigned permissions.
    """
    role = db.query(Role).filter(Role.id == role_id).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found"
        )

    # Get role's permissions
    permissions = db.query(Permission).join(RolePermission).filter(
        RolePermission.role_id == role_id
    ).order_by(Permission.resource, Permission.action).all()

    return RoleWithPermissionsResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system_role=role.is_system_role,
        created_at=role.created_at,
        updated_at=role.updated_at,
        permissions=[PermissionResponse.model_validate(perm) for perm in permissions]
    )


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    role_data: CreateRoleRequest,
    current_user: Optional[User] = Depends(get_current_user_from_token),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Create a new role.

    - **name**: Role name (must be unique)
    - **description**: Role description (optional)
    - **permission_ids**: List of permission IDs to assign (optional)
    """
    # Check if role name already exists
    existing_role = db.query(Role).filter(Role.name == role_data.name).first()
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{role_data.name}' already exists"
        )

    # Validate permission IDs
    if role_data.permission_ids:
        permissions = db.query(Permission).filter(
            Permission.id.in_(role_data.permission_ids)
        ).all()
        if len(permissions) != len(role_data.permission_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more permission IDs are invalid"
            )

    # Create role
    new_role = Role(
        name=role_data.name,
        description=role_data.description,
        is_system_role=False
    )
    db.add(new_role)
    db.flush()  # Get the role ID

    # Assign permissions
    for permission_id in role_data.permission_ids:
        role_permission = RolePermission(
            role_id=new_role.id,
            permission_id=permission_id,
            granted_by=current_user.id if current_user else None
        )
        db.add(role_permission)

    db.commit()
    db.refresh(new_role)

    # Log role creation
    audit_service.log_action(
        db=db,
        user=current_user,
        action=audit_service.ACTION_TYPES.get('ROLE_CREATE', 'role_create'),
        resource_type='role',
        resource_id=new_role.id,
        resource_name=new_role.name,
        new_values={
            'name': new_role.name,
            'description': new_role.description,
            'permission_ids': role_data.permission_ids
        },
        request=request
    )

    return RoleResponse.model_validate(new_role)


@router.patch("/{role_id}", response_model=RoleResponse, status_code=status.HTTP_200_OK)
def update_role(
    role_id: int,
    role_data: UpdateRoleRequest,
    current_user: Optional[User] = Depends(get_current_user_from_token),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Update a role.

    - **role_id**: Role ID
    - **name**: New role name (optional, cannot update system roles)
    - **description**: New description (optional)
    """
    role = db.query(Role).filter(Role.id == role_id).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found"
        )

    # Track old values for audit log
    old_values = {
        'name': role.name,
        'description': role.description
    }

    # System roles cannot be renamed
    if role_data.name and role_data.name != role.name:
        if role.is_system_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot rename system roles"
            )

        # Check if new name already exists
        existing_role = db.query(Role).filter(Role.name == role_data.name).first()
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{role_data.name}' already exists"
            )
        role.name = role_data.name

    # Update description
    if role_data.description is not None:
        role.description = role_data.description

    role.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(role)

    # Track new values for audit log
    new_values = {
        'name': role.name,
        'description': role.description
    }

    # Log role update
    audit_service.log_action(
        db=db,
        user=current_user,
        action=audit_service.ACTION_TYPES.get('ROLE_EDIT', 'role_edit'),
        resource_type='role',
        resource_id=role.id,
        resource_name=role.name,
        old_values=old_values,
        new_values=new_values,
        request=request
    )

    return RoleResponse.model_validate(role)


@router.delete("/{role_id}", status_code=status.HTTP_200_OK)
def delete_role(
    role_id: int,
    current_user: Optional[User] = Depends(get_current_user_from_token),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Delete a role.

    - **role_id**: Role ID to delete

    Note: Cannot delete system roles (Super Admin, Administrator, Operator, Viewer).
    """
    role = db.query(Role).filter(Role.id == role_id).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found"
        )

    # Prevent deleting system roles
    if role.is_system_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete system role '{role.name}'"
        )

    # Store name for audit log
    role_name = role.name

    # Delete role (cascade will delete related records)
    db.delete(role)
    db.commit()

    # Log role deletion
    audit_service.log_action(
        db=db,
        user=current_user,
        action=audit_service.ACTION_TYPES.get('ROLE_DELETE', 'role_delete'),
        resource_type='role',
        resource_id=role_id,
        resource_name=role_name,
        request=request
    )

    return {"message": f"Role '{role_name}' deleted successfully"}


@router.post("/{role_id}/permissions/{permission_id}", response_model=RoleWithPermissionsResponse, status_code=status.HTTP_200_OK)
def assign_permission(
    role_id: int,
    permission_id: int,
    current_user: Optional[User] = Depends(get_current_user_from_token),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Assign a permission to a role.

    - **role_id**: Role ID
    - **permission_id**: Permission ID to assign
    """
    role = db.query(Role).filter(Role.id == role_id).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found"
        )

    permission = db.query(Permission).filter(Permission.id == permission_id).first()

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permission with ID {permission_id} not found"
        )

    # Check if role already has this permission
    existing = db.query(RolePermission).filter(
        RolePermission.role_id == role_id,
        RolePermission.permission_id == permission_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{role.name}' already has permission '{permission.resource}:{permission.action}'"
        )

    # Assign permission
    role_permission = RolePermission(
        role_id=role_id,
        permission_id=permission_id,
        granted_by=current_user.id if current_user else None
    )
    db.add(role_permission)
    db.commit()

    # Log permission assignment
    audit_service.log_action(
        db=db,
        user=current_user,
        action=audit_service.ACTION_TYPES.get('PERMISSION_GRANT', 'permission_grant'),
        resource_type='role',
        resource_id=role.id,
        resource_name=role.name,
        new_values={'permission': f"{permission.resource}:{permission.action}"},
        request=request
    )

    # Return updated role with permissions
    return get_role(role_id, current_user, db)


@router.delete("/{role_id}/permissions/{permission_id}", response_model=RoleWithPermissionsResponse, status_code=status.HTTP_200_OK)
def remove_permission(
    role_id: int,
    permission_id: int,
    current_user: Optional[User] = Depends(get_current_user_from_token),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Remove a permission from a role.

    - **role_id**: Role ID
    - **permission_id**: Permission ID to remove
    """
    role = db.query(Role).filter(Role.id == role_id).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found"
        )

    permission = db.query(Permission).filter(Permission.id == permission_id).first()

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permission with ID {permission_id} not found"
        )

    # Check if role has this permission
    role_permission = db.query(RolePermission).filter(
        RolePermission.role_id == role_id,
        RolePermission.permission_id == permission_id
    ).first()

    if not role_permission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{role.name}' does not have permission '{permission.resource}:{permission.action}'"
        )

    # Remove permission
    db.delete(role_permission)
    db.commit()

    # Log permission removal
    audit_service.log_action(
        db=db,
        user=current_user,
        action=audit_service.ACTION_TYPES.get('PERMISSION_REVOKE', 'permission_revoke'),
        resource_type='role',
        resource_id=role.id,
        resource_name=role.name,
        old_values={'permission': f"{permission.resource}:{permission.action}"},
        request=request
    )

    # Return updated role with permissions
    return get_role(role_id, current_user, db)



# Create separate permissions router for cleaner URL structure
permissions_router = APIRouter(prefix="/auth/permissions", tags=["Roles & Permissions"])


@permissions_router.get("", response_model=PermissionListResponse, status_code=status.HTTP_200_OK)
def list_permissions(
    current_user: Optional[User] = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """
    List all available permissions.

    Returns all permissions in the system, grouped by resource.
    """
    permissions = db.query(Permission).order_by(Permission.resource, Permission.action).all()

    return PermissionListResponse(
        permissions=[PermissionResponse.model_validate(perm) for perm in permissions]
    )


# Export both routers
__all__ = ['router', 'permissions_router']
