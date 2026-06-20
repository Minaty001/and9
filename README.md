# 🧠 JARVIS PCOS (Personal Cognitive Operating System) — Definitive Repository

Welcome to the official production repository for **JARVIS PCOS (Neural Engine v4)**. This project contains the high-performance Flask AI orchestrator, dynamic intent execution engines, and local custom Android client wrappers.

> [!IMPORTANT]
> **Use the `and9` repository (`/root/and9`) always** for backend developments, intent executor tasks, custom permission overlays, and Android app updates.

---

## ⚡ Supported Assistant Commands

JARVIS parses natural language requests and converts them into intent payloads executed natively on Android or via web fallbacks:

*   **Android Operations**: Set Alarms, Make Calls, Search Address Contacts, Open Android Apps, play YouTube Videos directly.
*   **Storage Control**: Full `/storage/emulated/0` file systems permissions (Write, Read, List Folders, Delete Files).
*   **Device Management**: Flashlight toggles, WiFi settings panel, Battery state queries, Volume level, and Camera access.
*   **Cognitive Pipelines**: Goal tracking, Scheduled Event/Reminder builders, Session Reflection digests, and Web research engines.

For exact API payloads, JSON structures, and natural language command examples, refer to the **[Commands Reference & Intent Guide](COMMANDS_REFERENCE.md)**.

---

## 🚀 Backend Quick Start

Ensure Python 3.11+ is installed. Follow these steps to spin up the Neural Engine orchestrator:

```bash
# 1. Install required dependencies
pip install -r requirements.txt

# 2. Configure environment variables (Supabase, LLM providers, keys)
cp .env.example .env
# Edit .env and enter your key credentials

# 3. Spin up the orchestrator server
gunicorn app.main:app
```

---

## 📱 Android Client — Build & Setup

The Android interface is in the `android/` directory.

### Native Source Build
1. Locate or create `android/local.properties`.
2. Configure your server endpoints:
   ```properties
   JARVIS_BASE_URL=https://your-backend-app.onrender.com/api
   ```
3. Compile the debug APK:
   ```bash
   cd android
   ./gradlew assembleDebug
   # Build output: android/app/build/outputs/apk/debug/app-debug.apk
   ```

### 📦 Custom User APK Rebuilding (Automation)
If you have an existing signed `jarvis.apk` at `/storage/emulated/0/jarvis.apk` and need to safely strip unwanted digital assistant (permanent power button) overrides and inject system permissions, run:

```bash
python3 scripts/rebuild_user_apk.py
```

**What this automation script does:**
1. **Decompiles / Extracts** the raw apk assets.
2. **Removes the Digital Assistant service** structure from the Manifest.
3. **Injects high-access permissions** (`MANAGE_EXTERNAL_STORAGE`, `CALL_PHONE`, `READ_CONTACTS`).
4. **Repackages, aligns, and signs** with a generated cryptographic key.
5. **Replaces the file** at `/storage/emulated/0/jarvis.apk` with the final, optimized build.

---

## 🏗 System Architecture

```
and9/
  ├── android/             (Native Android client source app)
  ├── app/
  │    ├── agents/         (LLM orchestrators & coding/research agents)
  │    ├── api/            (REST endpoints & socket routers)
  │    ├── core/           (memory registers, goals, events, reflection)
  │    ├── skills/         (command actions & JSON intent builders)
  │    └── templates/      (control dashboard frontend)
  ├── scripts/             (automated APK patching utilities)
  ├── COMMANDS_REFERENCE.md (extensive usage command catalog)
  └── AUDIT.md             (system design audit & structural findings)
```

---

## 📄 License
Licensed under the MIT License. Built with love by **Minaty001**.
