#!/usr/bin/env python3
"""
SmartVenue Network TV Discovery Tool
=====================================

Standalone script for onsite venue surveys to discover network-controllable TVs.

Usage:
    python3 venue_tv_discovery.py [subnet]
    python3 venue_tv_discovery.py 192.168.1
    python3 venue_tv_discovery.py --help

Requirements:
    - nmap (for fast network scanning)
    - Python 3.8+
    - pip packages: requests, tabulate

Installation:
    sudo apt-get install nmap -y
    pip3 install requests tabulate

Output:
    - Console report with discovered TVs
    - JSON file: tv_discovery_report_YYYYMMDD_HHMMSS.json
    - CSV file: tv_discovery_report_YYYYMMDD_HHMMSS.csv
"""

import subprocess
import re
import json
import csv
import socket
import argparse
import sys
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import concurrent.futures

# Color output for terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# TV vendor MAC prefix database (top manufacturers only for standalone script)
TV_VENDORS = {
    # Samsung (920+ prefixes, showing top ones)
    "E4:E0:C5": "Samsung", "00:E0:64": "Samsung", "BC:14:85": "Samsung",
    "00:16:32": "Samsung", "00:12:47": "Samsung", "00:13:77": "Samsung",
    "00:15:B9": "Samsung", "00:16:6B": "Samsung", "00:17:C9": "Samsung",
    "00:18:AF": "Samsung", "00:1A:8A": "Samsung", "00:1B:98": "Samsung",
    "00:1D:25": "Samsung", "00:1E:7D": "Samsung", "00:1F:CD": "Samsung",
    "00:21:19": "Samsung", "00:23:39": "Samsung", "00:24:54": "Samsung",
    "00:26:37": "Samsung", "3C:5A:B4": "Samsung", "74:45:CE": "Samsung",
    "D0:C1:B1": "Samsung", "CC:07:AB": "Samsung", "B4:79:A7": "Samsung",

    # LG (185+ prefixes)
    "00:E0:91": "LG", "B8:38:61": "LG", "A0:23:9F": "LG",
    "00:1C:62": "LG", "00:1E:75": "LG", "00:1F:6B": "LG",
    "00:22:A9": "LG", "00:24:83": "LG", "10:68:3F": "LG",
    "40:B8:9A": "LG", "54:33:CB": "LG", "60:6B:BD": "LG",
    "64:BC:0C": "LG", "78:5D:C8": "LG", "9C:80:DF": "LG",

    # Sony (138+ prefixes)
    "00:04:1F": "Sony", "00:0D:F0": "Sony", "00:13:A9": "Sony",
    "00:16:FE": "Sony", "00:19:C5": "Sony", "00:1A:80": "Sony",
    "00:1B:63": "Sony", "00:1D:BA": "Sony", "00:1E:3D": "Sony",
    "30:52:CB": "Sony", "54:42:49": "Sony", "AC:9B:0A": "Sony",

    # Philips (22+ prefixes)
    "00:01:FE": "Philips", "00:04:ED": "Philips", "00:09:6E": "Philips",
    "00:0D:3A": "Philips", "00:12:56": "Philips", "00:17:A4": "Philips",

    # Hisense
    "00:1F:A4": "Hisense", "00:23:BA": "Hisense", "D8:90:E8": "Hisense",

    # TCL
    "00:00:DD": "TCL", "00:0C:61": "TCL", "10:05:01": "TCL",
    "C8:28:32": "TCL", "E8:9F:6D": "TCL",

    # CHiQ / Changhong
    "D8:47:10": "CHiQ", "84:2C:80": "CHiQ",

    # Sharp
    "00:03:A0": "Sharp", "00:17:C8": "Sharp", "08:7A:4C": "Sharp",

    # Toshiba
    "00:00:39": "Toshiba", "00:0D:F6": "Toshiba", "00:21:35": "Toshiba",

    # Vizio
    "00:1B:FB": "Vizio", "E0:B9:4D": "Vizio", "D4:E8:B2": "Vizio",

    # Roku
    "00:0D:4B": "Roku", "D8:31:CF": "Roku", "CC:6D:A0": "Roku",

    # Other brands
    "7C:61:66": "Apple TV", "A4:D1:D2": "Apple TV",
    "00:09:D0": "Panasonic", "00:0D:8E": "Panasonic",
}

