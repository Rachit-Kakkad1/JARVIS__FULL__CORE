"""
JARVIS Brain — Grok API integration using OpenAI-compatible SDK.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openai import OpenAI
from config import CONFIG
from brain.persona import get_system_prompt, get_facts_block


def _get_client():
    """Create an OpenAI client pointed at the Grok API."""
    return OpenAI(
        api_key=CONFIG["GROK_API_KEY"],
        base_url="https://api.x.ai/v1",
    )


def think(user_message, history=None, facts=None):
    """
    Send a message to Grok and get a response.
    
    Args:
        user_message: The user's text input
        history: List of {"role": str, "content": str} dicts
        facts: List of known facts about the user
    
    Returns:
        str: Jarvis's response text
    """
    if history is None:
        history = []
    if facts is None:
        facts = []

    try:
        client = _get_client()

        # Build system message with facts
        system_content = get_system_prompt()
        facts_block = get_facts_block(facts)
        if facts_block:
            system_content += "\n" + facts_block

        # Build messages array
        messages = [{"role": "system", "content": system_content}]

        # Add conversation history
        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        # Call Grok API
        response = client.chat.completions.create(
            model=CONFIG["GROK_MODEL"],
            messages=messages,
            max_tokens=800,
            temperature=0.75,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        error_msg = str(e)
        if "api_key" in error_msg.lower() or "auth" in error_msg.lower():
            return f"I'm experiencing an authentication issue with my brain, {CONFIG['USER_NAME']}. Please verify the API key in config.py."
        return f"I encountered an error processing that, {CONFIG['USER_NAME']}: {error_msg}"
