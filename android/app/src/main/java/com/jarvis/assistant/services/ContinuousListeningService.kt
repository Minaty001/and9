package com.jarvis.assistant.services

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.ServiceInfo
import android.os.Binder
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.Log
import androidx.core.app.NotificationCompat
import com.jarvis.assistant.R
import com.jarvis.assistant.SetupActivity
import com.jarvis.assistant.voice.ErrorRecoveryManager
import com.jarvis.assistant.voice.ListeningWatchdog
import com.jarvis.assistant.voice.WakeWordDetector
import java.util.ArrayList

/**
 * ContinuousListeningService
 *
 * A foreground service that maintains a persistent SpeechRecognizer loop.
 * It coordinates wake word detection (background) and command transcription (foreground overlay).
 *
 * Implements:
 *   - Wake word filtering (via WakeWordDetector)
 *   - Watchdog heartbeat monitoring (via ListeningWatchdog)
 *   - Failure recovery with exponential backoff (via ErrorRecoveryManager)
 *   - Screen-state aware power saving (pauses when screen is off)
 *   - Partial wake lock to prevent CPU sleep during active listening
 */
class ContinuousListeningService : Service() {

    companion object {
        private const val TAG = "JarvisListeningService"
        private const val NOTIFICATION_ID = 9001
        private const val CHANNEL_ID = "jarvis_listening_channel"
        private const val ACTION_START = "com.jarvis.assistant.action.START"
        private const val ACTION_STOP = "com.jarvis.assistant.action.STOP"

        fun start(context: Context) {
            val intent = Intent(context, ContinuousListeningService::class.java).apply {
                action = ACTION_START
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            val intent = Intent(context, ContinuousListeningService::class.java).apply {
                action = ACTION_STOP
            }
            context.startService(intent)
        }
    }

    interface Callback {
        fun onReadyForSpeech()
        fun onBeginningOfSpeech()
        fun onRmsChanged(rmsdB: Float)
        fun onPartialResults(text: String)
        fun onResults(text: String)
        fun onError(errorCode: Int, errorMessage: String)
        fun onStatusChanged(status: String)
    }

    private val binder = LocalBinder()
    private var callback: Callback? = null

    private var recognizer: SpeechRecognizer? = null
    private val mainHandler = Handler(Looper.getMainLooper())
    private val wakeWordDetector = WakeWordDetector()
    private lateinit var watchdog: ListeningWatchdog
    private lateinit var recoveryManager: ErrorRecoveryManager

    private var isStarted = false
    private var isListening = false
    private var isCommandMode = false
    private var isScreenOn = true

    private var wakeLock: PowerManager.WakeLock? = null

    inner class LocalBinder : Binder() {
        fun getService(): ContinuousListeningService = this@ContinuousListeningService
    }

    override fun onBind(intent: Intent?): IBinder {
        Log.d(TAG, "Client bound to service")
        return binder
    }

    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "Service onCreate")

        // Setup wake lock
        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Jarvis::ListeningWakeLock")

        // Setup recovery managers
        recoveryManager = ErrorRecoveryManager(this)
        watchdog = ListeningWatchdog(
            context = this,
            onRestartRequested = {
                Log.w(TAG, "Watchdog requested restart — recreating recognizer")
                mainHandler.post { recreateRecognizerAndRestart() }
            },
            onNuclearRestart = {
                Log.e(TAG, "Watchdog requested nuclear restart — re-initializing fully")
                mainHandler.post {
                    stopListening()
                    recreateRecognizerAndRestart()
                }
            },
            onHealthChanged = { health ->
                Log.i(TAG, "System health updated: $health")
            }
        )

        // Register screen state receiver
        val filter = IntentFilter().apply {
            addAction(Intent.ACTION_SCREEN_ON)
            addAction(Intent.ACTION_SCREEN_OFF)
        }
        registerReceiver(screenReceiver, filter)

