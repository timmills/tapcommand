# User Management Guide

## Overview

TapCommand uses role-based access control (RBAC) to manage user permissions. This guide explains how to create users, assign roles, and manage permissions.

## Table of Contents

1. [Creating Users](#creating-users)
2. [System Roles](#system-roles)
3. [Custom Roles & Permissions](#custom-roles--permissions)
4. [Password Management](#password-management)
5. [Best Practices](#best-practices)

---

## Creating Users

### Step-by-Step Guide

1. **Navigate to Users Page**
   - Click **Users** in the sidebar navigation
   - You'll see two tabs: **Users** and **Roles & Permissions**

2. **Create New User**
   - Click the **Create User** button in the top right
   - Fill in the required fields:
     - **Username**: Unique identifier for login (cannot be changed after creation)
     - **Email**: User's email address
     - **Password**: Must be at least 8 characters
     - **Full Name**: Optional display name

3. **Assign Roles**
   - Select one or more roles from the checkboxes
   - See [System Roles](#system-roles) below for role descriptions

4. **Configure Options**
   - **Active**: Uncheck to disable the account without deleting it
   - **Must change password on next login**: Checked by default for security

5. **Save**
   - Click **Create User**
   - The user can now log in with their username and password

### Editing Existing Users

- Click **Edit** next to any user in the users table
- You can update email, full name, roles, and active status
- Username cannot be changed after creation
- To reset a password, enter a new password in the edit modal

---

## System Roles

TapCommand includes four built-in system roles with predefined permissions:

### Super Admin
**Access Level**: Full system access
**Recommended For**: System administrators and IT staff

**Permissions Include**:
- All permissions from Administrator, Operator, and Viewer roles
- User management (create, edit, delete users)
- Role management (create, edit, delete roles)
- System settings and configuration
- Full access to all features and data

### Administrator
**Access Level**: Technical and configuration access
**Recommended For**: Venue managers and technical staff

**Permissions Include**:
- All permissions from Operator and Viewer roles
- Device management (add, configure, remove devices)
- IR library management (add, edit, delete IR codes)
- Firmware updates and OTA deployment
- Discovery and diagnostics
- Database backups and recovery
- Queue diagnostics

### Operator
**Access Level**: Day-to-day operations
**Recommended For**: Staff who need to control devices and schedules

**Permissions Include**:
- All permissions from Viewer role
- Control devices (send commands, change channels, adjust volume)
- Create and manage schedules
- View system architecture and technical details
- Monitor device status

### Viewer
**Access Level**: Read-only
**Recommended For**: Staff who only need to monitor the system

**Permissions Include**:
- View devices and their status
- View schedules
- View documentation
- No ability to make changes or send commands

### Role Hierarchy

```
Super Admin (Full Access)
    ↓
Administrator (Technical + Configuration)
    ↓
Operator (Day-to-day Operations)
    ↓
Viewer (Read-only)
```

Users can have **multiple roles**, and their effective permissions are the **union** of all assigned roles.

---

## Custom Roles & Permissions

For advanced use cases, you can create custom roles with specific permissions.

### Creating Custom Roles

1. **Switch to Roles & Permissions Tab**
   - Navigate to **Users** page
   - Click the **Roles & Permissions** tab

2. **Create New Role**
   - Click **Create Role**
   - Enter a name and description
   - Select specific permissions from the list

3. **Permission Groups**
   - Permissions are organized by resource type:
     - **Devices**: View, create, update, delete devices
     - **IR Senders**: Manage IR controllers
     - **IR Libraries**: Manage IR code libraries
     - **Templates**: Manage command templates
     - **Schedules**: View and manage schedules
     - **Users**: User management (admin only)
     - **Roles**: Role management (admin only)
     - And more...

4. **Bulk Selection**
   - Use **Select All** / **Deselect All** for each resource group
   - Or select individual permissions as needed

### Editing System Roles

- System role names cannot be changed (Super Admin, Administrator, Operator, Viewer)
- System roles cannot be deleted
- You can modify permissions for system roles if needed

### Deleting Custom Roles

- Only custom roles can be deleted
- Users with the deleted role will lose those permissions
- Consider reassigning users before deleting a role

---

## Password Management

### Password Requirements

- Minimum 8 characters
- No maximum length limit
- Should include a mix of letters, numbers, and symbols (recommended)

### Changing Passwords

**For Users**:
1. Navigate to **Settings** (if available in your role)
2. Enter current password and new password
3. Click **Update Password**

**For Administrators**:
1. Navigate to **Users** page
2. Click **Edit** next to the user
3. Enter a new password in the password field
4. Optionally check "Must change password on next login"
5. Click **Save Changes**

### Password Reset (Emergency Access)

If a user is completely locked out (forgotten password, account locked), system administrators can use the command-line password reset tool:

```bash
./reset-password.sh username
```

**Steps**:
1. SSH into the TapCommand server
2. Navigate to the TapCommand directory
3. Run the reset script with the username
4. Enter a new password when prompted
5. The script will:
   - Validate password strength
   - Update the password hash
   - Unlock the account
   - Clear failed login attempts
   - Allow the user to log in immediately

For detailed instructions, see `PASSWORD_RECOVERY.md`.

### Account Lockout

- Accounts are locked after 5 failed login attempts
- Locked accounts automatically unlock after 15 minutes
- Administrators can manually unlock by resetting the password
- Or use the command-line reset tool for immediate access

---

## Best Practices

### User Account Management

1. **Principle of Least Privilege**
   - Assign the minimum role necessary for each user
   - Don't make everyone a Super Admin

2. **Use Descriptive Usernames**
   - Use real names or email-based usernames (e.g., `john.smith` or `tim@example.com`)
   - Avoid generic names like `user1`, `admin2`

3. **Enforce Password Changes**
   - Always check "Must change password on next login" for new users
   - Periodically reset passwords for security

4. **Disable Instead of Delete**
   - Uncheck "Active" to disable accounts you might need later
   - Deleting removes all audit trail

5. **Regular Audits**
   - Review user list monthly
   - Remove or disable accounts for departed staff
   - Check role assignments are still appropriate

### Role Management

1. **Use System Roles First**
   - The four system roles cover most use cases
   - Only create custom roles for specialized workflows

2. **Document Custom Roles**
   - Use descriptive names and detailed descriptions
   - Document what each custom role is for

3. **Test Before Assigning**
   - Create a test user with the new role
   - Verify permissions work as expected
   - Then assign to real users

4. **Avoid Over-Permissioning**
   - Don't assign multiple overlapping roles
   - If a user needs more permissions, consider upgrading to the next system role

### Security Recommendations

1. **Strong Passwords**
   - Require at least 12 characters for admin accounts
   - Use a password manager

2. **Limit Super Admins**
   - Keep the number of Super Admin accounts to a minimum
   - Review Super Admin list regularly

3. **Monitor Activity**
   - Check user last login times
   - Disable accounts inactive for 90+ days

4. **Secure Password Reset Tool**
   - Restrict SSH access to trusted administrators
   - The reset script requires direct server access
   - Never share reset script output over unsecured channels

---

## Common Scenarios

### Scenario 1: New Staff Member

**Goal**: Create an account for a new venue operator

**Steps**:
1. Create user with username based on their name
2. Assign **Operator** role
3. Check "Must change password on next login"
4. Mark as **Active**
5. Send them their username and temporary password
6. They change password on first login

### Scenario 2: Temporary Access

**Goal**: Give a contractor temporary access to view devices

**Steps**:
1. Create user with contractor's name
2. Assign **Viewer** role (read-only)
3. Mark as **Active**
4. When contract ends, uncheck **Active** to disable

### Scenario 3: Promote User

**Goal**: Give an operator more permissions

**Steps**:
1. Edit the user
2. Add **Administrator** role (they keep Operator role too)
3. Or remove Operator and assign only Administrator
4. Save changes

### Scenario 4: Locked Out Super Admin

**Goal**: Recover access when the only Super Admin forgot their password

**Steps**:
1. SSH to server
2. Run `./reset-password.sh admin`
3. Enter new password
4. Log in with new password
5. Immediately change to a secure password

---

## Troubleshooting

### Can't Create Users

**Problem**: "Create User" button is greyed out or missing

**Solution**: You need the **Super Admin** role to create users. Contact your system administrator.

### User Can't Log In

**Checklist**:
- ✓ Is the account marked as **Active**?
- ✓ Is the password correct? (case-sensitive)
- ✓ Is the account locked due to failed attempts? (wait 15 minutes or reset password)
- ✓ Did they change their password if required?

### Permissions Not Working

**Problem**: User has a role but can't access features

**Solution**:
1. Check the role has the required permissions (Roles & Permissions tab)
2. User may need to log out and back in
3. Check browser console for errors
4. Verify the role is actually assigned to the user

### Can't Delete Role

**Problem**: Delete button is greyed out for a role

**Solution**: System roles (Super Admin, Administrator, Operator, Viewer) cannot be deleted. Only custom roles can be deleted.

---

## Quick Reference

### Default Admin Credentials

**Username**: `admin`
**Default Password**: Set during installation
**Role**: Super Admin

If you've lost the admin password, use the password reset script.

### Common URLs

- Users Management: `https://your-server/users`
- Documentation: `https://your-server/documentation`

### Support

For additional help:
- Check the **Documentation** page in TapCommand
- Contact your system administrator
- Review logs in `/var/log/tapcommand/` (server access required)

---

**Last Updated**: October 2025
**TapCommand Version**: 2.0+
