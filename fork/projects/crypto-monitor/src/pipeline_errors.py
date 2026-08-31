"""
src/pipeline_errors.py - Pipeline error collection and reporting.

Collectors and analyzers report errors here instead of crashing.
Errors are saved alongside the report for the day.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Literal

from src.paths import REPORTS_DIR
from src.file_utils import write_json_atomic


Severity = Literal["warning", "error", "critical"]


class PipelineErrorCollector:
    """
    Collects errors during pipeline execution.
    
    Usage:
        from src.pipeline_errors import error_collector
        
        # In each collector:
        error_collector.add_error("coin_prices", "API rate limited", "warning")
        
        # At end of pipeline:
        error_collector.save(date_str)
    """
    
    def __init__(self):
        self.errors: list[dict] = []
        self._enabled = True
    
    def add_error(
        self,
        collector: str,
        error: str,
        severity: Severity = "warning"
    ) -> None:
        """
        Record an error from a collector.
        
        Args:
            collector: Name of the collector/script that had the error
            error: Human-readable error description
            severity: How serious (warning, error, critical)
        """
        if not self._enabled:
            return
            
        self.errors.append({
            "collector": collector,
            "error": error,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
    
    def has_errors(self, min_severity: Severity = "warning") -> bool:
        """Check if any errors were recorded."""
        severity_order = {"warning": 0, "error": 1, "critical": 2}
        min_level = severity_order.get(min_severity, 0)
        return any(
            severity_order.get(e["severity"], 0) >= min_level
            for e in self.errors
        )
    
    def total_count(self) -> int:
        """Total number of errors recorded."""
        return len(self.errors)
    
    def count_by_severity(self) -> dict[str, int]:
        """Count errors by severity level."""
        counts = {"warning": 0, "error": 0, "critical": 0}
        for e in self.errors:
            if e["severity"] in counts:
                counts[e["severity"]] += 1
        return counts
    
    def save(self, report_date: str) -> Path:
        """
        Save errors to pipeline_errors_YYYY-MM-DD.json.
        
        Args:
            report_date: Date string in YYYY-MM-DD format
            
        Returns:
            Path to the saved errors file
        """
        filename = f"pipeline_errors_{report_date}.json"
        filepath = REPORTS_DIR / filename
        
        counts = self.count_by_severity()
        
        data = {
            "report_date": report_date,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "errors": self.errors,
            "warnings_count": counts["warning"],
            "errors_count": counts["error"],
            "critical_count": counts["critical"]
        }
        
        write_json_atomic(filepath, data)
        
        if self.errors:
            print(f"[PipelineErrors] Saved {len(self.errors)} errors to {filename}")
        
        return filepath
    
    def clear(self) -> None:
        """Clear all recorded errors."""
        self.errors = []
        self._enabled = True
    
    def disable(self) -> None:
        """Temporarily disable error collection."""
        self._enabled = False


# Global singleton instance
error_collector = PipelineErrorCollector()
