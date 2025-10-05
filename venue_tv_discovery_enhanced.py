#!/usr/bin/env python3
"""
SmartVenue Network TV Discovery Tool - Enhanced Version
=======================================================

Features:
- Interactive subnet selection
- Comprehensive MAC database (1,438 TV manufacturer prefixes)
- Port scanning for protocol detection
- JSON + CSV reports

Usage:
    python3 venue_tv_discovery_enhanced.py
    python3 venue_tv_discovery_enhanced.py --subnet 192.168.1
    python3 venue_tv_discovery_enhanced.py --range 1-100
"""

import subprocess
import re
import json
import csv
import socket
import argparse
import sys
import asyncio
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path

# Try to import optional dependencies
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

# Color output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# Load MAC prefixes from database if available, otherwise use built-in
def load_mac_prefixes_from_db():
    """Try to load MAC prefixes from SmartVenue database"""
    db_path = os.path.join(os.path.dirname(__file__), 'backend', 'smartvenue.db')

    if not os.path.exists(db_path):
        return None

    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        tv_brands = {
            # Major international brands
            'Samsung': ['Samsung', 'SAMSUNG'],
            'LG': ['LG Electronics', 'LG ELECTRONICS', 'LG Innotek'],
            'Sony': ['Sony Corporation', 'SONY'],
            'Philips': ['Philips', 'PHILIPS'],
            'Panasonic': ['Panasonic', 'PANASONIC'],
            'TCL': ['TCL'],
            'Hisense': ['Hisense', 'HISENSE'],
            'Sharp': ['Sharp', 'SHARP'],
            'Vizio': ['Vizio'],
            'Roku': ['Roku'],

            # Australian market brands
            'Skyworth': ['Skyworth'],
            'Haier': ['Haier'],
            'Toshiba': ['Toshiba', 'TOSHIBA'],
            'Changhong': ['Changhong', 'CHANGHONG'],
            'Hitachi': ['Hitachi', 'HITACHI'],
            'Fujitsu': ['Fujitsu', 'FUJITSU'],
            'Mitsubishi': ['Mitsubishi', 'MITSUBISHI'],
            'Sanyo': ['Sanyo', 'SANYO'],
            'Konka': ['Konka'],
            'Pioneer': ['Pioneer', 'PIONEER'],
            'Kogan': ['Kogan', 'KOGANEI'],
            'Teac': ['Teac', 'TEAC'],
            'JVC': ['JVC'],
            'Akai': ['Akai', 'AKAI'],
            'Grundig': ['Grundig', 'GRUNDIG'],
            'Westinghouse': ['Westinghouse'],
            'Polaroid': ['Polaroid'],
        }

        result = {}
        total_prefixes = 0

        for brand, patterns in tv_brands.items():
            prefixes = []
            for pattern in patterns:
                cursor.execute("SELECT mac_prefix FROM mac_vendors WHERE vendor_name LIKE ?", (f'%{pattern}%',))
                rows = cursor.fetchall()
                prefixes.extend([row[0] for row in rows])

            prefixes = list(set(prefixes))
            for prefix in prefixes:
                result[prefix] = brand
            total_prefixes += len(prefixes)

        conn.close()
        print(f"{Colors.OKGREEN}[✓] Loaded {total_prefixes} TV MAC prefixes from database{Colors.ENDC}")
        return result

    except Exception as e:
        print(f"{Colors.WARNING}[!] Could not load from database: {e}{Colors.ENDC}")
        return None

# Built-in MAC prefix database (fallback)
BUILTIN_TV_VENDORS = {
    # Samsung (top 50 of 920+)
    "E4:E0:C5": "Samsung", "00:E0:64": "Samsung", "BC:14:85": "Samsung",
    "00:16:32": "Samsung", "00:12:47": "Samsung", "00:13:77": "Samsung",
    "00:15:B9": "Samsung", "00:16:6B": "Samsung", "00:17:C9": "Samsung",
    "00:18:AF": "Samsung", "00:1A:8A": "Samsung", "00:1B:98": "Samsung",
    "00:1D:25": "Samsung", "00:1E:7D": "Samsung", "00:1F:CD": "Samsung",
    "00:21:19": "Samsung", "00:23:39": "Samsung", "00:24:54": "Samsung",
    "00:26:37": "Samsung", "3C:5A:B4": "Samsung", "74:45:CE": "Samsung",
    "D0:C1:B1": "Samsung", "CC:07:AB": "Samsung", "B4:79:A7": "Samsung",
    "7C:64:56": "Samsung", "CC:6E:A4": "Samsung",

    # LG (top 30 of 169+)
    "00:E0:91": "LG", "B8:38:61": "LG", "A0:23:9F": "LG",
    "00:1C:62": "LG", "00:1E:75": "LG", "00:1F:6B": "LG",
    "00:22:A9": "LG", "00:24:83": "LG", "10:68:3F": "LG",
    "40:B8:9A": "LG", "54:33:CB": "LG", "60:6B:BD": "LG",

    # Sony (top 20 of 138+)
    "00:04:1F": "Sony", "00:0D:F0": "Sony", "00:13:A9": "Sony",
    "00:16:FE": "Sony", "00:19:C5": "Sony", "00:1A:80": "Sony",
    "30:52:CB": "Sony", "54:42:49": "Sony", "AC:9B:0A": "Sony",

    # Others
    "00:01:FE": "Philips", "00:04:ED": "Philips",
    "00:0D:4B": "Roku", "D8:31:CF": "Roku", "CC:6D:A0": "Roku",
    "00:1B:FB": "Vizio", "E0:B9:4D": "Vizio",
    "D4:AB:82": "TCL", "F4:06:16": "TCL",
    "00:1E:8C": "Hisense", "28:76:10": "Hisense",
}

