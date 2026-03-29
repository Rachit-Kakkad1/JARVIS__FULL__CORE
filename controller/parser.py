"""
JARVIS Command Parser — Production-Grade Intent Recognition System
Fully deterministic, hybrid fuzzy pipeline using RapidFuzz.
"""

import re
import sys
import os

try:
    from rapidfuzz import fuzz, process
    _rapidfuzz_available = True
except ImportError:
    _rapidfuzz_available = False
    fuzz = None
    process = None
    print("⚠️ RapidFuzz not installed. Please run: pip install rapidfuzz")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CONFIG
import logging

logger = logging.getLogger(__name__)

# ── STEP 2: PRELOADED INTENTS (Sub 10ms requirement) ─────────────────────────
INTENTS = {
    "sleep_jarvis": ["sleep", "rest", "pause", "nap", "idle"],
    "shutdown_jarvis": ["shutdown", "power off", "turn off", "shut down", "kill"],
    "restart_pc": ["restart", "reboot"],
    "sleep_pc": ["hibernate"],
    "open_app": ["open", "launch", "start", "run"],
    "close_app": ["close", "exit", "stop", "terminate"],
    "youtube": ["play", "youtube", "watch"],
    "volume": ["volume", "sound", "mute", "unmute", "louder", "quieter"],
    "screenshot": ["screenshot", "capture"],
    "system_info": ["cpu", "ram", "memory", "status", "health"],
    "lock": ["lock", "lock screen"],
    "brightness": ["brightness", "screen", "dimmer", "brighter"],
    "open_url": ["open website", "go to", "navigate", "visit"],
    "clipboard": ["clipboard", "copy", "paste"],
    "plan_goal": ["prepare", "setup", "get ready", "plan"]
}

# ── STEP 1: NORMALIZATION LAYER ──────────────────────────────────────────────
FILLERS = ["please", "can", "you", "could", "jarvis", "hey", "just", "like", "um", 
           "sir", "a", "the", "my", "your", "yours", "yourself", "computer", "system", "on", "for", "me", "now"]

def _normalize(text: str) -> str:
    # Convert to lowercase
    text = text.lower()
    # Strip punctuation
    text = re.sub(r'[^\w\s]', '', text)
    # Remove filler words
    words = text.split()
    filtered = [w for w in words if w not in FILLERS]
    # Collapse whitespace
    return " ".join(filtered).strip()

def parse(text: str):
    """
    3-Stage Hybrid Pipeline:
    1. Normalization
    2. Intent Detection (fuzzy matching)
    3. Entity Extraction
    """
    if not text:
        return None

    if not _rapidfuzz_available:
        return None  # Fall through to AI brain if fuzzy matching unavailable

    norm_text = _normalize(text)
    if not norm_text:
        return None

    # ── STEP 3: FUZZY MATCHING ENGINE ────────────────────────────────────────
    best_intent = None
    best_score = 0
    matched_keyword = ""

    for intent, keywords in INTENTS.items():
        for kw in keywords:
            # token_set_ratio is best for partial/typo phrases
            score = fuzz.token_set_ratio(kw, norm_text)
            if score > best_score:
                best_score = score
                best_intent = intent
                matched_keyword = kw

    # 3b. Check User-Defined Multi-Step Macros
    try:
        from core.task_executor import load_macros
        macros = load_macros()
        for macro_name in macros.keys():
            m_score = fuzz.token_set_ratio(macro_name, norm_text)
            if m_score > best_score:
                best_score = m_score
                best_intent = "macro"
                matched_keyword = macro_name
    except ImportError:
        pass

    # Step 5: Confidence Thresholding
    if best_score < 70:
        return None # Fallback to AI Brain

    # ── STEP 4: ENTITY EXTRACTION ────────────────────────────────────────────
    target = norm_text
    
    # Try to dynamically locate the exact word that matched the keyword to remove it
    if len(matched_keyword.split()) == 1:
        best_w = ""
        best_w_score = 0
        for w in norm_text.split():
            s = fuzz.ratio(matched_keyword, w)
            if s > best_w_score:
                best_w_score = s
                best_w = w
        if best_w_score >= 70:
            target = norm_text.replace(best_w, "", 1).strip()
    else:
        # Multi-word exact replacement fallback
        target = norm_text.replace(matched_keyword, "", 1).strip()

    target = target if target else None

    # Construct strict arguments based on intent
    args = {}
    action = best_intent
    
    if action == "volume":
        if "up" in norm_text or "louder" in norm_text: args["dir"] = "up"
        elif "down" in norm_text or "quieter" in norm_text: args["dir"] = "down"
        elif "unmute" in norm_text: args["dir"] = "unmute"
        elif "mute" in norm_text: args["dir"] = "mute"
        else:
            pct = re.search(r"(\d+)", norm_text)
            if pct: args["level"] = int(pct.group(1))

    elif action == "brightness":
        if "up" in norm_text or "brighter" in norm_text: args["dir"] = "up"
        elif "down" in norm_text or "dimmer" in norm_text: args["dir"] = "down"
        else:
            pct = re.search(r"(\d+)", norm_text)
            if pct: args["level"] = int(pct.group(1))

    elif action == "restart_pc":
        action = "power"
        args["cmd"] = "restart"
        
    elif action == "sleep_pc":
        action = "power"
        args["cmd"] = "sleep"

    elif action == "clipboard":
        args["op"] = "read"
        
    elif action == "youtube":
        if target:
            target = re.sub(r"youtube", "", target).strip() # clean trailing artifacts

    # ── STEP 7: ERROR HANDLING ───────────────────────────────────────────────
    needs_target = ["open_app", "close_app", "open_url", "open_file"]
    error_response = None
    
    if action in needs_target and not target:
        error_response = "Could you clarify what you want me to open, Sir?"

    # Ensure return dict meets spec (also map "action" for legacy bridge compatibility)
    return {
        "intent": best_intent,
        "action": action,
        "target": target,
        "confidence": best_score,
        "args": args,
        "error_response": error_response
    }

def _fuzzy_app_match(name):
    """
    Suggest closest match using fuzzy matching if app not found.
    Used by apps.py controller when returning 'app not found'.
    """
    if not _rapidfuzz_available:
        return None
    known_apps = CONFIG.get("APP_PATHS", {})
    if not known_apps:
        return None
        
    match = process.extractOne(name, known_apps.keys(), scorer=fuzz.ratio)
    if match and match[1] >= 75:
        return match[0]
    return None
