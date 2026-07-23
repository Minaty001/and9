package com.jarvis.assistant.services

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.content.Intent
import android.graphics.Path
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.view.KeyEvent
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

/**
 * JarvisAccessibilityService
 *
 * Provides system-level capabilities that require accessibility access:
 *
 *   - Go to Home screen
 *   - Close any app (by injecting back gesture then home)
 *   - Click on UI elements by text
 *   - Open Quick Settings
 *   - Navigate back
 *
 * Phase 1+2 additions:
 *   - Screen state tracking (current app, activity, content changes)
 *   - Screen content description (text summary of visible elements)
 *   - Element finding by text/description/id/class/index
 *   - Text input automation (ACTION_SET_TEXT)
 *   - Scroll gesture (forward/backward)
 *   - Accessibility focus navigation (next/previous)
 *   - Event monitoring (window changes, content changes)
 *
 * This service must be enabled by the user in:
 *   Settings → Accessibility → Installed Apps → JARVIS
 *
 * Once enabled, the assistant can perform these actions via
 * [JarvisAccessibilityService.performAction].
 *
 * The service is BOUND (not started as foreground) and runs silently
 * in the background until called.
 */
class JarvisAccessibilityService : AccessibilityService() {

    companion object {
        private const val TAG = "JarvisAccessibility"

        @Volatile
        var instance: JarvisAccessibilityService? = null
            private set

        // ── Screen State Tracking (Phase 1) ────────────────────────

        /** Package name of the current foreground app. */
        @Volatile
        var currentAppPackage: String? = null
            private set

        /** Class name of the current activity. */
        @Volatile
        var currentActivity: String? = null
            private set

        /** Timestamp of last processed accessibility event (debounce). */
        private var lastEventTime = 0L

        /** Debounce interval in ms — skip events that arrive too fast. */
        private const val EVENT_DEBOUNCE_MS = 200L

        /** Cached screen description, recomputed on window change. */
        @Volatile
        private var cachedScreenDescription: String? = null
        private var screenDescriptionDirty = true

        // ── Public API: Screen State ───────────────────────────────

        /**
         * Returns the package name of the current foreground app,
         * or null if unknown.
         */
        fun getCurrentApp(): String? = currentAppPackage

        /**
         * Returns a text summary of the current screen contents.
         * Walks the active window's node tree and collects:
         *   - Visible text labels
         *   - Button/action text
         *   - Input field hints
         *   - Content descriptions
         * Result is cached and invalidated on window/content changes.
         */
        fun describeScreen(): String {
            if (!screenDescriptionDirty && cachedScreenDescription != null) {
                return cachedScreenDescription!!
            }
            val service = instance ?: return "Accessibility service not connected."
            val root = service.rootInActiveWindow ?: return "No active window found."

            val parts = mutableListOf<String>()
            try {
                // Collect package context
                if (currentAppPackage != null) {
                    parts.add("App: $currentAppPackage")
                }

                // Collect all visible text and descriptions
                val texts = mutableListOf<String>()
                val buttons = mutableListOf<String>()
                val inputs = mutableListOf<String>()
                val descriptions = mutableListOf<String>()

                collectVisibleElements(root, texts, buttons, inputs, descriptions)

                if (buttons.isNotEmpty()) {
                    parts.add("Buttons: ${buttons.joinToString(", ")}")
                }
                if (texts.isNotEmpty()) {
                    parts.add("Text: ${texts.joinToString(", ")}")
                }
                if (inputs.isNotEmpty()) {
                    parts.add("Inputs: ${inputs.joinToString(", ")}")
                }
                if (descriptions.isNotEmpty()) {
                    parts.add("Descriptions: ${descriptions.joinToString(", ")}")
                }
            } catch (e: Exception) {
                Log.e(TAG, "describeScreen error: ${e.message}")
            } finally {
                root.recycle()
            }

            val result = if (parts.isEmpty()) "Empty screen." else parts.joinToString("\n")
            cachedScreenDescription = result
            screenDescriptionDirty = false
            return result
        }

        /**
         * Recursively collect visible UI element info from the node tree.
         */
        private fun collectVisibleElements(
            node: AccessibilityNodeInfo,
            texts: MutableList<String>,
            buttons: MutableList<String>,
            inputs: MutableList<String>,
            descriptions: MutableList<String>
        ) {
            if (node == null) return

            try {
                val isVisible = node.isVisibleToUser
                if (!isVisible) return

                val className = node.className?.toString() ?: ""
                val text = node.text?.toString()?.takeIf { it.isNotBlank() }
                val desc = node.contentDescription?.toString()?.takeIf { it.isNotBlank() }

                val isButton = className.contains("Button", ignoreCase = true)
                        || className.contains("ImageButton", ignoreCase = true)
                        || node.isClickable
                val isInput = className.contains("EditText", ignoreCase = true)
                        || className.contains("AutoComplete", ignoreCase = true)
                        || node.isEditable
                val isText = className.contains("TextView", ignoreCase = true)
                        || className.contains("Text", ignoreCase = true)

                if (isButton && text != null && text !in buttons) {
                    buttons.add(text)
                } else if (isInput) {
                    val hint = node.hintText?.toString()?.takeIf { it.isNotBlank() }
                            ?: text ?: "(input field)"
                    if (hint !in inputs) inputs.add(hint)
                } else if (isText && text != null && text !in texts) {
                    texts.add(text)
                }

                if (desc != null && desc !in descriptions) {
                    descriptions.add(desc)
                }

                // Recurse children
                for (i in 0 until node.childCount) {
                    val child = node.getChild(i)
                    if (child != null) {
                        collectVisibleElements(child, texts, buttons, inputs, descriptions)
                        child.recycle()
                    }
                }
            } catch (e: Exception) {
                Log.w(TAG, "collectVisibleElements error: ${e.message}")
            }
        }

        // ── Public API: Element Finding (Phase 2) ──────────────────

        /**
         * Find a UI element matching the given selectors.
         *
         * Supported keys in [selector]:
         *   "text"        — node.text contains this string (case-insensitive)
         *   "description" — node.contentDescription contains this string
         *   "id"          — node.viewIdResourceName ends with this string
         *   "className"   — node.className contains this string
         *   "index"       — nth matching element (0-based), default 0
         *
         * Returns the first matching node, or null. Caller must recycle().
         */
        fun findElement(selector: Map<String, String>): AccessibilityNodeInfo? {
            val service = instance ?: return null
            val root = service.rootInActiveWindow ?: return null

            val textFilter = selector["text"]
            val descFilter = selector["description"]
            val idFilter = selector["id"]
            val classFilter = selector["className"]
            val targetIndex = selector["index"]?.toIntOrNull() ?: 0

            val matches = mutableListOf<AccessibilityNodeInfo>()
            try {
                findMatchingNodes(root, textFilter, descFilter, idFilter, classFilter, matches)
                return if (targetIndex < matches.size) {
                    matches[targetIndex]
                } else {
                    null
                }
            } catch (e: Exception) {
                Log.e(TAG, "findElement error: ${e.message}")
                // Recycle unmatched matches on error
                for (m in matches) {
                    try { m.recycle() } catch (_: Exception) {}
                }
                return null
            } finally {
                root.recycle()
            }
        }

        private fun findMatchingNodes(
            node: AccessibilityNodeInfo,
            textFilter: String?,
            descFilter: String?,
            idFilter: String?,
            classFilter: String?,
            results: MutableList<AccessibilityNodeInfo>
        ) {
            if (node == null) return
            try {
                var match = true
                if (textFilter != null) {
                    val nodeText = node.text?.toString() ?: ""
                    match = match && nodeText.contains(textFilter, ignoreCase = true)
                }
                if (descFilter != null) {
                    val nodeDesc = node.contentDescription?.toString() ?: ""
                    match = match && nodeDesc.contains(descFilter, ignoreCase = true)
                }
                if (idFilter != null) {
                    val nodeId = node.viewIdResourceName ?: ""
                    match = match && nodeId.endsWith(idFilter)
                }
                if (classFilter != null) {
                    val nodeClass = node.className?.toString() ?: ""
                    match = match && nodeClass.contains(classFilter, ignoreCase = true)
                }
                if (match) {
                    // Clone the node for external use (so recycling the tree doesn't break it)
                    val clone = AccessibilityNodeInfo.obtain(node)
                    results.add(clone)
                }

                for (i in 0 until node.childCount) {
                    val child = node.getChild(i)
                    if (child != null) {
                        findMatchingNodes(child, textFilter, descFilter, idFilter, classFilter, results)
                        child.recycle()
                    }
                }
            } catch (e: Exception) {
                Log.w(TAG, "findMatchingNodes error: ${e.message}")
            }
        }

        /**
         * Click a UI element matching the given selectors.
         * Returns true if found and clicked.
         *
         * If the matching node is not directly clickable, walks up to
         * find a clickable parent.
         */
        fun clickElement(selector: Map<String, String>): Boolean {
            var node = findElement(selector) ?: return false
            try {
                if (node.isClickable) {
                    return node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                }
                // Walk up to find clickable parent
                var parent = node.parent
                while (parent != null) {
                    if (parent.isClickable) {
                        val clicked = parent.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                        parent.recycle()
                        return clicked
                    }
                    val p = parent.parent
                    parent.recycle()
                    parent = p
                }
                return false
            } catch (e: Exception) {
                Log.e(TAG, "clickElement error: ${e.message}")
                return false
            } finally {
                node.recycle()
            }
        }

        /**
         * Type [text] into a UI element matching the given selectors.
         * Uses [AccessibilityNodeInfo.ACTION_SET_TEXT] (API 21+, minSdk 29 → safe).
         * Falls back to focusing then pasting if SET_TEXT unavailable.
         *
         * Returns true if the text was sent successfully.
         */
        fun typeText(selector: Map<String, String>, text: String): Boolean {
            var node = findElement(selector) ?: return false
            try {
                // First ensure the node is focused
                node.performAction(AccessibilityNodeInfo.ACTION_FOCUS)

                // Use SET_TEXT on API 21+ (ours is minSdk 29)
                val args = Bundle().apply {
                    putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text)
                }
                return node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
            } catch (e: Exception) {
                Log.e(TAG, "typeText error: ${e.message}")
                return false
            } finally {
                node.recycle()
            }
        }

