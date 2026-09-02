"""
src/paths.py - Project path constants.

All files should import path constants from here instead of
using hardcoded paths or calculating relative paths repeatedly.
"""

import os
import tempfile
from pathlib import Path
from uuid import uuid4

# Project root (parent of src/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Executables
BIN_DIR = PROJECT_ROOT / "bin"
VENV_PY = PROJECT_ROOT / ".venv" / "bin" / "python3"

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
LEAKS_DIR = DATA_DIR / "leaks"
INTERVENTIONS_DIR = DATA_DIR / "interventions"
REPORTS_DIR = PROJECT_ROOT / "reports"

# Config directory
CONFIG_DIR = PROJECT_ROOT / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

# Vendored third-party trees
THEHARVESTER_DIR = PROJECT_ROOT / "theHarvester"
THEHARVESTER_BIN = THEHARVESTER_DIR / "bin" / "theHarvester"

# Scratch space (SpiderFoot is cloned here at runtime, not shipped in the repo)
SCRATCH_DIR = Path(tempfile.gettempdir())
SPIDERFOOT_DIR = SCRATCH_DIR / "spiderfoot"
SPIDERFOOT_CLI = SPIDERFOOT_DIR / "sf.py"


def bin_path(name: str) -> Path:
    """Path to a bundled binary in bin/.

    Raises:
        FileNotFoundError: when the binary is not installed.
    """
    path = BIN_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Binary not found: {path}")
    return path


def scratch_file(name: str) -> Path:
    """Collision-free scratch path for `name`, unique per process and per call."""
    template = Path(name)
    return SCRATCH_DIR / f"{template.stem}_{os.getpid()}_{uuid4().hex[:8]}{template.suffix}"
