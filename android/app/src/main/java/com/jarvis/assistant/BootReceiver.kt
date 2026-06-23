package com.jarvis.assistant

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import com.jarvis.assistant.services.ContinuousListeningService

/**
 * BootReceiver
 *
 * Receives the BOOT_COMPLETED broadcast and starts the [ContinuousListeningService]
 * to ensure background listening is active immediately after system startup.
 */
class BootReceiver : BroadcastReceiver() {
    companion object {
        private const val TAG = "JarvisBootReceiver"
    }

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            Log.i(TAG, "Device boot completed. Starting JARVIS continuous listening service...")
            ContinuousListeningService.start(context)
        }
    }
}
