# Sonos Installer Update Summary

## Status: ✅ Already Complete

The installers do **NOT** need any updates. They already handle the Sonos integration dependencies automatically.

## How It Works

Both installation scripts (`install.sh` and `install-fancy.sh`) install Python dependencies from `requirements.txt`:

### install.sh
```bash
# Line 222
pip install -r requirements.txt
```

### install-fancy.sh
```bash
# Lines 283-284
pip install -r requirements.txt
```

## What Gets Installed

When `pip install -r requirements.txt` runs, it automatically installs:

### Primary Dependency
- `soco==0.30.12` - Sonos control library

### Secondary Dependencies (Auto-installed by pip)
- `lxml` - XML parsing library (required by soco)
- `appdirs` - Application directories helper (required by soco)
- `requests>=2.31.0` - HTTP library (already in requirements, used by soco)
- `xmltodict==1.0.2` - XML to dict converter (already in requirements, used by soco)
- `ifaddr==0.2.0` - Network interface enumeration (already in requirements, used by soco)

## Verification

To verify Sonos dependencies are correctly specified:

```bash
# Check requirements.txt includes soco
grep soco backend/requirements.txt

# Output:
# soco==0.30.12
```

## Installation Flow

When a user runs either installer:

1. **Clone repository** (includes updated `requirements.txt`)
2. **Create Python virtual environment**
3. **Run `pip install -r requirements.txt`** ← Installs soco + dependencies
4. **Start backend service** ← Sonos integration ready to use

## No Manual Steps Required

The installers are **already configured correctly**. No changes needed.

When the next installation runs (either fresh install or update), soco will be automatically installed along with all other dependencies.

## Testing New Installation

To test that Sonos support is properly installed:

```bash
# After running installer, activate venv and check
cd tapcommand
source venv/bin/activate
python -c "import soco; print(f'SoCo version: {soco.__version__}')"

# Expected output:
# SoCo version: 0.30.12
```

## Update Scripts

If you need to update an existing installation manually (without running the full installer):

```bash
cd tapcommand
source venv/bin/activate
pip install -r backend/requirements.txt
sudo systemctl restart tapcommand-backend.service
```

This will install soco and restart the backend with Sonos support enabled.

## Summary

✅ **requirements.txt** - Updated with `soco==0.30.12`
✅ **install.sh** - Already installs from requirements.txt
✅ **install-fancy.sh** - Already installs from requirements.txt
✅ **All dependencies** - Auto-installed by pip

**No installer changes needed!**
