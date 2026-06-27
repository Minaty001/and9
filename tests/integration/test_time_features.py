from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from backend.cognition.planner.entity_extractor import extract_reminder
from backend.utils.time_parser import parse_time
from ai.micro_brain.utils.timezone_utils import get_time_in_city


IST = ZoneInfo("Asia/Kolkata")


def _next_weekday(now: datetime, weekday: int) -> datetime:
    days_ahead = weekday - now.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return (now + timedelta(days=days_ahead)).replace(hour=7, minute=0, second=0, microsecond=0)


def test_parse_time_handles_next_weekday_clock_time():
    now = datetime.now(IST)
    result = parse_time("alarm next monday 7 am")

    assert result["type"] == "absolute"
    assert result["hour"] == 7
    assert result["minute"] == 0
    expected = _next_weekday(now, 0)
    parsed = datetime.fromisoformat(result["datetime"])
    assert parsed.date() == expected.date()


def test_city_time_uses_city_timezone_date():
    info = get_time_in_city("delhi")
    assert info is not None
    parsed = datetime.fromisoformat(info["datetime_iso"])
    assert info["date"] == parsed.date().isoformat()


def test_reminder_extractor_keeps_recurring_metadata():
    result = extract_reminder("daily reminder at 7 am")

    assert result["trigger_at"]["type"] == "absolute"
    assert result["repeat_rule"] == "daily"
    assert result["repeat_days"] is None


def test_relative_reminder_seconds():
    result = extract_reminder("set reminder for after 5 seconds to take medicine")
    assert result["trigger_at"]["type"] == "relative"
    assert result["trigger_at"]["seconds"] == 5
    assert result["label"] == "to take medicine"

    result_s = extract_reminder("remind me after 5s")
    assert result_s["trigger_at"]["type"] == "relative"
    assert result_s["trigger_at"]["seconds"] == 5

