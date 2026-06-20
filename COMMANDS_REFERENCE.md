# ⚡ JARVIS PCOS Command Reference & Intent Guide

This document provides a comprehensive reference for all natural language commands supported by the **JARVIS Personal Cognitive Operating System (PCOS)**. 

JARVIS translates natural language queries into structured JSON payloads on the backend and executes them as native Android Intents or web-based fallbacks on the frontend.

---

## 📋 Table of Contents
1. [Android Integration Commands](#1-android-integration-commands) (Alarms, Phone Calls, Contacts, Apps, YouTube)
2. [Storage & File Control Commands](#2-storage--file-control-commands) (Create, Read, List, Delete Files)
3. [Device Controls](#3-device-controls) (Flashlight, WiFi, Volume, Battery)
4. [Cognitive & Assistant Commands](#4-cognitive--assistant-commands) (Goals, Reminders, Reflection, Search)

---

## 1. Android Integration Commands

These commands interface directly with native Android applications via the `AndroidBridge` intent execution layer.

### ⏰ Set Alarm
Configures a physical alarm inside the device's default clock app.
* **Keywords**: `alarm`, `set alarm`, `wake me up`, `alert`
* **Backend Action**: `SET_ALARM`
* **JSON Intent Payload**:
  ```json
  {
    "action": "SET_ALARM",
    "package": "com.android.deskclock",
    "extras": {
      "hour": 7,
      "minute": 30,
      "label": "Gym Time",
      "skip_ui": false
    }
  }
  ```
* **Examples**:
  * *"set an alarm for 7:30 in the morning called Gym"*
  * *"wake me up at 6:15 AM"*
  * *"set alarm for 10 PM"*

### 📞 Make Call
Initiates direct phone calls or dials a number.
* **Keywords**: `call`, `dial`, `phone`
* **Backend Action**: `CALL`
* **JSON Intent Payload**:
  ```json
  {
    "action": "CALL",
    "data": "tel:+15550192834",
    "package": "com.android.phone",
    "extras": {}
  }
  ```
* **Examples**:
  * *"call +1 (555) 019-2834"*
  * *"dial 9876543210"*

### 👤 Access Contacts
Searches your address book and dials contacts by name.
* **Keywords**: `call [name]`, `ring [name]`
* **Backend Action**: `call_contact`
* **JSON Intent Payload**:
  ```json
  {
    "action": "call_contact",
    "payload": {
      "name": "Mom"
    }
  }
  ```
* **Client Behavior**: Resolves contact list locally via `AndroidBridge.getContacts()`, performs a fuzzy match on the name, extracts the phone number, and initiates the call.
* **Examples**:
  * *"call Mom"*
  * *"ring John Doe"*

### 🚀 Open App
Launches installed Android apps directly by package name.
* **Keywords**: `open`, `launch`, `khol`
* **Backend Action**: `LAUNCH_APP`
* **JSON Intent Payload**:
  ```json
  {
    "action": "LAUNCH_APP",
    "package": "com.spotify.music",
    "category": "android.intent.category.LAUNCHER",
    "extras": {}
  }
  ```
* **Examples**:
  * *"open Spotify"*
  * *"launch WhatsApp"*
  * *"Chrome khol"*

### 🎵 YouTube Playback
Launches YouTube and directly plays videos or search queries.
* **Keywords**: `play [song]`, `youtube`, `gaana laga`
* **Backend Action**: `PLAY_VIDEO`
* **JSON Intent Payload**:
  ```json
  {
    "action": "VIEW",
    "data": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "package": "com.google.android.youtube",
    "extras": {
      "is_video": true
    }
  }
  ```
* **Examples**:
  * *"Arijit Singh ka song laga do"*
  * *"Play Tum Hi Ho on YouTube"*

---

## 2. Storage & File Control Commands

Utilizes the `MANAGE_EXTERNAL_STORAGE` permission granted to the APK for full file system read, write, and directory control on your device.

### 📝 Create File
Writes text content to a file at a specific path.
* **Keywords**: `write file`, `make file`, `create file`
* **Backend Action**: `create_file`
* **JSON Intent Payload**:
  ```json
  {
    "action": "create_file",
    "payload": {
      "path": "/storage/emulated/0/Documents/notes.txt",
      "content": "Hello World"
    }
  }
  ```
* **Examples**:
  * *"create a file at /storage/emulated/0/test.txt with content hello world"*
  * *"save a note to /sdcard/todo.txt saying buy milk today"*

### 📖 Read File
Reads and displays the content of a local file.
* **Keywords**: `read file`, `cat file`, `view file`
* **Backend Action**: `read_file`
* **JSON Intent Payload**:
  ```json
  {
    "action": "read_file",
    "payload": {
      "path": "/storage/emulated/0/Documents/notes.txt"
    }
  }
  ```
* **Examples**:
  * *"read the file /storage/emulated/0/todo.txt"*
  * *"show me content of /sdcard/notes.txt"*

### 📁 List Directory
Lists all files and folders inside a directory.
* **Keywords**: `list folder`, `list directory`, `show files`
* **Backend Action**: `list_directory`
* **JSON Intent Payload**:
  ```json
  {
    "action": "list_directory",
    "payload": {
      "path": "/storage/emulated/0/Documents"
    }
  }
  ```
* **Examples**:
  * *"list files in /storage/emulated/0/Download"*
  * *"show folder /sdcard"*

### ❌ Delete File
Deletes a file from the device storage.
* **Keywords**: `delete file`, `remove file`, `rm file`
* **Backend Action**: `delete_file`
* **JSON Intent Payload**:
  ```json
  {
    "action": "delete_file",
    "payload": {
      "path": "/storage/emulated/0/test.txt"
    }
  }
  ```
* **Examples**:
  * *"delete file /storage/emulated/0/todo.txt"*
  * *"remove /sdcard/notes.txt"*

---

## 3. Device Controls

Commands designed to manage physical properties of the Android phone.

| Command | Action | Payload / State | Example | Web Fallback / Behavior |
|---------|--------|-----------------|---------|-------------------------|
| **Flashlight On** | `torch` | `"on"` | *"turn on flashlight"* | Toggles LED flash via getUserMedia camera stream |
| **Flashlight Off** | `torch` | `"off"` | *"turn off torch"* | Stops camera LED stream |
| **WiFi Settings** | `wifi` | `"open_settings"` | *"turn on wifi"* | Redirects to standard Android Wi-Fi settings panel |
| **Battery Status**| `none` | N/A | *"battery percentage"* | Queries web battery API (`navigator.getBattery`) |
| **Volume Up** | `volume`| `"up"` | *"volume up"* | Suggests side button adjustments |
| **Volume Down** | `volume`| `"down"`| *"volume down"* | Suggests side button adjustments |
| **Camera** | `camera`| N/A | *"open camera"* | Triggers file upload input with camera capture attribute |

---

## 4. Cognitive & Assistant Commands

Non-device commands routed to the specialized agents in the backend.

### 🎯 Goal Tracking
* **Keywords**: `goal`, `task`, `project`, `todo`
* **Examples**:
  * *"set a new goal: build AGI in 2026"*
  * *"complete my active goal"*
  * *"what are my current goals?"*

### 🔔 Calendar & Reminders
* **Keywords**: `remind me`, `schedule`, `event`, `appointment`
* **Examples**:
  * *"remind me to call John at 5:30 PM"*
  * *"upcoming reminders show karo"*
  * *"schedule a meeting tomorrow at 10 AM"*

### 📋 Reflection Engine
* **Keywords**: `daily review`, `summary`, `reflect`
* **Examples**:
  * *"aaj ka daily review do"*
  * *"reflect on this session"*
  * *"din ka summary review karo"*

### 🔍 Search & Web Research
* **Keywords**: `search`, `find`, `research`, `google`
* **Examples**:
  * *"search for latest AI developments"*
  * *"research the history of quantum computing"*
  * *"what is the weather today?"*
