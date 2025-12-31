import { useState, useCallback, useRef, useEffect } from 'react';
import UniversalModal from './UniversalModal';
import PromptExplorer from './PromptExplorer';
import BlueprintTree from './BlueprintTree';
import ResourceMonitor from './ResourceMonitor';
import RetroTerminal from './RetroTerminal';
import './WorkArea.css';

const WorkArea = ({ conversation, currentConfig, modelsMetadata, onPromptSelect, showTerminal, setShowTerminal }) => {
  const [modals, setModals] = useState({
    prompt_db: { isOpen: true, isMinimized: false, zIndex: 100 },
    blueprint: { isOpen: true, isMinimized: false, zIndex: 101 },
    resources: { isOpen: true, isMinimized: false, zIndex: 102 },
    terminal: { isOpen: false, isMinimized: false, zIndex: 103 }
  });

  // Sync showTerminal prop with internal modal state
  useEffect(() => {
    if (showTerminal && !modals.terminal.isOpen) {
      setModals(prev => ({
        ...prev,
        terminal: { ...prev.terminal, isOpen: true, isMinimized: false, zIndex: maxZ + 1 }
      }));
      setMaxZ(prev => prev + 1);
    }
  }, [showTerminal]);

  const [maxZ, setMaxZ] = useState(105);
  const [dockPos, setDockPos] = useState({ x: 0, y: 10 }); // Default: x=0 (centered via CSS), y=10
  const [isVerticalDock, setIsVerticalDock] = useState(false);
  const [isDraggingDock, setIsDraggingDock] = useState(false);
  const dragStartPos = useRef({ x: 0, y: 0 });

  const toggleModal = (id) => {
    const isCurrentlyOpen = modals[id].isOpen && !modals[id].isMinimized;
    
    // 1. Update internal state
    setModals(prev => ({
      ...prev,
      [id]: { 
        ...prev[id], 
        isOpen: true, 
        isMinimized: isCurrentlyOpen, 
        zIndex: maxZ + 1 
      }
    }));
    setMaxZ(prev => prev + 1);

    // 2. Update App state (outside of the internal state updater to avoid React warning)
    if (id === 'terminal') {
      setShowTerminal(!isCurrentlyOpen);
    }
  };

  const minimizeModal = (id) => {
    setModals(prev => ({
      ...prev,
      [id]: { ...prev[id], isMinimized: true }
    }));
  };

  const focusModal = (id) => {
    if (modals[id].zIndex === maxZ && !modals[id].isMinimized) return;
    setModals(prev => ({
      ...prev,
      [id]: { ...prev[id], zIndex: maxZ + 1, isMinimized: false }
    }));
    setMaxZ(prev => prev + 1);
  };

  const minimizeAll = () => {
    setModals(prev => {
      const next = {};
      Object.keys(prev).forEach(id => {
        next[id] = { ...prev[id], isMinimized: true };
      });
      return next;
    });
  };

  // Dock Dragging Logic
  const handleDockMouseDown = (e) => {
    if (e.target.closest('.dock-handle')) {
      setIsDraggingDock(true);
      dragStartPos.current = {
        x: e.clientX - dockPos.x,
        y: e.clientY - dockPos.y
      };
      e.preventDefault();
    }
  };

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (isDraggingDock) {
        setDockPos({
          x: e.clientX - dragStartPos.current.x,
          y: e.clientY - dragStartPos.current.y
        });
      }
    };

    const handleMouseUp = () => {
      setIsDraggingDock(false);
    };

    if (isDraggingDock) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDraggingDock]);

  return (
    <div className="work-area">
      <div 
        className={`work-area-dock ${isDraggingDock ? 'dragging' : ''} ${isVerticalDock ? 'vertical' : ''}`}
        style={{ 
          left: `calc(50% + ${dockPos.x}px)`, 
          top: `${dockPos.y}px`,
          transform: isVerticalDock ? 'translate(-50%, 0)' : 'translateX(-50%)'
        }}
        onMouseDown={handleDockMouseDown}
      >
        <div className="dock-handle" title="Verschieben">
          ⠿
        </div>
        <button 
          className="dock-btn orientation-toggle" 
          onClick={() => setIsVerticalDock(!isVerticalDock)}
          title={isVerticalDock ? "Horizontal ausrichten" : "Vertikal ausrichten"}
        >
          {isVerticalDock ? '➖' : '｜'}
        </button>
        <div className="dock-separator" />
        <button 
          className={`dock-btn ${modals.prompt_db.isOpen && !modals.prompt_db.isMinimized ? 'active' : ''} ${modals.prompt_db.isMinimized ? 'minimized' : ''}`} 
          onClick={() => toggleModal('prompt_db')}
          title="Prompt Database"
        >
          📂 {isVerticalDock ? '' : 'Prompt DB'}
        </button>
        <button 
          className={`dock-btn ${modals.blueprint.isOpen && !modals.blueprint.isMinimized ? 'active' : ''} ${modals.blueprint.isMinimized ? 'minimized' : ''}`} 
          onClick={() => toggleModal('blueprint')}
          title="Council Blueprint"
        >
          🗺️ {isVerticalDock ? '' : 'Blueprint'}
        </button>
        <button 
          className={`dock-btn ${modals.resources.isOpen && !modals.resources.isMinimized ? 'active' : ''} ${modals.resources.isMinimized ? 'minimized' : ''}`} 
          onClick={() => toggleModal('resources')}
          title="Resource Monitor"
        >
          📊 {isVerticalDock ? '' : 'Resources'}
        </button>
        <button 
          className={`dock-btn terminal-btn ${modals.terminal.isOpen && !modals.terminal.isMinimized ? 'active' : ''} ${modals.terminal.isMinimized ? 'minimized' : ''}`} 
          onClick={() => toggleModal('terminal')}
          title="IBM Terminal (Logs)"
        >
          📟 {isVerticalDock ? '' : 'IBM Terminal'}
        </button>
        <div className="dock-separator" />
        <button className="dock-btn minimize-all" onClick={minimizeAll} title="Minimize All">
          📉 {isVerticalDock ? '' : 'Minimize All'}
        </button>
      </div>

      <div className="modal-container">
        {modals.prompt_db.isOpen && (
          <UniversalModal
            id="prompt_db"
            title="Prompt Database"
            isOpen={!modals.prompt_db.isMinimized}
            onClose={() => toggleModal('prompt_db')}
            onMinimize={() => minimizeModal('prompt_db')}
            zIndex={modals.prompt_db.zIndex}
            onFocus={() => focusModal('prompt_db')}
            initialPos={{ x: 50, y: 50 }}
            initialSize={{ width: 600, height: 450 }}
          >
            <PromptExplorer 
              onSelect={onPromptSelect} 
              currentConfig={currentConfig}
            />
          </UniversalModal>
        )}

        {modals.blueprint.isOpen && (
          <UniversalModal
            id="blueprint"
            title="Council Blueprint"
            isOpen={!modals.blueprint.isMinimized}
            onClose={() => toggleModal('blueprint')}
            onMinimize={() => minimizeModal('blueprint')}
            zIndex={modals.blueprint.zIndex}
            onFocus={() => focusModal('blueprint')}
            initialPos={{ x: 150, y: 100 }}
            initialSize={{ width: 400, height: 500 }}
          >
            <BlueprintTree sessionState={conversation?.session_state} />
          </UniversalModal>
        )}

        {modals.resources.isOpen && (
          <UniversalModal
            id="resources"
            title="Resource Monitor"
            isOpen={!modals.resources.isMinimized}
            onClose={() => toggleModal('resources')}
            onMinimize={() => minimizeModal('resources')}
            zIndex={modals.resources.zIndex}
            onFocus={() => focusModal('resources')}
            initialPos={{ x: 400, y: 50 }}
            initialSize={{ width: 350, height: 400 }}
          >
            <ResourceMonitor config={currentConfig} modelsMetadata={modelsMetadata} />
          </UniversalModal>
        )}

        {modals.terminal.isOpen && (
          <UniversalModal
            id="terminal"
            title="IBM Terminal (Logs)"
            isOpen={!modals.terminal.isMinimized}
            onClose={() => toggleModal('terminal')}
            onMinimize={() => minimizeModal('terminal')}
            zIndex={modals.terminal.zIndex}
            onFocus={() => focusModal('terminal')}
            initialPos={{ x: 500, y: 300 }}
            initialSize={{ width: 600, height: 400 }}
          >
            <RetroTerminal 
              logs={conversation?.terminal_logs || []} 
              isVisible={true}
              onClose={() => toggleModal('terminal')} 
            />
          </UniversalModal>
        )}
      </div>
    </div>
  );
};

export default WorkArea;
