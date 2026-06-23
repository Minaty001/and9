package com.jarvis.assistant.voice

import android.util.Log
import kotlin.math.min

/**
 * WakeWordDetector
 *
 * Local, zero-network wake word detection with confidence scoring.
 * Supports multiple wake words with fuzzy matching to handle STT variations.
 *
 * Wake words: "hello", "jarvis", "assistant", "hey jarvis", "ok jarvis"
 *
 * Confidence scoring:
 *   Exact match          → 1.0  (execute immediately)
 *   Levenshtein ≤ 1      → 0.95 (very likely correct)
 *   Levenshtein ≤ 2      → 0.85 (probably correct)
 *   Phonetic match       → 0.70 (sounds like)
 *   Partial match        → 0.65 (contains wake word)
 *   Threshold: ≥ 0.60 triggers activation
 */
class WakeWordDetector {

    companion object {
        private const val TAG = "WakeWordDetector"
        private const val ACTIVATION_THRESHOLD = 0.60f

        // Primary wake words (case-insensitive)
        val WAKE_WORDS = listOf(
            "hello",
            "jarvis",
            "assistant",
            "hey jarvis",
            "ok jarvis",
            "okay jarvis",
            "jai",          // common STT mishearing of "Jarvis"
            "java",         // common STT mishearing of "Jarvis"
        )

        // Phonetic mappings — common STT errors for wake words
        private val PHONETIC_VARIANTS = mapOf(
            "jarvis" to listOf("jarwis", "jarvas", "jarvas", "jarwes", "garvis", "darvis", "harvest"),
            "hello"  to listOf("helo", "hellow", "helo", "ellow", "yelllo"),
            "assistant" to listOf("asistant", "asisstant", "asistent", "assitant"),
            "hey jarvis" to listOf("hay jarvis", "hey java", "hey garvis", "hey jarwis"),
        )
    }

    data class WakeWordResult(
        val detected: Boolean,
        val confidence: Float,
        val matchedWord: String,
        val inputText: String,
        val matchType: MatchType
    )

    enum class MatchType {
        EXACT, NEAR_EXACT, FUZZY, PHONETIC, PARTIAL, NONE
    }

    /**
     * Check if the given STT text contains a wake word.
     *
     * @param sttText Raw STT output from Android SpeechRecognizer
     * @return WakeWordResult with detection status and confidence
     */
    fun detect(sttText: String): WakeWordResult {
        val normalized = sttText.lowercase().trim()
        Log.d(TAG, "Checking wake word in: '$normalized'")

        // 1. Exact match
        for (wakeWord in WAKE_WORDS) {
            if (normalized == wakeWord || normalized.startsWith("$wakeWord ")) {
                Log.d(TAG, "EXACT match: '$wakeWord'")
                return WakeWordResult(true, 1.0f, wakeWord, sttText, MatchType.EXACT)
            }
        }

        // 2. Near-exact (Levenshtein ≤ 1)
        for (wakeWord in WAKE_WORDS) {
            val words = normalized.split(" ")
            for (word in words) {
                val dist = levenshtein(word, wakeWord)
                if (dist <= 1 && wakeWord.length >= 4) {
                    Log.d(TAG, "NEAR_EXACT match: '$word' ~ '$wakeWord' (dist=$dist)")
                    return WakeWordResult(true, 0.95f, wakeWord, sttText, MatchType.NEAR_EXACT)
                }
            }
        }

        // 3. Fuzzy match (Levenshtein ≤ 2)
        for (wakeWord in WAKE_WORDS) {
            val words = normalized.split(" ")
            for (word in words) {
                val dist = levenshtein(word, wakeWord)
                if (dist <= 2 && wakeWord.length >= 5) {
                    Log.d(TAG, "FUZZY match: '$word' ~ '$wakeWord' (dist=$dist)")
                    return WakeWordResult(true, 0.85f, wakeWord, sttText, MatchType.FUZZY)
                }
            }
        }

        // 4. Phonetic variant match
        for ((wakeWord, variants) in PHONETIC_VARIANTS) {
            for (variant in variants) {
                if (normalized.contains(variant)) {
                    Log.d(TAG, "PHONETIC match: '$variant' → '$wakeWord'")
                    return WakeWordResult(true, 0.70f, wakeWord, sttText, MatchType.PHONETIC)
                }
            }
        }

        // 5. Partial containment
        for (wakeWord in WAKE_WORDS) {
            if (normalized.contains(wakeWord)) {
                Log.d(TAG, "PARTIAL match: contains '$wakeWord'")
                return WakeWordResult(true, 0.65f, wakeWord, sttText, MatchType.PARTIAL)
            }
        }

        Log.d(TAG, "No wake word detected in: '$normalized'")
        return WakeWordResult(false, 0.0f, "", sttText, MatchType.NONE)
    }

    /**
     * Extract the command portion after the wake word.
     *
     * Example: "hey jarvis open whatsapp" → "open whatsapp"
     */
    fun extractCommand(sttText: String): String {
        val normalized = sttText.lowercase().trim()

        // Try to find and strip wake word from beginning
        for (wakeWord in WAKE_WORDS.sortedByDescending { it.length }) {
            if (normalized.startsWith(wakeWord)) {
                val command = normalized.removePrefix(wakeWord).trim()
                if (command.isNotEmpty()) {
                    Log.d(TAG, "Extracted command: '$command' (stripped '$wakeWord')")
                    return command
                }
            }
        }
        // If wake word not at start, return full text
        return sttText.trim()
    }

    /**
     * Returns true if the text exceeds the activation threshold.
     */
    fun isActivated(sttText: String): Boolean {
        val result = detect(sttText)
        return result.detected && result.confidence >= ACTIVATION_THRESHOLD
    }

    // ── Levenshtein Distance ─────────────────────────────────────

    private fun levenshtein(a: String, b: String): Int {
        val m = a.length
        val n = b.length
        val dp = Array(m + 1) { IntArray(n + 1) }
        for (i in 0..m) dp[i][0] = i
        for (j in 0..n) dp[0][j] = j
        for (i in 1..m) {
            for (j in 1..n) {
                dp[i][j] = if (a[i - 1] == b[j - 1]) {
                    dp[i - 1][j - 1]
                } else {
                    1 + min(dp[i - 1][j - 1], min(dp[i - 1][j], dp[i][j - 1]))
                }
            }
        }
        return dp[m][n]
    }
}
