"""
Network utility functions for TapCommand
"""
import socket
import ipaddress
import logging
import subprocess
import re
from typing import Optional, List, Tuple, Dict

logger = logging.getLogger(__name__)


def get_local_ip_and_subnet() -> Tuple[Optional[str], Optional[str]]:
    """
    Detect the local IP address and subnet by finding the interface
    used to reach the internet.

    Returns:
        Tuple of (ip_address, subnet_prefix)
        Example: ("192.168.1.50", "192.168.1")
    """
    try:
        # Create a socket to find which interface would be used to reach the internet
        # This doesn't actually send any packets
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        try:
            # Connect to Google DNS (doesn't actually send anything)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
        finally:
            s.close()

        if local_ip and local_ip != '127.0.0.1':
            # Extract the first 3 octets as subnet
            octets = local_ip.split('.')
            if len(octets) == 4:
                subnet = '.'.join(octets[:3])
                logger.info(f"Auto-detected local network: {local_ip} on subnet {subnet}.0/24")
                return local_ip, subnet

        logger.warning(f"Detected IP {local_ip} but could not determine subnet")
        return local_ip, None

    except Exception as e:
        logger.error(f"Failed to auto-detect local network: {e}")
        return None, None


def get_default_subnet() -> str:
    """
    Get the default subnet to use for network scanning.

    Auto-detects the local subnet if possible, otherwise falls back
    to a sensible default.

    Returns:
        Subnet prefix as string (e.g., "192.168.1")
    """
    _, subnet = get_local_ip_and_subnet()

    if subnet:
        return subnet

    # Fallback to common home network subnet
    logger.warning("Could not auto-detect subnet, falling back to 192.168.1")
    return "192.168.1"


def validate_subnet(subnet: str) -> bool:
    """
    Validate that a subnet string is valid.

    Args:
        subnet: Subnet prefix like "192.168.1" or "10.0.0"

    Returns:
        True if valid, False otherwise
    """
    try:
        # Try to construct a valid IP from the subnet
        test_ip = f"{subnet}.1"
        ipaddress.ip_address(test_ip)

        # Check it has exactly 3 octets
        octets = subnet.split('.')
        if len(octets) != 3:
            return False

        # Check each octet is a valid number
        for octet in octets:
            num = int(octet)
            if num < 0 or num > 255:
                return False

        return True

    except (ValueError, AttributeError):
        return False


