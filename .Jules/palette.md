## 2026-08-23 - Added Keyboard Navigation Accessibility Focus Styles
**Learning:** Found that custom interactive UI elements like buttons and icons in this specific Jarvis web app theme did not have explicit `:focus-visible` styles applied, which is a common accessibility regression when applying CSS resets or custom styles to native elements.
**Action:** Applied `outline` and `outline-offset` properties tied to the `var(--accent-blue)` theme variable to all button classes and selects to ensure visibility during keyboard navigation.
