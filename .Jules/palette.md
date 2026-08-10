## 2024-03-24 - Interactive Div Accessibility
**Learning:** Custom `div` elements used as interactive components (like the orbCore button) require complete semantic setup to be accessible. This includes `role="button"`, `tabindex="0"`, `:focus-visible` styles, and keyboard event handlers for both `Enter` and `Space` keys to match native button behavior.
**Action:** Always use native `<button>` elements when possible. When custom `div` elements must be used for complex UI interactions, ensure the full suite of ARIA attributes, focus management, and keyboard handlers are implemented.

## 2024-08-10 - Native Button Substitution in Lists
**Learning:** When building interactive lists like file browsers, it's common to mistakenly use generic `div` elements with click handlers. This breaks keyboard navigation and focus management for users navigating via `Tab`.
**Action:** Always replace interactive list items structured as `div`s with native `<button>` elements. Apply CSS resets (e.g., `appearance: none; background: transparent; width: 100%; text-align: left; border: none; padding: 0; font: inherit;`) and explicit `:focus-visible` styles to maintain the visual design while restoring built-in accessibility and tab order.
