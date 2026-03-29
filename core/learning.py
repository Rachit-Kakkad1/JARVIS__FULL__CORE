"""
JARVIS Adaptive Intelligence — Learning Engine
Tracks execution success of unknown plans and manages versioned serialization.
"""

import os
import json

LEARNED_PLANS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "learned_plans.json")

def load_learned_plans():
    """Fetch previously auto-learned routines from disk."""
    if not os.path.exists(LEARNED_PLANS_FILE):
        return {}
    try:
        with open(LEARNED_PLANS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def get_learned_plan(plan_name):
    """Retrieve the 'current' version of a learned plan seamlessly."""
    plans = load_learned_plans()
    plan_data = plans.get(plan_name)
    if not plan_data:
        return None
    curr_version = plan_data.get("current")
    return plan_data.get(curr_version)

def evaluate_execution(plan_name, steps, success_flags):
    """
    Determines if a dynamically generated plan executed safely enough to be learned.
    Returns True if >80% of module steps succeeded.
    """
    if not steps or not success_flags:
        return False
    
    failures = sum(1 for flag in success_flags if not flag)
    success_rate = (len(steps) - failures) / len(steps)
    
    return success_rate >= 0.8  # Threshold for learning

def save_learned_plan(plan_name, steps):
    """
    Saves a successful workflow into persistence.
    Uses version control (v1, v2) to prevent corruption from successive runs.
    """
    data = load_learned_plans()
    
    if plan_name not in data:
        # Brand new observed routine
        data[plan_name] = {"current": "v1", "v1": steps}
    else:
        # Existing routine evolved, save new version
        existing = data[plan_name]
        versions = [k for k in existing.keys() if k.startswith("v")]
        next_v = f"v{len(versions) + 1}"
        existing[next_v] = steps
        existing["current"] = next_v
        
    os.makedirs(os.path.dirname(LEARNED_PLANS_FILE), exist_ok=True)
    with open(LEARNED_PLANS_FILE, "w") as f:
        json.dump(data, f, indent=4)
