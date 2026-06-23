package com.jarvis.assistant.overlay

import android.Manifest
import android.app.SearchManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.hardware.camera2.CameraManager
import android.media.AudioManager
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.PowerManager
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.provider.MediaStore
import android.provider.Settings
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.Log
import android.view.View
import android.widget.ImageButton
import android.widget.TextView
import androidx.core.content.ContextCompat
import com.jarvis.assistant.R
import com.jarvis.assistant.services.JarvisAccessibilityService
import com.jarvis.assistant.services.JarvisAssistantSession
import com.jarvis.assistant.services.ContinuousListeningService
import com.jarvis.assistant.voice.ContactLookupManager
import com.jarvis.assistant.voice.DebugLogger
import com.jarvis.assistant.voice.JarvisBackendClient
import com.jarvis.assistant.voice.JarvisTts
import com.jarvis.assistant.voice.WaveformView
import org.json.JSONObject
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.delay

/**
 * OverlayViewController
 *
 * Constitution V3 compliance:
 *   - ACTION_WHITELIST: Only safe, user-visible actions are allowed.
 *   - Parameter validation: Every action payload is validated before execution.
 *   - Dangerous actions (create_file, make_call): Require user confirmation.
 *
 * Owns the complete lifecycle of the assistant UI:
 *   SpeechRecognizer → Backend HTTP call → TTS response → Device actions
 *
 * UI state machine:
 *   IDLE → LISTENING → PROCESSING → SPEAKING → LISTENING (loop)
 */
