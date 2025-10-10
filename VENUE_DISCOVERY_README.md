# TapCommand TV Discovery Tool - Onsite Usage Guide

## Overview

`venue_tv_discovery.py` is a standalone script for onsite venue surveys to discover and catalog network-controllable TVs. This tool identifies TVs that can be adopted into TapCommand for network control (faster, more reliable than IR).

## What It Does

1. **Scans the venue's network** using nmap for fast discovery
2. **Identifies TV brands** via MAC address lookup (Samsung, LG, Sony, Philips, etc.)
3. **Detects protocols** by port scanning (Samsung Legacy, Samsung Modern, LG WebOS, Sony IRCC, etc.)
4. **Gathers device details** (model, firmware, etc.)
5. **Generates reports** in JSON and CSV formats for import into TapCommand

## Pre-Installation (On Your Laptop)

### System Requirements
- Ubuntu/Debian Linux (or any Linux with apt)
- Python 3.8+
- sudo access (for installing nmap)

### Installation Steps

```bash
# 1. Install nmap (requires sudo)
sudo apt-get update
sudo apt-get install nmap -y

# 2. Install Python dependencies (recommended: use venv)
pip3 install requests tabulate

# OR with virtual environment (recommended):
python3 -m venv venue_venv
source venue_venv/bin/activate
pip install requests tabulate

# 3. Copy script to your laptop
# Copy venue_tv_discovery.py to your laptop/USB drive
chmod +x venue_tv_discovery.py

# 4. Test it works
./venue_tv_discovery.py --help
```

## Onsite Usage

### Quick Start

```bash
# Basic scan (192.168.1.0/24)
python3 venue_tv_discovery.py

# Scan specific subnet
python3 venue_tv_discovery.py 192.168.100

# Scan different subnet
python3 venue_tv_discovery.py 10.0.50

# Scan limited range (faster for small networks)
python3 venue_tv_discovery.py 192.168.1 --range 1-50
```

### Typical Workflow

1. **Connect to venue network**
   - Wifi or ethernet
   - Ensure you're on same network as TVs
   - Note the subnet (e.g., 192.168.1.x, 10.0.0.x)

2. **Run discovery**
   ```bash
   python3 venue_tv_discovery.py 192.168.1
   ```

3. **Wait for scan** (typically 30-60 seconds)
   - nmap will ping sweep the network
   - Script will identify TVs by MAC vendor
   - Port scanning to detect protocols
   - Samsung Modern TVs will be queried for details

4. **Review results** on screen
   - Table showing all discovered TVs
   - IP, Brand, Model, Protocol(s), Ports

5. **Collect report files**
   ```
   tv_discovery_report_20251004_143022.json
   tv_discovery_report_20251004_143022.csv
   ```

6. **Import into TapCommand**
   - Upload JSON/CSV to TapCommand admin portal
   - System will create virtual controllers
   - Initiate pairing for each TV

## Understanding the Output

### Console Output

