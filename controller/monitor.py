"""
JARVIS System Monitor — Real-time CPU, RAM, disk, temp, network tracking.
Singleton service that polls every CONFIG["MONITOR_INTERVAL"] seconds.
Runs in its own background thread. Always read from get_snapshot().
"""

import time
import threading
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CONFIG

try:
    import psutil
    _psutil_available = True
except ImportError:
    _psutil_available = False
    print("⚠️  psutil not installed. System monitoring disabled.")


class MonitorService:
    """Background service that polls system stats."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._data = {}
        self._data_lock = threading.Lock()
        self._running = False
        self._thread = None
        self._socketio = None
        self._start_time = time.time()  # Track JARVIS process start time

    def start(self, socketio=None):
        """Start the monitoring thread."""
        if self._running:
            return
        self._socketio = socketio
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        print("📊 System monitor started.")

    def stop(self):
        """Stop the monitoring thread."""
        self._running = False

    def _poll_loop(self):
        """Main polling loop — runs in background thread."""
        while self._running:
            try:
                self._update()
                # Emit to UI via SocketIO
                if self._socketio:
                    self._socketio.emit("system_stats", self._data)
            except Exception as e:
                print(f"⚠️  Monitor poll error: {e}")
            time.sleep(CONFIG.get("MONITOR_INTERVAL", 2))

    def _update(self):
        """Collect all system metrics."""
        if not _psutil_available:
            return

        try:
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            net = psutil.net_io_counters()
            boot_time = psutil.boot_time()

            # Temperature (may not be available on all systems)
            temp = None
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        if entries:
                            temp = entries[0].current
                            break
            except (AttributeError, Exception):
                pass

            with self._data_lock:
                self._data = {
                    "cpu_percent": cpu,
                    "ram_percent": mem.percent,
                    "ram_used_gb": round(mem.used / 1e9, 1),
                    "ram_total_gb": round(mem.total / 1e9, 1),
                    "disk_percent": disk.percent,
                    "disk_free_gb": round(disk.free / 1e9, 1),
                    "cpu_temp": temp,
                    "net_sent_mb": round(net.bytes_sent / 1e6, 1),
                    "net_recv_mb": round(net.bytes_recv / 1e6, 1),
                    "process_count": len(psutil.pids()),
                    "uptime_seconds": int(time.time() - self._start_time),
                }
        except Exception as e:
            print(f"⚠️  Monitor update error: {e}")

    def get_snapshot(self):
        """Return the latest system stats snapshot (thread-safe)."""
        with self._data_lock:
            return dict(self._data)

    def get_summary_text(self):
        """Return a human-readable summary of system stats."""
        data = self.get_snapshot()
        if not data:
            return f"System monitoring data is not available yet, {CONFIG['USER_NAME']}."

        uptime_secs = data.get("uptime_seconds", 0)
        hours = uptime_secs // 3600
        minutes = (uptime_secs % 3600) // 60

        parts = [
            f"CPU at {data.get('cpu_percent', 'N/A')}%",
            f"RAM at {data.get('ram_percent', 'N/A')}% ({data.get('ram_used_gb', '?')}GB of {data.get('ram_total_gb', '?')}GB)",
            f"Disk {data.get('disk_percent', 'N/A')}% full ({data.get('disk_free_gb', '?')}GB free)",
            f"{data.get('process_count', '?')} processes running",
            f"System uptime {hours}h {minutes}m",
        ]

        temp = data.get("cpu_temp")
        if temp:
            parts.append(f"CPU temperature {temp}°C")

        return f"{', '.join(parts)}, {CONFIG['USER_NAME']}."


# Global singleton instance
monitor = MonitorService()
