"""
app/skills/tasks.py — Executable task functions.

All system-interaction functions in one place. Safe for Render (no hardware deps).
Platform-conditional code (Termux/Windows) is isolated to specific functions.

Constitution V3:
   Rule 5/6 — LLM never used for command parsing.
   Rule 8 — Source tracking for all decisions.
"""
import subprocess
import json
import logging
import re
from datetime import datetime, timezone

from app.core.config import SERP_API_KEY, NEWS_API_KEY, IS_TERMUX, IS_WINDOWS
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
    except Exception as e:  # noqa: BLE001
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
    except Exception as e:  # noqa: BLE001
        return f"Search error: {e}"


# ── Time & Info ───────────────────────────────────────────────

def get_time() -> str:
    return datetime.now(timezone.utc).strftime("%I:%M %p, %A %B %d, %Y")


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
    except Exception as e:  # noqa: BLE001
        return f"News error: {e}"


# ── Device / System Control ───────────────────────────────────

# ── REMOVED (Constitution V3 Rule 5/6) ─────────────────────────
# parse_device_command_via_llm() — removed.
# LLM inference must NEVER be used for decisions per Rule 5:
#   llm_inference → confidence 0.0 → never used for actions.
# Device commands are now parsed via keyword matching only.
# ────────────────────────────────────────────────────────────────


