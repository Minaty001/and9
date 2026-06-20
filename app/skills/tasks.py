"""
app/skills/tasks.py — Executable task functions.

All system-interaction functions in one place. Safe for Render (no hardware deps).
Platform-conditional code (Termux/Windows) is isolated to specific functions.
"""
import os
import sys
import subprocess
import json
import logging
import re
from datetime import datetime

from app.core.config import SERP_API_KEY, NEWS_API_KEY, NOTES_DIR, IS_TERMUX, IS_WINDOWS
from app.skills.intent_executor import IntentExecutor

logger = logging.getLogger(__name__)


# ── Web Search ─────────────────────────────────────────────────

def search_web(query: str) -> str:
    """Quick web search via SerpAPI."""
    if not SERP_API_KEY:
        return "Search not configured (SERP_API_KEY not set)."
    import requests
    try:
        resp = requests.get(
            "https://serpapi.com/search",
            params={"q": query, "api_key": SERP_API_KEY},
            timeout=8,
        ).json()
        answer = resp.get("answer_box", {}).get("answer")
        if answer:
            return str(answer)
        results = resp.get("organic_results", [])
        if results:
            return results[0].get("snippet", "") or results[0].get("title", "")
        return f"No results for '{query}'."
    except Exception as e:
        logger.warning(f"Search failed: {e}")
        return f"Search error: {e}"


def get_realtime_data(query: str) -> str:
    """Fetch real-time data from SerpAPI without opening a browser."""
    if not SERP_API_KEY:
        return search_web(query)  # fallback to web search
    import requests
    try:
        resp = requests.get(
            "https://serpapi.com/search",
            params={"q": query, "api_key": SERP_API_KEY, "num": 3},
            timeout=8,
        ).json()
        answer = resp.get("answer_box", {}).get("answer")
        if answer:
            return str(answer)
        kg = resp.get("knowledge_graph", {})
        if kg.get("description"):
            return kg["description"]
        results = resp.get("organic_results", [])
        if results:
            snippets = [r.get("snippet", "") for r in results[:3] if r.get("snippet")]
            if snippets:
                return " | ".join(snippets)
        return f"No data found for '{query}'."
    except Exception as e:
        return f"Search error: {e}"


# ── Image Generation ──────────────────────────────────────────

def generate_image_task(prompt: str) -> dict:
    """Generate an image using SeaArt API. Returns dict with result and image_url."""
    if not prompt:
        return {"result": "No image description provided.", "image_url": None}
    try:
        from app.skills.img import generate_image
        filepath, image_url = generate_image(prompt)
        if filepath and image_url:
            return {
                "result": f"Image generated: {prompt}",
                "image_url": image_url,
            }
        elif image_url:
            return {"result": f"Image generated: {prompt}", "image_url": image_url}
        return {"result": "Image generation failed. The AI art service may be busy, try again.", "image_url": None}
    except Exception as e:
        logger.exception("Image generation error")
        return {"result": f"Image error: {e}", "image_url": None}


# ── Time & Info ───────────────────────────────────────────────

def get_time() -> str:
    return datetime.now().strftime("%I:%M %p, %A %B %d, %Y")


def get_time_date() -> str:
    return get_time()


def get_system_info() -> str:
    import platform
    info = {
        "OS": f"{platform.system()} {platform.release()}",
        "Machine": platform.machine(),
        "Python": platform.python_version(),
    }
    return " | ".join(f"{k}: {v}" for k, v in info.items())


# ── News ──────────────────────────────────────────────────────

def get_news(topic: str = "") -> str:
    if not NEWS_API_KEY:
        return "News not configured (NEWS_API_KEY not set)."
    import requests
    try:
        params = {"apiKey": NEWS_API_KEY, "language": "en", "pageSize": 5}
        if topic:
            params["q"] = topic
            url = "https://newsapi.org/v2/everything"
        else:
            params["country"] = "in"
            url = "https://newsapi.org/v2/top-headlines"
        data = requests.get(url, params=params, timeout=8).json()
        articles = data.get("articles", [])
        if not articles:
            return "No news found."
        return "Latest News:\n" + "\n".join(
            f"{i}. {a.get('title', '')}" for i, a in enumerate(articles[:5], 1)
        )
    except Exception as e:
        return f"News error: {e}"


# ── Device / System Control ───────────────────────────────────

