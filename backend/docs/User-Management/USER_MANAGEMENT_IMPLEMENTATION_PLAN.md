# TapCommand User Management & Access Control Implementation Plan

## Executive Summary

This document outlines the complete implementation plan for adding enterprise-grade user management and role-based access control (RBAC) to the TapCommand IR Control System. The system currently has no authentication or authorization, making this a critical security enhancement.

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [System Architecture](#system-architecture)
3. [Role Definitions](#role-definitions)
4. [Permission Model](#permission-model)
5. [Database Schema](#database-schema)
6. [API Changes](#api-changes)
7. [Frontend Changes](#frontend-changes)
8. [Implementation Roadmap](#implementation-roadmap)
9. [Security Considerations](#security-considerations)
10. [Testing Strategy](#testing-strategy)

---

## Current State Analysis

### Published Pages & Features

#### **1. Devices Page** (`/devices`)
- List of all connected IR devices/ports with filtering and sorting
- Filter by location, tags, device type
- View device details (expanded view)
- Select/deselect devices (bulk operations)
- Navigate to IR Senders configuration

#### **2. IR Senders Page** (`/ir-senders`)
- Discovered and managed IR sender hardware
- Add devices to management
- Remove devices from management
- Configure IR ports (device naming, tags, locations)
- Update device settings (location, API key, name)
- Health check/sync device status
- Forget discovered devices

#### **3. YAML Builder Page** (`/yaml-builder`)
- Device firmware template builder
- Select IR device libraries from hierarchy
- Assign libraries to ports
- Preview generated YAML
- Compile firmware (ESPHome)
- Download compiled binaries
- Save YAML to server/local

#### **4. Settings Page** (`/settings`)
- **YAML Templates Tab**: Edit base templates, WiFi config, OTA settings
- **Tag Management Tab**: Create, edit, delete device tags
- **Channels Tab**: Manage TV channels by area/location

#### **5. Backend API Routes**
- `/api/v1/devices` - Device discovery and listing
- `/api/v1/management` - Device management (CRUD)
- `/api/v1/admin` - Database admin interface
- `/api/v1/ir-codes` - IR code management
- `/api/v1/templates` - Template and firmware building
- `/api/v1/settings` - Settings and tags
- `/api/v1/channels` - Channel management
- `/api/v1/ir-libraries` - IR device libraries
- `/api/v1/commands` - Command queue and execution
- `/api/v1/ir-capture` - IR signal capture
- `/api/v1/schedules` - Schedule management

### Current Security Status

**⚠️ CRITICAL FINDING**: The application currently has **NO authentication or authorization system**. All endpoints are publicly accessible.

---

## System Architecture

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   FRONTEND (React)                        │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │   Login    │  │    Pages   │  │   Admin    │         │
│  │   Page     │  │   (RBAC)   │  │    UI      │         │
│  └────────────┘  └────────────┘  └────────────┘         │
│         │                │                │               │
│         └────────────────┴────────────────┘               │
│                          │                                │
│                  JWT Token Auth                           │
└──────────────────────────┼───────────────────────────────┘
                           │
┌──────────────────────────┼───────────────────────────────┐
│                   BACKEND (FastAPI)                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │    Auth    │  │Permission  │  │   Audit    │         │
│  │ Middleware │  │  Checker   │  │   Logger   │         │
│  └────────────┘  └────────────┘  └────────────┘         │
│         │                │                │               │
│         └────────────────┴────────────────┘               │
│                          │                                │
│                   API Endpoints                           │
│                   (Protected)                             │
└──────────────────────────┼───────────────────────────────┘
                           │
┌──────────────────────────┼───────────────────────────────┐
│                    DATABASE (SQLite)                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │   Users    │  │   Roles    │  │ Audit Log  │         │
│  │            │  │            │  │            │         │
│  └────────────┘  └────────────┘  └────────────┘         │
└───────────────────────────────────────────────────────────┘
```

### Authentication Flow

```
1. User enters credentials → Frontend
2. Frontend sends POST /api/v1/auth/login
3. Backend validates credentials
4. Backend generates JWT access + refresh tokens
5. Frontend stores tokens (memory + httpOnly cookie)
6. Frontend includes JWT in Authorization header for all requests
7. Backend middleware validates JWT and extracts user/permissions
8. API endpoint checks required permissions
9. Action is logged to audit log
```

---

## Role Definitions

### **Super Admin** (System Administrator)

**Description**: Full system access for IT administrators and system owners.

**Permissions**: ALL

**Use Cases**:
- Initial system setup
- User management
- System configuration
- Compliance audits
- Troubleshooting

**Restrictions**: None

---

### **Administrator** (Venue Manager)

**Description**: Full venue management without user administration capabilities.

**Permissions**:
- ✅ Manage all devices and configurations
- ✅ Add/remove IR senders and configure hardware
- ✅ Create/edit/delete: tags, channels, schedules
- ✅ Compile and deploy firmware
- ✅ Configure IR ports, capture IR signals
- ✅ Health checks and diagnostics
- ✅ View reports and audit logs
- ❌ Manage users or roles
- ❌ Access database directly

**Use Cases**:
- Day-to-day venue management
- Device installation and setup
- Template customization
- Problem resolution

---

### **Operator** (Daily Operations)

**Description**: Day-to-day operational control without destructive or configuration-changing abilities.

**Permissions**:
- ✅ View all devices and status
- ✅ Send commands to devices
- ✅ Create and modify schedules
- ✅ Configure device assignments (ports, locations, names)
- ✅ Edit channel configurations
- ✅ Run manual schedules
- ✅ Health checks
- ❌ Delete devices
- ❌ Add/remove IR senders
- ❌ Modify templates or compile firmware
- ❌ Manage users or tags

**Use Cases**:
- Shift managers
- Front desk staff
- Event coordinators

---

### **Viewer** (Read-Only)

**Description**: Read-only access for monitoring and reporting.

**Permissions**:
- ✅ View all pages and configurations
- ✅ View device status and health
- ✅ View schedules and channel lists
- ❌ Modify anything
- ❌ Send commands

**Use Cases**:
- Monitoring staff
- Reporting/analytics users
- Auditors
- Training environments

---

### **Custom Roles** (Flexible)

**Description**: Admin-defined roles with granular permission selection.

**Examples**:
- **Bar Manager**: Full control over "Bar" location only
- **Restaurant Operator**: Command + schedule access for "Restaurant" only
- **Night Auditor**: View-only access during specific hours
- **Maintenance Tech**: IR capture and firmware compilation only

---

## Permission Model

### Resource-Based Permissions

Permissions follow the format: `resource:action`

#### **Devices** (`devices`)
- `devices:view` - View device list and details
- `devices:edit` - Edit device configuration
- `devices:configure` - Configure device settings (non-destructive)
- `devices:delete` - Delete devices
- `devices:command` - Send commands to devices

#### **IR Senders** (`ir_senders`)
- `ir_senders:view` - View IR sender hardware
- `ir_senders:add` - Add devices to management
- `ir_senders:edit` - Edit device settings
- `ir_senders:configure` - Configure IR ports
- `ir_senders:delete` - Remove from management
- `ir_senders:health_check` - Run health checks

#### **Templates** (`templates`)
- `templates:view` - View templates and YAML
- `templates:edit` - Edit template configuration
- `templates:compile` - Compile firmware
- `templates:deploy` - Download/deploy binaries

#### **Tags** (`tags`)
- `tags:view` - View tags
- `tags:create` - Create new tags
- `tags:edit` - Edit existing tags
- `tags:delete` - Delete tags

#### **Channels** (`channels`)
- `channels:view` - View channel lists
- `channels:edit` - Edit channel configuration
- `channels:enable_disable` - Enable/disable channels
- `channels:create_inhouse` - Create custom channels
- `channels:delete_inhouse` - Delete custom channels

#### **Schedules** (`schedules`)
- `schedules:view` - View schedules
- `schedules:create` - Create schedules
- `schedules:edit` - Edit schedules
- `schedules:delete` - Delete schedules
- `schedules:run_manual` - Manually trigger schedules

#### **IR Capture** (`ir_capture`)
- `ir_capture:capture` - Capture IR signals
- `ir_capture:save` - Save captured signals
- `ir_capture:import` - Import signal libraries

#### **Settings** (`settings`)
- `settings:view` - View settings
- `settings:edit_wifi` - Edit WiFi configuration
- `settings:edit_ota` - Edit OTA settings
- `settings:edit_api_keys` - Edit API keys

#### **Users** (`users`)
- `users:view` - View user list
- `users:create` - Create new users
- `users:edit` - Edit user details
- `users:delete` - Delete users
- `users:assign_roles` - Assign/remove roles

#### **Audit** (`audit`)
- `audit:view` - View audit logs
- `audit:export` - Export audit logs

#### **Admin** (`admin`)
- `admin:database` - Access database admin interface
- `admin:system` - System configuration

### Permission Matrix by Role

| Permission | Super Admin | Administrator | Operator | Viewer |
|-----------|------------|---------------|----------|--------|
| **Devices** | | | | |
| `devices:view` | ✅ | ✅ | ✅ | ✅ |
| `devices:edit` | ✅ | ✅ | ✅ | ❌ |
| `devices:configure` | ✅ | ✅ | ✅ | ❌ |
| `devices:delete` | ✅ | ✅ | ❌ | ❌ |
| `devices:command` | ✅ | ✅ | ✅ | ❌ |
| **IR Senders** | | | | |
| `ir_senders:view` | ✅ | ✅ | ✅ | ✅ |
| `ir_senders:add` | ✅ | ✅ | ❌ | ❌ |
| `ir_senders:edit` | ✅ | ✅ | ❌ | ❌ |
| `ir_senders:configure` | ✅ | ✅ | ✅ | ❌ |
| `ir_senders:delete` | ✅ | ✅ | ❌ | ❌ |
| `ir_senders:health_check` | ✅ | ✅ | ✅ | ❌ |
| **Templates** | | | | |
| `templates:view` | ✅ | ✅ | ✅ | ✅ |
| `templates:edit` | ✅ | ✅ | ❌ | ❌ |
| `templates:compile` | ✅ | ✅ | ❌ | ❌ |
| `templates:deploy` | ✅ | ✅ | ❌ | ❌ |
| **Tags** | | | | |
| `tags:view` | ✅ | ✅ | ✅ | ✅ |
| `tags:create` | ✅ | ✅ | ❌ | ❌ |
| `tags:edit` | ✅ | ✅ | ❌ | ❌ |
| `tags:delete` | ✅ | ✅ | ❌ | ❌ |
| **Channels** | | | | |
| `channels:view` | ✅ | ✅ | ✅ | ✅ |
| `channels:edit` | ✅ | ✅ | ✅ | ❌ |
| `channels:enable_disable` | ✅ | ✅ | ✅ | ❌ |
| `channels:create_inhouse` | ✅ | ✅ | ❌ | ❌ |
| `channels:delete_inhouse` | ✅ | ✅ | ❌ | ❌ |
| **Schedules** | | | | |
| `schedules:view` | ✅ | ✅ | ✅ | ✅ |
| `schedules:create` | ✅ | ✅ | ✅ | ❌ |
| `schedules:edit` | ✅ | ✅ | ✅ | ❌ |
| `schedules:delete` | ✅ | ✅ | ❌ | ❌ |
| `schedules:run_manual` | ✅ | ✅ | ✅ | ❌ |
| **IR Capture** | | | | |
| `ir_capture:capture` | ✅ | ✅ | ❌ | ❌ |
| `ir_capture:save` | ✅ | ✅ | ❌ | ❌ |
| `ir_capture:import` | ✅ | ✅ | ❌ | ❌ |
| **Settings** | | | | |
| `settings:view` | ✅ | ✅ | ✅ | ✅ |
| `settings:edit_wifi` | ✅ | ✅ | ❌ | ❌ |
| `settings:edit_ota` | ✅ | ✅ | ❌ | ❌ |
| `settings:edit_api_keys` | ✅ | ✅ | ❌ | ❌ |
| **Users** | | | | |
| `users:view` | ✅ | ❌ | ❌ | ❌ |
| `users:create` | ✅ | ❌ | ❌ | ❌ |
| `users:edit` | ✅ | ❌ | ❌ | ❌ |
| `users:delete` | ✅ | ❌ | ❌ | ❌ |
| `users:assign_roles` | ✅ | ❌ | ❌ | ❌ |
| **Audit** | | | | |
| `audit:view` | ✅ | ✅ | ❌ | ❌ |
| `audit:export` | ✅ | ❌ | ❌ | ❌ |
| **Admin** | | | | |
| `admin:database` | ✅ | ❌ | ❌ | ❌ |
| `admin:system` | ✅ | ❌ | ❌ | ❌ |

---

## Database Schema

### New Tables

#### **users**
```sql
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
    UNIQUE(username),
    CHECK(LENGTH(username) >= 3),
    CHECK(LENGTH(password_hash) > 0)
);

-- Indexes
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);
```

#### **roles**
```sql
CREATE TABLE roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_system_role BOOLEAN DEFAULT FALSE,  -- Cannot be deleted
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    UNIQUE(name)
);

-- Indexes
CREATE INDEX idx_roles_name ON roles(name);
```

#### **permissions**
```sql
CREATE TABLE permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource VARCHAR(50) NOT NULL,  -- 'devices', 'tags', 'channels', etc.
    action VARCHAR(50) NOT NULL,    -- 'view', 'edit', 'delete', 'command'
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(resource, action)
);

-- Indexes
CREATE INDEX idx_permissions_resource ON permissions(resource);
CREATE UNIQUE INDEX idx_permissions_resource_action ON permissions(resource, action);
```

#### **role_permissions**
```sql
CREATE TABLE role_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by INTEGER REFERENCES users(id),
    UNIQUE(role_id, permission_id)
);

-- Indexes
CREATE INDEX idx_role_permissions_role ON role_permissions(role_id);
CREATE INDEX idx_role_permissions_permission ON role_permissions(permission_id);
```

#### **user_roles**
```sql
CREATE TABLE user_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by INTEGER REFERENCES users(id),
    expires_at TIMESTAMP,  -- Optional: for temporary role assignments
    UNIQUE(user_id, role_id)
);

-- Indexes
CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role_id);
CREATE INDEX idx_user_roles_expires ON user_roles(expires_at);
```

#### **user_location_restrictions** (Optional)
```sql
CREATE TABLE user_location_restrictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    location VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    UNIQUE(user_id, location)
);

-- Indexes
CREATE INDEX idx_location_restrictions_user ON user_location_restrictions(user_id);
```

#### **user_sessions**
```sql
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
);

