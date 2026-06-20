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
 * Owns the complete lifecycle of the assistant UI:
 *   SpeechRecognizer → Backend HTTP call → TTS response → Device actions
 *
 * UI state machine:
 *   IDLE → LISTENING → PROCESSING → SPEAKING → LISTENING (loop)
 *
 * Device actions supported:
 *   - Open apps              (PackageManager.getLaunchIntentForPackage)
 *   - Close apps / Go Home   (AccessibilityService)
 *   - Control volume         (AudioManager)
 *   - Flashlight on/off      (CameraManager.setTorchMode)
 *   - Launch browser         (ACTION_VIEW with URL)
 *   - Search web             (ACTION_WEB_SEARCH)
 *   - Open camera            (MediaStore.INTENT_ACTION_STILL_IMAGE_CAMERA)
 *   - Take screenshot        (via accessibility or system intent)
 *   - Open settings          (Settings.ACTION_SETTINGS)
 *   - Start voice conversation (continues listening loop)
 */
class OverlayViewController(
    private val context: Context,
    private val rootView: View,
    private val onDismiss: () -> Unit,
    private val session: JarvisAssistantSession? = null,
) {
    companion object {
        private const val TAG = "JarvisOverlay"
    }

    // ── UI refs ─────────────────────────────────────────────────
    private val statusText: TextView = rootView.findViewById(R.id.statusText)
    private val waveformView: WaveformView = rootView.findViewById(R.id.waveformView)
    private val micButton: ImageButton = rootView.findViewById(R.id.micButton)
    private val closeButton: ImageButton = rootView.findViewById(R.id.closeButton)

    // ── Speech ──────────────────────────────────────────────────
    private var recognizer: SpeechRecognizer? = null

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
        if (hasMicPermission()) {
            buildRecognizer()
        } else {
            showStatus("🎙️ Microphone permission needed")
            showPermissionHint()
        }
    }

    private fun dismissOverlay() {
        if (isDestroyedOrDismissed) return
        isDestroyedOrDismissed = true
        stopListening()
        tts.stop()
        onDismiss()
    }

    private fun setupButtons() {
        micButton.setOnClickListener {
            if (isListening) stopListening() else startListening()
        }
        closeButton.setOnClickListener {
            dismissOverlay()
        }
    }

    // ── SpeechRecognizer ─────────────────────────────────────────

    private fun buildRecognizer() {
        recognizer?.destroy()
        recognizer = SpeechRecognizer.createSpeechRecognizer(context).apply {
            setRecognitionListener(recognitionListener)
        }
    }

    fun startListening() {
        if (isDestroyedOrDismissed) return
        if (!hasMicPermission()) return
        if (recognizer == null) buildRecognizer()
        if (isListening) return
        isListening = true
        waveformView.startAnimating()
        showStatus("Listening...")
        micButton.setImageResource(R.drawable.ic_mic_active)

        try {
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, "hi-IN")
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "hi-IN")
                putExtra(RecognizerIntent.EXTRA_ONLY_RETURN_LANGUAGE_PREFERENCE, false)
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 1500L)
                putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 1000L)
            }
            recognizer?.startListening(intent)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start listening", e)
            showStatus("Tap mic to speak")
            isListening = false
            waveformView.stopAnimating()
            micButton.setImageResource(R.drawable.ic_mic)
        }
    }

    fun stopListening() {
        isListening = false
        try {
            recognizer?.stopListening()
        } catch (_: Exception) {}
        waveformView.stopAnimating()
        micButton.setImageResource(R.drawable.ic_mic)
    }

    /**
     * Process text input directly (e.g., from voice trigger or initial input).
     */
    fun processTextInput(text: String) {
        showStatus("Processing...")
        sendToBackend(text)
    }

    private val recognitionListener = object : RecognitionListener {
        override fun onReadyForSpeech(params: android.os.Bundle?) {
            showStatus("Listening...")
        }

        override fun onBeginningOfSpeech() {
            waveformView.startAnimating()
        }

        override fun onRmsChanged(rmsdB: Float) {
            mainHandler.post { waveformView.updateAmplitude(rmsdB) }
        }

        override fun onPartialResults(partialResults: android.os.Bundle?) {
            val partial = partialResults
                ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                ?.firstOrNull() ?: return
            showStatus("\"$partial\"")
        }

        override fun onResults(results: android.os.Bundle?) {
            isListening = false
            waveformView.stopAnimating()
            micButton.setImageResource(R.drawable.ic_mic)

            val text = results
                ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                ?.firstOrNull() ?: return

            showStatus("Processing...")
            sendToBackend(text)
        }

        override fun onError(error: Int) {
            isListening = false
            waveformView.stopAnimating()
            micButton.setImageResource(R.drawable.ic_mic)

            when (error) {
                SpeechRecognizer.ERROR_NO_MATCH,
                SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> {
                    showStatus("Didn't catch that. Tap mic to retry.")
                    // Auto-retry after short delay
                    mainHandler.postDelayed({
                        if (!isListening) startListening()
                    }, 1500)
                }
                SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> {
                    showStatus("Microphone permission denied.")
                }
                else -> {
                    showStatus("Tap mic to speak")
                }
            }
        }

        override fun onBufferReceived(buffer: ByteArray?) {}
        override fun onEndOfSpeech() {
            waveformView.stopAnimating()
        }
        override fun onEvent(eventType: Int, params: android.os.Bundle?) {}
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
                
                // 2. Handle extracted actions (Groq/OpenAI style)
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
     * Supports both single action and array of actions.
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
        val task = metadata.optString("task")
        val action = metadata.optString("action")
        val payload = metadata.optString("payload")
        val appName = metadata.optString("app_name")

        Log.d(TAG, "Device action: task=$task action=$action payload=$payload app=$appName")

        when (action.lowercase()) {
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
                adjustVolume(payload)
            }
            "alarm", "set_alarm" -> {
                val hourVal = metadata.optInt("hour", -1)
                val minVal = metadata.optInt("minute", -1)
                val labelVal = metadata.optString("label", "").ifEmpty { metadata.optString("message", "JARVIS Alarm") }
                
                if (hourVal != -1 && minVal != -1) {
                    setAlarm(hourVal, minVal, labelVal)
                } else {
                    val parts = payload.trim().split(" ")
                    val timeStr = parts.firstOrNull() ?: ""
                    val timeParts = timeStr.split(":")
                    val h = timeParts.firstOrNull()?.toIntOrNull() ?: -1
                    val m = timeParts.getOrNull(1)?.toIntOrNull() ?: -1
                    val lbl = parts.drop(1).joinToString(" ").ifEmpty { "JARVIS Alarm" }
                    if (h in 0..23 && m in 0..59) {
                        setAlarm(h, m, lbl)
                    } else {
                        Log.w(TAG, "Invalid alarm time format: $payload")
                    }
                }
            }
            "call", "make_call", "phone_call" -> {
                val numberOrName = payload.ifEmpty { appName }
                makeCall(numberOrName)
            }
            "create_file", "write_file", "make_file" -> {
                val fileName = metadata.optString("file_name")
                    .ifEmpty { metadata.optString("filename", "jarvis_note.txt") }
                val content = metadata.optString("content").ifEmpty { payload }
                createFile(fileName, content)
            }
            "open_app" -> {
                val packageToOpen = if (payload.isNotEmpty()) payload else appName
                openApp(packageToOpen)
            }
            "close_app" -> {
                closeApp()
            }
            "home", "go_home" -> {
                goHome()
            }
            "back", "go_back" -> {
                goBack()
            }
            "browser", "open_browser" -> {
                openBrowser(payload)
            }
            "search", "web_search" -> {
                webSearch(payload)
            }
            "camera", "open_camera" -> {
                openCamera()
            }
            "settings", "open_settings" -> {
                openSettings(payload)
            }
            "wifi", "wifi_settings" -> {
                openWifiSettings()
            }
            "screenshot" -> {
                takeScreenshot()
            }
            "notification", "notifications" -> {
                openNotifications()
            }
            "vibrate" -> {
                triggerVibrate()
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

    private fun makeCall(numberOrName: String) {
        if (numberOrName.isEmpty()) return
        
        val number = if (numberOrName.all { it.isDigit() || it == '+' || it == '-' || it == ' ' || it == '(' || it == ')' }) {
            numberOrName
        } else {
            val resolved = findContactNumber(numberOrName)
            if (resolved.isNullOrEmpty()) {
                Log.w(TAG, "Could not find contact: $numberOrName")
                showStatus("Contact not found: $numberOrName")
                speakReply("Sorry, contact $numberOrName nahi mila.")
                return
            }
            resolved
        }

        if (ContextCompat.checkSelfPermission(context, Manifest.permission.CALL_PHONE) != PackageManager.PERMISSION_GRANTED) {
            try {
                val intent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:${Uri.encode(number)}")).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                context.startActivity(intent)
                dismissOverlay()
            } catch (e: Exception) {
                Log.e(TAG, "Dial failed: ${e.message}")
            }
            return
        }

        try {
            val intent = Intent(Intent.ACTION_CALL, Uri.parse("tel:${Uri.encode(number)}")).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
            dismissOverlay()
        } catch (e: Exception) {
            Log.e(TAG, "Call failed: ${e.message}")
            showStatus("Failed to place call")
        }
    }

    private fun findContactNumber(name: String): String? {
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.READ_CONTACTS) != PackageManager.PERMISSION_GRANTED) {
            Log.w(TAG, "READ_CONTACTS permission not granted")
            return null
        }
        try {
            val uri = android.provider.ContactsContract.CommonDataKinds.Phone.CONTENT_URI
            val projection = arrayOf(
                android.provider.ContactsContract.CommonDataKinds.Phone.NUMBER,
                android.provider.ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME
            )
            val selection = "${android.provider.ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME} LIKE ?"
            val selectionArgs = arrayOf("%$name%")
            
            context.contentResolver.query(uri, projection, selection, selectionArgs, null)?.use { cursor ->
                if (cursor.moveToFirst()) {
                    val numIdx = cursor.getColumnIndex(android.provider.ContactsContract.CommonDataKinds.Phone.NUMBER)
                    if (numIdx != -1) {
                        return cursor.getString(numIdx)
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Contacts query failed: ${e.message}")
        }
        return null
    }

    private fun createFile(fileName: String, content: String) {
        val hasStoragePermission = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            android.os.Environment.isExternalStorageManager()
        } else {
            ContextCompat.checkSelfPermission(context, Manifest.permission.WRITE_EXTERNAL_STORAGE) == PackageManager.PERMISSION_GRANTED
        }

        if (!hasStoragePermission) {
            Log.w(TAG, "Storage permission not granted")
            showStatus("Storage permission required to create files")
            speakReply("Please grant storage permission in settings first.")
            return
        }

        try {
            val dir = android.os.Environment.getExternalStoragePublicDirectory(android.os.Environment.DIRECTORY_DOWNLOADS)
            if (!dir.exists()) {
                dir.mkdirs()
            }
            val file = java.io.File(dir, fileName)
            file.writeText(content)
            Log.d(TAG, "File created: ${file.absolutePath}")
            showStatus("Saved in Downloads: $fileName")
            speakReply("File $fileName create kar diya hai.")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to write file: ${e.message}")
            showStatus("File write failed")
            speakReply("File write fail ho gaya.")
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
        recognizer?.destroy()
        recognizer = null
    }
}
