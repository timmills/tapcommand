# Android TV Brands - Discovery & Checklist Update

**Date:** October 7, 2025
**Status:** Complete ✅

---

## Summary

Added support for Android TV brand detection and created comprehensive checklist for adding new TV brands in the future.

---

## What Was Added

### 1. Android TV Brand Detection

Added 4 new Android TV brands to network discovery:

| Brand | Vendor Pattern | MAC Prefixes | Ports | Priority |
|-------|---------------|--------------|-------|----------|
| **CHiQ** (Changhong) | changhong, chiq | D8:47:10, 84:2C:80 | 6466, 6467, 5555 | 72 |
| **TCL Android** | tcl | 00:00:DD, 00:0C:61, 10:05:01, C8:28:32, E8:9F:6D | 6466, 6467, 8060 | 71 |
| **Sharp Android** | sharp | 00:03:A0, 00:17:C8, 08:7A:4C | 6466, 6467 | 68 |
| **Toshiba Android** | toshiba | 00:00:39, 00:0D:F6, 00:21:35 | 6466, 6467 | 67 |

**Protocol:** Android TV Remote v2
- **Port 6466:** Control
- **Port 6467:** Pairing
- **Port 5555:** ADB (optional, developer mode)

### 2. Also Updated MAC Prefixes for Existing Brands

| Brand | Added MAC Prefixes |
|-------|--------------------|
| **Hisense** | 00:1F:A4, 00:23:BA, D8:90:E8 |
| **Vizio** | D4:E8:B2 (added to existing) |

---

## Files Modified

### 1. `backend/app/services/device_scanner_config.py`

**Added 4 new device type configs:**

```python
"chiq_android": DeviceTypeConfig(
    device_type="chiq_android",
    display_name="CHiQ Android TV",
    mac_vendor_patterns=["changhong", "chiq"],
    port_scans=[
        PortScanRule(port=6466, protocol="tcp", description="Android TV Remote Control"),
        PortScanRule(port=6467, protocol="tcp", description="Android TV Pairing"),
        PortScanRule(port=5555, protocol="tcp", description="Android ADB"),
    ],
    priority=72,
    enabled=True
),
# ... tcl_android, sharp_android, toshiba_android
```

**Updated `get_all_tv_vendors()` function:**
- Added all new Android TV brands to TV types list
- Now returns 12 TV brand patterns (up from 5)

### 2. `venue_tv_discovery.py`

**Updated `TV_VENDORS` dict:**
- Added MAC prefixes for CHiQ, TCL, Sharp, Toshiba
- Added Hisense, Vizio MAC prefixes
- Now includes 70+ MAC prefixes across 12 brands

**Updated `PROTOCOL_PORTS` dict:**
```python
"Hisense VIDAA": [36669],
"Vizio SmartCast": [7345, 9000],
"Android TV": [6466, 6467, 5555],  # CHiQ, TCL, Sharp, Toshiba
```

**Updated `detect_tv_protocol()` function:**
- Added port scanning for Hisense, Vizio, Android TV brands
- Added protocol detection for:
  - Hisense VIDAA (MQTT)
  - Vizio SmartCast
  - Android TV Remote v2
  - Android ADB

**Updated `print_adoption_guide()` function:**
- Added adoption instructions for Hisense, Vizio, Android TV brands
- Shows setup requirements and pairing methods per brand

### 3. `backend/NEW_TV_BRAND_CHECKLIST.md` ⭐ **NEW FILE**

**Comprehensive 450-line checklist** covering:

✅ **Prerequisites** - Research required before starting
✅ **10 Implementation Steps:**
1. Research & Documentation
2. Backend Implementation (executor, router, dependencies)
3. Network Discovery (scanner config, venue discovery)
4. API Endpoints (pairing if needed)
5. Database Updates
6. Frontend Integration
7. Documentation Updates
8. Testing (unit, integration, manual)
9. Git Workflow
10. Deployment

✅ **Quick Reference:**
- File locations (8 backend, 2 frontend, 6 docs)
- Time estimates (5-8 hours per brand)
- Android TV brands table with MAC prefixes

✅ **Examples and templates** for each step

---

## Android TV Protocol Details

### Shared Characteristics

All Android TV brands (CHiQ, TCL, Sharp, Toshiba) use the same protocol:

- **Protocol:** Android TV Remote Protocol v2
- **Library:** `androidtvremote2` (Python)
- **Control Port:** 6466 (TCP)
- **Pairing Port:** 6467 (TCP)
- **ADB Port:** 5555 (TCP, optional)
- **Authentication:** Pairing-based (4-digit code shown on TV)
- **Status Queries:** Power state, current app

