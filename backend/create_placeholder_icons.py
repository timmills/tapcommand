#!/usr/bin/env python3
"""
Create placeholder icons for channels where URLs are not accessible
"""

import sqlite3
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib


def create_placeholder_icon(text, size=(64, 64), bg_color=(70, 130, 180), text_color=(255, 255, 255)):
    """Create a placeholder icon with channel initials"""
    # Create image
    img = Image.new('RGB', size, bg_color)
    draw = ImageDraw.Draw(img)

    # Get initials (first letter of each word, max 3)
    words = text.upper().split()
    initials = ''.join(word[0] for word in words if word.isalpha())[:3]

    if not initials:
        initials = text[:3].upper()

    # Try to use a system font, fallback to default
    font_size = size[0] // 4
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        try:
            font = ImageFont.load_default()
        except:
            font = None

    # Calculate text position (center)
    if font:
        bbox = draw.textbbox((0, 0), initials, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    else:
        text_width = len(initials) * 8
        text_height = 16

    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2

    # Draw text
    draw.text((x, y), initials, fill=text_color, font=font)

    return img


def generate_color_from_text(text):
    """Generate a consistent color from text"""
    hash_obj = hashlib.md5(text.encode())
    hash_hex = hash_obj.hexdigest()

    # Use first 6 characters for RGB
    r = int(hash_hex[0:2], 16)
    g = int(hash_hex[2:4], 16)
    b = int(hash_hex[4:6], 16)

    # Ensure colors are not too dark or light
    r = max(50, min(200, r))
    g = max(50, min(200, g))
    b = max(50, min(200, b))

    return (r, g, b)


def main():
    """Create placeholder icons for all channels"""
    db_path = "tapcommand.db"
    icons_dir = Path("static/channel-icons")
    icons_dir.mkdir(parents=True, exist_ok=True)

    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all channels
    cursor.execute("""
        SELECT id, channel_name, logo_url, broadcaster_network
        FROM channels
        ORDER BY channel_name
    """)
    channels = cursor.fetchall()

    print(f"Creating placeholder icons for {len(channels)} channels...\n")

    created = 0

    for channel_id, channel_name, logo_url, broadcaster in channels:
        # Create safe filename
        safe_name = "".join(c for c in channel_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')[:30]
        filename = f"{safe_name}_placeholder.png"
        output_path = icons_dir / filename

        # Skip if already exists
        if output_path.exists():
            print(f"✓ {channel_name} - already exists")
            # Update database
            cursor.execute(
                "UPDATE channels SET local_logo_path = ? WHERE id = ?",
                (f"static/channel-icons/{filename}", channel_id)
            )
            continue

        # Generate color based on broadcaster/channel
        color_text = broadcaster if broadcaster else channel_name
        bg_color = generate_color_from_text(color_text)

        # Create placeholder icon
        icon = create_placeholder_icon(channel_name, bg_color=bg_color)
        icon.save(output_path, 'PNG')

        print(f"✓ {channel_name} - created placeholder")

        # Update database
        cursor.execute(
            "UPDATE channels SET local_logo_path = ? WHERE id = ?",
            (f"static/channel-icons/{filename}", channel_id)
        )

        created += 1

    conn.commit()

    print(f"\n=== Summary ===")
    print(f"Placeholder icons created: {created}")
    print(f"Total channels: {len(channels)}")

    # Show file statistics
    icon_files = list(icons_dir.glob("*.png"))
    if icon_files:
        total_size = sum(f.stat().st_size for f in icon_files)
        print(f"Total icon files: {len(icon_files)}")
        print(f"Total size: {total_size / 1024:.1f} KB")

    conn.close()
    return True


if __name__ == "__main__":
    main()