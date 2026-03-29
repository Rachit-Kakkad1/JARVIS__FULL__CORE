import React, { useState, useRef } from 'react';

export default function InputBar({ onSend, isListening, onMicToggle }) {
  const [text, setText] = useState('');
  const inputRef = useRef(null);

  const handleSend = () => {
    const msg = text.trim();
    if (!msg) return;
    onSend(msg);
    setText('');
    inputRef.current?.focus();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="input-bar">
      <input
        ref={inputRef}
        className="input-field"
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Enter command or ask a question..."
        autoFocus
      />
      <button
        className={`btn-mic ${isListening ? 'active' : ''}`}
        onClick={onMicToggle}
        title={isListening ? 'Stop listening' : 'Start listening'}
      >
        🎤
      </button>
      <button className="btn-send" onClick={handleSend}>
        EXECUTE
      </button>
    </div>
  );
}
