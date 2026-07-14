## 2024-07-14 - Keyboard Accessibility and Icon Buttons in Main Interface
**Learning:** Found that the primary interaction buttons on the main interface (like the send command button and timer buttons) lacked proper ARIA labels and `:focus-visible` styles, making keyboard navigation difficult and screen readers unable to interpret the icon-only send button.
**Action:** Always verify keyboard focus states (`:focus-visible`) and ensure icon-only buttons have descriptive `aria-label`s and `aria-hidden="true"` on their SVGs to improve accessibility.