-- Indexes
CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_sessions_token ON user_sessions(token_hash);
CREATE INDEX idx_sessions_refresh ON user_sessions(refresh_token_hash);
CREATE INDEX idx_sessions_expires ON user_sessions(expires_at);
CREATE INDEX idx_sessions_active ON user_sessions(user_id, is_revoked);
```

#### **audit_log**
```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    username VARCHAR(100),  -- Denormalized for deleted users
    action VARCHAR(100) NOT NULL,       -- 'device.edit', 'schedule.create', etc.
    resource_type VARCHAR(50),          -- 'device', 'schedule', etc.
    resource_id INTEGER,
    resource_name VARCHAR(255),         -- Human-readable resource identifier
    old_values JSON,                    -- Previous state (for updates)
    new_values JSON,                    -- New state (for creates/updates)
    details JSON,                       -- Additional context
    ip_address VARCHAR(50),
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

-- Indexes
CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_action ON audit_log(action);
CREATE INDEX idx_audit_resource ON audit_log(resource_type, resource_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_success ON audit_log(success);
```

### Seed Data (Initial Setup)

```python
# Default permissions
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

# Default roles with permissions
ROLES = {
    'Super Admin': {
        'description': 'Full system access',
        'is_system': True,
        'permissions': '*'  # All permissions
    },
    'Administrator': {
        'description': 'Full venue management',
        'is_system': True,
        'permissions': [
            'devices:*', 'ir_senders:*', 'templates:*', 'tags:*',
            'channels:*', 'schedules:*', 'ir_capture:*', 'settings:*',
            'audit:view'
        ]
    },
    'Operator': {
        'description': 'Day-to-day operations',
        'is_system': True,
        'permissions': [
            'devices:view', 'devices:edit', 'devices:configure', 'devices:command',
            'ir_senders:view', 'ir_senders:configure', 'ir_senders:health_check',
            'templates:view', 'tags:view', 'channels:view', 'channels:edit',
            'channels:enable_disable', 'schedules:view', 'schedules:create',
            'schedules:edit', 'schedules:run_manual', 'settings:view'
        ]
    },
    'Viewer': {
        'description': 'Read-only access',
        'is_system': True,
        'permissions': [
            'devices:view', 'ir_senders:view', 'templates:view', 'tags:view',
            'channels:view', 'schedules:view', 'settings:view'
        ]
    }
}

# Default admin user (password: admin - MUST BE CHANGED)
DEFAULT_ADMIN = {
    'username': 'admin',
    'email': 'admin@tapcommand.local',
    'password': 'admin',  # Will be hashed
    'full_name': 'System Administrator',
    'is_superuser': True,
    'must_change_password': True
}
```

---

## API Changes

### New Authentication Endpoints

#### **POST /api/v1/auth/login**
```python
Request:
{
    "username": "admin",
    "password": "password123"
}

Response (200 OK):
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer",
    "expires_in": 1800,  # 30 minutes
    "user": {
        "id": 1,
        "username": "admin",
        "email": "admin@tapcommand.local",
        "full_name": "System Administrator",
        "roles": ["Super Admin"],
        "permissions": ["*"]
    }
}

