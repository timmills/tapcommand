#!/usr/bin/env python3
"""
POTA File Analyzer for Bosch Audio Configurator

Analyzes .pota files to check API settings and device configuration
"""

import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import json

def analyze_pota(pota_file):
    """Analyze a POTA file"""

    print("=" * 80)
    print("BOSCH POTA FILE ANALYZER")
    print("=" * 80)
    print(f"File: {pota_file}")
    print("=" * 80)

    try:
        # POTA files are ZIP archives
        with zipfile.ZipFile(pota_file, 'r') as zip_ref:
            print("\n✓ POTA file opened successfully")

            # List contents
            print(f"\n📁 Archive Contents ({len(zip_ref.namelist())} files):")
            print("-" * 80)
            for name in zip_ref.namelist():
                info = zip_ref.getinfo(name)
                print(f"  - {name} ({info.file_size} bytes)")

            # Look for key files
            print("\n🔍 Analyzing Configuration Files:")
            print("-" * 80)

            for file_name in zip_ref.namelist():
                if file_name.endswith('.xml'):
                    print(f"\n📄 {file_name}")
                    print("  " + "-" * 76)

                    try:
                        content = zip_ref.read(file_name).decode('utf-8', errors='ignore')

                        # Parse XML
                        try:
                            root = ET.fromstring(content)

                            # Look for API-related settings
                            api_found = False

                            # Search for API/UDP/Control keywords
                            for elem in root.iter():
                                tag_lower = elem.tag.lower()

                                # Check element tags
                                if any(keyword in tag_lower for keyword in ['api', 'udp', 'control', 'external', 'network']):
                                    print(f"  🔍 Found: <{elem.tag}>")
                                    if elem.text:
                                        print(f"      Value: {elem.text}")
                                    if elem.attrib:
                                        print(f"      Attributes: {elem.attrib}")
                                    api_found = True

                                # Check attributes
                                for attr, value in elem.attrib.items():
                                    attr_lower = attr.lower()
                                    if any(keyword in attr_lower for keyword in ['api', 'udp', 'control', 'enable', 'port']):
                                        print(f"  🔍 Found attribute: {attr}=\"{value}\" in <{elem.tag}>")
                                        api_found = True

                            if not api_found:
                                print("  ℹ️  No API-related settings found in this file")

                        except ET.ParseError as e:
                            print(f"  ⚠️  XML parse error: {e}")
                            # Show first 500 chars anyway
                            print(f"  Raw content preview:")
                            print("  " + content[:500].replace("\n", "\n  "))

                    except Exception as e:
                        print(f"  ❌ Error reading file: {e}")

                elif file_name.endswith('.json'):
                    print(f"\n📄 {file_name}")
                    print("  " + "-" * 76)

                    try:
                        content = zip_ref.read(file_name).decode('utf-8')
                        data = json.loads(content)

                        # Pretty print JSON
                        print(json.dumps(data, indent=2)[:1000])

                    except Exception as e:
                        print(f"  ❌ Error parsing JSON: {e}")

            # Look for device information
            print("\n\n🖥️  Device Information:")
            print("-" * 80)

            for file_name in zip_ref.namelist():
                if 'device' in file_name.lower() or 'plena' in file_name.lower() or 'plm' in file_name.lower():
                    print(f"\n📄 {file_name}")
                    try:
                        content = zip_ref.read(file_name).decode('utf-8', errors='ignore')

                        # Look for IP address
                        if '192.168' in content or '10.' in content:
                            import re
                            ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', content)
                            if ips:
                                print(f"  IP Addresses found: {', '.join(set(ips))}")

                        # Look for model
                        if 'PLM' in content or 'plena' in content.lower():
                            lines = content.split('\n')
                            for line in lines:
                                if 'PLM' in line or 'plena' in line.lower():
                                    print(f"  {line.strip()[:100]}")

                    except Exception as e:
                        print(f"  ⚠️  Could not read: {e}")

            print("\n\n" + "=" * 80)
            print("RECOMMENDATIONS:")
            print("=" * 80)
            print("""
1. Look for any settings containing "API", "UDP", "Enable", or "Control"
2. Check if port 12128/12129 are configured
3. Look for "External Control" or "3rd Party Integration" settings
4. If you see API settings disabled, modify them in Bosch Audio Configurator
5. Upload the modified configuration to the device
            """)

    except zipfile.BadZipFile:
        print("❌ ERROR: Not a valid POTA/ZIP file")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_pota.py <path_to_pota_file>")
        print("Example: python analyze_pota.py config.pota")
        sys.exit(1)

    pota_file = sys.argv[1]

    if not Path(pota_file).exists():
        print(f"❌ ERROR: File not found: {pota_file}")
        sys.exit(1)

    success = analyze_pota(pota_file)
    sys.exit(0 if success else 1)
