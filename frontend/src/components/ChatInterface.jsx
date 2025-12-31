import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import Stage4 from './Stage4';
import PromptExplorer from './PromptExplorer';
import BlueprintTree from './BlueprintTree';
import ResourceMonitor from './ResourceMonitor';
import AuditViewer from './AuditViewer';
import './ChatInterface.css';

export default function ChatInterface({
  conversation,
  activeRevision,
  onSendMessage,
  isLoading,
  showStage4,
  humanFeedback,
  setHumanFeedback,
  onStage4Submit,
  onStage4Cancel,
  currentConfig,
  onOpenSettings,
  modelsMetadata
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  const [chatWidth, setChatWidth] = useState(45); // percentage
  const [blueprintWidth, setBlueprintWidth] = useState(30); // percentage
  const [showAudit, setShowAudit] = useState(false);
  const isResizingChat = useRef(false);
  const isResizingBlueprint = useRef(false);

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (isResizingChat.current) {
        const newWidth = (e.clientX / window.innerWidth) * 100;
        if (newWidth > 20 && newWidth < 70) {
          setChatWidth(newWidth);
        }
      } else if (isResizingBlueprint.current) {
        const chatPixelWidth = (chatWidth / 100) * window.innerWidth;
        const newBlueprintWidth = ((e.clientX - chatPixelWidth) / window.innerWidth) * 100;
        if (newBlueprintWidth > 15 && newBlueprintWidth < 50) {
          setBlueprintWidth(newBlueprintWidth);
        }
      }
    };

    const handleMouseUp = () => {
      isResizingChat.current = false;
      isResizingBlueprint.current = false;
      document.body.style.cursor = 'default';
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [chatWidth]);

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
            <div className="model-icons">
              {currentConfig.council_models?.map((m, i) => (
                <div key={i} className="model-mini-icon" title={m}>
                  {m.split('/').pop().substring(0, 2).toUpperCase()}
                </div>
              ))}
              <div className="model-mini-icon chairman" title={`Chairman: ${currentConfig.chairman_model}`}>
                👑
              </div>
            </div>
          </div>
          <div className="header-actions">
            <button className="edit-shortcut audit-btn" onClick={() => setShowAudit(true)} title="Mission Audit & Analysis">
              🔍 Audit
            </button>
            <button className="edit-shortcut" onClick={onOpenSettings} title="Edit Board Settings">
              ⚙️ Settings
            </button>
          </div>
        </div>
      )}

      <div className="mission-control-body">
        {/* Left Column: Chat */}
        <div className="column chat-column" style={{ width: `${chatWidth}%`, flex: 'none' }}>
          <div className="column-header">
            <h4>Council Communication</h4>
          </div>
          <div className="messages-container">
            {visibleMessages.length === 0 ? (
              <div className="stage0-container">
                <div className="empty-state">
                  <h2>Stage 0: Blueprinting</h2>
                  <p>Select a prompt or define your mission.</p>
                </div>
                <PromptExplorer 
                  onSelect={(content) => setInput(content)} 
                  currentConfig={currentConfig}
                />
              </div>
            ) : (
              visibleMessages.map((msg, index) => (
                <div key={index} className="message-group">
                  {msg.role === 'user' ? (
                    <div className="user-message">
                      <div className="message-label">You</div>
                      <div className="message-content">
                        <div className="markdown-content">
                          <ReactMarkdown>{msg.content}</ReactMarkdown>
                        </div>
                      </div>
                    </div>
                  ) : (msg.role === 'human_chairman' || msg.role === 'human_feedback') ? (
                    <div className="human-message">
                      <div className="message-label">Human Chairman Feedback</div>
                      <div className="message-content">
                        <div className="markdown-content">
                          <ReactMarkdown>{msg.content || msg.feedback}</ReactMarkdown>
                        </div>
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

        {/* Resizer 1 */}
        <div 
          className="resizer" 
          onMouseDown={() => {
            isResizingChat.current = true;
            document.body.style.cursor = 'col-resize';
          }}
        />

        {/* Middle Column: Event Tree */}
        <div className="column blueprint-column" style={{ width: `${blueprintWidth}%`, flex: 'none' }}>
          <div className="column-header">
            <h4>Council Blueprint</h4>
          </div>
          <BlueprintTree sessionState={conversation.session_state} />
          
          {conversation.session_state?.status === 'paused' && (
            <div className="breakpoint-notification">
              <div className="notification-content">
                <h5>🛑 Breakpoint Reached</h5>
                <p>The Council has reached a strategic milestone and awaits your approval to proceed.</p>
                <div className="notification-actions">
                  <button 
                    className="action-btn approve"
                    onClick={() => onSendMessage("Approved. Proceed with the blueprint.")}
                  >
                    Approve & Continue
                  </button>
                  <button 
                    className="action-btn reset"
                    onClick={() => onSendMessage("I want to reset the mission and refine the blueprint.")}
                  >
                    Reset & Refine
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Resizer 2 */}
        <div 
          className="resizer" 
          onMouseDown={() => {
            isResizingBlueprint.current = true;
            document.body.style.cursor = 'col-resize';
          }}
        />

        {/* Right Column: Resources */}
        <div className="column resources-column" style={{ flex: 1 }}>
          <div className="column-header">
            <h4>Resource Monitor</h4>
          </div>
          <ResourceMonitor config={currentConfig} modelsMetadata={modelsMetadata} />
        </div>
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