# Try to load from database, fallback to built-in
TV_VENDORS = load_mac_prefixes_from_db() or BUILTIN_TV_VENDORS

# Protocol ports
PROTOCOL_PORTS = {
    "Samsung": [55000, 8001, 8002],
    "LG": [3000, 3001],
    "Sony": [80, 10000],
    "Philips": [1925, 1926],
    "Roku": [8060],
}

def check_dependencies() -> Tuple[bool, List[str], bool]:
    """Check dependencies"""
    missing = []
    has_nmap = False

    try:
        subprocess.run(['nmap', '--version'], capture_output=True, timeout=2)
        has_nmap = True
    except:
        pass

    if not HAS_REQUESTS:
        missing.append('requests (pip3 install requests)')

    if not HAS_TABULATE:
        missing.append('tabulate (pip3 install tabulate)')

    return len(missing) == 0, missing, has_nmap

def get_local_ip_subnet() -> Optional[str]:
    """Detect local IP subnet automatically"""
    try:
        # Get local IP
        result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True)

        # Find first non-loopback IPv4
        for line in result.stdout.split('\n'):
            match = re.search(r'inet (\d+\.\d+\.\d+)\.\d+/\d+', line)
            if match and not match.group(1).startswith('127'):
                return match.group(1)
    except:
        pass

    return None

def prompt_for_subnet() -> str:
    """Interactive subnet selection"""
    auto_subnet = get_local_ip_subnet()

    print(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}Network Selection{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}\n")

    if auto_subnet:
        print(f"{Colors.OKGREEN}Auto-detected subnet: {auto_subnet}.0/24{Colors.ENDC}\n")

        response = input(f"Scan {auto_subnet}.0/24? [Y/n]: ").strip().lower()

        if response in ['', 'y', 'yes']:
            return auto_subnet

    # Manual entry
    print(f"\n{Colors.OKCYAN}Enter subnet to scan (first 3 octets):{Colors.ENDC}")
    print(f"  Examples: 192.168.1, 10.0.0, 172.16.50")

    while True:
        subnet = input(f"\nSubnet: ").strip()

        # Validate subnet format
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}$', subnet):
            parts = subnet.split('.')
            if all(0 <= int(p) <= 255 for p in parts):
                return subnet

        print(f"{Colors.FAIL}Invalid format. Use format: 192.168.1{Colors.ENDC}")

def get_mac_vendor(mac: str) -> Optional[str]:
    """Lookup vendor from MAC"""
    if not mac or mac == "Unknown":
        return None

    prefix = ':'.join(mac.upper().split(':')[:3])
    return TV_VENDORS.get(prefix)

async def ping_host_async(ip: str, timeout: float = 0.5) -> Dict:
    """Async ping"""
    try:
        process = await asyncio.create_subprocess_exec(
            'ping', '-c', '1', '-W', '1', ip,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout + 0.5
            )
        except asyncio.TimeoutError:
            process.kill()
            return {'ip': ip, 'online': False, 'latency_ms': None}

        if process.returncode == 0:
            output = stdout.decode()
            time_match = re.search(r'time=(\d+\.?\d*)', output)
            latency = float(time_match.group(1)) if time_match else None
            return {'ip': ip, 'online': True, 'latency_ms': latency}
        else:
            return {'ip': ip, 'online': False, 'latency_ms': None}
    except:
        return {'ip': ip, 'online': False, 'latency_ms': None}

async def ping_sweep_async(subnet: str, start: int, end: int) -> List[Dict]:
    """Async ping sweep"""
    print(f"{Colors.OKBLUE}[*] Scanning {subnet}.{start}-{end} with async ping...{Colors.ENDC}")

    batch_size = 50
    all_results = []

    for batch_start in range(start, end + 1, batch_size):
        batch_end = min(batch_start + batch_size, end + 1)
        ips = [f"{subnet}.{i}" for i in range(batch_start, batch_end)]

        tasks = [ping_host_async(ip) for ip in ips]
        results = await asyncio.gather(*tasks)

        online = [r for r in results if r['online']]
        all_results.extend(online)

        print(f"    Scanned {batch_end - start}/{end - start + 1} IPs... ({len(all_results)} online)", end='\r')

    print()
    return all_results

