"""
Authentication Router

Provides endpoints for user authentication:
- Login (username/password -> JWT tokens)
- Logout (revoke session)
- Refresh (get new access token)
- Me (get current user info)
- Change password

NOTE: These endpoints are standalone and do NOT enforce authentication
on other parts of the application yet.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta

from ..db.database import get_db
from ..models.auth import User, Role, UserRole, UserSession
from ..core.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    create_refresh_token,
    verify_token,
    hash_token,
    MAX_FAILED_LOGIN_ATTEMPTS,
    ACCOUNT_LOCK_MINUTES,
)
from ..services.audit import audit_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

# OAuth2 scheme for Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


# ==================== Pydantic Models ====================

class Token(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Change password request"""
    current_password: str
    new_password: str


class RoleResponse(BaseModel):
    """Role information"""
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """User information response"""
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

    class Config:
        from_attributes = True


# ==================== Helper Functions ====================

def get_current_user_from_token(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user from JWT token (optional - returns None if not authenticated).
    This is a standalone function that doesn't enforce authentication.
    """
    if not token:
        return None

    # Verify and decode token
    payload = verify_token(token, "access")
    if not payload:
        return None

    # Get user ID from token
    user_id = payload.get("user_id")
    if not user_id:
        return None

    # Check if token is revoked
    token_hashed = hash_token(token)
    session = db.query(UserSession).filter_by(
        token_hash=token_hashed,
        is_revoked=False
    ).first()

    if not session:
        return None

    # Get user from database
    user = db.query(User).filter_by(id=user_id, is_active=True).first()
    if not user:
        return None

    # Update last used
    session.last_used_at = datetime.utcnow()
    db.commit()

    return user


def check_account_locked(user: User) -> bool:
    """Check if account is locked"""
    if user.locked_until and user.locked_until > datetime.utcnow():
        return True
    return False


def lock_account(user: User, db: Session):
    """Lock account after failed login attempts"""
    user.locked_until = datetime.utcnow() + timedelta(minutes=ACCOUNT_LOCK_MINUTES)
    db.commit()


def reset_failed_attempts(user: User, db: Session):
    """Reset failed login attempts"""
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()


# ==================== Endpoints ====================

@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens.

    - **username**: Username or email
    - **password**: User password

    Returns access token (30 min) and refresh token (30 days).
    """
    # Find user by username or email
    user = db.query(User).filter(
        (User.username == form_data.username) | (User.email == form_data.username)
    ).first()

    if not user:
        # Log failed login attempt for unknown user
        audit_service.log_authentication_event(
            db=db,
            username=form_data.username,
            action=audit_service.ACTION_TYPES['AUTH_FAILED'],
            success=False,
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            error_message="User not found"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if account is locked
    if check_account_locked(user):
        minutes_remaining = int((user.locked_until - datetime.utcnow()).total_seconds() / 60)
        # Log locked account login attempt
        audit_service.log_authentication_event(
            db=db,
            username=user.username,
            action=audit_service.ACTION_TYPES['AUTH_LOCKED'],
            success=False,
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            error_message=f"Account locked for {minutes_remaining} minutes"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is locked. Try again in {minutes_remaining} minutes."
        )

    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    # Verify password
    if not verify_password(form_data.password, user.password_hash):
        # Increment failed login attempts
        user.failed_login_attempts += 1

        if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
            lock_account(user, db)
            # Log account lock event
            audit_service.log_authentication_event(
                db=db,
                username=user.username,
                action=audit_service.ACTION_TYPES['AUTH_LOCKED'],
                success=False,
                ip_address=request.client.host if request and request.client else None,
                user_agent=request.headers.get("user-agent") if request else None,
                error_message=f"Account locked after {MAX_FAILED_LOGIN_ATTEMPTS} failed attempts"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Too many failed login attempts. Account locked for {ACCOUNT_LOCK_MINUTES} minutes."
            )

        db.commit()
        # Log failed login attempt
        audit_service.log_authentication_event(
            db=db,
            username=user.username,
            action=audit_service.ACTION_TYPES['AUTH_FAILED'],
            success=False,
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            error_message="Invalid password",
            details={'failed_attempts': user.failed_login_attempts}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Reset failed attempts on successful login
    reset_failed_attempts(user, db)

    # Update last login
    user.last_login = datetime.utcnow()
    if request:
        user.last_login_ip = request.client.host if request.client else None
    db.commit()

    # Create JWT tokens
    token_data = {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "is_superuser": user.is_superuser,
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({"user_id": user.id})

    # Store session in database
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(access_token),
        refresh_token_hash=hash_token(refresh_token),
        expires_at=datetime.utcnow() + timedelta(minutes=30),
        refresh_expires_at=datetime.utcnow() + timedelta(days=30),
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.add(session)
    db.commit()

    # Log successful login
    audit_service.log_authentication_event(
        db=db,
        username=user.username,
        action=audit_service.ACTION_TYPES['AUTH_LOGIN'],
        success=True,
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=1800  # 30 minutes in seconds
    )


@router.post("/refresh", response_model=Token, status_code=status.HTTP_200_OK)
def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Get a new access token using refresh token.

    - **refresh_token**: Valid refresh token

    Returns new access and refresh tokens.
    """
    # Verify refresh token
    payload = verify_token(refresh_request.refresh_token, "refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Check if refresh token is revoked
    refresh_token_hashed = hash_token(refresh_request.refresh_token)
    session = db.query(UserSession).filter_by(
        refresh_token_hash=refresh_token_hashed,
        is_revoked=False
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or revoked"
        )

    # Get user
    user = db.query(User).filter_by(id=user_id, is_active=True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Create new tokens
    token_data = {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "is_superuser": user.is_superuser,
    }

    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token({"user_id": user.id})

    # Update session with new tokens
    session.token_hash = hash_token(new_access_token)
    session.refresh_token_hash = hash_token(new_refresh_token)
    session.expires_at = datetime.utcnow() + timedelta(minutes=30)
    session.refresh_expires_at = datetime.utcnow() + timedelta(days=30)
    session.last_used_at = datetime.utcnow()
    db.commit()

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=1800
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Logout user by revoking their session.

    Requires valid access token in Authorization header.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    # Find and revoke session
    token_hashed = hash_token(token)
    session = db.query(UserSession).filter_by(token_hash=token_hashed).first()

    if session:
        # Get user for audit log
        user = db.query(User).filter_by(id=session.user_id).first()

        session.is_revoked = True
        session.revoked_at = datetime.utcnow()
        db.commit()

        # Log logout event
        if user:
            audit_service.log_authentication_event(
                db=db,
                username=user.username,
                action=audit_service.ACTION_TYPES['AUTH_LOGOUT'],
                success=True,
                ip_address=request.client.host if request and request.client else None,
                user_agent=request.headers.get("user-agent") if request else None
            )

    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_current_user_info(
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user's information.

    Requires valid access token in Authorization header.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    # Get user's roles
    user_roles = db.query(Role).join(UserRole).filter(
        UserRole.user_id == current_user.id
    ).all()

    # Build response
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        must_change_password=current_user.must_change_password,
        roles=[RoleResponse.model_validate(role) for role in user_roles],
        last_login=current_user.last_login,
        created_at=current_user.created_at
    )


@router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    password_request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Change current user's password.

    Requires valid access token in Authorization header.

    - **current_password**: Current password
    - **new_password**: New password (must meet strength requirements)
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    # Verify current password
    if not verify_password(password_request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Validate new password strength
    is_valid, error_message = validate_password_strength(password_request.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    # Check if new password is same as current
    if password_request.current_password == password_request.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )

    # Update password
    current_user.password_hash = hash_password(password_request.new_password)
    current_user.password_changed_at = datetime.utcnow()
    current_user.must_change_password = False
    db.commit()

    # Log password change
    audit_service.log_authentication_event(
        db=db,
        username=current_user.username,
        action=audit_service.ACTION_TYPES['AUTH_PASSWORD_CHANGE'],
        success=True,
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None
    )

    return {"message": "Password changed successfully"}