Response (401 Unauthorized):
{
    "detail": "Incorrect username or password"
}

Response (403 Forbidden):
{
    "detail": "Account is locked. Try again in 15 minutes."
}
```

#### **POST /api/v1/auth/refresh**
```python
Request:
{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}

Response (200 OK):
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer",
    "expires_in": 1800
}
```

#### **POST /api/v1/auth/logout**
```python
Request:
Headers: Authorization: Bearer <access_token>

Response (200 OK):
{
    "message": "Successfully logged out"
}
```

#### **GET /api/v1/auth/me**
```python
Request:
Headers: Authorization: Bearer <access_token>

Response (200 OK):
{
    "id": 1,
    "username": "admin",
    "email": "admin@tapcommand.local",
    "full_name": "System Administrator",
    "is_active": true,
    "is_superuser": true,
    "roles": [
        {
            "id": 1,
            "name": "Super Admin",
            "description": "Full system access"
        }
    ],
    "permissions": ["*"],
    "location_restrictions": [],
    "last_login": "2025-10-03T14:30:00Z",
    "created_at": "2025-10-01T10:00:00Z"
}
```

#### **POST /api/v1/auth/change-password**
```python
Request:
{
    "current_password": "old_password",
    "new_password": "new_password"
}

Response (200 OK):
{
    "message": "Password changed successfully"
}
```

### New User Management Endpoints

#### **GET /api/v1/users**
```python
Permission: users:view

