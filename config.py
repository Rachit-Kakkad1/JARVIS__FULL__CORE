"""
JARVIS Configuration — All keys, paths, and user preferences.
"""

CONFIG = {
    # Identity
    "USER_NAME": "Sir",
    "JARVIS_NAME": "Jarvis",

    # Brain
    "BRAIN": "grok",                        # "grok" | "openai" | "claude"
    "GROK_API_KEY": "xai-YOUR_KEY_HERE",    # console.x.ai
    "GROK_MODEL": "grok-3-mini",            # grok-3-mini (fast) | grok-3
    "OPENAI_API_KEY": "",
    "MAX_HISTORY": 20,                      # messages kept in context

    # Voice
    "VOICE_OUTPUT": True,
    "VOICE_INPUT": True,
    "VOICE_SPEED": 160,                     # WPM
    "VOICE_VOLUME": 1.0,
    "WAKE_WORD": "hey jarvis",              # keyword to listen for
    "WAKE_WORD_ENGINE": "keyword",          # "keyword" (free) | "porcupine"

    # UI
    "UI_PORT": 5000,
    "UI_OPEN_BROWSER": True,               # auto-open on start

    # Apps (update paths for user's machine)
    "APP_PATHS": {
        "chrome":       r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "spotify":      r"%APPDATA%\Spotify\Spotify.exe",
        "vscode":       r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
        "notepad":      "notepad.exe",
        "calculator":   "calc.exe",
        "explorer":     "explorer.exe",
        "task manager": "taskmgr.exe",
        "discord":      r"%LOCALAPPDATA%\Discord\Update.exe --processStart Discord.exe",
        "whatsapp":     r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe",
        "vlc":          r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        "word":         r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
        "excel":        r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    },

    # Face Authentication
    "FACE_AUTH_ENABLED": True,              # Enable biometric face gate
    "FACE_AUTH_TOLERANCE": 0.35,             # Lower = stricter (0.3-0.45 recommended)
    "FACE_AUTH_DATA_DIR": "data/face_auth", # Where face encodings are stored

    # System
    "MONITOR_INTERVAL": 2,                  # seconds between system polls
    "DAILY_LIMIT": 100,                     # Grok free tier
    "SCREENSHOT_DIR": r"C:\Users\%USERNAME%\Pictures\Jarvis",
}
