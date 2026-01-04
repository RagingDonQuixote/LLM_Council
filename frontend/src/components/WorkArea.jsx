import { useState } from 'react';
import UniversalModal from './UniversalModal';
import PromptExplorer from './PromptExplorer';
import BlueprintTree from './BlueprintTree';
import ResourceMonitor from './ResourceMonitor';
import './WorkArea.css';

const WorkArea = ({ 
  conversation, 
  currentConfig, 
  modelsMetadata, 
  onPromptSelect,
  showBlueprint,
  setShowBlueprint,
  showResources,
  setShowResources,
  showPromptDb,
  setShowPromptDb,
  bringToFront,
  modalZIndices
}) => {
  // We no longer manage visibility state here, but we can manage minimize state if we want to.
  // However, simpler to just use isOpen.
  // If we want individual minimize state, we can add it here or in App.
  // For now, let's assume 'closing' via the X button sets showX to false (unmounts).
  // 'Minimizing' is not strictly implemented in App state yet (only isOpen).
  // UniversalModal has onMinimize.
  
  // Let's implement local minimize state so minimizing doesn't close (unmount).
  const [minimized, setMinimized] = useState({
    blueprint: false,
    resources: false,
    promptDb: false
  });

  const toggleMinimize = (id) => {
    setMinimized(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  return (
    <div className="work-area">
      {/* Dock removed - moved to TopMenuBar */}

      <div className="modal-container">
        {showPromptDb && (
          <UniversalModal
            id="promptDb"
            title="Prompt Database"
            isOpen={true} // Controlled by App
            onClose={() => setShowPromptDb(false)}
            onMinimize={() => toggleMinimize('promptDb')}
            isMinimized={minimized.promptDb}
            zIndex={modalZIndices.promptDb}
            onFocus={() => bringToFront('promptDb')}
            initialPos={{ x: 50, y: 50 }}
            initialSize={{ width: 600, height: 450 }}
          >
            {!minimized.promptDb && (
              <PromptExplorer 
                onSelect={onPromptSelect} 
                currentConfig={currentConfig}
              />
            )}
          </UniversalModal>
        )}

        {showBlueprint && (
          <UniversalModal
            id="blueprint"
            title="Council Blueprint"
            isOpen={true}
            onClose={() => setShowBlueprint(false)}
            onMinimize={() => toggleMinimize('blueprint')}
            isMinimized={minimized.blueprint}
            zIndex={modalZIndices.blueprint}
            onFocus={() => bringToFront('blueprint')}
            initialPos={{ x: 150, y: 100 }}
            initialSize={{ width: 400, height: 500 }}
          >
            {!minimized.blueprint && (
              <BlueprintTree sessionState={conversation?.session_state} />
            )}
          </UniversalModal>
        )}

        {showResources && (
          <UniversalModal
            id="resources"
            title="Resource Monitor"
            isOpen={true}
            onClose={() => setShowResources(false)}
            onMinimize={() => toggleMinimize('resources')}
            isMinimized={minimized.resources}
            zIndex={modalZIndices.resources}
            onFocus={() => bringToFront('resources')}
            initialPos={{ x: 400, y: 50 }}
            initialSize={{ width: 350, height: 400 }}
          >
            {!minimized.resources && (
              <ResourceMonitor config={currentConfig} modelsMetadata={modelsMetadata} />
            )}
          </UniversalModal>
        )}
      </div>
    </div>
  );
};

export default WorkArea;
