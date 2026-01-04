import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import Stage4 from './Stage4';
import WorkArea from './WorkArea';
import AuditViewer from './AuditViewer';
import './ChatInterface.css';

export default function ChatInterface({
  conversation,
  activeRevision,
  onSendMessage,
  onRestartConversation,
  isLoading,
  showStage4,
  humanFeedback,
  setHumanFeedback,
  onStage4Submit,
  onStage4Cancel,
  currentConfig,
  onOpenSettings,
  modelsMetadata,
  // New props for tools
  showBlueprint,
  setShowBlueprint,
  showResources,
  setShowResources,
  showPromptDb,
  setShowPromptDb,
  bringToFront,
  modalZIndices
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  const [showAudit, setShowAudit] = useState(false);

  // Filter messages to show only up to the active revision
  const getVisibleMessages = () => {
    if (!conversation) return [];
    
    const visibleMessages = [];
    let assistantCount = 0;
    
    for (const msg of conversation.messages) {
      if (msg.role === 'assistant') {
        if (assistantCount === activeRevision) {
          visibleMessages.push(msg);
          break; // Stop after showing the active revision
        }
        assistantCount++;
      } else if (msg.role === 'human_chairman') {
        // Only show human feedback if it leads up to the active revision
        if (assistantCount <= activeRevision) {
          visibleMessages.push(msg);
        }
      } else {
        visibleMessages.push(msg);
      }
    }
    return visibleMessages;
  };

  const visibleMessages = getVisibleMessages();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation, activeRevision]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  if (!conversation) {
    return (
      <div className="chat-interface">
        <div className="empty-state">
          <h2>Welcome to LLM Council</h2>
          <p>Create a new conversation to get started</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-interface mission-control">
      {currentConfig && (
        <div className="context-control-bar">
          <div className="active-board-info">
            <span className="board-badge">Mission Control</span>
            <span className="strategy-pill">{currentConfig.consensus_strategy}</span>
          </div>
          <div className="context-actions">
            <button className="audit-btn" onClick={() => setShowAudit(true)}>
              📜 Audit Log
            </button>
          </div>
        </div>
      )}

      <div className="messages-container">
        {visibleMessages.length === 0 ? (
          <div className="intro-message">
            <p>The Council is assembled. State your query.</p>
          </div>
        ) : (
          visibleMessages.map((msg, index) => (
            <div key={index} className={`message ${msg.role}`}>
              {msg.role === 'user' || msg.role === 'human_chairman' ? (
                <div className="user-message">
                  <div className="message-label">{msg.role === 'human_chairman' ? 'Human Feedback' : 'You'}</div>
                  <div className="message-content">
                    {msg.content}
                  </div>
                </div>
              ) : (
                <div className="assistant-message">
                  <div className="message-label">
                    LLM Council {conversation.messages.filter(m => m.role === 'assistant').length > 1 ? `(Revision ${conversation.messages.filter((m, i) => m.role === 'assistant' && conversation.messages.indexOf(msg) >= i).length})` : ''}
                  </div>

                  {/* Stage 1 */}
                  {msg.loading?.stage1 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Stage 1: Individual Responses</span>
                    </div>
                  )}
                  {msg.stage1 && <Stage1 responses={msg.stage1} />}

                  {/* Stage 2 */}
                  {msg.loading?.stage2 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Stage 2: Peer Ranking</span>
                    </div>
                  )}
                  {msg.stage2 && (
                    <Stage2
                      rankings={msg.stage2}
                      labelToModel={msg.metadata?.label_to_model}
                      aggregateRankings={msg.metadata?.aggregate_rankings}
                    />
                  )}

                  {/* Stage 3 */}
                  {msg.loading?.stage3 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Stage 3: Synthesis</span>
                    </div>
                  )}
                  {msg.stage3 && <Stage3 finalResponse={msg.stage3} />}

                  {/* Stage 4 - Human Chairman Review */}
                  {showStage4 && index === visibleMessages.length - 1 && (
                    <Stage4
                      humanFeedback={humanFeedback}
                      setHumanFeedback={setHumanFeedback}
                      onSubmit={(continueDiscussion) => onStage4Submit(continueDiscussion)}
                      isLoading={isLoading}
                      onCancel={onStage4Cancel}
                    />
                  )}
                </div>
              )}
            </div>
          ))
        )}

        {isLoading && !showStage4 && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <span>Council is deliberating...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <WorkArea 
        conversation={conversation}
        currentConfig={currentConfig}
        modelsMetadata={modelsMetadata}
        onPromptSelect={(content) => setInput(content)}
        // Pass down tool props
        showBlueprint={showBlueprint}
        setShowBlueprint={setShowBlueprint}
        showResources={showResources}
        setShowResources={setShowResources}
        showPromptDb={showPromptDb}
        setShowPromptDb={setShowPromptDb}
        bringToFront={bringToFront}
        modalZIndices={modalZIndices}
      />

      <div className="chat-input-area">
        {(conversation.messages.length === 0 || !showStage4) && (
          <form className="input-form" onSubmit={handleSubmit}>
            <textarea
              className="message-input"
              placeholder="Message the Council..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              rows={3}
            />
            <button
              type="submit"
              className="send-button"
              disabled={!input.trim() || isLoading}
            >
              Send
            </button>
          </form>
        )}
      </div>

      {showAudit && (
        <AuditViewer 
          conversationId={conversation.id} 
          onClose={() => setShowAudit(false)} 
        />
      )}
    </div>
  );
}
