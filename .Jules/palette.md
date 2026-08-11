## 2024-03-24 - Interactive Div Accessibility
**Learning:** Custom `div` elements used as interactive components (like the orbCore button) require complete semantic setup to be accessible. This includes `role="button"`, `tabindex="0"`, `:focus-visible` styles, and keyboard event handlers for both `Enter` and `Space` keys to match native button behavior.
**Action:** Always use native `<button>` elements when possible. When custom `div` elements must be used for complex UI interactions, ensure the full suite of ARIA attributes, focus management, and keyboard handlers are implemented.

## 2024-03-24 - Native Button Reset Patterns
**Learning:** When replacing interactive `div` or `span` elements with native `<button>` elements in existing UIs, it is crucial to explicitly reset their default styling (e.g., `appearance: none; background: transparent; border: none; padding: 0; text-align: left; color: inherit; font-family: inherit;`) to maintain visual consistency while gaining native keyboard accessibility and focus management.
**Action:** Always prefer native `<button>` tags for clickable list items or breadcrumbs, combined with CSS resets and explicit `:focus-visible` outlines.