def run_nmap_scan(subnet: str, start: int, end: int) -> List[Dict]:
    """nmap scan"""
    print(f"{Colors.OKBLUE}[*] Scanning {subnet}.{start}-{end} with nmap...{Colors.ENDC}")

    try:
        result = subprocess.run(
            ['nmap', '-sn', '--max-retries', '1', '-T4', f'{subnet}.{start}-{end}'],
            capture_output=True,
            text=True,
            timeout=60
        )

        online_hosts = []
        current_ip = None

        for line in result.stdout.split('\n'):
            ip_match = re.search(r'Nmap scan report for (\d+\.\d+\.\d+\.\d+)', line)
            if ip_match:
                current_ip = ip_match.group(1)

            if current_ip and 'Host is up' in line:
                latency_match = re.search(r'\(([0-9.]+)s latency\)', line)
                latency_ms = float(latency_match.group(1)) * 1000 if latency_match else None
                online_hosts.append({'ip': current_ip, 'online': True, 'latency_ms': latency_ms})
                current_ip = None

        print(f"{Colors.OKGREEN}[✓] Found {len(online_hosts)} online hosts{Colors.ENDC}")
        return online_hosts
    except:
        return []

def get_arp_cache() -> Dict[str, str]:
    """Get ARP cache"""
    try:
        result = subprocess.run(['ip', 'neigh', 'show'], capture_output=True, text=True, timeout=5)
        arp_map = {}
        for line in result.stdout.split('\n'):
            match = re.search(r'(\d+\.\d+\.\d+\.\d+)\s+.*?lladdr\s+([\da-f:]+)', line, re.IGNORECASE)
            if match:
                arp_map[match.group(1)] = match.group(2).upper()
        return arp_map
    except:
        return {}

