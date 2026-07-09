## 2024-07-09 - Making custom interactive divs accessible
**Learning:** When using custom `div` elements as buttons with click listeners, they completely fail for keyboard and screen reader users unless specifically engineered for accessibility.
**Action:** Always add `role="button"`, `tabindex="0"`, `aria-label`, and explicit keydown listeners (for 'Enter' and 'Space') to `div` elements that act as buttons. Combine this with `:focus-visible` CSS to ensure a complete accessible experience.
