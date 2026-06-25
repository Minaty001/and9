# Hunter Phase — Deep Scan Findings

## BUG-7: reflection.py name extraction regex false positive on "main" (HIGH)

**File**: `app/core/reflection.py` lines 155-157
**Severity**: HIGH — Incorrect user identity data permanently stored

**Description**: The `extract_key_facts()` method uses a regex pattern that improperly captures any word following the Hindi pronoun "main" (मैं) as a user name. The regex:

```python
r'(?:mera naam |my name is |i am |i\'m |main |call me )(\w+(?:\s+\w+)?)'
```

The `main ` pattern (meaning "I") is unanchored — it only requires "main " as a prefix, without requiring a name-specific verb like "hoon" (हूँ, "am"). Any sentence starting with "main " immediately followed by a word will match:

- `"main kya kar raha hoon"` → stores `name="Kya"`
- `"main ja raha hoon"` → stores `name="Ja"`
- `"main baith gaya"` → stores `name="Baith"`

**Impact**: False name facts (confidence 0.3) are stored in semantic memory via `store_fact()` and in user_facts via `learn_fact()`. These propagate to the user profile and can cause the LLM to believe the user's name is a non-name word.

**Root cause**: The regex was meant to match name declarations like "main Saif hoon" but the word "hoon" is not required in the pattern. Adding `hoon` after the capture group would fix it.

**Fix**: Change the regex to require `hoon`/`hun` after the captured name, matching the same pattern used in `understanding.py` (`r'main (\w+) hoon'`).

---

## BUG-18: reminder_actions.py passes wrong parameters to EventSystem.add_event() (HIGH)

**File**: `app/and9/actions/reminder_actions.py` lines 74-81
**Severity**: HIGH — Reminders set through AND9 pipeline store corrupted data

**Description**: The `execute_set_reminder()` function calls `events_sys.add_event()` with parameter names that don't match the target method's signature:

```python
# reminder_actions.py line 74-81 (WRONG):
events_sys.add_event(
    event_type="reminder",
    timestamp=reminder_time.timestamp(),
    metadata={
        "title": label,
        "time": reminder_time.isoformat(),
    },
)
```

But `EventSystem.add_event()` expects:
```python
def add_event(self, title: str, event_time: Optional[str] = None,
              notes: str = "", repeat: str = "none") -> Optional[dict]:
```

**Result mapping**:
| Caller's Key | Becomes | Value | Impact |
|---|---|---|---|
| `event_type="reminder"` | `title` | `"reminder"` | Title is always "reminder" instead of the actual label |
| `timestamp=float` | `event_time` | Unix timestamp float | Expected ISO string — may fail in Supabase timestamp column |
| `metadata=dict` | `notes` | Python dict | Inserted into text column — may fail or be silently cast |
| (missing) | `repeat` | `"none"` | Correct by default |

**Impact**: Reminders set through `/api/and9` endpoint store wrong data in Supabase. The `build_event_context()` method tries `e["event_time"][:16]` on the float value, which raises `TypeError: 'float' object is not subscriptable`. This is caught by `_safe()` and silently dropped, so reminders set via AND9 appear to work but are effectively invisible.

**Fix**: Change the call to use correct parameter names:
```python
events_sys.add_event(
    title=label,
    event_time=reminder_time.isoformat(),
    notes=f"Reminder: {label}",
)
```

Note: The `orchestrator.py` (core) `_handle_reminder()` uses the correct API — only the AND9-specific reminder action handler is affected.

---

## BUG-8: truth_engine.py has_relevant_memory() confidence-blind (MEDIUM)

**File**: `app/core/truth_engine.py` lines 106-134
**Severity**: MEDIUM — Low-confidence regex data can pass the truth gate

**Description**: `has_relevant_memory()` checks if the user profile contains ANY non-empty value, but does NOT verify confidence or verified status:

```python
def has_relevant_memory(memory_ctx: dict, query: str = "") -> bool:
    profile = memory_ctx.get("user_profile", {}) or {}
    for _cat, facts in profile.items():
        if isinstance(facts, dict) and facts:
            for _key, val in facts.items():
                if val and str(val).strip():
                    return True  # <-- ANY non-empty value passes
    ...
```

And `get_user_profile()` in `memory.py` returns ALL semantic memory without confidence/verified filtering — it just does `SELECT category, fact_key, fact_value` without a WHERE clause.

**Impact**: Regex-extracted data (confidence 0.3, unverified) like false positive names from BUG-7 satisfies the "has memory" gate. The LLM receives context containing these low-confidence "facts" and may answer as if they're true.

**Fix**: Add confidence/verified filtering to `has_relevant_memory()` or use `get_verified_facts(min_confidence=0.5)` instead of `get_user_profile()`.

---

## BUG-10: events.py timezone-naive datetime usage (MEDIUM)

**File**: `app/core/events.py` lines 87-88, 157-185; `app/and9/utils/time_parser.py`
**Severity**: MEDIUM — Reminder times can be off by timezone offset

**Description**: `events.py` uses `datetime.utcnow()` throughout for all reminder time calculations, while `app/and9/utils/time_parser.py` uses `datetime.now()` (local time). There is no timezone normalization between the two:

```python
# events.py:
now = datetime.utcnow()
cutoff = (now + timedelta(hours=hours_ahead)).isoformat()
```

```python
# time_parser.py (internal):
now = datetime.now()
```

On Render.com (mentioned in `config.py` as deployment target), the server time is UTC. If the user is in India (IST = UTC+5:30), a reminder set for "3 baje" through the AND9 pipeline:
1. `time_parser.py` parses "3 baje" as local 15:00 → returns `datetime.now().replace(hour=15)` = UTC 15:00 (wrong, should be UTC 09:30)
2. `events.py` stores this as `event_time` in Supabase as "15:00 UTC"
3. The reminder fires at 15:00 UTC = 8:30 PM IST, not 3:00 PM IST

