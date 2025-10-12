#!/usr/bin/env python3
"""
Database User Reset Script

Clears ALL users, roles, and permissions from the database and recreates
a fresh authentication system with default credentials.

DANGER: This will DELETE all user accounts, roles, and permissions!
        Device data, schedules, and other system data will be preserved.

Usage:
    python3 reset_database_users.py

This will:
- Delete all users (including admin)
- Delete all roles and permissions
- Recreate default roles and permissions
- Create two default users:
  * admin/admin (Super Admin - full access)
  * staff/staff (Operator - day-to-day operations)

After running, you can log in with either account.
"""

import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.auth import User, Role, Permission, RolePermission, UserRole
from app.db.seed_auth import seed_auth_data


def confirm_reset():
    """Confirm the user really wants to delete all user data"""
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  ⚠️  DATABASE USER RESET - DANGER ZONE  ⚠️".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    print("This script will DELETE ALL user accounts, roles, and permissions!")
    print()
    print("What will be deleted:")
    print("  ❌ All user accounts (including current admin)")
    print("  ❌ All roles (custom and system)")
    print("  ❌ All permissions")
    print("  ❌ All authentication tokens")
    print()
    print("What will be preserved:")
    print("  ✓ Devices and IR controllers")
    print("  ✓ Schedules and automation")
    print("  ✓ Settings and configuration")
    print("  ✓ Command history")
    print()
    print("After reset, new default users will be created:")
    print("  👤 Admin user: admin / admin (Super Admin)")
    print("  👤 Staff user: staff / staff (Operator)")
    print()

    response = input("Type 'DELETE ALL USERS' to confirm (or anything else to cancel): ")
    return response == "DELETE ALL USERS"


def reset_users(db: Session):
    """Delete all authentication data and reseed"""

    print()
    print("=" * 70)
    print("Deleting authentication data...")
    print("=" * 70)
    print()

    # Count existing data
    user_count = db.query(User).count()
    role_count = db.query(Role).count()
    permission_count = db.query(Permission).count()

    print(f"Found {user_count} users, {role_count} roles, {permission_count} permissions")
    print()

    # Delete in correct order (respecting foreign keys)
    print("1. Deleting user-role mappings...")
    deleted = db.query(UserRole).delete()
    print(f"   ✓ Deleted {deleted} user-role mappings")

    print("2. Deleting users...")
    deleted = db.query(User).delete()
    print(f"   ✓ Deleted {deleted} users")

    print("3. Deleting role-permission mappings...")
    deleted = db.query(RolePermission).delete()
    print(f"   ✓ Deleted {deleted} role-permission mappings")

    print("4. Deleting roles...")
    deleted = db.query(Role).delete()
    print(f"   ✓ Deleted {deleted} roles")

    print("5. Deleting permissions...")
    deleted = db.query(Permission).delete()
    print(f"   ✓ Deleted {deleted} permissions")

    db.commit()
    print()
    print("✓ All authentication data deleted")
    print()

    # Reseed with defaults
    print("=" * 70)
    print("Recreating fresh authentication system...")
    print("=" * 70)
    print()

    stats = seed_auth_data(db)

    # Create additional staff user with Operator role
    print()
    print("=" * 70)
    print("Creating additional staff user...")
    print("=" * 70)
    print()

    from app.core.security import hash_password
    from datetime import datetime

    # Check if Operator role exists
    operator_role = db.query(Role).filter_by(name='Operator').first()

    if operator_role:
        # Create staff user
        staff_user = User(
            username='staff',
            email='staff@tapcommand.local',
            password_hash=hash_password('staff'),
            full_name='Staff User',
            is_superuser=False,
            must_change_password=False,
            is_active=True,
            password_changed_at=datetime.utcnow(),
        )
        db.add(staff_user)
        db.flush()  # Flush to get the user ID

        # Assign Operator role
        user_role = UserRole(
            user_id=staff_user.id,
            role_id=operator_role.id
        )
        db.add(user_role)
        db.commit()

        print(f"   ✓ Created staff user: staff")
        print(f"   ✓ Assigned role: Operator (day-to-day operational control)")
        print()
    else:
        print("   ⚠ Warning: Operator role not found - staff user not created")
        print()

    print("=" * 70)
    print("✅ DATABASE RESET COMPLETE")
    print("=" * 70)
    print()
    print("You can now log in with:")
    print()
    print("  👤 Admin account:")
    print("     Username: admin")
    print("     Password: admin")
    print("     Role: Super Admin (full access)")
    print()
    print("  👤 Staff account:")
    print("     Username: staff")
    print("     Password: staff")
    print("     Role: Operator (day-to-day operations)")
    print()
    print("⚠️  Consider changing passwords after login (though it's no longer required)")
    print()


def main():
    print()

    if not confirm_reset():
        print()
        print("❌ Reset cancelled - no changes made")
        print()
        sys.exit(1)

    print()
    print("Proceeding with reset...")

    db: Session = SessionLocal()
    try:
        reset_users(db)
        sys.exit(0)
    except Exception as e:
        print()
        print(f"❌ Error during reset: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
