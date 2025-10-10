"""
Security utilities for authentication and authorization.

Provides password hashing, JWT token generation/validation,
and token utilities for the TapCommand application.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
import hashlib
import secrets

# Password hashing configuration
# Using bcrypt with 12 rounds (recommended for security/performance balance)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration (will be overridden by environment variables)
# These are defaults - should be set via environment variables in production
SECRET_KEY = secrets.token_urlsafe(32)  # Default secret (MUST be overridden in production)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Account security
MAX_FAILED_LOGIN_ATTEMPTS = 5
ACCOUNT_LOCK_MINUTES = 15


# ==================== Password Hashing ====================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password string

    Example:
        >>> hashed = hash_password("mypassword123")
        >>> print(hashed)
        $2b$12$...
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise

    Example:
        >>> hashed = hash_password("mypassword123")
        >>> verify_password("mypassword123", hashed)
        True
        >>> verify_password("wrongpassword", hashed)
        False
    """
    return pwd_context.verify(plain_password, hashed_password)


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password meets security requirements.

    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
        If valid: (True, None)
        If invalid: (False, "error description")

    Example:
        >>> validate_password_strength("weak")
        (False, "Password must be at least 8 characters long")
        >>> validate_password_strength("StrongPass123!")
        (True, None)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"

    # Check for special characters
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least one special character"

    return True, None


# ==================== JWT Token Generation ====================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    secret_key: Optional[str] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary of data to encode in token (typically user_id, username, etc.)
        expires_delta: Optional custom expiration time
        secret_key: Optional custom secret key (defaults to SECRET_KEY)

    Returns:
        Encoded JWT token string

    Example:
        >>> token = create_access_token({"user_id": 1, "username": "admin"})
        >>> print(token)
        eyJ0eXAiOiJKV1QiLCJhbGc...
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})

    # Encode token
    secret = secret_key or SECRET_KEY
    encoded_jwt = jwt.encode(to_encode, secret, algorithm=ALGORITHM)

    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    secret_key: Optional[str] = None
) -> str:
    """
    Create a JWT refresh token.

    Refresh tokens have a longer expiration time than access tokens
    and are used to obtain new access tokens without re-authentication.

    Args:
        data: Dictionary of data to encode in token
        expires_delta: Optional custom expiration time
        secret_key: Optional custom secret key (defaults to SECRET_KEY)

    Returns:
        Encoded JWT refresh token string

    Example:
        >>> token = create_refresh_token({"user_id": 1})
        >>> print(token)
        eyJ0eXAiOiJKV1QiLCJhbGc...
    """
    to_encode = data.copy()

    # Set expiration time (longer for refresh tokens)
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "type": "refresh"})

    # Encode token
    secret = secret_key or SECRET_KEY
    encoded_jwt = jwt.encode(to_encode, secret, algorithm=ALGORITHM)

    return encoded_jwt


# ==================== JWT Token Validation ====================

