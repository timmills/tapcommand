"""
TV Confidence Scorer
Analyzes devices to determine likelihood they are actual TVs vs other devices
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class TVConfidenceScorer:
    """Score devices based on likelihood of being a TV"""

    # Ports that indicate a TV
    TV_PORTS = {
        55000: ("Samsung Legacy TV", 90),
        8001: ("Samsung Tizen TV", 90),
        8002: ("Samsung Tizen SSL", 85),
        3000: ("LG webOS / Hisense", 80),
        3001: ("LG webOS SSL", 80),
        36669: ("Hisense Remote", 95),
        1925: ("Philips JointSpace", 90),
        1926: ("Philips JointSpace SSL", 85),
        8060: ("Roku ECP", 85),
        7345: ("Vizio SmartCast", 90),
        9000: ("Vizio Cast", 80),
        50001: ("Sony Control", 85),
        50002: ("Sony Control Alt", 80),
    }

    # Ports that indicate NOT a TV (phones, tablets, PCs)
    NON_TV_PORTS = {
        5037: ("Android ADB", -50),  # Android Debug Bridge (phones/tablets)
        62078: ("Android Wireless ADB", -50),
        22: ("SSH", -20),  # More common on PCs/servers
        3389: ("RDP", -40),  # Remote Desktop (Windows PCs)
        5900: ("VNC", -30),  # VNC (computers)
        445: ("SMB", -20),  # File sharing (computers)
    }

    # Hostname patterns that indicate TVs
    TV_HOSTNAME_PATTERNS = [
        ("tv", 30),
        ("samsung-tv", 40),
        ("lg-tv", 40),
        ("hisense", 40),
        ("roku", 35),
        ("smart-tv", 40),
    ]

    # Hostname patterns that indicate NOT a TV (stronger penalties)
    NON_TV_HOSTNAME_PATTERNS = [
        ("laptop", -80),
        ("desktop", -80),
        ("pc", -70),
        ("tablet", -90),
        ("tab-a", -90),  # Galaxy Tab A
        ("phone", -90),
        ("ipad", -90),
        ("iphone", -90),
        ("galaxy-tab", -90),
        ("galaxy-a", -80),  # Galaxy A series phones/tablets
        ("galaxy-s", -80),  # Galaxy S series phones
        ("macbook", -80),
        ("imac", -80),
    ]

    def score_device(
        self,
        vendor: Optional[str],
        hostname: Optional[str],
        open_ports: List[int],
        device_type_guess: Optional[str]
    ) -> Dict:
        """
        Score a device's likelihood of being a TV

        Returns:
            {
                'confidence_score': int (0-100),
                'is_likely_tv': bool,
                'reason': str,
                'port_matches': List[str],
                'hostname_hints': List[str]
            }
        """
        score = 50  # Start neutral
        port_matches = []
        hostname_hints = []
        reasons = []

        # 1. Check device type guess (if port scanning already identified it)
        if device_type_guess:
            tv_types = [
                'samsung_tv_legacy', 'samsung_tv_tizen',
                'lg_webos', 'sony_bravia', 'philips_android',
                'hisense_vidaa', 'tcl_roku', 'vizio_smartcast'
            ]
            if device_type_guess in tv_types:
                score += 40
                reasons.append(f"Port scan identified as {device_type_guess}")

        # 2. Check open ports for TV indicators
        for port in open_ports:
            if port in self.TV_PORTS:
                desc, points = self.TV_PORTS[port]
                score += points
                port_matches.append(f"{port} ({desc})")
                reasons.append(f"TV port {port} open ({desc})")

            if port in self.NON_TV_PORTS:
                desc, points = self.NON_TV_PORTS[port]
                score += points  # points are negative
                reasons.append(f"Non-TV port {port} ({desc})")

        # 3. Check hostname patterns
        if hostname:
            hostname_lower = hostname.lower()

            for pattern, points in self.TV_HOSTNAME_PATTERNS:
                if pattern in hostname_lower:
                    score += points
                    hostname_hints.append(f"'{pattern}' in hostname (+{points})")
                    reasons.append(f"Hostname contains '{pattern}'")

            for pattern, points in self.NON_TV_HOSTNAME_PATTERNS:
                if pattern in hostname_lower:
                    score += points  # points are negative
                    hostname_hints.append(f"'{pattern}' in hostname ({points})")
                    reasons.append(f"Hostname contains '{pattern}' (not a TV)")

        # 4. Vendor bonus (if recognized TV brand)
        if vendor:
            vendor_lower = vendor.lower()
            tv_vendors = ['samsung', 'lg', 'sony', 'hisense', 'philips', 'vizio', 'tcl', 'roku']

            for tv_vendor in tv_vendors:
                if tv_vendor in vendor_lower:
                    score += 20
                    reasons.append(f"TV vendor: {tv_vendor}")
                    break

        # Cap score between 0-100
        score = max(0, min(100, score))

        # Determine if likely a TV (threshold: 60)
        is_likely_tv = score >= 60

        return {
            'confidence_score': score,
            'is_likely_tv': is_likely_tv,
            'reason': '; '.join(reasons) if reasons else 'No specific indicators',
            'port_matches': port_matches,
            'hostname_hints': hostname_hints
        }


# Singleton instance
tv_confidence_scorer = TVConfidenceScorer()
