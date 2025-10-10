#!/usr/bin/env python3
"""
Download channel icons from URLs and resize them to consistent sizes
"""

import sqlite3
import requests
import os
import hashlib
from pathlib import Path
from urllib.parse import urlparse
from PIL import Image, ImageOps
import io
import time


def safe_filename(url, channel_name):
    """Create a safe filename from URL and channel name"""
    # Use URL hash to avoid issues with long URLs and special characters
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    # Clean channel name for filename
    safe_name = "".join(c for c in channel_name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_name = safe_name.replace(' ', '_')[:30]  # Limit length
    return f"{safe_name}_{url_hash}"


def download_and_process_image(url, output_path, target_size=(64, 64)):
    """Download image from URL and process it to consistent size"""
    try:
        # Download image with timeout and user agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15, stream=True, allow_redirects=True)
        response.raise_for_status()

        # Load image
        image_data = response.content
        image = Image.open(io.BytesIO(image_data))

        # Convert to RGBA if not already (to handle transparency)
        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        # Create a white background for SVGs and transparent images
        background = Image.new('RGBA', image.size, (255, 255, 255, 255))
        image = Image.alpha_composite(background, image)

        # Convert to RGB (remove alpha channel)
        image = image.convert('RGB')

        # Resize maintaining aspect ratio and center crop if needed
        image = ImageOps.fit(image, target_size, Image.Resampling.LANCZOS)

        # Save as PNG
        image.save(output_path, 'PNG', optimize=True)
        return True

    except Exception as e:
        print(f"Error processing {url}: {e}")
        return False


def download_channel_icons():
    """Download all channel icons from the database"""
    # Database and output paths
    db_path = "tapcommand.db"
    icons_dir = Path("static/channel-icons")
    icons_dir.mkdir(parents=True, exist_ok=True)

    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return False

    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all channels with logo URLs
        cursor.execute("""
            SELECT id, channel_name, logo_url
            FROM channels
            WHERE logo_url IS NOT NULL AND logo_url != ''
        """)
        channels = cursor.fetchall()

        print(f"Found {len(channels)} channels with logo URLs")
        print("Starting download and processing...")

        successful_downloads = 0
        failed_downloads = 0

        for channel_id, channel_name, logo_url in channels:
            print(f"\nProcessing: {channel_name}")
            print(f"URL: {logo_url}")

            # Create safe filename
            base_filename = safe_filename(logo_url, channel_name)
            output_path = icons_dir / f"{base_filename}.png"

            # Skip if file already exists
            if output_path.exists():
                print(f"  ✓ Already exists: {output_path}")
                # Update database with local path
                cursor.execute(
                    "UPDATE channels SET local_logo_path = ? WHERE id = ?",
                    (f"static/channel-icons/{output_path.name}", channel_id)
                )
                successful_downloads += 1
                continue

            # Download and process image
            if download_and_process_image(logo_url, output_path):
                print(f"  ✓ Downloaded: {output_path}")
                # Update database with local path
                cursor.execute(
                    "UPDATE channels SET local_logo_path = ? WHERE id = ?",
                    (f"static/channel-icons/{output_path.name}", channel_id)
                )
                successful_downloads += 1
            else:
                print(f"  ✗ Failed: {channel_name}")
                failed_downloads += 1

            # Small delay to be respectful to servers
            time.sleep(0.1)

        # Commit database changes
        conn.commit()

        print(f"\n=== Download Summary ===")
        print(f"Successful downloads: {successful_downloads}")
        print(f"Failed downloads: {failed_downloads}")
        print(f"Total channels: {len(channels)}")

        # Show some file statistics
        icon_files = list(icons_dir.glob("*.png"))
        if icon_files:
            total_size = sum(f.stat().st_size for f in icon_files)
            print(f"Total icon files: {len(icon_files)}")
            print(f"Total size: {total_size / 1024 / 1024:.1f} MB")

        conn.close()
        return True

    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    print("Starting channel icon download...")

    # Check if PIL is available
    try:
        from PIL import Image, ImageOps
    except ImportError:
        print("Error: Pillow (PIL) is not installed.")
        print("Please install it with: pip install Pillow")
        exit(1)

    success = download_channel_icons()

    if success:
        print("\n✅ Channel icon download completed!")
        print("All icons have been resized to 64x64 pixels and saved as PNG files.")
    else:
        print("\n❌ Channel icon download failed!")
        exit(1)