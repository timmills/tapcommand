#!/usr/bin/env python3
"""
Seed Authentication Data

Creates default permissions, roles, and admin user for SmartVenue.
Safe to run multiple times - will skip existing data.

Usage:
    python -m app.db.seed_auth
    # OR
    from app.db.seed_auth import seed_auth_data
    seed_auth_data(db_session)
"""

from sqlalchemy.orm import Session
from datetime import datetime
from ..models.auth import User, Role, Permission, RolePermission, UserRole
from ..core.security import hash_password


# Define all permissions (resource:action format)
PERMISSIONS = [
    # Devices
    ('devices', 'view', 'View device list and details'),
    ('devices', 'edit', 'Edit device configuration'),
    ('devices', 'configure', 'Configure device settings'),
    ('devices', 'delete', 'Delete devices'),
    ('devices', 'command', 'Send commands to devices'),

    # IR Senders
    ('ir_senders', 'view', 'View IR sender hardware'),
    ('ir_senders', 'add', 'Add devices to management'),
    ('ir_senders', 'edit', 'Edit device settings'),
    ('ir_senders', 'configure', 'Configure IR ports'),
    ('ir_senders', 'delete', 'Remove from management'),
    ('ir_senders', 'health_check', 'Run health checks'),

    # Templates
    ('templates', 'view', 'View templates and YAML'),
    ('templates', 'edit', 'Edit template configuration'),
    ('templates', 'compile', 'Compile firmware'),
    ('templates', 'deploy', 'Download/deploy binaries'),

    # Tags
    ('tags', 'view', 'View tags'),
    ('tags', 'create', 'Create new tags'),
    ('tags', 'edit', 'Edit existing tags'),
    ('tags', 'delete', 'Delete tags'),

    # Channels
    ('channels', 'view', 'View channel lists'),
    ('channels', 'edit', 'Edit channel configuration'),
    ('channels', 'enable_disable', 'Enable/disable channels'),
    ('channels', 'create_inhouse', 'Create custom channels'),
    ('channels', 'delete_inhouse', 'Delete custom channels'),

    # Schedules
    ('schedules', 'view', 'View schedules'),
    ('schedules', 'create', 'Create schedules'),
    ('schedules', 'edit', 'Edit schedules'),
    ('schedules', 'delete', 'Delete schedules'),
    ('schedules', 'run_manual', 'Manually trigger schedules'),

    # IR Capture
    ('ir_capture', 'capture', 'Capture IR signals'),
    ('ir_capture', 'save', 'Save captured signals'),
    ('ir_capture', 'import', 'Import signal libraries'),

    # Settings
    ('settings', 'view', 'View settings'),
    ('settings', 'edit_wifi', 'Edit WiFi configuration'),
    ('settings', 'edit_ota', 'Edit OTA settings'),
    ('settings', 'edit_api_keys', 'Edit API keys'),

    # Users
    ('users', 'view', 'View user list'),
    ('users', 'create', 'Create new users'),
    ('users', 'edit', 'Edit user details'),
    ('users', 'delete', 'Delete users'),
    ('users', 'assign_roles', 'Assign/remove roles'),

    # Audit
    ('audit', 'view', 'View audit logs'),
    ('audit', 'export', 'Export audit logs'),

    # Admin
    ('admin', 'database', 'Access database admin interface'),
    ('admin', 'system', 'System configuration'),
]


# Define roles with their permissions
ROLES = {
    'Super Admin': {
        'description': 'Full system access for IT administrators',
        'is_system': True,
        'permissions': '*',  # All permissions
    },
    'Administrator': {
        'description': 'Full venue management without user administration',
        'is_system': True,
        'permissions': [
            # All devices permissions
            'devices:view', 'devices:edit', 'devices:configure', 'devices:delete', 'devices:command',
            # All IR senders permissions
            'ir_senders:view', 'ir_senders:add', 'ir_senders:edit', 'ir_senders:configure',
            'ir_senders:delete', 'ir_senders:health_check',
            # All templates permissions
            'templates:view', 'templates:edit', 'templates:compile', 'templates:deploy',
            # All tags permissions
            'tags:view', 'tags:create', 'tags:edit', 'tags:delete',
            # All channels permissions
            'channels:view', 'channels:edit', 'channels:enable_disable',
            'channels:create_inhouse', 'channels:delete_inhouse',
            # All schedules permissions
            'schedules:view', 'schedules:create', 'schedules:edit',
            'schedules:delete', 'schedules:run_manual',
            # All IR capture permissions
            'ir_capture:capture', 'ir_capture:save', 'ir_capture:import',
            # All settings permissions
            'settings:view', 'settings:edit_wifi', 'settings:edit_ota', 'settings:edit_api_keys',
            # Audit view only
            'audit:view',
        ]
    },
    'Operator': {
        'description': 'Day-to-day operational control',
        'is_system': True,
        'permissions': [
            # Devices - view, edit, configure, command (no delete)
            'devices:view', 'devices:edit', 'devices:configure', 'devices:command',
            # IR senders - view, configure, health check (no add/delete)
            'ir_senders:view', 'ir_senders:configure', 'ir_senders:health_check',
            # Templates - view only
            'templates:view',
            # Tags - view only
            'tags:view',
            # Channels - view, edit, enable/disable (no create/delete)
            'channels:view', 'channels:edit', 'channels:enable_disable',
            # Schedules - view, create, edit, run manual (no delete)
            'schedules:view', 'schedules:create', 'schedules:edit', 'schedules:run_manual',
            # Settings - view only
            'settings:view',
        ]
    },
    'Viewer': {
        'description': 'Read-only access for monitoring',
        'is_system': True,
        'permissions': [
            # View-only permissions
            'devices:view',
            'ir_senders:view',
            'templates:view',
            'tags:view',
            'channels:view',
            'schedules:view',
            'settings:view',
        ]
    },
}


