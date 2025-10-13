"""
Network utility functions for TapCommand
"""
import socket
import ipaddress
import logging
from typing import Optional, List, Tuple

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
    Get all local subnets from all network interfaces.
    Useful for multi-homed systems.

    Returns:
        List of subnet prefixes (e.g., ["192.168.1", "10.0.0"])
    """
    subnets = []

    try:
        # Get hostname
        hostname = socket.gethostname()

        # Get all IPs for this hostname
        # This is a simple approach - for more complex needs, consider netifaces library
        ip_list = socket.getaddrinfo(hostname, None)

        for ip_info in ip_list:
            ip = ip_info[4][0]

            # Skip loopback and IPv6
            if ip.startswith('127.') or ':' in ip:
                continue

            # Extract subnet
            octets = ip.split('.')
            if len(octets) == 4:
                subnet = '.'.join(octets[:3])
                if subnet not in subnets:
                    subnets.append(subnet)

        logger.info(f"Detected local subnets: {subnets}")

    except Exception as e:
        logger.error(f"Failed to get all local subnets: {e}")

    return subnets
