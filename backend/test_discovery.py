#!/usr/bin/env python3
"""
Simple test script for TapCommand device discovery
Run this to test mDNS discovery without starting the full API
"""

import asyncio
import logging
from app.services.discovery import discovery_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_discovery():
    """Test device discovery"""
    logger.info("Starting device discovery test...")

    def on_discovered(device):
        logger.info(f"Discovered: {device.hostname} -> {device.ip_address}")
        logger.info(f"  Type: {device.device_type}")
        logger.info(f"  Friendly name: {device.friendly_name}")
        logger.info(f"  Properties: {device.properties}")

    def on_removed(hostname):
        logger.info(f"Removed: {hostname}")

    # Add callbacks
    discovery_service.add_discovery_callback(on_discovered)
    discovery_service.add_removal_callback(on_removed)

    # Start discovery
    await discovery_service.start_discovery()

    try:
        # Run for 30 seconds
        logger.info("Discovery running for 30 seconds...")
        await asyncio.sleep(30)

        # Show discovered devices
        devices = discovery_service.get_discovered_devices()
        logger.info(f"\nFound {len(devices)} devices:")
        for device in devices:
            logger.info(f"  {device.hostname} ({device.ip_address}) - {device.device_type}")

    finally:
        await discovery_service.stop_discovery()
        logger.info("Discovery test complete")


if __name__ == "__main__":
    asyncio.run(test_discovery())