```
======================================================================
TapCommand Network TV Discovery
======================================================================

[*] Scanning 192.168.1.1-254 with nmap...
[✓] Found 45 online hosts
[✓] Found 18 MAC addresses
[✓] Found 4 potential TV devices
[*] Detecting TV protocols (port scanning)...
    Scanning 192.168.1.50 (Samsung)... ✓ Samsung Legacy
    Scanning 192.168.1.52 (Samsung)... ✓ Samsung Modern (WebSocket)
    Scanning 192.168.1.100 (LG)... ✓ LG WebOS
    Scanning 192.168.1.120 (Sony)... ✓ Sony IRCC

======================================================================
DISCOVERED TVS (4 found)
======================================================================

╒════╤══════════════╤══════════╤═════════════╤════════════════════════════╤═════════╤════════════╕
│  # │ IP Address   │ Brand    │ Model       │ Protocol(s)                │ Ports   │ Hostname   │
╞════╪══════════════╪══════════╪═════════════╪════════════════════════════╪═════════╪════════════╡
│  1 │ 192.168.1.50 │ Samsung  │ LA40D550    │ Samsung Legacy             │ 55000   │ samsung-tv │
├────┼──────────────┼──────────┼─────────────┼────────────────────────────┼─────────┼────────────┤
│  2 │ 192.168.1.52 │ Samsung  │ QA55Q7FAM   │ Samsung Modern (WebSocket) │ 8001    │ samsung-q7 │
├────┼──────────────┼──────────┼─────────────┼────────────────────────────┼─────────┼────────────┤
│  3 │ 192.168.1.100│ LG       │ Unknown     │ LG WebOS                   │ 3000    │ lg-oled    │
├────┼──────────────┼──────────┼─────────────┼────────────────────────────┼─────────┼────────────┤
│  4 │ 192.168.1.120│ Sony     │ Unknown     │ Sony IRCC                  │ 80      │ bravia-tv  │
╘════╧══════════════╧══════════╧═════════════╧════════════════════════════╧═════════╧════════════╛

[✓] JSON report saved: tv_discovery_report_20251004_143022.json
[✓] CSV report saved: tv_discovery_report_20251004_143022.csv

======================================================================
NEXT STEPS - TV ADOPTION
======================================================================

Samsung Legacy TVs (1 found):
  • Can be adopted immediately
  • No token storage needed
  • On-screen pairing required on first use
  • IPs: 192.168.1.50

Samsung Modern TVs (1 found):
  • Requires token-based pairing
  • Full bidirectional control
  • Setup: Enable 'Power On with Mobile' in TV settings
  • IPs: 192.168.1.52

LG WebOS TVs (1 found):
  • Requires pairing key from TV screen
  • Full bidirectional control
  • IPs: 192.168.1.100

Sony Bravia TVs (1 found):
  • Requires PSK (Pre-Shared Key) configuration on TV
  • Settings → Network → IP Control → Authentication
  • IPs: 192.168.1.120

All discovered TVs can be adopted into TapCommand.
Import the JSON/CSV report to proceed with adoption.

Discovery complete!
```

### JSON Report Format

```json
{
  "scan_time": "2025-10-04T14:30:22.123456",
  "total_tvs_found": 4,
  "devices": [
    {
      "ip": "192.168.1.50",
      "mac": "E4:E0:C5:B8:5A:97",
      "vendor": "Samsung",
      "model": "LA40D550",
      "hostname": "samsung-tv",
      "protocols": ["Samsung Legacy"],
      "open_ports": [55000],
      "latency_ms": 2.3
    },
    {
      "ip": "192.168.1.52",
      "mac": "01:23:45:67:89:AB",
      "vendor": "Samsung",
      "model": "QA55Q7FAM",
      "device_name": "[TV] Samsung Q7 Series (55)",
      "firmware": "1560.5",
      "hostname": "samsung-q7",
      "protocols": ["Samsung Modern (WebSocket)"],
      "open_ports": [8001],
      "latency_ms": 1.8
    }
  ]
}
```

### CSV Report Format

| ip | mac | vendor | model | hostname | protocols | open_ports | latency_ms |
|----|-----|--------|-------|----------|-----------|------------|------------|
| 192.168.1.50 | E4:E0:C5:B8:5A:97 | Samsung | LA40D550 | samsung-tv | Samsung Legacy | 55000 | 2.3 |
| 192.168.1.52 | 01:23:45:67:89:AB | Samsung | QA55Q7FAM | samsung-q7 | Samsung Modern (WebSocket) | 8001 | 1.8 |

## Supported TV Brands & Protocols

### ✅ Fully Detected

- **Samsung**
  - Legacy (2011-2015 D/E/F series): Port 55000
  - Modern (2016+ Tizen): Port 8001/8002
  - 920+ MAC prefixes in database

- **LG**
  - WebOS (2014+): Port 3000/3001
  - 185+ MAC prefixes in database

- **Sony**
  - Bravia IRCC (2013+): Port 80
  - 138+ MAC prefixes in database

