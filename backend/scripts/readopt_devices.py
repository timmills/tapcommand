#!/usr/bin/env python3
"""
Re-adopt devices script
Automatically re-adopts IR controllers and network devices based on hostname patterns
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import SessionLocal
from app.models.device_management import DeviceDiscovery, ManagedDevice, IRPort
from app.services.esphome_client import esphome_manager
from datetime import datetime

async def readopt_ir_controllers():
    """Re-adopt all IR controllers (hostnames starting with 'ir-')"""
    db = SessionLocal()
    adopted_count = 0

    try:
        # Find all IR controllers in discovery
        ir_controllers = db.query(DeviceDiscovery).filter(
            DeviceDiscovery.hostname.like('ir-%'),
            DeviceDiscovery.is_managed == False
        ).all()

        print(f"Found {len(ir_controllers)} IR controllers to adopt")
        print("=" * 80)

        for discovered in ir_controllers:
            print(f"\n📌 Adopting: {discovered.hostname} ({discovered.ip_address})")

            # Check if already managed
            existing = db.query(ManagedDevice).filter(
                ManagedDevice.hostname == discovered.hostname
            ).first()

            if existing:
                print(f"   ⚠️  Already managed, skipping")
                continue

            # Fetch capabilities
            capabilities = None
            try:
                capabilities = await esphome_manager.fetch_capabilities(
                    discovered.hostname,
                    discovered.ip_address
                )
                print(f"   ✓ Fetched capabilities")
            except Exception as e:
                print(f"   ⚠️  Failed to fetch capabilities: {e}")

            # Extract MAC
            mac = discovered.mac_address
            if capabilities and 'mac' in capabilities:
                mac = capabilities['mac']

            # Create managed device
            managed_device = ManagedDevice(
                hostname=discovered.hostname,
                mac_address=mac,
                current_ip_address=discovered.ip_address,
                device_name=discovered.friendly_name or discovered.hostname,
                venue_name=None,
                location=None,
                total_ir_ports=5,
                firmware_version=discovered.firmware_version,
                device_type=discovered.device_type or "universal",
                is_online=True,
                notes=None
            )

            db.add(managed_device)
            db.flush()

            # Create IR ports
            gpio_map = {
                1: "GPIO13",  # D7
                2: "GPIO15",  # D8
                3: "GPIO12",  # D6
                4: "GPIO16",  # D0
                5: "GPIO5"    # D1
            }

            port_prefix = mac.replace(":", "").lower() if mac else discovered.hostname

            for i in range(5):
                port_number = i + 1
                ir_port = IRPort(
                    device_id=managed_device.id,
                    port_number=port_number,
                    port_id=f"{port_prefix}-{port_number}",
                    gpio_pin=gpio_map.get(port_number),
                    is_active=True,
                    device_number=i
                )
                db.add(ir_port)

            # Mark as managed
            discovered.is_managed = True

            db.commit()
            adopted_count += 1
            print(f"   ✅ Adopted successfully (ID: {managed_device.id})")

        print(f"\n{'=' * 80}")
        print(f"✅ Adopted {adopted_count} IR controllers")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

    return adopted_count

async def readopt_network_devices():
    """Re-adopt network devices as virtual controllers (hostnames starting with 'nw-')"""
    db = SessionLocal()
    adopted_count = 0

    try:
        # Find all network devices in discovery
        network_devices = db.query(DeviceDiscovery).filter(
            DeviceDiscovery.hostname.like('nw-%'),
            DeviceDiscovery.is_managed == False
        ).all()

        print(f"\nFound {len(network_devices)} network devices to adopt")
        print("=" * 80)

        if len(network_devices) == 0:
            print("ℹ️  No network devices found with 'nw-' prefix")
            return 0

        # Note: Network TV adoption requires the network-tv API endpoints
        # which need IP/protocol detection. For now, just report what we found.
        for discovered in network_devices:
            print(f"   - {discovered.hostname} ({discovered.ip_address})")

        print(f"\n⚠️  Network device adoption requires manual setup through the UI")
        print(f"   Go to: Network Controllers page and use 'Discover TVs' button")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

    return adopted_count

async def main():
    print("🔄 Re-adoption Script")
    print("=" * 80)

    # Adopt IR controllers
    ir_count = await readopt_ir_controllers()

    # Check for network devices
    nw_count = await readopt_network_devices()

    print(f"\n{'=' * 80}")
    print(f"📊 Summary:")
    print(f"   IR Controllers adopted: {ir_count}")
    print(f"   Network devices found: {nw_count}")
    print(f"\n✅ Re-adoption complete!")

if __name__ == '__main__':
    asyncio.run(main())
