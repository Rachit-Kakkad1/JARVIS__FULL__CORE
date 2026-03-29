"""
JARVIS Wake Word — "Hey Jarvis" keyword detection loop.
Free implementation using SpeechRecognition (no API key needed).

Optional upgrade path:
    # If pvporcupine installed, use Porcupine engine for always-on
    # detection without burning CPU. See: https://picovoice.ai/porcupine/
"""

import threading
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from voice.listener import listen_once, is_available


def listen_for_wake(wake_phrase, on_detected_fn):
    """
    Continuously listen for the wake word/phrase.
    When detected, calls on_detected_fn() and returns.
    Runs in a background daemon thread.
    
    Args:
        wake_phrase: The phrase to listen for (e.g., "hey jarvis")
        on_detected_fn: Function to call when wake word is detected
    """
    if not is_available():
        print("⚠️  Wake word detection unavailable (no speech recognition).")
        return None

    def _loop():
        print(f"🎧 Wake word listener active. Say '{wake_phrase}' to activate.")
        while True:
            try:
                result = listen_once(timeout=3, phrase_limit=5)
                if result and wake_phrase in result.lower():
                    print(f"🎧 Wake word detected: '{result}'")
                    on_detected_fn()
            except Exception as e:
                print(f"⚠️  Wake word error: {e}")

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return t
