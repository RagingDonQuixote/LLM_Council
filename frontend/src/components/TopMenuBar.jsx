import { useState, useRef, useEffect } from 'react';
import './TopMenuBar.css';

const TopMenuBar = ({
  onNewConversation,
  onOpenSettings,
  showTerminal,
  setShowTerminal,
  showDbBrowser,
  setShowDbBrowser,
  showBlueprint,
  setShowBlueprint,
  showResources,
  setShowResources,
  showPromptDb,
  setShowPromptDb,
  conversationActive // To disable buttons if no conversation
}) => {
  const [showDevTools, setShowDevTools] = useState(false);
  const devToolsRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (devToolsRef.current && !devToolsRef.current.contains(event.target)) {
        setShowDevTools(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  return (
    <div className="top-menu-bar">
      <div className="menu-group left">
      </div>

      <div className="menu-group center">
        {conversationActive && (
          <>
            <button 
              className={`menu-btn ${showPromptDb ? 'active' : ''}`}
              onClick={() => setShowPromptDb(!showPromptDb)}
              title="Prompt Library"
            >
              📚 Prompts
            </button>
            <button 
              className={`menu-btn ${showBlueprint ? 'active' : ''}`}
              onClick={() => setShowBlueprint(!showBlueprint)}
              title="Conversation Blueprint"
            >
              🗺️ Blueprint
            </button>
            <button 
              className={`menu-btn ${showResources ? 'active' : ''}`}
              onClick={() => setShowResources(!showResources)}
              title="Resource Monitor"
            >
              📊 Resources
            </button>
          </>
        )}

        <div className="dropdown-container" ref={devToolsRef}>
          <button 
            className={`menu-btn dropdown-trigger ${showDevTools ? 'active' : ''}`}
            onClick={() => setShowDevTools(!showDevTools)}
          >
            🛠️ Dev Tools ▾
          </button>
          {showDevTools && (
            <div className="dropdown-menu">
              <button 
                className={`dropdown-item ${showTerminal ? 'active' : ''}`}
                onClick={() => {
                  setShowTerminal(!showTerminal);
                  setShowDevTools(false);
                }}
              >
                📟 IBM Terminal
              </button>
              <button 
                className={`dropdown-item ${showDbBrowser ? 'active' : ''}`}
                onClick={() => {
                  setShowDbBrowser(!showDbBrowser);
                  setShowDevTools(false);
                }}
              >
                🗄️ DB Browser
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="menu-group right">
        <button className="menu-btn" onClick={onOpenSettings}>
          ⚙️ Settings
        </button>
      </div>
    </div>
  );
};

export default TopMenuBar;
