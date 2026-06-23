package com.jarvis.assistant.services

import android.content.Context
import android.content.ComponentName
import android.provider.Settings
import android.service.voice.VoiceInteractionService
import android.util.Log

/**
 * JarvisVoiceInteractionService
 *
 * Entry point that Android binds when JARVIS is selected
 * as the default Digital Assistant App.
 *
 * Required manifest config:
 *   - BIND_VOICE_INTERACTION permission
 *   - Intent-filter for VoiceInteractionService
 *   - Meta-data pointing to @xml/voice_interaction
 *
 * Invocation methods (all Android 10+ devices):
 *   - Long press power button
 *   - Swipe from corner gesture
 *   - Assistant shortcut in launcher
 *   - Settings → Apps → Default Apps → Digital Assistant App
 */
class JarvisVoiceInteractionService : VoiceInteractionService() {

    companion object {
        private const val TAG = "JarvisVoice"
        
        @JvmStatic
        @Volatile
        var activeInstance: JarvisVoiceInteractionService? = null

        /**
         * Check if JARVIS is set as the system default assistant.
         */
        fun isDefaultAssistant(context: Context): Boolean {
            val componentName = ComponentName(context, JarvisVoiceInteractionService::class.java)
            val current = Settings.Secure.getString(
                context.contentResolver,
                "voice_interaction_service"
            )
            return current?.contains(componentName.flattenToShortString()) ?: false
        }
    }

    override fun onReady() {
        super.onReady()
        activeInstance = this
        Log.i(TAG, "JARVIS assistant service registered and ready")
    }

    override fun onDestroy() {
        if (activeInstance === this) {
            activeInstance = null
        }
        super.onDestroy()
    }
}