Query params:
- limit: int (default: 50)
- offset: int (default: 0)
- search: str (username, email, full_name)
- role_id: int
- is_active: bool

Response (200 OK):
{
    "users": [
        {
            "id": 1,
            "username": "admin",
            "email": "admin@tapcommand.local",
            "full_name": "System Administrator",
            "is_active": true,
            "is_superuser": true,
            "roles": ["Super Admin"],
            "last_login": "2025-10-03T14:30:00Z",
            "created_at": "2025-10-01T10:00:00Z"
        }
    ],
    "total": 1
}
```

#### **POST /api/v1/users**
```python
Permission: users:create

Request:
{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "secure_password123",
    "full_name": "John Doe",
    "role_ids": [2],  # Administrator
    "is_active": true,
    "must_change_password": false,
    "location_restrictions": ["Bar", "Restaurant"]  # Optional
}

Response (201 Created):
{
    "id": 2,
    "username": "john_doe",
    "email": "john@example.com",
    "full_name": "John Doe",
    "is_active": true,
    "roles": ["Administrator"],
    "created_at": "2025-10-03T15:00:00Z"
}
```

#### **PUT /api/v1/users/{user_id}**
```python
Permission: users:edit

Request:
{
    "email": "newemail@example.com",
    "full_name": "John Doe Jr.",
    "is_active": true,
    "role_ids": [2, 3]  # Administrator + Operator
}

Response (200 OK):
{
    "id": 2,
    "username": "john_doe",
    "email": "newemail@example.com",
    "full_name": "John Doe Jr.",
    "is_active": true,
    "roles": ["Administrator", "Operator"],
    "updated_at": "2025-10-03T15:30:00Z"
}
```

#### **DELETE /api/v1/users/{user_id}**
```python
Permission: users:delete

Response (200 OK):
{
    "message": "User deleted successfully"
}
```

#### **POST /api/v1/users/{user_id}/reset-password**
```python
Permission: users:edit

Request:
{
    "new_password": "temporary_password123",
    "must_change_password": true
}

Response (200 OK):
{
    "message": "Password reset successfully"
}
```

### New Role Management Endpoints

#### **GET /api/v1/roles**
```python
Permission: users:view

Response (200 OK):
{
    "roles": [
        {
            "id": 1,
            "name": "Super Admin",
            "description": "Full system access",
            "is_system_role": true,
            "user_count": 1,
            "permission_count": 45,
            "permissions": ["*"]
        }
    ],
    "total": 4
}
```

#### **POST /api/v1/roles**
```python
Permission: users:assign_roles

Request:
{
    "name": "Bar Manager",
    "description": "Manage bar devices",
    "permission_ids": [1, 2, 3, 5, 10]
}

Response (201 Created):
{
    "id": 5,
    "name": "Bar Manager",
    "description": "Manage bar devices",
    "is_system_role": false,
    "created_at": "2025-10-03T16:00:00Z"
}
```

#### **PUT /api/v1/roles/{role_id}**
```python
Permission: users:assign_roles

Request:
{
    "description": "Updated description",
    "permission_ids": [1, 2, 3, 5, 10, 11]
}

Response (200 OK):
{
    "id": 5,
    "name": "Bar Manager",
    "description": "Updated description",
    "permission_count": 6,
    "updated_at": "2025-10-03T16:30:00Z"
}
```

#### **DELETE /api/v1/roles/{role_id}**
```python
Permission: users:assign_roles

Response (200 OK):
{
    "message": "Role deleted successfully"
}

