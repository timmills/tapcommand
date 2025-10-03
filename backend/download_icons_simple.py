#!/usr/bin/env python3
"""
Simple channel icon downloader - downloads what's available and skips failures
"""

import sqlite3
import requests
import os
import hashlib
from pathlib import Path
from urllib.parse import urlparse
import time


def safe_filename(url, channel_name):
    """Create a safe filename from URL and channel name"""
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    safe_name = "".join(c for c in channel_name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_name = safe_name.replace(' ', '_')[:30]
    return f"{safe_name}_{url_hash}"


def download_simple(url, output_path):
    """Simple download without image processing"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        response.raise_for_status()

        # Determine file extension from response
        content_type = response.headers.get('content-type', '').lower()
        if 'svg' in content_type:
            ext = '.svg'
        elif 'png' in content_type:
            ext = '.png'
        elif 'jpg' in content_type or 'jpeg' in content_type:
            ext = '.jpg'
        elif 'gif' in content_type:
            ext = '.gif'
        else:
            # Try to guess from URL
            parsed = urlparse(url)
            _, ext = os.path.splitext(parsed.path)
            if not ext:
                ext = '.png'  # Default

        # Update output path with correct extension
        output_path = output_path.with_suffix(ext)

        # Save the file
        with open(output_path, 'wb') as f:
            f.write(response.content)

        return True, output_path.name

    except Exception as e:
        print(f"    Error: {e}")
        return False, None


def main():
    """Download channel icons"""
    db_path = "smartvenue.db"
    icons_dir = Path("static/channel-icons")
    icons_dir.mkdir(parents=True, exist_ok=True)

    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get channels with URLs
    cursor.execute("""
        SELECT id, channel_name, logo_url
        FROM channels
        WHERE logo_url IS NOT NULL AND logo_url != ''
        ORDER BY channel_name
    """)
    channels = cursor.fetchall()

    print(f"Processing {len(channels)} channels with logo URLs...\n")

    successful = 0
    failed = 0

    for i, (channel_id, channel_name, logo_url) in enumerate(channels, 1):
        print(f"[{i}/{len(channels)}] {channel_name}")
        print(f"  URL: {logo_url}")

        # Create filename
        base_filename = safe_filename(logo_url, channel_name)
        output_path = icons_dir / base_filename

        # Check if we already have this file (any extension)
        existing_files = list(icons_dir.glob(f"{base_filename}.*"))
        if existing_files:
            existing_file = existing_files[0]
            print(f"  ✓ Already exists: {existing_file.name}")
            # Update database
            cursor.execute(
                "UPDATE channels SET local_logo_path = ? WHERE id = ?",
                (f"static/channel-icons/{existing_file.name}", channel_id)
            )
            successful += 1
            continue

        # Download
        success, filename = download_simple(logo_url, output_path)
        if success:
            print(f"  ✓ Downloaded: {filename}")
            # Update database
            cursor.execute(
                "UPDATE channels SET local_logo_path = ? WHERE id = ?",
                (f"static/channel-icons/{filename}", channel_id)
            )
            successful += 1
        else:
            print(f"  ✗ Failed")
            failed += 1

        # Small delay
        time.sleep(0.1)

        # Commit every 10 items
        if i % 10 == 0:
            conn.commit()

    # Final commit
    conn.commit()

    print(f"\n=== Summary ===")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total: {len(channels)}")

    # Show downloaded files
    downloaded_files = list(icons_dir.glob("*"))
    if downloaded_files:
        total_size = sum(f.stat().st_size for f in downloaded_files)
        print(f"Downloaded files: {len(downloaded_files)}")
        print(f"Total size: {total_size / 1024:.1f} KB")

    conn.close()
    return True


if __name__ == "__main__":
    main()