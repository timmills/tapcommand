#!/usr/bin/env python3
"""
Test script for device status checking system

Tests the status checking functionality for network devices
"""

import asyncio
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.device_status_checker import status_checker
from app.models.device_status import DeviceStatus
from app.models.virtual_controller import VirtualDevice, VirtualController
from app.db.database import Base

# Create test database
engine = create_engine('sqlite:///tapcommand.db')
SessionLocal = sessionmaker(bind=engine)

async def test_status_check():
    """Test device status checking"""
    print("\n" + "="*60)
    print("Testing Device Status Checker")
    print("="*60)

    db = SessionLocal()
    try:
        # Get all virtual devices
        devices = db.query(VirtualDevice).join(VirtualController).all()

        if not devices:
            print("\n⚠️  No Virtual Devices found in database")
            print("   Please adopt a network TV first using the UI")
            return False

        print(f"\nFound {len(devices)} network device(s)")

        # Test checking each device
        for device in devices:
            controller = device.controller
            print(f"\n{'='*60}")
            print(f"Checking: {controller.controller_name}")
            print(f"  Controller ID: {controller.controller_id}")
            print(f"  Protocol: {controller.protocol}")
            print(f"  IP Address: {device.ip_address}")

            # Perform status check
            await status_checker._check_device_status(db, device)
            db.commit()

            # Get updated status
            status = db.query(DeviceStatus).filter_by(
                controller_id=controller.controller_id
            ).first()

            if status:
                print(f"\n  Status Results:")
                print(f"    Online: {'✅ Yes' if status.is_online else '❌ No'}")
                print(f"    Power State: {status.power_state}")
                print(f"    Check Method: {status.check_method}")
                if status.current_channel:
                    print(f"    Current Channel: {status.current_channel}")
                if status.model_info:
                    print(f"    Model: {status.model_info}")
                print(f"    Last Checked: {status.last_checked_at}")
            else:
                print(f"  ❌ No status record created")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def test_on_demand_check():
    """Test on-demand status check"""
    print("\n" + "="*60)
    print("Testing On-Demand Status Check")
    print("="*60)

    db = SessionLocal()
    try:
        # Get first virtual controller
        controller = db.query(VirtualController).first()

        if not controller:
            print("\n⚠️  No Virtual Controllers found")
            return False

        print(f"\nRequesting immediate status check for: {controller.controller_id}")

        # Use the check_device_now method
        status = await status_checker.check_device_now(controller.controller_id)

        if status:
            print(f"\n✅ On-demand check successful:")
            print(f"  Online: {'Yes' if status.is_online else 'No'}")
            print(f"  Power: {status.power_state}")
            return True
        else:
            print(f"\n❌ On-demand check failed")
            return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def test_status_history():
    """Test status history retrieval"""
    print("\n" + "="*60)
    print("Testing Status History")
    print("="*60)

    db = SessionLocal()
    try:
        # Get all status records
        statuses = db.query(DeviceStatus).all()

        print(f"\nTotal status records: {len(statuses)}")

        for status in statuses:
            online_icon = "🟢" if status.is_online else "🔴"
            power_icon = "⚡" if status.power_state == "on" else "💤" if status.power_state == "off" else "❓"
            print(f"  {online_icon} {power_icon} {status.controller_id} - {status.power_state}")

        # Count online vs offline
        online_count = sum(1 for s in statuses if s.is_online)
        offline_count = len(statuses) - online_count

        print(f"\nSummary:")
        print(f"  Online: {online_count}")
        print(f"  Offline: {offline_count}")

        return True

    finally:
        db.close()


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("DEVICE STATUS CHECKER TEST SUITE")
    print("="*60)

    results = {
        "Status Check": False,
        "On-Demand Check": False,
        "Status History": False
    }

    # Test 1: Basic status check
    try:
        results["Status Check"] = await test_status_check()
    except Exception as e:
        print(f"\n❌ Status check test failed: {e}")

    # Test 2: On-demand check
    try:
        results["On-Demand Check"] = await test_on_demand_check()
    except Exception as e:
        print(f"\n❌ On-demand check test failed: {e}")

    # Test 3: Status history
    try:
        results["Status History"] = await test_status_history()
    except Exception as e:
        print(f"\n❌ Status history test failed: {e}")

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for test_name, passed in results.items():
        icon = "✅" if passed else "❌"
        print(f"{icon} {test_name}")

    print("\n" + "="*60)

    # Exit with appropriate code
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    asyncio.run(main())
