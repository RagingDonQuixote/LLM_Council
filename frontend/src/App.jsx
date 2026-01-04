import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import Settings from './components/Settings';
import RetroTerminal from './components/RetroTerminal';
import TopMenuBar from './components/TopMenuBar';
import DbBrowser from './components/DbBrowser';
import UniversalModal from './components/UniversalModal';
import { api } from './api';
import './App.css';

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [activeRevision, setActiveRevision] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [versionInfo, setVersionInfo] = useState({ printname: 'LLM Council', version: '' });
  const [showSettings, setShowSettings] = useState(false);
  const [showStage4, setShowStage4] = useState(false);
  
  // Tool Visibility States
  const [showTerminal, setShowTerminal] = useState(false);
  const [showDbBrowser, setShowDbBrowser] = useState(false);
  const [showBlueprint, setShowBlueprint] = useState(false);
  const [showResources, setShowResources] = useState(false);
  const [showPromptDb, setShowPromptDb] = useState(false);

  // Z-Index Management for Modals
  const [maxZ, setMaxZ] = useState(1000);
  const [modalZIndices, setModalZIndices] = useState({
    terminal: 1000,
    dbBrowser: 1000,
    blueprint: 1000,
    resources: 1000,
    promptDb: 1000
  });

  const bringToFront = (modalId) => {
    setMaxZ(prev => {
      const newMax = prev + 1;
      setModalZIndices(prevIndices => ({
        ...prevIndices,
        [modalId]: newMax
      }));
      return newMax;
    });
  };

  const [terminalLogs, setTerminalLogs] = useState([]);
  const [humanFeedback, setHumanFeedback] = useState('');
  const [councilConfig, setCouncilConfig] = useState(null);
  const [modelsMetadata, setModelsMetadata] = useState({});
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);

  // Load initial data on mount
  useEffect(() => {
    loadConversations();
    loadVersion();
    loadCouncilStatus();
  }, []);

  const loadCouncilStatus = async () => {
    try {
      const config = await api.getConfig();
      setCouncilConfig(config);
      
      const allModelIds = [...config.council_models];
      if (config.chairman_model && !allModelIds.includes(config.chairman_model)) {
        allModelIds.push(config.chairman_model);
      }
      
      if (allModelIds.length > 0) {
        const metadata = await api.getModelsMetadata(allModelIds);
        setModelsMetadata(metadata);
      }
    } catch (error) {
      console.error('Failed to load council status:', error);
    }
  };

  const loadVersion = async () => {
    try {
      const info = await api.getVersion();
      setVersionInfo(info);
    } catch (error) {
      console.error('Failed to load version:', error);
    }
  };

  // Load conversation details when selected
  useEffect(() => {
    if (currentConversationId) {
      loadConversation(currentConversationId);
    }
  }, [currentConversationId]);

  const loadConversations = async () => {
    try {
      const convs = await api.listConversations();
      setConversations(convs);
      
      // Auto-select latest conversation if exists, but DO NOT create a new one automatically
      if (convs.length > 0 && !currentConversationId) {
        // Optional: auto-select the most recent one
        // setCurrentConversationId(convs[0].id);
      }
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadConversation = async (id, revisionIndex = null) => {
    try {
      const conv = await api.getConversation(id);
      setCurrentConversation(conv);
      
      // If a revision index was provided, set it. Otherwise default to the last one.
      const assistantMsgs = conv.messages.filter(m => m.role === 'assistant');
      if (revisionIndex !== null) {
        setActiveRevision(revisionIndex);
      } else {
        setActiveRevision(Math.max(0, assistantMsgs.length - 1));
      }
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const handleArchiveConversation = async (id) => {
    try {
      await api.archiveConversation(id);
      setConversations(conversations.filter((c) => c.id !== id));
      if (currentConversationId === id) {
        setCurrentConversationId(null);
        setCurrentConversation(null);
      }
    } catch (error) {
      console.error('Failed to archive conversation:', error);
      alert('Failed to archive conversation');
    }
  };

  const handleDeleteConversationPermanent = async (id) => {
    try {
      await api.deleteConversationPermanent(id);
      setConversations(conversations.filter((c) => c.id !== id));
      if (currentConversationId === id) {
        setCurrentConversationId(null);
        setCurrentConversation(null);
      }
      setDeleteConfirmId(null);
    } catch (error) {
      console.error('Failed to delete conversation:', error);
      alert('Failed to delete conversation');
    }
  };

  const onRequestDelete = (id) => {
    setDeleteConfirmId(id);
    bringToFront('deleteConfirm');
  };

  const handleNewConversation = async () => {
    try {
      const newConv = await api.createConversation();
      setConversations([
        { id: newConv.id, created_at: newConv.created_at, message_count: 0 },
        ...conversations,
      ]);
      setCurrentConversationId(newConv.id);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const handleSelectConversation = (id, revisionIndex = null) => {
    if (id === currentConversationId && revisionIndex !== null) {
      setActiveRevision(revisionIndex);
    } else {
      setCurrentConversationId(id);
      // loadConversation will be triggered by useEffect
      // but we need to pass the revisionIndex somehow or let it default
    }
  };

  const handleOpenSettings = () => {
    setShowSettings(true);
  };

  const handleCloseSettings = () => {
    setShowSettings(false);
    loadCouncilStatus(); // Refresh council status after settings change
  };

  const handleHumanFeedbackSubmit = async (continueDiscussion, rating) => {
    if (!currentConversationId) return;

    setIsLoading(true);
    if (continueDiscussion) {
      setShowTerminal(true);
      bringToFront('terminal');
      setTerminalLogs(prev => [...prev, '--- STARTING REVISION ROUND ---', `Human Feedback: ${humanFeedback}`, 'Initiating Council stream with feedback...']);
      
      try {
        // Optimistically add user message (the feedback)
        const feedbackMsg = { role: 'user', content: `Human Chairman Feedback: ${humanFeedback}` };
        
        // Add assistant placeholder for the new round
        const assistantMessage = {
          role: 'assistant',
          stage1: null,
          stage2: null,
          stage3: null,
          metadata: null,
          loading: { stage1: false, stage2: false, stage3: false }
        };

        setCurrentConversation((prev) => ({
          ...prev,
          messages: [...prev.messages, feedbackMsg, assistantMessage],
        }));

        await api.submitHumanFeedbackStream(currentConversationId, humanFeedback, (eventType, event) => {
          switch (eventType) {
            case 'log':
              setTerminalLogs(prev => [...prev, event.message]);
              break;
            case 'stage1_start':
              setCurrentConversation((prev) => {
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                lastMsg.loading.stage1 = true;
                return { ...prev, messages };
              });
              break;
            case 'stage1_complete':
              setCurrentConversation((prev) => {
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                lastMsg.stage1 = event.data;
                lastMsg.loading.stage1 = false;
                return { ...prev, messages };
              });
              break;
            case 'stage2_start':
              setCurrentConversation((prev) => {
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                lastMsg.loading.stage2 = true;
                return { ...prev, messages };
              });
              break;
            case 'stage2_complete':
              setCurrentConversation((prev) => {
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                lastMsg.stage2 = event.data;
                lastMsg.metadata = event.metadata;
                lastMsg.loading.stage2 = false;
                return { ...prev, messages };
              });
              break;
            case 'stage3_start':
              setCurrentConversation((prev) => {
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                lastMsg.loading.stage3 = true;
                return { ...prev, messages };
              });
              break;
            case 'stage3_complete':
              setCurrentConversation((prev) => {
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                lastMsg.stage3 = event.data;
                lastMsg.loading.stage3 = false;
                return { ...prev, messages };
              });
              break;
            case 'human_input_required':
              setShowStage4(true);
              setIsLoading(false);
              break;
            case 'complete':
              setTerminalLogs(prev => [...prev, '--- REVISION COMPLETE ---']);
              loadConversations();
              setIsLoading(false);
              break;
            case 'error':
              console.error('Stream error:', event.message);
              setTerminalLogs(prev => [...prev, `ERROR: ${event.message}`]);
              setIsLoading(false);
              break;
          }
        });

        setShowStage4(false);
        setHumanFeedback('');
      } catch (error) {
        console.error('Failed to submit feedback stream:', error);
        setIsLoading(false);
      }
    } else {
      try {
        await api.submitHumanFeedback(currentConversationId, humanFeedback);
        handleEndSession(rating);
        setShowStage4(false);
        setHumanFeedback('');
      } catch (error) {
        console.error('Failed to submit feedback:', error);
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleEndSession = (rating) => {
    const finalRating = rating || 5;
    api.endSession(currentConversationId, finalRating).then(() => {
      loadConversations();
    });
  };

  const handleRestartConversation = async (id) => {
    const targetId = id || currentConversationId;
    if (!targetId) return;
    if (!confirm('Are you sure you want to restart this conversation? All messages will be lost.')) return;
    
    try {
      setIsLoading(true);
      await api.resetConversation(targetId);
      
      if (targetId === currentConversationId) {
        await loadConversation(targetId);
        setTerminalLogs([]);
      } else {
        // If we restarted a non-active conversation, we might want to reload the list 
        // if the title or metadata changed (though reset usually keeps title)
        loadConversations();
      }
      setIsLoading(false);
    } catch (error) {
      console.error('Failed to restart conversation:', error);
      setIsLoading(false);
      alert('Failed to restart conversation');
    }
  };

  const handleStage4Submit = (continueDiscussion, rating) => {
    handleHumanFeedbackSubmit(continueDiscussion, rating);
  };

  const handleStage4Cancel = () => {
    setShowStage4(false);
    setHumanFeedback('');
  };

  const handleSendMessage = async (content) => {
    if (!currentConversation) return;

    setIsLoading(true);
    setTerminalLogs([]); // Clear logs for new message
    setShowTerminal(true); // Show terminal when council starts working
    bringToFront('terminal');
    
    try {
      await api.sendMessage(currentConversation.id, content, (event) => {
        if (event.type === 'log') {
          setTerminalLogs(prev => [...prev, `[COUNCIL] ${event.message}`]);
        } else if (event.type === 'session_state') {
          // Update conversation with new blueprint/session state
          setCurrentConversation(prev => ({
            ...prev,
            session_state: event.data
          }));
        } else if (event.type === 'stage1_start') {
          // Handle stage start if needed
        } else if (event.type === 'stage1_complete') {
          // We'll update the full conversation at the end
        } else if (event.type === 'human_input_required') {
          setShowStage4(true);
        } else if (event.type === 'complete') {
          // Final fetch to get the full updated conversation
          loadConversation(currentConversation.id);
          setIsLoading(false);
        } else if (event.type === 'error') {
          setTerminalLogs(prev => [...prev, `[ERROR] ${event.message}`]);
          setIsLoading(false);
        }
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      setTerminalLogs(prev => [...prev, `[ERROR] ${error.message}`]);
      setIsLoading(false);
    }
  };

  return (
    <div className="app">
      <TopMenuBar 
        onNewConversation={handleNewConversation}
        onOpenSettings={handleOpenSettings}
        showTerminal={showTerminal}
        setShowTerminal={(val) => { setShowTerminal(val); if(val) bringToFront('terminal'); }}
        showDbBrowser={showDbBrowser}
        setShowDbBrowser={(val) => { setShowDbBrowser(val); if(val) bringToFront('dbBrowser'); }}
        showBlueprint={showBlueprint}
        setShowBlueprint={(val) => { setShowBlueprint(val); if(val) bringToFront('blueprint'); }}
        showResources={showResources}
        setShowResources={(val) => { setShowResources(val); if(val) bringToFront('resources'); }}
        showPromptDb={showPromptDb}
        setShowPromptDb={(val) => { setShowPromptDb(val); if(val) bringToFront('promptDb'); }}
        conversationActive={!!currentConversation}
      />

      <Sidebar
          conversations={conversations}
          currentConversationId={currentConversationId}
          activeRevision={activeRevision}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
          onArchiveConversation={handleArchiveConversation}
          onDeleteConversation={onRequestDelete}
          onRestartConversation={handleRestartConversation}
          onOpenSettings={handleOpenSettings}
          versionInfo={versionInfo}
          councilConfig={councilConfig}
          modelsMetadata={modelsMetadata}
        />
      
      <ChatInterface
        conversation={currentConversation}
        activeRevision={activeRevision}
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
        showStage4={showStage4}
        humanFeedback={humanFeedback}
        setHumanFeedback={setHumanFeedback}
        onStage4Submit={handleStage4Submit}
        onStage4Cancel={handleStage4Cancel}
        isLoadingStage4={isLoading}
        currentConfig={councilConfig}
        onOpenSettings={handleOpenSettings}
        modelsMetadata={modelsMetadata}
        // Pass tool visibility states
        showBlueprint={showBlueprint}
        setShowBlueprint={setShowBlueprint}
        showResources={showResources}
        setShowResources={setShowResources}
        showPromptDb={showPromptDb}
        setShowPromptDb={setShowPromptDb}
        bringToFront={bringToFront}
        modalZIndices={modalZIndices}
        // Terminal is now global, handled in App
       />

      {/* Global Modals */}
      {showTerminal && (
        <UniversalModal
          id="terminal"
          title="IBM Terminal (Logs)"
          isOpen={true}
          onClose={() => setShowTerminal(false)}
          onMinimize={() => {}} // Could implement minimize state in App if needed
          zIndex={modalZIndices.terminal}
          onFocus={() => bringToFront('terminal')}
          initialPos={{ x: 500, y: 300 }}
          initialSize={{ width: 600, height: 400 }}
        >
          <RetroTerminal 
            logs={terminalLogs} 
            isVisible={true}
            onClose={() => setShowTerminal(false)} 
          />
        </UniversalModal>
      )}

      {showDbBrowser && (
        <UniversalModal
          id="dbBrowser"
          title="Database Browser"
          isOpen={true}
          onClose={() => setShowDbBrowser(false)}
          zIndex={modalZIndices.dbBrowser}
          onFocus={() => bringToFront('dbBrowser')}
          initialPos={{ x: 100, y: 100 }}
          initialSize={{ width: 800, height: 600 }}
        >
          <DbBrowser 
            isOpen={true}
            onClose={() => setShowDbBrowser(false)}
          />
        </UniversalModal>
      )}

      {deleteConfirmId && (
        <UniversalModal
          id="deleteConfirm"
          title="Löschen bestätigen"
          isOpen={true}
          onClose={() => setDeleteConfirmId(null)}
          zIndex={22000} // Very high z-index
          onFocus={() => bringToFront('deleteConfirm')}
          initialPos={{ x: 300, y: 200 }}
          initialSize={{ width: 400, height: 250 }}
          minSize={{ width: 300, height: 200 }}
        >
          <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px', height: '100%' }}>
            <div>
              <h3 style={{ marginTop: 0 }}>Wirklich löschen?</h3>
              <p>Möchten Sie diese Konversation wirklich endgültig löschen oder ins Archiv verschieben?</p>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: 'auto' }}>
              <button 
                onClick={() => handleArchiveConversation(deleteConfirmId)}
                style={{
                  padding: '10px',
                  background: '#f1c40f',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: 'bold'
                }}
              >
                📦 Ins Archiv verschieben
              </button>
              <button 
                onClick={() => handleDeleteConversationPermanent(deleteConfirmId)}
                style={{
                  padding: '10px',
                  background: '#e74c3c',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: 'bold'
                }}
              >
                🗑️ Endgültig löschen
              </button>
              <button 
                onClick={() => setDeleteConfirmId(null)}
                style={{
                  padding: '10px',
                  background: '#ecf0f1',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Abbrechen
              </button>
            </div>
          </div>
        </UniversalModal>
      )}

      {showSettings && (
        <Settings 
          onClose={handleCloseSettings} 
          versionInfo={versionInfo}
        />
      )}
    </div>
  );
}

export default App;
