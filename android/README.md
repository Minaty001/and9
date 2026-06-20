## JARVIS Android — Build Instructions

### 1. Set your backend URL
Edit `android/local.properties`:
```
JARVIS_BASE_URL=https://your-app.onrender.com/api
```
Or leave default (http://10.0.2.2:5000/api) for emulator → local Flask dev.

### 2. Build APK
```bash
cd android
./gradlew assembleDebug
# APK → android/app/build/outputs/apk/debug/app-debug.apk
```

### 3. Install
```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

### 4. Device Setup (one-time)
1. Open JARVIS app → complete setup wizard (grant Overlay + Mic)
2. Settings → Apps → Default Apps → Digital Assistant App → **JARVIS**

### 5. Use
Hold Power button (or swipe Assistant gesture) → JARVIS overlay appears + mic starts instantly.
