"""
JARVIS Files Controller — Open files, search, read/write.
"""

import os
import subprocess
import glob
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CONFIG


def open_file(path):
    """
    Open a file or folder using the system default application.
    
    Args:
        path: File or folder path to open
    
    Returns:
        str: Confirmation message
    """
    expanded = os.path.expandvars(os.path.expanduser(path))

    if os.path.exists(expanded):
        try:
            os.startfile(expanded)
            return f"Opening {os.path.basename(expanded)}, {CONFIG['USER_NAME']}."
        except Exception as e:
            return f"Error opening file: {e}"
    else:
        # Try searching for it
        results = search_file(path)
        if results:
            try:
                os.startfile(results[0])
                return f"Found and opening {os.path.basename(results[0])}, {CONFIG['USER_NAME']}."
            except Exception as e:
                return f"Error opening found file: {e}"
        return f"File not found: {path}, {CONFIG['USER_NAME']}."


def search_file(name, search_dirs=None):
    """
    Search for a file by name.
    
    Args:
        name: File name or pattern to search for
        search_dirs: Directories to search in (default: common locations)
    
    Returns:
        list[str]: List of matching file paths
    """
    if search_dirs is None:
        home = os.path.expanduser("~")
        search_dirs = [
            os.path.join(home, "Desktop"),
            os.path.join(home, "Documents"),
            os.path.join(home, "Downloads"),
            os.path.join(home, "Pictures"),
            os.path.join(home, "Videos"),
            os.path.join(home, "Music"),
        ]

    results = []
    for directory in search_dirs:
        if not os.path.exists(directory):
            continue
        pattern = os.path.join(directory, "**", f"*{name}*")
        try:
            matches = glob.glob(pattern, recursive=True)
            results.extend(matches[:10])  # Limit per directory
        except Exception:
            continue

    return results[:20]  # Limit total results


def read_file(path):
    """
    Read the contents of a text file.
    
    Args:
        path: File path to read
    
    Returns:
        str: File contents or error message
    """
    expanded = os.path.expandvars(os.path.expanduser(path))

    if not os.path.exists(expanded):
        return f"File not found: {path}"

    try:
        with open(expanded, "r", encoding="utf-8") as f:
            content = f.read()
        return content[:5000]  # Limit output size
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(path, content):
    """
    Write content to a text file.
    
    Args:
        path: File path to write to
        content: Content to write
    
    Returns:
        str: Confirmation message
    """
    expanded = os.path.expandvars(os.path.expanduser(path))

    try:
        os.makedirs(os.path.dirname(expanded), exist_ok=True)
        with open(expanded, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File written: {expanded}, {CONFIG['USER_NAME']}."
    except Exception as e:
        return f"Error writing file: {e}"
