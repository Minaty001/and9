"""Tests for the integrated offline Micro Neural Brain intent routing fallback."""
import sys
import os
import pytest

# Ensure app package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.brain.planner.intent_router import detect_intent_with_confidence

def test_micro_brain_fallback():
    """Verify that queries classified by Micro Neural Brain are successfully routed."""
    # "settings chalana hai" should map to open_app via Neural Brain fallback
    intent, action, params, confidence = detect_intent_with_confidence("settings chalana hai")
    assert intent == "open_app"
    assert action == "open_app"
    assert "settings" in params.get("app_name", "").lower()
    assert confidence >= 0.70
