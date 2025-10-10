"""
Database content reporting service.

Generates snapshots of database contents for backup metadata.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class DatabaseReportService:
    """Service for generating database content reports."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def generate_report(self) -> Dict:
        """
        Generate a comprehensive report of database contents.

        Returns:
            Dictionary with table counts and summary statistics
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            report = {
                "generated_at": datetime.now().isoformat(),
                "database_path": str(self.db_path),
                "tables": {},
                "summary": {}
            }

            # Get list of all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]

            # Get row counts for each table
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    report["tables"][table] = count
                except Exception as e:
                    logger.warning(f"Could not count rows in table {table}: {e}")
                    report["tables"][table] = None

            # Generate summary statistics for key entities
            report["summary"] = self._generate_summary(cursor)

            conn.close()

            return report

        except Exception as e:
            logger.error(f"Error generating database report: {e}")
            return {
                "generated_at": datetime.now().isoformat(),
                "error": str(e),
                "tables": {},
                "summary": {}
            }

    def _generate_summary(self, cursor: sqlite3.Cursor) -> Dict:
        """
        Generate summary statistics for key entities.

        Args:
            cursor: SQLite cursor

        Returns:
            Dictionary with summary statistics
        """
        summary = {}

        # Get key statistics
        try:
            # Device statistics
            cursor.execute("SELECT COUNT(*) FROM devices")
            summary["total_devices"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT device_type) FROM devices")
            summary["device_types_count"] = cursor.fetchone()[0]

            # User statistics
            cursor.execute("SELECT COUNT(*) FROM users")
            summary["total_users"] = cursor.fetchone()[0]

            # Schedule statistics
            cursor.execute("SELECT COUNT(*) FROM schedules")
            summary["total_schedules"] = cursor.fetchone()[0]

            # Channel statistics
            cursor.execute("SELECT COUNT(*) FROM channels")
            summary["total_channels"] = cursor.fetchone()[0]

            # IR statistics
            cursor.execute("SELECT COUNT(*) FROM ir_commands")
            summary["total_ir_commands"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM captured_remotes")
            summary["total_captured_remotes"] = cursor.fetchone()[0]

            # Command history
            cursor.execute("SELECT COUNT(*) FROM command_history")
            summary["total_command_history"] = cursor.fetchone()[0]

            # Recent activity (commands in last 24 hours)
            cursor.execute("""
                SELECT COUNT(*) FROM command_history
                WHERE created_at >= datetime('now', '-1 day')
            """)
            summary["commands_last_24h"] = cursor.fetchone()[0]

            # Audit log entries
            cursor.execute("SELECT COUNT(*) FROM audit_log")
            summary["total_audit_entries"] = cursor.fetchone()[0]

        except Exception as e:
            logger.warning(f"Error generating summary statistics: {e}")

        return summary

    def save_report(self, report: Dict, output_path: Path) -> bool:
        """
        Save report to JSON file.

        Args:
            report: Report dictionary
            output_path: Path to save JSON file

        Returns:
            True if successful
        """
        try:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving report: {e}")
            return False

    def load_report(self, report_path: Path) -> Optional[Dict]:
        """
        Load report from JSON file.

        Args:
            report_path: Path to JSON report file

        Returns:
            Report dictionary or None if not found
        """
        try:
            if not report_path.exists():
                return None

            with open(report_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading report: {e}")
            return None

    def generate_human_readable_summary(self, report: Dict) -> str:
        """
        Generate a human-readable summary from report.

        Args:
            report: Report dictionary

        Returns:
            Human-readable summary string
        """
        if not report or "summary" not in report:
            return "No report data available"

        summary = report["summary"]
        parts = []

        if summary.get("total_devices"):
            parts.append(f"{summary['total_devices']} devices")

        if summary.get("total_users"):
            parts.append(f"{summary['total_users']} users")

        if summary.get("total_schedules"):
            parts.append(f"{summary['total_schedules']} schedules")

        if summary.get("total_channels"):
            parts.append(f"{summary['total_channels']} channels")

        if summary.get("total_ir_commands"):
            parts.append(f"{summary['total_ir_commands']} IR commands")

        if summary.get("total_captured_remotes"):
            parts.append(f"{summary['total_captured_remotes']} remotes")

        if not parts:
            return "Empty database"

        return ", ".join(parts)
