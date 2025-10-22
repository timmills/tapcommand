"""
Network Sweep Service
Performs fast network discovery with ping sweep, ARP lookup, and MAC vendor identification
"""
import asyncio
import subprocess
import re
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class NetworkSweepService:
    """Service for discovering devices on the network"""

    def __init__(self):
        self.arp_cache = {}

    async def ping_host(self, ip: str, timeout: float = 0.3) -> Dict:
        """Ping a single host and return result"""
        try:
            # Run ping with timeout (use -W flag in milliseconds)
            process = await asyncio.create_subprocess_exec(
                'ping', '-c', '1', '-W', '1', ip,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Add asyncio timeout to prevent hanging
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout + 0.2
                )
            except asyncio.TimeoutError:
                process.kill()
                return {
                    'ip': ip,
                    'online': False,
                    'response_time_ms': None
                }

            if process.returncode == 0:
                # Extract response time
                output = stdout.decode()
                time_match = re.search(r'time=(\d+\.?\d*)', output)
                response_time = float(time_match.group(1)) if time_match else None

                return {
                    'ip': ip,
                    'online': True,
                    'response_time_ms': response_time
                }
            else:
                return {
                    'ip': ip,
                    'online': False,
                    'response_time_ms': None
                }
        except Exception as e:
            logger.error(f"Error pinging {ip}: {e}")
            return {
                'ip': ip,
                'online': False,
                'response_time_ms': None,
                'error': str(e)
            }

    async def get_arp_cache(self) -> Dict[str, str]:
        """Get current ARP cache (IP -> MAC mapping)"""
        try:
            # Read ARP cache
            process = await asyncio.create_subprocess_exec(
                'ip', 'neigh', 'show',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            output = stdout.decode()

            # Parse ARP entries
            # Format: 192.168.101.1 dev eth0 lladdr aa:bb:cc:dd:ee:ff REACHABLE
            arp_map = {}
            for line in output.split('\n'):
                match = re.search(r'(\d+\.\d+\.\d+\.\d+)\s+.*?lladdr\s+([\da-f:]+)', line, re.IGNORECASE)
                if match:
                    ip = match.group(1)
                    mac = match.group(2).upper()
                    arp_map[ip] = mac

            self.arp_cache = arp_map
            return arp_map

        except Exception as e:
            logger.error(f"Error reading ARP cache: {e}")
            return {}

    def get_mac_for_ip(self, ip: str) -> Optional[str]:
        """Get MAC address for IP from ARP cache"""
        return self.arp_cache.get(ip)

    def lookup_vendor(self, mac: str, db_session) -> Optional[str]:
        """Lookup vendor from MAC address"""
        from ..models.network_discovery import MACVendor

        if not mac or mac == "Unknown":
            return None

        try:
            # Extract OUI (first 3 octets)
            # MAC format: AA:BB:CC:DD:EE:FF
            prefix = ':'.join(mac.split(':')[:3])

            vendor = db_session.query(MACVendor).filter(
                MACVendor.mac_prefix == prefix
            ).first()

            return vendor.vendor_name if vendor else "Unknown Vendor"

        except Exception as e:
            logger.error(f"Error looking up vendor for {mac}: {e}")
            return None

    def get_hostname(self, ip: str) -> Optional[str]:
        """Try to get hostname via reverse DNS"""
        try:
            result = subprocess.run(
                ['host', ip],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0:
                # Parse: "1.101.168.192.in-addr.arpa domain name pointer hostname.local."
                match = re.search(r'pointer\s+([\w\.-]+)', result.stdout)
                if match:
                    hostname = match.group(1).rstrip('.')
                    return hostname
        except Exception:
            pass
        return None

    def guess_device_type(self, vendor: str) -> Optional[str]:
        """Guess device type from vendor name using configuration"""
        from .device_scanner_config import get_device_type_by_vendor

        config = get_device_type_by_vendor(vendor)
        return config.device_type if config else None

    async def check_port_open(self, ip: str, port: int, timeout: float = 0.5) -> bool:
        """Check if a TCP port is open"""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return False

    async def identify_device_by_ports(self, ip: str, vendor: str) -> Optional[Dict]:
        """
        Identify specific device type by scanning known ports
        Returns device type and open ports
        """
        from .device_scanner_config import get_device_type_by_vendor, get_enabled_device_types

        # First try to narrow down by vendor
        vendor_config = get_device_type_by_vendor(vendor)

        if vendor_config:
            # Scan ports for this specific device type
            open_ports = []
            for port_rule in vendor_config.port_scans:
                is_open = await self.check_port_open(
                    ip,
                    port_rule.port,
                    timeout=port_rule.timeout_ms / 1000.0
                )
                if is_open:
                    open_ports.append({
                        "port": port_rule.port,
                        "protocol": port_rule.protocol,
                        "description": port_rule.description
                    })

            if open_ports:
                return {
                    "device_type": vendor_config.device_type,
                    "display_name": vendor_config.display_name,
                    "open_ports": open_ports
                }

        return None

    async def scan_subnet(
        self,
        subnet: str = "192.168.101",
        start: int = 1,
        end: int = 254,
        batch_size: int = 100,
        db_session = None
    ) -> List[Dict]:
        """
        Perform fast network sweep using nmap

        Args:
            subnet: First 3 octets (e.g., "192.168.101")
            start: Starting host number
            end: Ending host number
            batch_size: Number of concurrent pings (ignored, kept for compatibility)
            db_session: Database session for vendor lookup

        Returns:
            List of discovered devices with MAC and vendor info
        """
        from ..models.network_discovery import NetworkScanCache

        scan_id = str(uuid.uuid4())
        logger.info(f"Starting network scan {scan_id} on {subnet}.{start}-{end}")

        discovered_devices = []

        # Use nmap for fast ping sweep
        try:
            logger.info(f"Running nmap ping sweep...")
            process = await asyncio.create_subprocess_exec(
                'nmap', '-sn', '--max-retries', '0', '-T5',
                f'{subnet}.{start}-{end}',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=30.0
            )

            output = stdout.decode()
            logger.debug(f"nmap output: {output[:500]}")

            # Parse nmap output for online hosts
            online_hosts = []
            for line in output.split('\n'):
                # Look for lines like:
                # "Nmap scan report for 192.168.101.50"
                # "Nmap scan report for hostname (192.168.101.50)"
                # Match IP in parentheses first, then standalone IP
                match = re.search(r'Nmap scan report for .+?\((\d+\.\d+\.\d+\.\d+)\)', line)
                if not match:
                    match = re.search(r'Nmap scan report for (\d+\.\d+\.\d+\.\d+)', line)
                if match:
                    ip = match.group(1)
                    online_hosts.append({'ip': ip, 'online': True, 'response_time_ms': None})

            logger.info(f"Found {len(online_hosts)} online hosts via nmap")

        except asyncio.TimeoutError:
            logger.error("nmap scan timed out")
            online_hosts = []
        except Exception as e:
            logger.error(f"nmap scan failed: {e}, falling back to ping")
            # Fallback to ping sweep
            online_hosts = []
            batch_size = 50
            for batch_start in range(start, end + 1, batch_size):
                batch_end = min(batch_start + batch_size, end + 1)
                ips = [f"{subnet}.{i}" for i in range(batch_start, batch_end)]
                tasks = [self.ping_host(ip) for ip in ips]
                results = await asyncio.gather(*tasks)
                for result in results:
                    if result['online']:
                        online_hosts.append(result)

        # Step 2: Get ARP cache (contains MAC addresses from ping responses)
        logger.info("Reading ARP cache...")
        await self.get_arp_cache()

        # Step 3: Build device info with MAC and vendor lookup
        for host in online_hosts:
            ip = host['ip']
            mac = self.get_mac_for_ip(ip)
            vendor = self.lookup_vendor(mac, db_session) if mac and db_session else None
            hostname = self.get_hostname(ip)
            device_guess = self.guess_device_type(vendor)

            # Step 4: Port scan for detailed identification (if vendor matched)
            port_scan_info = None
            if vendor and device_guess:
                port_scan_info = await self.identify_device_by_ports(ip, vendor)

            # Use port scan results if available
            if port_scan_info:
                device_type_final = port_scan_info['device_type']
                display_name = port_scan_info['display_name']
                open_ports_json = str(port_scan_info['open_ports'])  # Store as string for now
            else:
                device_type_final = device_guess
                display_name = None
                open_ports_json = None

            device_info = {
                'ip_address': ip,
                'mac_address': mac or "Unknown",
                'vendor': vendor,
                'hostname': hostname,
                'is_online': True,
                'response_time_ms': host['response_time_ms'],
                'device_type_guess': device_type_final,
                'scan_id': scan_id,
                'last_seen': datetime.now(timezone.utc),
                # Additional port scan info (not in DB model yet, but added to response)
                '_port_scan_display_name': display_name,
                '_port_scan_ports': port_scan_info['open_ports'] if port_scan_info else []
            }

            discovered_devices.append(device_info)

            # Store in database if session provided
            if db_session:
                # Check if already exists
                existing = db_session.query(NetworkScanCache).filter_by(
                    ip_address=ip
                ).first()

                # Filter out fields that start with _ (not in DB model)
                db_fields = {k: v for k, v in device_info.items() if not k.startswith('_')}

                if existing:
                    # Update existing entry
                    for key, value in db_fields.items():
                        setattr(existing, key, value)
                else:
                    # Create new entry
                    cache_entry = NetworkScanCache(**db_fields)
                    db_session.add(cache_entry)

        if db_session:
            db_session.commit()

        logger.info(f"Scan {scan_id} complete: {len(discovered_devices)} devices")
        return discovered_devices

    async def scan_for_tvs(self, subnet: str = "192.168.101", db_session = None) -> List[Dict]:
        """
        Quick scan focused on TV brands

        Returns only devices that match known TV vendor MACs
        """
        all_devices = await self.scan_subnet(subnet=subnet, db_session=db_session)

        # Filter to potential TVs
        tv_devices = [
            d for d in all_devices
            if d['device_type_guess'] in [
                'samsung_tv', 'lg_tv', 'sony_tv', 'philips_tv', 'roku', 'apple_tv'
            ]
        ]

        logger.info(f"Found {len(tv_devices)} potential TV devices out of {len(all_devices)} total")
        return tv_devices

    async def scan_for_brand(
        self,
        brand: str,
        subnet: str = "192.168.101",
        db_session = None
    ) -> List[Dict]:
        """
        Scan for specific brand TVs

        Args:
            brand: "Samsung", "LG", "Sony", "Philips"
        """
        all_devices = await self.scan_subnet(subnet=subnet, db_session=db_session)

        brand_lower = brand.lower()
        brand_devices = [
            d for d in all_devices
            if d['vendor'] and brand_lower in d['vendor'].lower()
        ]

        logger.info(f"Found {len(brand_devices)} {brand} devices")
        return brand_devices

    async def scan_multiple_subnets(
        self,
        subnets: List[str],
        start: int = 1,
        end: int = 254,
        db_session = None
    ) -> List[Dict]:
        """
        Scan multiple subnets in parallel and merge results

        Args:
            subnets: List of subnet prefixes (e.g., ["192.168.101", "10.0.0", "100.64.0"])
            start: Starting host number
            end: Ending host number
            db_session: Database session for vendor lookup

        Returns:
            Combined list of discovered devices from all subnets
        """
        if not subnets:
            logger.warning("No subnets provided for scanning")
            return []

        logger.info(f"Starting multi-subnet scan across {len(subnets)} subnets: {subnets}")

        # Create tasks for parallel scanning
        tasks = [
            self.scan_subnet(subnet=subnet, start=start, end=end, db_session=db_session)
            for subnet in subnets
        ]

        # Run all scans concurrently
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Merge results and handle exceptions
            all_devices = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Scan failed for subnet {subnets[i]}: {result}")
                elif isinstance(result, list):
                    all_devices.extend(result)
                    logger.info(f"Subnet {subnets[i]} scan completed: {len(result)} devices")

            logger.info(f"Multi-subnet scan complete: {len(all_devices)} total devices across {len(subnets)} subnets")
            return all_devices

        except Exception as e:
            logger.error(f"Multi-subnet scan failed: {e}")
            return []

    async def scan_enabled_subnets(self, db_session = None) -> List[Dict]:
        """
        Scan all enabled subnets from configuration

        Reads subnet configuration from database and scans only enabled subnets.
        If no configuration exists, auto-detects subnets.

        Args:
            db_session: Database session for vendor lookup

        Returns:
            Combined list of discovered devices from all enabled subnets
        """
        from ..services.settings_service import settings_service
        from ..utils.network_utils import get_all_local_subnets

        # Get configured subnets from database
        configured = settings_service.get_setting("network_scan_subnets")

        if configured is None:
            # No configuration - auto-detect and scan all
            logger.info("No subnet configuration found, auto-detecting subnets...")
            subnets = get_all_local_subnets()

            # Save detected subnets to database for future use
            settings_service.set_setting(
                "network_scan_subnets",
                [{"subnet": s, "enabled": True} for s in subnets],
                description="Auto-detected subnets for network scanning",
                setting_type="json",
                is_public=False
            )
        else:
            # Parse configured subnets and filter to enabled only
            subnets = []

            # Handle both old format (list of strings) and new format (list of dicts)
            if isinstance(configured, list):
                for item in configured:
                    if isinstance(item, dict):
                        if item.get('enabled', True):
                            subnets.append(item['subnet'])
                    else:
                        # Old format - assume all enabled
                        subnets.append(item)

            logger.info(f"Using configured subnets: {subnets}")

        if not subnets:
            logger.warning("No enabled subnets found - skipping scan")
            return []

        # Scan all enabled subnets
        return await self.scan_multiple_subnets(subnets=subnets, db_session=db_session)


# Singleton instance
network_sweep_service = NetworkSweepService()
