package com.jarvis.assistant

import android.Manifest
import android.app.role.RoleManager
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.jarvis.assistant.services.JarvisVoiceInteractionService
import com.jarvis.assistant.services.ContinuousListeningService
import com.jarvis.assistant.voice.DebugLogger
import android.os.Environment
import android.content.pm.PackageManager

/**
 * SetupActivity
 *
 * Handles five setup tasks:
 *   1. RECORD_AUDIO permission (microphone for speech recognition)
 *   2. CAMERA permission (torch support)
 *   3. Set JARVIS as default Digital Assistant App
 *   4. Enable JARVIS Accessibility Service
 *   5. Configure Backend URL and API Keys
 */
class SetupActivity : AppCompatActivity() {

    private lateinit var statusCamera: TextView
    private lateinit var statusMic: TextView
    private lateinit var statusAssist: TextView
    private lateinit var statusAccessibility: TextView
    private lateinit var statusContacts: TextView
    private lateinit var statusStorage: TextView
    private lateinit var btnCamera: Button
    private lateinit var btnMic: Button
    private lateinit var btnAssist: Button
    private lateinit var btnAccessibility: Button
    private lateinit var btnContacts: Button
    private lateinit var btnStorage: Button

    private lateinit var editBackendUrl: EditText
    private lateinit var editGroqKey: EditText
    private lateinit var btnSaveConfig: Button
    private lateinit var btnShowLogs: Button

    private val requestMicPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { refreshStatus() }

    private val requestCameraPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { refreshStatus() }

    private val requestContactsPermissions = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { refreshStatus() }

    private val requestNormalStoragePermissions = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { refreshStatus() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_setup)

        statusCamera = findViewById(R.id.statusCamera)
        statusMic = findViewById(R.id.statusMic)
        statusAssist = findViewById(R.id.statusAssist)
        statusAccessibility = findViewById(R.id.statusAccessibility)
        statusContacts = findViewById(R.id.statusContacts)
        statusStorage = findViewById(R.id.statusStorage)
        btnCamera = findViewById(R.id.btnGrantCamera)
        btnMic = findViewById(R.id.btnGrantMic)
        btnAssist = findViewById(R.id.btnSetAssistant)
        btnAccessibility = findViewById(R.id.btnEnableAccessibility)
        btnContacts = findViewById(R.id.btnGrantContacts)
        btnStorage = findViewById(R.id.btnGrantStorage)

        editBackendUrl = findViewById(R.id.editBackendUrl)
        editGroqKey = findViewById(R.id.editGroqKey)
        btnSaveConfig = findViewById(R.id.btnSaveConfig)
        btnShowLogs = findViewById(R.id.btnShowLogs)

        btnCamera.setOnClickListener {
            requestCameraPermission.launch(Manifest.permission.CAMERA)
        }

        btnMic.setOnClickListener {
            requestMicPermission.launch(Manifest.permission.RECORD_AUDIO)
        }

        btnAssist.setOnClickListener {
            openAssistantSettings()
        }

        btnAccessibility.setOnClickListener {
            openAccessibilitySettings()
        }

        btnContacts.setOnClickListener {
            requestContactsPermissions.launch(
                arrayOf(Manifest.permission.CALL_PHONE, Manifest.permission.READ_CONTACTS, Manifest.permission.WRITE_CONTACTS)
            )
        }

        btnStorage.setOnClickListener {
            openStorageSettings()
        }

        btnSaveConfig.setOnClickListener {
            saveConfiguration()
        }

        btnShowLogs.setOnClickListener {
            showDebugLogs()
        }

