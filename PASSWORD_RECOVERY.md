# Password Recovery Guide

## If You Get Locked Out

If you forget your password or get locked out due to too many failed login attempts, you can reset your password directly on the server.

### Quick Reset (Recommended)

From the `/home/coastal/smartvenue` directory:

```bash
./reset-password.sh <username> <new_password>
```

**Example:**
```bash
./reset-password.sh admin MyNewPassword123!
```

This script will:
- ✅ Reset your password
- ✅ Unlock your account
- ✅ Clear failed login attempts
- ✅ Activate the account if it was deactivated
- ✅ Remove the "must change password" requirement

### Manual Reset (Advanced)

If you prefer to run the Python script directly:

```bash
cd /home/coastal/smartvenue/backend
source ../venv/bin/activate
python3 reset_password.py <username> <new_password>
```

### Password Requirements

Your new password must meet these requirements:
- At least 8 characters long
- At least one uppercase letter (A-Z)
- At least one lowercase letter (a-z)
- At least one number (0-9)
- At least one special character (!@#$%^&*)

**Good passwords:**
- `SecurePass123!`
- `MyVenue@2025`
- `Admin#Password1`

**Bad passwords:**
- `password` (too simple, no uppercase, no numbers, no special chars)
- `12345678` (no letters)
- `Password` (no numbers or special chars)

### Security Notes

⚠️ **Important Security Considerations:**

1. **SSH Access Required** - You need SSH/terminal access to the server to run these scripts
2. **Virtual Environment** - The scripts automatically activate the Python virtual environment
3. **Direct Database Access** - These scripts bypass the API and modify the database directly
4. **No Authentication** - Anyone with SSH access can reset any password (keep your server secure!)
5. **Audit Trail** - Password resets via this method are NOT logged in the audit system

### Troubleshooting

**"Virtual environment not found"**
```bash
# Check if venv exists
ls /home/coastal/smartvenue/venv

# If missing, recreate it
cd /home/coastal/smartvenue
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

**"User not found"**
```bash
# List all users in the database
cd /home/coastal/smartvenue/backend
source ../venv/bin/activate
sqlite3 ../smartvenue.db "SELECT id, username, email, is_active FROM users;"
```

**"Permission denied"**
```bash
# Make sure the script is executable
chmod +x /home/coastal/smartvenue/reset-password.sh
```

### Default Admin Account

The system comes with a default admin account:
- **Username:** `admin`
- **Password:** `admin`
- **Permissions:** Full superuser access

If all else fails, you can reset the admin account:
```bash
./reset-password.sh admin admin
```

### Prevention Tips

To avoid getting locked out:

1. **Use a Password Manager** - Store your password securely
2. **Document Your Credentials** - Keep them in a safe place
3. **Create Multiple Admin Accounts** - Have a backup admin account
4. **Set Strong Passwords** - But ones you can remember or retrieve
5. **Keep SSH Access** - Always maintain server access for recovery

## Need Help?

If you're still locked out or need assistance:

1. Check the server logs: `/tmp/backend.log`
2. Verify the database exists: `/home/coastal/smartvenue/smartvenue.db`
3. Check if the backend is running: `ps aux | grep uvicorn`
4. Review this guide carefully for troubleshooting steps

---

**Last Updated:** 2025-10-10