def get_all_local_subnets() -> List[str]:
    """
    Get all local subnets from all network interfaces using 'ip addr'.
    Properly handles multiple NICs, Tailscale, and variable CIDR masks.

    Filters out:
    - Loopback addresses (127.x.x.x)
    - IPv6 addresses
    - Link-local addresses (169.254.x.x)

    Returns:
        List of subnet prefixes (e.g., ["192.168.1", "10.0.0", "100.64.0"])
    """
    subnets = []

    try:
        # Use 'ip addr show' to get all interface addresses
        result = subprocess.run(
            ['ip', 'addr', 'show'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            logger.warning("Failed to run 'ip addr show', falling back to socket method")
            return _get_subnets_fallback()

        # Parse output for IPv4 addresses with CIDR
        # Format: "inet 192.168.101.153/24 brd 192.168.101.255 scope global eth0"
        for line in result.stdout.split('\n'):
            match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)/(\d+)', line)
            if match:
                ip = match.group(1)
                cidr = int(match.group(2))

                # Skip loopback
                if ip.startswith('127.'):
                    continue

                # Skip link-local
                if ip.startswith('169.254.'):
                    continue

                # Extract subnet based on CIDR mask
                subnet = _cidr_to_subnet(ip, cidr)

                if subnet and subnet not in subnets:
                    subnets.append(subnet)
                    logger.debug(f"Detected subnet {subnet}.0/{cidr} from interface with IP {ip}")

        logger.info(f"Detected {len(subnets)} local subnets: {subnets}")

    except FileNotFoundError:
        logger.warning("'ip' command not found, falling back to socket method")
        return _get_subnets_fallback()
    except Exception as e:
        logger.error(f"Failed to get all local subnets: {e}")
        return _get_subnets_fallback()

    return subnets


def _cidr_to_subnet(ip: str, cidr: int) -> Optional[str]:
    """
    Convert an IP address and CIDR mask to a subnet prefix.

    Args:
        ip: IP address (e.g., "192.168.101.153")
        cidr: CIDR mask (e.g., 24)

    Returns:
        Subnet prefix (e.g., "192.168.101") or None if unsupported
    """
    try:
        octets = ip.split('.')
        if len(octets) != 4:
            return None

        if cidr == 24:
            # Most common: /24 = 255.255.255.0
            return '.'.join(octets[:3])
        elif cidr == 16:
            # /16 = 255.255.0.0
            return '.'.join(octets[:2]) + '.0'
        elif cidr == 8:
            # /8 = 255.0.0.0 (rare but used by Tailscale sometimes)
            return octets[0] + '.0.0'
        elif cidr >= 25 and cidr <= 30:
            # /25-/30: Still use /24 subnet for scanning simplicity
            # This means we'll scan the entire /24 even if host is on smaller subnet
            logger.debug(f"Converting /{cidr} to /24 for scanning: {ip}")
            return '.'.join(octets[:3])
        elif cidr >= 17 and cidr <= 23:
            # /17-/23: Use /16 subnet for scanning
            logger.debug(f"Converting /{cidr} to /16 for scanning: {ip}")
            return '.'.join(octets[:2]) + '.0'
        elif cidr == 10:
            # Tailscale uses /10 (100.64.0.0/10)
            # Scan just the /16 where this IP resides
            logger.debug(f"Tailscale /10 detected, using /16 subset for scanning: {ip}")
            return '.'.join(octets[:2]) + '.0'
        else:
            logger.warning(f"Unsupported CIDR mask /{cidr} for IP {ip}, skipping")
            return None

    except Exception as e:
        logger.error(f"Error converting CIDR to subnet: {e}")
        return None


def _get_subnets_fallback() -> List[str]:
    """
    Fallback method using socket.getaddrinfo() if 'ip addr' is unavailable.
    Less reliable but works on systems without iproute2.

    Returns:
        List of subnet prefixes
    """
    subnets = []

    try:
        hostname = socket.gethostname()
        ip_list = socket.getaddrinfo(hostname, None)

        for ip_info in ip_list:
            ip = ip_info[4][0]

            # Skip loopback and IPv6
            if ip.startswith('127.') or ':' in ip:
                continue

            # Skip link-local
            if ip.startswith('169.254.'):
                continue

            # Extract /24 subnet (assume /24 since we don't have CIDR info)
            octets = ip.split('.')
            if len(octets) == 4:
                subnet = '.'.join(octets[:3])
                if subnet not in subnets:
                    subnets.append(subnet)

        logger.info(f"Fallback method detected subnets: {subnets}")

    except Exception as e:
        logger.error(f"Fallback subnet detection failed: {e}")

    return subnets


def get_interface_info() -> List[Dict[str, str]]:
    """
    Get detailed information about all network interfaces.

    Returns:
        List of dicts with keys: interface, ip, subnet, cidr, state
        Example: [
            {"interface": "eth0", "ip": "192.168.101.153", "subnet": "192.168.101", "cidr": "24", "state": "UP"},
            {"interface": "tailscale0", "ip": "100.64.1.2", "subnet": "100.64.0", "cidr": "10", "state": "UP"}
        ]
    """
    interfaces = []

    try:
        result = subprocess.run(
            ['ip', 'addr', 'show'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return interfaces

        current_interface = None
        current_state = None

        for line in result.stdout.split('\n'):
            # Match interface line: "2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500"
            iface_match = re.search(r'^\d+:\s+(\S+):\s+<([^>]+)>', line)
            if iface_match:
                current_interface = iface_match.group(1)
                flags = iface_match.group(2)
                current_state = 'UP' if 'UP' in flags else 'DOWN'
                continue

            # Match inet line: "inet 192.168.101.153/24 brd 192.168.101.255 scope global eth0"
            inet_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)/(\d+)', line)
            if inet_match and current_interface:
                ip = inet_match.group(1)
                cidr = inet_match.group(2)

                # Skip loopback
                if ip.startswith('127.'):
                    continue

                subnet = _cidr_to_subnet(ip, int(cidr))

                if subnet:
                    interfaces.append({
                        'interface': current_interface,
                        'ip': ip,
                        'subnet': subnet,
                        'cidr': cidr,
                        'state': current_state
                    })

        logger.debug(f"Detected {len(interfaces)} interfaces: {interfaces}")

    except Exception as e:
        logger.error(f"Failed to get interface info: {e}")

    return interfaces
