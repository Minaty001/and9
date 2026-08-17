## 2024-03-24 - Interactive Div Accessibility
**Learning:** Custom `div` elements used as interactive components (like the orbCore button) require complete semantic setup to be accessible. This includes `role="button"`, `tabindex="0"`, `:focus-visible` styles, and keyboard event handlers for both `Enter` and `Space` keys to match native button behavior.
**Action:** Always use native `<button>` elements when possible. When custom `div` elements must be used for complex UI interactions, ensure the full suite of ARIA attributes, focus management, and keyboard handlers are implemented.

## 2026-08-17 - Refactoring Div to Native Button
**Learning:** Using `div` with `role="button"` and JavaScript keyboard handlers is error-prone and can lead to duplicate event listeners or missing native behaviors. Native `<button>` elements handle `Enter` and `Space` keys and focus management inherently.
**Action:** Replaced the custom interactive `#orbCore` `div` with a `<button type="button">`, applying `appearance: none; border: none; padding: 0; background: transparent;` to maintain design while automatically inheriting native accessibility benefits.
