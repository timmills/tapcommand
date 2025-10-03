import asyncio
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import aiohttp
import logging

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.ir_codes import IRLibrary, IRCommand, IRImportLog
from ..db.database import get_db

logger = logging.getLogger(__name__)


class FlipperIRDBImporter:
    """Import IR codes from Flipper-IRDB GitHub repository"""

    BASE_URL = "https://api.github.com/repos/Lucaslhm/Flipper-IRDB/contents"
    RAW_URL = "https://raw.githubusercontent.com/Lucaslhm/Flipper-IRDB/main"
    DEFAULT_LOCAL_REPO = Path(__file__).resolve().parents[3] / "data" / "Flipper-IRDB"

    def __init__(self, db: Session, local_repo_path: Optional[Path] = None):
        self.db = db
        self.session = None
        self.local_repo_path = Path(local_repo_path) if local_repo_path else self.DEFAULT_LOCAL_REPO
        self.use_local_repo = self.local_repo_path.exists()

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def import_all_codes(self) -> IRImportLog:
        """Import all IR codes from Flipper-IRDB"""

        # Create import log
        import_log = IRImportLog(
            source="flipper-irdb",
            import_type="full",
            status="running",
            start_time=datetime.now(timezone.utc)
        )
        self.db.add(import_log)
        self.db.commit()

        try:
            logger.info("Starting Flipper-IRDB import")

            # Get all device categories
            categories = await self._get_device_categories()
            logger.info(f"Found {len(categories)} device categories")

            total_processed = 0
            total_imported = 0
            total_failed = 0

            for category in categories:
                logger.info(f"Processing category: {category}")

                # Get brands in this category
                brands = await self._get_brands_in_category(category)
                logger.info(f"Found {len(brands)} brands in {category}")

                for brand in brands:
                    logger.info(f"Processing brand: {category}/{brand}")

                    # Get IR files for this brand
                    ir_files = await self._get_ir_files_for_brand(category, brand)
                    logger.info(f"Found {len(ir_files)} IR files for {category}/{brand}")

                    for ir_file in ir_files:
                        total_processed += 1

                        try:
                            success = await self._import_ir_file(category, brand, ir_file)
                            if success:
                                total_imported += 1
                            else:
                                total_failed += 1

                        except Exception as e:
                            logger.error(f"Error importing {category}/{brand}/{ir_file}: {str(e)}")
                            total_failed += 1

                        # Commit periodically to avoid huge transactions
                        if total_processed % 50 == 0:
                            self.db.commit()
                            logger.info(f"Progress: {total_processed} processed, {total_imported} imported, {total_failed} failed")

            # Update import log
            import_log.status = "completed"
            import_log.end_time = datetime.now(timezone.utc)
            start_time = import_log.start_time
            if start_time and start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            end_time = import_log.end_time
            if end_time and end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)
            if start_time and end_time:
                import_log.duration_seconds = int((end_time - start_time).total_seconds())
            import_log.libraries_processed = total_processed
            import_log.libraries_imported = total_imported
            import_log.libraries_failed = total_failed

            # Count total commands imported
            command_count = self.db.query(func.count(IRCommand.id)).scalar()
            import_log.commands_imported = command_count

            self.db.commit()
            logger.info(f"Import completed: {total_imported}/{total_processed} libraries imported")

            return import_log

        except Exception as e:
            logger.error(f"Import failed: {str(e)}")
            import_log.status = "failed"
            import_log.error_message = str(e)
            import_log.end_time = datetime.now(timezone.utc)
            self.db.commit()
            raise

    async def import_brand(self, category: str, brand: str) -> IRImportLog:
        """Import IR codes for a specific category/brand"""

        import_log = IRImportLog(
            source="flipper-irdb",
            import_type="filtered",
            status="running",
            start_time=datetime.now(timezone.utc),
            import_details={
                "category": category,
                "brand": brand
            }
        )
        self.db.add(import_log)
        self.db.commit()

        try:
            logger.info(f"Starting filtered import for {category}/{brand}")

            ir_files = await self._get_ir_files_for_brand(category, brand)
            logger.info(f"Found {len(ir_files)} IR files for {category}/{brand}")

            total_processed = 0
            total_imported = 0
            total_failed = 0

            for ir_file in ir_files:
                total_processed += 1

                try:
                    if await self._import_ir_file(category, brand, ir_file):
                        total_imported += 1
                    else:
                        total_failed += 1
                except Exception as e:
                    logger.error(f"Error importing {category}/{brand}/{ir_file}: {str(e)}")
                    total_failed += 1

                if total_processed % 50 == 0:
                    self.db.commit()
                    logger.info(
                        f"Progress: {total_processed} processed, {total_imported} imported, {total_failed} failed"
                    )

            import_log.status = "completed"
            import_log.end_time = datetime.now(timezone.utc)
            start_time = import_log.start_time
            if start_time and start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            end_time = import_log.end_time
            if end_time and end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)
            if start_time and end_time:
                import_log.duration_seconds = int((end_time - start_time).total_seconds())
            import_log.libraries_processed = total_processed
            import_log.libraries_imported = total_imported
            import_log.libraries_failed = total_failed

            command_count = (
                self.db.query(func.count(IRCommand.id))
                .filter(IRCommand.library.has(brand=brand, device_category=category))
                .scalar()
            )
            import_log.commands_imported = command_count

            self.db.commit()
            logger.info(
                f"Filtered import completed: {total_imported}/{total_processed} libraries imported"
            )

            return import_log

        except Exception as e:
            logger.error(f"Filtered import failed: {str(e)}")
            import_log.status = "failed"
            import_log.error_message = str(e)
            import_log.end_time = datetime.now(timezone.utc)
            self.db.commit()
            raise

    async def _get_device_categories(self) -> List[str]:
        """Get all device categories (top-level directories)"""
        if self.use_local_repo:
            categories = [
                item.name
                for item in self.local_repo_path.iterdir()
                if item.is_dir() and not item.name.startswith('.')
            ]
            return categories

        async with self.session.get(self.BASE_URL) as response:
            if response.status != 200:
                raise Exception(f"Failed to fetch categories: {response.status}")

            data = await response.json()
            categories = [
                item['name'] for item in data
                if item['type'] == 'dir' and not item['name'].startswith('.')
            ]
            return categories

    async def _get_brands_in_category(self, category: str) -> List[str]:
        """Get all brands in a device category"""
        if self.use_local_repo:
            category_path = self.local_repo_path / category
            if not category_path.exists():
                logger.warning(f"Local category not found: {category}")
                return []

            return [
                item.name
                for item in category_path.iterdir()
                if item.is_dir()
            ]

        url = f"{self.BASE_URL}/{category}"
        async with self.session.get(url) as response:
            if response.status != 200:
                logger.warning(f"Failed to fetch brands for {category}: {response.status}")
                return []

            data = await response.json()
            brands = [
                item['name'] for item in data
                if item['type'] == 'dir'
            ]
            return brands

    async def _get_ir_files_for_brand(self, category: str, brand: str) -> List[str]:
        """Get all .ir files for a brand"""
        if self.use_local_repo:
            brand_path = self.local_repo_path / category / brand
            if not brand_path.exists():
                logger.warning(f"Local brand path not found: {category}/{brand}")
                return []

            return [
                item.name
                for item in brand_path.iterdir()
                if item.is_file() and item.name.endswith('.ir')
            ]

        url = f"{self.BASE_URL}/{category}/{brand}"
        async with self.session.get(url) as response:
            if response.status != 200:
                logger.warning(f"Failed to fetch IR files for {category}/{brand}: {response.status}")
                return []

            data = await response.json()
            ir_files = [
                item['name'] for item in data
                if item['type'] == 'file' and item['name'].endswith('.ir')
            ]
            return ir_files

    async def _import_ir_file(self, category: str, brand: str, filename: str) -> bool:
        """Import a single .ir file"""

        source_path = f"{category}/{brand}/{filename}"
        raw_url = f"{self.RAW_URL}/{source_path}"

        # Check if already imported by file hash
        existing = self.db.query(IRLibrary).filter_by(
            source="flipper-irdb",
            source_path=source_path
        ).first()

        # Download or read file content
        if self.use_local_repo:
            local_file = self.local_repo_path / category / brand / filename
            if not local_file.exists():
                logger.warning(f"Local file not found: {local_file}")
                return False

            content = local_file.read_text(encoding='utf-8')
        else:
            async with self.session.get(raw_url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to download {source_path}: {response.status}")
                    return False

                content = await response.text()

        # Calculate file hash
        file_hash = hashlib.md5(content.encode()).hexdigest()

        # Skip if already imported with same hash
        if existing and existing.file_hash == file_hash:
            logger.debug(f"Skipping {source_path} - already imported")
            return True

        # Parse IR file
        try:
            library_data, commands_data = self._parse_ir_file(content, category, brand, filename)
        except Exception as e:
            logger.error(f"Failed to parse {source_path}: {str(e)}")
            return False

        # Create or update library
        if existing:
            library = existing
            library.file_hash = file_hash
            library.last_updated = datetime.now(timezone.utc)
            library.import_status = "imported"

            # Delete existing commands to replace them
            self.db.query(IRCommand).filter_by(library_id=library.id).delete()
        else:
            library = IRLibrary(
                source="flipper-irdb",
                source_path=source_path,
                source_url=raw_url,
                file_hash=file_hash,
                last_updated=datetime.now(timezone.utc),
                import_status="imported",
                **library_data
            )
            self.db.add(library)
            self.db.flush()  # Get the ID

        # Add commands
        for cmd_data in commands_data:
            command = IRCommand(
                library_id=library.id,
                **cmd_data
            )
            self.db.add(command)

        logger.debug(f"Imported {source_path}: {len(commands_data)} commands")
        return True

    def _parse_ir_file(self, content: str, category: str, brand: str, filename: str) -> Tuple[Dict, List[Dict]]:
        """Parse .ir file content into library and commands data"""

        lines = content.strip().split('\n')

        # Extract metadata from header
        version = None
        comments = []

        i = 0
        while i < len(lines) and not lines[i].startswith('name:'):
            line = lines[i].strip()
            if line.startswith('Version:'):
                version = line.split(':', 1)[1].strip()
            elif line.startswith('#'):
                comments.append(line[1:].strip())
            i += 1

        # Extract model from filename
        model = filename.replace('.ir', '').replace(f'{brand}_', '', 1)

        # Library data
        library_data = {
            'device_category': category,
            'brand': brand,
            'model': model,
            'name': f"{brand} {model}",
            'description': ' | '.join(comments) if comments else None,
            'version': version
        }

        # Parse commands
        commands_data = []
        current_command = {}

        for line in lines[i:]:
            line = line.strip()
            if not line:
                continue

            if line.startswith('name:'):
                # Save previous command if exists
                if current_command:
                    commands_data.append(self._finalize_command(current_command))

                # Start new command
                current_command = {
                    'name': line.split(':', 1)[1].strip(),
                    'raw_data': {}
                }

            elif ':' in line and current_command:
                key, value = line.split(':', 1)
                current_command['raw_data'][key.strip()] = value.strip()

        # Add final command
        if current_command:
            commands_data.append(self._finalize_command(current_command))

        return library_data, commands_data

    def _finalize_command(self, command_data: Dict) -> Dict:
        """Convert raw command data to final format"""

        raw = command_data['raw_data']

        # Determine protocol and format signal data
        protocol = raw.get('protocol', 'unknown')
        signal_data = {}

        if protocol.lower().startswith('samsung'):
            signal_data = {
                'address': raw.get('address', ''),
                'command': raw.get('command', '')
            }
        elif protocol.lower() == 'nec':
            signal_data = {
                'address': raw.get('address', ''),
                'command': raw.get('command', '')
            }
        elif protocol.lower().startswith('sony'):
            signal_data = {
                'data': raw.get('command', ''),
                'nbits': 12  # Default for Sony
            }
        elif protocol.lower() == 'rc5':
            signal_data = {
                'address': raw.get('address', ''),
                'command': raw.get('command', '')
            }
        else:
            # Store raw data for unknown protocols
            signal_data = raw.copy()

        # Categorize command by name
        category = self._categorize_command(command_data['name'])

        return {
            'name': command_data['name'],
            'display_name': self._format_display_name(command_data['name']),
            'category': category,
            'protocol': protocol,
            'signal_data': signal_data
        }

    def _categorize_command(self, name: str) -> str:
        """Categorize command by name patterns"""
        name_lower = name.lower()

        if any(word in name_lower for word in ['power', 'on', 'off']):
            return 'power'
        elif any(word in name_lower for word in ['vol', 'volume']):
            return 'volume'
        elif any(word in name_lower for word in ['ch', 'channel']):
            return 'channel'
        elif any(word in name_lower for word in ['mute', 'silent']):
            return 'audio'
        elif name_lower.isdigit() or any(word in name_lower for word in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']):
            return 'number'
        elif any(word in name_lower for word in ['up', 'down', 'left', 'right', 'ok', 'enter', 'menu', 'back']):
            return 'navigation'
        elif any(word in name_lower for word in ['input', 'source', 'hdmi', 'usb', 'av']):
            return 'input'
        else:
            return 'other'

    def _format_display_name(self, name: str) -> str:
        """Format command name for display"""
        # Replace underscores with spaces and title case
        formatted = name.replace('_', ' ').title()

        # Special cases
        replacements = {
            'Vol Up': 'Volume Up',
            'Vol Down': 'Volume Down',
            'Ch Up': 'Channel Up',
            'Ch Down': 'Channel Down',
            'Tv': 'TV',
            'Hdmi': 'HDMI',
            'Usb': 'USB',
            'Av': 'AV'
        }

        for old, new in replacements.items():
            formatted = formatted.replace(old, new)

        return formatted


# Async service function
async def import_flipper_irdb(db: Session) -> IRImportLog:
    """Import all IR codes from Flipper-IRDB"""
    async with FlipperIRDBImporter(db) as importer:
        return await importer.import_all_codes()


# Sync wrapper for easier usage
def import_flipper_irdb_sync(db: Session) -> IRImportLog:
    """Synchronous wrapper for IR import"""
    return asyncio.run(import_flipper_irdb(db))


async def import_flipper_brand(db: Session, category: str, brand: str) -> IRImportLog:
    """Import IR codes for a specific category/brand"""
    async with FlipperIRDBImporter(db) as importer:
        return await importer.import_brand(category, brand)


def import_flipper_brand_sync(db: Session, category: str, brand: str) -> IRImportLog:
    """Synchronous wrapper for filtered import"""
    return asyncio.run(import_flipper_brand(db, category, brand))