        /**
         * Scroll the current screen in the given [direction].
         * Supported values: "forward", "backward", "up", "down",
         * "neeche", "niche", "upar".
         *
         * Finds the first scrollable container and sends the scroll action.
         * Returns true if the scroll action was dispatched.
         */
        fun scroll(direction: String): Boolean {
            val service = instance ?: return false
            val root = service.rootInActiveWindow ?: return false

            val isForward = direction.lowercase() in listOf(
                "forward", "down", "neeche", "niche"
            )
            val action = if (isForward) {
                AccessibilityNodeInfo.ACTION_SCROLL_FORWARD
            } else {
                AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD
            }

            try {
                val scrollable = findScrollableContainer(root)
                if (scrollable != null) {
                    return scrollable.performAction(action)
                }
                return false
            } catch (e: Exception) {
                Log.e(TAG, "scroll error: ${e.message}")
                return false
            } finally {
                root.recycle()
            }
        }

        private fun findScrollableContainer(node: AccessibilityNodeInfo): AccessibilityNodeInfo? {
            if (node == null) return null
            try {
                if (node.isScrollable) {
                    return node
                }
                for (i in 0 until node.childCount) {
                    val child = node.getChild(i)
                    if (child != null) {
                        val result = findScrollableContainer(child)
                        if (result != null) {
                            child.recycle()
                            return result
                        }
                        child.recycle()
                    }
                }
            } catch (e: Exception) {
                Log.w(TAG, "findScrollableContainer error: ${e.message}")
            }
            return null
        }

