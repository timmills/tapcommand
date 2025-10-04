"""
Clean up duplicate LCN entries - keep only HD versions when both SD and HD exist
"""

import sys
import os

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.models.device import Channel

def cleanup_duplicate_lcns():
    """Remove SD LCN entries when HD versions exist for the same channel"""
    db = SessionLocal()

    try:
        # Get all channels grouped by name
        channels = db.query(Channel).all()

        # Group channels by name
        channel_groups = {}
        for ch in channels:
            if ch.channel_name not in channel_groups:
                channel_groups[ch.channel_name] = []
            channel_groups[ch.channel_name].append(ch)

        deleted_count = 0
        updated_count = 0

        # Process each group
        for name, group in channel_groups.items():
            # Find channels with both SD and HD LCNs in same record
            for ch in group:
                if ch.lcn and '/' in ch.lcn and 'HD' in ch.lcn:
                    # Parse the LCN string like "5 / 50 HD" or "6 / 60 HD"
                    parts = ch.lcn.split('/')
                    if len(parts) == 2:
                        sd_lcn = parts[0].strip()
                        hd_part = parts[1].strip()

                        # Extract HD LCN number (remove "HD" suffix)
                        hd_lcn = hd_part.replace('HD', '').strip()

                        # Update to only keep HD LCN
                        old_lcn = ch.lcn
                        ch.lcn = hd_lcn
                        updated_count += 1
                        print(f"Updated '{name}': '{old_lcn}' -> '{hd_lcn}'")

        db.commit()

        print(f"\nCleanup complete:")
        print(f"  Updated: {updated_count} channel LCNs")

    except Exception as e:
        print(f"Error during cleanup: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting LCN cleanup...")
    cleanup_duplicate_lcns()
    print("\nDone!")
