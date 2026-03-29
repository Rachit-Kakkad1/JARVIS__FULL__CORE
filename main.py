"""
JARVIS — Main entry point. Starts everything.
"""

import sys
import os
import time
import webbrowser
import threading

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import CONFIG


def print_banner():
    """Print the JARVIS startup banner."""
    banner = """
    ╔══════════════════════════════════════╗
    ║   J.A.R.V.I.S.  —  PHASE 3 ONLINE  ║
    ╚══════════════════════════════════════╝
    """
    print(banner)
    print(f"    Brain: {CONFIG['BRAIN'].upper()} | Model: {CONFIG['GROK_MODEL']}")
    print(f"    Voice Output: {'ON' if CONFIG['VOICE_OUTPUT'] else 'OFF'}")
    print(f"    Voice Input: {'ON' if CONFIG['VOICE_INPUT'] else 'OFF'}")
    print(f"    UI Port: {CONFIG['UI_PORT']}")
    print()


def main():
    """Orchestrate JARVIS startup."""
    print_banner()

    # ── Step 1: Ensure data directories exist ─────────────────────
    os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), "assets"), exist_ok=True)

    # ── Step 2: Start system monitor ──────────────────────────────
    print("📊 Starting system monitor...")
    from controller.monitor import monitor
    # We'll pass socketio after server starts

    # ── Step 3: Import and start the UI server ────────────────────
    print("🌐 Starting UI server...")
    from ui.server import app, socketio, run_server

    # Start monitor with socketio reference
    monitor.start(socketio)

    # Start Flask-SocketIO in a background thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # ── Step 4: Auto-open browser ─────────────────────────────────
    if CONFIG.get("UI_OPEN_BROWSER", True):
        time.sleep(2)
        url = f"http://localhost:{CONFIG['UI_PORT']}"
        print(f"🌐 Opening browser: {url}")
        webbrowser.open(url)

    # ── Step 5: Start voice system ────────────────────────────────
    if CONFIG.get("VOICE_INPUT", True):
        try:
            from voice.speaker import speak, speak_async
            from voice.listener import listen_once, is_available as listener_available
            from voice.wakeword import listen_for_wake
            from ui.bridge import on_user_input

            if listener_available():
                print("🎧 Starting wake word listener...")

                def on_wake():
                    """Handle wake word detection."""
                    speak("Yes, Sir?")
                    text = listen_once(timeout=8, phrase_limit=15)
                    if text:
                        print(f"\n👤 {CONFIG['USER_NAME']}: {text}")
                        on_user_input(text, socketio)
                    else:
                        speak("I didn't catch that, Sir.")

                listen_for_wake(CONFIG.get("WAKE_WORD", "hey jarvis"), on_wake)
                print(f"🎧 Say '{CONFIG['WAKE_WORD']}' to activate.")
            else:
                print("⚠️  Voice input not available. Use the UI for text input.")
        except Exception as e:
            print(f"⚠️  Voice system error: {e}. Continuing without voice.")

    # ── Step 6: Startup greeting ──────────────────────────────────
    try:
        from voice.speaker import speak_async
        speak_async(f"All systems online and ready, {CONFIG['USER_NAME']}.")
    except Exception:
        print(f"\n🤖 JARVIS: All systems online and ready, {CONFIG['USER_NAME']}.\n")

    # ── Step 7: Keep main thread alive ────────────────────────────
    print("\n✅ JARVIS is fully operational. Press Ctrl+C to shut down.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n")
        try:
            from voice.speaker import speak
            speak(f"Shutting down. Goodbye, {CONFIG['USER_NAME']}.")
        except Exception:
            print(f"🤖 JARVIS: Shutting down. Goodbye, {CONFIG['USER_NAME']}.")
        monitor.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()
