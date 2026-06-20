package com.jarvis.assistant.voice

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Log
import java.util.Locale
import java.util.UUID

/**
 * JarvisTts — Android TextToSpeech wrapper.
 *
 * Uses en-IN locale (Indian English) to match the Hinglish style of responses.
 * Speaks at 1.2x rate (matching web client setting).
 * Calls [onDone] when utterance finishes (to trigger next listen cycle).
 */
class JarvisTts(context: Context) {

    companion object {
        private const val TAG = "JarvisTts"
        private const val SPEECH_RATE = 1.2f
        private const val PITCH       = 1.0f
    }

    private var tts: TextToSpeech? = null
    private var isReady = false
    private var pendingText: String? = null
    private var pendingCallback: (() -> Unit)? = null

    init {
        tts = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                val result = tts?.setLanguage(Locale("hi", "IN"))
                if (result == TextToSpeech.LANG_MISSING_DATA ||
                    result == TextToSpeech.LANG_NOT_SUPPORTED) {
                    // Fallback to en-IN
                    tts?.language = Locale("en", "IN")
                }
                tts?.setSpeechRate(SPEECH_RATE)
                tts?.setPitch(PITCH)
                isReady = true
                Log.d(TAG, "TTS initialized")

                // Speak any pending text
                pendingText?.let { speak(it, pendingCallback ?: {}) }
                pendingText = null
                pendingCallback = null
            } else {
                Log.e(TAG, "TTS init failed: $status")
            }
        }
    }

    /**
     * Speak [text] and call [onDone] when finished.
     */
    fun speak(text: String, onDone: () -> Unit) {
        if (!isReady) {
            pendingText = text
            pendingCallback = onDone
            return
        }

        val uttId = UUID.randomUUID().toString()
        tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) {}
            override fun onDone(utteranceId: String?) {
                if (utteranceId == uttId) onDone()
            }
            override fun onError(utteranceId: String?) {
                if (utteranceId == uttId) onDone()
            }
        })

        // Trim to 500 chars max to keep responses snappy
        val trimmed = if (text.length > 500) text.take(497) + "..." else text

        tts?.speak(trimmed, TextToSpeech.QUEUE_FLUSH, null, uttId)
    }

    fun stop() {
        tts?.stop()
    }

    fun shutdown() {
        tts?.stop()
        tts?.shutdown()
        tts = null
        isReady = false
    }
}
