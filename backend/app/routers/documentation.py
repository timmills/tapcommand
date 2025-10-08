"""
Documentation API Router

Serves documentation files from the /docs directory
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import List
import os

router = APIRouter(prefix="/api/documentation", tags=["documentation"])

# Path to docs directory
DOCS_DIR = Path(__file__).parent.parent.parent / "docs"


@router.get("/list")
async def list_documentation_files() -> List[dict]:
    """
    List all markdown documentation files in the docs directory

    Returns:
        List of documentation files with metadata
    """
    if not DOCS_DIR.exists():
        return []

    docs = []

    # Walk through docs directory recursively
    for root, dirs, files in os.walk(DOCS_DIR):
        for file in files:
            if file.endswith('.md'):
                file_path = Path(root) / file
                relative_path = file_path.relative_to(DOCS_DIR)

                # Get file size
                file_size = file_path.stat().st_size

                # Get modified time
                modified_time = file_path.stat().st_mtime

                # Create a friendly title from filename
                title = file.replace('.md', '').replace('_', ' ').replace('-', ' ').title()

                # Determine category from subdirectory
                category = str(relative_path.parent) if str(relative_path.parent) != '.' else 'General'

                docs.append({
                    'filename': file,
                    'path': str(relative_path.as_posix()),
                    'title': title,
                    'category': category,
                    'size': file_size,
                    'modified': modified_time
                })

    # Sort by category, then title
    docs.sort(key=lambda x: (x['category'], x['title']))

    return docs


@router.get("/content/{file_path:path}")
async def get_documentation_content(file_path: str) -> dict:
    """
    Get the content of a specific documentation file

    Args:
        file_path: Relative path to the documentation file

    Returns:
        Documentation file content and metadata
    """
    # Security: Prevent directory traversal
    if '..' in file_path or file_path.startswith('/'):
        raise HTTPException(status_code=400, detail="Invalid file path")

    doc_file = DOCS_DIR / file_path

    # Check if file exists and is within docs directory
    if not doc_file.exists():
        raise HTTPException(status_code=404, detail="Documentation file not found")

    if not doc_file.is_relative_to(DOCS_DIR):
        raise HTTPException(status_code=400, detail="Invalid file path")

    # Read file content
    try:
        content = doc_file.read_text(encoding='utf-8')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

    # Get metadata
    file_size = doc_file.stat().st_size
    modified_time = doc_file.stat().st_mtime

    return {
        'filename': doc_file.name,
        'path': file_path,
        'content': content,
        'size': file_size,
        'modified': modified_time
    }
