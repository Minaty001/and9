## 2024-07-21 - Interactive Semantic Elements
**Learning:** Adding interactive behavior (like `addEventListener('click')`) to non-interactive semantic elements like `<div>` makes them inaccessible to screen readers and keyboard users.
**Action:** When turning non-interactive elements into buttons or actionable controls, always add `role="button"`, `tabindex="0"`, `aria-label`, and a keyboard event listener (to handle 'Enter' and 'Space') to ensure full accessibility. Also include a `:focus-visible` CSS rule for visual feedback during keyboard navigation.
