package com.jarvis.assistant.voice

import android.util.Log
import java.text.SimpleDateFormat
import java.util.*

/**
 * Simple in-memory logger to collect the last 100 log entries
 * for display in the app's debug view.
 */
object DebugLogger {
    private const val MAX_LOGS = 100
    private val logs = mutableListOf<String>()
    private val dateFormat = SimpleDateFormat("HH:mm:ss.SSS", Locale.getDefault())

    fun log(tag: String, message: String) {
        val time = dateFormat.format(Date())
        val entry = "[$time] $tag: $message"
        Log.d(tag, message)
        
        synchronized(logs) {
            logs.add(0, entry)
            if (logs.size > MAX_LOGS) {
                logs.removeAt(logs.size - 1)
            }
        }
    }

    fun getLogs(): List<String> {
        return synchronized(logs) { logs.toList() }
    }

    fun clear() {
        synchronized(logs) { logs.clear() }
    }
}
