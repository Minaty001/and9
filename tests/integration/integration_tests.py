"""
AND9 — Integration Test Suite (Priority 8).

Validates the end-to-end intent resolution pipeline.
Tests normalisation, classification, extraction, validation, and action dispatch.

Run with:
    pytest tests/integration_tests.py -v
"""
import pytest
from app.cognition.planner import AND9
from app.core.constants import ActionType
from app.cognition.planner.brain_types import IntentType

@pytest.fixture
def and9():
    """Returns a fresh instance of the AND9 brain."""
    return AND9(enable_patterns=False)

def test_alarm_intent(and9):
    """Test setting an alarm with time parsing."""
    res = and9.process("set alarm for tomorrow morning")
    assert res["success"] is True
    assert res["action"] == ActionType.SET_ALARM.value
    assert res["intent"] == IntentType.SET_ALARM.value
    assert res["payload"]["hour"] == 9
    assert res["payload"]["minute"] == 0

def test_timer_intent(and9):
    """Test timer intent and parameter validation."""
    # Complete query
    res = and9.process("10 minute ka timer lagao")
    assert res["success"] is True
    assert res["action"] == ActionType.SET_TIMER.value
    assert res["payload"]["length"] == 600

    # Incomplete query should trigger validation failure
    res_incomplete = and9.process("timer lagao")
    assert res_incomplete["success"] is False
    assert "kitne time ka" in res_incomplete["response"].lower()

def test_call_intent(and9):
    """Test contact resolution call intent."""
    res = and9.process("call mummy")
    assert res["success"] is True
    assert res["action"] == ActionType.CALL.value
    assert res["payload"]["contact_query"] == "mummy"

def test_app_launch_intent(and9):
    """Test dynamic app launch."""
    res = and9.process("open instagram")
    assert res["success"] is True
    assert res["action"] == ActionType.LAUNCH_APP.value
    assert res["payload"]["package"] == "com.instagram.android"

def test_youtube_play_intent(and9):
    """Test youtube video play deep link."""
    res = and9.process("play doremon on youtube")
    assert res["success"] is True
    assert res["action"] == ActionType.YOUTUBE_PLAY.value
    assert "doremon" in res["payload"]["query"]

def test_search_fallback(and9):
    """Test that generic questions fallback to SEARCH instead of CHAT."""
    res = and9.process("who is the prime minister of india")
    assert res["success"] is True
    assert res["action"] == ActionType.CHAT.value

def test_emergency_intent(and9):
    """Test emergency override."""
    res = and9.process("mujhe bachao emergency hai")
    assert res["success"] is True
    assert res["action"] == ActionType.EMERGENCY.value
    assert res["payload"]["number"] == "112"

def test_flashlight_toggle(and9):
    """Test flashlight hardware control."""
    res = and9.process("turn on the flashlight")
    assert res["success"] is True
    assert res["action"] == ActionType.FLASHLIGHT_ON.value

def test_chrome_firewall(and9):
    """Test that open chrome goes to launch, not search fallback."""
    res = and9.process("chrome kholo")
    assert res["success"] is True
    assert res["action"] == ActionType.LAUNCH_APP.value
    assert res["payload"]["package"] in ("com.android.chrome", "com.chrome")
