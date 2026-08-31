"""
src/paths.py - Project path constants.

All files should import path constants from here instead of
using hardcoded paths or calculating relative paths repeatedly.
"""

from pathlib import Path

# Project root (parent of src/)
PROJECT_ROOT = Path(__file__).parent.parent

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = DATA_DIR / "reports"
CACHE_DIR = DATA_DIR / "_cache"

# Config directory
CONFIG_DIR = PROJECT_ROOT / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
WHALE_REGISTRY_FILE = CONFIG_DIR / "whale_registry.json"

# Python scripts
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
COLLECTORS_DIR = PROJECT_ROOT / "collectors"
ANALYZERS_DIR = PROJECT_ROOT / "analyzers"
REPORTS_DIR_SCRIPTS = PROJECT_ROOT / "reports"

# Python venv
PYTHON_BIN = PROJECT_ROOT / "venv" / "bin" / "python"


# Convenience: data subdirectories
def data_subdir(name: str) -> Path:
    """Get path to a data subdirectory."""
    return DATA_DIR / name


def history_file(data_type: str, subdir: str | None = None) -> Path:
    """
    Get path to history file for a data type.
    
    Args:
        data_type: Type name e.g. "prices", "whales"
        subdir: Optional subdirectory within data/
        
    Returns:
        Path to *_history.json file
    """
    if subdir:
        return DATA_DIR / subdir / f"{data_type}_history.json"
    return DATA_DIR / f"{data_type}_history.json"


def latest_file(data_type: str, subdir: str | None = None) -> Path:
    """
    Get path to latest file for a data type.
    
    Args:
        data_type: Type name e.g. "prices", "whales"
        subdir: Optional subdirectory within data/
        
    Returns:
        Path to *_latest.json file
    """
    if subdir:
        return DATA_DIR / subdir / f"{data_type}_latest.json"
    return DATA_DIR / f"{data_type}_latest.json"
