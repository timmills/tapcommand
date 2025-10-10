# 🛡️ TapCommand Rollback Guide

This guide provides multiple ways to safely return to the stable working state from September 2025.

## Current Branch Structure

```
stable-working-sept-2025    ← NEVER TOUCH - Permanent backup branch
├── feature/gpt-takeover    ← Original working branch
└── feature/frontend-modularization ← New development branch
```

## Rollback Methods

### Method 1: Quick Rollback to Stable Branch (Recommended)

```bash
# Switch to stable branch (this is your working state)
git checkout stable-working-sept-2025

# Restore database backup
cp backup-database-sept-2025.db backend/tapcommand.db

# If you want to continue from stable state with new branch:
git checkout -b feature/new-approach-from-stable
```

### Method 2: Reset Development Branch to Stable State

```bash
# Reset current branch to stable state (DESTRUCTIVE)
git reset --hard stable-working-sept-2025

# Or merge stable state into current branch (NON-DESTRUCTIVE)
git merge stable-working-sept-2025
```

### Method 3: Individual File Rollback

If you only want to rollback specific files:

```bash
# Rollback specific file from stable branch
git checkout stable-working-sept-2025 -- frontend/src/App.tsx

# Rollback backend template generation
git checkout stable-working-sept-2025 -- backend/app/routers/templates.py

# Rollback entire frontend directory
git checkout stable-working-sept-2025 -- frontend/
```

### Method 4: Create Backup Copy (Ultimate Safety)

```bash
# Create complete backup copy of working directory
cp -r /home/coastal/tapcommand /home/coastal/tapcommand-backup-sept2025

# Later restore from backup
rm -rf /home/coastal/tapcommand
mv /home/coastal/tapcommand-backup-sept2025 /home/coastal/tapcommand
cd /home/coastal/tapcommand
git checkout stable-working-sept-2025
```

## Current Stable State Includes:

✅ **Working Frontend**: 4-tab interface (Devices, IR Senders, YAML Builder, Settings)
✅ **Working Backend**: FastAPI with mDNS discovery, template generation
✅ **Complete Database**: 70+ IR libraries, device configs, templates (backup-database-sept-2025.db)
✅ **Database Schema**: Complete IR library management, device management
✅ **YAML Generation**: Dynamic template system with placeholder replacement
✅ **Device Discovery**: mDNS-based device detection and management
✅ **Template Builder**: Device selection → port assignment → YAML generation
✅ **Capability Reporting**: ESP devices report supported brands/commands

## Verification Commands

After rollback, verify everything works:

```bash
# Check you're on the right branch/commit
git branch -v
git log --oneline -5

# Verify services start correctly
cd backend && ./run.sh &
cd ../frontend && npm run dev &

# Test key endpoints
curl http://localhost:8000/api/v1/management/discovered
curl http://localhost:8000/api/v1/templates/device-hierarchy
```

## Emergency Contacts

**Commit Hash of Stable State**: `5f2b9be`
**Branch**: `stable-working-sept-2025`
**Date Created**: September 24, 2025

## What NOT to Do

❌ **Never** modify the `stable-working-sept-2025` branch
❌ **Never** force push to `stable-working-sept-2025`
❌ **Never** rebase the stable branch

## Development Workflow

```bash
# Safe development pattern:
git checkout stable-working-sept-2025
git checkout -b feature/my-new-feature
# Make changes...
git commit -m "My changes"

# If something breaks:
git checkout stable-working-sept-2025  # Instant rollback
```

## Archive Information

This rollback guide preserves the working state before implementing architectural improvements suggested in `COMPREHENSIVE_ANALYSIS.md`. The stable branch contains:

- **Frontend**: Complete 38K-line App.tsx (functional but monolithic)
- **Backend**: Working template generation system with placeholder replacement
- **Analysis**: Comprehensive architecture analysis and improvement recommendations

Use this guide to safely experiment with architectural improvements while maintaining ability to return to known-good state.