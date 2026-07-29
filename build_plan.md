# Master Plan: Build JARVIS PCOS Flutter APK

This document outlines the step-by-step master plan for building the custom Flutter client APK that connects to `localhost:8000` (mapped to `10.0.2.2:8000` in emulators).

---

## 📋 Phase 1: Environment & Project Setup
1. **Initialize Flutter Project**: Done (created at `/home/saifali/and9/flutter_client`).
2. **Align File Ownership**: Change ownership of the generated directory to the host user to bypass root permissions:
   ```bash
   docker run --rm -v /home/saifali/and9:/workspace alpine chown -R 1000:1000 /workspace/flutter_client
   ```
3. **Configure API Endpoints**: Set default server URL to `http://10.0.2.2:8000` (allowing fallback dynamically via UI configuration).

---

## 🛠️ Phase 2: Configuration & Permissions
1. **Target API Level**:
   - `minSdk = 28` (Android 9)
   - `targetSdk = 36` (Android 16 compatibility)
   - `compileSdk = 36`
2. **Declare Permissions in `AndroidManifest.xml`**:
   - `INTERNET` (API connection)
   - `RECORD_AUDIO` (voice support)
   - `READ_CONTACTS` & `WRITE_CONTACTS` (contact lookup)
   - `CALL_PHONE` (direct dialing)
   - `SYSTEM_ALERT_WINDOW` (overlay overlay UI)
   - `POST_NOTIFICATIONS` (alerts and background status)
   - `MANAGE_EXTERNAL_STORAGE` (file system control)
3. **Enable Cleartext HTTP Traffic**:
   - Set `android:usesCleartextTraffic="true"` in the application tag to allow `http://localhost:8000` and `http://10.0.2.2:8000` cleartext calls.

---

## 💻 Phase 3: Code Implementation
1. **Main UI (`lib/main.dart`)**:
   - Implement premium dark mode with gradient chat bubbles.
   - Design status indicator showing server status (ONLINE / OFFLINE).
   - Incorporate a settings config to update the URL.
   - Include a permission request button using `permission_handler`.
   - Parse response intents (e.g. `CALL`, `PLAY_VIDEO`) to launch corresponding device actions.
2. **Dependencies (`pubspec.yaml`)**:
   - Add `http`, `permission_handler`, `shared_preferences`, and `url_launcher`.

---

## ⚙️ Phase 4: Compilation via Docker
Since Java and Android SDK are not installed on the host, compilation runs inside a pre-configured Docker container:
```bash
docker run --rm -v /home/saifali/and9/flutter_client:/workspace -w /workspace ghcr.io/cirruslabs/flutter:stable flutter build apk --debug
```

---

## 🔍 Phase 5: Verification & Activity Log
1. **Confirm Output**: Verify that `app-debug.apk` is generated under `flutter_client/build/app/outputs/flutter-apk/`.
2. **Final Ownership Correction**: Run chown again to ensure permissions are accessible.
3. **Record Activity**: Write final execution status into `activities.db`.
