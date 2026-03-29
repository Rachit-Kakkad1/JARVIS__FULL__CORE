"""
JARVIS UI Server — Flask + Flask-SocketIO backend.
Serves the React app and handles all WebSocket communication.
Includes biometric face authentication gate.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, send_from_directory, jsonify, request
from flask_socketio import SocketIO
from flask_cors import CORS

from config import CONFIG
from brain import usage

from ui.bridge import on_user_input, handle_quick_action

# Path to React build output
REACT_BUILD = os.path.join(os.path.dirname(__file__), "react-app", "dist")

# Create Flask app
app = Flask(__name__, static_folder=REACT_BUILD, static_url_path="")
CORS(app)

# Create SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ── Session authentication state ────────────────────────────────────
_authenticated_sessions = set()


def is_session_authenticated(sid=None):
    """Check if the current session is authenticated."""
    if not CONFIG.get("FACE_AUTH_ENABLED", True):
        return True  # Auth disabled in config
    return sid in _authenticated_sessions


# ── HTTP ROUTES ──────────────────────────────────────────────────────

@app.route("/")
def serve_index():
    """Serve the React app."""
    return send_from_directory(REACT_BUILD, "index.html")


@app.route("/api/status")
def api_status():
    """Return system status."""
    return jsonify({
        "status": "online",
        "phase": 3,
        "brain": CONFIG.get("BRAIN", "grok"),
        "usage_remaining": usage.remaining(),
        "usage_count": usage.get_count(),
        "daily_limit": CONFIG.get("DAILY_LIMIT", 100),
    })


# ── FACE AUTH API ────────────────────────────────────────────────────

@app.route("/api/face-auth/status")
def face_auth_status():
    """Check if face auth is enabled and if a face is enrolled."""
    if not CONFIG.get("FACE_AUTH_ENABLED", True):
        return jsonify({
            "enabled": False,
            "enrolled": False,
            "authenticated": True,
            "message": "Face authentication is disabled.",
        })

    try:
        from security.face_auth import get_authenticator
        auth = get_authenticator()
        return jsonify({
            "enabled": True,
            "enrolled": auth.has_enrolled_face(),
            "authenticated": False,
            "engine": auth.engine,
            "message": "Ready for authentication." if auth.has_enrolled_face()
                       else "No face enrolled. Enrollment required.",
        })
    except Exception as e:
        return jsonify({
            "enabled": True,
            "enrolled": False,
            "authenticated": False,
            "error": str(e),
            "message": f"Face auth error: {e}",
        }), 500


@app.route("/api/face-auth/enroll", methods=["POST"])
def face_auth_enroll():
    """Enroll the authorized user's face."""
    try:
        from security.face_auth import get_authenticator
        auth = get_authenticator()
        result = auth.enroll()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Enrollment error: {e}",
        }), 500


@app.route("/api/face-auth/verify", methods=["POST"])
def face_auth_verify():
    """Verify the current face against the enrolled face."""
    try:
        from security.face_auth import get_authenticator
        auth = get_authenticator()
        result = auth.verify()

        # If verified, mark ALL connected sessions as authenticated
        if result.get("authenticated"):
            for sid in list(_authenticated_sessions):
                pass  # Keep existing
            # We'll authenticate via socket event instead
            pass

        return jsonify(result)
    except Exception as e:
        return jsonify({
            "authenticated": False,
            "confidence": 0.0,
            "message": f"Verification error: {e}",
        }), 500


@app.errorhandler(404)
def not_found(e):
    """Serve React app for all unmatched routes (SPA support)."""
    index_path = os.path.join(REACT_BUILD, "index.html")
    if os.path.exists(index_path):
        return send_from_directory(REACT_BUILD, "index.html")
    return jsonify({"error": "Not found"}), 404


# ── SOCKET EVENTS (client → server) ─────────────────────────────────

@socketio.on("connect")
def handle_connect():
    """Handle client connection."""
    print("🔌 UI client connected.")
    sid = request.sid

    if not CONFIG.get("FACE_AUTH_ENABLED", True):
        _authenticated_sessions.add(sid)
        socketio.emit("jarvis_message", {
            "role": "assistant",
            "content": f"Systems online and ready, {CONFIG['USER_NAME']}. How may I assist you?",
            "type": "system"
        }, to=sid)
    else:
        # Don't send welcome until authenticated
        socketio.emit("auth_required", {
            "message": "Biometric authentication required."
        }, to=sid)


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection."""
    sid = request.sid
    _authenticated_sessions.discard(sid)
    print("🔌 UI client disconnected.")


@socketio.on("face_auth_success")
def handle_face_auth_success():
    """Mark this session as authenticated after face verification."""
    sid = request.sid
    _authenticated_sessions.add(sid)
    print(f"🔐 Session {sid[:8]}... authenticated via face scan.")
    socketio.emit("jarvis_message", {
        "role": "assistant",
        "content": f"Identity confirmed. Welcome back, {CONFIG['USER_NAME']}. All systems at your disposal.",
        "type": "system"
    }, to=sid)


@socketio.on("user_message")
def handle_user_message(data):
    """Handle incoming user message from the chat input."""
    sid = request.sid
    if not is_session_authenticated(sid):
        socketio.emit("jarvis_message", {
            "role": "assistant",
            "content": "⚠️ Authentication required. Please complete face verification first.",
            "type": "error"
        }, to=sid)
        return

    text = data if isinstance(data, str) else data.get("text", "")
    if text:
        print(f"\n👤 {CONFIG['USER_NAME']}: {text}")
        on_user_input(text, socketio)


@socketio.on("quick_action")
def handle_quick_action_event(data):
    """Handle quick action button press from UI."""
    sid = request.sid
    if not is_session_authenticated(sid):
        return

    from ui.bridge import handle_quick_action as do_quick_action
    action = data if isinstance(data, str) else data.get("action", "")
    if action:
        print(f"\n⚡ Quick action: {action}")
        do_quick_action(action, socketio)


@socketio.on("voice_toggle")
def handle_voice_toggle(data):
    """Toggle voice listening on/off."""
    enabled = data if isinstance(data, bool) else data.get("enabled", False)
    print(f"🎤 Voice {'enabled' if enabled else 'disabled'}.")


def get_app():
    """Return the Flask app and SocketIO instances."""
    return app, socketio


def run_server():
    """Start the Flask-SocketIO server."""
    port = CONFIG.get("UI_PORT", 5000)
    print(f"🌐 Starting JARVIS UI server on http://localhost:{port}")
    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False,
        allow_unsafe_werkzeug=True,
    )

