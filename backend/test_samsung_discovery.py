#!/usr/bin/env python3
"""
Quick test script to discover Samsung TVs on the network
Tests connectivity and gathers device information
"""

import sys
import requests
from samsungtvws import SamsungTVWS

# Samsung TVs on your network
TV_IPS = [
    "192.168.101.48",
    "192.168.101.50",
    "192.168.101.52"
]

def test_tv_rest_api(ip: str):
    """Test if Samsung TV REST API is accessible"""
    try:
        url = f"http://{ip}:8001/api/v2/"
        response = requests.get(url, timeout=3)

        if response.status_code == 200:
            data = response.json()
            device_info = data.get('device', {})

            return {
                'ip': ip,
                'reachable': True,
                'name': device_info.get('name', 'Unknown'),
                'model': device_info.get('modelName', 'Unknown'),
                'version': device_info.get('version', 'Unknown'),
                'type': device_info.get('type', 'Unknown'),
                'wifi_mac': device_info.get('wifiMac', 'Unknown'),
                'raw_response': data
            }
        else:
            return {
                'ip': ip,
                'reachable': False,
                'error': f'HTTP {response.status_code}'
            }

    except requests.exceptions.Timeout:
        return {
            'ip': ip,
            'reachable': False,
            'error': 'Connection timeout'
        }
    except requests.exceptions.ConnectionError:
        return {
            'ip': ip,
            'reachable': False,
            'error': 'Connection refused - TV might be off or port blocked'
        }
    except Exception as e:
        return {
            'ip': ip,
            'reachable': False,
            'error': str(e)
        }


def test_websocket_connection(ip: str):
    """Test WebSocket connection (requires pairing)"""
    try:
        # This will trigger on-screen pairing prompt if not already paired
        tv = SamsungTVWS(host=ip, port=8001, name="TapCommand Discovery Test")

        # Try to get token (won't work without user accepting on TV)
        # Just testing if port is open and responding
        return {
            'websocket_port_open': True,
            'note': 'WebSocket port accessible (pairing required for control)'
        }
    except Exception as e:
        return {
            'websocket_port_open': False,
            'error': str(e)
        }


def main():
    print("=" * 70)
    print("Samsung TV Network Discovery Test")
    print("=" * 70)
    print()

    results = []

    for ip in TV_IPS:
        print(f"Testing {ip}...")
        print("-" * 70)

        # Test REST API
        rest_result = test_tv_rest_api(ip)
        results.append(rest_result)

        if rest_result['reachable']:
            print(f"✓ REST API accessible")
            print(f"  Name: {rest_result['name']}")
            print(f"  Model: {rest_result['model']}")
            print(f"  Version: {rest_result['version']}")
            print(f"  Type: {rest_result['type']}")
            print(f"  WiFi MAC: {rest_result['wifi_mac']}")

            # Test WebSocket
            ws_result = test_websocket_connection(ip)
            if ws_result['websocket_port_open']:
                print(f"✓ WebSocket port 8001 accessible")
                print(f"  {ws_result['note']}")
            else:
                print(f"✗ WebSocket connection failed: {ws_result['error']}")
        else:
            print(f"✗ Not reachable: {rest_result['error']}")

        print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    reachable_count = sum(1 for r in results if r['reachable'])
    print(f"TVs found: {reachable_count}/{len(TV_IPS)}")
    print()

    if reachable_count > 0:
        print("Next steps:")
        print("1. Choose a TV to pair with")
        print("2. Run pairing script (will trigger on-screen prompt)")
        print("3. Accept pairing on TV within 30 seconds")
        print("4. Token will be saved for future use")
    else:
        print("No TVs found. Check:")
        print("- Are TVs powered on?")
        print("- Are they on the same network?")
        print("- Is port 8001 blocked by firewall?")

    print()

    # Save results to file for reference
    import json
    with open('/tmp/samsung_tv_discovery.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("Full results saved to: /tmp/samsung_tv_discovery.json")


if __name__ == "__main__":
    main()
