import { useState, useEffect, useRef, useMemo } from 'react';
import './UniversalModal.css';

const UniversalModal = ({
  id,
  title,
  isOpen,
  onClose,
  onMinimize,
  children,
  initialPos = { x: 100, y: 100 },
  initialSize = { width: 500, height: 400 },
  minSize = { width: 200, height: 150 },
  zIndex = 100,
  onFocus
}) => {
  // Use lazy initialization for state to correctly load from localStorage
  const [pos, setPos] = useState(() => {
    const saved = localStorage.getItem(`modal_pref_${id}`);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.pos) {
          console.log(`Loaded pos from storage for ${id}:`, parsed.pos);
          return parsed.pos;
        }
      } catch (e) { console.error('Error loading pos', e); }
    }
    console.log(`Using initialPos for ${id}:`, initialPos);
    return initialPos;
  });

  const [size, setSize] = useState(() => {
    const saved = localStorage.getItem(`modal_pref_${id}`);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.size) return parsed.size;
      } catch (e) { console.error('Error loading size', e); }
    }
    return initialSize;
  });

  const [isMaximized, setIsMaximized] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(null); 
  
  const modalRef = useRef(null);
  const dragStartPos = useRef({ x: 0, y: 0 });
  const resizeStartData = useRef({ x: 0, y: 0, width: 0, height: 0, pos: { x: 0, y: 0 } });

  // Remove the problematic useEffect that overwrites the state
  // We rely entirely on lazy initialization in useState above.
  
  const savePreferences = () => {
    console.log(`Saving preferences for ${id}:`, { pos, size });
    localStorage.setItem(`modal_pref_${id}`, JSON.stringify({ pos, size }));
  };

  const handleResetToDefault = () => {
    setPos(initialPos);
    setSize(initialSize);
    setIsMaximized(false);
    localStorage.removeItem(`modal_pref_${id}`); // Clear saved preference
  };

  const handleSetAsDefault = () => {
    savePreferences();
    alert(`${title}: Position und Größe als Standard gespeichert.`);
  };

  const handleMouseDown = (e) => {
    onFocus?.();
    if (isMaximized) return;
    
    if (e.target.classList.contains('modal-header') || e.target.parentElement.classList.contains('modal-header')) {
      setIsDragging(true);
      dragStartPos.current = {
        x: e.clientX - pos.x,
        y: e.clientY - pos.y
      };
    }
  };

  const handleResizeStart = (direction, e) => {
    e.stopPropagation();
    e.preventDefault();
    onFocus?.();
    if (isMaximized) return;

    setIsResizing(direction);
    resizeStartData.current = {
      x: e.clientX,
      y: e.clientY,
      width: size.width,
      height: size.height,
      pos: { ...pos }
    };
  };

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (isDragging) {
        setPos({
          x: e.clientX - dragStartPos.current.x,
          y: e.clientY - dragStartPos.current.y
        });
      } else if (isResizing) {
        const dx = e.clientX - resizeStartData.current.x;
        const dy = e.clientY - resizeStartData.current.y;
        
        let newWidth = resizeStartData.current.width;
        let newHeight = resizeStartData.current.height;
        let newX = resizeStartData.current.pos.x;
        let newY = resizeStartData.current.pos.y;

        if (isResizing.includes('e')) newWidth = Math.max(minSize.width, resizeStartData.current.width + dx);
        if (isResizing.includes('s')) newHeight = Math.max(minSize.height, resizeStartData.current.height + dy);
        if (isResizing.includes('w')) {
          const possibleWidth = resizeStartData.current.width - dx;
          if (possibleWidth >= minSize.width) {
            newWidth = possibleWidth;
            newX = resizeStartData.current.pos.x + dx;
          }
        }
        if (isResizing.includes('n')) {
          const possibleHeight = resizeStartData.current.height - dy;
          if (possibleHeight >= minSize.height) {
            newHeight = possibleHeight;
            newY = resizeStartData.current.pos.y + dy;
          }
        }

        setPos({ x: newX, y: newY });
        setSize({ width: newWidth, height: newHeight });
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      setIsResizing(null);
      savePreferences(); // Auto-save after drag or resize
    };

    if (isDragging || isResizing) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, isResizing, minSize]);

  // Sync maximized state with open state
  useEffect(() => {
    if (!isOpen) {
      setIsMaximized(false);
    }
  }, [isOpen]);

  const style = isMaximized 
    ? { zIndex } 
    : {
        left: `${pos.x}px`,
        top: `${pos.y}px`,
        width: isOpen ? `${size.width}px` : '220px', // Compact width when minimized
        height: isOpen ? `${size.height}px` : '38px', // Fixed height when "minimized" (closed)
        zIndex,
        overflow: isOpen ? 'visible' : 'hidden'
      };

  const handleMinimize = (e) => {
    e.stopPropagation();
    setIsMaximized(false); 
    onMinimize();
  };

  // If NOT isOpen (minimized in WorkArea logic), we don't render at all
  if (!isOpen) return null;

  return (
    <div 
      ref={modalRef}
      className={`universal-modal ${isMaximized ? 'maximized' : ''} ${isDragging ? 'dragging' : ''} ${isResizing ? 'resizing' : ''}`}
      style={isMaximized 
        ? { zIndex } 
        : {
            left: `${pos.x}px`,
            top: `${pos.y}px`,
            width: `${size.width}px`,
            height: `${size.height}px`,
            zIndex
          }
      }
      onMouseDown={() => onFocus?.()}
    >
      <div className="modal-debug-info">
        x: {Math.round(pos.x)}, y: {Math.round(pos.y)}, z: {zIndex}
      </div>
      <div className="modal-header" onMouseDown={handleMouseDown}>
        <span className="modal-title">{title}</span>
        <div className="modal-controls">
          <button className="control-btn" onClick={handleSetAsDefault} title="Set as Default (Save size/pos)">📌</button>
          <button className="control-btn" onClick={handleResetToDefault} title="Reset to Default">🔄</button>
          <button className="control-btn" onClick={handleMinimize} title="Minimize">➖</button>
          <button className="control-btn" onClick={() => setIsMaximized(!isMaximized)} title={isMaximized ? "Restore" : "Maximize"}>
            {isMaximized ? '🗗' : '🗖'}
          </button>
          <button className="control-btn close" onClick={onClose} title="Close">✖</button>
        </div>
      </div>
      
      <div className="modal-content">
        {children}
      </div>

      {!isMaximized && isOpen && (
        <>
          <div className="resize-handle n" onMouseDown={(e) => handleResizeStart('n', e)} />
          <div className="resize-handle s" onMouseDown={(e) => handleResizeStart('s', e)} />
          <div className="resize-handle e" onMouseDown={(e) => handleResizeStart('e', e)} />
          <div className="resize-handle w" onMouseDown={(e) => handleResizeStart('w', e)} />
          <div className="resize-handle ne" onMouseDown={(e) => handleResizeStart('ne', e)} />
          <div className="resize-handle nw" onMouseDown={(e) => handleResizeStart('nw', e)} />
          <div className="resize-handle se" onMouseDown={(e) => handleResizeStart('se', e)} />
          <div className="resize-handle sw" onMouseDown={(e) => handleResizeStart('sw', e)} />
        </>
      )}
    </div>
  );
};

export default UniversalModal;