**Note for the English-only API `/api/events`**: The endpoints accept ISO strings (no timezone info), which also get stored as-is. The `TimeParser` in the AND9 pipeline would set times based on local `datetime.now()` but store them as UTC.

**Impact**: Users setting reminders for specific times through the AND9 Hinglish pipeline will have them fire 5.5 hours late (IST) or early (EST).

**Fix**: Standardize on timezone-aware datetimes. Either convert all `datetime.now()` calls to `datetime.now(timezone.utc)` or add timezone conversion when storing/retrieving event times.

---

## BUG-19: memory.py _safe() silently swallows ALL exceptions (MEDIUM)

**File**: `app/core/memory.py` lines 108-113
**Severity**: MEDIUM — Database failures invisible to application logic

**Description**: The `_safe()` wrapper catches ALL exceptions and returns a default value:

```python
def _safe(self, fn, default=None):
    try:
        return fn()
    except Exception as e:
        logger.warning(f"Supabase op failed: {e}")
        return default
```

This means:
- A Supabase connection failure returns the same empty/default result as "no data found"
- Callers cannot distinguish between "Supabase is down" and "the table is empty"
- Feature degradation is silent — no error is raised to the API layer

**Every method in Memory uses `_safe()`**: `add()`, `get_recent_chat()`, `get_facts()`, `add_episode()`, `store_fact()`, `get_user_profile()`, etc.

**Impact**: When Supabase is unavailable (network issue, expired key, rate limit), the assistant silently loses all persistence without any observable error — it operates as if the user has no history.

**Fix**: Either:
1. Propagate exceptions for critical operations (writes, session management) while allowing reads to gracefully degrade, or
2. Add a health-check flag that forces in-memory fallback mode explicitly

---

## BUG-14: skill_registry.py execute_skill() unhandled import errors (MEDIUM)

**File**: `app/and9/android/skill_registry.py` lines 94-117
**Severity**: MEDIUM — Action execution can fail with raw traceback

**Description**: The `execute_skill()` function performs dynamic import and attribute access without handling the failures:

```python
def execute_skill(action_type: str, params: dict, events_sys: Any = None) -> dict:
    if action_type not in _SKILL_REGISTRY:
        logger.warning("Action %s not in Skill Registry, falling back to dynamic import.", action_type)
        return {}

    module_path, func_name, arg_mapper = _SKILL_REGISTRY[action_type]
    import importlib
    module = importlib.import_module(module_path)   # can raise ModuleNotFoundError
    handler = getattr(module, func_name)             # can raise AttributeError
    kwargs = arg_mapper(params, events_sys)
    return handler(**kwargs)                         # can raise TypeError
```

While `android_executor.py` wraps the call in a try/except, the error dict returned uses `str(e)` which could include sensitive path information:
```python
return {
    "response": f"Action '{action_type}' failed: {str(e)} 😅",
    ...
}
```

**Impact**: If an action module is renamed or a handler function is deleted, raw traceback info could leak in the API response.

**Fix**: Handle `ModuleNotFoundError` and `AttributeError` explicitly with user-friendly messages.

---

## BUG-16: orchestrator.py goal completion uses first active goal (LOW)

**File**: `app/core/orchestrator.py` line 356
**Severity**: LOW — Ambiguous goal completion

**Description**: The `_handle_goal()` method always completes the first active goal without user confirmation:

```python
goals = self.goals.get_active_goals()
if goals:
    self.goals.complete_goal(goals[0]["id"])
```

If the user has multiple active goals and says "complete goal", the first one (not necessarily the one they intended) gets marked as done. There's no disambiguation or user prompt.

**Fix**: When multiple active goals exist, return a disambiguation prompt showing the list instead of auto-completing `goals[0]`.

---

## BUG-20: understanding.py detect_expertise() capitalization bug in stored profile (LOW)

**File**: `app/core/understanding.py` line 440
**Severity**: LOW — Stored expertise level in profile ignored due to case mismatch

**Description**: The `detect_expertise()` method checks for stored expertise level in the user profile by exact match:

```python
stored = user_profile.get('expertise_level')
if stored in ('beginner', 'intermediate', 'expert'):
    return stored
```

But `user_profile` from `Memory.get_user_profile()` returns facts stored via `store_fact()` → stored with key `"expertise_level"`. However, `learn_fact()` stores with `fact_key` which is the entity type name. These may differ in case or naming convention. If stored as `"Expertise_level"` or `"expertise"`, the check fails and the detection falls through to the keyword heuristic.

**Impact**: Minor — user may get re-evaluated as intermediate every time. Not a functional bug but a consistency issue.

---

## Summary

| ID | Severity | Component | Category | Fixable |
|---|---|---|---|---|
| BUG-7 | **HIGH** | reflection.py | Data quality / False positive | Yes |
| BUG-18 | **HIGH** | reminder_actions.py | Wrong API parameters | Yes |
| BUG-8 | MEDIUM | truth_engine.py | Missing confidence filter | Yes |
| BUG-10 | MEDIUM | events.py | Timezone unaware | Yes |
| BUG-19 | MEDIUM | memory.py | Silent exception swallow | Refactor |
| BUG-14 | MEDIUM | skill_registry.py | Unhandled imports | Yes |
| BUG-16 | LOW | orchestrator.py | Ambiguous auto-complete | Yes |
| BUG-20 | LOW | understanding.py | Profile key case | Yes |