        loadConfiguration()
    }

    private fun loadConfiguration() {
        val prefs = getSharedPreferences("JarvisPrefs", MODE_PRIVATE)
        editBackendUrl.setText(prefs.getString("backend_url", BuildConfig.JARVIS_BASE_URL))
        editGroqKey.setText(prefs.getString("groq_api_key", BuildConfig.GROQ_API_KEY))
    }

    private fun saveConfiguration() {
        val url = editBackendUrl.text.toString().trim()
        val groqKey = editGroqKey.text.toString().trim()

        if (url.isEmpty()) {
            Toast.makeText(this, "Backend URL cannot be empty", Toast.LENGTH_SHORT).show()
            return
        }

        getSharedPreferences("JarvisPrefs", MODE_PRIVATE).edit().apply {
            putString("backend_url", url)
            putString("groq_api_key", groqKey)
            apply()
        }
        Toast.makeText(this, "Configuration saved", Toast.LENGTH_SHORT).show()
    }

    private fun showDebugLogs() {
        val logs = DebugLogger.getLogs().joinToString("\n")
        val dialogView = TextView(this).apply {
            text = if (logs.isEmpty()) "No logs yet." else logs
            setPadding(32, 32, 32, 32)
            textSize = 12f
            typeface = android.graphics.Typeface.MONOSPACE
            setTextColor(0xFFFFFFFF.toInt())
            setBackgroundColor(0xFF0A0D1A.toInt())
        }

        val scrollView = android.widget.ScrollView(this).apply {
            addView(dialogView)
        }

        AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Dialog)
            .setTitle("Debug Logs")
            .setView(scrollView)
            .setPositiveButton("Close", null)
            .setNeutralButton("Clear") { _, _ ->
                DebugLogger.clear()
            }
            .show()
    }

    override fun onResume() {
        super.onResume()
        refreshStatus()
    }

    private fun refreshStatus() {
        val hasCamera = ContextCompat.checkSelfPermission(
            this, Manifest.permission.CAMERA
        ) == android.content.pm.PackageManager.PERMISSION_GRANTED

        val hasMic = ContextCompat.checkSelfPermission(
            this, Manifest.permission.RECORD_AUDIO
        ) == android.content.pm.PackageManager.PERMISSION_GRANTED

        val isDefaultAssistant = JarvisVoiceInteractionService.isDefaultAssistant(this)

        val isAccessibilityEnabled = isAccessibilityServiceEnabled()

        val hasContacts = ContextCompat.checkSelfPermission(this, Manifest.permission.READ_CONTACTS) == PackageManager.PERMISSION_GRANTED &&
                ContextCompat.checkSelfPermission(this, Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED

        val hasStorage = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            Environment.isExternalStorageManager()
        } else {
            ContextCompat.checkSelfPermission(this, Manifest.permission.WRITE_EXTERNAL_STORAGE) == PackageManager.PERMISSION_GRANTED
        }

        if (hasMic) {
            ContinuousListeningService.start(this)
        }

        updateItem(statusCamera, btnCamera, hasCamera, "Camera permission")
        updateItem(statusMic, btnMic, hasMic, "Microphone permission")
        updateItem(statusAssist, btnAssist, isDefaultAssistant, "Default Digital Assistant App")
        updateItem(statusAccessibility, btnAccessibility, isAccessibilityEnabled, "Accessibility Service")
        updateItem(statusContacts, btnContacts, hasContacts, "Phone & Contacts permission")
        updateItem(statusStorage, btnStorage, hasStorage, "Full Storage permission")
    }

    private fun openStorageSettings() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            try {
                val intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION).apply {
                    data = Uri.parse("package:$packageName")
                }
                startActivity(intent)
            } catch (e: Exception) {
                try {
                    val intent = Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION)
                    startActivity(intent)
                } catch (_: Exception) {
                    val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                        data = Uri.fromParts("package", packageName, null)
                    }
                    startActivity(intent)
                }
            }
        } else {
            requestNormalStoragePermissions.launch(
                arrayOf(Manifest.permission.READ_EXTERNAL_STORAGE, Manifest.permission.WRITE_EXTERNAL_STORAGE)
            )
        }
    }

    private fun updateItem(status: TextView, btn: Button, granted: Boolean, label: String) {
        if (granted) {
            status.text = "✅ $label granted"
            status.setTextColor(0xFF00FF88.toInt())
            btn.visibility = View.GONE
        } else {
            status.text = "❌ $label required"
            status.setTextColor(0xFFFF4444.toInt())
            btn.visibility = View.VISIBLE
        }
    }

    private fun openAssistantSettings() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val roleManager = getSystemService(RoleManager::class.java)
            if (roleManager != null && !roleManager.isRoleHeld(RoleManager.ROLE_ASSISTANT)) {
                val requestIntent = roleManager.createRequestRoleIntent(RoleManager.ROLE_ASSISTANT)
                if (requestIntent != null) {
                    try {
                        startActivity(requestIntent)
                        return
                    } catch (_: Exception) {
                        // Fall through to manual settings if the request cannot be opened.
                    }
                }
            }
        }

        try {
            startActivity(Intent(Settings.ACTION_VOICE_INPUT_SETTINGS))
        } catch (_: Exception) {
            try {
                startActivity(Intent("com.android.settings.ASSIST_GESTURE_SETTINGS"))
            } catch (_: Exception) {
                try {
                    startActivity(Intent(Settings.ACTION_MANAGE_DEFAULT_APPS_SETTINGS))
                } catch (_: Exception) {
                    val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                        data = Uri.fromParts("package", packageName, null)
                    }
                    startActivity(intent)
                }
            }
        }
    }

    private fun openAccessibilitySettings() {
        try {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
        } catch (_: Exception) {
            val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                data = Uri.fromParts("package", packageName, null)
            }
            startActivity(intent)
        }
    }

    private fun isAccessibilityServiceEnabled(): Boolean {
        val enabledServices = Settings.Secure.getString(
            contentResolver,
            Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
        )
        return enabledServices?.contains(packageName) ?: false
    }
}
