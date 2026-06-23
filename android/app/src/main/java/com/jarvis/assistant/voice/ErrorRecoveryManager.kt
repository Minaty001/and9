package com.jarvis.assistant.voice

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.speech.SpeechRecognizer
import android.util.Log

/**
 * ErrorRecoveryManager
 *
 * Centralized error recovery system for all JARVIS subsystems.
 * Implements exponential backoff retry with state machine:
 *
 *   HEALTHY → DEGRADED → RECOVERING → HEALTHY
 *                    ↘              ↗
 *                      CRITICAL
 *
 * Handles:
 *   - STT (SpeechRecognizer) crash/hang
 *   - TTS (TextToSpeech) failure
 *   - API / network failure with retry
 *   - Accessibility service disconnection
 *   - Browser/intent failure
 */
class ErrorRecoveryManager(private val context: Context) {

    companion object {
        private const val TAG = "JarvisRecovery"
        private const val MAX_API_RETRIES = 3
        private const val BASE_BACKOFF_MS = 1000L
        private const val MAX_BACKOFF_MS = 30_000L
    }

    enum class SubsystemState {
        HEALTHY, DEGRADED, RECOVERING, CRITICAL
    }

    data class SubsystemStatus(
        val name: String,
        var state: SubsystemState = SubsystemState.HEALTHY,
        var failureCount: Int = 0,
        var lastFailureMs: Long = 0L,
        var lastRecoveryMs: Long = 0L,
        var totalRecoveries: Int = 0
    )

    private val subsystems = mutableMapOf(
        "stt"           to SubsystemStatus("STT"),
        "tts"           to SubsystemStatus("TTS"),
        "api"           to SubsystemStatus("API"),
        "accessibility" to SubsystemStatus("Accessibility"),
        "browser"       to SubsystemStatus("Browser")
    )

    private val handler = Handler(Looper.getMainLooper())

    // ── STT Recovery ───────────────────────────────────────────

    /**
     * Called when SpeechRecognizer crashes or produces unrecoverable error.
     * @param rebuilder Lambda that creates a fresh SpeechRecognizer
     */
    fun recoverStt(
        errorCode: Int,
        rebuilder: () -> Unit,
        onRecovered: () -> Unit = {},
        onFailed: () -> Unit = {}
    ) {
        val sub = subsystems["stt"]!!
        sub.failureCount++
        sub.lastFailureMs = System.currentTimeMillis()

        val backoff = calculateBackoff(sub.failureCount)
        Log.w(TAG, "STT error (code=$errorCode, failure #${sub.failureCount}) — retrying in ${backoff}ms")

        sub.state = SubsystemState.RECOVERING

        handler.postDelayed({
            try {
                rebuilder()
                sub.state = SubsystemState.HEALTHY
                sub.failureCount = 0
                sub.totalRecoveries++
                sub.lastRecoveryMs = System.currentTimeMillis()
                Log.i(TAG, "✅ STT recovered (total recoveries: ${sub.totalRecoveries})")
                onRecovered()
            } catch (e: Exception) {
                Log.e(TAG, "STT recovery failed: ${e.message}")
                sub.state = if (sub.failureCount >= 5) SubsystemState.CRITICAL else SubsystemState.DEGRADED
                onFailed()
            }
        }, backoff)
    }

    // ── TTS Recovery ───────────────────────────────────────────

    /**
     * Called when TextToSpeech engine fails.
     * @param reinitializer Lambda that reinitializes TTS
     */
    fun recoverTts(
        reinitializer: () -> Unit,
        onRecovered: () -> Unit = {},
        onFailed: () -> Unit = {}
    ) {
        val sub = subsystems["tts"]!!
        sub.failureCount++
        sub.lastFailureMs = System.currentTimeMillis()

        val backoff = calculateBackoff(sub.failureCount)
        Log.w(TAG, "TTS failure #${sub.failureCount} — reinitializing in ${backoff}ms")
        sub.state = SubsystemState.RECOVERING

        handler.postDelayed({
            try {
                reinitializer()
                sub.state = SubsystemState.HEALTHY
                sub.failureCount = 0
                sub.totalRecoveries++
                Log.i(TAG, "✅ TTS recovered")
                onRecovered()
            } catch (e: Exception) {
                Log.e(TAG, "TTS recovery failed: ${e.message}")
                sub.state = SubsystemState.DEGRADED
                onFailed()
            }
        }, backoff)
    }

    // ── API Recovery ───────────────────────────────────────────

