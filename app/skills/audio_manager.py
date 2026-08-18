"""
app/skills/audio_manager.py — Bluetooth audio detection and switching.

Auto-detects Bluetooth microphones and speakers on Windows,
and can switch the system default audio devices to them.
"""

import logging
import subprocess
from typing import Any

from app.core.config import IS_WINDOWS

logger = logging.getLogger(__name__)


def get_bluetooth_audio_devices() -> list[dict[str, str]]:
    """Detect connected Bluetooth audio devices (mic + speaker).

    Uses PowerShell to query audio endpoints via Plug and Play.
    Returns a list of dicts with keys: name, type ('mic'/'speaker'), device_id.

    Returns empty list on non-Windows or if no Bluetooth audio is found.
    """
    if not IS_WINDOWS:
        return []

    ps_script = """
    Get-PnpDevice -Class AudioEndpoint | Where-Object {
        $_.FriendlyName -match 'Bluetooth|Hands-Free|Headset|Headphones|Earphones|AirPods'
    } | Select-Object FriendlyName, Class, InstanceId, Status
    | ConvertTo-Json
    """
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []

        import json
        devices = json.loads(result.stdout)
        if isinstance(devices, dict):
            devices = [devices]

        audio_devices = []
        for dev in devices:
            name = dev.get("FriendlyName", "")
            instance_id = dev.get("InstanceId", "")
            status = dev.get("Status", "")
            if status.lower() != "ok":
                continue
            # Determine if it's output (speaker) or input (mic)
            # Quirk: we match on name patterns
            lower_name = name.lower()
            if any(kw in lower_name for kw in ["microphone", "mic", "hands-free"]):
                dev_type = "mic"
            elif any(kw in lower_name for kw in ["headphone", "speaker", "stereo", "headset"]):
                dev_type = "speaker"
            else:
                # Default: if name suggests two-way audio, report both clues
                dev_type = "unknown"

            audio_devices.append({
                "name": name,
                "type": dev_type,
                "device_id": instance_id,
            })
        return audio_devices
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        logger.warning(f"Failed to detect Bluetooth audio: {e}")
        return []


def has_bluetooth_audio() -> bool:
    """Quick check if Bluetooth audio is connected and available."""
    return len(get_bluetooth_audio_devices()) > 0


def set_default_bluetooth_audio() -> dict[str, Any]:
    """Auto-detect and set Bluetooth audio as the default device.

    Sets Bluetooth speaker as default playback device and
    Bluetooth mic as default recording device if found.

    Returns:
        dict with keys: success (bool), message (str),
                        mic (str|None), speaker (str|None)
    """
    if not IS_WINDOWS:
        return {
            "success": False,
            "message": "Bluetooth audio management is only available on Windows.",
            "mic": None,
            "speaker": None,
        }

    devices = get_bluetooth_audio_devices()
    if not devices:
        return {
            "success": False,
            "message": "No connected Bluetooth audio devices found.",
            "mic": None,
            "speaker": None,
        }

    mic_name = None
    speaker_name = None
    for dev in devices:
        if dev["type"] == "mic":
            mic_name = dev["name"]
        elif dev["type"] == "speaker":
            speaker_name = dev["name"]
        elif dev["type"] == "unknown" and speaker_name is None:
            speaker_name = dev["name"]

    # Use PowerShell to set default audio devices
    # We use a .NET-based COM approach via PowerShell
    changes = []
    if speaker_name:
        ps_set_speaker = f"""
        $obj = New-Object -ComObject MMDevices.MMDeviceEnumerator
        $devices = $obj.EnumerateAudioEndpoints('Render', 1)
        foreach ($dev in $devices) {{
            if ($dev.FriendlyName -like '*{speaker_name}*') {{
                $dev.SetAsDefault(0)
                break
            }}
        }}
        """
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_set_speaker],
                capture_output=True, timeout=10, check=False,
            )
            changes.append(f"speaker → {speaker_name}")
        except Exception as e:
            logger.warning(f"Failed to set Bluetooth speaker: {e}")

    if mic_name:
        ps_set_mic = f"""
        $obj = New-Object -ComObject MMDevices.MMDeviceEnumerator
        $devices = $obj.EnumerateAudioEndpoints('Capture', 1)
        foreach ($dev in $devices) {{
            if ($dev.FriendlyName -like '*{mic_name}*') {{
                $dev.SetAsDefault(1)
                break
            }}
        }}
        """
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_set_mic],
                capture_output=True, timeout=10, check=False,
            )
            changes.append(f"mic → {mic_name}")
        except Exception as e:
            logger.warning(f"Failed to set Bluetooth mic: {e}")

    if changes:
        return {
            "success": True,
            "message": "Bluetooth audio set as default: " + ", ".join(changes),
            "mic": mic_name,
            "speaker": speaker_name,
        }
    else:
        return {
            "success": False,
            "message": "Found Bluetooth devices but could not set them as default.",
            "mic": mic_name,
            "speaker": speaker_name,
        }


