## 2024-03-24 - Interactive Div Accessibility
**Learning:** Custom `div` elements used as interactive components (like the orbCore button) require complete semantic setup to be accessible. This includes `role="button"`, `tabindex="0"`, `:focus-visible` styles, and keyboard event handlers for both `Enter` and `Space` keys to match native button behavior.
**Action:** Always use native `<button>` elements when possible. When custom `div` elements must be used for complex UI interactions, ensure the full suite of ARIA attributes, focus management, and keyboard handlers are implemented.
## 2024-08-04 - Native Button Focus Styles
**Learning:** When refactoring custom div components into native `<button>` elements, be careful not to remove the existing custom `:focus-visible` styles. While browsers provide default focus rings, custom styles are necessary to maintain visual consistency and appropriate contrast within the application's specific design theme.
**Action:** Always preserve the element's existing custom `:focus-visible` CSS rules when replacing an ARIA role setup with a native button.