Response (400 Bad Request):
{
    "detail": "Cannot delete system role"
}
```

### New Audit Log Endpoints

#### **GET /api/v1/audit**
```python
Permission: audit:view

Query params:
- limit: int (default: 100)
- offset: int (default: 0)
- user_id: int
- action: str
- resource_type: str
- start_date: datetime
- end_date: datetime
- success: bool

Response (200 OK):
{
    "logs": [
        {
            "id": 1,
            "user_id": 1,
            "username": "admin",
            "action": "device.edit",
            "resource_type": "ManagedDevice",
            "resource_id": 5,
            "resource_name": "Main Bar TV",
            "old_values": {"location": "Bar"},
            "new_values": {"location": "Main Bar"},
            "ip_address": "192.168.1.100",
            "timestamp": "2025-10-03T14:30:00Z",
            "success": true
        }
    ],
    "total": 150
}
```

#### **GET /api/v1/audit/export**
```python
Permission: audit:export

Query params: (same as GET /api/v1/audit)
- format: str (csv, json)

Response (200 OK):
Content-Type: text/csv or application/json
<file download>
```

### Protected Endpoint Modifications

All existing endpoints will be modified to include:

1. **Authentication requirement**: JWT token in `Authorization: Bearer <token>` header
2. **Permission check**: Validate user has required permission
3. **Audit logging**: Log all state-changing operations
4. **Location filtering** (optional): Filter results by user's location restrictions

Example modification:

```python
# Before
@router.get("/api/v1/management/managed")
def get_managed_devices(db: Session = Depends(get_db)):
    devices = db.query(ManagedDevice).all()
    return devices

# After
@router.get("/api/v1/management/managed")
@require_permission("ir_senders:view")
def get_managed_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(ManagedDevice)

    # Apply location restrictions if user has them
    if current_user.has_location_restrictions():
        locations = current_user.get_allowed_locations(db)
        query = query.filter(ManagedDevice.location.in_(locations))

    devices = query.all()
    return devices
```

---

## Frontend Changes

### New Pages

#### **1. Login Page** (`/login`)

**Components**:
- Username/email input
- Password input (with show/hide toggle)
- "Remember me" checkbox
- Login button
- "Forgot password?" link (future)
- Error message display

**Features**:
- Form validation
- Loading state during authentication
- Redirect to dashboard after successful login
- Display lock countdown if account is locked

**Location**: `/frontend/src/pages/LoginPage.tsx`

---

#### **2. User Management Page** (`/admin/users`)

**Tabs**:
1. **Users Tab**
   - User list with search/filter
   - Create user button
   - Edit/delete actions per user
   - User detail modal

2. **Roles Tab**
   - Role list
   - Create role button
   - Edit/delete actions per role
   - Permission assignment interface

3. **Audit Logs Tab**
   - Log viewer with filters
   - Export button
   - Log detail expansion

**Components**:
- `UserList` - User table with pagination
- `UserForm` - Create/edit user modal
- `RoleList` - Role table
- `RoleForm` - Create/edit role modal
- `PermissionMatrix` - Visual permission editor
- `AuditLogViewer` - Log table with filters

**Location**: `/frontend/src/pages/UserManagementPage.tsx`

---

### Authentication Context

**Location**: `/frontend/src/contexts/AuthContext.tsx`

```typescript
interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  hasPermission: (permission: string) => boolean;
  hasRole: (role: string) => boolean;
  canAccessLocation: (location: string) => boolean;
}
```

---

### Permission Hooks

**Location**: `/frontend/src/hooks/usePermission.ts`

```typescript
// Check single permission
const canEdit = usePermission('devices:edit');

// Check multiple permissions (OR)
const canModify = usePermissions(['devices:edit', 'devices:delete']);

// Check multiple permissions (AND)
const canFullyManage = usePermissions(['devices:edit', 'devices:delete'], 'all');

// Check role
const isAdmin = useRole('Administrator');
```

---

### Protected Routes

**Location**: `/frontend/src/components/ProtectedRoute.tsx`

```typescript
<ProtectedRoute permission="users:view">
  <UserManagementPage />
</ProtectedRoute>

<ProtectedRoute role="Super Admin">
  <DatabaseAdminPage />
</ProtectedRoute>
```

---

### UI Component Modifications

All existing pages will be modified to:

1. **Hide/disable features** based on permissions
2. **Show permission tooltips** explaining why actions are unavailable
3. **Filter data** based on location restrictions
4. **Display user info** in header (username, role badge)

Example modifications:

```typescript
// Before
<button onClick={handleDelete}>Delete Device</button>

// After
<button
  onClick={handleDelete}
  disabled={!hasPermission('devices:delete')}
  title={!hasPermission('devices:delete') ? 'You do not have permission to delete devices' : ''}
>
  Delete Device
