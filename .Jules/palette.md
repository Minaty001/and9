## 2024-08-24 - Missing focus states and ARIA labels in custom webapp UI
**Learning:** Native `<button>` elements that rely solely on class-based custom styling without global `:focus-visible` definitions lose accessibility for keyboard navigation. Icon-only functional buttons also missed ARIA labels, rendering them inaccessible to screen readers.
**Action:** Ensure all interactive elements have `:focus-visible` definitions with proper outline/outline-offset in base CSS, and ensure all icon-only action buttons get explicit `aria-label` attributes.
