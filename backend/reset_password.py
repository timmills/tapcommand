#!/usr/bin/env python3
"""
Emergency Password Reset Script

Use this script if you get locked out of your account.

IMPORTANT: Must run from within the virtual environment!

From /home/coastal/tapcommand/backend:

    source ../venv/bin/activate
    python3 reset_password.py <username> <new_password>

Example:

    source ../venv/bin/activate
    python3 reset_password.py admin MyNewPassword123!

This will:
- Reset the password
- Clear failed login attempts
- Unlock the account
- Remove password change requirement
"""

import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.auth import User
from app.core.security import hash_password, validate_password_strength
from datetime import datetime


def reset_password(username: str, new_password: str):
    """Reset a user's password and unlock their account"""

    # Validate password strength
    is_valid, error_message = validate_password_strength(new_password)
    if not is_valid:
        print(f"❌ Password validation failed: {error_message}")
        print("\nPassword requirements:")
        print("  - At least 4 characters")
        return False

    db: Session = SessionLocal()
    try:
        # Find user
        user = db.query(User).filter(User.username == username).first()

        if not user:
            print(f"❌ User '{username}' not found")
            return False

        print(f"Found user: {user.username} ({user.email})")
        print(f"Current status:")
        print(f"  - Active: {user.is_active}")
        print(f"  - Failed login attempts: {user.failed_login_attempts}")
        print(f"  - Locked until: {user.locked_until or 'Not locked'}")
        print()

        # Reset password
        user.password_hash = hash_password(new_password)
        user.password_changed_at = datetime.utcnow()
        user.failed_login_attempts = 0
        user.locked_until = None
        user.must_change_password = False

        # Ensure account is active
        if not user.is_active:
            print("⚠️  Account was inactive - activating it now")
            user.is_active = True

        db.commit()

        print("✅ Password reset successful!")
        print(f"✅ Account unlocked")
        print(f"✅ Failed login attempts cleared")
        print(f"✅ Password change requirement removed")
        print()
        print(f"You can now log in with:")
        print(f"  Username: {user.username}")
        print(f"  Password: {new_password}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def main():
    if len(sys.argv) != 3:
        print("Emergency Password Reset Script")
        print("=" * 50)
        print()
        print("Usage:")
        print(f"  python {sys.argv[0]} <username> <new_password>")
        print()
        print("Example:")
        print(f"  python {sys.argv[0]} admin MyNewPassword123!")
        print()
        print("This will reset the password and unlock the account.")
        sys.exit(1)

    username = sys.argv[1]
    new_password = sys.argv[2]

    print()
    print("Emergency Password Reset")
    print("=" * 50)
    print()

    if reset_password(username, new_password):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