def decode_token(token: str, secret_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string to decode
        secret_key: Optional custom secret key (defaults to SECRET_KEY)

    Returns:
        Decoded token payload dictionary if valid, None if invalid

    Example:
        >>> token = create_access_token({"user_id": 1})
        >>> payload = decode_token(token)
        >>> print(payload['user_id'])
        1
    """
    try:
        secret = secret_key or SECRET_KEY
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access", secret_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Verify a JWT token and check its type.

    Args:
        token: JWT token string to verify
        token_type: Expected token type ("access" or "refresh")
        secret_key: Optional custom secret key (defaults to SECRET_KEY)

    Returns:
        Decoded token payload if valid and type matches, None otherwise

    Example:
        >>> token = create_access_token({"user_id": 1})
        >>> payload = verify_token(token, "access")
        >>> print(payload is not None)
        True
        >>> verify_token(token, "refresh")  # Wrong type
        None
    """
    payload = decode_token(token, secret_key)

    if payload is None:
        return None

    # Check token type
    if payload.get("type") != token_type:
        return None

    return payload


# ==================== Token Hashing (for database storage) ====================

def hash_token(token: str) -> str:
    """
    Create a SHA256 hash of a token for secure database storage.

    Never store actual tokens in the database - always store hashes.
    This prevents token leakage if the database is compromised.

    Args:
        token: JWT token to hash

    Returns:
        SHA256 hash of the token (hex string)

    Example:
        >>> token = "eyJ0eXAiOiJKV1QiLCJhbGc..."
        >>> hashed = hash_token(token)
        >>> print(len(hashed))
        64
    """
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token_hash(token: str, token_hash: str) -> bool:
    """
    Verify a token against its stored hash.

    Args:
        token: JWT token to verify
        token_hash: Stored token hash to compare against

    Returns:
        True if token matches hash, False otherwise

    Example:
        >>> token = "eyJ0eXAiOiJKV1QiLCJhbGc..."
        >>> hashed = hash_token(token)
        >>> verify_token_hash(token, hashed)
        True
        >>> verify_token_hash("wrong_token", hashed)
        False
    """
    return hash_token(token) == token_hash


# ==================== Token Utilities ====================

def get_token_expiration(token: str, secret_key: Optional[str] = None) -> Optional[datetime]:
    """
    Get the expiration time of a token.

    Args:
        token: JWT token string
        secret_key: Optional custom secret key (defaults to SECRET_KEY)

    Returns:
        Expiration datetime if token is valid, None otherwise

    Example:
        >>> token = create_access_token({"user_id": 1})
        >>> exp = get_token_expiration(token)
        >>> print(exp > datetime.utcnow())
        True
    """
    payload = decode_token(token, secret_key)
    if payload is None:
        return None

    exp_timestamp = payload.get("exp")
    if exp_timestamp is None:
        return None

    return datetime.utcfromtimestamp(exp_timestamp)


def is_token_expired(token: str, secret_key: Optional[str] = None) -> bool:
    """
    Check if a token is expired.

    Args:
        token: JWT token string
        secret_key: Optional custom secret key (defaults to SECRET_KEY)

    Returns:
        True if token is expired or invalid, False if still valid

    Example:
        >>> token = create_access_token({"user_id": 1})
        >>> is_token_expired(token)
        False
    """
    exp = get_token_expiration(token, secret_key)
    if exp is None:
        return True

    return datetime.utcnow() > exp


# ==================== Configuration Update ====================

def update_jwt_config(
    secret_key: Optional[str] = None,
    algorithm: Optional[str] = None,
    access_token_expire: Optional[int] = None,
    refresh_token_expire: Optional[int] = None
):
    """
    Update JWT configuration at runtime (typically from environment variables).

    Args:
        secret_key: JWT secret key (should be a strong random string)
        algorithm: JWT algorithm (default: HS256)
        access_token_expire: Access token expiration in minutes
        refresh_token_expire: Refresh token expiration in days

    Example:
        >>> update_jwt_config(
        ...     secret_key="your-secret-key-here",
        ...     access_token_expire=15,
        ...     refresh_token_expire=7
        ... )
    """
    global SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

    if secret_key:
        SECRET_KEY = secret_key

    if algorithm:
        ALGORITHM = algorithm

    if access_token_expire:
        ACCESS_TOKEN_EXPIRE_MINUTES = access_token_expire

    if refresh_token_expire:
        REFRESH_TOKEN_EXPIRE_DAYS = refresh_token_expire


# ==================== Exports ====================

__all__ = [
    # Password hashing
    "hash_password",
    "verify_password",
    "validate_password_strength",
    # JWT tokens
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "verify_token",
    # Token hashing
    "hash_token",
    "verify_token_hash",
    # Token utilities
    "get_token_expiration",
    "is_token_expired",
    # Configuration
    "update_jwt_config",
    # Constants
    "MAX_FAILED_LOGIN_ATTEMPTS",
    "ACCOUNT_LOCK_MINUTES",
]
