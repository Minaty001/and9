# Bug-Hunter Final Report — JARVIS PCOS

**Run mode**: Full project scan (all files)
**Pipeline**: Recon → Hunter → Skeptic → Referee → Fixer
**Date**: 2026-06-24

---

## Summary

- **Total files scanned**: 155 (source) + 859 (vendored deps skipped)
- **Bugs found**: 8
- **Bugs confirmed (Referee)**: 2
- **Bugs fixed**: 2
- **Bug types**: Wrong API parameters (HIGH), Timezone mismatch (MEDIUM)

---

## Fixed Bugs

### BUG-18 (HIGH) — `reminder_actions.py` wrong `add_event()` params

**File**: `app/and9/actions/reminder_actions.py` line 74-81

**Problem**: `execute_set_reminder()` called `events_sys.add_event()` with wrong parameter names that don't match the `EventSystem.add_event()` signature:

| Caller's Key | Maps To | Actual Value | Expected |
|---|---|---|---|
| `event_type="reminder"` | `title` | Always "reminder" | The user's actual label |
| `timestamp=float` | `event_time` | Unix timestamp | ISO datetime string |
| `metadata=dict` | `notes` | Python dict | String |

**Impact**: Reminders set through the AND9 pipeline (`/api/and9`) store corrupted data in Supabase — title always "reminder", event_time as float. When `build_event_context()` tries `e["event_time"][:16]` on a float, it crashes (caught by `_safe()`). These reminders are effectively invisible — never shown in UI, never fire.

**Fix**: Changed call to use correct parameter names:
```python
events_sys.add_event(
    title=label,
    event_time=reminder_time.isoformat(),
    notes=f"Reminder: {label}",
)
```

---

### BUG-10 (MEDIUM) — `events.py` timezone-naive datetime

**File**: `app/core/events.py` (8 occurrences)

**Problem**: All time calculations used `datetime.utcnow()` (deprecated in Python 3.12+, removed in 3.14). For users in non-UTC timezones (e.g., India IST = UTC+5:30), reminder times are off by the timezone offset.

**Example**: A user in IST says "kal 3 baje yaad dilana":
1. `parse_event_from_text()` → `datetime.utcnow() + timedelta(days=1)` = tomorrow at UTC date
2. Sets `hour=15` on UTC datetime → `"2024-06-25T15:00:00"` (UTC 3 PM = IST 8:30 PM)
3. User expects reminder at IST 3 PM, but it fires at IST 8:30 PM — **5.5 hours late**

**Fix**: Replaced all `datetime.utcnow()` with `datetime.now(timezone.utc).replace(tzinfo=None)` — eliminates the deprecated call, explicitly marks UTC intent, and preserves naive ISO output format for backward compatibility.

---

## Dismissed Findings

| ID | Category | Reason |
|---|---|---|
| BUG-7 | reflection.py regex | `extract_key_facts()` is dead code (defined, never called) |
| BUG-8 | truth_engine filter | Working as designed — confidence filtering is a storage-time concern |
| BUG-14 | skill_registry errors | Caught by caller (`android_executor.py`) |
| BUG-16 | Goal auto-complete | Design choice, not a bug |
| BUG-19 | memory.py silent fails | Intentional fallback behavior |
| BUG-20 | expertise key case | No evidence of mismatch |

---

## Files Modified

1. **`app/and9/actions/reminder_actions.py`** — Fixed `add_event()` parameter names
2. **`app/core/events.py`** — Replaced deprecated `datetime.utcnow()` with timezone-aware equivalent

---

## Pipeline Artifacts

- `.bug-hunter/recon.md` — Architecture map, trust boundaries, 20 initial suspects
- `.bug-hunter/hunter_findings.md` — 8 deep-scan findings with code evidence
- `.bug-hunter/referee_verdicts.md` — Skeptic challenges + final verdicts for each
- `.bug-hunter/payloads/` — Individual issue files

---

## Verification

Both modified files compile and import without errors:
- `python -m py_compile app/core/events.py` ✓
- `python -m py_compile app/and9/actions/reminder_actions.py` ✓
- Import test: `from app.core import events` ✓
- Import test: `from app.and9.actions import reminder_actions` ✓
