## 2024-03-24 - Interactive Div Accessibility
**Learning:** Custom `div` elements used as interactive components (like the orbCore button) require complete semantic setup to be accessible. This includes `role="button"`, `tabindex="0"`, `:focus-visible` styles, and keyboard event handlers for both `Enter` and `Space` keys to match native button behavior.
**Action:** Always use native `<button>` elements when possible. When custom `div` elements must be used for complex UI interactions, ensure the full suite of ARIA attributes, focus management, and keyboard handlers are implemented.
## 2025-08-01 - Native Button Refactor for Accessibility
**Learning:** When creating accessible interactive elements like buttons, using a custom `<div role="button" tabindex="0">` introduces unnecessary boilerplate since you also have to manually wire up multiple `keydown` event listeners for 'Enter' and 'Space' keys to mimic native functionality.
**Action:** Always prefer native `<button>` elements with `appearance: none;` and reset styles to match the desired design, as it handles keyboard accessibility and focus management out of the box, reducing codebase complexity.