- **Philips**
  - Android TV JointSpace (2016+): Port 1925/1926
  - 22+ MAC prefixes in database

- **Roku**
  - ECP (External Control Protocol): Port 8060

## Troubleshooting

### "Missing dependencies" Error

```bash
# Install nmap
sudo apt-get install nmap

# Install Python packages
pip3 install requests tabulate

# Or create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install requests tabulate
```

### "No online hosts found"

- Check you're connected to venue network
- Verify TVs are powered on
- Try smaller range: `--range 1-50`
- Check firewall isn't blocking ping

### "No TV vendors detected"

- TVs may be off
- Network may use different subnet
- Try: `ip addr` to see your IP, then scan that subnet
- Some TVs use uncommon MAC prefixes (not in database)

### "No control ports open"

- TV network control may be disabled
- Check TV settings → Network → External Device Manager
- Some TVs require setup before ports open
- Firewall may be blocking ports

### Permission Denied

```bash
# Make script executable
chmod +x venue_tv_discovery.py

# Or run with python3
python3 venue_tv_discovery.py
```

## Advanced Usage

### Scan Multiple Subnets

```bash
# Scan multiple networks
python3 venue_tv_discovery.py 192.168.1
python3 venue_tv_discovery.py 192.168.2
python3 venue_tv_discovery.py 10.0.0

# Combine results manually or import all JSONs
```

### Fast Scan (Small Networks)

```bash
# If you know TVs are in specific range
python3 venue_tv_discovery.py 192.168.1 --range 10-50
python3 venue_tv_discovery.py 192.168.1 --range 100-150

# Scans faster, good for targeted discovery
```

### Debugging

The script shows progress:
- `[*]` - In progress
- `[✓]` - Success
- `[!]` - Warning/Error

If scan seems stuck, it's likely the nmap phase (can take 30-60s for /24 network).

## What Happens After Discovery?

1. **Upload Reports** to TapCommand admin panel
2. **System creates virtual controllers** for each TV
3. **Pairing initiated** based on protocol:
   - Samsung Legacy: Accept on TV screen
   - Samsung Modern: Accept pairing, token stored
   - LG WebOS: Enter pairing key
   - Sony: Enter PSK from TV settings
4. **Test commands** sent (volume up/down)
5. **TVs added to control page** - ready to use!

## Performance Notes

- **Scan time**: ~30-60 seconds for /24 network (254 IPs)
- **Port scanning**: ~1 second per potential TV
- **Samsung API query**: ~3 seconds per Modern TV
- **Total time**: Usually 1-2 minutes for typical venue

## Benefits of Network Control vs IR

| Feature | Network Control | IR Control |
|---------|----------------|------------|
| **Speed** | 50-100ms | 500-800ms |
| **Reliability** | 99.9% | ~90% |
| **Range** | Unlimited (same network) | 5-10m line-of-sight |
| **Status Feedback** | Yes (power, vol, input) | No |
| **Setup Time** | 5 min | 30 min |
| **Hardware Cost** | $0 | $25 per blaster |

## Dependencies

### Required
- `nmap` - Network scanning tool
- `python3` - Python 3.8+
- `requests` - HTTP library (pip package)
- `tabulate` - Table formatting (pip package)

### Optional
- Virtual environment (recommended for clean install)

## File Outputs

All files saved to current directory:

```
tv_discovery_report_20251004_143022.json  # Full details, for automation
tv_discovery_report_20251004_143022.csv   # Spreadsheet format
```

## Security Notes

- Script only reads network information (non-invasive)
- No changes made to TVs
- No passwords or credentials stored
- Safe to run on production networks

## Support

For issues or questions:
- Check this README
- Review console output for error messages
- Contact TapCommand support with report files

## Version History

- **v1.0** (2025-10-04)
  - Initial release
  - Supports Samsung, LG, Sony, Philips
  - nmap-based scanning
  - JSON/CSV output
  - Protocol detection

---

**Script Location**: `/home/coastal/tapcommand/venue_tv_discovery.py`
**Last Updated**: October 4, 2025