def set_default_system_audio() -> dict[str, Any]:
    """Reset audio back to system default (non-Bluetooth)."""
    if not IS_WINDOWS:
        return {"success": False, "message": "Only available on Windows."}

    try:
        ps_script = """
        $obj = New-Object -ComObject MMDevices.MMDeviceEnumerator
        # Reset render (playback) to first non-BT device
        $devices = $obj.EnumerateAudioEndpoints('Render', 1)
        foreach ($dev in $devices) {
            if ($dev.FriendlyName -notmatch 'Bluetooth|Hands-Free|Headset|AirPods') {
                $dev.SetAsDefault(0)
                break
            }
        }
        # Reset capture (recording) to first non-BT device
        $devices = $obj.EnumerateAudioEndpoints('Capture', 1)
        foreach ($dev in $devices) {
            if ($dev.FriendlyName -notmatch 'Bluetooth|Hands-Free|Headset|AirPods') {
                $dev.SetAsDefault(1)
                break
            }
        }
        """
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, timeout=10, check=False,
        )
        return {"success": True, "message": "Audio reset to system default devices."}
    except Exception as e:
        return {"success": False, "message": f"Failed to reset audio: {e}"}


# ── Convenience wrapper for tasks.py ──────────────────────────

def handle_audio_command(query: str) -> dict:
    """Handle Bluetooth and audio-related commands.

    Parses keywords from query and dispatches to the right function.

    Returns dict with reply, action, payload.
    """
    q = query.lower()

    # Bluetooth audio detection / switch
    if any(kw in q for kw in ["bluetooth audio", "bluetooth mic", "bluetooth speaker",
                               "auto detect bluetooth", "switch to bluetooth",
                               "connect bluetooth audio", "use bluetooth"]):
        result = set_default_bluetooth_audio()
        return {
            "reply": result["message"],
            "action": "bluetooth_audio",
            "payload": result,
        }

    # Check Bluetooth audio status
    if any(kw in q for kw in ["bluetooth status", "audio status", "check bluetooth",
                               "bluetooth devices", "bt status"]):
        devices = get_bluetooth_audio_devices()
        if devices:
            names = ", ".join(d["name"] for d in devices)
            return {
                "reply": f"Found Bluetooth audio devices: {names}",
                "action": "bluetooth_status",
                "payload": {"devices": devices},
            }
        return {
            "reply": "No Bluetooth audio devices detected.",
            "action": "bluetooth_status",
            "payload": {"devices": []},
        }

    # Reset to system default audio
    if any(kw in q for kw in ["reset audio", "system audio", "default audio",
                               "switch to speaker", "use laptop speaker"]):
        result = set_default_system_audio()
        return {
            "reply": result["message"],
            "action": "audio_reset",
            "payload": result,
        }

    return {
        "reply": "Audio command not recognized. Try 'switch to Bluetooth audio' or 'check Bluetooth status'.",
        "action": "none",
        "payload": {},
    }
