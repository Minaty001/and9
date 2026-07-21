## 2024-05-18 - Making Custom UI Elements Accessible
**Learning:** Custom interactive elements like the central JARVIS orb look clickable visually but are invisible to screen readers and keyboard users because they use standard `div` tags without semantics.
**Action:** Always add `role="button"`, `tabindex="0"`, an `aria-label`, and `keydown` support for `Enter`/`Space` to custom `div` interactives to ensure full accessibility.
