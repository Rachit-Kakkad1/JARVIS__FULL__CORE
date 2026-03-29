import React, { useState, useEffect, useRef, useCallback } from 'react';

const SCAN_STATES = {
  CHECKING: 'checking',
  ENROLLING: 'enrolling',
  SCANNING: 'scanning',
  VERIFIED: 'verified',
  DENIED: 'denied',
  ERROR: 'error',
};

export default function FaceScanGate({ onAuthenticated }) {
  const [state, setState] = useState(SCAN_STATES.CHECKING);
  const [message, setMessage] = useState('INITIALIZING BIOMETRIC SYSTEMS...');
  const [subMessage, setSubMessage] = useState('');
  const [confidence, setConfidence] = useState(0);
  const [preview, setPreview] = useState(null);
  const [scanProgress, setScanProgress] = useState(0);
  const [showRetry, setShowRetry] = useState(false);
  const [enrolled, setEnrolled] = useState(false);
  const [particles, setParticles] = useState([]);
  const progressRef = useRef(null);
  const hasAutoScanned = useRef(false);

  // Generate random particles for the background
  useEffect(() => {
    const pts = Array.from({ length: 40 }, (_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: Math.random() * 2 + 1,
      duration: Math.random() * 8 + 4,
      delay: Math.random() * 5,
    }));
    setParticles(pts);
  }, []);

  // Check auth status on mount
  useEffect(() => {
    checkStatus();
  }, []);

  // Animate scan progress
  useEffect(() => {
    if (state === SCAN_STATES.SCANNING || state === SCAN_STATES.ENROLLING) {
      setScanProgress(0);
      const interval = setInterval(() => {
        setScanProgress(prev => {
          if (prev >= 90) {
            clearInterval(interval);
            return 90;
          }
          return prev + Math.random() * 3;
        });
      }, 100);
      progressRef.current = interval;
      return () => clearInterval(interval);
    }
  }, [state]);

  const checkStatus = async () => {
    try {
      const res = await fetch('/api/face-auth/status');
      const data = await res.json();

      if (!data.enabled) {
        // Auth disabled, go straight through
        onAuthenticated();
        return;
      }

      if (data.enrolled) {
        setEnrolled(true);
        setState(SCAN_STATES.SCANNING);
        setMessage('BIOMETRIC SCAN INITIATED');
        setSubMessage('Position your face within the scan zone');
        // Auto-trigger verification
        if (!hasAutoScanned.current) {
          hasAutoScanned.current = true;
          setTimeout(() => doVerify(), 1500);
        }
      } else {
        setEnrolled(false);
        setState(SCAN_STATES.ENROLLING);
        setMessage('FACE ENROLLMENT REQUIRED');
        setSubMessage('First-time setup — registering your biometric profile');
        setTimeout(() => doEnroll(), 2000);
      }
    } catch (err) {
      setState(SCAN_STATES.ERROR);
      setMessage('SYSTEM ERROR');
      setSubMessage(err.message);
    }
  };

  const doEnroll = async () => {
    setState(SCAN_STATES.ENROLLING);
    setMessage('CAPTURING BIOMETRIC DATA...');
    setSubMessage('Hold still — scanning facial geometry');

    try {
      const res = await fetch('/api/face-auth/enroll', { method: 'POST' });
      const data = await res.json();

      if (data.success) {
        setScanProgress(100);
        if (data.preview) setPreview(data.preview);
        setMessage('BIOMETRIC PROFILE CREATED');
        setSubMessage(data.message);
        setEnrolled(true);

        // Now verify
        setTimeout(() => {
          setPreview(null);
          setState(SCAN_STATES.SCANNING);
          setMessage('VERIFYING IDENTITY...');
          setSubMessage('Comparing face against enrolled profile');
          setTimeout(() => doVerify(), 1500);
        }, 2500);
      } else {
        setState(SCAN_STATES.ERROR);
        setMessage('ENROLLMENT FAILED');
        setSubMessage(data.message);
        setShowRetry(true);
      }
    } catch (err) {
      setState(SCAN_STATES.ERROR);
      setMessage('ENROLLMENT ERROR');
      setSubMessage(err.message);
      setShowRetry(true);
    }
  };

  const doVerify = async () => {
    setState(SCAN_STATES.SCANNING);
    setMessage('SCANNING...');
    setSubMessage('Analyzing facial biometrics');

    try {
      const res = await fetch('/api/face-auth/verify', { method: 'POST' });
      const data = await res.json();

      setScanProgress(100);
      if (data.preview) setPreview(data.preview);
      setConfidence(data.confidence || 0);

      if (data.authenticated) {
        setState(SCAN_STATES.VERIFIED);
        setMessage('IDENTITY VERIFIED');
        setSubMessage(`Confidence: ${(data.confidence * 100).toFixed(1)}%`);

        // Notify server via socket
        // Small delay for the animation to play
        setTimeout(() => {
          onAuthenticated();
        }, 3000);
      } else {
        setState(SCAN_STATES.DENIED);
        setMessage('ACCESS DENIED');
        setSubMessage(data.message || 'Face does not match authorized user.');
        setShowRetry(true);
      }
    } catch (err) {
      setState(SCAN_STATES.ERROR);
      setMessage('VERIFICATION ERROR');
      setSubMessage(err.message);
      setShowRetry(true);
    }
  };

  const handleRetry = () => {
    setShowRetry(false);
    setPreview(null);
    setScanProgress(0);
    setConfidence(0);
    hasAutoScanned.current = false;

    if (enrolled) {
      setState(SCAN_STATES.SCANNING);
      setMessage('RE-SCANNING...');
      setSubMessage('Position your face within the scan zone');
      setTimeout(() => doVerify(), 1500);
    } else {
      setState(SCAN_STATES.ENROLLING);
      setMessage('RETRYING ENROLLMENT...');
      setSubMessage('Hold still — scanning facial geometry');
      setTimeout(() => doEnroll(), 1500);
    }
  };

  const stateClass =
    state === SCAN_STATES.VERIFIED ? 'verified' :
    state === SCAN_STATES.DENIED ? 'denied' :
    state === SCAN_STATES.ERROR ? 'denied' : '';

  return (
    <div className={`face-gate ${stateClass}`}>
      {/* Background particles */}
      <div className="face-gate-particles">
        {particles.map(p => (
          <div
            key={p.id}
            className="face-gate-particle"
            style={{
              left: `${p.x}%`,
              top: `${p.y}%`,
              width: `${p.size}px`,
              height: `${p.size}px`,
              animationDuration: `${p.duration}s`,
              animationDelay: `${p.delay}s`,
            }}
          />
        ))}
      </div>

      {/* Grid overlay */}
      <div className="face-gate-grid" />

      {/* Top header */}
      <div className="face-gate-header">
        <div className="face-gate-header-line" />
        <span className="face-gate-header-text">J.A.R.V.I.S. SECURITY PROTOCOL</span>
        <div className="face-gate-header-line" />
      </div>

      {/* Main scan area */}
      <div className="face-gate-scanner">
        {/* Outer ring decorations */}
        <svg className="scan-ring-svg" viewBox="0 0 320 320">
          {/* Outermost ring — slow rotation */}
          <circle className="scan-ring scan-ring-1" cx="160" cy="160" r="155"
            strokeDasharray="12 8 6 20 3 15" strokeWidth="1" />
          {/* Middle ring — counter rotation */}
          <circle className="scan-ring scan-ring-2" cx="160" cy="160" r="142"
            strokeDasharray="20 6 10 12 4 8" strokeWidth="1.5" />
          {/* Inner ring — fast */}
          <circle className="scan-ring scan-ring-3" cx="160" cy="160" r="128"
            strokeDasharray="5 12 8 6 15 4" strokeWidth="1" />

          {/* Targeting tick marks */}
          {[0, 45, 90, 135, 180, 225, 270, 315].map(angle => (
            <line
              key={angle}
              className="scan-tick"
              x1="160" y1="12"
              x2="160" y2="22"
              transform={`rotate(${angle} 160 160)`}
            />
          ))}
        </svg>

        {/* Corner targeting brackets */}
        <div className={`scan-bracket scan-bracket-tl ${state === SCAN_STATES.SCANNING ? 'active' : ''}`} />
        <div className={`scan-bracket scan-bracket-tr ${state === SCAN_STATES.SCANNING ? 'active' : ''}`} />
        <div className={`scan-bracket scan-bracket-bl ${state === SCAN_STATES.SCANNING ? 'active' : ''}`} />
        <div className={`scan-bracket scan-bracket-br ${state === SCAN_STATES.SCANNING ? 'active' : ''}`} />

        {/* Face preview or placeholder */}
        <div className="scan-viewport">
          {preview ? (
            <img
              className="scan-preview-img"
              src={`data:image/jpeg;base64,${preview}`}
              alt="Face capture"
            />
          ) : (
            <div className="scan-placeholder">
              <svg viewBox="0 0 80 80" className="scan-face-icon">
                <ellipse cx="40" cy="34" rx="18" ry="22" fill="none" stroke="currentColor" strokeWidth="1.5" />
                <ellipse cx="40" cy="65" rx="28" ry="15" fill="none" stroke="currentColor" strokeWidth="1.5" />
                <circle cx="33" cy="30" r="2" fill="currentColor" />
                <circle cx="47" cy="30" r="2" fill="currentColor" />
                <path d="M35 40 Q40 45 45 40" fill="none" stroke="currentColor" strokeWidth="1" />
              </svg>
            </div>
          )}

          {/* Scan line sweeping effect */}
          {(state === SCAN_STATES.SCANNING || state === SCAN_STATES.ENROLLING) && (
            <div className="scan-line-sweep" />
          )}
        </div>

        {/* Verified checkmark / Denied X overlay */}
        {state === SCAN_STATES.VERIFIED && (
          <div className="scan-result-overlay verified-overlay">
            <svg viewBox="0 0 60 60" className="result-icon">
              <circle cx="30" cy="30" r="28" fill="none" stroke="var(--green)" strokeWidth="2" className="result-circle" />
              <path d="M18 30 L26 38 L42 22" fill="none" stroke="var(--green)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="result-check" />
            </svg>
          </div>
        )}
        {state === SCAN_STATES.DENIED && (
          <div className="scan-result-overlay denied-overlay">
            <svg viewBox="0 0 60 60" className="result-icon">
              <circle cx="30" cy="30" r="28" fill="none" stroke="var(--red)" strokeWidth="2" className="result-circle" />
              <path d="M20 20 L40 40 M40 20 L20 40" fill="none" stroke="var(--red)" strokeWidth="3" strokeLinecap="round" className="result-x" />
            </svg>
          </div>
        )}
      </div>

      {/* Progress bar */}
      <div className="scan-progress-track">
        <div
          className={`scan-progress-fill ${stateClass}`}
          style={{ width: `${scanProgress}%` }}
        />
      </div>

      {/* Status text */}
      <div className={`face-gate-status ${stateClass}`}>
        <div className="face-gate-status-label">{message}</div>
        <div className="face-gate-status-sub">{subMessage}</div>
      </div>

      {/* Confidence readout */}
      {confidence > 0 && (
        <div className="face-gate-confidence">
          <span className="confidence-label">MATCH CONFIDENCE</span>
          <span className={`confidence-value ${stateClass}`}>
            {(confidence * 100).toFixed(1)}%
          </span>
        </div>
      )}

      {/* Retry button */}
      {showRetry && (
        <button className="face-gate-retry" onClick={handleRetry}>
          ↻ RETRY SCAN
        </button>
      )}

      {/* Bottom decorative line */}
      <div className="face-gate-footer">
        <div className="face-gate-footer-line" />
        <span className="face-gate-footer-text">
          BIOMETRIC SECURITY ACTIVE // AETHERION SYSTEMS
        </span>
        <div className="face-gate-footer-line" />
      </div>
    </div>
  );
}