</button>
```

---

### Header Modifications

**Location**: `/frontend/src/App.tsx` (header section)

**Add**:
- User avatar/initials
- Username display
- Role badge(s)
- Dropdown menu:
  - Profile
  - Change Password
  - Logout
- Admin menu item (Super Admin only)

---

## Implementation Roadmap

### **Phase 1: Backend Foundation** (Week 1)

**Tasks**:
1. ✅ Create database schema and migration scripts
2. ✅ Create SQLAlchemy models for users, roles, permissions
3. ✅ Implement password hashing utilities (bcrypt)
4. ✅ Create seed data script for default roles and permissions
5. ✅ Write unit tests for models

**Deliverables**:
- Database migration file: `/backend/migrations/add_user_management.py`
- Model files: `/backend/app/models/auth.py`
- Seed script: `/backend/app/db/seed_auth.py`
- Test file: `/backend/tests/test_auth_models.py`

**Estimated Time**: 3-4 days

---

### **Phase 2: Authentication Implementation** (Week 1-2)

**Tasks**:
1. ✅ Implement JWT token generation and validation
2. ✅ Create authentication endpoints (login, logout, refresh, me)
3. ✅ Implement password change endpoint
4. ✅ Add rate limiting for login attempts
5. ✅ Implement account locking after failed attempts
6. ✅ Write authentication middleware
7. ✅ Write unit and integration tests

**Deliverables**:
- Auth utilities: `/backend/app/core/security.py`
- Auth router: `/backend/app/routers/auth.py`
- Auth dependencies: `/backend/app/api/dependencies.py`
- Tests: `/backend/tests/test_auth.py`

**Estimated Time**: 4-5 days

---

### **Phase 3: Authorization & Permissions** (Week 2)

**Tasks**:
1. ✅ Implement permission checking logic
2. ✅ Create `@require_permission` decorator
3. ✅ Create `get_current_user` dependency
4. ✅ Implement location-based filtering
5. ✅ Add permission checks to all existing endpoints
6. ✅ Write unit tests for permission system

**Deliverables**:
- Permission utilities: `/backend/app/core/permissions.py`
- Updated routers: All files in `/backend/app/routers/`
- Tests: `/backend/tests/test_permissions.py`

**Estimated Time**: 3-4 days

---

### **Phase 4: Audit Logging** (Week 2-3)

**Tasks**:
1. ✅ Create audit logging service
2. ✅ Add audit logging to all state-changing endpoints
3. ✅ Implement audit log query endpoint
4. ✅ Implement audit log export (CSV, JSON)
5. ✅ Write tests for audit logging

**Deliverables**:
- Audit service: `/backend/app/services/audit.py`
- Audit router: `/backend/app/routers/audit.py`
- Tests: `/backend/tests/test_audit.py`

**Estimated Time**: 2-3 days

---

### **Phase 5: User Management API** (Week 3)

**Tasks**:
1. ✅ Create user management endpoints (CRUD)
2. ✅ Create role management endpoints (CRUD)
3. ✅ Create permission listing endpoint
4. ✅ Implement user search and filtering
5. ✅ Add password reset functionality
6. ✅ Write integration tests

**Deliverables**:
- Users router: `/backend/app/routers/users.py`
- Roles router: `/backend/app/routers/roles.py`
- Tests: `/backend/tests/test_user_management.py`

**Estimated Time**: 3-4 days

---

### **Phase 6: Frontend Authentication** (Week 3-4)

**Tasks**:
1. ✅ Create Login page
2. ✅ Implement AuthContext and provider
3. ✅ Create authentication service
4. ✅ Implement token storage (localStorage + httpOnly cookies)
5. ✅ Add token refresh logic
6. ✅ Create ProtectedRoute component
7. ✅ Update App.tsx with authentication flow
8. ✅ Add header user menu

**Deliverables**:
- Login page: `/frontend/src/pages/LoginPage.tsx`
- Auth context: `/frontend/src/contexts/AuthContext.tsx`
- Auth service: `/frontend/src/services/auth.ts`
- Protected route: `/frontend/src/components/ProtectedRoute.tsx`
- Updated App: `/frontend/src/App.tsx`

**Estimated Time**: 4-5 days

---

### **Phase 7: Frontend Permission System** (Week 4)

**Tasks**:
1. ✅ Create permission hooks (usePermission, useRole)
2. ✅ Update all pages with permission checks
3. ✅ Add UI indicators for disabled features
4. ✅ Implement location filtering in device lists
5. ✅ Add role badges to user interface
6. ✅ Write component tests

**Deliverables**:
- Permission hooks: `/frontend/src/hooks/usePermission.ts`
- Updated pages: All files in `/frontend/src/pages/`
- Updated components: All files in `/frontend/src/components/`
- Tests: `/frontend/src/__tests__/permissions.test.tsx`

**Estimated Time**: 3-4 days

---

### **Phase 8: User Management UI** (Week 4-5)

**Tasks**:
1. ✅ Create User Management page
2. ✅ Implement user list with search/filter
3. ✅ Create user create/edit forms
4. ✅ Implement role management UI
5. ✅ Create permission matrix component
6. ✅ Implement audit log viewer
7. ✅ Add export functionality
8. ✅ Write component tests

**Deliverables**:
- User management page: `/frontend/src/pages/UserManagementPage.tsx`
- User components: `/frontend/src/components/users/`
- Role components: `/frontend/src/components/roles/`
- Audit components: `/frontend/src/components/audit/`
- Tests: `/frontend/src/__tests__/user_management.test.tsx`

**Estimated Time**: 5-6 days

---

### **Phase 9: Testing & Security** (Week 5-6)

**Tasks**:
1. ✅ Comprehensive security testing
2. ✅ Penetration testing (OWASP Top 10)
3. ✅ Performance testing (auth overhead)
4. ✅ Integration testing (end-to-end flows)
5. ✅ Fix identified vulnerabilities
6. ✅ Code review and refactoring
7. ✅ Load testing for concurrent users

**Deliverables**:
- Security audit report
- Performance test results
- Fixed vulnerabilities
- Updated tests

**Estimated Time**: 5-7 days

---

### **Phase 10: Documentation & Training** (Week 6)

**Tasks**:
1. ✅ Write API documentation (OpenAPI/Swagger)
2. ✅ Create user guide for admins
3. ✅ Create user guide for operators
4. ✅ Document deployment process
5. ✅ Create troubleshooting guide
6. ✅ Record demo videos
7. ✅ Prepare training materials

**Deliverables**:
- `/docs/USER_MANAGEMENT_GUIDE.md`
- `/docs/ADMIN_GUIDE.md`
- `/docs/API_AUTHENTICATION.md`
- `/docs/DEPLOYMENT_AUTH.md`
- Demo videos

**Estimated Time**: 3-4 days

---

### **Total Estimated Time**: 5-6 weeks

---

## Security Considerations

### Authentication Security

1. **Password Requirements**:
   - Minimum 8 characters
   - At least one uppercase letter
   - At least one lowercase letter
   - At least one number
   - At least one special character
   - Cannot be same as username
   - Cannot be in common password list

2. **Password Storage**:
   - Use bcrypt with salt rounds ≥ 12
   - Never store plaintext passwords
   - Hash passwords before database storage

3. **JWT Tokens**:
   - Use strong secret key (256-bit minimum)
   - Set reasonable expiration (15-30 min for access, 7-30 days for refresh)
   - Include user ID, username, roles in payload
   - Sign with HS256 or RS256 algorithm
   - Validate signature on every request

4. **Session Management**:
   - Store refresh tokens in database
   - Allow token revocation
   - Track active sessions per user
   - Implement session timeout
   - Allow admin to revoke user sessions

5. **Account Security**:
   - Lock account after 5 failed login attempts
   - Lock duration: 15 minutes (configurable)
   - Reset failed attempts on successful login
   - Log all authentication events

### Authorization Security

1. **Permission Checks**:
   - Always check permissions on backend (never trust frontend)
   - Use whitelist approach (deny by default)
   - Check permissions before database queries
   - Validate resource ownership

2. **Location Restrictions**:
   - Apply location filters at database level
   - Validate location access before any operation
   - Prevent privilege escalation via location bypass

3. **Role Hierarchy**:
   - Prevent users from assigning higher roles than they have
   - Prevent self-role-assignment exploits
   - System roles cannot be deleted or modified

### API Security

1. **Rate Limiting**:
   - Login endpoint: 5 requests per minute per IP
   - General API: 100 requests per minute per user
   - Use sliding window algorithm
   - Return 429 Too Many Requests on limit

2. **CORS**:
   - Restrict allowed origins to known frontends
   - Do not use wildcard (*) in production
   - Validate Origin header

3. **CSRF Protection**:
   - Use SameSite cookies for refresh tokens
   - Validate CSRF tokens on state-changing requests
   - Double-submit cookie pattern

4. **Input Validation**:
   - Validate all inputs on backend
   - Use Pydantic schemas for validation
   - Sanitize inputs to prevent injection attacks
   - Limit input lengths

5. **SQL Injection Prevention**:
   - Use SQLAlchemy ORM (parameterized queries)
   - Never concatenate user input into SQL
   - Validate input types

### Data Security

1. **Sensitive Data**:
   - Never log passwords or tokens
   - Mask sensitive data in audit logs
   - Encrypt API keys in database
   - Use environment variables for secrets

2. **Database Security**:
   - Use strong database password
   - Restrict database file permissions
   - Regular database backups
   - Encrypt backups

3. **Audit Logging**:
   - Log all authentication events
   - Log all authorization failures
   - Log all data modifications
   - Include IP address and user agent
   - Retain logs for compliance period

### Network Security

1. **HTTPS**:
   - Enforce HTTPS in production
   - Use valid SSL certificates
   - Implement HSTS headers
   - Redirect HTTP to HTTPS

2. **Security Headers**:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `X-XSS-Protection: 1; mode=block`
   - `Strict-Transport-Security: max-age=31536000`
   - `Content-Security-Policy: default-src 'self'`

### Frontend Security

1. **Token Storage**:
   - Store access token in memory (React state)
   - Store refresh token in httpOnly cookie
   - Never store in localStorage (XSS risk)
   - Clear tokens on logout

2. **XSS Prevention**:
   - Use React's built-in escaping
   - Sanitize user-generated content
   - Use Content Security Policy
   - Validate URLs before rendering links

3. **CSRF Prevention**:
   - Include CSRF token in requests
   - Validate token on backend
   - Use SameSite cookies

---

## Testing Strategy

### Unit Tests

**Backend**:
- User model CRUD operations
- Password hashing and validation
- JWT token generation and validation
- Permission checking logic
- Role assignment logic
- Audit logging service

**Frontend**:
- AuthContext provider
- Permission hooks
- Authentication service
- Token refresh logic

### Integration Tests

**Backend**:
- Complete authentication flow (login → access protected endpoint → refresh → logout)
- User management operations
- Role management operations
- Permission enforcement across all endpoints
- Audit log creation and querying

**Frontend**:
- Login flow (login → redirect → access protected page)
- Logout flow
- Token refresh flow
- Permission-based UI rendering

### Security Tests

1. **Authentication Bypass**:
   - Attempt to access protected endpoints without token
   - Attempt to use expired tokens
   - Attempt to use invalid tokens
   - Attempt to forge tokens

2. **Authorization Bypass**:
   - Attempt to access resources without permission
   - Attempt to escalate privileges
   - Attempt to access other users' data
   - Attempt to bypass location restrictions

3. **Injection Attacks**:
   - SQL injection in all input fields
   - XSS in all input fields
   - Command injection attempts

4. **Brute Force**:
   - Attempt multiple failed logins
   - Verify account locking
   - Verify rate limiting

5. **Session Attacks**:
   - Session fixation
   - Session hijacking
   - CSRF attacks

### Performance Tests

1. **Authentication Performance**:
   - Measure login latency
   - Measure token validation overhead
   - Test concurrent login requests
   - Test token refresh performance

2. **Permission Check Performance**:
   - Measure permission check latency
   - Test impact on API response time
   - Optimize database queries for permissions

3. **Load Testing**:
   - Test with 100+ concurrent users
   - Measure database connection pool usage
   - Identify bottlenecks

### Acceptance Tests

**User Stories**:
1. As a Super Admin, I can create, edit, and delete users
2. As a Super Admin, I can assign roles to users
3. As an Administrator, I can manage devices but not users
4. As an Operator, I can send commands but not delete devices
5. As a Viewer, I can view but not modify anything
6. Users with location restrictions can only access their locations
7. All actions are logged in audit log
8. Failed login attempts lock the account

---

## Deployment Checklist

### Pre-Deployment

- [ ] Run all tests (unit, integration, security)
- [ ] Review all code changes
- [ ] Update database schema (run migrations)
- [ ] Seed default roles and permissions
- [ ] Create initial admin user
- [ ] Update environment variables
- [ ] Review security configuration
- [ ] Test backup and restore procedures

### Configuration

- [ ] Set strong JWT secret key (256-bit random)
- [ ] Set secure database password
- [ ] Configure CORS origins
- [ ] Configure rate limiting thresholds
- [ ] Set session timeout values
- [ ] Configure audit log retention period
- [ ] Set up HTTPS certificates
- [ ] Configure security headers

### Post-Deployment

- [ ] Verify login functionality
- [ ] Verify permission enforcement
- [ ] Test all user roles
- [ ] Verify audit logging
- [ ] Change default admin password
- [ ] Create production users
- [ ] Document admin procedures
- [ ] Train administrators
- [ ] Monitor error logs
- [ ] Review security logs

### Monitoring

- [ ] Set up login failure monitoring
- [ ] Set up unauthorized access alerts
- [ ] Monitor API response times
- [ ] Track concurrent user sessions
- [ ] Review audit logs regularly
- [ ] Monitor database size (audit logs)
- [ ] Set up automated backups

---

## Maintenance Tasks

### Daily

- Review failed login attempts
- Monitor unauthorized access attempts
- Check for locked accounts
- Review system errors

### Weekly

- Review audit logs for suspicious activity
- Check user session counts
- Review permission usage
- Backup database

### Monthly

- Review user accounts (remove inactive)
- Review roles and permissions (cleanup unused)
- Rotate API keys
- Update security patches
- Review audit log retention
- Performance analysis

### Quarterly

- Security audit
- Penetration testing
- User access review
- Update documentation
- Review and update passwords

---

## Appendix

### File Structure

```
tapcommand/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── dependencies.py          # NEW: Auth dependencies
│   │   ├── core/
│   │   │   ├── security.py              # NEW: JWT, password hashing
│   │   │   └── permissions.py           # NEW: Permission checking
│   │   ├── models/
│   │   │   └── auth.py                  # NEW: User, Role, Permission models
│   │   ├── routers/
│   │   │   ├── auth.py                  # NEW: Authentication endpoints
│   │   │   ├── users.py                 # NEW: User management
│   │   │   ├── roles.py                 # NEW: Role management
│   │   │   └── audit.py                 # NEW: Audit log endpoints
│   │   ├── services/
│   │   │   └── audit.py                 # NEW: Audit logging service
│   │   └── db/
│   │       └── seed_auth.py             # NEW: Seed auth data
│   ├── migrations/
│   │   └── add_user_management.py       # NEW: Database migration
│   └── tests/
│       ├── test_auth.py                 # NEW: Auth tests
│       ├── test_permissions.py          # NEW: Permission tests
│       └── test_user_management.py      # NEW: User mgmt tests
├── frontend/
│   └── src/
│       ├── contexts/
│       │   └── AuthContext.tsx          # NEW: Auth context
│       ├── hooks/
│       │   └── usePermission.ts         # NEW: Permission hooks
│       ├── services/
│       │   └── auth.ts                  # NEW: Auth API service
│       ├── components/
│       │   ├── ProtectedRoute.tsx       # NEW: Route guard
│       │   ├── users/                   # NEW: User components
│       │   ├── roles/                   # NEW: Role components
│       │   └── audit/                   # NEW: Audit components
│       └── pages/
│           ├── LoginPage.tsx            # NEW: Login page
│           └── UserManagementPage.tsx   # NEW: User admin page
└── docs/
    ├── USER_MANAGEMENT_GUIDE.md         # NEW: User guide
    ├── ADMIN_GUIDE.md                   # NEW: Admin guide
    └── API_AUTHENTICATION.md            # NEW: API docs
