#!/usr/bin/env python3
"""
Scheduled Network Scanner Service
Runs network scans every 10 minutes in the background
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List
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


async def perform_scheduled_scan(subnets: List[str] = None, start: int = 1, end: int = 254):
    """
    Perform a network scan and update the database

    Args:
        subnets: List of subnets to scan (e.g., ["192.168.101", "10.0.0"])
                 If None, uses configured/auto-detected subnets
        start: Starting host number (default: 1)
        end: Ending host number (default: 254)
    """
    global scan_in_progress, last_scan_time, last_scan_result

    if scan_in_progress:
        logger.warning("Scan already in progress, skipping...")
        return {"status": "skipped", "reason": "scan_in_progress"}

    scan_in_progress = True
    db = SessionLocal()

    try:
        start_time = datetime.now()

        if subnets:
            # Scan specific subnets
            logger.info(f"🔍 Starting scheduled network scan across {len(subnets)} subnets: {subnets}")
            devices = await network_sweep_service.scan_multiple_subnets(
                subnets=subnets,
                start=start,
                end=end,
                db_session=db
            )
            subnet_info = f"{len(subnets)} subnets: {', '.join(subnets)}"
        else:
            # Use configured/auto-detected subnets
            logger.info("🔍 Starting scheduled network scan (auto-configured subnets)")
            devices = await network_sweep_service.scan_enabled_subnets(db_session=db)
            subnet_info = "auto-configured"

        elapsed = (datetime.now() - start_time).total_seconds()

        result = {
            "status": "success",
            "scan_time": start_time.isoformat(),
            "duration_seconds": elapsed,
            "devices_found": len(devices),
            "subnets": subnet_info,
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


async def run_scheduled_scanner(interval_minutes: int = 10, subnets: List[str] = None):
    """
    Run network scanner on a schedule

    Args:
        interval_minutes: Minutes between scans (default: 10)
        subnets: List of subnets to scan. If None, uses auto-configured subnets.
    """
    logger.info(f"🔄 Starting scheduled network scanner (every {interval_minutes} minutes)")

    if subnets:
        logger.info(f"   Configured subnets: {', '.join(subnets)}")
    else:
        logger.info("   Using auto-configured subnets from database")

    logger.info(f"   Press Ctrl+C to stop")

    # Run initial scan immediately
    await perform_scheduled_scan(subnets=subnets)

    while True:
        try:
            await asyncio.sleep(interval_minutes * 60)
            await perform_scheduled_scan(subnets=subnets)

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
    parser.add_argument('--subnets', type=str, help='Comma-separated list of subnets to scan (e.g., "192.168.101,10.0.0"). If not provided, uses auto-configured subnets.')
    parser.add_argument('--subnet', type=str, help='DEPRECATED: Use --subnets instead. Single subnet for backward compatibility.')

    args = parser.parse_args()

    # Parse subnets
    subnets = None
    if args.subnets:
        subnets = [s.strip() for s in args.subnets.split(',')]
    elif args.subnet:
        # Backward compatibility
        logger.warning("--subnet is deprecated, use --subnets instead")
        subnets = [args.subnet]

    asyncio.run(run_scheduled_scanner(interval_minutes=args.interval, subnets=subnets))
