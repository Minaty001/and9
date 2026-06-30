"""
Phase 31 — Audit Logger.

Structured security audit event logging with query and export capabilities.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from .config import SecurityConfig
from .models import SecurityEvent

logger = logging.getLogger(__name__)


class AuditLogger:
    """Structured audit event logger with query and export.

    Usage:
        audit = AuditLogger(config)
        event = SecurityEvent(event_type="auth", severity="medium", ...)
        audit.log_event(event)
        recent = audit.get_recent_events(limit=10)
    """

    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
        self._events: List[SecurityEvent] = []

    def log_event(self, event: SecurityEvent) -> None:
        """Log a security event.

        Args:
            event: The SecurityEvent to log.
        """
        self._events.append(event)
        logger.debug("Audit event logged: %s/%s", event.event_type, event.severity)
        # Prune old events beyond retention
        self._prune_old()

    def query(self, filters: Optional[Dict] = None) -> List[SecurityEvent]:
        """Query events by filters.

        Args:
            filters: Dict of field:value to filter on.

        Returns:
            List of matching SecurityEvent objects.
        """
        if not filters:
            return list(self._events)
        results = self._events
        for key, value in filters.items():
            if key == "event_type":
                results = [e for e in results if e.event_type == value]
            elif key == "severity":
                results = [e for e in results if e.severity == value]
            elif key == "user_id":
                results = [e for e in results if e.user_id == value]
            elif key == "blocked":
                results = [e for e in results if e.blocked == value]
            elif key == "source":
                results = [e for e in results if e.source == value]
        return results

    def get_events_by_user(self, user_id: str) -> List[SecurityEvent]:
        """Get all events for a specific user.

        Args:
            user_id: The user identifier.

        Returns:
            List of SecurityEvent objects.
        """
        return [e for e in self._events if e.user_id == user_id]

    def get_recent_events(self, limit: int = 50) -> List[SecurityEvent]:
        """Get the most recent events.

        Args:
            limit: Maximum number of events to return.

        Returns:
            List of SecurityEvent objects, newest first.
        """
        sorted_events = sorted(self._events, key=lambda e: e.timestamp, reverse=True)
        return sorted_events[:limit]

    def export_logs(self, format: str = "json") -> str:
        """Export audit logs in the specified format.

        Args:
            format: Export format ("json" or "csv").

        Returns:
            Formatted string of audit events.
        """
        if format == "json":
            return json.dumps(
                [e.model_dump(mode="json") for e in self._events],
                indent=2,
                default=str,
            )
        elif format == "csv":
            lines = ["event_type,severity,source,user_id,blocked,timestamp"]
            for e in self._events:
                lines.append(
                    f"{e.event_type},{e.severity},{e.source},{e.user_id},{e.blocked},{e.timestamp.isoformat()}"
                )
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def clear(self) -> None:
        """Clear all events (for testing)."""
        self._events.clear()

    def _prune_old(self) -> None:
        """Remove events older than retention period."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.config.audit_log_retention_days)
        self._events = [e for e in self._events if e.timestamp >= cutoff]
