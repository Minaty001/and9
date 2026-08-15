"""
app/skills/pc_control.py — Windows PC control functions.

Provides functions for volume, brightness, app launching, media control,
screenshots, system commands, and more on Windows.
All functions gracefully handle non-Windows platforms via IS_WINDOWS check.
"""

import logging
import subprocess
import os
import re

from app.core.config import IS_WINDOWS

logger = logging.getLogger(__name__)

# ── Lazy imports (graceful if optional deps not installed) ─────────

_pyautogui = None
_sbc = None
_pygetwindow = None
_keyboard = None


def _lazy_import_pyautogui():
    global _pyautogui
    if _pyautogui is None:
        try:
            import pyautogui as m
            _pyautogui = m
        except ImportError:
            _pyautogui = False
    return _pyautogui if _pyautogui is not False else None


def _lazy_import_sbc():
    global _sbc
    if _sbc is None:
        try:
            import screen_brightness_control as m
            _sbc = m
        except ImportError:
            _sbc = False
    return _sbc if _sbc is not False else None


def _lazy_import_pygetwindow():
    global _pygetwindow
    if _pygetwindow is None:
        try:
            import pygetwindow as m
            _pygetwindow = m
        except ImportError:
            _pygetwindow = False
    return _pygetwindow if _pygetwindow is not False else None


def _lazy_import_keyboard():
    global _keyboard
    if _keyboard is None:
        try:
            import keyboard as m
            _keyboard = m
        except ImportError:
            _keyboard = False
    return _keyboard if _keyboard is not False else None


# ── Helpers ────────────────────────────────────────────────────────

def _ensure_windows() -> str | None:
    """Return error string if not on Windows, else None."""
    if not IS_WINDOWS:
        return "This PC control feature is only available on Windows."
    return None