# Protocol detection ports
PROTOCOL_PORTS = {
    "Samsung Legacy": [55000],
    "Samsung Modern": [8001, 8002],
    "LG WebOS": [3000, 3001],
    "Sony IRCC": [80],
    "Philips JointSpace": [1925, 1926],
    "Hisense VIDAA": [36669],
    "Roku": [8060],
    "Vizio SmartCast": [7345, 9000],
    "Android TV": [6466, 6467, 5555],  # CHiQ, TCL, Sharp, Toshiba
}

def check_dependencies() -> Tuple[bool, List[str]]:
    """Check if required dependencies are installed"""
    missing = []

    # Check nmap
    try:
        subprocess.run(['nmap', '--version'], capture_output=True, timeout=2)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        missing.append('nmap (install: sudo apt-get install nmap)')

    # Check Python packages
    try:
        import requests
    except ImportError:
        missing.append('requests (install: pip3 install requests)')

    try:
        from tabulate import tabulate
    except ImportError:
        missing.append('tabulate (install: pip3 install tabulate)')

    return len(missing) == 0, missing

def get_mac_vendor(mac: str) -> Optional[str]:
    """Lookup vendor from MAC address using built-in database"""
    if not mac or mac == "Unknown":
        return None

    # Extract OUI (first 3 octets)
    prefix = ':'.join(mac.upper().split(':')[:3])

    return TV_VENDORS.get(prefix)