        /**
         * Move accessibility focus to the next focusable element.
         * Returns true if focus was moved.
         */
        fun focusNext(): Boolean {
            val service = instance ?: return false
            return service.performGlobalAction(GLOBAL_ACTION_NEXT_TEXT)
                || service.performGlobalAction(GLOBAL_ACTION_NEXT_BUTTON)
        }

        /**
         * Move accessibility focus to the previous focusable element.
         * Returns true if focus was moved.
         */
        fun focusPrevious(): Boolean {
            val service = instance ?: return false
            return service.performGlobalAction(GLOBAL_ACTION_PREVIOUS_TEXT)
                || service.performGlobalAction(GLOBAL_ACTION_PREVIOUS_BUTTON)
        }

        // ── Existing Public API ───────────────────────────────────

        /**
         * Perform an accessibility action. Returns true if the action
         * was dispatched successfully.
         *
         * Supported actions:
         *   "home"         — Go to home screen
         *   "back"         — Navigate back
         *   "recents"      - Open recent apps
         *   "close_app"    - Close current app (back then home)
         *   "quick_settings" - Open quick settings
         *   "notifications" - Open notification shade
         *   "screenshot"   - Take screenshot (Android 9+)
         *   "scroll_forward" - Scroll down/forward
         *   "scroll_backward" - Scroll up/backward
         *   "focus_next"   - Next focusable element
         *   "focus_previous" - Previous focusable element
         */
        fun performAction(action: String): Boolean {
            val service = instance ?: run {
                Log.w(TAG, "Accessibility service not bound")
                return false
            }

            return when (action) {
                "home" -> {
                    service.performGlobalAction(GLOBAL_ACTION_HOME)
                    true
                }
                "back" -> {
                    service.performGlobalAction(GLOBAL_ACTION_BACK)
                    true
                }
                "recents" -> {
                    service.performGlobalAction(GLOBAL_ACTION_RECENTS)
                    true
                }
                "close_app" -> {
                    // Close the current app by going back then home
                    service.performGlobalAction(GLOBAL_ACTION_BACK)
                    Thread.sleep(150)
                    service.performGlobalAction(GLOBAL_ACTION_HOME)
                    true
                }
                "quick_settings" -> {
                    service.performGlobalAction(GLOBAL_ACTION_QUICK_SETTINGS)
                    true
                }
                "notifications" -> {
                    service.performGlobalAction(GLOBAL_ACTION_NOTIFICATIONS)
                    true
                }
                "screenshot" -> {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                        service.performGlobalAction(GLOBAL_ACTION_TAKE_SCREENSHOT)
                    } else {
                        false
                    }
                }
                "scroll_forward" -> scroll("forward")
                "scroll_backward" -> scroll("backward")
                "focus_next" -> focusNext()
                "focus_previous" -> focusPrevious()
                else -> {
                    Log.w(TAG, "Unknown accessibility action: $action")
                    false
                }
            }
        }

        /**
         * Find a clickable node on screen containing the given text
         * and click it. Returns true if found and clicked.
         */
        fun clickText(text: String): Boolean {
            val service = instance ?: return false
            val root = service.rootInActiveWindow ?: return false
            try {
                return findAndClick(root, text)
            } finally {
                root.recycle()
            }
        }

        private fun findAndClick(node: AccessibilityNodeInfo, text: String): Boolean {
            if (node.text?.toString()?.contains(text, ignoreCase = true) == true
                || node.contentDescription?.toString()?.contains(text, ignoreCase = true) == true) {
                if (node.isClickable) {
                    node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                    return true
                }
            }
            // Check if parent is clickable
            var parent = node.parent
            while (parent != null) {
                if (parent.isClickable && (parent.text?.toString()?.contains(text, ignoreCase = true) == true
                        || parent.contentDescription?.toString()?.contains(text, ignoreCase = true) == true)) {
                    parent.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                    parent.recycle()
                    return true
                }
                val p = parent.parent
                parent.recycle()
                parent = p
            }
            // Recurse into children
            for (i in 0 until node.childCount) {
                val child = node.getChild(i)
                if (child != null) {
                    if (findAndClick(child, text)) {
                        child.recycle()
                        return true
                    }
                    child.recycle()
                }
            }
            return false
        }
    }

    // ── Service Lifecycle ─────────────────────────────────────────

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        Log.i(TAG, "Accessibility service connected")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) return

        // Debounce rapid events
        val now = System.currentTimeMillis()
        if (now - lastEventTime < EVENT_DEBOUNCE_MS) return
        lastEventTime = now

        try {
            when (event.eventType) {
                AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED -> {
                    // Track foreground app and activity
                    val pkg = event.packageName?.toString()
                    val cls = event.className?.toString()

                    if (pkg != null && pkg != currentAppPackage) {
                        Log.d(TAG, "App changed: $pkg")
                        currentAppPackage = pkg
                        screenDescriptionDirty = true
                    }
                    if (cls != null && cls != currentActivity) {
                        currentActivity = cls
                        screenDescriptionDirty = true
                    }
                }
                AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED -> {
                    // Content changed — invalidate screen description cache
                    screenDescriptionDirty = true
                }
                AccessibilityEvent.TYPE_VIEW_CLICKED -> {
                    // Something was clicked — screen may have changed
                    screenDescriptionDirty = true
                }
                AccessibilityEvent.TYPE_VIEW_SCROLLED -> {
                    // Scrolling happened — don't invalidate, but mark potentially stale
                    screenDescriptionDirty = true
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "onAccessibilityEvent error: ${e.message}")
        }
    }

    override fun onInterrupt() {
        Log.d(TAG, "Accessibility service interrupted")
    }

    override fun onDestroy() {
        super.onDestroy()
        instance = null
        currentAppPackage = null
        currentActivity = null
        cachedScreenDescription = null
        Log.i(TAG, "Accessibility service destroyed")
    }

    /**
     * Handle key events (optional — for power button detection).
     */
    override fun onKeyEvent(event: KeyEvent): Boolean {
        return super.onKeyEvent(event)
    }
}
