#!/usr/bin/env python3
"""
Standalone Network Scanner
Runs independently from web server, scans network and updates database

Usage:
    python3 -m app.services.standalone_network_scanner --subnet 192.168.101 --start 1 --end 254
    python3 -m app.services.standalone_network_scanner --scan-tvs  # Quick TV-only scan
    python3 -m app.services.standalone_network_scanner --continuous  # Run every 5 minutes
"""

import asyncio
import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.database import SessionLocal
from app.models.network_discovery import NetworkScanCache, MACVendor
from app.services.network_sweep import network_sweep_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def perform_scan(subnet: str, start: int, end: int, scan_tvs_only: bool = False):
    """Perform network scan and update database"""
    db = SessionLocal()
    try:
        logger.info(f"🔍 Starting network scan: {subnet}.{start}-{end}")
        start_time = time.time()

        if scan_tvs_only:
            devices = await network_sweep_service.scan_for_tvs(
                subnet=subnet,
                db_session=db
            )
            logger.info(f"✅ TV scan complete: {len(devices)} TVs found")
        else:
            devices = await network_sweep_service.scan_subnet(
                subnet=subnet,
                start=start,
                end=end,
                db_session=db
            )
            logger.info(f"✅ Scan complete: {len(devices)} devices found")

        elapsed = time.time() - start_time
        logger.info(f"⏱️  Scan duration: {elapsed:.2f} seconds")

        # Print summary
        if devices:
            logger.info("\n📊 Discovered Devices:")
            logger.info("-" * 80)
            for dev in devices:
                vendor = dev.get('vendor', 'Unknown')
                device_type = dev.get('device_type_guess', '')
                display_name = dev.get('_port_scan_display_name')
                open_ports = dev.get('_port_scan_ports', [])

                # Build type badge
                if display_name:
                    type_badge = f"[{display_name}]"
                elif device_type:
                    type_badge = f"[{device_type}]"
                else:
                    type_badge = ""

                # Show open ports
                ports_info = ""
                if open_ports:
                    port_list = ", ".join([f"{p['port']} ({p['description']})" for p in open_ports])
                    ports_info = f" | Ports: {port_list}"

                logger.info(
                    f"  {dev['ip_address']:15} | {dev['mac_address']:17} | "
                    f"{vendor:30} {type_badge}{ports_info}"
                )
            logger.info("-" * 80)

            # Show TV summary with port details
            tv_devices = [d for d in devices if d.get('device_type_guess')]
            if tv_devices:
                logger.info(f"\n📺 Found {len(tv_devices)} potential TV devices:")
                for dev in tv_devices:
                    display_name = dev.get('_port_scan_display_name', dev.get('device_type_guess'))
                    open_ports = dev.get('_port_scan_ports', [])

                    port_info = ""
                    if open_ports:
                        port_nums = [str(p['port']) for p in open_ports]
                        port_info = f" [Ports: {', '.join(port_nums)}]"

                    logger.info(
                        f"  {dev['ip_address']} - {display_name} "
                        f"({dev.get('vendor', 'Unknown')}){port_info}"
                    )

        return devices

    except Exception as e:
        logger.error(f"❌ Scan failed: {e}", exc_info=True)
        return []
    finally:
        db.close()


async def continuous_scan(subnet: str, interval_minutes: int = 5):
    """Run network scan continuously at specified interval"""
    logger.info(f"🔄 Starting continuous scanning mode (every {interval_minutes} minutes)")
    logger.info(f"   Subnet: {subnet}")
    logger.info(f"   Press Ctrl+C to stop")

    while True:
        try:
            await perform_scan(subnet, 1, 254, scan_tvs_only=False)
            logger.info(f"💤 Sleeping for {interval_minutes} minutes...")
            await asyncio.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            logger.info("\n⏹️  Stopping continuous scan")
            break
        except Exception as e:
            logger.error(f"❌ Error in continuous scan: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retry


async def main():
    parser = argparse.ArgumentParser(
        description='Standalone Network Scanner - Updates database with discovered devices'
    )
    parser.add_argument(
        '--subnet',
        default='192.168.101',
        help='Subnet to scan (first 3 octets, e.g., 192.168.101)'
    )
    parser.add_argument(
        '--start',
        type=int,
        default=1,
        help='Start IP (4th octet)'
    )
    parser.add_argument(
        '--end',
        type=int,
        default=254,
        help='End IP (4th octet)'
    )
    parser.add_argument(
        '--scan-tvs',
        action='store_true',
        help='Quick scan for TVs only (filters to known TV vendors)'
    )
    parser.add_argument(
        '--continuous',
        action='store_true',
        help='Run continuously every 5 minutes'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=5,
        help='Scan interval in minutes (for --continuous mode)'
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("TapCommand Network Scanner")
    logger.info("=" * 80)

    if args.continuous:
        await continuous_scan(args.subnet, args.interval)
    else:
        devices = await perform_scan(
            subnet=args.subnet,
            start=args.start,
            end=args.end,
            scan_tvs_only=args.scan_tvs
        )

        # Exit code based on results
        if devices:
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # No devices found


if __name__ == '__main__':
    asyncio.run(main())