        // Check initial screen state
        isScreenOn = powerManager.isInteractive
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val action = intent?.action
        Log.d(TAG, "onStartCommand: action=$action")

        if (action == ACTION_STOP) {
            stopForeground(true)
            stopSelf()
            return START_NOT_STICKY
        }

        if (!isStarted) {
            isStarted = true
            createNotificationChannel()
            startForeground(
                NOTIFICATION_ID,
                buildNotification("JARVIS is active", "Continuous listening engine running"),
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
                } else {
                    0
                }
            )

            acquireWakeLock()
            watchdog.start()
            mainHandler.post { recreateRecognizerAndRestart() }
        }

        return START_STICKY
    }

    override fun onDestroy() {
        Log.d(TAG, "Service onDestroy")
        isStarted = false
        stopListening()
        watchdog.stop()
        releaseWakeLock()
        try {
            unregisterReceiver(screenReceiver)
        } catch (_: Exception) {}
        destroyRecognizer()
        super.onDestroy()
    }

    // ── Public Control API ──────────────────────────────────────

    fun registerCallback(cb: Callback) {
        this.callback = cb
        Log.d(TAG, "Callback registered")
    }

    fun unregisterCallback() {
        this.callback = null
        Log.d(TAG, "Callback unregistered")
    }

    fun setCommandMode(enabled: Boolean) {
        if (isCommandMode != enabled) {
            isCommandMode = enabled
            Log.d(TAG, "Mode changed: isCommandMode=$isCommandMode")
            // Restart listening under new mode parameters
            mainHandler.post { restartListening() }
        }
    }

    fun forceRestartListening() {
        mainHandler.post {
            stopListening()
            startListeningInternal()
        }
    }

    // ── Speech Recognizer Logic ─────────────────────────────────

    private fun recreateRecognizerAndRestart() {
        destroyRecognizer()
        if (!isScreenOn && !isCommandMode) {
            Log.d(TAG, "Screen off and not in command mode — skipping recognizer creation")
            return
        }
        try {
            Log.d(TAG, "Creating SpeechRecognizer instance")
            recognizer = SpeechRecognizer.createSpeechRecognizer(this).apply {
                setRecognitionListener(speechListener)
            }
            startListeningInternal()
        } catch (e: Exception) {
            Log.e(TAG, "Failed to create SpeechRecognizer", e)
            recoveryManager.recoverStt(SpeechRecognizer.ERROR_RECOGNIZER_BUSY, {
                recreateRecognizerAndRestart()
            })
        }
    }

    private fun destroyRecognizer() {
        try {
            recognizer?.setRecognitionListener(null)
            recognizer?.destroy()
        } catch (e: Exception) {
            Log.e(TAG, "Error destroying SpeechRecognizer", e)
        }
        recognizer = null
        isListening = false
    }

    private fun startListeningInternal() {
        if (isListening) return
        if (recognizer == null) {
            recreateRecognizerAndRestart()
            return
        }

        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "hi-IN") // Default to Hindi-English hybrid
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "hi-IN")
            putExtra(RecognizerIntent.EXTRA_ONLY_RETURN_LANGUAGE_PREFERENCE, false)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            if (isCommandMode) {
                // Command mode has shorter silence timeout for snappier responses
                putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 1500L)
                putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 1000L)
            } else {
                // Wake word background mode is more relaxed
                putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 3000L)
                putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 2000L)
            }
        }

        try {
            recognizer?.startListening(intent)
            isListening = true
            watchdog.onRestartInitiated()
            Log.d(TAG, "SpeechRecognizer started listening (commandMode=$isCommandMode)")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to startSpeechRecognizer", e)
            isListening = false
            recoveryManager.recoverStt(SpeechRecognizer.ERROR_RECOGNIZER_BUSY, {
                recreateRecognizerAndRestart()
            })
        }
    }

    private fun stopListening() {
        isListening = false
        try {
            recognizer?.stopListening()
        } catch (_: Exception) {}
    }

    private fun restartListening() {
        stopListening()
        // Wait a tiny bit for the recognizer to stop before starting again
        mainHandler.postDelayed({
            if (isStarted && (isScreenOn || isCommandMode)) {
                startListeningInternal()
            }
        }, 50)
    }

    // ── Speech Listener Callback ───────────────────────────────

    private val speechListener = object : RecognitionListener {
        override fun onReadyForSpeech(params: Bundle?) {
            Log.d(TAG, "SpeechListener: onReadyForSpeech")
            watchdog.onListenerReady()
            if (isCommandMode) {
                callback?.onReadyForSpeech()
                callback?.onStatusChanged("Listening...")
            }
        }

        override fun onBeginningOfSpeech() {
            Log.d(TAG, "SpeechListener: onBeginningOfSpeech")
            if (isCommandMode) {
                callback?.onBeginningOfSpeech()
            }
        }

        override fun onRmsChanged(rmsdB: Float) {
            if (isCommandMode) {
                callback?.onRmsChanged(rmsdB)
            }
        }

        override fun onBufferReceived(buffer: ByteArray?) {}

        override fun onEndOfSpeech() {
            Log.d(TAG, "SpeechListener: onEndOfSpeech")
            if (isCommandMode) {
                callback?.onStatusChanged("Thinking...")
            }
        }

        override fun onError(error: Int) {
            Log.w(TAG, "SpeechListener onError: $error")
            watchdog.onError(error)

            if (isCommandMode) {
                val errorMsg = getErrorMessage(error)
                callback?.onError(error, errorMsg)
            }

            // Auto-recovery flow
            if (error == SpeechRecognizer.ERROR_RECOGNIZER_BUSY ||
                error == SpeechRecognizer.ERROR_CLIENT ||
                error == SpeechRecognizer.ERROR_AUDIO) {
                // Serious error: Recreate recognizer
                recoveryManager.recoverStt(error, {
                    recreateRecognizerAndRestart()
                })
            } else {
                // Timeout or no-match: just restart listening loop
                restartListening()
            }
        }

        override fun onResults(results: Bundle?) {
            watchdog.onResult()
            val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
            val text = matches?.firstOrNull() ?: ""
            Log.d(TAG, "SpeechListener onResults: '$text'")

            if (text.isNotEmpty()) {
                if (isCommandMode) {
                    callback?.onResults(text)
                    // Wait for overlay processing/TTS before resuming listening (or overlay will handle setting mode)
                } else {
                    // Wake Word Mode check
                    val detectResult = wakeWordDetector.detect(text)
                    if (detectResult.detected) {
                        Log.i(TAG, "🔥 Wake Word Detected: '${detectResult.matchedWord}' with confidence ${detectResult.confidence}")
                        triggerAssistantOverlay(detectResult.inputText)
                    } else {
                        // Silent loop restart
                        restartListening()
                    }
                }
            } else {
                restartListening()
            }
        }

        override fun onPartialResults(partialResults: Bundle?) {
            val matches = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
            val text = matches?.firstOrNull() ?: ""
            if (text.isNotEmpty()) {
                if (isCommandMode) {
                    callback?.onPartialResults(text)
                } else {
                    // Pre-check partial results for fast wake word activation
                    val detectResult = wakeWordDetector.detect(text)
                    if (detectResult.detected && detectResult.confidence >= 0.85f) {
                        Log.i(TAG, "🔥 Fast Wake Word Detected in partial: '${detectResult.matchedWord}'")
                        stopListening()
                        triggerAssistantOverlay(detectResult.inputText)
                    }
                }
            }
        }

        override fun onEvent(eventType: Int, params: Bundle?) {}
    }

    private fun triggerAssistantOverlay(rawText: String) {
        val command = wakeWordDetector.extractCommand(rawText)
        Log.d(TAG, "Triggering overlay with command: '$command'")

        // Update notification to indicate active interaction
        updateNotification("JARVIS Active", "Processing command: $command")

        // 1. Try to invoke via JarvisVoiceInteractionService static reference
        val invoked = try {
            val clazz = Class.forName("com.jarvis.assistant.services.JarvisVoiceInteractionService")
            val field = clazz.getDeclaredField("activeInstance")
            field.isAccessible = true
            val activeInstance = field.get(null)
            if (activeInstance != null) {
                val showSessionMethod = clazz.getMethod("showSession", Bundle::class.java, Int::class.javaPrimitiveType)
                val args = Bundle().apply {
                    putStringArrayList(RecognizerIntent.EXTRA_RESULTS, arrayListOf(command))
                    putBoolean("wake_word_triggered", true)
                }
                showSessionMethod.invoke(activeInstance, args, 0)
                Log.d(TAG, "Successfully invoked assistant session via showSession")
                true
            } else {
                false
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to invoke JarvisVoiceInteractionService directly: ${e.message}")
            false
        }

        // 2. Fallback: Launch voice command intent to let Android handle assistant launch
        if (!invoked) {
            Log.w(TAG, "Direct invocation failed. Trying Intent fallback.")
            try {
                val intent = Intent(Intent.ACTION_VOICE_COMMAND).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK
                }
                startActivity(intent)
            } catch (e: Exception) {
                Log.e(TAG, "Failed to launch voice command intent: ${e.message}")
            }
        }

        // Switch to command mode anticipation
        isCommandMode = true
    }

    // ── Screen State Monitoring ────────────────────────────────

    private val screenReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.action) {
                Intent.ACTION_SCREEN_ON -> {
                    Log.d(TAG, "Screen ON — resuming background listening")
                    isScreenOn = true
                    acquireWakeLock()
                    restartListening()
                }
                Intent.ACTION_SCREEN_OFF -> {
                    Log.d(TAG, "Screen OFF — pausing background listening to save battery")
                    isScreenOn = false
                    releaseWakeLock()
                    stopListening()
                    if (!isCommandMode) {
                        destroyRecognizer()
                    }
                }
            }
        }
    }

    // ── Power Management (Wake Lock) ───────────────────────────

    private fun acquireWakeLock() {
        try {
            if (wakeLock?.isHeld == false) {
                wakeLock?.acquire(10 * 60 * 1000L) // 10 minutes max lock per acquisition
                Log.d(TAG, "WakeLock acquired")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error acquiring wake lock", e)
        }
    }

    private fun releaseWakeLock() {
        try {
            if (wakeLock?.isHeld == true) {
                wakeLock?.release()
                Log.d(TAG, "WakeLock released")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error releasing wake lock", e)
        }
    }

    // ── Notification Helpers ───────────────────────────────────

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val name = "JARVIS Assistant"
            val descriptionText = "Continuous background listening for wake word activation"
            val importance = NotificationManager.IMPORTANCE_LOW
            val channel = NotificationChannel(CHANNEL_ID, name, importance).apply {
                description = descriptionText
            }
            val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(title: String, text: String): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, SetupActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(title)
            .setContentText(text)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .build()
    }

    private fun updateNotification(title: String, text: String) {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        notificationManager.notify(NOTIFICATION_ID, buildNotification(title, text))
    }

    private fun getErrorMessage(errorCode: Int): String {
        return when (errorCode) {
            SpeechRecognizer.ERROR_AUDIO -> "Audio recording error"
            SpeechRecognizer.ERROR_CLIENT -> "Client side error"
            SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Permission missing"
            SpeechRecognizer.ERROR_NETWORK -> "Network error"
            SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> "Network timeout"
            SpeechRecognizer.ERROR_NO_MATCH -> "No speech match"
            SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "STT Engine busy"
            SpeechRecognizer.ERROR_SERVER -> "Server error"
            SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "No speech input"
            else -> "Unknown STT error ($errorCode)"
        }
    }
}
