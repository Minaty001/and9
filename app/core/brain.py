"""
app/core/brain.py — Central LLM interface.

Provider priority:
  1. Groq (primary — fast, llama-3.3-70b-versatile)
  2. Opencode Zen (fallback — deepseek-v4-flash-free)

All LLM calls go through ask_llm(). Never call providers directly.
"""
import json
import re
import logging
from typing import Optional

import requests

from app.core.config import (
    GROQ_API_KEY, GROQ_API_BASE, GROQ_CHAT_MODEL,
    OPENCODE_API_KEY, OPENCODE_API_BASE, OPENCODE_CHAT_MODEL,
)
from app.core.memory import Memory
from app.core.personality import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_session = requests.Session()

# ── Model cache per provider ───────────────────────────────────
_groq_models: list = []
_opencode_models: list = []


# ═══════════════════════════════════════════════════════════════
# Provider: Groq
# ═══════════════════════════════════════════════════════════════

def _groq_call(
    payload_messages: list,
    model: str,
    temperature: float,
    max_tokens: int,
) -> Optional[str]:
    """Call Groq API. Returns response text or None on failure."""
    if not GROQ_API_KEY:
        return None
    payload = {
        "model": model,
        "messages": payload_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        resp = _session.post(
            f"{GROQ_API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=12,  # Groq is fast — 12s is plenty; fail fast → fallback
        )
        if resp.status_code == 200:
            text = resp.json()["choices"][0]["message"]["content"].strip()
            logger.info(f"Groq OK — model={model}")
            return text
        # 429 = rate limit, 503 = overloaded → fall through to fallback
        logger.warning(f"Groq error {resp.status_code}: {resp.text[:120]}")
        return None
    except requests.exceptions.Timeout:
        logger.warning("Groq timeout — falling back to Opencode")
        return None
    except Exception as e:
        logger.warning(f"Groq call failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# Provider: Opencode Zen (fallback)
# ═══════════════════════════════════════════════════════════════

def _get_opencode_models() -> list:
    global _opencode_models
    if _opencode_models:
        return _opencode_models
    if not OPENCODE_API_KEY:
        return []
    try:
        resp = _session.get(
            f"{OPENCODE_API_BASE}/models",
            headers={"Authorization": f"Bearer {OPENCODE_API_KEY}"},
            timeout=10,
        )
        if resp.status_code == 200:
            _opencode_models = [m["id"] for m in resp.json().get("data", []) if "id" in m]
            logger.info(f"Opencode models fetched: {len(_opencode_models)} available")
            return _opencode_models
    except Exception as e:
        logger.warning(f"Could not fetch Opencode models: {e}")
    return []


def _resolve_opencode_model(requested: str) -> str:
    """Return the best available Opencode model."""
    models = _get_opencode_models()
    if not models:
        return requested
    if requested in models:
        return requested
    # Prefer free models in priority order
    for kw in ["deepseek-v4-flash-free", "deepseek", "llama", "mistral"]:
        for m in models:
            if kw in m.lower():
                logger.info(f"Opencode fallback model: {m}")
                return m
    return models[0]


def _opencode_call(
    payload_messages: list,
    model: str,
    temperature: float,
    max_tokens: int,
) -> Optional[str]:
    """Call Opencode Zen API. Returns response text or None on failure."""
    if not OPENCODE_API_KEY:
        return None
    resolved = _resolve_opencode_model(model)
    payload = {
        "model": resolved,
        "messages": payload_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        resp = _session.post(
            f"{OPENCODE_API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENCODE_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,  # Opencode fallback — 20s max
        )
        if resp.status_code == 200:
            text = resp.json()["choices"][0]["message"]["content"].strip()
            logger.info(f"Opencode OK — model={resolved}")
            return text
        logger.error(f"Opencode error {resp.status_code}: {resp.text[:120]}")
        return None
    except requests.exceptions.Timeout:
        logger.error("Opencode timeout")
        return None
    except Exception as e:
        logger.error(f"Opencode call failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# Public Interface
# ═══════════════════════════════════════════════════════════════

def ask_llm(
    messages: list,
    model: str = GROQ_CHAT_MODEL,
    system: Optional[str] = None,
    context: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 512,
) -> str:
    """Send messages to LLM. Tries Groq first, falls back to Opencode Zen.

    Args:
        messages:    Chat messages list (role/content dicts).
        model:       Preferred model name (used for Groq; Opencode uses its own default).
        system:      Optional system prompt override.
        context:     Rich context from ContextBuilder (highest priority over system).
        temperature: Sampling temperature.
        max_tokens:  Max response tokens.

    Returns:
        The LLM response text, or an error string.
    """
    # Build system message
    payload_messages: list = []
    if context:
        payload_messages.append({"role": "system", "content": context})
    elif system:
        payload_messages.append({"role": "system", "content": system})
        payload_messages.append({"role": "system", "content": SYSTEM_PROMPT})

    payload_messages.extend(messages)

    # ── 1. Try Groq (primary) ──────────────────────────────────
    result = _groq_call(payload_messages, model, temperature, max_tokens)
    if result is not None:
        return result

    # ── 2. Try Opencode Zen (fallback) ────────────────────────
    logger.warning("Groq unavailable — using Opencode Zen fallback")
    result = _opencode_call(payload_messages, OPENCODE_CHAT_MODEL, temperature, max_tokens)
    if result is not None:
        return result

    # ── 3. Both failed ────────────────────────────────────────
    if not GROQ_API_KEY and not OPENCODE_API_KEY:
        return "AI service not configured. Please set GROQ_API_KEY in environment variables."
    return "[LLM error: both providers failed]"


def ask_llm_json(
    messages: list,
    model: str = GROQ_CHAT_MODEL,
    system: Optional[str] = None,
) -> dict:
    """Ask LLM and parse JSON from the response."""
    raw = ask_llm(messages, model=model, system=system, temperature=0.0)
    try:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except (json.JSONDecodeError, AttributeError) as e:
        logger.debug("ask_llm_json parse failed: %s", e)
    return {}


# Keep for backwards compat (used by some agents)
def get_available_models() -> list:
    """Return combined list of available models from all providers."""
    models = []
    if GROQ_API_KEY:
        models.append(GROQ_CHAT_MODEL)
    models.extend(_get_opencode_models())
    return models


# ── REMOVED (Constitution V3 Rule 5/6) ───────────────────────────
# extract_facts_from_text() and FACT_EXTRACTION_PROMPT removed.
# LLM inference must NEVER be stored as fact per Rule 5:
#   llm_inference → confidence 0.0 → never stored.
# Use direct regex extraction (understanding.py) instead.
# ────────────────────────────────────────────────────────────────
