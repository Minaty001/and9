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

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        Log.i(TAG, "Accessibility service connected")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // We don't need to react to events — this is an action-only service
    }

    override fun onInterrupt() {
        Log.d(TAG, "Accessibility service interrupted")
    }

    override fun onDestroy() {
        super.onDestroy()
        instance = null
        Log.i(TAG, "Accessibility service destroyed")
    }

    /**
     * Handle key events (optional — for power button detection).
     */
    override fun onKeyEvent(event: KeyEvent): Boolean {
        return super.onKeyEvent(event)
    }
}
