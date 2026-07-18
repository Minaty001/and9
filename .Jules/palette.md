## 2026-07-18 - Adding Keyboard/Screen Reader A11y to Custom UI Components
**Learning:** Using highly stylized `div` elements for core interactions (like the glowing orb) requires manual semantic roles, tab indexing, and keyboard event handlers to ensure they are accessible to screen reader or keyboard-only users.
**Action:** Add `role="button"`, `tabindex="0"`, and `aria-label` alongside a `keydown` listener (Enter/Space) and a `:focus-visible` CSS rule to all custom interactive `div` elements going forward.
