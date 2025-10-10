#!/usr/bin/env python3
"""
Migration: Add User Management and Access Control

Creates eight new tables for comprehensive user management:
1. users - User accounts with authentication
2. roles - User roles (Super Admin, Administrator, Operator, Viewer, Custom)
3. permissions - Granular resource-based permissions
4. role_permissions - Many-to-many relationship between roles and permissions
5. user_roles - Many-to-many relationship between users and roles
6. user_location_restrictions - Optional location-based access control
7. user_sessions - JWT token tracking and revocation
8. audit_log - Comprehensive audit trail of all user actions

Usage:
    cd backend
    python migrations/add_user_management.py
"""

import sqlite3
import sys
import os


def run_migration():
    """Create user management and access control tables"""
    # Use the default database path
    db_path = "tapcommand.db"

    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        print("Please run the backend server first to create the database.")
        return False

    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if tables already exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cursor.fetchone():
            print("User management tables already exist.")
            conn.close()
            return True

        print("Creating user management and access control tables...")

        # 1. Create users table
        create_users_sql = """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(100) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            is_superuser BOOLEAN DEFAULT FALSE,
            must_change_password BOOLEAN DEFAULT FALSE,
            password_changed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            last_login_ip VARCHAR(50),
            failed_login_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP,
            created_by INTEGER REFERENCES users(id),
            CHECK(LENGTH(username) >= 3)
        )
        """
        cursor.execute(create_users_sql)
        print("✓ Created 'users' table")

        # Create indexes for users
        cursor.execute("CREATE UNIQUE INDEX idx_users_username ON users(username)")
        cursor.execute("CREATE UNIQUE INDEX idx_users_email ON users(email)")
        cursor.execute("CREATE INDEX idx_users_active ON users(is_active)")
        cursor.execute("CREATE INDEX idx_users_superuser ON users(is_superuser)")
        print("✓ Created indexes for users")

        # 2. Create roles table
        create_roles_sql = """
        CREATE TABLE roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) UNIQUE NOT NULL,
            description TEXT,
            is_system_role BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER REFERENCES users(id)
        )
        """
        cursor.execute(create_roles_sql)
        print("✓ Created 'roles' table")

        # Create indexes for roles
        cursor.execute("CREATE UNIQUE INDEX idx_roles_name ON roles(name)")
        cursor.execute("CREATE INDEX idx_roles_system ON roles(is_system_role)")
        print("✓ Created indexes for roles")

        # 3. Create permissions table
        create_permissions_sql = """
        CREATE TABLE permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource VARCHAR(50) NOT NULL,
            action VARCHAR(50) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(resource, action)
        )
        """
        cursor.execute(create_permissions_sql)
        print("✓ Created 'permissions' table")

        # Create indexes for permissions
        cursor.execute("CREATE INDEX idx_permissions_resource ON permissions(resource)")
        cursor.execute("CREATE UNIQUE INDEX idx_permissions_resource_action ON permissions(resource, action)")
        print("✓ Created indexes for permissions")

        # 4. Create role_permissions table
        create_role_permissions_sql = """
        CREATE TABLE role_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            granted_by INTEGER REFERENCES users(id),
            UNIQUE(role_id, permission_id)
        )
        """
        cursor.execute(create_role_permissions_sql)
        print("✓ Created 'role_permissions' table")

        # Create indexes for role_permissions
        cursor.execute("CREATE INDEX idx_role_permissions_role ON role_permissions(role_id)")
        cursor.execute("CREATE INDEX idx_role_permissions_permission ON role_permissions(permission_id)")
        cursor.execute("CREATE UNIQUE INDEX idx_role_permissions_unique ON role_permissions(role_id, permission_id)")
        print("✓ Created indexes for role_permissions")

        # 5. Create user_roles table
        create_user_roles_sql = """
        CREATE TABLE user_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            assigned_by INTEGER REFERENCES users(id),
            expires_at TIMESTAMP,
            UNIQUE(user_id, role_id)
        )
        """
        cursor.execute(create_user_roles_sql)
        print("✓ Created 'user_roles' table")

        # Create indexes for user_roles
        cursor.execute("CREATE INDEX idx_user_roles_user ON user_roles(user_id)")
        cursor.execute("CREATE INDEX idx_user_roles_role ON user_roles(role_id)")
        cursor.execute("CREATE INDEX idx_user_roles_expires ON user_roles(expires_at)")
        cursor.execute("CREATE UNIQUE INDEX idx_user_roles_unique ON user_roles(user_id, role_id)")
        print("✓ Created indexes for user_roles")

        # 6. Create user_location_restrictions table
        create_user_location_restrictions_sql = """
        CREATE TABLE user_location_restrictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            location VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER REFERENCES users(id),
            UNIQUE(user_id, location)
        )
        """
        cursor.execute(create_user_location_restrictions_sql)
        print("✓ Created 'user_location_restrictions' table")

        # Create indexes for user_location_restrictions
        cursor.execute("CREATE INDEX idx_location_restrictions_user ON user_location_restrictions(user_id)")
        cursor.execute("CREATE INDEX idx_location_restrictions_location ON user_location_restrictions(location)")
        print("✓ Created indexes for user_location_restrictions")

        # 7. Create user_sessions table
        create_user_sessions_sql = """
        CREATE TABLE user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash VARCHAR(255) UNIQUE NOT NULL,
            refresh_token_hash VARCHAR(255) UNIQUE,
            expires_at TIMESTAMP NOT NULL,
            refresh_expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address VARCHAR(50),
            user_agent TEXT,
            is_revoked BOOLEAN DEFAULT FALSE,
            revoked_at TIMESTAMP,
            revoked_by INTEGER REFERENCES users(id)
        )
        """
        cursor.execute(create_user_sessions_sql)
        print("✓ Created 'user_sessions' table")

        # Create indexes for user_sessions
        cursor.execute("CREATE INDEX idx_sessions_user ON user_sessions(user_id)")
        cursor.execute("CREATE UNIQUE INDEX idx_sessions_token ON user_sessions(token_hash)")
        cursor.execute("CREATE UNIQUE INDEX idx_sessions_refresh ON user_sessions(refresh_token_hash)")
        cursor.execute("CREATE INDEX idx_sessions_expires ON user_sessions(expires_at)")
        cursor.execute("CREATE INDEX idx_sessions_active ON user_sessions(user_id, is_revoked)")
        print("✓ Created indexes for user_sessions")

        # 8. Create audit_log table
        create_audit_log_sql = """
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id),
            username VARCHAR(100),
            action VARCHAR(100) NOT NULL,
            resource_type VARCHAR(50),
            resource_id INTEGER,
            resource_name VARCHAR(255),
            old_values TEXT,
            new_values TEXT,
            details TEXT,
            ip_address VARCHAR(50),
            user_agent TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN DEFAULT TRUE,
            error_message TEXT
        )
        """
        cursor.execute(create_audit_log_sql)
        print("✓ Created 'audit_log' table")

        # Create indexes for audit_log
        cursor.execute("CREATE INDEX idx_audit_user ON audit_log(user_id)")
        cursor.execute("CREATE INDEX idx_audit_username ON audit_log(username)")
        cursor.execute("CREATE INDEX idx_audit_action ON audit_log(action)")
        cursor.execute("CREATE INDEX idx_audit_resource ON audit_log(resource_type, resource_id)")
        cursor.execute("CREATE INDEX idx_audit_timestamp ON audit_log(timestamp)")
        cursor.execute("CREATE INDEX idx_audit_success ON audit_log(success)")
        print("✓ Created indexes for audit_log")

        # Commit the changes
        conn.commit()
        print("\nMigration completed successfully!")

        # Verify tables were created
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table'
            AND name IN ('users', 'roles', 'permissions', 'role_permissions',
                         'user_roles', 'user_location_restrictions', 'user_sessions', 'audit_log')
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Created {len(tables)} tables: {', '.join(tables)}")

        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False
    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("Running migration: Add User Management and Access Control")
    print("=" * 70)
    print()
    success = run_migration()

    if success:
        print("\n✅ Migration completed successfully!")
        print("\nNew tables created:")
        print("  - users: User accounts with authentication")
        print("  - roles: User roles (Super Admin, Administrator, Operator, Viewer)")
        print("  - permissions: Resource-based permissions (devices:view, etc.)")
        print("  - role_permissions: Role-to-permission mappings")
        print("  - user_roles: User-to-role assignments")
        print("  - user_location_restrictions: Optional location-based access")
        print("  - user_sessions: JWT token tracking and revocation")
        print("  - audit_log: Comprehensive audit trail")
        print("\nNext steps:")
        print("  1. Run the seed script: python backend/app/db/seed_auth.py")
        print("  2. Create default admin user and roles")
        print("  3. Test authentication endpoints")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