def run_nmap_scan(subnet: str, start: int = 1, end: int = 254) -> List[Dict]:
    """Run nmap ping sweep to find online hosts"""
    print(f"{Colors.OKBLUE}[*] Scanning {subnet}.{start}-{end} with nmap...{Colors.ENDC}")

    try:
        cmd = [
            'nmap', '-sn',  # Ping scan only
            '--max-retries', '1',  # Fast scan
            '-T4',  # Aggressive timing
            f'{subnet}.{start}-{end}'
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        output = result.stdout

        # Parse nmap output
        online_hosts = []
        current_ip = None

        for line in output.split('\n'):
            # Look for IP addresses
            ip_match = re.search(r'Nmap scan report for (\d+\.\d+\.\d+\.\d+)', line)
            if ip_match:
                current_ip = ip_match.group(1)

            # Look for "Host is up" to confirm online
            if current_ip and 'Host is up' in line:
                # Extract latency if available
                latency_match = re.search(r'\(([0-9.]+)s latency\)', line)
                latency_ms = float(latency_match.group(1)) * 1000 if latency_match else None

                online_hosts.append({
                    'ip': current_ip,
                    'online': True,
                    'latency_ms': latency_ms
                })
                current_ip = None

        print(f"{Colors.OKGREEN}[✓] Found {len(online_hosts)} online hosts{Colors.ENDC}")
        return online_hosts

    except subprocess.TimeoutExpired:
        print(f"{Colors.FAIL}[!] nmap scan timed out{Colors.ENDC}")
        return []
    except Exception as e:
        print(f"{Colors.FAIL}[!] nmap scan failed: {e}{Colors.ENDC}")
        return []

def get_arp_cache() -> Dict[str, str]:
    """Get MAC addresses from ARP cache"""
    try:
        result = subprocess.run(
            ['ip', 'neigh', 'show'],
            capture_output=True,
            text=True,
            timeout=5
        )

        arp_map = {}
        for line in result.stdout.split('\n'):
            # Format: 192.168.1.1 dev eth0 lladdr aa:bb:cc:dd:ee:ff REACHABLE
            match = re.search(r'(\d+\.\d+\.\d+\.\d+)\s+.*?lladdr\s+([\da-f:]+)', line, re.IGNORECASE)
            if match:
                ip = match.group(1)
                mac = match.group(2).upper()
                arp_map[ip] = mac

        return arp_map

    except Exception as e:
        print(f"{Colors.WARNING}[!] Could not read ARP cache: {e}{Colors.ENDC}")
        return {}

def get_hostname(ip: str) -> Optional[str]:
    """Try to resolve hostname via reverse DNS"""
    try:
        hostname = socket.gethostbyaddr(ip)[0]
        return hostname
    except:
        return None

def check_port(ip: str, port: int, timeout: float = 0.5) -> bool:
    """Check if a TCP port is open"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False

def detect_tv_protocol(ip: str, vendor: str) -> Dict:
    """Detect which protocol(s) a TV supports based on open ports"""
    detected_protocols = []
    open_ports = []

    # Determine which ports to scan based on vendor
    ports_to_check = []

    if vendor == "Samsung":
        ports_to_check.extend([55000, 8001, 8002])
    elif vendor == "LG":
        ports_to_check.extend([3000, 3001])
    elif vendor == "Sony":
        ports_to_check.extend([80, 10000])
    elif vendor == "Philips":
        ports_to_check.extend([1925, 1926])
    elif vendor == "Hisense":
        ports_to_check.extend([36669, 3000])
    elif vendor == "Vizio":
        ports_to_check.extend([7345, 9000])
    elif vendor == "Roku":
        ports_to_check.extend([8060])
    elif vendor in ["TCL", "CHiQ", "Sharp", "Toshiba"]:
        # Android TV ports
        ports_to_check.extend([6466, 6467, 5555, 8060])

    # Check each port
    for port in ports_to_check:
        if check_port(ip, port, timeout=1.0):
            open_ports.append(port)

            # Map port to protocol
            if port == 55000:
                detected_protocols.append("Samsung Legacy")
            elif port in [8001, 8002]:
                detected_protocols.append("Samsung Modern (WebSocket)")
            elif port in [3000, 3001]:
                detected_protocols.append("LG WebOS")
            elif port == 80 and vendor == "Sony":
                detected_protocols.append("Sony IRCC")
            elif port in [1925, 1926]:
                detected_protocols.append("Philips JointSpace")
            elif port == 36669:
                detected_protocols.append("Hisense VIDAA (MQTT)")
            elif port in [7345, 9000]:
                detected_protocols.append("Vizio SmartCast")
            elif port == 8060:
                detected_protocols.append("Roku ECP")
            elif port in [6466, 6467]:
                detected_protocols.append("Android TV Remote v2")
            elif port == 5555 and vendor in ["TCL", "CHiQ", "Sharp", "Toshiba"]:
                detected_protocols.append("Android ADB")

    return {
        'open_ports': open_ports,
        'protocols': detected_protocols
    }

def test_samsung_modern_api(ip: str) -> Optional[Dict]:
    """Test Samsung modern TV REST API (port 8001)"""
    try:
        import requests
        url = f"http://{ip}:8001/api/v2/"
        response = requests.get(url, timeout=3)

        if response.status_code == 200:
            data = response.json()
            device = data.get('device', {})
            return {
                'model': device.get('modelName', 'Unknown'),
                'name': device.get('name', 'Unknown'),
                'firmware': device.get('version', 'Unknown'),
                'type': device.get('type', 'Unknown'),
                'wifi_mac': device.get('wifiMac', 'Unknown'),
            }
    except:
        pass

    return None

def discover_tvs_on_network(subnet: str = "192.168.1") -> List[Dict]:
    """Main discovery function - find all TVs on network"""

    print(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}SmartVenue Network TV Discovery{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}\n")

    # Step 1: nmap ping sweep
    online_hosts = run_nmap_scan(subnet)

    if not online_hosts:
        print(f"{Colors.FAIL}[!] No online hosts found. Check network connection.{Colors.ENDC}")
        return []

    # Step 2: Get MAC addresses from ARP
    print(f"{Colors.OKBLUE}[*] Reading ARP cache for MAC addresses...{Colors.ENDC}")
    arp_cache = get_arp_cache()
    print(f"{Colors.OKGREEN}[✓] Found {len(arp_cache)} MAC addresses{Colors.ENDC}")

    # Step 3: Identify TV vendors
    print(f"{Colors.OKBLUE}[*] Identifying TV vendors...{Colors.ENDC}")

    tv_devices = []
    potential_tvs = []

    for host in online_hosts:
        ip = host['ip']
        mac = arp_cache.get(ip, "Unknown")
        vendor = get_mac_vendor(mac) if mac != "Unknown" else None
        hostname = get_hostname(ip)

        # Only process if vendor is a known TV manufacturer
        if vendor in ["Samsung", "LG", "Sony", "Philips", "Roku", "Apple TV", "Vizio", "Panasonic",
                      "Hisense", "TCL", "CHiQ", "Sharp", "Toshiba"]:
            potential_tvs.append({
                'ip': ip,
                'mac': mac,
                'vendor': vendor,
                'hostname': hostname,
                'latency_ms': host.get('latency_ms')
            })

    print(f"{Colors.OKGREEN}[✓] Found {len(potential_tvs)} potential TV devices{Colors.ENDC}")

    if not potential_tvs:
        print(f"{Colors.WARNING}[!] No TV vendors detected. Showing all hosts...{Colors.ENDC}")
        # Show all hosts for debugging
        for host in online_hosts[:10]:  # Limit to 10
            ip = host['ip']
            mac = arp_cache.get(ip, "Unknown")
            vendor = get_mac_vendor(mac) if mac != "Unknown" else "Unknown"
            print(f"    {ip} - {mac} - {vendor}")
        return []

    # Step 4: Port scan to detect protocols
    print(f"{Colors.OKBLUE}[*] Detecting TV protocols (port scanning)...{Colors.ENDC}")

    for tv in potential_tvs:
        print(f"    Scanning {tv['ip']} ({tv['vendor']})...", end=' ')

        protocol_info = detect_tv_protocol(tv['ip'], tv['vendor'])
        tv['open_ports'] = protocol_info['open_ports']
        tv['protocols'] = protocol_info['protocols']

        # Try to get detailed info for Samsung Modern TVs
        if 8001 in tv['open_ports'] and tv['vendor'] == "Samsung":
            samsung_info = test_samsung_modern_api(tv['ip'])
            if samsung_info:
                tv['model'] = samsung_info['model']
                tv['device_name'] = samsung_info['name']
                tv['firmware'] = samsung_info['firmware']

        if tv['protocols']:
            print(f"{Colors.OKGREEN}✓ {', '.join(tv['protocols'])}{Colors.ENDC}")
            tv_devices.append(tv)
        else:
            print(f"{Colors.WARNING}No control ports open{Colors.ENDC}")

    return tv_devices

def print_discovery_report(tvs: List[Dict]):
    """Print formatted report to console"""
    try:
        from tabulate import tabulate

        if not tvs:
            print(f"\n{Colors.WARNING}No controllable TVs found.{Colors.ENDC}\n")
            return

        print(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}DISCOVERED TVS ({len(tvs)} found){Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}\n")

        # Prepare table data
        table_data = []
        for i, tv in enumerate(tvs, 1):
            table_data.append([
                i,
                tv['ip'],
                tv['vendor'],
                tv.get('model', 'Unknown'),
                ', '.join(tv.get('protocols', [])),
                ', '.join(map(str, tv.get('open_ports', []))),
                tv.get('hostname', '-')[:30] if tv.get('hostname') else '-'
            ])

        headers = ['#', 'IP Address', 'Brand', 'Model', 'Protocol(s)', 'Ports', 'Hostname']

        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        print()

    except ImportError:
        # Fallback to simple print if tabulate not available
        print(f"\n{Colors.OKGREEN}Found {len(tvs)} controllable TVs:{Colors.ENDC}\n")
        for i, tv in enumerate(tvs, 1):
            print(f"{i}. {tv['ip']} - {tv['vendor']} - {', '.join(tv.get('protocols', []))}")
        print()

def save_report_json(tvs: List[Dict], filename: str):
    """Save discovery report as JSON"""
    report = {
        'scan_time': datetime.now().isoformat(),
        'total_tvs_found': len(tvs),
        'devices': tvs
    }

    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"{Colors.OKGREEN}[✓] JSON report saved: {filename}{Colors.ENDC}")

def save_report_csv(tvs: List[Dict], filename: str):
    """Save discovery report as CSV"""
    if not tvs:
        return

    with open(filename, 'w', newline='') as f:
        fieldnames = ['ip', 'mac', 'vendor', 'model', 'hostname', 'protocols', 'open_ports', 'latency_ms']
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        for tv in tvs:
            writer.writerow({
                'ip': tv['ip'],
                'mac': tv.get('mac', ''),
                'vendor': tv.get('vendor', ''),
                'model': tv.get('model', 'Unknown'),
                'hostname': tv.get('hostname', ''),
                'protocols': ', '.join(tv.get('protocols', [])),
                'open_ports': ', '.join(map(str, tv.get('open_ports', []))),
                'latency_ms': tv.get('latency_ms', ''),
            })

    print(f"{Colors.OKGREEN}[✓] CSV report saved: {filename}{Colors.ENDC}")

def print_adoption_guide(tvs: List[Dict]):
    """Print next steps for adopting discovered TVs"""
    if not tvs:
        return

    print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}NEXT STEPS - TV ADOPTION{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}\n")

    samsung_legacy = [tv for tv in tvs if "Samsung Legacy" in tv.get('protocols', [])]
    samsung_modern = [tv for tv in tvs if "Samsung Modern" in tv.get('protocols', [])]
    lg_tvs = [tv for tv in tvs if "LG WebOS" in tv.get('protocols', [])]
    sony_tvs = [tv for tv in tvs if "Sony" in tv.get('protocols', [])]
    hisense_tvs = [tv for tv in tvs if "Hisense" in tv.get('protocols', [])]
    vizio_tvs = [tv for tv in tvs if "Vizio" in tv.get('protocols', [])]
    android_tvs = [tv for tv in tvs if "Android TV" in tv.get('protocols', [])]
    roku_tvs = [tv for tv in tvs if "Roku ECP" in tv.get('protocols', []) and tv.get('vendor') != 'Samsung']

    if samsung_legacy:
        print(f"{Colors.OKGREEN}Samsung Legacy TVs ({len(samsung_legacy)} found):{Colors.ENDC}")
        print(f"  • Can be adopted immediately")
        print(f"  • No token storage needed")
        print(f"  • On-screen pairing required on first use")
        print(f"  • IPs: {', '.join([tv['ip'] for tv in samsung_legacy])}")
        print()

    if samsung_modern:
        print(f"{Colors.OKGREEN}Samsung Modern TVs ({len(samsung_modern)} found):{Colors.ENDC}")
        print(f"  • Requires token-based pairing")
        print(f"  • Full bidirectional control")
        print(f"  • Setup: Enable 'Power On with Mobile' in TV settings")
        print(f"  • IPs: {', '.join([tv['ip'] for tv in samsung_modern])}")
        print()

    if lg_tvs:
        print(f"{Colors.OKGREEN}LG WebOS TVs ({len(lg_tvs)} found):{Colors.ENDC}")
        print(f"  • Requires pairing key from TV screen")
        print(f"  • Full bidirectional control")
        print(f"  • IPs: {', '.join([tv['ip'] for tv in lg_tvs])}")
        print()

    if sony_tvs:
        print(f"{Colors.OKGREEN}Sony Bravia TVs ({len(sony_tvs)} found):{Colors.ENDC}")
        print(f"  • Requires PSK (Pre-Shared Key) configuration on TV")
        print(f"  • Settings → Network → IP Control → Authentication")
        print(f"  • IPs: {', '.join([tv['ip'] for tv in sony_tvs])}")
        print()

    if hisense_tvs:
        print(f"{Colors.OKGREEN}Hisense VIDAA TVs ({len(hisense_tvs)} found):{Colors.ENDC}")
        print(f"  • Uses MQTT protocol (port 36669)")
        print(f"  • Optional SSL (auto-detected)")
        print(f"  • Default credentials (no pairing needed)")
        print(f"  • IPs: {', '.join([tv['ip'] for tv in hisense_tvs])}")
        print()

    if vizio_tvs:
        print(f"{Colors.OKGREEN}Vizio SmartCast TVs ({len(vizio_tvs)} found):{Colors.ENDC}")
        print(f"  • Requires pairing token")
        print(f"  • Enable 'SmartCast' in TV settings")
        print(f"  • IPs: {', '.join([tv['ip'] for tv in vizio_tvs])}")
        print()

    if android_tvs:
        print(f"{Colors.OKGREEN}Android TVs ({len(android_tvs)} found - CHiQ/TCL/Sharp/Toshiba):{Colors.ENDC}")
        print(f"  • Uses Android TV Remote Protocol v2")
        print(f"  • Pairing required (4-digit code shown on TV)")
        print(f"  • No developer mode needed")
        print(f"  • IPs: {', '.join([tv['ip'] for tv in android_tvs])}")
        print()

    if roku_tvs:
        print(f"{Colors.OKGREEN}Roku TVs/Devices ({len(roku_tvs)} found):{Colors.ENDC}")
        print(f"  • External Control Protocol (ECP)")
        print(f"  • No pairing required")
        print(f"  • Can be adopted immediately")
        print(f"  • IPs: {', '.join([tv['ip'] for tv in roku_tvs])}")
        print()

    print(f"{Colors.OKBLUE}All discovered TVs can be adopted into SmartVenue.{Colors.ENDC}")
    print(f"{Colors.OKBLUE}Import the JSON/CSV report to proceed with adoption.{Colors.ENDC}\n")

def main():
    parser = argparse.ArgumentParser(
        description='SmartVenue Network TV Discovery Tool - Find adoptable TVs on local network',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 venue_tv_discovery.py                 # Scan 192.168.1.0/24
  python3 venue_tv_discovery.py 192.168.100     # Scan 192.168.100.0/24
  python3 venue_tv_discovery.py 10.0.0          # Scan 10.0.0.0/24

Output files:
  - tv_discovery_report_YYYYMMDD_HHMMSS.json
  - tv_discovery_report_YYYYMMDD_HHMMSS.csv
        """
    )

    parser.add_argument(
        'subnet',
        nargs='?',
        default='192.168.1',
        help='Network subnet to scan (first 3 octets, e.g., "192.168.1")'
    )

    parser.add_argument(
        '--range',
        default='1-254',
        help='IP range to scan (default: 1-254)'
    )

    args = parser.parse_args()

    # Check dependencies
    deps_ok, missing = check_dependencies()
    if not deps_ok:
        print(f"{Colors.FAIL}Missing dependencies:{Colors.ENDC}")
        for dep in missing:
            print(f"  - {dep}")
        print(f"\n{Colors.WARNING}Please install missing dependencies and try again.{Colors.ENDC}")
        sys.exit(1)

    # Parse range
    if '-' in args.range:
        start, end = map(int, args.range.split('-'))
    else:
        start, end = 1, 254

    # Run discovery
    tvs = discover_tvs_on_network(args.subnet)

    # Print report
    print_discovery_report(tvs)

    # Save reports
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_filename = f'tv_discovery_report_{timestamp}.json'
    csv_filename = f'tv_discovery_report_{timestamp}.csv'

    save_report_json(tvs, json_filename)
    save_report_csv(tvs, csv_filename)

    # Print adoption guide
    print_adoption_guide(tvs)

    print(f"{Colors.OKGREEN}Discovery complete!{Colors.ENDC}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}[!] Scan interrupted by user{Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.FAIL}[!] Error: {e}{Colors.ENDC}")
        sys.exit(1)
