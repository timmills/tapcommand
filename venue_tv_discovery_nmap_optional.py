#!/usr/bin/env python3
"""
SmartVenue Network TV Discovery Tool (nmap optional)
====================================================

Standalone script for onsite venue surveys to discover network-controllable TVs.
Falls back to Python-based ping if nmap not available.

Usage:
    python3 venue_tv_discovery_nmap_optional.py [subnet]
    python3 venue_tv_discovery_nmap_optional.py 192.168.101
    python3 venue_tv_discovery_nmap_optional.py --help

Requirements:
    - Python 3.8+
    - pip packages: requests, tabulate
    - nmap (optional, for faster scans)

Installation:
    pip3 install requests tabulate
    sudo apt-get install nmap -y  # Optional but recommended
"""

import subprocess
import re
import json
import csv
import socket
import argparse
import sys
import asyncio
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

# TV vendor MAC prefix database (comprehensive coverage)
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
    "A4:EB:D3": "Samsung", "50:32:75": "Samsung", "00:09:18": "Samsung",
    "7C:64:56": "Samsung", "CC:6E:A4": "Samsung",  # Added from actual devices found

    # LG (185+ prefixes)
    "00:E0:91": "LG", "B8:38:61": "LG", "A0:23:9F": "LG",
    "00:1C:62": "LG", "00:1E:75": "LG", "00:1F:6B": "LG",
    "00:22:A9": "LG", "00:24:83": "LG", "10:68:3F": "LG",
    "40:B8:9A": "LG", "54:33:CB": "LG", "60:6B:BD": "LG",
    "64:BC:0C": "LG", "78:5D:C8": "LG", "9C:80:DF": "LG",
    "A8:23:FE": "LG", "C8:08:E9": "LG", "F4:7B:5E": "LG",

    # Sony (138+ prefixes)
    "00:04:1F": "Sony", "00:0D:F0": "Sony", "00:13:A9": "Sony",
    "00:16:FE": "Sony", "00:19:C5": "Sony", "00:1A:80": "Sony",
    "00:1B:63": "Sony", "00:1D:BA": "Sony", "00:1E:3D": "Sony",
    "30:52:CB": "Sony", "54:42:49": "Sony", "AC:9B:0A": "Sony",
    "FC:F1:52": "Sony", "08:00:46": "Sony", "00:1D:0D": "Sony",

    # Philips (22+ prefixes)
    "00:01:FE": "Philips", "00:04:ED": "Philips", "00:09:6E": "Philips",
    "00:0D:3A": "Philips", "00:12:56": "Philips", "00:17:A4": "Philips",
    "50:D4:F7": "Philips", "00:0E:9B": "Philips",

    # Roku
    "00:0D:4B": "Roku", "D8:31:CF": "Roku", "CC:6D:A0": "Roku",
    "B0:A7:37": "Roku", "B8:A1:75": "Roku", "DC:3A:5E": "Roku",

    # Apple TV
    "7C:61:66": "Apple TV", "A4:D1:D2": "Apple TV", "F0:DB:F8": "Apple TV",
    "00:25:00": "Apple TV", "28:37:37": "Apple TV",

    # Vizio
    "00:1B:FB": "Vizio", "E0:B9:4D": "Vizio", "00:26:18": "Vizio",

    # Panasonic
    "00:09:D0": "Panasonic", "00:0D:8E": "Panasonic", "00:1C:CD": "Panasonic",

    # TCL
    "D4:AB:82": "TCL", "F4:06:16": "TCL", "C8:31:43": "TCL",

    # Hisense
    "00:1E:8C": "Hisense", "28:76:10": "Hisense", "D8:0D:17": "Hisense",

    # Sharp
    "00:0D:4A": "Sharp", "00:1D:BC": "Sharp", "04:4E:AF": "Sharp",
}

# Protocol detection ports
PROTOCOL_PORTS = {
    "Samsung Legacy": [55000],
    "Samsung Modern": [8001, 8002],
    "LG WebOS": [3000, 3001],
    "Sony IRCC": [80],
    "Philips JointSpace": [1925, 1926],
    "Roku": [8060],
}

def check_dependencies() -> Tuple[bool, List[str], bool]:
    """Check if required dependencies are installed"""
    missing = []
    has_nmap = False

    # Check nmap (optional)
    try:
        subprocess.run(['nmap', '--version'], capture_output=True, timeout=2)
        has_nmap = True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass  # nmap is optional

    # Check Python packages
    try:
        import requests
    except ImportError:
        missing.append('requests (install: pip3 install requests)')

    try:
        from tabulate import tabulate
    except ImportError:
        missing.append('tabulate (install: pip3 install tabulate)')

    return len(missing) == 0, missing, has_nmap

def get_mac_vendor(mac: str) -> Optional[str]:
    """Lookup vendor from MAC address using built-in database"""
    if not mac or mac == "Unknown":
        return None

    # Extract OUI (first 3 octets)
    prefix = ':'.join(mac.upper().split(':')[:3])

    return TV_VENDORS.get(prefix)

async def ping_host_async(ip: str, timeout: float = 0.5) -> Dict:
    """Async ping a single host"""
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

    except Exception as e:
        return {'ip': ip, 'online': False, 'latency_ms': None}

async def ping_sweep_async(subnet: str, start: int = 1, end: int = 254) -> List[Dict]:
    """Async ping sweep (fallback when nmap not available)"""
    print(f"{Colors.OKBLUE}[*] Scanning {subnet}.{start}-{end} with async ping (nmap not available)...{Colors.ENDC}")
    print(f"{Colors.WARNING}    Note: This is slower than nmap. Consider installing nmap for faster scans.{Colors.ENDC}")

    # Create tasks for all IPs in batches
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

    print()  # New line after progress
    return all_results