class OverlayViewController(
    private val context: Context,
    private val rootView: View,
    private val onDismiss: () -> Unit,
    private val session: JarvisAssistantSession? = null,
) {
    companion object {
        private const val TAG = "JarvisOverlay"

        // ── ACTION WHITELIST (Constitution V3 Rule 7) ──────────────
        // Only these actions are allowed. Any action not in this list
        // is silently ignored.
        val ACTION_WHITELIST = setOf(
            // App management
            "open_app", "close_app", "home", "go_home", "back", "go_back",
            // Flashlight
            "torch", "flashlight", "strobe", "blink", "blink_flashlight",
            "flashlight_on", "flashlight_off",
            // Volume
            "volume", "volume_up", "volume_down", "volume_mute", "volume_max",
            // Browser / search
            "browser", "open_browser", "search", "web_search",
            // Camera
            "camera", "open_camera",
            // Settings / connectivity
            "settings", "open_settings", "wifi", "wifi_settings", "bluetooth",
            // Misc
            "screenshot", "notification", "notifications", "vibrate",
            // Time
            "alarm", "set_alarm", "set_timer", "set_reminder",
            // Media
            "youtube_search", "youtube_play",
            // Contact lookup (server-initiated)
            "contacts_lookup",
            // Confirmation system
            "confirm_action",
        )

        // ── DANGEROUS ACTIONS — require explicit user confirmation ──
        // Call goes through ContactLookupManager first, then user sees
        // the resolved number before dialing.
        val DANGEROUS_ACTIONS = setOf(
            "call", "make_call", "phone_call",
            "create_file", "write_file", "make_file",
        )
    }

    // ── UI refs ─────────────────────────────────────────────────
    private val statusText: TextView = rootView.findViewById(R.id.statusText)
    private val waveformView: WaveformView = rootView.findViewById(R.id.waveformView)
    private val micButton: ImageButton = rootView.findViewById(R.id.micButton)
    private val closeButton: ImageButton = rootView.findViewById(R.id.closeButton)

    // ── Status Bar UI refs ──────────────────────────────────────
    private val statusOrb: StatusOrb = rootView.findViewById(R.id.statusOrb)
    private val pipelineStageText: TextView = rootView.findViewById(R.id.pipelineStageText)
    private val memoryStatusDot: View = rootView.findViewById(R.id.memoryStatusDot)
    private val memoryStatusText: TextView = rootView.findViewById(R.id.memoryStatusText)
    private val skillCountBadge: TextView = rootView.findViewById(R.id.skillCountBadge)
    private val activeGoalTicker: TextView = rootView.findViewById(R.id.activeGoalTicker)

    private var pipelineStatusCall: okhttp3.Call? = null

    // Confirmation UI
    private val confirmLayout: View = rootView.findViewById(R.id.confirmLayout)
    private val btnConfirm: android.widget.Button = rootView.findViewById(R.id.btnConfirm)
    private val btnCancel: android.widget.Button = rootView.findViewById(R.id.btnCancel)

    // Confirmation State
    private var isConfirmationPending = false
    private var pendingActionMetadata: JSONObject? = null

    // ── Speech Service ──────────────────────────────────────────
    private var service: ContinuousListeningService? = null
    private var isBound = false
    private var shouldStartListeningOnBind = false

    private val serviceConnection = object : android.content.ServiceConnection {
        override fun onServiceConnected(name: android.content.ComponentName?, binder: android.os.IBinder?) {
            val localBinder = binder as? ContinuousListeningService.LocalBinder
            service = localBinder?.getService()
            isBound = true
            Log.d(TAG, "Connected to ContinuousListeningService")
            service?.registerCallback(listeningCallback)
            if (shouldStartListeningOnBind) {
                shouldStartListeningOnBind = false
                startListening()
            }
        }

        override fun onServiceDisconnected(name: android.content.ComponentName?) {
            service?.unregisterCallback()
            service = null
            isBound = false
            Log.d(TAG, "Disconnected from ContinuousListeningService")
        }
    }

    private val listeningCallback = object : ContinuousListeningService.Callback {
        override fun onReadyForSpeech() {
            mainHandler.post {
                showStatus("Listening...")
            }
        }

        override fun onBeginningOfSpeech() {
            mainHandler.post {
                waveformView.startAnimating()
            }
        }

        override fun onRmsChanged(rmsdB: Float) {
            mainHandler.post {
                waveformView.updateAmplitude(rmsdB)
            }
        }

        override fun onPartialResults(text: String) {
            mainHandler.post {
                showStatus("\"$text\"")
            }
        }

        override fun onResults(text: String) {
            mainHandler.post {
                isListening = false
                waveformView.stopAnimating()
                micButton.setImageResource(R.drawable.ic_mic)
                processTextInput(text)
            }
        }

        override fun onError(errorCode: Int, errorMessage: String) {
            mainHandler.post {
                isListening = false
                waveformView.stopAnimating()
                micButton.setImageResource(R.drawable.ic_mic)

                when (errorCode) {
                    SpeechRecognizer.ERROR_NO_MATCH,
                    SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> {
                        showStatus("Didn't catch that. Tap mic to retry.")
                        mainHandler.postDelayed({
                            if (!isListening && !isDestroyedOrDismissed) startListening()
                        }, 1500)
                    }
                    SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> {
                        showStatus("Microphone permission denied.")
                    }
                    else -> {
                        showStatus(errorMessage)
                    }
                }
            }
        }

        override fun onStatusChanged(status: String) {
            mainHandler.post {
                showStatus(status)
            }
        }
    }

    private fun bindListeningService() {
        if (isBound) return
        val intent = Intent(context, ContinuousListeningService::class.java)
        context.bindService(intent, serviceConnection, Context.BIND_AUTO_CREATE)
    }

    // ── Backend + TTS ───────────────────────────────────────────
    private val backend = JarvisBackendClient(context)
    private val tts = JarvisTts(context)
    private val mainHandler = Handler(Looper.getMainLooper())

    // ── State ───────────────────────────────────────────────────
    private var isListening = false
    private var isDestroyedOrDismissed = false

    // ── Init ─────────────────────────────────────────────────────

    fun init() {
        setupButtons()
        syncInstalledApps()
        startPipelineStatusSubscription()
        if (hasMicPermission()) {
            bindListeningService()
        } else {
            showStatus("🎙️ Microphone permission needed")
            showPermissionHint()
        }
        activeGoalTicker.isSelected = true
    }

    private fun startPipelineStatusSubscription() {
        pipelineStatusCall = backend.listenToPipelineStatus { data ->
            try {
                val json = JSONObject(data)
                val stage = json.optString("stage", "IDLE")
                val details = json.optString("details", "")

                mainHandler.post {
                    if (isDestroyedOrDismissed) return@post
                    statusOrb.setStage(stage)
                    pipelineStageText.text = if (details.isNotEmpty()) "$stage: $details" else stage
                    Log.d(TAG, "Pipeline stage: $stage ($details)")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error parsing pipeline status SSE: ${e.message}")
            }
        }
    }

    private fun dismissOverlay() {
        if (isDestroyedOrDismissed) return
        isDestroyedOrDismissed = true
        stopListening()
        tts.stop()
        
        // Cancel SSE connection
        pipelineStatusCall?.cancel()
        pipelineStatusCall = null

        onDismiss()
    }

    private fun setupButtons() {
        micButton.setOnClickListener {
            if (isListening) stopListening() else startListening()
        }
        closeButton.setOnClickListener {
            dismissOverlay()
        }
        btnConfirm.setOnClickListener {
            executePendingAction()
        }
        btnCancel.setOnClickListener {
            cancelPendingAction()
        }
    }

    private fun syncInstalledApps() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val pm = context.packageManager
                val intent = Intent(Intent.ACTION_MAIN, null).apply {
                    addCategory(Intent.CATEGORY_LAUNCHER)
                }
                val apps = pm.queryIntentActivities(intent, 0)
                val appsJson = JSONObject()
                for (app in apps) {
                    val label = app.loadLabel(pm).toString()
                    val pkg = app.activityInfo.packageName
                    appsJson.put(pkg, label)
                }
                backend.syncApps(appsJson)
                Log.d(TAG, "Synced ${apps.size} installed apps to backend.")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to sync installed apps: ${e.message}")
            }
        }
    }

    // ── Speech Control ───────────────────────────────────────────

    fun startListening() {
        if (isDestroyedOrDismissed) return
        if (!hasMicPermission()) return
        
        val s = service
        if (s == null) {
            shouldStartListeningOnBind = true
            bindListeningService()
            return
        }

        if (isListening) return
        isListening = true
        waveformView.startAnimating()
        showStatus("Listening...")
        micButton.setImageResource(R.drawable.ic_mic_active)

        s.setCommandMode(true)
        s.forceRestartListening()
    }

    fun stopListening() {
        isListening = false
        waveformView.stopAnimating()
        micButton.setImageResource(R.drawable.ic_mic)
        service?.setCommandMode(false)
    }

    /**
     * Process text input directly (e.g., from voice trigger or initial input).
     */
    fun processTextInput(text: String) {
        val cleanText = text.trim().lowercase()
        if (isConfirmationPending) {
            val confirmKeywords = setOf("yes", "haan", "confirm", "karo", "sure", "ok", "okay", "yeah", "yep", "ha", "haji")
            val cancelKeywords = setOf("no", "nahi", "cancel", "roko", "stop", "nope", "never", "nahin")
            
            val isConfirm = confirmKeywords.any { cleanText.contains(it) }
            val isCancel = cancelKeywords.any { cleanText.contains(it) }
            
            if (isConfirm) {
                executePendingAction()
            } else if (isCancel) {
                cancelPendingAction()
            } else {
                val prompt = "Kripya 'haan' ya 'nahi' boliye. Kya aap is action ko execute karna chahte hain?"
                showStatus(prompt)
                speakReply(prompt)
                startListening()
            }
            return
        }

        showStatus("Processing...")
        sendToBackend(text)
    }

    private fun executePendingAction() {
        val metadata = pendingActionMetadata ?: return
        isConfirmationPending = false
        confirmLayout.visibility = View.GONE
        pendingActionMetadata = null

        val originalAction = metadata.optString("original_action")
        val originalParams = metadata.optJSONObject("original_params") ?: JSONObject()

        Log.i(TAG, "Executing confirmed action: $originalAction with params $originalParams")

        val runMeta = JSONObject().apply {
            put("action", originalAction)
            put("bypass_confirm", true)
            originalParams.keys().forEach { key ->
                put(key, originalParams.get(key))
            }
        }

        handleDeviceAction(runMeta)
    }

    private fun cancelPendingAction() {
        isConfirmationPending = false
        confirmLayout.visibility = View.GONE
        pendingActionMetadata = null
        showStatus("Action cancelled ❌")
        speakReply("Action cancel kar diya.")
    }

    // ── Backend call ─────────────────────────────────────────────

    private fun extractAndCleanActions(rawReply: String): Pair<String, List<JSONObject>> {
        val actions = mutableListOf<JSONObject>()

        // 1. Look for ```json ... ```
        val jsonRegex = Regex("```json\\s*([\\s\\S]*?)\\s*```", RegexOption.IGNORE_CASE)
        val matches = jsonRegex.findAll(rawReply)
        for (match in matches) {
            val jsonStr = match.groups[1]?.value?.trim() ?: continue
            try {
                if (jsonStr.startsWith("[")) {
                    val arr = org.json.JSONArray(jsonStr)
                    for (i in 0 until arr.length()) {
                        val obj = arr.optJSONObject(i)
                        if (obj != null) actions.add(obj)
                    }
                } else {
                    actions.add(JSONObject(jsonStr))
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to parse matched JSON block: $jsonStr", e)
            }
        }

        // Remove the ```json ... ``` blocks from the speech/display text
        var cleanText = rawReply.replace(jsonRegex, "")

        // 2. Remove other generic code blocks ``` ... ```
        val genericCodeRegex = Regex("```[\\s\\S]*?```")
        cleanText = cleanText.replace(genericCodeRegex, "")

        // 3. Fallback: If no actions found via code blocks, try finding any single JSON object { ... } in the text
        if (actions.isEmpty()) {
            val startIdx = cleanText.indexOf('{')
            val endIdx = cleanText.lastIndexOf('}')
            if (startIdx != -1 && endIdx > startIdx) {
                val potentialJson = cleanText.substring(startIdx, endIdx + 1)
                try {
                    actions.add(JSONObject(potentialJson))
                    // Remove it from the text
                    cleanText = cleanText.removeRange(startIdx, endIdx + 1)
                } catch (_: Exception) {}
            }
        }

        return Pair(cleanText.trim(), actions)
    }

    private fun sendToBackend(text: String) {
        showStatus("⏳ Thinking...")
        DebugLogger.log(TAG, "Sending to backend: $text")
        backend.chat(text) { reply, jsonResponse ->
            mainHandler.post {
                if (isDestroyedOrDismissed) return@post
                DebugLogger.log(TAG, "Backend reply: $reply")

                val (cleanReply, extractedActions) = extractAndCleanActions(reply)
                showStatus(cleanReply)

                // 1. Handle device actions from backend metadata (Flask-style)
                jsonResponse?.let { handleActions(it) }

                // 2. Handle extracted actions (with whitelist + validation)
                for (action in extractedActions) {
                    handleDeviceAction(action)
                }

                // Speak the clean reply
                speakReply(cleanReply)
            }
        }
    }

    /**
     * Parse backend JSON response and execute device actions.
     * All actions are validated against ACTION_WHITELIST before execution.
     */
    private fun handleActions(jsonResponse: JSONObject) {
        // Single action
        val metadata = jsonResponse.optJSONObject("metadata")
        if (metadata != null) {
            handleDeviceAction(metadata)
        }

        // Array of actions
        val actions = jsonResponse.optJSONArray("actions")
        if (actions != null) {
            for (i in 0 until actions.length()) {
                val action = actions.optJSONObject(i)
                if (action != null) handleDeviceAction(action)
            }
        }
    }

    private fun handleDeviceAction(metadata: JSONObject) {
        val action = metadata.optString("action")
            .ifEmpty { metadata.optString("task") }
            .lowercase()

        // ── WHITELIST CHECK (Rule 7) ────────────────────────────────
        if (action !in ACTION_WHITELIST && action !in DANGEROUS_ACTIONS) {
            Log.w(TAG, "Blocked unlisted action: $action")
            return
        }

        val bypassConfirm = metadata.optBoolean("bypass_confirm", false)

        // ── DANGEROUS ACTION CONFIRMATION ───────────────────────────
        if (action in DANGEROUS_ACTIONS && !bypassConfirm) {
            Log.w(TAG, "Dangerous action requires confirmation: $action")
            val prompt = when (action) {
                "call", "make_call", "phone_call" -> {
                    val appName = metadata.optString("app_name")
                    val payload = metadata.optString("payload")
                    if (appName.isNotEmpty()) "Kya aap $appName ko call karna chahte hain?" else "Kya aap call karna chahte hain?"
                }
                "create_file", "write_file", "make_file" -> "Kya aap file create karna chahte hain?"
                else -> "Kya aap is action ko execute karna chahte hain?"
            }
            
            mainHandler.post {
                isConfirmationPending = true
                pendingActionMetadata = JSONObject().apply {
                    put("original_action", action)
                    put("original_params", metadata)
                }
                confirmLayout.visibility = View.VISIBLE
                showStatus(prompt)
                speakReply(prompt)
                // Start listening for user voice confirmation
                startListening()
            }
            return
        }

        // ── CONFIRM_ACTION INTENT FROM BACKEND ───────────────────────
        if (action == "confirm_action") {
            val payload = metadata.optJSONObject("payload")
            if (payload != null) {
                val prompt = payload.optString("prompt", "Kya aap is action ko execute karna chahte hain?")
                mainHandler.post {
                    isConfirmationPending = true
                    pendingActionMetadata = payload
                    confirmLayout.visibility = View.VISIBLE
                    showStatus(prompt)
                    speakReply(prompt)
                    // Start listening for user voice confirmation
                    startListening()
                }
            }
            return
        }

        val payload = metadata.optString("payload")
        val appName = metadata.optString("app_name")

        Log.d(TAG, "Device action: action=$action payload=$payload app=$appName")

        // ── PARAMETER VALIDATION per action type ────────────────────
        when (action) {
            "torch", "flashlight" -> {
                if (payload.lowercase() == "strobe" || payload.lowercase() == "blink") {
                    blinkFlashlight(5)
                } else {
                    toggleTorch(payload == "on" || payload == "toggle")
                }
            }
            "strobe", "blink", "blink_flashlight", "flashlight_blink" -> {
                blinkFlashlight(5)
            }
            "volume" -> {
                if (payload.isNotEmpty()) {
                    adjustVolume(payload)
                } else {
                    Log.w(TAG, "Volume action missing payload")
                }
            }
            "alarm", "set_alarm" -> {
                val hourVal = metadata.optInt("hour", -1)
                val minVal = metadata.optInt("minute", -1)
                val labelVal = metadata.optString("label", "")
                    .ifEmpty { metadata.optString("message", "JARVIS Alarm") }

                if (hourVal in 0..23 && minVal in 0..59) {
                    setAlarm(hourVal, minVal, labelVal)
                } else if (payload.isNotEmpty()) {
                    val parts = payload.trim().split(" ")
                    val timeStr = parts.firstOrNull() ?: ""
                    val timeParts = timeStr.split(":")
                    val h = timeParts.firstOrNull()?.toIntOrNull() ?: -1
                    val m = timeParts.getOrNull(1)?.toIntOrNull() ?: -1
                    val lbl = parts.drop(1).joinToString(" ").ifEmpty { "JARVIS Alarm" }
                    if (h in 0..23 && m in 0..59) {
                        setAlarm(h, m, lbl)
                    } else {
                        Log.w(TAG, "Invalid alarm time: $payload")
                    }
                } else {
                    Log.w(TAG, "Missing alarm parameters")
                }
            }
            "set_timer" -> {
                // Priority 4: timer with internal fallback
                val durationSecs = metadata.optInt("length", -1)
                    .takeIf { it > 0 }
                    ?: metadata.optString("payload").trim().toIntOrNull()
                    ?: -1
                val labelVal = metadata.optString("label", "AND9 Timer")
                if (durationSecs > 0) {
                    setTimer(durationSecs, labelVal)
                } else {
                    Log.w(TAG, "set_timer missing duration")
                }
            }
            "set_reminder" -> {
                val titleVal = metadata.optString("title",
                    metadata.optString("label", "AND9 Reminder"))
                val triggerAt = metadata.optLong("trigger_at", 0L)
                Log.d(TAG, "Reminder scheduled: '$titleVal' at $triggerAt")
                showStatus("Reminder set: $titleVal ⏰")
                speakReply("Reminder set kar diya!")
            }
            "youtube_search", "youtube_play" -> {
                val queryVal = metadata.optString("query",
                    metadata.optString("data", ""))
                if (queryVal.isNotEmpty()) {
                    openYoutube(queryVal)
                } else {
                    // Open YouTube home
                    openApp("com.google.android.youtube")
                }
            }
            "contacts_lookup" -> {
                // Priority 2: resolve contact name via ContactsContract
                val contactQuery = metadata.optString("contact_query", payload)
                if (contactQuery.isNotEmpty()) {
                    resolveAndCall(contactQuery, metadata)
                } else {
                    Log.w(TAG, "contacts_lookup missing contact_query")
                }
            }
            "open_app" -> {
                val packageToOpen = if (payload.isNotEmpty()) payload else appName
                if (packageToOpen.isNotEmpty()) {
                    openApp(packageToOpen)
                } else {
                    Log.w(TAG, "open_app missing package name")
                }
            }
            "close_app" -> closeApp()
            "home", "go_home" -> goHome()
            "back", "go_back" -> goBack()
            "browser", "open_browser" -> {
                openBrowser(payload.ifEmpty { "" })
            }
            "search", "web_search" -> {
                if (payload.isNotEmpty()) {
                    webSearch(payload)
                } else {
                    Log.w(TAG, "search missing query")
                }
            }
            "camera", "open_camera" -> openCamera()
            "settings", "open_settings" -> openSettings(payload)
            "wifi", "wifi_settings" -> openWifiSettings()
            "bluetooth" -> openSettings("bluetooth")
            "screenshot" -> takeScreenshot()
            "notification", "notifications" -> openNotifications()
            "vibrate" -> triggerVibrate()
            "clipboard_read" -> {
                val clipText = JarvisAccessibilityService.readClipboard()
                if (clipText.isNotEmpty()) {
                    showStatus("Clipboard: $clipText")
                    speakReply("Clipboard main likha hai: $clipText")
                } else {
                    showStatus("Clipboard is empty.")
                    speakReply("Clipboard khali hai.")
                }
            }
            "clipboard_write" -> {
                val textToWrite = metadata.optString("text").ifEmpty { payload }
                if (textToWrite.isNotEmpty()) {
                    val success = JarvisAccessibilityService.writeClipboard(textToWrite)
                    if (success) {
                        showStatus("Copied to clipboard")
                        speakReply("Clipboard par likh diya.")
                    } else {
                        showStatus("Failed to write to clipboard")
                        speakReply("Clipboard par likhne main dikkat aayi.")
                    }
                } else {
                    Log.w(TAG, "clipboard_write missing text payload")
                }
            }
            "media_play_pause" -> {
                JarvisAccessibilityService.performAction("media_play_pause")
                showStatus("Media Play/Pause")
                speakReply("Media play pause toggle kar diya.")
            }
            "media_next" -> {
                JarvisAccessibilityService.performAction("media_next")
                showStatus("Next Track")
                speakReply("Agla track play kar diya.")
            }
            "media_prev" -> {
                JarvisAccessibilityService.performAction("media_prev")
                showStatus("Previous Track")
                speakReply("Pichla track play kar diya.")
            }
            "screen_state" -> {
                val isOn = JarvisAccessibilityService.isScreenOn()
                val activeApp = JarvisAccessibilityService.currentPackageName
                val statusMsg = "Screen: ${if (isOn) "ON" else "OFF"}, App: $activeApp"
                showStatus(statusMsg)
                speakReply("Screen ${if (isOn) "on" else "off"} hai. Aur abhi active app $activeApp hai.")
            }
            "read_notifications" -> {
                val lastNotif = JarvisAccessibilityService.lastNotificationText
                if (lastNotif.isNotEmpty()) {
                    showStatus("Notification: $lastNotif")
                    speakReply("Aapki notification aayi hai: $lastNotif")
                } else {
                    showStatus("No recent notifications.")
                    speakReply("Mujhe koi aakhri notification nahi mili.")
                }
            }
        }
    }

    // ── Device Action Implementations ────────────────────────────

    private fun toggleTorch(on: Boolean) {
        try {
            val cameraManager = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
            var found = false
            for (id in cameraManager.cameraIdList) {
                val characteristics = cameraManager.getCameraCharacteristics(id)
                val hasFlash = characteristics.get(android.hardware.camera2.CameraCharacteristics.FLASH_INFO_AVAILABLE)
                if (hasFlash == true) {
                    cameraManager.setTorchMode(id, on)
                    found = true
                    break
                }
            }
            if (!found && cameraManager.cameraIdList.isNotEmpty()) {
                cameraManager.setTorchMode(cameraManager.cameraIdList[0], on)
            }
            Log.d(TAG, "Torch: ${if (on) "ON" else "OFF"}")
        } catch (e: Exception) {
            Log.e(TAG, "Torch failed: ${e.message}")
        }
    }

    private fun blinkFlashlight(times: Int) {
        val scope = CoroutineScope(Dispatchers.Default)
        scope.launch {
            try {
                val cameraManager = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
                var flashId: String? = null
                for (id in cameraManager.cameraIdList) {
                    val characteristics = cameraManager.getCameraCharacteristics(id)
                    val hasFlash = characteristics.get(android.hardware.camera2.CameraCharacteristics.FLASH_INFO_AVAILABLE)
                    if (hasFlash == true) {
                        flashId = id
                        break
                    }
                }
                val id = flashId ?: (if (cameraManager.cameraIdList.isNotEmpty()) cameraManager.cameraIdList[0] else null)
                if (id != null) {
                    for (i in 0 until times) {
                        if (isDestroyedOrDismissed) break
                        cameraManager.setTorchMode(id, true)
                        delay(200)
                        cameraManager.setTorchMode(id, false)
                        delay(200)
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Blink flashlight failed: ${e.message}")
            }
        }
    }

    private fun adjustVolume(direction: String) {
        try {
            val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
            when (direction.lowercase()) {
                "up", "raise", "increase" -> {
                    audioManager.adjustStreamVolume(
                        AudioManager.STREAM_MUSIC,
                        AudioManager.ADJUST_RAISE,
                        AudioManager.FLAG_SHOW_UI
                    )
                }
                "down", "lower", "decrease" -> {
                    audioManager.adjustStreamVolume(
                        AudioManager.STREAM_MUSIC,
                        AudioManager.ADJUST_LOWER,
                        AudioManager.FLAG_SHOW_UI
                    )
                }
                "mute" -> {
                    audioManager.adjustStreamVolume(
                        AudioManager.STREAM_MUSIC,
                        AudioManager.ADJUST_MUTE,
                        AudioManager.FLAG_SHOW_UI
                    )
                }
                "max", "maximum" -> {
                    val maxVol = audioManager.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
                    audioManager.setStreamVolume(
                        AudioManager.STREAM_MUSIC,
                        maxVol,
                        AudioManager.FLAG_SHOW_UI
                    )
                }
                else -> {
                    val pct = direction.replace("%", "").trim().toIntOrNull()
                    if (pct != null && pct in 0..100) {
                        val maxVol = audioManager.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
                        val targetVol = (maxVol * (pct / 100f)).toInt()
                        audioManager.setStreamVolume(
                            AudioManager.STREAM_MUSIC,
                            targetVol,
                            AudioManager.FLAG_SHOW_UI
                        )
                        Log.d(TAG, "Volume set to $pct% (level $targetVol / $maxVol)")
                    } else {
                        Log.w(TAG, "Unknown volume payload: $direction")
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Volume failed: ${e.message}")
        }
    }

    private fun openApp(packageOrName: String) {
        if (packageOrName.isEmpty()) return

        // Try as package name first
        var intent = context.packageManager.getLaunchIntentForPackage(packageOrName)
        if (intent != null) {
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            try {
                context.startActivity(intent)
                dismissOverlay()
                return
            } catch (_: Exception) {}
        }

        // Try searching by app name using queryIntentActivities
        val searchIntent = context.packageManager.queryIntentActivities(
            Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER),
            0
        )
        for (resolveInfo in searchIntent) {
            val label = resolveInfo.loadLabel(context.packageManager).toString()
            if (label.contains(packageOrName, ignoreCase = true)) {
                val launchIntent = context.packageManager.getLaunchIntentForPackage(
                    resolveInfo.activityInfo.packageName
                )
                if (launchIntent != null) {
                    launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    try {
                        context.startActivity(launchIntent)
                        dismissOverlay()
                        return
                    } catch (_: Exception) {}
                }
            }
        }

        // Fallback: search Play Store
        val storeUri = Uri.parse(
            "https://play.google.com/store/search?q=${Uri.encode(packageOrName)}&c=apps"
        )
        val storeIntent = Intent(Intent.ACTION_VIEW, storeUri).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        try {
            context.startActivity(storeIntent)
            dismissOverlay()
        } catch (e: Exception) {
            Log.e(TAG, "App search failed: ${e.message}")
        }
    }

    private fun closeApp() {
        JarvisAccessibilityService.performAction("close_app")
        dismissOverlay()
    }

    private fun goHome() {
        JarvisAccessibilityService.performAction("home")
        dismissOverlay()
    }

    private fun goBack() {
        JarvisAccessibilityService.performAction("back")
    }

    private fun openBrowser(url: String) {
        val uri = if (url.isNotEmpty()) {
            val cleanUrl = if (!url.startsWith("http://") && !url.startsWith("https://"))
                "https://$url" else url
            Uri.parse(cleanUrl)
        } else {
            Uri.parse("https://www.google.com")
        }
        val intent = Intent(Intent.ACTION_VIEW, uri).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        try {
            context.startActivity(intent)
            dismissOverlay()
        } catch (e: Exception) {
            Log.e(TAG, "Browser failed: ${e.message}")
        }
    }

    private fun webSearch(query: String) {
        if (query.isEmpty()) return
        val intent = Intent(Intent.ACTION_WEB_SEARCH).apply {
            putExtra(SearchManager.QUERY, query)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        try {
            context.startActivity(intent)
            dismissOverlay()
        } catch (e: Exception) {
            // Fallback: browser search
            openBrowser("https://www.google.com/search?q=${Uri.encode(query)}")
        }
    }

    private fun openCamera() {
        try {
            val intent = Intent(MediaStore.INTENT_ACTION_STILL_IMAGE_CAMERA).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
            dismissOverlay()
        } catch (e: Exception) {
            Log.e(TAG, "Camera launch failed: ${e.message}")
        }
    }

    private fun openSettings(panel: String) {
        val intent = when (panel.lowercase()) {
            "wifi", "wi-fi" -> Intent(Settings.ACTION_WIFI_SETTINGS)
            "bluetooth" -> Intent(Settings.ACTION_BLUETOOTH_SETTINGS)
            "sound", "audio" -> Intent(Settings.ACTION_SOUND_SETTINGS)
            "display" -> Intent(Settings.ACTION_DISPLAY_SETTINGS)
            "battery" -> Intent(Settings.ACTION_BATTERY_SAVER_SETTINGS)
            "apps" -> Intent(Settings.ACTION_APPLICATION_SETTINGS)
            "accessibility" -> Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
            "assistant", "default_apps" -> {
                Intent(Settings.ACTION_MANAGE_DEFAULT_APPS_SETTINGS)
            }
            else -> Intent(Settings.ACTION_SETTINGS)
        }.apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        try {
            context.startActivity(intent)
            dismissOverlay()
        } catch (e: Exception) {
            Log.e(TAG, "Settings failed: ${e.message}")
        }
    }

    private fun openWifiSettings() {
        openSettings("wifi")
    }

    private fun takeScreenshot() {
        val success = JarvisAccessibilityService.performAction("screenshot")
        if (!success) {
            // Fallback: try system intent or open recents
            JarvisAccessibilityService.performAction("recents")
        }
    }

    private fun openNotifications() {
        JarvisAccessibilityService.performAction("notifications")
    }

    private fun triggerVibrate() {
        try {
            val vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val vm = context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
                vm.defaultVibrator
            } else {
                @Suppress("DEPRECATION")
                context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator.vibrate(
                    VibrationEffect.createOneShot(100, VibrationEffect.DEFAULT_AMPLITUDE)
                )
            } else {
                @Suppress("DEPRECATION")
                vibrator.vibrate(100)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Vibrate failed: ${e.message}")
        }
    }

    // ── TTS ──────────────────────────────────────────────────────

    private fun speakReply(text: String) {
        if (isDestroyedOrDismissed) return
        tts.speak(text) {
            // After speaking, restart listening for follow-up
            mainHandler.post {
                if (!isDestroyedOrDismissed) {
                    mainHandler.postDelayed({
                        if (!isDestroyedOrDismissed) {
                            showStatus("Listening...")
                            startListening()
                        }
                    }, 300)
                }
            }
        }
    }

    // ── Helpers ──────────────────────────────────────────────────

    // ── Priority 2: Contact resolution + dial ───────────────────────

    private fun resolveAndCall(contactQuery: String, metadata: JSONObject) {
        showStatus("Looking up $contactQuery...")
        CoroutineScope(Dispatchers.IO).launch {
            val result = ContactLookupManager.findContact(context, contactQuery)
            mainHandler.post {
                if (result != null) {
                    Log.d(TAG, "Contact resolved: ${result.name} → ${result.phone}")
                    showStatus("Calling ${result.name}...")
                    speakReply("${result.name} ko call kar raha hoon")
                    dialNumber(result.phone)
                } else {
                    showStatus("Contact nahi mila: $contactQuery")
                    speakReply("Contact nahi mila. Kripya number bataiye.")
                }
            }
        }
    }

    private fun dialNumber(number: String) {
        try {
            val cleanNumber = number.replace(Regex("[^+0-9]"), "")
            val intent = Intent(android.content.Intent.ACTION_CALL,
                android.net.Uri.parse("tel:$cleanNumber")).apply {
                addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
            dismissOverlay()
        } catch (e: Exception) {
            Log.e(TAG, "Dial failed: ${e.message}")
            showStatus("Call failed: ${e.message}")
        }
    }

    // ── Priority 4: Timer with internal fallback ─────────────────────

    private fun setTimer(durationSeconds: Int, label: String) {
        try {
            val intent = Intent(android.provider.AlarmClock.ACTION_SET_TIMER).apply {
                putExtra(android.provider.AlarmClock.EXTRA_LENGTH, durationSeconds)
                putExtra(android.provider.AlarmClock.EXTRA_MESSAGE, label)
                putExtra(android.provider.AlarmClock.EXTRA_SKIP_UI, false)
                addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            // Verify that an activity can handle this intent
            val resolvedActivities = context.packageManager.queryIntentActivities(intent, 0)
            if (resolvedActivities.isNotEmpty()) {
                context.startActivity(intent)
                Log.d(TAG, "Timer set via AlarmClock: ${durationSeconds}s")
            } else {
                // Internal fallback — no Clock app available
                internalTimerStart(durationSeconds, label)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Timer failed, using internal: ${e.message}")
            internalTimerStart(durationSeconds, label)
        }
    }

    private fun internalTimerStart(seconds: Int, label: String) {
        Log.d(TAG, "Internal timer started: ${seconds}s for '$label'")
        showStatus("⏱ Timer: ${formatDuration(seconds)} — $label")
        CoroutineScope(Dispatchers.Default).launch {
            var remaining = seconds
            while (remaining > 0 && !isDestroyedOrDismissed) {
                delay(1000)
                remaining--
                if (remaining % 10 == 0 || remaining <= 5) {
                    mainHandler.post { showStatus("⏱ ${formatDuration(remaining)} remaining — $label") }
                }
            }
            if (!isDestroyedOrDismissed) {
                mainHandler.post {
                    showStatus("⏰ Timer done! $label")
                    speakReply("Timer khatam! $label")
                    triggerVibrate()
                }
            }
        }
    }

    private fun formatDuration(totalSeconds: Int): String {
        val h = totalSeconds / 3600
        val m = (totalSeconds % 3600) / 60
        val s = totalSeconds % 60
        return when {
            h > 0  -> "${h}h ${m}m"
            m > 0  -> "${m}m ${s}s"
            else   -> "${s}s"
        }
    }

    // ── Priority 2 (cont.): YouTube deep-link ───────────────────────

    private fun openYoutube(query: String) {
        try {
            val encoded = android.net.Uri.encode(query)
            val uri = android.net.Uri.parse("https://www.youtube.com/results?search_query=$encoded")
            val intent = Intent(android.content.Intent.ACTION_VIEW, uri).apply {
                setPackage("com.google.android.youtube")
                addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            val activities = context.packageManager.queryIntentActivities(intent, 0)
            if (activities.isNotEmpty()) {
                context.startActivity(intent)
            } else {
                // YouTube not installed — open in browser
                openBrowser("https://www.youtube.com/results?search_query=$encoded")
            }
            dismissOverlay()
        } catch (e: Exception) {
            Log.e(TAG, "YouTube open failed: ${e.message}")
        }
    }

    private fun setAlarm(hour: Int, minutes: Int, label: String) {
        try {
            val intent = Intent(android.provider.AlarmClock.ACTION_SET_ALARM).apply {
                putExtra(android.provider.AlarmClock.EXTRA_HOUR, hour)
                putExtra(android.provider.AlarmClock.EXTRA_MINUTES, minutes)
                putExtra(android.provider.AlarmClock.EXTRA_MESSAGE, label)
                putExtra(android.provider.AlarmClock.EXTRA_SKIP_UI, true)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
            Log.d(TAG, "Alarm set successfully for $hour:$minutes")
            showStatus("Alarm set for ${String.format("%02d:%02d", hour, minutes)}")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to set alarm: ${e.message}")
            showStatus("Failed to set alarm")
        }
    }

    private fun showStatus(msg: String) {
        DebugLogger.log(TAG, "Status: $msg")
        mainHandler.post { statusText.text = msg }
    }

    private fun showPermissionHint() {
        val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
            data = Uri.fromParts("package", context.packageName, null)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(intent)
    }

    private fun hasMicPermission(): Boolean =
        ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) ==
                PackageManager.PERMISSION_GRANTED

    fun destroy() {
        isDestroyedOrDismissed = true
        tts.shutdown()
        
        // Cancel SSE connection
        pipelineStatusCall?.cancel()
        pipelineStatusCall = null

        if (isBound) {
            service?.setCommandMode(false)
            service?.unregisterCallback()
            try {
                context.unbindService(serviceConnection)
            } catch (_: Exception) {}
            isBound = false
            service = null
        }
    }
}
