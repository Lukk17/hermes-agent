"""
src/file_utils.py - Safe file operations.

Provides atomic JSON writes and safe JSON reads to prevent corruption.
"""

import json
import os
from pathlib import Path


def write_json_atomic(path: Path, data: dict | list) -> None:
    """
    Write JSON data atomically to prevent corruption.
    
    Writes to a temporary file first, then renames to target.
    This ensures the file is never partially written.
    
    Args:
        path: Target file path
        data: Data to write (dict or list)
        
    Example:
        from src.file_utils import write_json_atomic
        write_json_atomic(Path("data/test.json"), {"key": "value"})
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2))
    # os.replace overwrites an existing target on every platform.
    # Path.rename raises FileExistsError on Windows, which broke a same-day rerun.
    os.replace(temp, path)


def load_json_safe(path: Path) -> dict | list | None:
    """
    Load JSON file safely without crashing.
    
    Args:
        path: Path to JSON file
        
    Returns:
        dict or list if file exists and is valid JSON
        None if file missing or invalid JSON
        
    Example:
        from src.file_utils import load_json_safe
        data = load_json_safe(Path("data/test.json"))
        if data is None:
            print("File missing or invalid")
    """
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def load_json_or_raise(path: Path) -> dict | list:
    """
    Load JSON file, raising an exception if missing or invalid.
    
    Args:
        path: Path to JSON file
        
    Returns:
        dict or list if file exists and is valid JSON
        
    Raises:
        FileNotFoundError: If file does not exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return json.loads(path.read_text())
