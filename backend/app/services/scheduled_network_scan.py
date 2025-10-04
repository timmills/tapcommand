#!/usr/bin/env python3
"""
Scheduled Network Scanner Service
Runs network scans every 10 minutes in the background
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.database import SessionLocal
from app.services.network_sweep import network_sweep_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global state
scan_in_progress = False
last_scan_time = None
last_scan_result = None


async def perform_scheduled_scan(subnet: str = "192.168.101", start: int = 1, end: int = 254):
    """Perform a network scan and update the database"""
    global scan_in_progress, last_scan_time, last_scan_result

    if scan_in_progress:
        logger.warning("Scan already in progress, skipping...")
        return {"status": "skipped", "reason": "scan_in_progress"}

    scan_in_progress = True
    db = SessionLocal()

    try:
        logger.info(f"🔍 Starting scheduled network scan: {subnet}.{start}-{end}")
        start_time = datetime.now()

        devices = await network_sweep_service.scan_subnet(
            subnet=subnet,
            start=start,
            end=end,
            db_session=db
        )

        elapsed = (datetime.now() - start_time).total_seconds()

        result = {
            "status": "success",
            "scan_time": start_time.isoformat(),
            "duration_seconds": elapsed,
            "devices_found": len(devices),
            "subnet": subnet,
            "range": f"{start}-{end}"
        }

        last_scan_time = start_time
        last_scan_result = result

        logger.info(f"✅ Scheduled scan complete: {len(devices)} devices in {elapsed:.2f}s")

        return result

    except Exception as e:
        logger.error(f"❌ Scheduled scan failed: {e}", exc_info=True)
        result = {
            "status": "error",
            "error": str(e),
            "scan_time": datetime.now().isoformat()
        }
        last_scan_result = result
        return result

    finally:
        scan_in_progress = False
        db.close()


async def run_scheduled_scanner(interval_minutes: int = 10, subnet: str = "192.168.101"):
    """Run network scanner on a schedule"""
    logger.info(f"🔄 Starting scheduled network scanner (every {interval_minutes} minutes)")
    logger.info(f"   Subnet: {subnet}")
    logger.info(f"   Press Ctrl+C to stop")

    # Run initial scan immediately
    await perform_scheduled_scan(subnet=subnet)

    while True:
        try:
            await asyncio.sleep(interval_minutes * 60)
            await perform_scheduled_scan(subnet=subnet)

        except KeyboardInterrupt:
            logger.info("\n⏹️  Stopping scheduled scanner")
            break
        except Exception as e:
            logger.error(f"❌ Error in scheduled scanner: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retry


def get_scan_status():
    """Get current scan status"""
    return {
        "scan_in_progress": scan_in_progress,
        "last_scan_time": last_scan_time.isoformat() if last_scan_time else None,
        "last_scan_result": last_scan_result
    }


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Scheduled Network Scanner Service')
    parser.add_argument('--interval', type=int, default=10, help='Scan interval in minutes')
    parser.add_argument('--subnet', default='192.168.101', help='Subnet to scan')

    args = parser.parse_args()

    asyncio.run(run_scheduled_scanner(interval_minutes=args.interval, subnet=args.subnet))
