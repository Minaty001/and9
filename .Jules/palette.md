## 2026-08-29 - Focus Visibility and ARIA Labels
**Learning:** Found multiple interactive elements lacking keyboard focus indicators and icon-only buttons missing ARIA labels, creating accessibility barriers for screen reader and keyboard users in the Jarvis webapp.
**Action:** Consistently applying `:focus-visible` with `outline` and `outline-offset` to all interactive elements, and ensuring all icon-only buttons and form inputs have explicit ARIA labels.
