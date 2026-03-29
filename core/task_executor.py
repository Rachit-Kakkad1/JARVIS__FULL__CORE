"""
JARVIS Task Execution Engine
Parses and executes multi-step macros / goals.
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CONFIG
from voice.speaker import speak_async

MACRO_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "custom_commands.json")
RUNTIME_STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "memory", "runtime_state.json")

def _update_runtime_state(state_dict):
    """Write current execution state to memory."""
    os.makedirs(os.path.dirname(RUNTIME_STATE_FILE), exist_ok=True)
    try:
        with open(RUNTIME_STATE_FILE, "w") as f:
            json.dump(state_dict, f, indent=4)
    except Exception:
        pass

def load_macros():
    """Load macros from custom_commands.json, initializing if necessary."""
    if not os.path.exists(MACRO_FILE):
        os.makedirs(os.path.dirname(MACRO_FILE), exist_ok=True)
        default_macros = {
            "dev mode": [
                {"action": "open_app", "target": "vscode"},
                {"action": "open_url", "target": "https://github.com"}
            ],
            "relax": [
                {"action": "youtube", "target": "lofi hip hop radio"},
                {"action": "brightness", "target": None, "args": {"level": 30}}
            ]
        }
        with open(MACRO_FILE, 'w') as f:
            json.dump(default_macros, f, indent=4)
        return default_macros
        
    with open(MACRO_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def execute_macro(macro_name, execute_command_fn, socketio):
    """
    Executes a multi-step macro iteratively.
    Args:
        macro_name: Name of the macro (e.g., "dev mode")
        execute_command_fn: Reference to `bridge.execute_command` to avoid circular imports.
        socketio: SocketIO reference for pushing UI updates.
    """
    macros = load_macros()
    steps = macros.get(macro_name)
    if not steps:
        msg = f"I don't have a macro known as {macro_name}, sir."
        speak_async(msg)
        return msg

    msg = f"Initializing macro sequence: {macro_name}"
    speak_async("Right away, sir. " + msg)
    socketio.emit("jarvis_message", {"role": "assistant", "content": msg, "type": "system"})

    state = {
        "name": macro_name,
        "step": 0,
        "status": "running",
        "total_steps": len(steps),
        "steps": steps
    }
    _update_runtime_state(state)

    success_flags = []

    for i, step in enumerate(steps):
        state["step"] = i + 1
        _update_runtime_state(state)
        
        action = step.get("action")
        target = step.get("target")
        args = step.get("args", {})
        
        cmd = {
            "action": action,
            "target": target,
            "args": args
        }
        
        socketio.emit("activity", {
            "action": action,
            "target": target if target else "",
            "result": f"Macro step {i+1}/{len(steps)} executing..."
        })
        
        try:
            result = execute_command_fn(cmd)
            socketio.emit("jarvis_message", {
                "role": "assistant",
                "content": result,
                "type": "command"
            })
            success_flags.append(True)
        except Exception as e:
            socketio.emit("jarvis_message", {
                "role": "assistant",
                "content": f"Macro error during {action}: {e}",
                "type": "error"
            })
            # Resilience: log error but continue execution
            print(f"⚠️ Step failed ({action}): {e}")
            continue 
            
        time.sleep(1.5)

    state["status"] = "completed"
    _update_runtime_state(state)

    success_count = sum(1 for f in success_flags if f)
    fail_count = len(success_flags) - success_count
    
    if fail_count == 0:
        finish_msg = "Goal successfully completed, Sir."
    elif success_count > 0:
        finish_msg = "Goal partially completed, Sir."
    else:
        finish_msg = "I was unable to complete the task, Sir."
        
    socketio.emit("jarvis_message", {"role": "assistant", "content": finish_msg, "type": "system"})
    speak_async(finish_msg)
    
    return finish_msg, success_flags