def _run_powershell(script: str, timeout: int = 10) -> str:
    """Run a PowerShell script and return stdout."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return ""
    except Exception as e:
        logger.warning(f"PowerShell error: {e}")
        return ""


# ── Volume Control ─────────────────────────────────────────────────

def pc_volume(level_or_updown: str | int) -> str:
    """Set volume level: 0-100, or 'up'/'down'.

    Uses pycaw if available, otherwise PowerShell fallback.
    """
    err = _ensure_windows()
    if err:
        return err

    # Try pycaw first
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        import ctypes

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
    except ImportError:
        volume = None
    except Exception:
        volume = None

    if volume is not None:
        # pycaw path
        try:
            current = volume.GetMasterVolumeLevelScalar()
            if isinstance(level_or_updown, str):
                lvl = level_or_updown.lower()
                if lvl == "up" or lvl == "increase":
                    new_scalar = min(1.0, current + 0.1)
                elif lvl == "down" or lvl == "decrease":
                    new_scalar = max(0.0, current - 0.1)
                elif lvl == "max" or lvl == "full":
                    new_scalar = 1.0
                elif lvl == "mute":
                    volume.SetMute(1, None)
                    return "System muted."
                elif lvl == "unmute":
                    volume.SetMute(0, None)
                    return "System unmuted."
                else:
                    try:
                        pct = int(lvl)
                        new_scalar = max(0.0, min(1.0, pct / 100.0))
                    except ValueError:
                        return "Say 'volume up', 'volume down', or 'volume N' (0-100)."
            elif isinstance(level_or_updown, (int, float)):
                new_scalar = max(0.0, min(1.0, level_or_updown / 100.0))
            else:
                return "Invalid volume level."

            volume.SetMasterVolumeLevelScalar(new_scalar, None)
            pct = int(new_scalar * 100)
            return f"Volume set to {pct}%."
        except Exception as e:
            logger.warning(f"pycav volume failed: {e}")
            # Fall through to PowerShell

    # PowerShell fallback
    if isinstance(level_or_updown, str):
        lvl = level_or_updown.lower()
        if lvl == "up":
            ps = """
            $obj = New-Object -ComObject MMDevices.MMDeviceEnumerator
            $dev = $obj.EnumerateAudioEndpoints('Render', 1) | Select-Object -First 1
            $vol = $dev.Activate(1, 5, $null)  # 1 = IAudioEndpointVolume
            $current = $vol.GetMasterVolumeLevelScalar()
            $vol.SetMasterVolumeLevelScalar([Math]::Min(1.0, $current + 0.1), $null)
            """
        elif lvl == "down":
            ps = """
            $obj = New-Object -ComObject MMDevices.MMDeviceEnumerator
            $dev = $obj.EnumerateAudioEndpoints('Render', 1) | Select-Object -First 1
            $vol = $dev.Activate(1, 5, $null)
            $current = $vol.GetMasterVolumeLevelScalar()
            $vol.SetMasterVolumeLevelScalar([Math]::Max(0.0, $current - 0.1), $null)
            """
        elif lvl == "max":
            ps = """
            $obj = New-Object -ComObject MMDevices.MMDeviceEnumerator
            $dev = $obj.EnumerateAudioEndpoints('Render', 1) | Select-Object -First 1
            $vol = $dev.Activate(1, 5, $null)
            $vol.SetMasterVolumeLevelScalar(1.0, $null)
            """
        elif lvl == "mute":
            ps = """
            $obj = New-Object -ComObject MMDevices.MMDeviceEnumerator
            $dev = $obj.EnumerateAudioEndpoints('Render', 1) | Select-Object -First 1
            $vol = $dev.Activate(1, 5, $null)
            $vol.SetMute(1, $null)
            """
        elif lvl == "unmute":
            ps = """
            $obj = New-Object -ComObject MMDevices.MMDeviceEnumerator
            $dev = $obj.EnumerateAudioEndpoints('Render', 1) | Select-Object -First 1
            $vol = $dev.Activate(1, 5, $null)
            $vol.SetMute(0, $null)
            """
        else:
            try:
                pct = max(0, min(100, int(lvl)))
                ps = f"""
                $obj = New-Object -ComObject MMDevices.MMDeviceEnumerator
                $dev = $obj.EnumerateAudioEndpoints('Render', 1) | Select-Object -First 1
                $vol = $dev.Activate(1, 5, $null)
                $vol.SetMasterVolumeLevelScalar({pct / 100.0}, $null)
                """
            except ValueError:
                return "Say 'volume up', 'volume down', or 'volume N' (0-100)."
    elif isinstance(level_or_updown, (int, float)):
        pct = max(0, min(100, int(level_or_updown)))
        ps = f"""
        $obj = New-Object -ComObject MMDevices.MMDeviceEnumerator
        $dev = $obj.EnumerateAudioEndpoints('Render', 1) | Select-Object -First 1
        $vol = $dev.Activate(1, 5, $null)
        $vol.SetMasterVolumeLevelScalar({pct / 100.0}, $null)
        """
    else:
        return "Invalid volume level."

    _run_powershell(ps)
    return "Adjusting system volume."


def pc_mute() -> str:
    """Toggle mute on/off. Returns current mute state."""
    return pc_volume("mute")


def pc_unmute() -> str:
    """Unmute system audio."""
    return pc_volume("unmute")


# ── Brightness Control ─────────────────────────────────────────────

def pc_brightness(level_or_updown: str | int) -> str:
    """Set screen brightness: 0-100, or 'up'/'down'.

    Uses screen-brightness-control if available, falls back to PowerShell.
    """
    err = _ensure_windows()
    if err:
        return err

    sbc = _lazy_import_sbc()
    if sbc:
        try:
            if isinstance(level_or_updown, str):
                lvl = level_or_updown.lower()
                if lvl == "up":
                    current = sbc.get_brightness()[0]
                    new_val = min(100, current + 10)
                elif lvl == "down":
                    current = sbc.get_brightness()[0]
                    new_val = max(0, current - 10)
                elif lvl in ("max", "full"):
                    new_val = 100
                elif lvl == "min":
                    new_val = 0
                else:
                    try:
                        new_val = max(0, min(100, int(lvl)))
                    except ValueError:
                        return "Say 'brightness up', 'brightness down', or 'brightness N' (0-100)."
            elif isinstance(level_or_updown, (int, float)):
                new_val = max(0, min(100, int(level_or_updown)))
            else:
                return "Invalid brightness level."

            sbc.set_brightness(new_val)
            return f"Brightness set to {new_val}%."
        except Exception as e:
            logger.warning(f"sbc brightness failed: {e}")
            # Fall through to PowerShell

    # PowerShell fallback using WMI
    if isinstance(level_or_updown, str):
        lvl = level_or_updown.lower()
        if lvl == "up":
            ps = """
            $monitors = Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods
            $current = (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness
            $new = [Math]::Min(100, $current + 10)
            $monitors.WmiSetBrightness(1, $new) | Out-Null
            """
        elif lvl == "down":
            ps = """
            $monitors = Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods
            $current = (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness
            $new = [Math]::Max(0, $current - 10)
            $monitors.WmiSetBrightness(1, $new) | Out-Null
            """
        else:
            try:
                new_val = max(0, min(100, int(lvl)))
                ps = f"""
                $monitors = Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods
                $monitors.WmiSetBrightness(1, {new_val}) | Out-Null
                """
            except ValueError:
                return "Say 'brightness up', 'brightness down', or 'brightness N' (0-100)."
    elif isinstance(level_or_updown, (int, float)):
        new_val = max(0, min(100, int(level_or_updown)))
        ps = f"""
        $monitors = Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods
        $monitors.WmiSetBrightness(1, {new_val}) | Out-Null
        """
    else:
        return "Invalid brightness level."

    _run_powershell(ps)
    return "Adjusting screen brightness."


# ── System Commands ────────────────────────────────────────────────

def pc_lock() -> str:
    """Lock the workstation."""
    err = _ensure_windows()
    if err:
        return err
    try:
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], timeout=5, check=False)
        return "Workstation locked."
    except Exception as e:
        return f"Failed to lock: {e}"


def pc_shutdown(delay: int = 60) -> str:
    """Shutdown the PC after delay seconds."""
    err = _ensure_windows()
    if err:
        return err
    if delay < 0:
        delay = 0
    try:
        subprocess.run(["shutdown", "/s", "/t", str(delay), "/c", "JARVIS initiated shutdown"], timeout=5, check=False)
        if delay > 0:
            return f"Shutdown scheduled in {delay} seconds. Run 'abort shutdown' to cancel."
        return "Shutting down now."
    except Exception as e:
        return f"Failed to initiate shutdown: {e}"


def pc_restart(delay: int = 60) -> str:
    """Restart the PC after delay seconds."""
    err = _ensure_windows()
    if err:
        return err
    if delay < 0:
        delay = 0
    try:
        subprocess.run(["shutdown", "/r", "/t", str(delay), "/c", "JARVIS initiated restart"], timeout=5, check=False)
        if delay > 0:
            return f"Restart scheduled in {delay} seconds. Run 'abort shutdown' to cancel."
        return "Restarting now."
    except Exception as e:
        return f"Failed to initiate restart: {e}"


def pc_abort_shutdown() -> str:
    """Cancel a pending shutdown/restart."""
    err = _ensure_windows()
    if err:
        return err
    try:
        subprocess.run(["shutdown", "/a"], capture_output=True, timeout=5, check=False)
        return "Shutdown cancelled."
    except Exception as e:
        return f"Failed to cancel shutdown: {e}"


def pc_sleep() -> str:
    """Put the PC to sleep."""
    err = _ensure_windows()
    if err:
        return err
    try:
        _run_powershell("(Add-Type -Assembly System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState('Sleep', $false, $false))")
        return "Putting PC to sleep."
    except Exception as e:
        return f"Failed to sleep: {e}"


def pc_hibernate() -> str:
    """Hibernate the PC."""
    err = _ensure_windows()
    if err:
        return err
    try:
        _run_powershell("(Add-Type -Assembly System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState('Hibernate', $false, $false))")
        return "Hibernating PC."
    except Exception as e:
        return f"Failed to hibernate: {e}"


# ── Screenshot ─────────────────────────────────────────────────────

def pc_screenshot(save_path: str | None = None) -> str:
    """Take a screenshot and save to file.

    Uses pyautogui if available, otherwise PowerShell fallback.

    Returns path to the saved screenshot or error message.
    """
    err = _ensure_windows()
    if err:
        return err

    if save_path is None:
        screenshot_dir = os.path.join(os.environ.get("TEMP", "/tmp"), "jarvis_screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)
        from datetime import datetime
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        save_path = os.path.join(screenshot_dir, filename)

    pg = _lazy_import_pyautogui()
    if pg:
        try:
            img = pg.screenshot()
            img.save(save_path)
            return f"Screenshot saved to {save_path}"
        except Exception as e:
            logger.warning(f"pyautogui screenshot failed: {e}")

    # PowerShell fallback
    ps_path = save_path.replace("\\", "\\\\")
    ps = f"""
    Add-Type -AssemblyName System.Windows.Forms
    $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bitmap = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
    $bitmap.Save('{ps_path}', [System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose()
    $bitmap.Dispose()
    """
    _run_powershell(ps, timeout=15)
    if os.path.exists(save_path):
        return f"Screenshot saved to {save_path}"
    return "Failed to take screenshot."


# ── Media Control ──────────────────────────────────────────────────

def pc_media_play_pause() -> str:
    """Toggle media play/pause."""
    kb = _lazy_import_keyboard()
    if kb:
        try:
            kb.send("play/pause media")
            return "Toggled play/pause."
        except Exception:
            pass
    # Fallback: PowerShell via Shell.Application
    _run_powershell("""
    $shell = New-Object -ComObject Shell.Application
    $shell.Windows() | ForEach-Object { $_.TogglePlayPause() }
    """)
    return "Toggled play/pause."


def pc_media_next() -> str:
    """Skip to next track."""
    kb = _lazy_import_keyboard()
    if kb:
        try:
            kb.send("next track")
            return "Skipped to next track."
        except Exception:
            pass
    # Fallback: send media next scan code
    import ctypes
    try:
        ctypes.windll.user32.keybd_event(0xB0, 0, 0, 0)  # VK_MEDIA_NEXT_TRACK
        ctypes.windll.user32.keybd_event(0xB0, 0, 2, 0)
    except Exception:
        pass
    return "Next track."


def pc_media_prev() -> str:
    """Go to previous track."""
    kb = _lazy_import_keyboard()
    if kb:
        try:
            kb.send("previous track")
            return "Went to previous track."
        except Exception:
            pass
    try:
        import ctypes
        ctypes.windll.user32.keybd_event(0xB1, 0, 0, 0)  # VK_MEDIA_PREV_TRACK
        ctypes.windll.user32.keybd_event(0xB1, 0, 2, 0)
    except Exception:
        pass
    return "Previous track."


# ── App Launcher ───────────────────────────────────────────────────

# Known Windows app paths
PC_APP_MAP = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "terminal": "wt.exe",
    "powershell": "powershell.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "edge": "msedge.exe",
    "word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
    "outlook": "OUTLOOK.EXE",
    "vs code": "code.exe",
    "vscode": "code.exe",
    "visual studio code": "code.exe",
    "notepad++": "notepad++.exe",
    "spotify": "spotify.exe",
    "task manager": "taskmgr.exe",
    "control panel": "control.exe",
    "settings": "ms-settings:",
    "snipping tool": "SnippingTool.exe",
    "camera": "microsoft.windows.camera:",
}


def pc_open_app(app_name: str) -> str:
    """Launch an application by name.

    Uses a built-in app map for common apps, then falls back to
    'start' command for anything else.
    """
    err = _ensure_windows()
    if err:
        return err

    name = app_name.lower().strip()

    # Check app map
    for key, exec_path in PC_APP_MAP.items():
        if key in name:
            try:
                if exec_path.endswith(":"):
                    # URI scheme (like ms-settings:)
                    subprocess.Popen(["start", exec_path], shell=True)
                else:
                    subprocess.Popen([exec_path])
                return f"Opening {app_name}."
            except Exception as e:
                return f"Failed to open {app_name}: {e}"

    # Try 'start' as fallback
    try:
        subprocess.Popen(["start", app_name], shell=True)
        return f"Opening {app_name}."
    except Exception:
        return f"Could not find '{app_name}' to open."


# ── Keyboard Typing ────────────────────────────────────────────────

def pc_type_text(text: str) -> str:
    """Type text using keyboard simulation.

    Uses pyautogui if available, otherwise keyboard library.
    """
    err = _ensure_windows()
    if err:
        return err

    pg = _lazy_import_pyautogui()
    if pg:
        try:
            pg.typewrite(text, interval=0.02)
            return f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}"
        except Exception:
            pass

    kb = _lazy_import_keyboard()
    if kb:
        try:
            kb.write(text, delay=0.02)
            return f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}"
        except Exception:
            pass

    return "Could not type text (pyautogui/keyboard not installed)."


# ── Window Management ──────────────────────────────────────────────

def pc_list_windows() -> str:
    """List open window titles. Returns a formatted string."""
    err = _ensure_windows()
    if err:
        return err

    gw = _lazy_import_pygetwindow()
    if gw:
        try:
            windows = gw.getAllTitles()
            open_wins = [w for w in windows if w.strip()]
            if not open_wins:
                return "No open windows found."
            return "Open windows:\n" + "\n".join(f"  {i}. {w}" for i, w in enumerate(open_wins[:20], 1))
        except Exception:
            pass

    # PowerShell fallback
    ps_output = _run_powershell("""
    Get-Process | Where-Object { $_.MainWindowTitle -ne '' } |
        Select-Object -ExpandProperty MainWindowTitle |
        Sort-Object -Unique |
        Select-Object -First 20
    """)
    if ps_output:
        lines = ps_output.strip().split("\n")
        return "Open windows:\n" + "\n".join(f"  {i}. {w}" for i, w in enumerate(lines, 1))
    return "Could not list windows."


def pc_activate_window(title: str) -> str:
    """Bring a window matching title to the foreground."""
    err = _ensure_windows()
    if err:
        return err

    gw = _lazy_import_pygetwindow()
    if gw:
        try:
            windows = gw.getWindowsWithTitle(title)
            if windows:
                windows[0].activate()
                return f"Switched to {title}."
        except Exception:
            pass

    # PowerShell fallback
    safe_title = title.replace("'", "''")
    ps = f"""
    $w = Get-Process | Where-Object {{ $_.MainWindowTitle -like '*{safe_title}*' }} | Select-Object -First 1
    if ($w) {{
        Add-Type @"
            using System;
            using System.Runtime.InteropServices;
            public class WinAPI {{
                [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
            }}
"@
        [WinAPI]::SetForegroundWindow($w.MainWindowHandle)
        Write-Output "Switched to $($w.MainWindowTitle)"
    }} else {{
        Write-Output "No window matching '{safe_title}' found."
    }}
    """
    output = _run_powershell(ps, timeout=10)
    if output and "Switched" in output:
        return output
    return f"Could not find window matching '{title}'."


# ── Battery & System Info ──────────────────────────────────────────

def pc_battery_status() -> str:
    """Get battery level and charging status."""
    err = _ensure_windows()
    if err:
        return err

    ps = """
    $batt = Get-WmiObject -Class Win32_Battery
    if ($batt) {
        $pct = $batt.EstimatedChargeRemaining
        $status = switch ($batt.BatteryStatus) {
            1 { "Discharging" }
            2 { "On AC power" }
            3 { "Fully Charged" }
            4 { "Low" }
            5 { "Critical" }
            6 { "Charging" }
            7 { "Charging & High" }
            8 { "Charging & Low" }
            9 { "Charging & Critical" }
            10 { "Undefined" }
            11 { "Partially Charged" }
            default { "Unknown" }
        }
        Write-Output "Battery: ${pct}% ($status)"
    } else {
        Write-Output "No battery detected (desktop PC?)"
    }
    """
    output = _run_powershell(ps)
    return output or "Could not read battery status."


def pc_wifi_status() -> str:
    """Get WiFi connection status and SSID."""
    err = _ensure_windows()
    if err:
        return err

    output = _run_powershell("""
    $wifi = netsh wlan show interfaces | Select-String "SSID\\s*:\\s*(.+)$"
    $state = netsh wlan show interfaces | Select-String "State\\s*:\\s*(.+)$"
    if ($wifi) {
        $ssid = $wifi.Matches.Groups[1].Value.Trim()
        $connected = if ($state) { $state.Matches.Groups[1].Value.Trim() } else { "Unknown" }
        Write-Output "WiFi: $ssid ($connected)"
    } else {
        Write-Output "WiFi: Not connected"
    }
    """)
    return output or "Could not read WiFi status."


def pc_notification(title: str, message: str) -> str:
    """Show a Windows toast notification.

    Uses PowerShell to display a toast notification via Windows.UI.Notifications.
    """
    err = _ensure_windows()
    if err:
        return err

    safe_title = title.replace("'", "''")
    safe_msg = message.replace("'", "''")
    ps = f"""
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
    $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
    $textNodes = $template.GetElementsByTagName("text")
    $textNodes.Item(0).AppendChild($template.CreateTextNode('{safe_title}')) > $null
    $textNodes.Item(1).AppendChild($template.CreateTextNode('{safe_msg}')) > $null
    $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("JARVIS").Show($toast)
    """
    _run_powershell(ps, timeout=10)
    return f"Notification sent: {title}"


# ── get_system_info (enhanced) ─────────────────────────────────────

def pc_get_system_info() -> str:
    """Get detailed PC system info.

    Extends the basic get_system_info in tasks.py with PC-specific details.
    """
    err = _ensure_windows()
    if err:
        return err

    ps = """
    $os = Get-CimInstance Win32_OperatingSystem
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    $ram = Get-CimInstance Win32_ComputerSystem
    $gpu = Get-CimInstance Win32_VideoController | Select-Object -First 1
    $disk = Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | Where-Object { $_.DeviceID -eq 'C:' }

    $osName = $os.Caption
    $osVer = $os.Version
    $cpuName = $cpu.Name
    $ramGB = [Math]::Round($ram.TotalPhysicalMemory / 1GB, 1)
    $gpuName = if ($gpu) { $gpu.Name } else { "N/A" }
    $diskFree = if ($disk) { [Math]::Round($disk.FreeSpace / 1GB, 1) } else { "N/A" }
    $diskTotal = if ($disk) { [Math]::Round($disk.Size / 1GB, 1) } else { "N/A" }

    Write-Output "OS: $osName (Build $osVer)"
    Write-Output "CPU: $cpuName"
    Write-Output "RAM: ${ramGB}GB"
    Write-Output "GPU: $gpuName"
    Write-Output "C: Drive: ${diskFree}GB free / ${diskTotal}GB total"
    """
    output = _run_powershell(ps)
    return output.replace("\n", " | ") if output else "Could not read system info."


# ── Main dispatcher for tasks.py ───────────────────────────────────

def handle_pc_command(query: str) -> dict:
    """Parse a PC control command from natural language and dispatch.

    Args:
        query: Natural language command (e.g. "volume up", "lock PC",
               "screenshot", "open notepad")

    Returns:
        dict with keys: reply, action, payload
    """
    q = query.lower().strip()

    # ── Volume ──────────────────────────────────────────────────
    if "volume" in q:
        if "up" in q or "increase" in q or "raise" in q or "louder" in q:
            return {"reply": pc_volume("up"), "action": "pc_volume", "payload": "up"}
        if "down" in q or "decrease" in q or "lower" in q:
            return {"reply": pc_volume("down"), "action": "pc_volume", "payload": "down"}
        if "max" in q or "full" in q or "100" in q:
            return {"reply": pc_volume("max"), "action": "pc_volume", "payload": 100}
        if "mute" in q:
            return {"reply": pc_mute(), "action": "pc_volume", "payload": "mute"}
        if "unmute" in q:
            return {"reply": pc_unmute(), "action": "pc_volume", "payload": "unmute"}
        # Try to extract a number
        num_match = re.search(r'(\d{1,3})', q)
        if num_match:
            val = int(num_match.group(1))
            if 0 <= val <= 100:
                return {"reply": pc_volume(val), "action": "pc_volume", "payload": val}
        return {"reply": pc_volume("up"), "action": "pc_volume", "payload": "up"}

    # ── Mute / Unmute ───────────────────────────────────────────
    if q.startswith("mute") and "volume" not in q:
        return {"reply": pc_mute(), "action": "pc_volume", "payload": "mute"}
    if q.startswith("unmute"):
        return {"reply": pc_unmute(), "action": "pc_volume", "payload": "unmute"}

    # ── Brightness ──────────────────────────────────────────────
    if "brightness" in q:
        if "up" in q or "increase" in q:
            return {"reply": pc_brightness("up"), "action": "pc_brightness", "payload": "up"}
        if "down" in q or "decrease" in q:
            return {"reply": pc_brightness("down"), "action": "pc_brightness", "payload": "down"}
        if "max" in q or "full" in q:
            return {"reply": pc_brightness("max"), "action": "pc_brightness", "payload": 100}
        if "min" in q:
            return {"reply": pc_brightness("min"), "action": "pc_brightness", "payload": 0}
        num_match = re.search(r'(\d{1,3})', q)
        if num_match:
            val = int(num_match.group(1))
            if 0 <= val <= 100:
                return {"reply": pc_brightness(val), "action": "pc_brightness", "payload": val}
        return {"reply": pc_brightness("up"), "action": "pc_brightness", "payload": "up"}

    # ── Lock ────────────────────────────────────────────────────
    if q in ("lock", "lock pc", "lock computer", "lock laptop", "lock workstation"):
        return {"reply": pc_lock(), "action": "pc_lock", "payload": {}}

    # ── Shutdown / Restart / Sleep / Hibernate ──────────────────
    if "shutdown" in q or "shut down" in q:
        if "abort" in q or "cancel" in q:
            return {"reply": pc_abort_shutdown(), "action": "pc_shutdown", "payload": "abort"}
        return {"reply": pc_shutdown(60), "action": "pc_shutdown", "payload": 60}

    if "restart" in q or "reboot" in q:
        return {"reply": pc_restart(60), "action": "pc_restart", "payload": 60}

    if "sleep" in q and "pc" in q or ("sleep" in q and "computer" in q):
        return {"reply": pc_sleep(), "action": "pc_sleep", "payload": {}}

    if "hibernate" in q:
        return {"reply": pc_hibernate(), "action": "pc_hibernate", "payload": {}}

    # ── Screenshot ──────────────────────────────────────────────
    if "screenshot" in q or "capture screen" in q or "print screen" in q:
        return {"reply": pc_screenshot(), "action": "pc_screenshot", "payload": {}}

    # ── Media Control ───────────────────────────────────────────
    if any(kw in q for kw in ["play", "pause"]) and any(kw in q for kw in ["music", "song", "media", "video", "track"]):
        return {"reply": pc_media_play_pause(), "action": "pc_media", "payload": "play_pause"}
    if any(kw in q for kw in ["next track", "skip track", "next song", "next media"]):
        return {"reply": pc_media_next(), "action": "pc_media", "payload": "next"}
    if any(kw in q for kw in ["previous track", "prev track", "previous song", "back track"]):
        return {"reply": pc_media_prev(), "action": "pc_media", "payload": "prev"}
    if "play/pause" in q:
        return {"reply": pc_media_play_pause(), "action": "pc_media", "payload": "play_pause"}

    # ── App Launcher ────────────────────────────────────────────
    if "open " in q or "launch " in q:
        match = re.search(r"\b(?:open|launch)\s+(.+)$", q)
        if not match:
            match = re.search(r"\b(?:open|launch)\s+(.+)", q)
        if match:
            app_name = match.group(1).strip()
            return {"reply": pc_open_app(app_name), "action": "pc_open_app", "payload": app_name}

    # ── Type text ───────────────────────────────────────────────
    if q.startswith(("type ", "write ")):
        text = q[5:] if q.startswith("type ") else q[6:]  # Keep index logic but group prefix check
        if text:
            return {"reply": pc_type_text(text), "action": "pc_type", "payload": text}

    # ── Window Management ───────────────────────────────────────
    if "list windows" in q or "open windows" in q or "show windows" in q:
        return {"reply": pc_list_windows(), "action": "pc_list_windows", "payload": {}}

    if "switch to " in q or "activate " in q:
        match = re.search(r"(?:switch to|activate)\s+(.+)$", q)
        if match:
            title = match.group(1).strip()
            return {"reply": pc_activate_window(title), "action": "pc_activate_window", "payload": title}

    # ── Battery ─────────────────────────────────────────────────
    if "battery" in q or "power" in q:
        return {"reply": pc_battery_status(), "action": "pc_battery", "payload": {}}

    # ── WiFi ────────────────────────────────────────────────────
    if "wifi" in q or "wi-fi" in q or "network" in q:
        return {"reply": pc_wifi_status(), "action": "pc_wifi", "payload": {}}

    # ── System Info ─────────────────────────────────────────────
    if any(kw in q for kw in ["system info", "pc info", "computer info", "specs", "hardware"]):
        return {"reply": pc_get_system_info(), "action": "pc_system_info", "payload": {}}

    return {"reply": "PC command not recognized. Try 'volume up', 'lock PC', 'screenshot', or 'open notepad'.", "action": "none", "payload": {}}
