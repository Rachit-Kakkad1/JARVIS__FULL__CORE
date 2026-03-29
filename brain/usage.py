"""
JARVIS Usage Tracker — Daily API request counter (100/day limit).
"""

import os
import json
from datetime import date

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CONFIG

USAGE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "jarvis_usage.json")


def load_usage():
    """Load usage data from JSON file. Resets if it's a new day."""
    today = date.today().isoformat()
    try:
        if os.path.exists(USAGE_FILE):
            with open(USAGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("date") == today:
                    return data
    except (json.JSONDecodeError, IOError):
        pass
    # New day or first run
    return {"date": today, "count": 0}


def save_usage(usage_data):
    """Save usage data to JSON file."""
    os.makedirs(os.path.dirname(USAGE_FILE), exist_ok=True)
    with open(USAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(usage_data, f, indent=2)


def check(speak_fn=None):
    """
    Check if daily limit has been reached.
    
    Args:
        speak_fn: Optional function to speak warning message
    
    Returns:
        bool: True if requests are available, False if limit reached
    """
    usage = load_usage()
    limit = CONFIG.get("DAILY_LIMIT", 100)
    if usage["count"] >= limit:
        msg = f"I've reached the daily API limit of {limit} requests, {CONFIG['USER_NAME']}. I'll be fully operational again tomorrow."
        print(f"\n⚠️  {msg}")
        if speak_fn:
            try:
                speak_fn(msg)
            except Exception:
                pass
        return False
    return True


def increment():
    """Increment the daily request counter and save."""
    usage = load_usage()
    usage["count"] += 1
    save_usage(usage)
    return usage["count"]


def remaining():
    """Return the number of API requests remaining today."""
    usage = load_usage()
    limit = CONFIG.get("DAILY_LIMIT", 100)
    return max(0, limit - usage["count"])


def get_count():
    """Return the current request count for today."""
    usage = load_usage()
    return usage["count"]
