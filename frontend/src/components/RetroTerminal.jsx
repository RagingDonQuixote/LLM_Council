import React, { useState, useEffect, useRef } from 'react';
import './RetroTerminal.css';

export default function RetroTerminal({ logs, isVisible, onClose }) {
  const logsEndRef = useRef(null);

  // Auto-scroll logs
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  if (!isVisible) return null;

  return (
    <div className="retro-terminal-content">
      <div className="terminal-body">
        <div className="terminal-content">
          <div className="terminal-header">
            SYSTEM STATUS: ONLINE
            <br />
            LAST UPDATE: {new Date().toLocaleTimeString()}
            <br />
            ----------------------------------------
          </div>
          {logs.map((log, i) => (
            <div key={i} className="terminal-line">
              <span className="timestamp">[{new Date().toLocaleTimeString()}]</span>
              <span className="prompt">C:\COUNCIL&gt;</span> {log}
            </div>
          ))}
          <div className="terminal-cursor">_</div>
          <div ref={logsEndRef} />
        </div>
      </div>
    </div>
  );
}
