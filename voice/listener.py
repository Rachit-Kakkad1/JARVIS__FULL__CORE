"""
JARVIS Listener — Microphone to text using SpeechRecognition.
Graceful degradation: if SpeechRecognition not installed, returns None.
"""

import threading
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_sr_available = False
_recognizer = None
_is_sleeping = False

def set_sleep_mode(state: bool):
    """Enable or disable polling the microphone."""
    global _is_sleeping
    _is_sleeping = state

try:
    import speech_recognition as sr
    _sr_available = True
    _recognizer = sr.Recognizer()
except ImportError:
    print("⚠️  SpeechRecognition not installed. Voice input disabled (text-only mode).")

_ambient_adjusted = False


def _adjust_ambient():
    """Adjust for ambient noise on first listen."""
    global _ambient_adjusted
    if _ambient_adjusted or not _sr_available:
        return
    try:
        with sr.Microphone() as source:
            print("🎤 Calibrating microphone for ambient noise...")
            _recognizer.adjust_for_ambient_noise(source, duration=1)
            _ambient_adjusted = True
            print("🎤 Microphone calibrated.")
    except Exception as e:
        print(f"⚠️  Microphone calibration error: {e}")
        _ambient_adjusted = True  # Don't retry


def listen_once(timeout=5, phrase_limit=15):
    """
    Listen for a single phrase from the microphone.
    
    Args:
        timeout: Seconds to wait for speech to start
        phrase_limit: Max seconds of speech to capture
    
    Returns:
        str | None: Recognized text, or None on failure/timeout
    """
    if not _sr_available:
        return None

    if _is_sleeping:
        # Don't poll mic so CPU idles, don't print logs so terminal stays clean
        time.sleep(1)
        return None

    _adjust_ambient()

    try:
        with sr.Microphone() as source:
            print("🎤 Listening...")
            audio = _recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_limit
            )

        print("🎤 Processing speech...")
        text = _recognizer.recognize_google(audio)
        print(f"🎤 Heard: {text}")
        return text

    except sr.WaitTimeoutError:
        print("🎤 No speech detected (timeout).")
        return None
    except sr.UnknownValueError:
        print("🎤 Could not understand audio.")
        return None
    except sr.RequestError as e:
        print(f"⚠️  Speech recognition service error: {e}")
        return None
    except Exception as e:
        print(f"⚠️  Listener error: {e}")
        return None


def listen_continuous(callback_fn):
    """
    Continuously listen and call callback_fn with recognized text.
    Runs in a daemon thread.
    
    Args:
        callback_fn: Function to call with recognized text string
    """
    def _loop():
        while True:
            result = listen_once(timeout=5, phrase_limit=15)
            if result:
                try:
                    callback_fn(result)
                except Exception as e:
                    print(f"⚠️  Callback error: {e}")

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return t


def is_available():
    """Check if speech recognition is available."""
    return _sr_available