# Default admin user
DEFAULT_ADMIN = {
    'username': 'admin',
    'email': 'admin@smartvenue.local',
    'password': 'admin',  # MUST BE CHANGED on first login
    'full_name': 'System Administrator',
    'is_superuser': True,
    'must_change_password': True,
}


def seed_auth_data(db: Session) -> dict:
    """
    Seed authentication data into the database.

    Creates permissions, roles, role-permission mappings, and default admin user.
    Safe to run multiple times - will skip existing data.

    Args:
        db: SQLAlchemy database session

    Returns:
        Dictionary with counts of created items

    Example:
        >>> from app.db.database import SessionLocal
        >>> from app.db.seed_auth import seed_auth_data
        >>> db = SessionLocal()
        >>> result = seed_auth_data(db)
        >>> print(result)
        {'permissions': 45, 'roles': 4, 'users': 1}
    """
    stats = {
        'permissions': 0,
        'roles': 0,
        'role_permissions': 0,
        'users': 0,
    }

    print("=" * 70)
    print("Seeding Authentication Data")
    print("=" * 70)
    print()

    # 1. Create permissions
    print("1. Creating permissions...")
    permission_map = {}  # Map permission string to Permission object

    for resource, action, description in PERMISSIONS:
        # Check if permission already exists
        existing = db.query(Permission).filter_by(
            resource=resource,
            action=action
        ).first()

        if existing:
            permission_map[f"{resource}:{action}"] = existing
            continue

        # Create new permission
        permission = Permission(
            resource=resource,
            action=action,
            description=description
        )
        db.add(permission)
        permission_map[f"{resource}:{action}"] = permission
        stats['permissions'] += 1

    db.commit()
    print(f"   ✓ Created {stats['permissions']} new permissions ({len(permission_map)} total)")
    print()

    # 2. Create roles
    print("2. Creating roles...")
    role_map = {}  # Map role name to Role object

    for role_name, role_config in ROLES.items():
        # Check if role already exists
        existing = db.query(Role).filter_by(name=role_name).first()

        if existing:
            role_map[role_name] = existing
            continue

        # Create new role
        role = Role(
            name=role_name,
            description=role_config['description'],
            is_system_role=role_config['is_system']
        )
        db.add(role)
        db.flush()  # Flush to get the role ID
        role_map[role_name] = role
        stats['roles'] += 1

        # Assign permissions to role
        if role_config['permissions'] == '*':
            # Assign all permissions (Super Admin)
            for perm in permission_map.values():
                role_perm = RolePermission(
                    role_id=role.id,
                    permission_id=perm.id
                )
                db.add(role_perm)
                stats['role_permissions'] += 1
        else:
            # Assign specific permissions
            for perm_string in role_config['permissions']:
                perm = permission_map.get(perm_string)
                if perm:
                    role_perm = RolePermission(
                        role_id=role.id,
                        permission_id=perm.id
                    )
                    db.add(role_perm)
                    stats['role_permissions'] += 1
                else:
                    print(f"   ⚠ Warning: Permission '{perm_string}' not found for role '{role_name}'")

    db.commit()
    print(f"   ✓ Created {stats['roles']} new roles ({len(role_map)} total)")
    print(f"   ✓ Created {stats['role_permissions']} role-permission mappings")
    print()

    # 3. Create default admin user
    print("3. Creating default admin user...")

    # Check if admin user already exists
    existing_admin = db.query(User).filter_by(username=DEFAULT_ADMIN['username']).first()

    if existing_admin:
        print(f"   ⚠ Admin user '{DEFAULT_ADMIN['username']}' already exists - skipping")
    else:
        # Create admin user
        admin_user = User(
            username=DEFAULT_ADMIN['username'],
            email=DEFAULT_ADMIN['email'],
            password_hash=hash_password(DEFAULT_ADMIN['password']),
            full_name=DEFAULT_ADMIN['full_name'],
            is_superuser=DEFAULT_ADMIN['is_superuser'],
            must_change_password=DEFAULT_ADMIN['must_change_password'],
            is_active=True,
            password_changed_at=datetime.utcnow(),
        )
        db.add(admin_user)
        db.flush()  # Flush to get the user ID

        # Assign Super Admin role
        super_admin_role = role_map.get('Super Admin')
        if super_admin_role:
            user_role = UserRole(
                user_id=admin_user.id,
                role_id=super_admin_role.id
            )
            db.add(user_role)

        stats['users'] += 1
        db.commit()

        print(f"   ✓ Created admin user: {DEFAULT_ADMIN['username']}")
        print(f"   ✓ Default password: {DEFAULT_ADMIN['password']}")
        print(f"   ⚠ IMPORTANT: Change password on first login!")

    print()
    print("=" * 70)
    print("Authentication Data Seeding Complete")
    print("=" * 70)
    print()
    print(f"Summary:")
    print(f"  - Permissions created: {stats['permissions']}")
    print(f"  - Roles created: {stats['roles']}")
    print(f"  - Role-Permission mappings: {stats['role_permissions']}")
    print(f"  - Users created: {stats['users']}")
    print()

    if stats['users'] > 0:
        print("⚠ SECURITY REMINDER:")
        print(f"   Username: {DEFAULT_ADMIN['username']}")
        print(f"   Password: {DEFAULT_ADMIN['password']}")
        print("   Please change the admin password immediately!")
        print()

    return stats


def main():
    """Main entry point for running seed script directly"""
    from .database import SessionLocal

    db = SessionLocal()
    try:
        seed_auth_data(db)
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
