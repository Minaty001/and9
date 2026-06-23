package com.jarvis.assistant.voice

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.speech.SpeechRecognizer
import android.util.Log

/**
 * ListeningWatchdog
 *
 * Monitors the health of the STT engine and triggers recovery when
 * the recognizer stops responding.
 *
 * Failure detection:
 *   - No onReadyForSpeech callback within [heartbeatIntervalMs]
 *   - 3+ consecutive errors
 *   - Recognizer not started after restartListener callback
 *
 * Recovery flow:
 *   HEALTHY → (no heartbeat) → DEGRADED → (restart) → RECOVERING → HEALTHY
 *   RECOVERING → (3 fails) → CRITICAL → (nuclear restart) → RECOVERING
 */
class ListeningWatchdog(
    private val context: Context,
    private val onRestartRequested: () -> Unit,
    private val onNuclearRestart: () -> Unit,
    private val onHealthChanged: (WatchdogHealth) -> Unit = {}
) {
    companion object {
        private const val TAG = "JarvisWatchdog"
        private const val HEARTBEAT_INTERVAL_MS = 30_000L    // 30 seconds
        private const val MAX_CONSECUTIVE_ERRORS = 5
        private const val MAX_RESTART_ATTEMPTS = 3
    }

    enum class WatchdogHealth {
        HEALTHY, DEGRADED, RECOVERING, CRITICAL
    }

    private val handler = Handler(Looper.getMainLooper())
    private var health = WatchdogHealth.HEALTHY
    private var consecutiveErrors = 0
    private var restartAttempts = 0
    private var lastHeartbeat = System.currentTimeMillis()
    private var isRunning = false

    // ── Heartbeat Runnable ─────────────────────────────────────

    private val heartbeatRunnable = object : Runnable {
        override fun run() {
            if (!isRunning) return

            val elapsed = System.currentTimeMillis() - lastHeartbeat
            Log.d(TAG, "Heartbeat check — last seen ${elapsed}ms ago, health=$health")

            if (elapsed > HEARTBEAT_INTERVAL_MS) {
                Log.w(TAG, "⚠️ Watchdog: No heartbeat for ${elapsed}ms — triggering recovery")
                triggerRecovery()
            }

            // Reschedule
            handler.postDelayed(this, HEARTBEAT_INTERVAL_MS)
        }
    }

    // ── Public API ─────────────────────────────────────────────

    /** Start monitoring. Call once when listening begins. */
    fun start() {
        if (isRunning) return
        isRunning = true
        lastHeartbeat = System.currentTimeMillis()
        handler.postDelayed(heartbeatRunnable, HEARTBEAT_INTERVAL_MS)
        Log.i(TAG, "Watchdog started — heartbeat every ${HEARTBEAT_INTERVAL_MS}ms")
    }

    /** Stop monitoring. Call when service is destroyed. */
    fun stop() {
        isRunning = false
        handler.removeCallbacks(heartbeatRunnable)
        Log.i(TAG, "Watchdog stopped")
    }

    /**
     * Call this whenever STT successfully becomes ready for speech.
     * Resets the heartbeat timer.
     */
    fun onListenerReady() {
        lastHeartbeat = System.currentTimeMillis()
        consecutiveErrors = 0
        restartAttempts = 0
        setHealth(WatchdogHealth.HEALTHY)
        Log.d(TAG, "❤️ Heartbeat — STT ready")
    }

    /**
     * Call this whenever STT produces a result (success).
     */
    fun onResult() {
        lastHeartbeat = System.currentTimeMillis()
        consecutiveErrors = 0
        setHealth(WatchdogHealth.HEALTHY)
    }

    /**
     * Call this on every STT error. Tracks consecutive failures.
     */
    fun onError(errorCode: Int) {
        consecutiveErrors++
        Log.w(TAG, "STT error #$consecutiveErrors (code=$errorCode)")

        if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
            Log.e(TAG, "🚨 $consecutiveErrors consecutive errors — triggering recovery")
            triggerRecovery()
        } else {
            setHealth(WatchdogHealth.DEGRADED)
        }
    }

    /**
     * Call when a restart was successfully initiated.
     */
    fun onRestartInitiated() {
        restartAttempts++
        setHealth(WatchdogHealth.RECOVERING)
        lastHeartbeat = System.currentTimeMillis() // Give it time to recover
        Log.i(TAG, "Recovery attempt #$restartAttempts initiated")
    }

    // ── Internal ───────────────────────────────────────────────

    private fun triggerRecovery() {
        consecutiveErrors = 0

        if (restartAttempts < MAX_RESTART_ATTEMPTS) {
            Log.w(TAG, "🔄 Watchdog: Requesting STT restart (attempt ${restartAttempts + 1}/$MAX_RESTART_ATTEMPTS)")
            setHealth(WatchdogHealth.RECOVERING)
            onRestartRequested()
        } else {
            Log.e(TAG, "💥 Watchdog: $MAX_RESTART_ATTEMPTS restarts failed — nuclear restart")
            restartAttempts = 0
            setHealth(WatchdogHealth.CRITICAL)
            onNuclearRestart()
        }
    }

    private fun setHealth(newHealth: WatchdogHealth) {
        if (health != newHealth) {
            Log.i(TAG, "Health: $health → $newHealth")
            health = newHealth
            onHealthChanged(newHealth)
        }
    }

    fun getHealth(): WatchdogHealth = health
    fun getConsecutiveErrors(): Int = consecutiveErrors
}
