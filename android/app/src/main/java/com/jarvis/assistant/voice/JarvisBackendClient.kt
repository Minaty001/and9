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
 * Supports three AI providers (auto-detected):
 *   1. Custom Flask backend at JARVIS_BASE_URL (default)
 *   2. Groq API (set groqApiKey in local.properties)
 *   3. OpenAI-compatible API (set openaiApiKey in local.properties)
 *
 * Provider selection priority:
 *   GROQ_API_KEY is set → Groq
 *   OPENAI_API_KEY is set → OpenAI
 *   Neither → Custom Flask backend
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
        get() = prefs.getString("backend_url", BuildConfig.JARVIS_BASE_URL) ?: BuildConfig.JARVIS_BASE_URL
    
    private val groqApiKey: String
        get() = prefs.getString("groq_api_key", BuildConfig.GROQ_API_KEY) ?: BuildConfig.GROQ_API_KEY
        
    private val openaiApiKey: String
        get() = prefs.getString("openai_api_key", BuildConfig.OPENAI_API_KEY) ?: BuildConfig.OPENAI_API_KEY

    private val groqModel: String = try {
        context.packageManager
            .getApplicationInfo(context.packageName, android.content.pm.PackageManager.GET_META_DATA)
            .metaData?.getString("groqModel") ?: "mixtral-8x7b-32768"
    } catch (_: Exception) { "mixtral-8x7b-32768" }

    private val openaiModel: String = try {
        context.packageManager
            .getApplicationInfo(context.packageName, android.content.pm.PackageManager.GET_META_DATA)
            .metaData?.getString("openaiModel") ?: "gpt-4o-mini"
    } catch (_: Exception) { "gpt-4o-mini" }

    private val openaiBaseUrl: String = try {
        context.packageManager
            .getApplicationInfo(context.packageName, android.content.pm.PackageManager.GET_META_DATA)
            .metaData?.getString("openaiBaseUrl") ?: "https://api.openai.com/v1"
    } catch (_: Exception) { "https://api.openai.com/v1" }

    private fun useGroq(): Boolean = groqApiKey.isNotEmpty()
    private fun useOpenAI(): Boolean = !useGroq() && openaiApiKey.isNotEmpty()

    /**
     * Send [text] to the configured AI backend and deliver the reply to [onResult].
     */
    fun chat(text: String, onResult: (String, JSONObject?) -> Unit) {
        DebugLogger.log(TAG, "User: $text")
        when {
            useGroq() -> chatGroq(text, onResult)
            useOpenAI() -> chatOpenAI(text, onResult)
            else -> chatCustomBackend(text, onResult)
        }
    }

    // ── Custom Flask Backend ──────────────────────────────────────

    private fun chatCustomBackend(text: String, onResult: (String, JSONObject?) -> Unit) {
        val url = if (baseUrl.endsWith("/")) "${baseUrl}chat" else "$baseUrl/chat"
        DebugLogger.log(TAG, "Calling backend: $url")
        
        val json = JSONObject().put("message", text).toString()
        val body = json.toRequestBody("application/json".toMediaType())

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

    // ── Groq API ──────────────────────────────────────────────────

    private fun chatGroq(text: String, onResult: (String, JSONObject?) -> Unit) {
        val json = JSONObject().apply {
            put("model", groqModel)
            put("messages", org.json.JSONArray().apply {
                put(JSONObject().apply {
                    put("role", "system")
                    put("content", buildSystemPrompt())
                })
                put(JSONObject().apply {
                    put("role", "user")
                    put("content", text)
                })
            })
            put("temperature", 0.7)
            put("max_tokens", 1024)
        }.toString()

        val request = Request.Builder()
            .url("https://api.groq.com/openai/v1/chat/completions")
            .header("Authorization", "Bearer $groqApiKey")
            .header("Content-Type", "application/json")
            .post(json.toRequestBody("application/json".toMediaType()))
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                Log.e(TAG, "Groq call failed: ${e.message}")
                onResult("AI service unavailable. Please check connection.", null)
            }

            override fun onResponse(call: Call, response: Response) {
                try {
                    val bodyStr = response.body?.string() ?: "{}"
                    val obj = JSONObject(bodyStr)
                    val reply = obj
                        .optJSONArray("choices")
                        ?.optJSONObject(0)
                        ?.optJSONObject("message")
                        ?.optString("content", "No response.")
                        ?: "No response."
                    onResult(reply, obj)
                } catch (e: Exception) {
                    Log.e(TAG, "Groq parse error: ${e.message}")
                    onResult("Something went wrong.", null)
                } finally {
                    response.close()
                }
            }
        })
    }

    // ── OpenAI-compatible API ─────────────────────────────────────

    private fun chatOpenAI(text: String, onResult: (String, JSONObject?) -> Unit) {
        val json = JSONObject().apply {
            put("model", openaiModel)
            put("messages", org.json.JSONArray().apply {
                put(JSONObject().apply {
                    put("role", "system")
                    put("content", buildSystemPrompt())
                })
                put(JSONObject().apply {
                    put("role", "user")
                    put("content", text)
                })
            })
            put("temperature", 0.7)
            put("max_tokens", 1024)
        }.toString()

        val request = Request.Builder()
            .url("$openaiBaseUrl/chat/completions")
            .header("Authorization", "Bearer $openaiApiKey")
            .header("Content-Type", "application/json")
            .post(json.toRequestBody("application/json".toMediaType()))
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                Log.e(TAG, "OpenAI call failed: ${e.message}")
                onResult("AI service unavailable. Please check connection.", null)
            }

            override fun onResponse(call: Call, response: Response) {
                try {
                    val bodyStr = response.body?.string() ?: "{}"
                    val obj = JSONObject(bodyStr)
                    val reply = obj
                        .optJSONArray("choices")
                        ?.optJSONObject(0)
                        ?.optJSONObject("message")
                        ?.optString("content", "No response.")
                        ?: "No response."
                    onResult(reply, obj)
                } catch (e: Exception) {
                    Log.e(TAG, "OpenAI parse error: ${e.message}")
                    onResult("Something went wrong.", null)
                } finally {
                    response.close()
                }
            }
        })
    }

    private fun getBatteryInfo(): String {
        return try {
            val intent = context.registerReceiver(null, android.content.IntentFilter(android.content.Intent.ACTION_BATTERY_CHANGED))
            val level = intent?.getIntExtra(android.os.BatteryManager.EXTRA_LEVEL, -1) ?: -1
            val scale = intent?.getIntExtra(android.os.BatteryManager.EXTRA_SCALE, -1) ?: -1
            val status = intent?.getIntExtra(android.os.BatteryManager.EXTRA_STATUS, -1) ?: -1
            val isCharging = status == android.os.BatteryManager.BATTERY_STATUS_CHARGING ||
                    status == android.os.BatteryManager.BATTERY_STATUS_FULL
            val batteryPct = if (level >= 0 && scale > 0) (level * 100 / scale.toFloat()).toInt() else -1
            "$batteryPct% (${if (isCharging) "charging" else "not charging"})"
        } catch (_: Exception) { "Unknown" }
    }

    private fun getFreeStorageGb(): String {
        return try {
            val stat = android.os.StatFs(android.os.Environment.getDataDirectory().path)
            val bytesAvailable = stat.blockSizeLong * stat.availableBlocksLong
            val gb = bytesAvailable / (1024f * 1024f * 1024f)
            String.format(java.util.Locale.US, "%.2f GB free", gb)
        } catch (_: Exception) { "Unknown" }
    }

    // ── System Prompt ─────────────────────────────────────────────

    private fun buildSystemPrompt(): String = buildString {
        appendLine("You are JARVIS, an AI assistant running on Android. You control the device.")
        appendLine("")
        appendLine("DEVICE STATUS:")
        appendLine("- Model: ${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL}")
        appendLine("- Android Version: ${android.os.Build.VERSION.RELEASE}")
        appendLine("- Battery Level: ${getBatteryInfo()}")
        appendLine("- Free Storage: ${getFreeStorageGb()}")
        appendLine("")
        appendLine("CAPABILITIES:")
        appendLine("- Open apps by package name or app name")
        appendLine("- Close apps and go to home screen")
        appendLine("- Control flashlight/torch (on/off/strobe)")
        appendLine("- Adjust volume (up/down/mute/max or a percentage like \"50\")")
        appendLine("- Open browser with URLs")
        appendLine("- Search the web")
        appendLine("- Open camera")
        appendLine("- Open settings panels (wifi, bluetooth, display/brightness, sound, battery, apps, accessibility, assistant)")
        appendLine("- Go back, go home, open recent apps")
        appendLine("- Take screenshots")
        appendLine("- Open notifications")
        appendLine("")
        appendLine("To trigger a device action, end your response with a JSON block:")
        appendLine("```json")
        appendLine("{\"action\": \"open_app\", \"payload\": \"com.whatsapp\"}")
        appendLine("```")
        appendLine("")
        appendLine("Available actions: open_app, close_app, home, back, torch (on/off/strobe), volume (up/down/mute/max/0-100), browser (url), search (query), camera, settings (panel), wifi, screenshot, notifications")
        appendLine("")
        appendLine("Keep responses concise. Respond in Hinglish (Hindi + English mix).")
    }
}
