
## 2024-10-25 - Focus Management and Unstyled Buttons
**Learning:** Found an unstyled `.text-btn` in the right panel header, and many interactive elements lacked keyboard-friendly focus indicators. It's common in this app's components to lack unified focus styles for native interactive elements.
**Action:** When adding or auditing interactive components, ensure explicit `:focus-visible` rules are applied, utilizing `--accent-blue` with `outline-offset` to avoid clipping.
