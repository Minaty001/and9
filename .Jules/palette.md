## 2024-08-21 - Missing Keyboard Focus Indicators
**Learning:** Found that custom styled buttons and inputs across the Jarvis webapp completely lack `:focus-visible` styles, rendering keyboard navigation nearly impossible for users relying on non-mouse input devices.
**Action:** Implement a global `:focus-visible` CSS rule for interactive elements (buttons, inputs, selects) utilizing `var(--accent-blue)` with `outline` and `outline-offset` to ensure consistent and highly visible focus states across the app.
