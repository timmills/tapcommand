#!/usr/bin/env python3
"""
Create network discovery tables
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from app.db.database import create_tables

if __name__ == "__main__":
    print("Creating network discovery tables...")
    create_tables()
    print("✅ Tables created successfully")
