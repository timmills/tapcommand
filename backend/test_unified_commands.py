#!/usr/bin/env python3
"""
Test script for unified command architecture

Tests both IR and Network TV commands through the new queue system
"""

import asyncio
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.commands.models import CommandRequest
from app.commands.queue import QueueManager
from app.db.database import Base

# Create test database
engine = create_engine('sqlite:///smartvenue.db')
SessionLocal = sessionmaker(bind=engine)

async def test_ir_command():
    """Test IR command through unified queue"""
    print("\n" + "="*60)
    print("Testing IR Command (ESPHome)")
    print("="*60)

    db = SessionLocal()
    try:
        queue_manager = QueueManager(db)

        # Create IR command request
        request = CommandRequest(
            controller_id="ir-dc4516",
            command="power",
            parameters={"port": 1}
        )

        print(f"\nSending command: {request.command} to {request.controller_id}")

        # Execute command
        result = await queue_manager.enqueue_command(request)

        print(f"\nResult:")
        print(f"  Status: {result.status}")
        print(f"  Command ID: {result.command_id}")
        if result.result_data:
            print(f"  Data: {result.result_data}")
        if result.error_message:
            print(f"  Error: {result.error_message}")

        return result.status == "completed"

    finally:
        db.close()

async def test_network_command():
    """Test Network TV command through unified queue"""
    print("\n" + "="*60)
    print("Testing Network TV Command")
    print("="*60)

    db = SessionLocal()
    try:
        queue_manager = QueueManager(db)

        # First, check if we have any Virtual Controllers
        from app.models.virtual_controller import VirtualController

        controller = db.query(VirtualController).first()

        if not controller:
            print("\n⚠️  No Virtual Controllers found in database")
            print("   Please adopt a network TV first using the UI")
            return False

        print(f"\nFound Virtual Controller: {controller.controller_name}")
        print(f"  ID: {controller.controller_id}")
        print(f"  Protocol: {controller.protocol}")

        # Create network TV command request
        request = CommandRequest(
            controller_id=controller.controller_id,
            command="power"
        )

        print(f"\nSending command: {request.command} to {request.controller_id}")

        # Execute command
        result = await queue_manager.enqueue_command(request)

        print(f"\nResult:")
        print(f"  Status: {result.status}")
        print(f"  Command ID: {result.command_id}")
        if result.result_data:
            print(f"  Data: {result.result_data}")
        if result.error_message:
            print(f"  Error: {result.error_message}")

        return result.status == "completed"

    finally:
        db.close()

async def test_command_history():
    """Test command history retrieval"""
    print("\n" + "="*60)
    print("Testing Command History")
    print("="*60)

    db = SessionLocal()
    try:
        queue_manager = QueueManager(db)

        # Get recent commands
        commands = queue_manager.get_recent_commands(limit=5)

        print(f"\nRecent commands ({len(commands)}):")
        for cmd in commands:
            status_icon = "✓" if cmd.status == "completed" else "✗"
            print(f"  {status_icon} {cmd.command} -> {cmd.controller_id} [{cmd.status}]")

        return True

    finally:
        db.close()

async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("UNIFIED COMMAND ARCHITECTURE TEST")
    print("="*60)

    results = {
        "IR Command": False,
        "Network Command": False,
        "Command History": False
    }

    # Test IR commands
    try:
        results["IR Command"] = await test_ir_command()
    except Exception as e:
        print(f"\n❌ IR Command test failed: {e}")

    # Test Network TV commands
    try:
        results["Network Command"] = await test_network_command()
    except Exception as e:
        print(f"\n❌ Network Command test failed: {e}")

    # Test command history
    try:
        results["Command History"] = await test_command_history()
    except Exception as e:
        print(f"\n❌ Command History test failed: {e}")

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
