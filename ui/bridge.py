"""
JARVIS UI Bridge — Connects brain ↔ voice ↔ controller ↔ socketio.
Central routing layer for all user interactions.
"""

import sys
import os
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import CONFIG
from brain import grok, memory, usage
from voice.speaker import speak_async
from voice.listener import set_sleep_mode
from controller import parser, apps, browser, system, files, monitor as monitor_module

import re
import time as _time
import logging

logger = logging.getLogger(__name__)

# ── Sleep State ──────────────────────────────────────────────────────
_sleep_state = {
    "sleeping": False,
    "awaiting_duration": False,
    "wake_time": None,
    "timer_thread": None,
    "socketio_ref": None,
}


def on_user_input(text, socketio):
    """
    Process user input: parse for commands first, fall through to Grok brain.
    
    Args:
        text: User's text input
        socketio: Flask-SocketIO instance for emitting events
    """
    if not text or not text.strip():
        return

    text = text.strip()

    # ── Sleep: awaiting duration input ────────────────────────────
    if _sleep_state["awaiting_duration"]:
        _handle_sleep_duration(text, socketio)
        return

    # ── Sleep: block all input while sleeping ─────────────────────
    if _sleep_state["sleeping"]:
        remaining = 0
        if _sleep_state["wake_time"]:
            remaining = max(0, int((_sleep_state["wake_time"] - _time.time()) / 60))
        # Allow "wake up" to cancel sleep early
        t_lower = text.lower().strip()
        if any(w in t_lower for w in ["wake up", "wake yourself", "wake jarvis", "i'm back"]):
            _wake_jarvis(socketio)
            return
        msg = f"I'm currently sleeping, {CONFIG['USER_NAME']}. I'll wake up in {remaining} minute{'s' if remaining != 1 else ''}. Say 'wake up' to wake me early."
        socketio.emit("jarvis_message", {
            "role": "assistant",
            "content": msg,
            "type": "system"
        })
        return

    # Emit typing indicator
    socketio.emit("jarvis_typing", True)

    # Check for Conversational Plan Clarification Context
    from brain.memory import get_context, update_context
    pending_goal = get_context("awaiting_plan_clarification")
    if pending_goal:
        # Clear the lock to prevent looping
        update_context("awaiting_plan_clarification", None)
        
        items = [i.strip() for i in text.replace(" and ", ",").split(",") if i.strip()]
        if not items:
            socketio.emit("jarvis_message", {"role": "assistant", "content": "I didn't catch that, Sir. Cancelling plan preparation.", "type": "system"})
            speak_async("I didn't catch that, Sir. Cancelling plan preparation.")
            return

        steps = []
        for item in items:
            # Force target into open_app mapping natively to ensure conformity
            parsed = parser.parse(f"open {item}")
            if parsed and "error_response" not in parsed:
                parsed["priority"] = len(steps) + 1
                steps.append(parsed)
            else:
                # Silent failure fallback mapping
                steps.append({"action": "open_app", "target": item.lower(), "priority": len(steps) + 1})

        from core.learning import save_learned_plan
        save_learned_plan(pending_goal, steps)
        
        confirm_msg = "Understood. Executing your setup now, Sir."
        socketio.emit("jarvis_message", {"role": "assistant", "content": confirm_msg, "type": "system"})
        speak_async(confirm_msg)
        
        from core.planner import execute_plan
        def _execute_new():
            execute_plan(pending_goal, socketio, execute_command)
        import threading
        threading.Thread(target=_execute_new, daemon=True).start()
        return

    try:
        # Step 1: Try to parse as a local command
        cmd = parser.parse(text)

        if cmd:
            # 1. Error Response Check (e.g. missing target)
            error_response = cmd.get("error_response")
            if error_response:
                socketio.emit("jarvis_message", {
                    "role": "assistant",
                    "content": error_response,
                    "type": "system"
                })
                speak_async(error_response)
                return

            confidence = cmd.get("confidence", 100)
            
            # Phase 17: Goal Routing & Confidence Split Edge Case
            if cmd["action"] == "plan_goal":
                if confidence >= 85:
                    from core.planner import execute_plan
                    def _run_planner():
                        execute_plan(text, socketio, execute_command)
                    threading.Thread(target=_run_planner, daemon=True).start()
                    return
                else:
                    # Gating prevents overlap risk with conversational queries ("how do i prepare steak?")
                    cmd = None

        if cmd:
            # 2. Confidence Logging
            confidence = cmd.get("confidence", 100)
            if 70 <= confidence < 85:
                logger.info("Low confidence intent match (%d%%): %s", confidence, cmd["action"])
                print(f"⚠️ Low confidence match ({confidence}%): Executing '{cmd['action']}'")

            # 3. Context Injection (Semantic / Working Memory)
            target_word = str(cmd.get("target", "")).lower()
            if any(w in target_word for w in ["that", "last", "it"]):
                from brain.memory import get_context
                if cmd["action"] == "youtube":
                    last_song = get_context("last_song")
                    if last_song: cmd["target"] = last_song
                elif cmd["action"] in ["open_app", "close_app"]:
                    last_app = get_context("last_app")
                    if last_app: cmd["target"] = last_app
                elif cmd["action"] == "open_url":
                    last_url = get_context("last_url")
                    if last_url: cmd["target"] = last_url

            # 4. Context Saving (Update Working Memory)
            from brain.memory import update_context
            if cmd["action"] == "youtube" and cmd.get("target"):
                update_context("last_song", cmd.get("target"))
            elif cmd["action"] in ["open_app", "close_app"] and cmd.get("target"):
                update_context("last_app", cmd.get("target"))
            elif cmd["action"] == "open_url" and cmd.get("target"):
                update_context("last_url", cmd.get("target"))

            if cmd["action"] == "macro":
                from core.task_executor import execute_macro
                # Run the macro loop in a background thread so it doesn't block the UI server
                def _run_macro():
                    execute_macro(cmd["target"], execute_command, socketio)
                threading.Thread(target=_run_macro, daemon=True).start()
                return

            # Handle actions that need socketio directly
            if cmd["action"] == "sleep_jarvis":
                _sleep_state["awaiting_duration"] = True
                _sleep_state["socketio_ref"] = socketio
                msg = f"How many minutes should I sleep, {CONFIG['USER_NAME']}?"
                socketio.emit("jarvis_message", {
                    "role": "assistant",
                    "content": msg,
                    "type": "command"
                })
                speak_async(msg)
                return

            if cmd["action"] == "shutdown_jarvis":
                farewell = f"Shutting down all systems. Goodbye, {CONFIG['USER_NAME']}."
                socketio.emit("jarvis_message", {
                    "role": "assistant",
                    "content": farewell,
                    "type": "command"
                })
                speak_async(farewell)
                def _delayed_exit():
                    import time
                    time.sleep(3)
                    os._exit(0)
                threading.Thread(target=_delayed_exit, daemon=True).start()
                return

            # Execute local command — no API quota burned
            result = execute_command(cmd)
            socketio.emit("jarvis_message", {
                "role": "assistant",
                "content": result,
                "type": "command"
            })
            socketio.emit("activity", {
                "action": cmd["action"],
                "target": cmd.get("target", ""),
                "result": result
            })
            speak_async(result)
        else:
            # Step 2: Send to Grok brain
            if not usage.check():
                limit_msg = f"Daily API limit reached, {CONFIG['USER_NAME']}. Local commands still work."
                socketio.emit("jarvis_message", {
                    "role": "assistant",
                    "content": limit_msg,
                    "type": "system"
                })
                speak_async(limit_msg)
                return

            # Load memory
            mem = memory.load_memory()

            # Check for facts in user message
            new_facts = memory.extract_facts(text)

            # Get AI response
            response = grok.think(text, mem["history"], mem["facts"])

            # Increment usage counter
            usage.increment()

            # Save exchange to memory
            memory.add_exchange(mem, text, response)

            # Add any new facts
            if new_facts:
                memory.add_facts(mem, new_facts)
                memory.save_memory(mem)

            # Emit response
            socketio.emit("jarvis_message", {
                "role": "assistant",
                "content": response,
                "type": "ai"
            })
            speak_async(response)

    except Exception as e:
        error_msg = f"I encountered an error, {CONFIG['USER_NAME']}: {str(e)}"
        socketio.emit("jarvis_message", {
            "role": "assistant",
            "content": error_msg,
            "type": "error"
        })
        speak_async(error_msg)

    finally:
        socketio.emit("jarvis_typing", False)


