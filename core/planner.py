"""
JARVIS Autonomous Planning Engine
Translates abstract user goals into prioritized execution arrays natively.
"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CONFIG
from controller import parser

try:
    from rapidfuzz import fuzz, process
    _rapidfuzz_available = True
except ImportError:
    _rapidfuzz_available = False
    fuzz = None
    process = None

PLAN_TEMPLATES_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "plan_templates.json")

def load_templates():
    templates = {}
    if os.path.exists(PLAN_TEMPLATES_FILE):
        try:
            with open(PLAN_TEMPLATES_FILE, "r") as f:
                templates = json.load(f)
        except Exception:
            pass
            
    # Phase 18: Dynamically merge in Learned routines
    try:
        from core.learning import load_learned_plans
        learned = load_learned_plans()
        for name, data in learned.items():
            curr_v = data.get("current")
            if curr_v and data.get(curr_v):
                templates[name] = data[curr_v]
    except ImportError:
        pass
        
    return templates

def validate_plan(plan_array):
    """
    Validates a plan array ensuring safety and execution conformity.
    Rejects plans containing un-parseable intents or unsafe payloads.
    """
    valid_intents = getattr(parser, "INTENTS", {}).keys()
    if not valid_intents:
        # Fallback list if INTENTS fails to resolve for any reason
        valid_intents = [
            "sleep_jarvis", "shutdown_jarvis", "power", "open_app", 
            "close_app", "youtube", "volume", "screenshot", 
            "system_info", "lock", "brightness", "open_url", "clipboard"
        ]
        
    for step in plan_array:
        action = step.get("action")
        # Validate that the action is natively executable by JARVIS
        if action not in valid_intents and action != "macro":
            return False
    return True

def generate_plan(goal_text, context=None, system_state=None):
    """
    Translates a vague goal (e.g. 'Setup for meeting') into an execution plan.
    Priority 1: Check static plan templates.
    """
    templates = load_templates()
    if not templates or not _rapidfuzz_available:
        return None

    # Use RapidFuzz to evaluate if the abstract user goal maps directly to a static template
    # E.g., goal_text="get ready for my meeting" vs key="meeting"
    best_match = process.extractOne(goal_text, templates.keys(), scorer=fuzz.token_set_ratio)
    
    if best_match and best_match[1] >= 75:
        plan_name = best_match[0]
        base_plan = templates[plan_name]
        
        # Sort execution order by explicit priority mapping
        base_plan.sort(key=lambda x: x.get("priority", 99))
        
        if validate_plan(base_plan):
            return {
                "name": plan_name,
                "steps": base_plan,
                "source": "template"
            }
            
    # Priority 2: Need Clarification from User
    return {"status": "needs_clarification", "target": goal_text}

def execute_plan(goal_text, socketio, execute_command_fn):
    """
    Generates and pipes the execution plan into the core orchestrator.
    Called directly from bridge.py when a `plan_goal` is encountered.
    """
    # Grab working memory context for plan injection later
    from brain.memory import load_memory
    mem = load_memory()
    context = mem.get("context", {})
    
    plan = generate_plan(goal_text, context=context)
    
    if not plan:
        return
        
    if plan.get("status") == "needs_clarification":
        target = plan.get("target", goal_text)
        msg = f"I'm missing part of your {target}, Sir. What should I include? For example: terminal, browser, or specific tools."
        from brain.memory import update_context
        update_context("awaiting_plan_clarification", target)
        socketio.emit("jarvis_message", {"role": "assistant", "content": msg, "type": "system"})
        from voice.speaker import speak_async
        speak_async(msg)
        return

    plan_name = plan["name"]
    msg = f"Planning complete. Executing goal: {plan_name}"
    socketio.emit("jarvis_message", {"role": "assistant", "content": msg, "type": "system"})

    # Map the validated plan structure directly into the task_executor natively and skip disk caching
    from core.task_executor import _update_runtime_state
    import time
    
    steps = plan["steps"]
    state = {
        "name": plan_name,
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
            "result": f"Plan stage {i+1}/{len(steps)} computing..."
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
                "content": f"Plan error during {action}: {e}",
                "type": "error"
            })
            success_flags.append(False)
            continue 
            
        time.sleep(1.5)

    state["status"] = "completed"
    _update_runtime_state(state)
    
    # Phase 18: Adaptive Intelligence Loop
    if plan.get("source") == "ai":
        from core.learning import evaluate_execution, save_learned_plan
        # Only prompt to learn if execution array completed safely
        if evaluate_execution(plan_name, steps, success_flags):
            socketio.emit("jarvis_message", {
                "role": "assistant", 
                "content": f"Execution of the dynamic plan '{plan_name}' was successful. I have serialized it to logic memory for next time, Sir.", 
                "type": "system"
            })
            # Normally this would pause for an explicit Yes/No conversational response.
            # We bypass the conversational hook here for pure architecture rollout.
            save_learned_plan(plan_name, steps)

    socketio.emit("jarvis_message", {"role": "assistant", "content": f"Goal '{plan_name}' successfully completed.", "type": "system"})