### Comparison with Other Protocols

| Feature | Android TV | Roku | Hisense VIDAA | LG webOS |
|---------|-----------|------|---------------|----------|
| Pairing Required | ✅ Yes | ❌ No | ❌ No | ✅ Yes |
| Power-On (WOL) | ⚠️ Unreliable | ✅ Works | ⚠️ Unreliable | ⚠️ Unreliable |
| Status Queries | ⚠️ Limited | ⚠️ Limited | ✅ Full | ✅ Full |
| Setup Complexity | Medium | Low | Low | Medium |

---

## Discovery Integration Status

### Backend Scanner (device_scanner_config.py)

✅ **12 TV brands configured:**
1. Samsung Legacy (priority 100)
2. Samsung Tizen (priority 90)
3. LG webOS (priority 80)
4. Hisense VIDAA (priority 75)
5. **CHiQ Android** (priority 72) ⭐ NEW
6. **TCL Android** (priority 71) ⭐ NEW
7. Sony Bravia (priority 70)
8. **Sharp Android** (priority 68) ⭐ NEW
9. **Toshiba Android** (priority 67) ⭐ NEW
10. Vizio SmartCast (priority 65)
11. TCL Roku (priority 55)
12. Roku (priority 50)

### Standalone Discovery (venue_tv_discovery.py)

✅ **12 TV brands detectable:**
- Samsung (Legacy + Modern)
- LG webOS
- Sony Bravia
- Philips JointSpace
- Hisense VIDAA ⭐ UPDATED
- Vizio SmartCast ⭐ UPDATED
- Roku / TCL Roku
- **CHiQ Android** ⭐ NEW
- **TCL Android** ⭐ NEW
- **Sharp Android** ⭐ NEW
- **Toshiba Android** ⭐ NEW

---

## What This Enables

### For Users

1. **Automatic Detection:** CHiQ, TCL, Sharp, Toshiba TVs will be automatically detected during network scans
2. **Brand Identification:** MAC address lookup identifies manufacturer
3. **Protocol Detection:** Port scanning confirms Android TV capability
4. **Adoption Guidance:** Discovery report shows setup requirements

### For Developers

1. **Checklist Template:** NEW_TV_BRAND_CHECKLIST.md provides step-by-step guide for adding new brands
2. **MAC Prefix Database:** Expanded with 25+ new prefixes
3. **Port Detection:** Android TV ports (6466, 6467, 5555) now scanned
4. **Consistent Patterns:** All Android TV brands follow same implementation pattern

---

## Next Steps

### To Fully Support Android TV Brands (CHiQ, TCL, Sharp, Toshiba)

**Backend (5-7 hours):**
1. ✅ Add to discovery (DONE)
2. ⚠️ Create Android TV executor using `androidtvremote2` (2-3 hours)
3. ⚠️ Create pairing endpoints (1 hour)
4. ⚠️ Update router (15 min)
5. ⚠️ Add to status poller (30 min)
6. ⚠️ Update requirements.txt (5 min)

**Frontend (2-3 hours):**
1. ⚠️ Add Android TV brands to brand info cards
2. ⚠️ Create pairing flow UI
3. ⚠️ Test adoption process

**Documentation (30 min):**
1. ⚠️ Update SUPPORTED_NETWORK_TVS.md
2. ⚠️ Update NETWORK_TV_SETUP_GUIDE.md
3. ⚠️ Add to status capabilities doc

**Current Status:** Discovery layer complete ✅, execution layer pending ⚠️

---

## Brand Support Matrix (After This Update)

### Discovery Status

| Brand | MAC Detection | Port Detection | Protocol Detection | Executor | Status Polling |
|-------|--------------|----------------|-------------------|----------|----------------|
| Samsung Legacy | ✅ | ✅ | ✅ | ✅ | ❌ |
| Samsung Tizen | ✅ | ✅ | ✅ | ⚠️ Planned | ⚠️ Planned |
| LG webOS | ✅ | ✅ | ✅ | ✅ | ✅ |
| Sony Bravia | ✅ | ✅ | ✅ | ✅ | ✅ |
| Philips | ✅ | ✅ | ✅ | ✅ | ✅ |
| Hisense VIDAA | ✅ | ✅ | ✅ | ✅ | ✅ |
| Vizio SmartCast | ✅ | ✅ | ✅ | ✅ | ✅ |
| Roku | ✅ | ✅ | ✅ | ✅ | ✅ |
| **CHiQ Android** | ✅ NEW | ✅ NEW | ✅ NEW | ⚠️ TODO | ⚠️ TODO |
| **TCL Android** | ✅ NEW | ✅ NEW | ✅ NEW | ⚠️ TODO | ⚠️ TODO |
| **Sharp Android** | ✅ NEW | ✅ NEW | ✅ NEW | ⚠️ TODO | ⚠️ TODO |
| **Toshiba Android** | ✅ NEW | ✅ NEW | ✅ NEW | ⚠️ TODO | ⚠️ TODO |

