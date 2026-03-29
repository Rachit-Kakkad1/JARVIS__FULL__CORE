import React, { useRef, useEffect, useState } from 'react';

export default function ChatWindow({ messages, isTyping }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  return (
    <div className="chat-window">
      {messages.map((msg, i) => (
        <Message key={i} msg={msg} />
      ))}
      {isTyping && (
        <div className="typing-indicator">
          <span className="typing-label">JARVIS // PROCESSING</span>
          <div className="typing-dots">
            <span className="typing-dot"></span>
            <span className="typing-dot"></span>
            <span className="typing-dot"></span>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}

function Message({ msg }) {
  const isUser = msg.role === 'user';
  const [displayed, setDisplayed] = useState(isUser ? msg.content : '');
  const [done, setDone] = useState(isUser);

  useEffect(() => {
    if (isUser) return;
    setDisplayed('');
    setDone(false);
    let idx = 0;
    const text = msg.content || '';
    const speed = Math.max(8, 35 - Math.floor(text.length / 20));
    const interval = setInterval(() => {
      idx++;
      setDisplayed(text.substring(0, idx));
      if (idx >= text.length) {
        clearInterval(interval);
        setDone(true);
      }
    }, speed);
    return () => clearInterval(interval);
  }, [msg.content, isUser]);

  const time = msg.timestamp
    ? new Date(msg.timestamp).toLocaleTimeString('en-US', { hour12: false })
    : new Date().toLocaleTimeString('en-US', { hour12: false });

  return (
    <div className={`message ${isUser ? 'user' : 'assistant'}`}>
      {!isUser && <div className="message-prefix">JARVIS //</div>}
      <div className="message-text">{displayed}{!done && <span className="cursor-blink">▍</span>}</div>
      <div className="message-time">{time}</div>
    </div>
  );
}