```

### Environment Variables

```bash
# JWT Configuration
JWT_SECRET_KEY=<256-bit-random-secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# Security
BCRYPT_ROUNDS=12
ACCOUNT_LOCK_MINUTES=15
MAX_FAILED_LOGINS=5

# Rate Limiting
LOGIN_RATE_LIMIT=5/minute
API_RATE_LIMIT=100/minute

# Session
SESSION_TIMEOUT_MINUTES=30
MAX_SESSIONS_PER_USER=5

# Audit
AUDIT_LOG_RETENTION_DAYS=90
```

### Database Migration Script

```bash
# Run migration
python backend/migrations/add_user_management.py

# Seed initial data
python backend/app/db/seed_auth.py

# Verify migration
sqlite3 backend/tapcommand.db ".schema users"
```

---

## Conclusion

This implementation plan provides a comprehensive, secure, and scalable user management and access control system for TapCommand. The phased approach ensures systematic implementation with proper testing at each stage.

**Key Benefits**:
- ✅ Enterprise-grade security
- ✅ Granular permission control
- ✅ Comprehensive audit logging
- ✅ Flexible role system
- ✅ Easy to maintain and extend
- ✅ Production-ready

**Next Steps**:
1. Review and approve this plan
2. Set up development environment
3. Begin Phase 1 implementation
4. Schedule regular progress reviews
5. Plan production deployment

---

**Document Version**: 1.0
**Last Updated**: 2025-10-03
**Author**: TapCommand Development Team
**Status**: Ready for Implementation
