"""Database seeding helpers.

Device type/brand data has moved to imported IR libraries, but we keep
this module to ensure default ESPHome templates are present.
"""

from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session

from ..models.ir_codes import ESPTemplate, IRLibrary


TEMPLATE_PATH = Path(__file__).resolve().parents[3] / "esphome" / "templates" / "d1_mini_base.yaml"


def _ensure_default_template(db: Session) -> None:
    existing = db.query(ESPTemplate).filter(ESPTemplate.name == "D1 Mini Base").first()
    try:
        content = TEMPLATE_PATH.read_text()
    except FileNotFoundError:
        print(f"Default template not found at {TEMPLATE_PATH}; skipping seed.")
        return

    if existing:
        return

    template = ESPTemplate(
        name="D1 Mini Base",
        board="d1_mini",
        description="Base ESPHome profile for D1 Mini with YAML builder metadata.",
        template_yaml=content,
    )
    db.add(template)
    db.commit()
    print("Seeded default D1 Mini ESPHome template.")


# ESP native libraries removed - using dynamic template generation instead


def seed_database(db: Session):
    """Seed default ESPHome templates and report legacy status."""

    _ensure_default_template(db)
    # ESP native libraries removed - using dynamic template generation instead
    print("Template seeding complete; using dynamic IR library system.")