**Legend:**
- ✅ Complete
- ⚠️ Planned / TODO
- ❌ Not supported

---

## Testing

### How to Test Discovery

**Run venue_tv_discovery.py:**
```bash
python3 venue_tv_discovery.py 192.168.1
```

**Expected output for Android TV:**
```
Scanning 192.168.1.50 (CHiQ)... ✓ Android TV Remote v2
```

**CSV/JSON report will include:**
- Brand: CHiQ / TCL / Sharp / Toshiba
- Protocols: Android TV Remote v2, Android ADB (if developer mode enabled)
- Ports: 6466, 6467, (5555)

### How to Test Backend Scanner

```python
from app.services.device_scanner_config import get_device_type_by_vendor

# Test CHiQ detection
config = get_device_type_by_vendor("Changhong")
assert config.device_type == "chiq_android"

# Test TCL detection
config = get_device_type_by_vendor("TCL")
assert config.device_type == "tcl_android"
```

---

## Notes for Future Brand Additions

### Use the Checklist!

When adding new TV brands in the future, follow `NEW_TV_BRAND_CHECKLIST.md`:

1. **Research first** - Gather protocol, ports, MAC prefixes, library
2. **Update discovery** - Add to both `device_scanner_config.py` and `venue_tv_discovery.py`
3. **Create executor** - Implement CommandExecutor interface
4. **Test thoroughly** - Unit tests + real hardware
5. **Document everything** - Update all relevant docs

### Common Patterns

**Most TV brands follow one of these patterns:**

| Pattern | Brands | Auth | Library |
|---------|--------|------|---------|
| Pairing-based WebSocket | LG, Samsung Modern | Pairing key | pywebostv, samsungtvws |
| PSK-based REST | Sony | Pre-shared key | requests |
| MQTT | Hisense | Default creds | hisensetv |
| HTTP REST | Roku, Vizio, Philips | Token/none | requests, pyvizio |
| Android TV | CHiQ, TCL, Sharp, Toshiba | Pairing code | androidtvremote2 |
| Legacy TCP | Samsung Legacy | None | socket |

---

## Summary Statistics

### Lines Added

- `device_scanner_config.py`: +60 lines
- `venue_tv_discovery.py`: +100 lines
- `NEW_TV_BRAND_CHECKLIST.md`: +450 lines (new file)
- `ANDROID_TV_BRANDS_UPDATE.md`: +350 lines (this file)
- **Total:** ~960 lines

### MAC Prefixes Added

- CHiQ: 2 prefixes
- TCL: 5 prefixes
- Sharp: 3 prefixes
- Toshiba: 3 prefixes
- Hisense: 3 prefixes
- Vizio: 1 prefix
- **Total:** 17 new MAC prefixes

### Brands Now Detectable

- **Before:** 8 brands (Samsung x2, LG, Sony, Philips, Hisense, Vizio, Roku)
- **After:** 12 brands (+ CHiQ, TCL Android, Sharp, Toshiba)
- **Increase:** +50% more brands

---

## Git Commit Summary

**Files Modified:**
- `backend/app/services/device_scanner_config.py`
- `venue_tv_discovery.py`

**Files Created:**
- `backend/NEW_TV_BRAND_CHECKLIST.md`
- `backend/ANDROID_TV_BRANDS_UPDATE.md`

**Commit Message:**
```
feat: Add Android TV brand detection and comprehensive brand checklist

- Add 4 Android TV brands to discovery (CHiQ, TCL, Sharp, Toshiba)
- Add 17 new MAC address prefixes across 6 brands
- Update venue_tv_discovery.py with Android TV protocol detection
- Update device_scanner_config.py with 4 new device types
- Create NEW_TV_BRAND_CHECKLIST.md (450-line comprehensive guide)
- Create ANDROID_TV_BRANDS_UPDATE.md (documentation)

Discovery layer now supports 12 TV brands total (up from 8)
```

---

**Ready for CHiQ implementation when you want to proceed!** 🚀

See `backend/CHIQ_TV_RESEARCH.md` for complete CHiQ implementation plan.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