def run_nmap_scan(subnet: str, start: int = 1, end: int = 254) -> List[Dict]:
    """Run nmap ping sweep to find online hosts"""
    print(f"{Colors.OKBLUE}[*] Scanning {subnet}.{start}-{end} with nmap...{Colors.ENDC}")

    try:
        cmd = [
            'nmap', '-sn',
            '--max-retries', '1',
            '-T4',
            f'{subnet}.{start}-{end}'
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        output = result.stdout
        online_hosts = []
        current_ip = None

        for line in output.split('\n'):
            ip_match = re.search(r'Nmap scan report for (\d+\.\d+\.\d+\.\d+)', line)
            if ip_match:
                current_ip = ip_match.group(1)

            if current_ip and 'Host is up' in line:
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
    elif vendor == "Roku":
        ports_to_check.extend([8060])
    elif vendor in ["Vizio", "TCL", "Hisense", "Sharp", "Panasonic"]:
        # Generic TV ports
        ports_to_check.extend([80, 8080])

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
            elif port == 8060:
                detected_protocols.append("Roku ECP")
            elif port in [80, 8080]:
                detected_protocols.append(f"{vendor} HTTP")

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

async def discover_tvs_on_network_async(subnet: str = "192.168.1", start: int = 1, end: int = 254, use_nmap: bool = True) -> List[Dict]:
    """Main discovery function - find all TVs on network"""

    print(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}SmartVenue Network TV Discovery - ALL BRANDS{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}\n")

    print(f"{Colors.OKCYAN}Scanning for: Samsung, LG, Sony, Philips, Roku, Apple TV,{Colors.ENDC}")
    print(f"{Colors.OKCYAN}              Vizio, Panasonic, TCL, Hisense, Sharp{Colors.ENDC}\n")

    # Step 1: Network scan (nmap or async ping)
    if use_nmap:
        online_hosts = run_nmap_scan(subnet, start, end)
    else:
        online_hosts = await ping_sweep_async(subnet, start, end)

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
        if vendor in ["Samsung", "LG", "Sony", "Philips", "Roku", "Apple TV", "Vizio", "Panasonic", "TCL", "Hisense", "Sharp"]:
            potential_tvs.append({
                'ip': ip,
                'mac': mac,
                'vendor': vendor,
                'hostname': hostname,
                'latency_ms': host.get('latency_ms')
            })

    print(f"{Colors.OKGREEN}[✓] Found {len(potential_tvs)} potential TV devices{Colors.ENDC}")

    if not potential_tvs:
        print(f"{Colors.WARNING}[!] No TV vendors detected.{Colors.ENDC}")
        print(f"{Colors.WARNING}    Showing first 10 online hosts for debugging:{Colors.ENDC}\n")
        for host in online_hosts[:10]:
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
        'brands_found': list(set([tv['vendor'] for tv in tvs])),
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

    # Group by vendor
    by_vendor = {}
    for tv in tvs:
        vendor = tv['vendor']
        if vendor not in by_vendor:
            by_vendor[vendor] = []
        by_vendor[vendor].append(tv)

    for vendor, vendor_tvs in by_vendor.items():
        print(f"{Colors.OKGREEN}{vendor} TVs ({len(vendor_tvs)} found):{Colors.ENDC}")
        print(f"  IPs: {', '.join([tv['ip'] for tv in vendor_tvs])}")
        print(f"  Protocols: {', '.join(set([p for tv in vendor_tvs for p in tv.get('protocols', [])]))}")
        print()

    print(f"{Colors.OKBLUE}All discovered TVs can be adopted into SmartVenue.{Colors.ENDC}")
    print(f"{Colors.OKBLUE}Import the JSON/CSV report to proceed with adoption.{Colors.ENDC}\n")

def main():
    parser = argparse.ArgumentParser(
        description='SmartVenue Network TV Discovery Tool - Find ALL TV brands',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported Brands:
  Samsung, LG, Sony, Philips, Roku, Apple TV, Vizio,
  Panasonic, TCL, Hisense, Sharp

Examples:
  python3 venue_tv_discovery_nmap_optional.py 192.168.101
  python3 venue_tv_discovery_nmap_optional.py 10.0.0 --range 1-50
        """
    )

    parser.add_argument(
        'subnet',
        nargs='?',
        default='192.168.1',
        help='Network subnet to scan (first 3 octets)'
    )

    parser.add_argument(
        '--range',
        default='1-254',
        help='IP range to scan (default: 1-254)'
    )

    args = parser.parse_args()

    # Check dependencies
    deps_ok, missing, has_nmap = check_dependencies()
    if not deps_ok:
        print(f"{Colors.FAIL}Missing required dependencies:{Colors.ENDC}")
        for dep in missing:
            print(f"  - {dep}")
        print(f"\n{Colors.WARNING}Please install missing dependencies and try again.{Colors.ENDC}")
        sys.exit(1)

    if not has_nmap:
        print(f"{Colors.WARNING}Note: nmap not found. Using slower Python-based ping.{Colors.ENDC}")
        print(f"{Colors.WARNING}For faster scans, install nmap: sudo apt-get install nmap{Colors.ENDC}\n")

    # Parse range
    if '-' in args.range:
        start, end = map(int, args.range.split('-'))
    else:
        start, end = 1, 254

    # Run discovery
    tvs = asyncio.run(discover_tvs_on_network_async(args.subnet, start, end, has_nmap))

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
        import traceback
        traceback.print_exc()
        sys.exit(1)
