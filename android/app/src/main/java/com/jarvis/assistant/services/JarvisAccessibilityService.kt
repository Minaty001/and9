package com.jarvis.assistant.services

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.content.Intent
import android.content.Context
import android.content.ClipboardManager
import android.content.ClipData
import android.media.AudioManager
import android.os.PowerManager
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
 *   - Go to Home screen
 *   - Close any app
 *   - Click on UI elements by text
 *   - Open Quick Settings
 *   - Navigate back
 *   - Clipboard read/write
 *   - System media playback control (Play/Pause, Next, Prev)
 *   - Screen state checking
 *   - Passive notification capture
 */
class JarvisAccessibilityService : AccessibilityService() {

    companion object {
        private const val TAG = "JarvisAccessibility"

        @Volatile
        var instance: JarvisAccessibilityService? = null
            private set

        @Volatile
        var currentPackageName: String = "unknown"
            private set

        @Volatile
        var lastNotificationText: String = ""
            private set

        /**
         * Perform an accessibility action. Returns true if the action
         * was dispatched successfully.
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
                "media_play_pause" -> {
                    sendMediaKeyEvent(service, KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE)
                    true
                }
                "media_next" -> {
                    sendMediaKeyEvent(service, KeyEvent.KEYCODE_MEDIA_NEXT)
                    true
                }
                "media_prev" -> {
                    sendMediaKeyEvent(service, KeyEvent.KEYCODE_MEDIA_PREVIOUS)
                    true
                }
                else -> {
                    Log.w(TAG, "Unknown accessibility action: $action")
                    false
                }
            }
        }

        private fun sendMediaKeyEvent(service: JarvisAccessibilityService, keyCode: Int) {
            try {
                val audioManager = service.getSystemService(Context.AUDIO_SERVICE) as AudioManager
                val eventDown = KeyEvent(KeyEvent.ACTION_DOWN, keyCode)
                val eventUp = KeyEvent(KeyEvent.ACTION_UP, keyCode)
                audioManager.dispatchMediaKeyEvent(eventDown)
                audioManager.dispatchMediaKeyEvent(eventUp)
            } catch (e: Exception) {
                Log.e(TAG, "Failed to send media key event: ${e.message}")
            }
        }

        /**
         * Read the contents of the system clipboard.
         */
        fun readClipboard(): String {
            val service = instance ?: return ""
            var text = ""
            try {
                val clipboard = service.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                val primaryClip = clipboard.primaryClip
                if (primaryClip != null && primaryClip.itemCount > 0) {
                    text = primaryClip.getItemAt(0).text?.toString() ?: ""
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error reading clipboard: ${e.message}")
            }
            return text
        }

        /**
         * Write a text string to the system clipboard.
         */
        fun writeClipboard(text: String): Boolean {
            val service = instance ?: return false
            try {
                val clipboard = service.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                val clip = ClipData.newPlainText("Jarvis", text)
                clipboard.setPrimaryClip(clip)
                return true
            } catch (e: Exception) {
                Log.e(TAG, "Error writing clipboard: ${e.message}")
                return false
            }
        }

        /**
         * Check if the screen is currently interactive (on).
         */
        fun isScreenOn(): Boolean {
            val service = instance ?: return false
            return try {
                val pm = service.getSystemService(Context.POWER_SERVICE) as PowerManager
                pm.isInteractive
            } catch (e: Exception) {
                false
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
        if (event == null) return

        if (event.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) {
            val pkg = event.packageName?.toString()
            if (!pkg.isNullOrEmpty()) {
                currentPackageName = pkg
            }
        } else if (event.eventType == AccessibilityEvent.TYPE_NOTIFICATION_STATE_CHANGED) {
            val notificationText = StringBuilder()
            event.text?.forEach {
                notificationText.append(it).append(" ")
            }
            val pkg = event.packageName?.toString() ?: "unknown"
            if (notificationText.isNotEmpty()) {
                lastNotificationText = "[$pkg] ${notificationText.toString().trim()}"
                Log.d(TAG, "Captured notification: $lastNotificationText")
            }
        }
    }

    override fun onInterrupt() {
        Log.d(TAG, "Accessibility service interrupted")
    }

    override fun onDestroy() {
        super.onDestroy()
        instance = null
        Log.i(TAG, "Accessibility service destroyed")
    }

    override fun onKeyEvent(event: KeyEvent): Boolean {
        return super.onKeyEvent(event)
    }
}
