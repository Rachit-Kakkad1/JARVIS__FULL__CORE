"""
JARVIS Memory — Cognitive Tri-Tier Architecture
Handles Episodic (short-term), Semantic (long-term facts), and Working Context.
"""

import os
import json
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CONFIG
import logging

logger = logging.getLogger(__name__)

# ── MEMORY PATHS ─────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "memory")
EPISODIC_FILE = os.path.join(DATA_DIR, "episodic_memory.json")
SEMANTIC_FILE = os.path.join(DATA_DIR, "semantic_memory.json")
CONTEXT_FILE = os.path.join(DATA_DIR, "working_context.json")

# ── TRIGGERS ─────────────────────────────────────────────────────────────────
FACT_TRIGGERS = [
    "my name is", "i am", "i work", "i like", "i love",
    "i hate", "i live", "call me", "i study", "i'm from",
    "i prefer", "my favorite", "my favourite", "i go to", 
    "i play", "i want", "i need",
]


def _load_json(file_path, default):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return default


def _save_json(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── CORE API ─────────────────────────────────────────────────────────────────

def load_memory():
    """Load all memory layers. Returns dict bridging legacy interface."""
    episodic = _load_json(EPISODIC_FILE, [])
    semantic = _load_json(SEMANTIC_FILE, [])
    context = _load_json(CONTEXT_FILE, {})
    
    return {
        "history": episodic,
        "facts": semantic,
        "context": context
    }


def save_memory(mem):
    """Save all memory layers to disk."""
    _save_json(EPISODIC_FILE, mem.get("history", []))
    _save_json(SEMANTIC_FILE, mem.get("facts", []))
    _save_json(CONTEXT_FILE, mem.get("context", {}))


# ── EXTRACTORS & HELPERS ─────────────────────────────────────────────────────

def extract_facts(text):
    text_lower = text.lower().strip()
    for trigger in FACT_TRIGGERS:
        if trigger in text_lower:
            return [text.strip()]
    return []


def trim_history(history, max_messages=None):
    if max_messages is None:
        max_messages = CONFIG.get("MAX_HISTORY", 5)
    max_entries = max_messages * 2
    if len(history) > max_entries:
        return history[-max_entries:]
    return history


def add_exchange(mem, user_text, assistant_text):
    """Legacy bridge support: Add exchange and extract facts."""
    new_facts = extract_facts(user_text)
    if new_facts:
        for f in new_facts:
            if f not in mem["facts"]:
                mem["facts"].append(f)
                
    mem["history"].append({"role": "user", "content": user_text})
    mem["history"].append({"role": "assistant", "content": assistant_text})
    mem["history"] = trim_history(mem["history"])
    save_memory(mem)
    return mem


# ── WORKING CONTEXT API (With TTL) ───────────────────────────────────────────
import time

CONTEXT_TTL_SECONDS = 600 # 10 minutes

def update_context(key, value):
    """Update a specific key in the working context with a timestamp."""
    mem = load_memory()
    mem["context"][key] = {
        "value": value,
        "timestamp": time.time()
    }
    _save_json(CONTEXT_FILE, mem["context"])

def get_context(key, default=None):
    """Retrieve a specific key from the working context if it hasn't expired."""
    data = _load_json(CONTEXT_FILE, {}).get(key)
    if not data or not isinstance(data, dict):
        return default
        
    age = time.time() - data.get("timestamp", 0)
    if age > CONTEXT_TTL_SECONDS:
        # Expired, clean it up silently in memory (will flush to disk later)
        return default
        
    return data.get("value", default)

def clear_context():
    """Clear all working context."""
    _save_json(CONTEXT_FILE, {})