def parse_device_command_via_llm(query: str) -> dict:
    """Use the LLM to parse natural language device command into JSON action/payload."""
    from app.core.brain import ask_llm
    prompt = """Analyze the user's command and map it to one of the following structured actions:
1. set_alarm:
   {"action": "set_alarm", "payload": {"hour": int (0-23), "minute": int (0-59), "label": "string"}}
2. make_call:
   {"action": "make_call", "payload": {"number": "string (digits and + only)"}}
3. call_contact:
   {"action": "call_contact", "payload": {"name": "string (name of the contact to search)"}}
4. create_event:
   {"action": "create_event", "payload": {"title": "string", "time": "string (date/time)"}}
5. create_file:
   {"action": "create_file", "payload": {"path": "string (full destination path, e.g. /storage/emulated/0/Documents/notes.txt)", "content": "string (content to write)"}}
6. read_file:
   {"action": "read_file", "payload": {"path": "string (full path to read)"}}
7. list_directory:
   {"action": "list_directory", "payload": {"path": "string (full path to directory)"}}
8. delete_file:
   {"action": "delete_file", "payload": {"path": "string (full path to delete)"}}
9. none:
   If it doesn't match any of these.

Respond ONLY with a valid JSON object. Do not include markdown code block formatting or any other text.

Examples:
- "set an alarm for 7:30 in the morning called Gym"
  {"action": "set_alarm", "payload": {"hour": 7, "minute": 30, "label": "Gym"}}
- "call Mom"
  {"action": "call_contact", "payload": {"name": "Mom"}}
- "remind me to buy groceries tomorrow at 5 PM"
  {"action": "create_event", "payload": {"title": "buy groceries", "time": "tomorrow at 5 PM"}}
- "call +1 (555) 019-2834"
  {"action": "make_call", "payload": {"number": "+15550192834"}}
- "write a file to /storage/emulated/0/test.txt with content hello world"
  {"action": "create_file", "payload": {"path": "/storage/emulated/0/test.txt", "content": "hello world"}}

Command: """ + query
    try:
        response = ask_llm([{"role": "user", "content": prompt}], temperature=0.1)
        if response:
            response_clean = response.strip()
            # Extract JSON block using regex to avoid issues with extra text
            match = re.search(r"\{.*\}", response_clean, re.DOTALL)
            if match:
                response_clean = match.group(0)
            return json.loads(response_clean)
    except Exception as e:
        logger.warning(f"Failed to parse command via LLM: {e}")
    return {"action": "none", "payload": {}}


