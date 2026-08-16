## 2024-03-24 - Interactive Div Accessibility
**Learning:** Custom `div` elements used as interactive components (like the orbCore button) require complete semantic setup to be accessible. This includes `role="button"`, `tabindex="0"`, `:focus-visible` styles, and keyboard event handlers for both `Enter` and `Space` keys to match native button behavior.
**Action:** Always use native `<button>` elements when possible. When custom `div` elements must be used for complex UI interactions, ensure the full suite of ARIA attributes, focus management, and keyboard handlers are implemented.

## 2026-08-16 - File Explorer Accessibility
**Learning:** The file explorer in the admin portal used interactive `div` and `span` elements without proper keyboard accessibility. Converting them to native `<button type="button">` with CSS resets (`appearance: none`, etc.) provides built-in keyboard navigation and focus management, removing the need for custom ARIA roles and keydown listeners.
**Action:** Always prefer native `<button>` elements for interactive UI components like file list items and breadcrumbs. Apply CSS resets to maintain design consistency and explicitly define `:focus-visible` styles to ensure focus states are visible for keyboard users.
