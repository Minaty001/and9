## 2024-05-25 - Essential Native Button Resets and ARIA Labels
**Learning:** Discovered that native button `<button>` elements (like `.text-btn`) lacked CSS resets and `:focus-visible` styles, leading to invisible keyboard navigation. Additionally, icon-only modal close buttons lacked ARIA labels.
**Action:** Implemented a global `:focus-visible` rule for interactive elements and provided standard CSS resets for `.text-btn` while maintaining focus visibility. Always verify ARIA labels on icon-only buttons.