def handle_device_command(query: str) -> dict:
    """Handle Android device commands with actual intent execution.

    Constitution V3: NO LLM-based command parsing. All parsing is
    via keyword matching (source: regex/kw_extraction).
    """
    q = query.lower()
    executor = IntentExecutor()

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

    # Flashlight / Torch
    if "torch" in q or "flashlight" in q or "flash" in q:
        is_on = bool(re.search(r"\b(on|enable|start|turn on|switch on)\b", q))
        if IS_TERMUX:
            try:
                subprocess.run(["termux-torch", "on" if is_on else "off"], check=False, capture_output=True, timeout=5)
                return {"reply": f"Flashlight turned {'on' if is_on else 'off'}.", "action": "none"}
            except Exception as e:  # noqa: BLE001
                return {"reply": f"Failed to toggle flashlight: {e}", "action": "none"}
        return {"reply": f"Turning {'on' if is_on else 'off'} the flashlight.", "action": "torch", "payload": "on" if is_on else "off"}

    # WiFi
    if "wifi" in q or "wi-fi" in q:
        is_on = bool(re.search(r"\b(on|enable|start|turn on|switch on)\b", q))
        if IS_TERMUX:
            try:
                subprocess.run(["termux-wifi-enable", "true" if is_on else "false"], check=False, capture_output=True, timeout=5)
                return {"reply": f"Wi-Fi turned {'on' if is_on else 'off'}.", "action": "none"}
            except Exception as e:  # noqa: BLE001
                return {"reply": f"Failed to toggle Wi-Fi: {e}", "action": "none"}
        return {"reply": "Opening Wi-Fi settings.", "action": "wifi", "payload": "open_settings"}

    # Battery
    if "battery" in q:
        if IS_TERMUX:
            try:
                res = subprocess.run(["termux-battery-status"], check=False, capture_output=True, text=True, timeout=5)
                data = json.loads(res.stdout)
                perc = data.get("percentage", "unknown")
                status = data.get("status", "unknown")
                return {"reply": f"Battery is at {perc}%, and is currently {status}.", "action": "none"}
            except Exception as e:  # noqa: BLE001
                return {"reply": f"Failed to read battery status: {e}", "action": "none"}
        return {"reply": "Sorry, battery status is only available locally.", "action": "none"}

    # Volume
    if "volume" in q:
        if IS_TERMUX:
            is_up = bool(re.search(r"\b(up|increase|raise|louder)\b", q))
            try:
                if is_up:
                    subprocess.run(["termux-volume", "music", "max"], check=False, capture_output=True, timeout=5)
                    return {"reply": "Volume increased.", "action": "none"}
                else:
                    subprocess.run(["termux-volume", "music", "5"], check=False, capture_output=True, timeout=5)
                    return {"reply": "Volume decreased.", "action": "none"}
            except Exception as e:  # noqa: BLE001
                return {"reply": f"Failed to adjust volume: {e}", "action": "none"}
        if IS_WINDOWS:
            from app.skills.pc_control import pc_volume
            reply = pc_volume("up" if re.search(r"\b(up|increase|raise|louder)\b", q) else "down")
            return {"reply": reply, "action": "volume", "payload": reply}
        return {"reply": "Adjusting volume.", "action": "volume", "payload": "up" if bool(re.search(r"\b(up|increase|raise|louder)\b", q)) else "down"}

    # Brightness
    if "brightness" in q:
        if IS_WINDOWS:
            from app.skills.pc_control import pc_brightness
            if "up" in q or "increase" in q:
                return {"reply": pc_brightness("up"), "action": "brightness", "payload": "up"}
            if "down" in q or "decrease" in q:
                return {"reply": pc_brightness("down"), "action": "brightness", "payload": "down"}
            num_match = re.search(r'(\d{1,3})', q)
            if num_match:
                val = int(num_match.group(1))
                if 0 <= val <= 100:
                    return {"reply": pc_brightness(val), "action": "brightness", "payload": val}
            return {"reply": pc_brightness("up"), "action": "brightness", "payload": "up"}
        if IS_TERMUX:
            return {"reply": "Brightness control not supported via Termux.", "action": "none"}
        return {"reply": "Brightness control is not available.", "action": "none"}

    # Bluetooth
    if "bluetooth" in q and "audio" not in q and "speaker" not in q and "mic" not in q:
        if IS_WINDOWS:
            from app.skills.audio_manager import handle_audio_command
            return handle_audio_command(query)
        return {"reply": "Bluetooth control is not supported from JARVIS right now.", "action": "none"}

    # Camera
    if re.search(r"\b(open camera|take photo|take picture|take selfie|camera|photo)\b", q):
        return {"reply": "Opening camera.", "action": "camera", "payload": ""}

    # Open App — keyword-based, no LLM
    if "open" in q or "launch" in q:
        match = re.search(r"\b(?:open|launch)\s+(.+)$", q)
        app_name = match.group(1).strip() if match else ""
        if not app_name:
            return {"reply": "Tell me which app to open.", "action": "none"}
        app_map = {
            "youtube": "com.google.android.youtube",
            "whatsapp": "com.whatsapp",
            "chrome": "com.android.chrome",
            "calculator": "com.google.android.calculator",
            "maps": "com.google.android.apps.maps",
            "telegram": "org.telegram.messenger",
            "spotify": "com.spotify.music",
            "instagram": "com.instagram.android",
            "camera": "com.android.camera"
        }
        target = None
        for key, pkg in app_map.items():
            if key in app_name:
                target = pkg
                break

        if target:
            if IS_TERMUX:
                try:
                    subprocess.run(["monkey", "-p", target, "-c", "android.intent.category.LAUNCHER", "1"], check=False, capture_output=True, timeout=5)
                    return {"reply": f"Opening {app_name}...", "action": "none"}
                except Exception as e:  # noqa: BLE001
                    return {"reply": f"Failed to open {app_name}: {e}", "action": "none"}
            return {"reply": f"Opening {app_name}.", "action": "open_app", "payload": target}
        else:
            return {"reply": f"I couldn't find an exact match for '{app_name}'. Try the full app name.", "action": "none"}

    # Alarm — keyword-based
    alarm_match = re.search(
        r'(?:set|alarm|alarm set|alarm lagao|alarm laga do)\s+(?:for\s+)?(\d{1,2})(?::(\d{2}))?\s*(?:am|pm|AM|PM)?\s*(?:(?:called|named|for|label)?\s*(.+?))?$',
        q
    )
    if alarm_match:
        hour = int(alarm_match.group(1))
        minute = int(alarm_match.group(2) or "0")
        label = (alarm_match.group(3) or "Jarvis Alarm").strip()
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            intent = executor.set_alarm(hour, minute, label)
            return {
                "reply": f"Setting alarm for {hour:02d}:{minute:02d} ({label}).",
                "action": "SET_ALARM",
                "intent": intent,
                "payload": intent
            }

    # Call — keyword-based
    call_match = re.search(r'(?:call|dial)\s+([+]?\d[\d\s\-()]+)', q)
    if call_match:
        number = call_match.group(1).strip()
        intent = executor.make_call(number)
        return {
            "reply": f"Calling {number}...",
            "action": "CALL",
            "intent": intent,
            "payload": intent
        }

    return {"reply": "Device command not recognized or supported.", "action": "none"}
