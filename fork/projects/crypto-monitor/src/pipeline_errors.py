"""
src/pipeline_errors.py - Pipeline error collection and reporting.

Collectors and analyzers report errors here instead of crashing. They run as
subprocesses, so every process flushes its own errors to a sidecar file when it
exits and the pipeline parent merges those sidecars into one report for the day.
"""

import atexit
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal

from src.file_utils import write_json_atomic
from src.paths import REPORTS_DIR

Severity = Literal["warning", "error", "critical"]

SIDECAR_DIR = REPORTS_DIR / ".pipeline_errors"


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
        self._persisted = False

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
        self._persisted = False

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
        Merge every sidecar written during this run, then save the day's report.

        Args:
            report_date: Date string in YYYY-MM-DD format

        Returns:
            Path to the saved errors file
        """
        self.errors.extend(self._drain_sidecars())
        self.errors.sort(key=lambda entry: entry["timestamp"])

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
        self._persisted = True

        if self.errors:
            print(f"[PipelineErrors] Saved {len(self.errors)} errors to {filename}")

        return filepath

    def flush_to_sidecar(self) -> Path | None:
        """
        Persist this process's errors so they survive its exit.

        Returns:
            Path to the sidecar, or None when there is nothing to persist
        """
        if self._persisted or not self.errors:
            return None

        sidecar = SIDECAR_DIR / f"{os.getpid()}-{uuid.uuid4().hex[:8]}.json"
        write_json_atomic(sidecar, {"pid": os.getpid(), "errors": self.errors})
        self._persisted = True

        return sidecar

    def clear(self) -> None:
        """Start-of-run reset. Drops sidecars left behind by a previous run."""
        self.errors = []
        self._enabled = True
        self._persisted = False
        self._purge_sidecars()

    def disable(self) -> None:
        """Temporarily disable error collection."""
        self._enabled = False

    def _drain_sidecars(self) -> list[dict]:
        collected: list[dict] = []
        for sidecar in sorted(SIDECAR_DIR.glob("*.json")):
            try:
                payload = json.loads(sidecar.read_text(encoding="utf-8"))
                collected.extend(payload.get("errors") or [])
            except (OSError, ValueError) as e:
                collected.append({
                    "collector": sidecar.name,
                    "error": f"unreadable error sidecar: {e}",
                    "severity": "warning",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })
            sidecar.unlink(missing_ok=True)

        return collected

    def _purge_sidecars(self) -> None:
        for sidecar in SIDECAR_DIR.glob("*.json"):
            sidecar.unlink(missing_ok=True)


# Global singleton instance
error_collector = PipelineErrorCollector()

# Collectors are subprocesses: without this their errors would die with them.
atexit.register(error_collector.flush_to_sidecar)
