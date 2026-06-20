package com.jarvis.assistant.services

import android.content.Context
import android.os.Bundle
import android.service.voice.VoiceInteractionSession
import android.service.voice.VoiceInteractionSessionService
import android.speech.RecognizerIntent
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import com.jarvis.assistant.R
import com.jarvis.assistant.overlay.OverlayViewController

/**
 * JarvisSessionService
 *
 * Android calls this service when the assistant is invoked. It creates
 * a [VoiceInteractionSession] which manages the assistant's full lifecycle:
 *
 *   onCreate() → onCreateContentView() → onShow() → onHide() → onDestroy()
 *
 * Each session runs in its own system-managed window. This service is
 * declared with BIND_VOICE_INTERACTION permission and is referenced from
 * res/xml/voice_interaction.xml via android:sessionService.
 */
class JarvisSessionService : VoiceInteractionSessionService() {

    override fun onNewSession(args: Bundle?): VoiceInteractionSession {
        Log.d(TAG, "New session created")
        return JarvisAssistantSession(this)
    }

    companion object {
        private const val TAG = "JarvisSession"
    }
}

/**
 * JarvisAssistantSession
 *
 * The actual assistant session produced by [JarvisSessionService].
 * It manages:
 * - The overlay UI (microphone, waveform, status text)
 * - Speech recognition lifecycle
 * - Backend communication
 * - Device actions (torch, volume, navigation)
 */
class JarvisAssistantSession(context: Context) : VoiceInteractionSession(context) {

    companion object {
        private const val TAG = "JarvisSession"
    }

    private var controller: OverlayViewController? = null

    /**
     * Called when the system creates the session's content view.
     * We inflate our overlay UI.
     */
    override fun onCreateContentView(): View {
        val inflater = LayoutInflater.from(context)
        val view = inflater.inflate(R.layout.overlay_bottom_sheet, null)

        // Configure window layout params to slide from bottom, transparent background, match parent width
        window?.window?.let { w ->
            w.setGravity(android.view.Gravity.BOTTOM)
            w.setLayout(
                android.view.ViewGroup.LayoutParams.MATCH_PARENT,
                android.view.ViewGroup.LayoutParams.WRAP_CONTENT
            )
            w.setBackgroundDrawable(android.graphics.drawable.ColorDrawable(android.graphics.Color.TRANSPARENT))
        }

        controller = OverlayViewController(
            context = context,
            rootView = view,
            onDismiss = { hide() },
            session = this
        )
        controller?.init()
        return view
    }

    /**
     * Called when the session window is shown.
     * [args] may contain extras from the invoking app.
     * [showFlags] indicate how the session was triggered.
     */
    override fun onShow(args: Bundle?, showFlags: Int) {
        super.onShow(args, showFlags)
        Log.d(TAG, "Session shown, flags=$showFlags")

        // Handle any initial voice input that was passed with the invocation
        val voiceResults = args?.getStringArrayList(
            RecognizerIntent.EXTRA_RESULTS
        )
        if (!voiceResults.isNullOrEmpty()) {
            val initialText = voiceResults[0]
            Log.d(TAG, "Initial voice input: $initialText")
            controller?.processTextInput(initialText)
        } else {
            controller?.startListening()
        }
    }

    /**
     * Called when the session window is hidden.
     * Stops any ongoing speech recognition or audio playback.
     */
    override fun onHide() {
        super.onHide()
        controller?.stopListening()
    }

    /**
     * Called when the session is destroyed. Clean up all resources.
     */
    override fun onDestroy() {
        super.onDestroy()
        controller?.destroy()
        controller = null
    }
}
