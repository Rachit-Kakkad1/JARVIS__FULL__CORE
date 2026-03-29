import React, { useState, useEffect, useRef, useCallback } from 'react';
import { io } from 'socket.io-client';
import ArcReactor from './components/ArcReactor';
import ChatWindow from './components/ChatWindow';
import InputBar from './components/InputBar';
import SystemMonitor from './components/SystemMonitor';
import QuickActions from './components/QuickActions';
import ActivityLog from './components/ActivityLog';
import Navigation from './components/Navigation';
import Panel from './components/Panel';
import FaceScanGate from './components/FaceScanGate';
import './styles/globals.css';

const SOCKET_URL = window.location.hostname === 'localhost'
  ? `http://localhost:5000`
  : window.location.origin;

export default function App() {
  // ── State ───────────────────────────────────────────────────────
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [messages, setMessages] = useState([]);
  const [systemStats, setSystemStats] = useState({});
  const [isTyping, setIsTyping] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [activities, setActivities] = useState([]);
  const [activeNav, setActiveNav] = useState('dashboard');
  const [toasts, setToasts] = useState([]);
  const [status, setStatus] = useState({ usage_remaining: 100, brain: 'grok' });
  const [uptime, setUptime] = useState(0);
  const socketRef = useRef(null);
  const toastIdRef = useRef(0);

  // ── Socket Connection ───────────────────────────────────────────
  useEffect(() => {
    const socket = io(SOCKET_URL, {
      transports: ['websocket', 'polling'],
      reconnectionAttempts: 10,
    });
    socketRef.current = socket;

    socket.on('connect', () => {
      addActivity('Connected to JARVIS backend');
    });

    socket.on('system_stats', (data) => {
      setSystemStats(data);
      if (data.uptime_seconds) setUptime(data.uptime_seconds);
    });

    socket.on('jarvis_message', (data) => {
      const msg = typeof data === 'string'
        ? { role: 'assistant', content: data, timestamp: Date.now() }
        : { ...data, timestamp: data.timestamp || Date.now() };
      setMessages((prev) => [...prev, msg]);
    });

    socket.on('jarvis_typing', (val) => {
      setIsTyping(!!val);
    });

    socket.on('activity', (data) => {
      const desc = data.result || `${data.action}: ${data.target || ''}`;
      addActivity(desc);
    });

    // Fetch initial status
    fetch('/api/status')
      .then(r => r.json())
      .then(setStatus)
      .catch(() => {});

    return () => { socket.disconnect(); };
  }, []);

  // ── Uptime ticker ────────────────────────────────────────────────
  useEffect(() => {
    const interval = setInterval(() => {
      setUptime(prev => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // ── Helpers ──────────────────────────────────────────────────────
  const addActivity = useCallback((description) => {
    setActivities((prev) => [
      { description, timestamp: Date.now() },
      ...prev
    ].slice(0, 20));
  }, []);

  const addToast = useCallback((text) => {
    const id = ++toastIdRef.current;
    setToasts((prev) => [...prev, { id, text }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter(t => t.id !== id));
    }, 2500);
  }, []);

  const handleSend = useCallback((text) => {
    // Add user message to chat
    setMessages((prev) => [...prev, {
      role: 'user',
      content: text,
      timestamp: Date.now()
    }]);
    // Send to server
    socketRef.current?.emit('user_message', text);
    addActivity(`User: ${text}`);
  }, [addActivity]);

  const handleQuickAction = useCallback((actionId) => {
    socketRef.current?.emit('quick_action', actionId);
    addToast(`EXECUTING // ${actionId.toUpperCase()}`);
    addActivity(`Quick action: ${actionId}`);
  }, [addToast, addActivity]);

  const handleMicToggle = useCallback(() => {
    setIsListening(prev => {
      const next = !prev;
      socketRef.current?.emit('voice_toggle', next);
      addToast(next ? 'VOICE // ACTIVE' : 'VOICE // STANDBY');
      return next;
    });
  }, [addToast]);

  // ── Time formatting ─────────────────────────────────────────────
  const now = new Date();
  const dayOfYear = Math.floor((now - new Date(now.getFullYear(), 0, 0)) / 86400000);
  const stardate = `${now.getFullYear()}.${String(dayOfYear).padStart(3, '0')}`;
  const timeStr = now.toLocaleTimeString('en-US', { hour12: false });

  const getGreeting = () => {
    const h = now.getHours();
    if (h < 12) return 'Good morning, Sir';
    if (h < 17) return 'Good afternoon, Sir';
    return 'Good evening, Sir';
  };

  const formatUptime = (secs) => {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  const cpuBadgeClass = (systemStats.cpu_percent || 0) >= 75 ? 'critical' : (systemStats.cpu_percent || 0) >= 55 ? 'warning' : '';
  const ramBadgeClass = (systemStats.ram_percent || 0) >= 75 ? 'critical' : (systemStats.ram_percent || 0) >= 55 ? 'warning' : '';

  // ── Face Auth Handler ────────────────────────────────────────────
  const handleAuthenticated = useCallback(() => {
    setIsAuthenticated(true);
    // Tell the server this session is now authenticated
    socketRef.current?.emit('face_auth_success');
    addActivity('Biometric authentication successful');
    addToast('IDENTITY // VERIFIED');
  }, [addActivity, addToast]);

  // ── Render ──────────────────────────────────────────────────────

  // Show face scan gate if not authenticated
  if (!isAuthenticated) {
    return <FaceScanGate onAuthenticated={handleAuthenticated} />;
  }

  return (
    <div className="app-container">
      {/* ── LEFT SIDEBAR ──────────────────────────────────────── */}
      <div className="sidebar-left">
        <ArcReactor />

        <Panel title="System Status">
          <div className="system-status">
            <div className="status-row">
              <span className="status-dot online"></span>
              <span className="status-label">Status</span>
              <span className="status-value green">ONLINE</span>
            </div>
            <div className="status-row">
              <span className="status-dot online"></span>
              <span className="status-label">Phase</span>
              <span className="status-value">3 — FULL</span>
            </div>
            <div className="status-row">
              <span className="status-dot online"></span>
              <span className="status-label">Brain</span>
              <span className="status-value">{(status.brain || 'GROK').toUpperCase()} — {status.usage_remaining ?? '?'}</span>
            </div>
            <div className="status-row">
              <span className={`status-dot ${isListening ? 'listening' : 'online'}`}></span>
              <span className="status-label">Voice</span>
              <span className={`status-value ${isListening ? 'amber' : ''}`}>
                {isListening ? 'LISTENING' : 'STANDBY'}
              </span>
            </div>
          </div>
        </Panel>

        <Panel title="System Uptime">
          <div className="uptime-display">
            <div className="uptime-time">{formatUptime(uptime)}</div>
            <div className="uptime-label">SYSTEM UPTIME</div>
          </div>
        </Panel>

        <Navigation activeNav={activeNav} onNavChange={setActiveNav} />
      </div>

      {/* ── CENTER PANEL ──────────────────────────────────────── */}
      <div className="center-panel">
        <div className="header-bar">
          <div>
            <div className="header-greeting">{getGreeting()}</div>
            <div className="header-stardate">STARDATE: {stardate} // {timeStr}</div>
          </div>
          <div className="header-badges">
            <span className={`header-badge ${cpuBadgeClass}`}>
              CPU {Math.round(systemStats.cpu_percent || 0)}%
            </span>
            <span className={`header-badge ${ramBadgeClass}`}>
              RAM {Math.round(systemStats.ram_percent || 0)}%
            </span>
          </div>
        </div>

        <ChatWindow messages={messages} isTyping={isTyping} />

        <InputBar
          onSend={handleSend}
          isListening={isListening}
          onMicToggle={handleMicToggle}
        />
      </div>

      {/* ── RIGHT SIDEBAR ─────────────────────────────────────── */}
      <div className="sidebar-right">
        <SystemMonitor stats={systemStats} />
        <QuickActions onAction={handleQuickAction} />
        <ActivityLog activities={activities} />
      </div>

      {/* ── TOAST NOTIFICATIONS ───────────────────────────────── */}
      <div className="toast-container">
        {toasts.map((t) => (
          <div key={t.id} className="toast">{t.text}</div>
        ))}
      </div>
    </div>
  );
}