def handle_device_command(query: str, params: dict | None = None) -> dict:
    """Handle Android device commands with actual intent execution.

    Args:
        query: The raw user query (for fallback parsing).
        params: Structured params from LLMIntentRouter (app_name, action, etc.).
    """
    if params is None:
        params = {}
    q = query.lower()
    executor = IntentExecutor()

    # ── Fast path: use LLM-extracted params ─────────────────────
    app_name = params.get("app_name")
    call_name = params.get("name")
    call_number = params.get("number")
    action = params.get("action")
    target = params.get("target")
    state = params.get("state")

    if app_name:
        intent = executor.open_app(app_name)
        if "error" not in intent:
            return {
                "reply": f"Opening {app_name}...",
                "action": "LAUNCH_APP",
                "intent": intent,
                "payload": intent
            }
        # Fall through to Termux execution below

    if call_number:
        intent = executor.make_call(call_number)
        return {
            "reply": f"Calling {call_number}...",
            "action": "CALL", "intent": intent, "payload": intent
        }

    if call_name:
        return {
            "reply": f"Searching contacts for {call_name}...",
            "action": "call_contact", "payload": {"name": call_name}
        }

    if action == "toggle" and target:
        is_on = state if state is not None else True
        if target in ("flashlight", "torch", "flash"):
            if IS_TERMUX:
                try:
                    subprocess.run(["termux-torch", "on" if is_on else "off"], capture_output=True, timeout=5)
                    return {"reply": f"Flashlight turned {'on' if is_on else 'off'}.", "action": "none"}
                except Exception as e:
                    return {"reply": f"Failed to toggle flashlight: {e}", "action": "none"}
            return {"reply": f"Turning {'on' if is_on else 'off'} the flashlight.", "action": "torch", "payload": "on" if is_on else "off"}
        if target in ("wifi", "wi-fi", "wlan"):
            if IS_TERMUX:
                try:
                    subprocess.run(["termux-wifi-enable", "true" if is_on else "false"], capture_output=True, timeout=5)
                    return {"reply": f"Wi-Fi turned {'on' if is_on else 'off'}.", "action": "none"}
                except Exception as e:
                    return {"reply": f"Failed to toggle Wi-Fi: {e}", "action": "none"}
            return {"reply": "Opening Wi-Fi settings.", "action": "wifi", "payload": "open_settings"}

    if action == "volume" and target in ("up", "down", "increase", "decrease"):
        is_up = target in ("up", "increase")
        if IS_TERMUX:
            try:
                if is_up:
                    subprocess.run(["termux-volume", "music", "max"], capture_output=True, timeout=5)
                else:
                    subprocess.run(["termux-volume", "music", "5"], capture_output=True, timeout=5)
                return {"reply": f"Volume {'increased' if is_up else 'decreased'}.", "action": "none"}
            except Exception as e:
                return {"reply": f"Failed to adjust volume: {e}", "action": "none"}
        return {"reply": f"Volume {'up' if is_up else 'down'}.",
                "action": "volume", "payload": "up" if is_up else "down"}

    if action == "status" and target == "battery":
        if IS_TERMUX:
            try:
                res = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=5)
                data = json.loads(res.stdout)
                perc = data.get("percentage", "unknown")
                status = data.get("status", "unknown")
                return {"reply": f"Battery is at {perc}%, and is currently {status}.", "action": "none"}
            except Exception as e:
                return {"reply": f"Failed to read battery: {e}", "action": "none"}
        return {"reply": "Sorry, battery status is only available locally.", "action": "none"}

    if action == "open" and target == "camera":
        return {"reply": "Opening camera.", "action": "camera", "payload": ""}

    # ── Fallback: legacy keyword + LLM parsing ─────────────────
    # YouTube playback
    if "youtube" in q or ("play" in q and ("song" in q or "music" in q or "youtube" in q)):
        from app.skills.youtube import handle_music_request
        result = handle_music_request(query)
        if result and result.get("youtube_url"):
            video_id = result["youtube_url"].split("v=")[-1] if "v=" in result["youtube_url"] else None
            intent = executor.play_youtube(query, video_id)
            return {
                "reply": result["reply"],
                "action": "PLAY_VIDEO",
                "intent": intent,
                "payload": intent
            }
        return {
            "reply": "YouTube search nahi hua. Try again!",
            "action": "none",
            "payload": {}
        }

    # Try LLM parser for alarm, call, contacts, files, storage operations
    parsed = parse_device_command_via_llm(query)
    action = parsed.get("action", "none")
    payload = parsed.get("payload", {})

    if action == "set_alarm":
        hour = payload.get("hour", 7)
        minute = payload.get("minute", 0)
        label = payload.get("label", "Jarvis Alarm")
        intent = executor.set_alarm(hour, minute, label)
        return {
            "reply": f"Setting alarm for {hour:02d}:{minute:02d} ({label}).",
            "action": "SET_ALARM",
            "intent": intent,
            "payload": intent
        }

    elif action == "create_event":
        title = payload.get("title", "Reminder")
        time_str = payload.get("time", "")
        intent = executor.create_reminder(title, time_str)
        return {
            "reply": f"Creating reminder: {title}",
            "action": "CREATE_EVENT",
            "intent": intent,
            "payload": intent
        }

    elif action == "make_call":
        number = payload.get("number", "")
        if number:
            intent = executor.make_call(number)
            return {
                "reply": f"Calling {number}...",
                "action": "CALL",
                "intent": intent,
                "payload": intent
            }

    elif action == "call_contact":
        name = payload.get("name", "")
        return {
            "reply": f"Searching contacts for {name} to make a call...",
            "action": "call_contact",
            "payload": payload
        }

    elif action == "create_file":
        path = payload.get("path", "")
        content = payload.get("content", "")
        return {
            "reply": f"Creating file at {path}...",
            "action": "create_file",
            "payload": payload
        }

    elif action == "read_file":
        path = payload.get("path", "")
        return {
            "reply": f"Reading file {path}...",
            "action": "read_file",
            "payload": payload
        }

    elif action == "list_directory":
        path = payload.get("path", "")
        return {
            "reply": f"Listing directory {path}...",
            "action": "list_directory",
            "payload": payload
        }

    elif action == "delete_file":
        path = payload.get("path", "")
        return {
            "reply": f"Deleting file {path}...",
            "action": "delete_file",
            "payload": payload
        }

    # Flashlight / Torch
    if "torch" in q or "flashlight" in q or "flash" in q:
        is_on = bool(re.search(r"\b(on|enable|start|turn on|switch on)\b", q))
        if IS_TERMUX:
            try:
                subprocess.run(["termux-torch", "on" if is_on else "off"], capture_output=True, timeout=5)
                return {"reply": f"Flashlight turned {'on' if is_on else 'off'}.", "action": "none"}
            except Exception as e:
                return {"reply": f"Failed to toggle flashlight: {e}", "action": "none"}
        return {"reply": f"Turning {'on' if is_on else 'off'} the flashlight.", "action": "torch", "payload": "on" if is_on else "off"}

    # WiFi
    if "wifi" in q or "wi-fi" in q:
        is_on = bool(re.search(r"\b(on|enable|start|turn on|switch on)\b", q))
        if IS_TERMUX:
            try:
                subprocess.run(["termux-wifi-enable", "true" if is_on else "false"], capture_output=True, timeout=5)
                return {"reply": f"Wi-Fi turned {'on' if is_on else 'off'}.", "action": "none"}
            except Exception as e:
                return {"reply": f"Failed to toggle Wi-Fi: {e}", "action": "none"}
        return {"reply": "Opening Wi-Fi settings.", "action": "wifi", "payload": "open_settings"}

    # Battery
    if "battery" in q:
        if IS_TERMUX:
            try:
                res = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=5)
                data = json.loads(res.stdout)
                perc = data.get("percentage", "unknown")
                status = data.get("status", "unknown")
                return {"reply": f"Battery is at {perc}%, and is currently {status}.", "action": "none"}
            except Exception as e:
                return {"reply": f"Failed to read battery status: {e}", "action": "none"}
        return {"reply": "Sorry, battery status is only available locally.", "action": "none"}

    # Volume
    if "volume" in q:
        is_up = bool(re.search(r"\b(up|increase|raise|louder)\b", q))
        if IS_TERMUX:
            try:
                if is_up:
                    subprocess.run(["termux-volume", "music", "max"], capture_output=True, timeout=5)
                    return {"reply": "Volume increased.", "action": "none"}
                else:
                    subprocess.run(["termux-volume", "music", "5"], capture_output=True, timeout=5)
                    return {"reply": "Volume decreased.", "action": "none"}
            except Exception as e:
                return {"reply": f"Failed to adjust volume: {e}", "action": "none"}
        return {"reply": "Adjusting volume.", "action": "volume", "payload": "up" if is_up else "down"}

    # Brightness
    if "brightness" in q:
        return {"reply": "Brightness control is not supported from JARVIS right now.", "action": "none"}

    # Bluetooth
    if "bluetooth" in q:
        return {"reply": "Bluetooth control is not supported from JARVIS right now.", "action": "none"}

    # Camera
    if re.search(r"\b(open camera|take photo|take picture|take selfie|camera|photo)\b", q):
        return {"reply": "Opening camera.", "action": "camera", "payload": ""}

    # Open App (fallback — uses IntentExecutor with full app map)
    if "open" in q or "launch" in q:
        match = re.search(r"\b(?:open|launch)\s+(.+)$", q)
        app_name = match.group(1).strip() if match else ""
        if not app_name:
            return {"reply": "Tell me which app to open.", "action": "none"}
        intent = executor.open_app(app_name)
        if "error" not in intent:
            pkg = intent.get("package", "")
            if IS_TERMUX:
                try:
                    subprocess.run(["monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"], capture_output=True, timeout=5)
                    return {"reply": f"Opening {app_name}...", "action": "none"}
                except Exception as e:
                    return {"reply": f"Failed to open {app_name}: {e}", "action": "none"}
            return {"reply": f"Opening {app_name}.", "action": "open_app", "payload": pkg}
        else:
            return {"reply": f"I couldn't find an exact match for '{app_name}'. Try the full app name.", "action": "none"}

    return {"reply": "Device command not recognized or supported.", "action": "none"}
