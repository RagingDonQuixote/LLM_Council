import React, { useState, useEffect, useRef } from 'react';
import './RetroTerminal.css';

export default function RetroTerminal({ logs, isVisible, onClose }) {
  const [position, setPosition] = useState({ x: 100, y: 100 });
  const [size, setSize] = useState({ width: 600, height: 400 });
  const [isMinimized, setIsMinimized] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  
  const terminalRef = useRef(null);
  const logsEndRef = useRef(null);

  // Auto-scroll logs
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const handleMouseDown = (e) => {
    if (e.target.className === 'terminal-header' || e.target.className === 'terminal-title') {
      setIsDragging(true);
      setDragOffset({
        x: e.clientX - position.x,
        y: e.clientY - position.y
      });
    }
  };

  const handleResizeMouseDown = (e) => {
    e.stopPropagation();
    setIsResizing(true);
  };

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (isDragging) {
        setPosition({
          x: e.clientX - dragOffset.x,
          y: e.clientY - dragOffset.y
        });
      } else if (isResizing) {
        const newWidth = Math.max(300, e.clientX - position.x);
        const newHeight = Math.max(200, e.clientY - position.y);
        setSize({ width: newWidth, height: newHeight });
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      setIsResizing(false);
    };

    if (isDragging || isResizing) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, isResizing, dragOffset, position]);

  if (!isVisible) return null;

  return (
    <div 
      ref={terminalRef}
      className={`retro-terminal ${isMinimized ? 'minimized' : ''}`}
      style={{
        left: position.x,
        top: position.y,
        width: isMinimized ? '200px' : size.width,
        height: isMinimized ? '35px' : size.height
      }}
    >
      <div className="terminal-header" onMouseDown={handleMouseDown}>
        <div className="terminal-title">C:\COUNCIL\LOGS.EXE</div>
        <div className="terminal-controls">
          <button onClick={() => setIsMinimized(!isMinimized)} className="control-btn">
            {isMinimized ? '□' : '_'}
          </button>
          <button onClick={onClose} className="control-btn close">×</button>
        </div>
      </div>
      
      {!isMinimized && (
        <div className="terminal-body">
          <div className="terminal-content">
            {logs.map((log, i) => (
              <div key={i} className="terminal-line">
                <span className="prompt">C:\></span> {log}
              </div>
            ))}
            <div className="terminal-cursor">_</div>
            <div ref={logsEndRef} />
          </div>
          <div className="terminal-resize" onMouseDown={handleResizeMouseDown}>◢</div>
        </div>
      )}
    </div>
  );
}
