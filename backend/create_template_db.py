#!/usr/bin/env python3
"""
Create a clean template database for deployment
This initializes the database with essential seed data but no site-specific data
"""

import os
import sys
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.database import Base, engine, create_tables, init_database, SessionLocal


def create_template_database():
    """Create a clean template database"""

    template_path = Path(__file__).parent / "smartvenue_template.db"

    # Remove existing template if it exists
    if template_path.exists():
        print(f"Removing existing template: {template_path}")
        template_path.unlink()

    # Temporarily change database location
    db_url = f"sqlite:///{template_path}"

    print("Creating database tables...")
    create_tables()

    print("Initializing with seed data...")
    init_database()

    print(f"✓ Template database created: {template_path}")
    print(f"  Size: {template_path.stat().st_size / 1024:.2f} KB")

    # Show what was created
    db = SessionLocal()
    try:
        # Import models to check what was created
        from app.models.user import User, Role
        from app.models.ir_code import IRCode

        user_count = db.query(User).count()
        role_count = db.query(Role).count()
        ir_count = db.query(IRCode).count()

        print(f"\nTemplate database contents:")
        print(f"  - Users: {user_count}")
        print(f"  - Roles: {role_count}")
        print(f"  - IR Codes: {ir_count}")

    finally:
        db.close()

    print("\n✓ Template database is ready for deployment")
    print(f"  Installers will copy this to smartvenue.db on first install")


if __name__ == "__main__":
    create_template_database()
