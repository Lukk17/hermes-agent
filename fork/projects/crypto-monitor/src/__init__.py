"""
src/__init__.py - src package for crypto-monitor.

Imports commonly used functions for convenience.
"""

from src.config import load_config
from src.exceptions import APIKeyMissingError, DataCollectionError
from src.file_utils import write_json_atomic, load_json_safe
from src.paths import (
    PROJECT_ROOT,
    DATA_DIR,
    REPORTS_DIR,
    CACHE_DIR,
    CONFIG_DIR,
    PYTHON_BIN,
)
from src.pipeline_errors import error_collector, PipelineErrorCollector
from src.types import CoinData, BTCWhaleData, ETHWhaleData

__all__ = [
    # config
    "load_config",
    # exceptions
    "APIKeyMissingError",
    "DataCollectionError",
    # file utils
    "write_json_atomic",
    "load_json_safe",
    # paths
    "PROJECT_ROOT",
    "DATA_DIR",
    "REPORTS_DIR",
    "CACHE_DIR",
    "CONFIG_DIR",
    "PYTHON_BIN",
    # pipeline errors
    "error_collector",
    "PipelineErrorCollector",
    # types
    "CoinData",
    "BTCWhaleData",
    "ETHWhaleData",
]
