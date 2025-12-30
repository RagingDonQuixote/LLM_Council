import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import Settings from './components/Settings';
import { api } from './api';
import './App.css';

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [activeRevision, setActiveRevision] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showStage4, setShowStage4] = useState(false);
  const [humanFeedback, setHumanFeedback] = useState('');

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

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

  const handleDeleteConversation = async (id) => {
    try {
      await api.deleteConversation(id);
      setConversations(conversations.filter((c) => c.id !== id));
      if (currentConversationId === id) {
        setCurrentConversationId(null);
        setCurrentConversation(null);
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
      alert('Failed to delete conversation');
    }
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
  };

  const handleHumanFeedbackSubmit = async (continueDiscussion) => {
    if (!currentConversationId) return;

    setIsLoading(true);
    try {
      const result = await api.submitHumanFeedback(currentConversationId, humanFeedback, continueDiscussion);

      if (result.continued) {
        // Reload conversation to show new stages
        loadConversation(currentConversationId);
        // Reset for potential next iteration
        setShowStage4(false);
        setHumanFeedback('');
      } else {
        // End session
        handleEndSession();
        setShowStage4(false);
        setHumanFeedback('');
      }
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEndSession = () => {
    const rating = prompt('Please rate this council session (0-5 stars):', '5');
    if (rating !== null) {
      const numRating = parseInt(rating);
      if (numRating >= 0 && numRating <= 5) {
        api.endSession(currentConversationId, numRating).then(() => {
          alert('Session ended. Thank you for your feedback!');
          loadConversations();
        });
      }
    }
  };

  const handleStage4Submit = (continueDiscussion) => {
    handleHumanFeedbackSubmit(continueDiscussion);
  };

  const handleStage4Cancel = () => {
    setShowStage4(false);
    setHumanFeedback('');
  };

  const handleSendMessage = async (content) => {
    if (!currentConversationId) return;

    setIsLoading(true);
    try {
      // Optimistically add user message to UI
      const userMessage = { role: 'user', content };
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage],
      }));

      // Create a partial assistant message that will be updated progressively
      const assistantMessage = {
        role: 'assistant',
        stage1: null,
        stage2: null,
        stage3: null,
        stage4: null,
        metadata: null,
        loading: {
          stage1: false,
          stage2: false,
          stage3: false,
          stage4: false,
        },
      };

      // Add the partial assistant message
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
      }));

      // Send message with streaming
      await api.sendMessageStream(currentConversationId, content, (eventType, event) => {
        switch (eventType) {
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
            // Show Stage 4 instead of modal
            setShowStage4(true);
            setIsLoading(false);
            break;

          case 'title_complete':
            // Reload conversations to get updated title
            loadConversations();
            break;

          case 'complete':
            // Stream complete, reload conversations list
            loadConversations();
            setIsLoading(false);
            break;

          case 'error':
            console.error('Stream error:', event.message);
            setIsLoading(false);
            break;

          default:
            console.log('Unknown event type:', eventType);
        }
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      // Remove optimistic messages on error
      setCurrentConversation((prev) => ({
        ...prev,
        messages: prev.messages.slice(0, -2),
      }));
      setIsLoading(false);
    }
  };

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        activeRevision={activeRevision}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        onOpenSettings={handleOpenSettings}
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
      />
      {showSettings && (
        <Settings onClose={handleCloseSettings} />
      )}
    </div>
  );
}

export default App;
