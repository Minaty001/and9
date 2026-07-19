## 2024-03-24 - Interactive Div Accessibility
**Learning:** Custom `div` elements used as interactive components (like the orbCore button) require complete semantic setup to be accessible. This includes `role="button"`, `tabindex="0"`, `:focus-visible` styles, and keyboard event handlers for both `Enter` and `Space` keys to match native button behavior.
**Action:** Always use native `<button>` elements when possible. When custom `div` elements must be used for complex UI interactions, ensure the full suite of ARIA attributes, focus management, and keyboard handlers are implemented.
