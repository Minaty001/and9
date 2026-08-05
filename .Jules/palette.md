## 2024-03-24 - Interactive Div Accessibility
**Learning:** Custom `div` elements used as interactive components (like the orbCore button) require complete semantic setup to be accessible. This includes `role="button"`, `tabindex="0"`, `:focus-visible` styles, and keyboard event handlers for both `Enter` and `Space` keys to match native button behavior.
**Action:** Always use native `<button>` elements when possible. When custom `div` elements must be used for complex UI interactions, ensure the full suite of ARIA attributes, focus management, and keyboard handlers are implemented.
## 2024-03-24 - Admin Focus Visibility
**Learning:** In the Jarvis admin panel (admin.html), buttons lacked explicit `:focus-visible` states, falling back to default browser behavior which was difficult to see against the dark background.
**Action:** When adding new interactive elements to the admin portal, always explicitly define a `:focus-visible` state using the theme color `#FFA500` (e.g., `outline: 2px solid #FFA500; outline-offset: 2px;`) to ensure keyboard accessibility.
