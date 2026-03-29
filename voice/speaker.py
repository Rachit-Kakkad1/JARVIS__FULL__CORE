"""
JARVIS Speaker — Text-to-speech using pyttsx3 (offline).
Graceful degradation: if pyttsx3 not installed, prints only.
"""

import threading
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CONFIG

_engine = None
_engine_lock = threading.Lock()
_tts_available = False

try:
    import pyttsx3
    _tts_available = True
except ImportError:
    print("⚠️  pyttsx3 not installed. Voice output disabled (text-only mode).")


def _init_engine():
    """Initialize the pyttsx3 engine with preferred voice settings."""
    global _engine
    if not _tts_available:
        return None

    try:
        _engine = pyttsx3.init()
        _engine.setProperty("rate", CONFIG.get("VOICE_SPEED", 160))
        _engine.setProperty("volume", CONFIG.get("VOICE_VOLUME", 1.0))

        # Auto-select deepest male voice
        voices = _engine.getProperty("voices")
        priority_keywords = ["david", "daniel", "mark", "james", "male"]
        selected = None

        for keyword in priority_keywords:
            for voice in voices:
                if keyword in voice.name.lower() or keyword in voice.id.lower():
                    selected = voice
                    break
            if selected:
                break

        if selected:
            _engine.setProperty("voice", selected.id)
            print(f"🔊 Voice selected: {selected.name}")
        elif voices:
            # Fallback to first available voice
            _engine.setProperty("voice", voices[0].id)
            print(f"🔊 Voice fallback: {voices[0].name}")

        return _engine
    except Exception as e:
        print(f"⚠️  TTS engine init failed: {e}")
        return None


def speak(text):
    """
    Speak text aloud and print to console.
    Blocks until speech is complete.
    """
    print(f"\n🤖 JARVIS: {text}\n")

    if not _tts_available or not CONFIG.get("VOICE_OUTPUT", True):
        return

    with _engine_lock:
        global _engine
        if _engine is None:
            _engine = _init_engine()
        if _engine is None:
            return

        try:
            _engine.say(text)
            _engine.runAndWait()
        except RuntimeError:
            # Engine might be in a bad state, reinitialize
            try:
                _engine = _init_engine()
                if _engine:
                    _engine.say(text)
                    _engine.runAndWait()
            except Exception:
                pass
        except Exception as e:
            print(f"⚠️  TTS error: {e}")


def speak_async(text):
    """
    Speak text aloud in a background daemon thread (non-blocking).
    """
    t = threading.Thread(target=speak, args=(text,), daemon=True)
    t.start()
    return t
