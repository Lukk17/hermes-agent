"""
src/config.py - ONE standardized config loader.

All files should import load_config from here instead of having their own.
"""

from pathlib import Path
import json

CONFIG_FILE = Path(__file__).parent.parent / "config" / "settings.json"

_config_cache: dict | None = None


def load_config() -> dict:
    """
    Load and cache config from settings.json.
    
    Returns:
        dict: Configuration dictionary from settings.json
        
    Example:
        from src.config import load_config
        config = load_config()
        api_endpoints = config.get("api_endpoints", {})
    """
    global _config_cache
    if _config_cache is None:
        if CONFIG_FILE.exists():
            _config_cache = json.loads(CONFIG_FILE.read_text())
        else:
            _config_cache = {}
    return _config_cache


def reload_config() -> dict:
    """Force reload config from disk."""
    global _config_cache
    _config_cache = None
    return load_config()
