## 2026-07-08 - Icon-Only Button Accessibility Pattern
**Learning:** Found a common pattern in the JARVIS v2 Android UI template where utility buttons (close, add, search, send, voice note) rely solely on Unicode characters or CSS icons without accessible names, rendering them silent or ambiguous to screen readers.
**Action:** Always verify icon-only interactive elements (`<button>`, `<a>`) across all new and existing templates and proactively inject descriptive `aria-label` attributes to ensure keyboard and screen-reader accessibility.
