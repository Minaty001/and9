package com.jarvis.assistant.voice

import android.content.Context
import android.util.Log
import com.jarvis.assistant.BuildConfig
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * JarvisBackendClient
 *
 * Constitution V3 compliance:
 *   Rule 5 — Only the custom backend (server) calls LLMs, never the client.
 *   Rule 6 — No direct LLM access from Android app. All AI processing is
 *            routed through the server-side orchestrator pipeline.
 *
 * Provider: Custom Flask backend at JARVIS_BASE_URL (only).
 * Direct Groq/OpenAI calls have been removed — all LLM calls go through
 * the backend's truth-verified pipeline.
 */
class JarvisBackendClient(private val context: Context) {

    companion object {
        private const val TAG = "JarvisBackend"
        private const val PREFS_NAME = "JarvisPrefs"
    }

    private val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(15, TimeUnit.SECONDS)
        .build()

    private val baseUrl: String
        get() = prefs.getString("backend_url", BuildConfig.JARVIS_BASE_URL)
            ?: BuildConfig.JARVIS_BASE_URL

    /**
     * Send [text] to the backend server for processing.
     * All AI/LLM logic happens server-side through the orchestrator pipeline.
     * This client only handles the HTTP transport and response parsing.
     */
    fun chat(text: String, onResult: (String, JSONObject?) -> Unit) {
        DebugLogger.log(TAG, "User: $text")
        chatCustomBackend(text, null, onResult)
    }

    /**
     * Send [text] along with current [screenContext] (screen description
     * + foreground app) so the backend can tailor responses based on
     * what the user is seeing.
     *
     * The backend receives `"screen_context"` and `"current_app"` fields
     * alongside the message. Both are optional and fully backwards-compatible.
     */
    fun chatWithScreenContext(
        text: String,
        screenContext: String?,
        currentApp: String?,
        onResult: (String, JSONObject?) -> Unit
    ) {
        DebugLogger.log(TAG, "User: $text | Screen: ${currentApp ?: "?"}")
        chatCustomBackend(text, ScreenContextData(screenContext, currentApp), onResult)
    }

    private data class ScreenContextData(
        val screenDescription: String?,
        val currentApp: String?
    )

    // ── Custom Flask Backend (only provider) ───────────────────────

    private fun chatCustomBackend(
        text: String,
        screenContext: ScreenContextData?,
        onResult: (String, JSONObject?) -> Unit
    ) {
        val url = if (baseUrl.endsWith("/")) "${baseUrl}chat" else "$baseUrl/chat"
        DebugLogger.log(TAG, "Calling backend: $url")

        val json = JSONObject().put("message", text)
        // Attach optional screen context for accessibility-aware responses
        screenContext?.let { ctx ->
            ctx.screenDescription?.let { json.put("screen_context", it) }
            ctx.currentApp?.let { json.put("current_app", it) }
        }
        val body = json.toString().toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url(url)
            .post(body)
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                DebugLogger.log(TAG, "Backend call failed: ${e.message}")
                onResult("Network error. Please check connection.", null)
            }

            override fun onResponse(call: Call, response: Response) {
                try {
                    val bodyStr = response.body?.string() ?: "{}"
                    DebugLogger.log(TAG, "Backend response: $bodyStr")
                    val obj = JSONObject(bodyStr)
                    val reply = obj.optString("reply", "No response.")
                    onResult(reply, obj)
                } catch (e: Exception) {
                    DebugLogger.log(TAG, "Parse error: ${e.message}")
                    onResult("Something went wrong.", null)
                } finally {
                    response.close()
                }
            }
        })
    }

    // ── Priority 6: Dynamic Package Sync ───────────────────────────

    fun syncApps(appsJson: JSONObject) {
        val url = if (baseUrl.endsWith("/")) "${baseUrl}and9/apps" else "$baseUrl/and9/apps"
        val body = appsJson.toString().toRequestBody("application/json".toMediaType())
        val request = Request.Builder().url(url).post(body).build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                DebugLogger.log(TAG, "Failed to sync apps: ${e.message}")
            }
            override fun onResponse(call: Call, response: Response) {
                DebugLogger.log(TAG, "Apps synced. Status: ${response.code}")
                response.close()
            }
        })
    }

    // ── REMOVED (Constitution V3 Rule 5/6) ─────────────────────────
    // chatGroq() — removed. Android must never call LLM directly.
    // chatOpenAI() — removed. Android must never call LLM directly.
    // buildSystemPrompt() — removed. System prompt is built server-side
    //   by the orchestration pipeline with truth-verified context.
    // ────────────────────────────────────────────────────────────────
}
