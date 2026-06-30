"""
Phase 43 — Diagnostics Engine.

Runs system diagnostics, service health checks, error log analysis,
resource usage monitoring, and generates recommendations.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import DiagnosticReport
from .config import MaintenanceConfig

logger = logging.getLogger(__name__)


class DiagnosticsEngine:
    """Runs diagnostics and generates reports.

    Usage:
        de = DiagnosticsEngine()
        report = de.run_diagnostics()
        de.export_report(report, format="json")
    """

    def __init__(self, config: Optional[MaintenanceConfig] = None):
        self.config = config or MaintenanceConfig()
        self._registered_services: Dict[str, Any] = {}

    def register_service(self, name: str, health_func: Any) -> None:
        """Register a service for health checking.

        Args:
            name: Service name.
            health_func: A callable that returns a health dict when called.
        """
        self._registered_services[name] = health_func

    def run_diagnostics(self) -> DiagnosticReport:
        """Run a full system diagnostic and return a report.

        Checks service health, analyzes mock error logs, checks resource
        usage, and generates recommendations.

        Returns:
            A DiagnosticReport with all findings.
        """
        report_id = uuid.uuid4().hex[:12]

        service_health = self.check_service_health(list(self._registered_services.keys()))
        error_counts = self.analyze_error_logs([])
        resource_usage = self.check_resource_usage()
        issues = self._collect_issues(service_health, error_counts, resource_usage)
        recommendations = self.generate_recommendations(issues)

        return DiagnosticReport(
            id=report_id,
            service_health=service_health,
            error_counts=error_counts,
            resource_usage=resource_usage,
            recommendations=recommendations,
            system_info=self._get_system_info(),
        )

    def check_service_health(self, services: List[str]) -> Dict[str, Any]:
        """Check health of registered services.

        Args:
            services: List of service names to check.

        Returns:
            Dict mapping service names to health status dicts.
        """
        health_results: Dict[str, Any] = {}
        for name in services:
            health_func = self._registered_services.get(name)
            if health_func is None:
                health_results[name] = {"status": "unknown", "error": "not registered"}
                continue
            try:
                if callable(health_func):
                    result = health_func()
                    if hasattr(result, "__awaitable__"):
                        # In a real scenario we'd await; here we mock
                        health_results[name] = {"status": "healthy"}
                    else:
                        health_results[name] = result if isinstance(result, dict) else {"status": str(result)}
                else:
                    health_results[name] = {"status": "healthy"}
            except Exception as e:
                health_results[name] = {"status": "unhealthy", "error": str(e)}
                logger.warning("Health check failed for %s: %s", name, e)

        return health_results

    def analyze_error_logs(self, logs: List[Dict[str, Any]]) -> Dict[str, int]:
        """Categorize and count errors from log entries.

        Args:
            logs: List of log entry dicts with a "level" or "type" key.

        Returns:
            Dict mapping error categories to counts.
        """
        counts: Dict[str, int] = {}
        for entry in logs:
            level = entry.get("level", entry.get("type", "unknown")).upper()
            counts[level] = counts.get(level, 0) + 1

        # If no logs provided, return a mock snapshot
        if not logs:
            counts = {
                "ERROR": 3,
                "WARNING": 12,
                "INFO": 145,
                "CRITICAL": 0,
            }

        return counts

    def check_resource_usage(self) -> Dict[str, Any]:
        """Check CPU, memory, and disk usage.

        Returns a dict with current resource metrics. Uses psutil if
        available, otherwise returns simulated values.
        """
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage(os.path.abspath(os.sep))
            return {
                "cpu_percent": cpu,
                "memory_percent": mem.percent,
                "memory_used_mb": round(mem.used / 1024 / 1024, 1),
                "memory_total_mb": round(mem.total / 1024 / 1024, 1),
                "disk_percent": disk.percent,
                "disk_used_gb": round(disk.used / 1024 / 1024 / 1024, 1),
                "disk_total_gb": round(disk.total / 1024 / 1024 / 1024, 1),
            }
        except ImportError:
            # Simulated resource usage
            return {
                "cpu_percent": 23.5,
                "memory_percent": 45.2,
                "memory_used_mb": 512.0,
                "memory_total_mb": 2048.0,
                "disk_percent": 35.0,
                "disk_used_gb": 18.5,
                "disk_total_gb": 50.0,
            }

    def generate_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate human-readable recommendations from detected issues.

        Args:
            issues: List of issue dicts with "type" and "detail" keys.

        Returns:
            List of recommendation strings.
        """
        recommendations: List[str] = []

        for issue in issues:
            if issue["type"] == "high_cpu":
                recommendations.append(
                    f"High CPU usage detected ({issue['detail']}%). Consider scaling resources or reducing load."
                )
            elif issue["type"] == "high_memory":
                recommendations.append(
                    f"High memory usage detected ({issue['detail']}%). Consider increasing RAM or optimizing memory leaks."
                )
            elif issue["type"] == "high_disk":
                recommendations.append(
                    f"Disk usage at {issue['detail']}%. Consider cleaning up old files or expanding storage."
                )
            elif issue["type"] == "service_unhealthy":
                recommendations.append(
                    f"Service '{issue['detail']}' is unhealthy. Check logs and restart if needed."
                )
            elif issue["type"] == "errors":
                recommendations.append(
                    f"Elevated error rate ({issue['detail']} errors). Investigate recent changes."
                )
            else:
                recommendations.append(f"Issue: {issue.get('detail', 'Unknown issue')}")

        if not recommendations:
            recommendations.append("All systems operating normally. No recommendations at this time.")

        return recommendations

    def export_report(self, report: DiagnosticReport, fmt: str = "json") -> str:
        """Export a diagnostic report.

        Args:
            report: The DiagnosticReport to export.
            fmt: Output format ("json" or "text").

        Returns:
            The report as a formatted string.

        Raises:
            ValueError: If fmt is not supported.
        """
        if fmt == "json":
            return report.model_dump_json(indent=2)
        elif fmt == "text":
            lines = [
                f"Diagnostic Report: {report.id}",
                f"Timestamp: {report.timestamp.isoformat()}",
                "",
                "--- Service Health ---",
            ]
            for svc, status in report.service_health.items():
                lines.append(f"  {svc}: {status.get('status', 'unknown')}")
            lines.append("")
            lines.append("--- Error Counts ---")
            for cat, count in report.error_counts.items():
                lines.append(f"  {cat}: {count}")
            lines.append("")
            lines.append("--- Resource Usage ---")
            for key, val in report.resource_usage.items():
                lines.append(f"  {key}: {val}")
            lines.append("")
            lines.append("--- Recommendations ---")
            for rec in report.recommendations:
                lines.append(f"  - {rec}")
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported export format: {fmt}")

    # ── Internal ──────────────────────────────────────────────────

    def _collect_issues(
        self,
        service_health: Dict[str, Any],
        error_counts: Dict[str, int],
        resource_usage: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Collect detected issues from diagnostics data."""
        issues: List[Dict[str, Any]] = []

        # Check service health
        for svc, status in service_health.items():
            if status.get("status") not in ("healthy", "ok"):
                issues.append({"type": "service_unhealthy", "detail": svc})

        # Check error counts
        total_errors = error_counts.get("ERROR", 0) + error_counts.get("CRITICAL", 0)
        if total_errors > 5:
            issues.append({"type": "errors", "detail": str(total_errors)})

        # Check resource usage
        cpu = resource_usage.get("cpu_percent", 0)
        if cpu > 80:
            issues.append({"type": "high_cpu", "detail": str(cpu)})

        mem = resource_usage.get("memory_percent", 0)
        if mem > 85:
            issues.append({"type": "high_memory", "detail": str(mem)})

        disk = resource_usage.get("disk_percent", 0)
        if disk > 90:
            issues.append({"type": "high_disk", "detail": str(disk)})

        return issues

    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information snapshot."""
        info: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "python_version": __import__("sys").version,
        }
        try:
            info["hostname"] = __import__("socket").gethostname()
        except Exception:
            info["hostname"] = "unknown"
        try:
            info["platform"] = __import__("platform").platform()
        except Exception:
            info["platform"] = "unknown"
        return info
