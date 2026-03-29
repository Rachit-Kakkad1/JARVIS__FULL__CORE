"""
JARVIS Apps Controller — Open/close applications, focus windows.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CONFIG

try:
    import psutil
    _psutil_available = True
except ImportError:
    _psutil_available = False
    print("⚠️  psutil not installed. Process management limited.")

try:
    import pygetwindow as gw
    _gw_available = True
except ImportError:
    _gw_available = False


def open_app(name):
    """
    Open an application by name.
    
    Args:
        name: Application name (must match a key in CONFIG["APP_PATHS"])
    
    Returns:
        str: Confirmation message
    """
    name_lower = name.lower().strip()
    fuzzy_used = False

    # Look up in configured app paths
    app_paths = CONFIG.get("APP_PATHS", {})
    path = app_paths.get(name_lower)

    if not path:
        # Try advanced fuzzy match from parser
        try:
            from controller.parser import _fuzzy_app_match
            fuzzy_key = _fuzzy_app_match(name_lower)
            if fuzzy_key:
                path = app_paths[fuzzy_key]
                name_lower = fuzzy_key
                fuzzy_used = True
        except ImportError:
            pass

    if not path:
        return f"I don't have a path configured for '{name}', {CONFIG['USER_NAME']}. Please add it to config.py."

    try:
        # Expand environment variables
        expanded = os.path.expandvars(path)

        # Handle commands with arguments (like Discord's --processStart)
        if " " in expanded and not os.path.exists(expanded):
            parts = expanded.split(" ", 1)
            if os.path.exists(parts[0]):
                subprocess.Popen(expanded, shell=True)
            else:
                subprocess.Popen(expanded, shell=True)
        else:
            subprocess.Popen([expanded])

        if fuzzy_used:
            return f"I couldn't find exactly '{name}', but I found a close match. Opening {name_lower.title()}, {CONFIG['USER_NAME']}."
        return f"Opening {name_lower.title()}, {CONFIG['USER_NAME']}."

    except FileNotFoundError:
        return f"Could not find {name_lower.title()} at the configured path, {CONFIG['USER_NAME']}. Please verify the path in config.py."
    except Exception as e:
        return f"Error opening {name_lower.title()}: {e}"


def close_app(name):
    """
    Close an application by name.
    
    Args:
        name: Application name or process name
    
    Returns:
        str: Confirmation message
    """
    if not _psutil_available:
        return f"Process management is not available, {CONFIG['USER_NAME']}. Please install psutil."

    name_lower = name.lower().strip()
    killed = False

    for proc in psutil.process_iter(['name', 'pid']):
        try:
            proc_name = proc.info['name'].lower()
            if name_lower in proc_name or proc_name.replace(".exe", "") in name_lower:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except psutil.TimeoutExpired:
                    proc.kill()
                killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if killed:
        return f"Closing {name.title()}, {CONFIG['USER_NAME']}."
    else:
        return f"Could not find a running process for '{name}', {CONFIG['USER_NAME']}."


def list_running():
    """
    List all running process names.
    
    Returns:
        list[str]: List of process names
    """
    if not _psutil_available:
        return []

    processes = set()
    for proc in psutil.process_iter(['name']):
        try:
            processes.add(proc.info['name'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return sorted(processes)


def focus_window(title_keyword):
    """
    Focus a window by title keyword.
    
    Args:
        title_keyword: Substring to search in window titles
    
    Returns:
        bool: True if window found and focused
    """
    if not _gw_available:
        return False

    try:
        windows = gw.getWindowsWithTitle(title_keyword)
        if windows:
            win = windows[0]
            if win.isMinimized:
                win.restore()
            win.activate()
            return True
    except Exception:
        pass

    return False
