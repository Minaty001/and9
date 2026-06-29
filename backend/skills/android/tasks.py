"""
app/skills/tasks.py — Executable task functions.

All system-interaction functions in one place. Safe for Render (no hardware deps).
Platform-conditional code (Termux/Windows) is isolated to specific functions.

Constitution V3:
   Rule 5/6 — LLM never used for command parsing.
   Rule 8 — Source tracking for all decisions.
"""
import os
import sys
import subprocess
import json
import logging
import re
from datetime import datetime

from backend.core.config import NEWS_API_KEY, NOTES_DIR, IS_TERMUX, IS_WINDOWS
from backend.skills.android.intent_executor import IntentExecutor

logger = logging.getLogger(__name__)


# ── Web Search (DuckDuckGo, no API key) ──────────────────────────

def search_web(query: str) -> str:
    """Quick web search via DuckDuckGo."""
    try:
        from backend.integrations.duckduckgo import web_search
        results = web_search(query, max_results=3)
        if results:
            snippets = [r.get("body", "") or r.get("title", "") for r in results if r.get("body") or r.get("title")]
            if snippets:
                return " | ".join(snippets)
        return f"No results for '{query}'."
    except Exception as e:
        logger.warning(f"Search failed: {e}")
        return f"Search error: {e}"


def get_realtime_data(query: str) -> str:
    """Fetch real-time data via DuckDuckGo without opening a browser."""
    try:
        from backend.integrations.duckduckgo import web_search
        results = web_search(query, max_results=3)
        if results:
            snippets = [r.get("body", "") for r in results if r.get("body")]
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
        from backend.skills.media.img import generate_image
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

    # YouTube — only route to music handler when there's playback/search intent
    # "open youtube" should open the app, NOT search music
    _youtube_play_intent = (
        re.search(r"\b(play|search|find|watch|dekhna|sunna|chalao|laga|bajao)\b", q)
        and "youtube" in q
    )
    if _youtube_play_intent:
        from backend.skills.media.youtube import handle_music_request
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
            "google chrome": "com.android.chrome",
            "calculator": "com.google.android.calculator",
            "maps": "com.google.android.apps.maps",
            "google maps": "com.google.android.apps.maps",
            "telegram": "org.telegram.messenger",
            "spotify": "com.spotify.music",
            "instagram": "com.instagram.android",
            "camera": "com.android.camera",
            "gmail": "com.google.android.gm",
            "phone": "com.google.android.dialer",
            "dialer": "com.google.android.dialer",
            "contacts": "com.google.android.contacts",
            "settings": "com.android.settings",
            "gallery": "com.google.android.apps.photos",
            "photos": "com.google.android.apps.photos",
            "play store": "com.android.vending",
            "playstore": "com.android.vending",
            "clock": "com.google.android.deskclock",
            "files": "com.google.android.documentsui",
            "drive": "com.google.android.apps.docs",
            "meet": "com.google.android.apps.meetings",
            "twitter": "com.twitter.android",
            "x": "com.twitter.android",
            "facebook": "com.facebook.katana",
            "snapchat": "com.snapchat.android",
            "netflix": "com.netflix.mediaclient",
            "amazon": "com.amazon.mShop.android.shopping",
            "flipkart": "com.flipkart.android",
            "paytm": "net.one97.paytm",
            "phonepe": "com.phonepe.app",
            "gpay": "com.google.android.apps.walletnfcrel",
            "google pay": "com.google.android.apps.walletnfcrel",
            "zoom": "us.zoom.videomeetings",
            "music": "com.google.android.music",
            "youtube music": "com.google.android.apps.youtube.music",
        }
        target = None
        # Sort by key length descending so multi-word keys ("youtube music") match before shorter ones
        for key, pkg in sorted(app_map.items(), key=lambda x: len(x[0]), reverse=True):
            if key in app_name:
                target = pkg
                break

        if target:
            if IS_TERMUX:
                try:
                    subprocess.run(["monkey", "-p", target, "-c", "android.intent.category.LAUNCHER", "1"], capture_output=True, timeout=5)
                    return {"reply": f"Opening {app_name}...", "action": "none"}
                except Exception as e:
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
