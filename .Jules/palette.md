## 2024-05-18 - Dynamic Image Alt Text
**Learning:** When images are dynamically generated via JavaScript and injected into the DOM, it's easy to overlook `alt` tags, leading to screen reader inaccessible content.
**Action:** Always verify that dynamic HTML generation templates (e.g., using backticks in JS) include descriptive `alt` attributes for images, leveraging existing data properties like prompt text.
