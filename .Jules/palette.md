## 2024-03-24 - Interactive Div Accessibility
**Learning:** Custom `div` elements used as interactive components (like the orbCore button) require complete semantic setup to be accessible. This includes `role="button"`, `tabindex="0"`, `:focus-visible` styles, and keyboard event handlers for both `Enter` and `Space` keys to match native button behavior.
**Action:** Always use native `<button>` elements when possible. When custom `div` elements must be used for complex UI interactions, ensure the full suite of ARIA attributes, focus management, and keyboard handlers are implemented.

## 2024-03-24 - Custom Modal Dialog Accessibility
**Learning:** For custom modals that handle visual imagery rather than text, mapping proper semantics (`role="dialog"`, `aria-modal="true"`) is only part of the solution; they also need `tabindex="-1"` and an explicit `.focus()` call on open, alongside custom keyboard handlers (`Esc`, `Space`, `Enter`) so keyboard-only users can interact with and dismiss the element seamlessly.
**Action:** When implementing non-standard modals without native `<dialog>`, guarantee focus entrapment/return and provide key bindings matching native modal behavior.
