"""
Phase 28 — Time Parser.

Parses natural language time expressions into structured TimeExpression
objects. Supports relative, absolute, and recurring time formats.
"""

from __future__ import annotations

import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from .models import TimeExpression

logger = logging.getLogger(__name__)


class TimeParser:
    """Parses natural language time expressions.

    Usage:
        parser = TimeParser()
        expr = parser.parse("in 5 minutes")
        expr = parser.parse("tomorrow at 3pm")
        expr = parser.parse("every weekday at 9am")
    """

    def __init__(self):
        self._patterns = self._build_patterns()

    def parse(self, expression: str) -> Optional[TimeExpression]:
        """Parse a time expression string.

        Args:
            expression: Natural language time expression.

        Returns:
            TimeExpression if parsed successfully, None otherwise.
        """
        expr = expression.strip().lower()

        for pattern in self._patterns:
            match = pattern["regex"].search(expr)
            if match:
                try:
                    return pattern["handler"](match, expr)
                except (ValueError, IndexError) as e:
                    logger.debug("Failed to parse '%s' with pattern: %s", expr, e)
                    continue

        # Try absolute time parsing (HH:MM)
        parsed = self._try_parse_absolute(expr)
        if parsed:
            return parsed

        return None

    def _build_patterns(self) -> list:
        """Build parsing pattern list."""
        def handle_in_minutes(m, raw):
            """Handle 'in N minutes/hours/seconds'"""
            n = int(m.group(1))
            unit = m.group(2)
            now = datetime.now(timezone.utc)
            if unit.startswith("minute"):
                parsed = now + timedelta(minutes=n)
            elif unit.startswith("hour"):
                parsed = now + timedelta(hours=n)
            else:
                parsed = now + timedelta(seconds=n)
            return TimeExpression(raw=raw, parsed_time=parsed, confidence=0.9)

        def handle_tomorrow(m, raw):
            """Handle 'tomorrow at HH:MM' or 'tomorrow HH:MM'"""
            time_str = m.group(1) or ""
            now = datetime.now(timezone.utc)
            parsed = now + timedelta(days=1)
            if time_str:
                time_str = time_str.strip().replace(" ", "")
                parsed = self._apply_time(parsed, time_str)
            return TimeExpression(raw=raw, parsed_time=parsed, confidence=0.95)

        def handle_next_day(m, raw):
            """Handle 'next Monday/Tuesday/...'"""
            day = m.group(1).lower()
            now = datetime.now(timezone.utc)
            days = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                    "friday": 4, "saturday": 5, "sunday": 6}
            target = days.get(day, 0)
            current = now.weekday()
            diff = (target - current) % 7
            if diff == 0:
                diff = 7  # next week, not today
            parsed = now + timedelta(days=diff)
            time_str = m.group(2) or ""
            if time_str:
                time_str = time_str.strip().replace(" ", "")
                parsed = self._apply_time(parsed, time_str)
            return TimeExpression(raw=raw, parsed_time=parsed, confidence=0.9)

        def handle_recurring(m, raw):
            """Handle 'every weekday/weekend/day at HH:MM'"""
            period = m.group(1).lower()
            time_str = m.group(2) or ""
            now = datetime.now(timezone.utc)
            parsed = now
            if time_str:
                time_str = time_str.strip().replace(" ", "")
                parsed = self._apply_time(now, time_str)
            # If time is in past, advance to next occurrence
            if parsed <= now:
                if period == "day":
                    parsed += timedelta(days=1)
                elif period == "weekday":
                    # Advance to next weekday
                    for _ in range(7):
                        parsed += timedelta(days=1)
                        if parsed.weekday() < 5:
                            break
                elif period == "weekend":
                    for _ in range(7):
                        parsed += timedelta(days=1)
                        if parsed.weekday() >= 5:
                            break
                else:  # weekly
                    parsed += timedelta(weeks=1)

            pattern_map = {
                "day": "daily", "weekday": "weekdays",
                "weekend": "weekends", "week": "weekly",
            }
            return TimeExpression(
                raw=raw, parsed_time=parsed,
                is_recurring=True,
                recurrence_pattern=pattern_map.get(period, "daily"),
                confidence=0.85,
            )

        def handle_relative_day(m, raw):
            """Handle 'in 2 days', 'in 3 weeks'"""
            n = int(m.group(1))
            unit = m.group(2)
            now = datetime.now(timezone.utc)
            if unit.startswith("day"):
                parsed = now + timedelta(days=n)
            elif unit.startswith("week"):
                parsed = now + timedelta(weeks=n)
            else:
                parsed = now + timedelta(days=n)
            return TimeExpression(raw=raw, parsed_time=parsed, confidence=0.9)

        def handle_at_time(m, raw):
            """Handle 'at HH:MM' (today)"""
            time_str = m.group(1)
            now = datetime.now(timezone.utc)
            parsed = self._apply_time(now, time_str)
            if parsed <= now:
                # If time already passed today, assume tomorrow
                parsed += timedelta(days=1)
            return TimeExpression(raw=raw, parsed_time=parsed, confidence=0.95)

        return [
            {"regex": re.compile(r"in\s+(\d+)\s+(minute|hour|second)s?"), "handler": handle_in_minutes},
            {"regex": re.compile(r"tomorrow(?:\s+at\s+(.+))?"), "handler": handle_tomorrow},
            {"regex": re.compile(r"next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)(?:\s+at\s+(.+))?"), "handler": handle_next_day},
            {"regex": re.compile(r"every\s+(weekday|weekend|day|week)(?:\s+at\s+(.+))?"), "handler": handle_recurring},
            {"regex": re.compile(r"in\s+(\d+)\s+(day|week)s?"), "handler": handle_relative_day},
            {"regex": re.compile(r"at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm))"), "handler": handle_at_time},
            {"regex": re.compile(r"at\s+(\d{1,2}:\d{2})"), "handler": handle_at_time},
        ]

    def _apply_time(self, dt: datetime, time_str: str) -> datetime:
        """Apply a time string (HH:MM or HH:MMam/pm) to a datetime.

        Args:
            dt: Base datetime.
            time_str: Time string to apply.

        Returns:
            Updated datetime.
        """
        time_str = time_str.lower().replace(" ", "")
        is_pm = "pm" in time_str
        is_am = "am" in time_str
        time_str = time_str.replace("am", "").replace("pm", "")

        if ":" in time_str:
            parts = time_str.split(":")
            hour = int(parts[0])
            minute = int(parts[1])
        else:
            hour = int(time_str)
            minute = 0

        if is_pm and hour < 12:
            hour += 12
        elif is_am and hour == 12:
            hour = 0

        return dt.replace(hour=hour, minute=minute, second=0, microsecond=0)

    def _try_parse_absolute(self, expr: str) -> Optional[TimeExpression]:
        """Try parsing absolute time formats."""
        # HH:MM format
        m = re.match(r"^(\d{1,2}):(\d{2})\s*(am|pm)?$", expr)
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2))
            period = m.group(3)
            if period:
                period = period.lower()
                if period == "pm" and hour < 12:
                    hour += 12
                elif period == "am" and hour == 12:
                    hour = 0
            now = datetime.now(timezone.utc)
            parsed = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if parsed <= now:
                parsed += timedelta(days=1)
            return TimeExpression(raw=expr, parsed_time=parsed, confidence=0.95)
        return None
