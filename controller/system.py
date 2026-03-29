"""
JARVIS System Controller — Volume, brightness, power, screenshots, lock.
Windows-specific implementations with graceful fallbacks.
"""

import os
import ctypes
from datetime import datetime
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CONFIG

# Try importing optional dependencies
try:
    import pyautogui
    _pyautogui_available = True
except ImportError:
    _pyautogui_available = False

try:
    from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    from ctypes import cast, POINTER
    _pycaw_available = True
except ImportError:
    _pycaw_available = False

try:
    import screen_brightness_control as sbc
    _sbc_available = True
except ImportError:
    _sbc_available = False


# ── VOLUME ───────────────────────────────────────────────────────────

def _get_volume_interface():
    """Get the Windows audio endpoint volume interface."""
    if not _pycaw_available:
        return None
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))
    except Exception:
        return None


def volume_up():
    """Increase system volume by ~10%."""
    vol = _get_volume_interface()
    if vol:
        try:
            current = vol.GetMasterVolumeLevelScalar()
            new_level = min(1.0, current + 0.1)
            vol.SetMasterVolumeLevelScalar(new_level, None)
            return f"Volume increased to {int(new_level * 100)}%, {CONFIG['USER_NAME']}."
        except Exception:
            pass

    # Fallback to pyautogui
    if _pyautogui_available:
        for _ in range(5):
            pyautogui.hotkey('volumeup')
        return f"Volume increased, {CONFIG['USER_NAME']}."

    return f"Volume control is not available, {CONFIG['USER_NAME']}."


def volume_down():
    """Decrease system volume by ~10%."""
    vol = _get_volume_interface()
    if vol:
        try:
            current = vol.GetMasterVolumeLevelScalar()
            new_level = max(0.0, current - 0.1)
            vol.SetMasterVolumeLevelScalar(new_level, None)
            return f"Volume decreased to {int(new_level * 100)}%, {CONFIG['USER_NAME']}."
        except Exception:
            pass

    if _pyautogui_available:
        for _ in range(5):
            pyautogui.hotkey('volumedown')
        return f"Volume decreased, {CONFIG['USER_NAME']}."

    return f"Volume control is not available, {CONFIG['USER_NAME']}."


def mute():
    """Mute system audio."""
    vol = _get_volume_interface()
    if vol:
        try:
            vol.SetMute(1, None)
            return f"System muted, {CONFIG['USER_NAME']}."
        except Exception:
            pass

    if _pyautogui_available:
        pyautogui.hotkey('volumemute')
        return f"System muted, {CONFIG['USER_NAME']}."

    return f"Mute control is not available, {CONFIG['USER_NAME']}."


def unmute():
    """Unmute system audio."""
    vol = _get_volume_interface()
    if vol:
        try:
            vol.SetMute(0, None)
            return f"System unmuted, {CONFIG['USER_NAME']}."
        except Exception:
            pass

    if _pyautogui_available:
        pyautogui.hotkey('volumemute')
        return f"System unmuted, {CONFIG['USER_NAME']}."

    return f"Unmute control is not available, {CONFIG['USER_NAME']}."


def set_volume(level):
    """
    Set system volume to a specific percentage.
    
    Args:
        level: Volume level 0-100
    """
    level = max(0, min(100, int(level)))

    vol = _get_volume_interface()
    if vol:
        try:
            vol.SetMasterVolumeLevelScalar(level / 100.0, None)
            return f"Volume set to {level}%, {CONFIG['USER_NAME']}."
        except Exception:
            pass

    return f"Could not set volume to {level}%, {CONFIG['USER_NAME']}. Pycaw may not be available."


# ── SCREENSHOT ───────────────────────────────────────────────────────

def screenshot(save_dir=None):
    """Take a screenshot and save it."""
    if not _pyautogui_available:
        return f"Screenshot capability not available, {CONFIG['USER_NAME']}. Please install pyautogui."

    if save_dir is None:
        save_dir = os.path.expandvars(CONFIG.get("SCREENSHOT_DIR", "."))

    try:
        os.makedirs(save_dir, exist_ok=True)
        filename = f"jarvis_{datetime.now():%Y%m%d_%H%M%S}.png"
        path = os.path.join(save_dir, filename)
        pyautogui.screenshot(path)
        return f"Screenshot saved to {path}, {CONFIG['USER_NAME']}."
    except Exception as e:
        return f"Error taking screenshot: {e}"


# ── LOCK SCREEN ──────────────────────────────────────────────────────

def lock_screen():
    """Lock the Windows workstation."""
    try:
        ctypes.windll.user32.LockWorkStation()
        return f"Locking workstation, {CONFIG['USER_NAME']}."
    except Exception as e:
        return f"Could not lock screen: {e}"


# ── POWER ────────────────────────────────────────────────────────────

def shutdown(cmd):
    """
    Execute a power command.
    
    Args:
        cmd: "shutdown", "restart", or "sleep"
    """
    cmds = {
        "shutdown": "shutdown /s /t 5",
        "restart": "shutdown /r /t 5",
        "sleep": "rundll32.exe powrprof.dll,SetSuspendState 0,1,0",
    }

    command = cmds.get(cmd)
    if not command:
        return f"Unknown power command: {cmd}"

    try:
        os.system(command)
        return f"Initiating {cmd}, {CONFIG['USER_NAME']}. Goodbye."
    except Exception as e:
        return f"Error executing {cmd}: {e}"


# ── BRIGHTNESS ───────────────────────────────────────────────────────

def get_brightness():
    """Get current screen brightness level."""
    if not _sbc_available:
        return None
    try:
        level = sbc.get_brightness()
        return level[0] if isinstance(level, list) else level
    except Exception:
        return None


def set_brightness(level):
    """Set screen brightness to a specific level."""
    if not _sbc_available:
        return f"Brightness control not available, {CONFIG['USER_NAME']}. Please install screen-brightness-control."
    try:
        level = max(0, min(100, int(level)))
        sbc.set_brightness(level)
        return f"Brightness set to {level}%, {CONFIG['USER_NAME']}."
    except Exception as e:
        return f"Error setting brightness: {e}"


def brightness_up():
    """Increase brightness by 10%."""
    current = get_brightness()
    if current is not None:
        new_level = min(100, current + 10)
        return set_brightness(new_level)
    return f"Could not adjust brightness, {CONFIG['USER_NAME']}."


def brightness_down():
    """Decrease brightness by 10%."""
    current = get_brightness()
    if current is not None:
        new_level = max(0, current - 10)
        return set_brightness(new_level)
    return f"Could not adjust brightness, {CONFIG['USER_NAME']}."
