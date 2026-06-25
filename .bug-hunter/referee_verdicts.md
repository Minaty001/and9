# Referee Phase — Final Verdicts

## BUG-7: reflection.py name extraction regex — DISMISSED (LOW)

**Skeptic challenge**: `extract_key_facts()` is defined but NEVER called anywhere in the application codebase. It's dead code — documented as a utility method but not wired into any pipeline.

**Verdict**: **LOW (latent)** — The function exists but isn't invoked. No production impact. If someone later calls it, the false positives would corrupt user data. Recommend fixing the regex regardless since dead code is a maintenance liability.

---

## BUG-18: reminder_actions.py wrong EventSystem.add_event() params — CONFIRMED (HIGH)

**Skeptic challenge**: Examine the actual method signature vs. the call:

```python
# EventSystem.add_event signature (events.py):
def add_event(self, title: str, event_time: Optional[str] = None,
              notes: str = "", repeat: str = "none") -> Optional[dict]:

# Actual call (reminder_actions.py line 74-81):
events_sys.add_event(
    event_type="reminder",         # → title="reminder" (always!)
    timestamp=reminder_time.timestamp(),  # → event_time=float (should be ISO string)
    metadata={"title": label, ...},       # → notes=dict (should be string)
)
```

**Data corruption**: Title is always "reminder" instead of the user-given label. Event_time is a Unix timestamp float instead of ISO string. Notes is a Python dict instead of string. Supabase expects `TEXT` columns for event_time and notes — a dict inserted into a text column may fail depending on the driver version. The float timestamp silently converts.

**Impact chain**: When `build_event_context()` tries `e.get("event_time", "")[:16]` on a float, it raises `TypeError`. Caught by `_safe()`. Reminders set through `/api/and9` pipeline appear to work but are effectively invisible — they never show up in the UI and never fire.

**Verdict**: **CONFIRMED (HIGH)** — Active bug in a production code path. Fixable with a one-line parameter rename.

---

## BUG-8: truth_engine.py has_relevant_memory() confidence-blind — DISMISSED (INFO)

**Skeptic challenge**: The function's purpose is to check "does ANY data exist?" — a binary presence check. Quality filtering already happens at storage time (confidence caps in `cap_confidence()`, Rule 5/6 rejections). The LLM instruction in ContextBuilder already says "Sirf upar diya hua context use karo. Kabhi bhi information invent mat karo." — the LLM won't hallucinate based on low-confidence data.

**Data flow**: Low-confidence (0.3) regex data is already marked `verified=False`. The distinction is visible to the LLM via `Extracted info: {'name': 'Kya'}` in the context. The LLM is trained to use such data cautiously.

**Verdict**: **DISMISSED (INFO)** — Working as designed. Confidence filtering at the truth gate would be an enhancement, not a bug fix.

---

## BUG-10: events.py timezone-naive datetime — CONFIRMED (MEDIUM)

**Skeptic challenge**: Trace the exact time math:

1. User in IST says "kal 3 baje yaad dilana" (remind me tomorrow at 3 PM)
2. `parse_event_from_text()` → `datetime.utcnow() + timedelta(days=1)` → tomorrow UTC date
3. Sets hour=15 on UTC datetime → `"2024-06-25T15:00:00"` (UTC 3 PM, which is IST 8:30 PM)
4. `get_due_events()` → `datetime.utcnow().isoformat()` → `"2024-06-25T09:30:00"` (IST 3 PM = UTC 9:30 AM)
5. `.lte("event_time", "2024-06-25T09:30:00")` — event_time `"2024-06-25T15:00:00"` is NOT <= `"09:30:00"`
6. Event is never returned as "due"! It only becomes due at UTC 15:00 = IST 8:30 PM

**Impact**: Time-based reminders fire 5.5 hours late for IST users. The bug affects ALL users whose local timezone is not UTC. For the AND9 pipeline path (via `time_parser.py`), the same issue exists in reverse — `datetime.now()` gives local time but events.py compares against `datetime.utcnow()`.

**Verdict**: **CONFIRMED (MEDIUM)** — Active bug affecting all timezone-aware users. Requires standardization on timezone-aware datetimes or explicit timezone handling.

---

## BUG-19: memory.py _safe() silent failures — DISMISSED (INFO)

**Skeptic challenge**: This is an intentional design pattern for a consumer-grade AI assistant. Silently falling back to in-memory storage when Supabase is unavailable is the desired behavior — the assistant should keep working without persistence rather than crashing. The warning log exists for debugging.

**Verdict**: **DISMISSED (INFO)** — Intentional design. Not a bug.

---

## BUG-14: skill_registry.py unhandled import errors — DISMISSED (LOW)

**Skeptic challenge**: The exceptions from `execute_skill()` propagate to `android_executor.py` which catches them:

```python
except Exception as e:
    logger.error("Handler '%s' failed: %s", handler_path, e, exc_info=True)
    return {
        "response": f"Action '{action_type}' failed: {str(e)} 😅",
        ...
    }
```

The error message includes `str(e)` which for a `ModuleNotFoundError` shows the module path (e.g., `"No module named 'app.and9.actions.nonexistent'"`). This is a minor information leak but in a local-only Termux app, this has no security impact.

**Verdict**: **DISMISSED (LOW)** — Already handled by the caller. Minor path disclosure in error messages is negligible for a local-only app.

---

## BUG-16: orchestrator.py goal completion ambiguity — DISMISSED (LOW)

**Skeptic challenge**: The auto-complete of `goals[0]` when multiple active goals exist is a simplification for single-goal users. Users with multiple goals can specify "complete [title]" which the IntentRouter would handle differently. This is a UX convenience, not a correctness bug.

**Verdict**: **DISMISSED (LOW)** — Minor UX design choice. Only matters for power users with multiple concurrent goals.

---

## BUG-20: understanding.py detect_expertise() capitalization — DISMISSED (LOW)

**Skeptic challenge**: The profile key `expertise_level` is set by `learn_fact(key="expertise_level", ...)` which uses exactly the key the function checks. There's no case mismatch in the actual codebase. The concern was hypothetical.

**Verdict**: **DISMISSED (LOW)** — Keys are consistent in practice. No evidence of actual mismatch.

---

## FINAL SUMMARY

| ID | Severity | Status | Component | Fix |
|---|---|---|---|---|
| BUG-7 | LOW (latent) | `extract_key_facts()` never called | reflection.py | Fix regex to require `hoon` after `main` |
| **BUG-18** | **HIGH** | **CONFIRMED** | **reminder_actions.py** | **Fix add_event() params** |
| BUG-8 | INFO | Dismissed (by design) | truth_engine.py | Enhancement |
| **BUG-10** | **MEDIUM** | **CONFIRMED** | **events.py** | **Use timezone-aware datetimes** |
| BUG-19 | INFO | Dismissed (by design) | memory.py | Not a bug |
| BUG-14 | LOW | Dismissed (caught by caller) | skill_registry.py | Enhancement |
| BUG-16 | LOW | Dismissed (design choice) | orchestrator.py | Enhancement |
| BUG-20 | LOW | Dismissed (no evidence) | understanding.py | Not a bug |

**Fixable bugs (Referee-approved for Fixer phase):**
1. **BUG-18** (HIGH) — Fix `reminder_actions.py` `add_event()` call parameters
2. **BUG-10** (MEDIUM) — Fix `events.py` to use timezone-aware datetime