    /**
     * Retry an API call with exponential backoff.
     * @param attempt Current attempt number (1-indexed)
     * @param call    Lambda to execute the API call
     * @param onSuccess Called with the successful result
     * @param onExhausted Called when all retries are exhausted
     */
    fun <T> retryApiCall(
        attempt: Int,
        call: () -> T,
        onSuccess: (T) -> Unit,
        onExhausted: (Exception) -> Unit
    ) {
        val sub = subsystems["api"]!!

        if (attempt > MAX_API_RETRIES) {
            sub.state = SubsystemState.DEGRADED
            Log.e(TAG, "API: All $MAX_API_RETRIES retries exhausted")
            onExhausted(Exception("Max retries ($MAX_API_RETRIES) exhausted"))
            return
        }

        val backoff = if (attempt == 1) 0L else calculateBackoff(attempt - 1)
        Log.d(TAG, "API call attempt $attempt/$MAX_API_RETRIES (backoff=${backoff}ms)")

        handler.postDelayed({
            try {
                val result = call()
                sub.state = SubsystemState.HEALTHY
                sub.failureCount = 0
                sub.totalRecoveries++
                onSuccess(result)
            } catch (e: Exception) {
                sub.failureCount++
                sub.lastFailureMs = System.currentTimeMillis()
                Log.w(TAG, "API attempt $attempt failed: ${e.message}")
                // Recurse with next attempt
                retryApiCall(attempt + 1, call, onSuccess, onExhausted)
            }
        }, backoff)
    }

    // ── Accessibility Recovery ─────────────────────────────────

    /**
     * Called when accessibility service is not available.
     * Guides user to re-enable it.
     */
    fun handleAccessibilityFailure(onUserNotified: (String) -> Unit) {
        val sub = subsystems["accessibility"]!!
        sub.failureCount++
        sub.lastFailureMs = System.currentTimeMillis()

        val msg = when {
            sub.failureCount == 1 -> "Accessibility service disabled. Some features unavailable."
            sub.failureCount >= 3 -> "Please enable JARVIS in Settings → Accessibility to restore full control."
            else -> "Accessibility temporarily unavailable."
        }

        sub.state = SubsystemState.DEGRADED
        Log.w(TAG, "Accessibility failure #${sub.failureCount}: $msg")
        onUserNotified(msg)
    }

    /** Call when accessibility service reconnects. */
    fun onAccessibilityRestored() {
        val sub = subsystems["accessibility"]!!
        sub.state = SubsystemState.HEALTHY
        sub.failureCount = 0
        sub.totalRecoveries++
        Log.i(TAG, "✅ Accessibility service restored")
    }

    // ── Browser / Intent Recovery ──────────────────────────────

    /**
     * Fallback chain for browser/intent failures.
     * @param primary Primary intent launcher
     * @param fallback Fallback intent launcher
     */
    fun withBrowserFallback(
        primary: () -> Unit,
        fallback: () -> Unit,
        onAllFailed: () -> Unit = {}
    ) {
        val sub = subsystems["browser"]!!
        try {
            primary()
            sub.state = SubsystemState.HEALTHY
        } catch (e: Exception) {
            Log.w(TAG, "Primary browser action failed: ${e.message} — trying fallback")
            try {
                fallback()
                sub.state = SubsystemState.DEGRADED
            } catch (e2: Exception) {
                Log.e(TAG, "Fallback also failed: ${e2.message}")
                sub.state = SubsystemState.CRITICAL
                sub.failureCount++
                onAllFailed()
            }
        }
    }

    // ── Status ─────────────────────────────────────────────────

    /** Get current health status of all subsystems. */
    fun getStatus(): Map<String, String> =
        subsystems.mapValues { (_, v) -> "${v.state} (failures=${v.failureCount}, recoveries=${v.totalRecoveries})" }

    /** Returns true if the system is fully operational. */
    fun isHealthy(): Boolean =
        subsystems.values.none { it.state == SubsystemState.CRITICAL }

    /** Reset failure count for a subsystem (e.g., after manual user recovery). */
    fun resetSubsystem(name: String) {
        subsystems[name]?.let {
            it.state = SubsystemState.HEALTHY
            it.failureCount = 0
            Log.i(TAG, "Subsystem '$name' manually reset")
        }
    }

    // ── Helpers ────────────────────────────────────────────────

    private fun calculateBackoff(attempt: Int): Long {
        val backoff = BASE_BACKOFF_MS * (1L shl minOf(attempt - 1, 5)) // 2^(attempt-1) * base, capped
        return minOf(backoff, MAX_BACKOFF_MS)
    }
}