def check_port(ip: str, port: int, timeout: float = 0.5) -> bool:
    """Check port"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False

def detect_tv_protocol(ip: str, vendor: str) -> Dict:
    """Detect protocol"""
    detected_protocols = []
    open_ports = []

    ports_to_check = PROTOCOL_PORTS.get(vendor, [])

    for port in ports_to_check:
        if check_port(ip, port, timeout=1.0):
            open_ports.append(port)

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
            elif port == 8060:
                detected_protocols.append("Roku ECP")

    return {'open_ports': open_ports, 'protocols': detected_protocols}

def test_samsung_modern_api(ip: str) -> Optional[Dict]:
    """Test Samsung API"""
    if not HAS_REQUESTS:
        return None
    try:
        response = requests.get(f"http://{ip}:8001/api/v2/", timeout=3)
        if response.status_code == 200:
            data = response.json()
            device = data.get('device', {})
            return {
                'model': device.get('modelName', 'Unknown'),
                'name': device.get('name', 'Unknown'),
                'firmware': device.get('version', 'Unknown'),
            }
    except:
        pass
    return None

async def discover_tvs(subnet: str, start: int, end: int, use_nmap: bool) -> List[Dict]:
    """Main discovery"""
    print(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}SmartVenue Network TV Discovery{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}\n")

    print(f"{Colors.OKCYAN}Scanning for 27 TV brands:{Colors.ENDC}")
    print(f"{Colors.OKCYAN}  International: Samsung, LG, Sony, Philips, Panasonic, TCL, Hisense,{Colors.ENDC}")
    print(f"{Colors.OKCYAN}                 Sharp, Vizio, Roku{Colors.ENDC}")
    print(f"{Colors.OKCYAN}  Australian: Skyworth, Haier, Toshiba, Changhong, Hitachi, Fujitsu,{Colors.ENDC}")
    print(f"{Colors.OKCYAN}              Mitsubishi, Sanyo, Konka, Pioneer, Kogan, Teac, JVC,{Colors.ENDC}")
    print(f"{Colors.OKCYAN}              Akai, Grundig, Westinghouse, Polaroid{Colors.ENDC}\n")
    print(f"{Colors.OKCYAN}MAC Database: {len(TV_VENDORS)} TV manufacturer prefixes{Colors.ENDC}\n")

    # Scan
    if use_nmap:
        online_hosts = run_nmap_scan(subnet, start, end)
    else:
        online_hosts = await ping_sweep_async(subnet, start, end)

    if not online_hosts:
        return []

    # ARP
    print(f"{Colors.OKBLUE}[*] Reading ARP cache...{Colors.ENDC}")
    arp_cache = get_arp_cache()
    print(f"{Colors.OKGREEN}[✓] Found {len(arp_cache)} MAC addresses{Colors.ENDC}")

    # Identify
    print(f"{Colors.OKBLUE}[*] Identifying TV vendors...{Colors.ENDC}")
    potential_tvs = []

    for host in online_hosts:
        ip = host['ip']
        mac = arp_cache.get(ip, "Unknown")
        vendor = get_mac_vendor(mac)

        if vendor:
            potential_tvs.append({
                'ip': ip,
                'mac': mac,
                'vendor': vendor,
                'latency_ms': host.get('latency_ms')
            })

    print(f"{Colors.OKGREEN}[✓] Found {len(potential_tvs)} potential TV devices{Colors.ENDC}")

    if not potential_tvs:
        return []

    # Port scan
    print(f"{Colors.OKBLUE}[*] Detecting TV protocols (port scanning)...{Colors.ENDC}")
    tv_devices = []

    for tv in potential_tvs:
        print(f"    Scanning {tv['ip']} ({tv['vendor']})...", end=' ')

        protocol_info = detect_tv_protocol(tv['ip'], tv['vendor'])
        tv['open_ports'] = protocol_info['open_ports']
        tv['protocols'] = protocol_info['protocols']

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

def print_report(tvs: List[Dict]):
    """Print report"""
    if not tvs:
        print(f"\n{Colors.WARNING}No controllable TVs found.{Colors.ENDC}\n")
        return

    if HAS_TABULATE:
        print(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}DISCOVERED TVS ({len(tvs)} found){Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}\n")

        table_data = []
        for i, tv in enumerate(tvs, 1):
            table_data.append([
                i,
                tv['ip'],
                tv['vendor'],
                tv.get('model', 'Unknown'),
                ', '.join(tv.get('protocols', [])),
                ', '.join(map(str, tv.get('open_ports', []))),
            ])

        headers = ['#', 'IP', 'Brand', 'Model', 'Protocol(s)', 'Ports']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        print()
    else:
        print(f"\n{Colors.OKGREEN}Found {len(tvs)} TVs{Colors.ENDC}\n")
        for i, tv in enumerate(tvs, 1):
            print(f"{i}. {tv['ip']} - {tv['vendor']} {tv.get('model', 'Unknown')}")

def save_reports(tvs: List[Dict]):
    """Save JSON/CSV"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # JSON
    json_file = f'tv_discovery_report_{timestamp}.json'
    report = {
        'scan_time': datetime.now().isoformat(),
        'total_tvs_found': len(tvs),
        'brands_found': list(set([tv['vendor'] for tv in tvs])),
        'devices': tvs
    }
    with open(json_file, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"{Colors.OKGREEN}[✓] JSON report: {json_file}{Colors.ENDC}")

    # CSV
    if tvs:
        csv_file = f'tv_discovery_report_{timestamp}.csv'
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['ip', 'mac', 'vendor', 'model', 'protocols', 'open_ports', 'latency_ms'])
            writer.writeheader()
            for tv in tvs:
                writer.writerow({
                    'ip': tv['ip'],
                    'mac': tv.get('mac', ''),
                    'vendor': tv.get('vendor', ''),
                    'model': tv.get('model', 'Unknown'),
                    'protocols': ', '.join(tv.get('protocols', [])),
                    'open_ports': ', '.join(map(str, tv.get('open_ports', []))),
                    'latency_ms': tv.get('latency_ms', ''),
                })
        print(f"{Colors.OKGREEN}[✓] CSV report: {csv_file}{Colors.ENDC}")

def main():
    parser = argparse.ArgumentParser(description='SmartVenue TV Discovery - Enhanced')
    parser.add_argument('--subnet', help='Subnet to scan (e.g., 192.168.1)')
    parser.add_argument('--range', default='1-254', help='IP range (default: 1-254)')
    parser.add_argument('--no-interactive', action='store_true', help='Skip interactive prompts')

    args = parser.parse_args()

    # Check dependencies
    deps_ok, missing, has_nmap = check_dependencies()
    if not deps_ok:
        print(f"{Colors.FAIL}Missing: {', '.join(missing)}{Colors.ENDC}")
        sys.exit(1)

    # Get subnet
    if args.subnet:
        subnet = args.subnet
    elif args.no_interactive:
        subnet = get_local_ip_subnet() or '192.168.1'
    else:
        subnet = prompt_for_subnet()

    # Parse range
    start, end = map(int, args.range.split('-')) if '-' in args.range else (1, 254)

    # Run
    tvs = asyncio.run(discover_tvs(subnet, start, end, has_nmap))
    print_report(tvs)
    save_reports(tvs)

    print(f"\n{Colors.OKGREEN}Discovery complete!{Colors.ENDC}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}[!] Interrupted{Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.FAIL}[!] Error: {e}{Colors.ENDC}")
        sys.exit(1)
