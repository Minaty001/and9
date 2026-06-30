"""
Phase 41 — Coverage Tracker.

Tracks code coverage per module, checks thresholds, and generates coverage
reports. Works with arbitrary line-level coverage data.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from .models import CoverageSnapshot

logger = logging.getLogger(__name__)


class CoverageTracker:
    """Tracks code coverage for modules.

    Usage:
        tracker = CoverageTracker(threshold=0.7)
        snapshot = tracker.track_coverage("my_module", 80, 100)
        pct = tracker.get_coverage("my_module")
        ok = tracker.check_threshold()
        report = tracker.generate_report()
    """

    def __init__(self, threshold: float = 0.7):
        self._threshold = threshold
        self._snapshots: Dict[str, CoverageSnapshot] = {}
        self._history: List[CoverageSnapshot] = []

    def track_coverage(
        self,
        module: str,
        lines_covered: int,
        total_lines: int,
        uncovered_lines: Optional[List[int]] = None,
    ) -> CoverageSnapshot:
        """Track coverage for a module.

        Args:
            module: Module name.
            lines_covered: Number of covered lines.
            total_lines: Total executable lines.
            uncovered_lines: Optional list of uncovered line numbers.

        Returns:
            CoverageSnapshot for this update.
        """
        coverage_percent = (lines_covered / total_lines * 100) if total_lines > 0 else 100.0

        snapshot = CoverageSnapshot(
            module=module,
            total_lines=total_lines,
            covered_lines=lines_covered,
            coverage_percent=round(coverage_percent, 2),
            uncovered_lines=uncovered_lines or [],
            timestamp=datetime.now(timezone.utc),
        )
        self._snapshots[module] = snapshot
        self._history.append(snapshot)
        logger.debug(
            "Coverage for %s: %.1f%% (%d/%d lines)",
            module, coverage_percent, lines_covered, total_lines,
        )
        return snapshot

    def get_coverage(self, module: str) -> float:
        """Get coverage percentage for a module.

        Args:
            module: Module name.

        Returns:
            Coverage fraction (0.0–1.0), or 0.0 if unknown.
        """
        snapshot = self._snapshots.get(module)
        if snapshot is None:
            return 0.0
        return snapshot.coverage_percent / 100.0

    def get_overall_coverage(self) -> float:
        """Calculate overall coverage across all tracked modules.

        Returns:
            Coverage fraction (0.0–1.0).
        """
        if not self._snapshots:
            return 0.0
        total_covered = sum(s.covered_lines for s in self._snapshots.values())
        total_lines = sum(s.total_lines for s in self._snapshots.values())
        if total_lines == 0:
            return 0.0
        return total_covered / total_lines

    def get_uncovered_lines(self, module: str) -> List[int]:
        """Get uncovered line numbers for a module.

        Args:
            module: Module name.

        Returns:
            List of uncovered line numbers, empty if unknown.
        """
        snapshot = self._snapshots.get(module)
        if snapshot is None:
            return []
        return list(snapshot.uncovered_lines)

    def check_threshold(self) -> bool:
        """Check if all tracked modules meet the coverage threshold.

        Returns:
            True if every module meets or exceeds the threshold.
        """
        if not self._snapshots:
            return True
        for module, snapshot in self._snapshots.items():
            pct = snapshot.coverage_percent / 100.0
            if pct < self._threshold:
                logger.warning(
                    "Coverage below threshold for %s: %.1f%% < %.0f%%",
                    module, pct * 100, self._threshold * 100,
                )
                return False
        return True

    def get_modules_below_threshold(self) -> List[str]:
        """Get list of modules that are below the coverage threshold."""
        below = []
        for module, snapshot in self._snapshots.items():
            pct = snapshot.coverage_percent / 100.0
            if pct < self._threshold:
                below.append(module)
        return below

    def generate_report(self) -> Dict[str, Any]:
        """Generate a coverage report dict.

        Returns:
            Dict with summary, per-module breakdown, and threshold status.
        """
        overall = self.get_overall_coverage()
        modules = {}
        for module, snap in self._snapshots.items():
            modules[module] = {
                "total_lines": snap.total_lines,
                "covered_lines": snap.covered_lines,
                "coverage_percent": snap.coverage_percent,
                "uncovered_lines": snap.uncovered_lines,
            }

        return {
            "overall_coverage_percent": round(overall * 100, 2),
            "overall_coverage_fraction": round(overall, 4),
            "threshold": self._threshold,
            "threshold_met": self.check_threshold(),
            "modules_below_threshold": self.get_modules_below_threshold(),
            "total_modules": len(self._snapshots),
            "modules": modules,
            "history_count": len(self._history),
        }

    def get_all_snapshots(self) -> Dict[str, CoverageSnapshot]:
        """Return all current coverage snapshots by module."""
        return dict(self._snapshots)

    def clear(self) -> None:
        """Clear all coverage data."""
        self._snapshots.clear()
        self._history.clear()