def execute_command(cmd):
    """
    Route a parsed command to the appropriate controller function.
    
    Args:
        cmd: Dict with keys {action, target, args}
    
    Returns:
        str: Result message from the controller
    """
    action = cmd.get("action", "")
    target = cmd.get("target", "")
    args = cmd.get("args", {})

    try:
        if action == "open_app":
            return apps.open_app(target)

        elif action == "close_app":
            return apps.close_app(target)

        elif action == "youtube":
            if target:
                return browser.play_youtube(target)
            else:
                return browser.open_url("https://www.youtube.com")

        elif action == "open_url":
            return browser.open_url(target)

        elif action == "volume":
            if "level" in args:
                return system.set_volume(args["level"])
            direction = args.get("dir", "")
            if direction == "up":
                return system.volume_up()
            elif direction == "down":
                return system.volume_down()
            elif direction == "mute":
                return system.mute()
            elif direction == "unmute":
                return system.unmute()
            return f"Volume command not recognized, {CONFIG['USER_NAME']}."

        elif action == "screenshot":
            save_dir = os.path.expandvars(CONFIG.get("SCREENSHOT_DIR", "."))
            return system.screenshot(save_dir)

        elif action == "system_info":
            mon = monitor_module.monitor
            return mon.get_summary_text()

        elif action == "lock":
            return system.lock_screen()

        elif action == "power":
            power_cmd = args.get("cmd", "")
            return system.shutdown(power_cmd)

        elif action == "brightness":
            if "level" in args:
                return system.set_brightness(args["level"])
            direction = args.get("dir", "")
            if direction == "up":
                return system.brightness_up()
            elif direction == "down":
                return system.brightness_down()
            return f"Brightness command not recognized, {CONFIG['USER_NAME']}."

        elif action == "open_file":
            return files.open_file(target)

        elif action == "clipboard":
            op = args.get("op", "read")
            if op == "read":
                try:
                    import pyperclip
                    content = pyperclip.paste()
                    return f"Clipboard contents: {content[:500]}"
                except ImportError:
                    return f"Clipboard access requires pyperclip, {CONFIG['USER_NAME']}."
            return f"Clipboard operation '{op}' not supported."

        else:
            return f"Unknown command action: {action}"

    except Exception as e:
        return f"Error executing {action}: {str(e)}"


