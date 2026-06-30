"""
AND9 — Recurring Reminder Engine (Phase C).

Automatically reschedules reminders based on their repeat_rule.
Called after a reminder fires to create the next occurrence.

Supported rules:
    daily    → +1 day
    weekdays → +1 day, skip Saturday/Sunday
    weekly   → +7 days (optionally on specific weekday[s])
    monthly  → same day next month (with month-end clamping)
    yearly   → same date next year
"""
import logging
import json
from datetime import datetime, timedelta
from calendar import monthrange
from zoneinfo import ZoneInfo
from typing import Optional

from app.services.reminder import storage

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")


class RecurringEngine:
    """Handles auto-rescheduling of recurring reminders.

    Usage:
        engine = RecurringEngine()
        engine.reschedule(reminder_dict)   # after a reminder fires
    """

    def reschedule(self, reminder: dict) -> Optional[int]:
        """Reschedule a recurring reminder after it has fired.

        Args:
            reminder: The fired reminder dict (from storage.get_due() or get_by_id()).

        Returns:
            The new reminder ID if rescheduled, or None if the series has ended
            or the reminder is non-recurring.
        """
        rule = (reminder.get("repeat_rule") or "").strip().lower()
        if not rule:
            return None  # one-shot, not recurring

        # Check repeat_end
        repeat_end = reminder.get("repeat_end")
        if repeat_end:
            end_dt = datetime.fromisoformat(repeat_end)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=IST)
            if datetime.now(IST) > end_dt:
                logger.info("Recurring series #%d ended (past repeat_end)", reminder["id"])
                return None

        trigger_str = reminder.get("trigger_time")
        if not trigger_str:
            logger.warning("Reminder #%d has no trigger_time", reminder["id"])
            return None

        try:
            trigger_dt = datetime.fromisoformat(trigger_str)
        except (ValueError, TypeError):
            logger.warning("Reminder #%d has invalid trigger_time: %s", reminder["id"], trigger_str)
            return None

        if trigger_dt.tzinfo is None:
            trigger_dt = trigger_dt.replace(tzinfo=IST)

        next_trigger = self._compute_next(rule, trigger_dt, reminder)
        if next_trigger is None:
            logger.info("Recurring series #%d ended (no next trigger computed)", reminder["id"])
            return None

        new_id = storage.reschedule_recurring(reminder["id"], next_trigger)
        logger.info(
            "Rescheduled #%d → #%d (%s): %s",
            reminder["id"], new_id, rule, next_trigger.isoformat()
        )
        return new_id

    # ── Rule-specific computing ────────────────────────────────────

    def _compute_next(self, rule: str, last_trigger: datetime,
                      reminder: dict) -> Optional[datetime]:
        """Compute the next trigger datetime based on the repeat rule."""
        now = datetime.now(IST)

        if rule == "daily":
            return self._daily(last_trigger, now)

        elif rule == "weekdays":
            return self._weekdays(last_trigger, now)

        elif rule == "weekly":
            return self._weekly(last_trigger, now, reminder)

        elif rule == "monthly":
            return self._monthly(last_trigger, now)

        elif rule == "yearly":
            return self._yearly(last_trigger, now)

        else:
            logger.warning("Unknown repeat_rule '%s' for reminder #%d", rule, reminder.get("id"))
            return None

    @staticmethod
    def _daily(last: datetime, now: datetime) -> datetime:
        """Next occurrence: +1 day."""
        candidate = last + timedelta(days=1)
        while candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    @staticmethod
    def _weekdays(last: datetime, now: datetime) -> datetime:
        """Next occurrence: +1 day, skip weekends (Saturday=5, Sunday=6)."""
        candidate = last + timedelta(days=1)
        while candidate <= now or candidate.weekday() >= 5:
            if candidate > now and candidate.weekday() < 5:
                break
            candidate += timedelta(days=1)
        return candidate

    @staticmethod
    def _weekly(last: datetime, now: datetime,
                reminder: dict) -> datetime:
        """Next occurrence: +7 days, or pinned to specific weekday(s).

        If the reminder has specific days (from 'every Monday' parsing),
        find the next one; otherwise just add 7 days.
        """
        days: Optional[list] = reminder.get("days")  # from parse_recurring
        if not days:
            repeat_days = reminder.get("repeat_days")
            if isinstance(repeat_days, str) and repeat_days:
                try:
                    days = json.loads(repeat_days)
                except Exception:
                    parts = [p.strip() for p in repeat_days.split(",") if p.strip()]
                    days = [int(p) for p in parts if p.isdigit()]
        if days and len(days) > 0:
            # Pinned to specific weekday(s) — find the next one
            target = days[0]  # use the first specified day
            candidate = _next_weekday(last, target)
            while candidate <= now:
                candidate += timedelta(days=7)
            return candidate
        # No specific day → every 7 days from last trigger
        candidate = last + timedelta(days=7)
        while candidate <= now:
            candidate += timedelta(days=7)
        return candidate

    @staticmethod
    def _monthly(last: datetime, now: datetime) -> datetime:
        """Next occurrence: same day next month, clamped to month-end."""
        candidate = _add_month_clamped(last)
        while candidate <= now:
            candidate = _add_month_clamped(candidate)
        return candidate

    @staticmethod
    def _yearly(last: datetime, now: datetime) -> datetime:
        """Next occurrence: same date next year."""
        try:
            candidate = last.replace(year=last.year + 1)
        except ValueError:
            # Feb 29 in non-leap year → use Feb 28
            candidate = last.replace(year=last.year + 1, day=28)
        while candidate <= now:
            try:
                candidate = candidate.replace(year=candidate.year + 1)
            except ValueError:
                candidate = candidate.replace(year=candidate.year + 1, day=28)
        return candidate


# ── Date helpers ─────────────────────────────────────────────────────


def _next_weekday(from_dt: datetime, target_weekday: int) -> datetime:
    """Return the next occurrence of target_weekday (0=Mon..6=Sun) on or after from_dt."""
    days_ahead = target_weekday - from_dt.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return from_dt + timedelta(days=days_ahead)


def _add_month_clamped(dt: datetime) -> datetime:
    """Add one month, clamping the day to the target month's max days."""
    year = dt.year + (dt.month // 12)
    month = (dt.month % 12) + 1
    if month == 1:
        year += 1  # actually this is already handled by the above logic
    # Actually let me redo this properly
    total_months = dt.year * 12 + dt.month  # 1-based month
    total_months += 1
    year = (total_months - 1) // 12
    month = (total_months - 1) % 12 + 1
    max_day = monthrange(year, month)[1]
    day = min(dt.day, max_day)
    return dt.replace(year=year, month=month, day=day, hour=dt.hour,
                      minute=dt.minute, second=dt.second, microsecond=dt.microsecond)