def handle_quick_action(action_name, socketio):
    """
    Handle a quick action button press from the UI.
    
    Args:
        action_name: Name of the quick action
        socketio: Flask-SocketIO instance
    """
    action_map = {
        "youtube": {"action": "open_url", "target": "https://www.youtube.com", "args": {}},
        "spotify": {"action": "open_app", "target": "spotify", "args": {}},
        "chrome": {"action": "open_app", "target": "chrome", "args": {}},
        "vscode": {"action": "open_app", "target": "vscode", "args": {}},
        "capture": {"action": "screenshot", "target": None, "args": {}},
        "sysinfo": {"action": "system_info", "target": None, "args": {}},
    }

    cmd = action_map.get(action_name.lower())
    if cmd:
        result = execute_command(cmd)
        socketio.emit("jarvis_message", {
            "role": "assistant",
            "content": result,
            "type": "command"
        })
        socketio.emit("activity", {
            "action": action_name,
            "target": "",
            "result": result
        })
        speak_async(result)
    else:
        msg = f"Unknown quick action: {action_name}"
        socketio.emit("jarvis_message", {
            "role": "assistant",
            "content": msg,
            "type": "error"
        })


# ── Sleep Mode Helpers ───────────────────────────────────────────────

def _handle_sleep_duration(text, socketio):
    """Parse the user's duration reply and put Jarvis to sleep."""
    _sleep_state["awaiting_duration"] = False

    # Extract sleep duration explicitly measuring by hours, minutes, or target time.
    text_lower = text.lower()
    minutes = None
    
    # 1. Parse specific target time like "1:30 pm"
    time_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", text_lower)
    if time_match:
        from datetime import datetime, timedelta
        now = datetime.now()
        hour = int(time_match.group(1))
        minute_part = int(time_match.group(2)) if time_match.group(2) else 0
        ampm = time_match.group(3)
        
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
            
        try:
            target = now.replace(hour=hour, minute=minute_part, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            minutes = int((target - now).total_seconds() / 60)
        except ValueError:
            minutes = None

    if minutes is None:
        # 2. Parse explicit hours like "2 hours"
        hr_match = re.search(r"(\d+)\s*hour", text_lower)
        if hr_match:
            minutes = int(hr_match.group(1)) * 60
        else:
            # 3. Fallback to basic minutes match
            min_match = re.search(r"(\d+)", text)
            if min_match:
                minutes = int(min_match.group(1))

    if not minutes:
        msg = f"I didn't catch the duration, {CONFIG['USER_NAME']}. Sleep cancelled."
        socketio.emit("jarvis_message", {
            "role": "assistant",
            "content": msg,
            "type": "system"
        })
        speak_async(msg)
        return

    if minutes <= 0 or minutes > 1440:
        msg = f"That doesn't seem right, {CONFIG['USER_NAME']}. Please give 1 to 1440 minutes. Sleep cancelled."
        socketio.emit("jarvis_message", {
            "role": "assistant",
            "content": msg,
            "type": "system"
        })
        speak_async(msg)
        return

    # Activate sleep
    _sleep_state["sleeping"] = True
    _sleep_state["wake_time"] = _time.time() + (minutes * 60)
    _sleep_state["socketio_ref"] = socketio
    set_sleep_mode(True)

    msg = f"Going to sleep for {minutes} minute{'s' if minutes != 1 else ''}, {CONFIG['USER_NAME']}. Say 'wake up' to wake me early. Good night."
    socketio.emit("jarvis_message", {
        "role": "assistant",
        "content": msg,
        "type": "system"
    })
    socketio.emit("jarvis_sleep", {"sleeping": True, "minutes": minutes})
    speak_async(msg)

    logger.info("Jarvis entering sleep mode for %d minutes", minutes)
    print(f"\n😴 JARVIS sleeping for {minutes} minutes...")

    # Start wake timer
    def _sleep_timer():
        _time.sleep(minutes * 60)
        if _sleep_state["sleeping"]:
            _wake_jarvis(socketio)

    t = threading.Thread(target=_sleep_timer, daemon=True)
    t.start()
    _sleep_state["timer_thread"] = t


def _wake_jarvis(socketio):
    """Wake Jarvis from sleep mode."""
    _sleep_state["sleeping"] = False
    _sleep_state["awaiting_duration"] = False
    _sleep_state["wake_time"] = None
    _sleep_state["timer_thread"] = None
    set_sleep_mode(False)

    msg = f"I'm back online and fully operational, {CONFIG['USER_NAME']}."
    socketio.emit("jarvis_message", {
        "role": "assistant",
        "content": msg,
        "type": "system"
    })
    socketio.emit("jarvis_sleep", {"sleeping": False})
    speak_async(msg)

    logger.info("Jarvis waking up from sleep mode")
    print("\n☀️ JARVIS is awake!")

