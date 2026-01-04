import { useState } from 'react';
import './Sidebar.css';

export default function Sidebar({
  conversations,
  currentConversationId,
  activeRevision,
  onSelectConversation,
  onNewConversation,
  onArchiveConversation,
  onDeleteConversation,
  onRestartConversation,
  onOpenSettings,
  versionInfo,
  councilConfig,
  modelsMetadata,
}) {
  const [showCouncilStatus, setShowCouncilStatus] = useState(true);

  const formatPrice = (price) => {
    if (!price || price === 0) return 'Free';
    return `$${(price * 1000000).toFixed(1)}/1M`;
  };

  const getModelShortName = (modelId) => {
    return modelId.split('/')[1] || modelId;
  };

  const handleDeleteClick = (e, id) => {
    e.stopPropagation();
    e.preventDefault(); 
    console.log("Delete requested for:", id); 
    onDeleteConversation(id); // Now calls onRequestDelete from App
  };

  const handleCopyPrompt = (e, conversation) => {
    e.stopPropagation();
    const lastMessage = conversation.messages?.[conversation.messages.length - 1];
    if (lastMessage?.role === 'user') {
      navigator.clipboard.writeText(lastMessage.content).then(() => {
        // Could show a toast notification here
        console.log('Prompt copied to clipboard');
      });
    }
  };

  const handleChangeRating = (e, conversation) => {
    e.stopPropagation();
    const newRating = prompt('Rate this conversation (0-5):', '0');
    if (newRating !== null) {
      const rating = parseInt(newRating);
      if (rating >= 0 && rating <= 5) {
        // TODO: Implement rating update API call
        console.log('Update rating for', conversation.id, 'to', rating);
      }
    }
  };

  const handleRevisionClick = (e, id, index) => {
    e.stopPropagation();
    onSelectConversation(id, index);
  };

  const handleRestartClick = (e, id) => {
    e.stopPropagation();
    onRestartConversation(id);
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1>{versionInfo?.printname || 'LLM Council'}</h1>
        <div className="header-buttons">
          <button className="settings-btn" onClick={onOpenSettings}>
            ⚙️ Settings
          </button>
          <button className="new-conversation-btn" onClick={onNewConversation}>
            + New Conversation
          </button>
        </div>
      </div>

      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="no-conversations">No conversations yet</div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${
                conv.id === currentConversationId ? 'active' : ''
              }`}
              onClick={() => onSelectConversation(conv.id)}
            >
              <div className="conversation-header">
                <div className="conversation-title">
                  {conv.title || 'New Conversation'}
                </div>
                <div className="conversation-icon-bar">
                  <button
                    className="icon-btn"
                    onClick={(e) => handleChangeRating(e, conv)}
                    title="Change rating"
                  >
                    ⭐
                  </button>
                  <button
                    className="icon-btn restart-btn"
                    onClick={(e) => handleRestartClick(e, conv.id)}
                    title="Restart conversation"
                  >
                    🔄
                  </button>
                  <button
                    className="icon-btn delete-btn"
                    onClick={(e) => handleDeleteClick(e, conv.id)}
                    title="Delete conversation"
                  >
                    🗑️
                  </button>
                </div>
              </div>
              
              <div className="conversation-footer">
                <div className="conversation-meta">
                  {new Date(conv.created_at).toLocaleDateString()}
                </div>
                
                {conv.metadata?.revision_count > 0 && (
                  <div className="revision-badges">
                    {[...Array(conv.metadata.revision_count + 1)].map((_, i) => (
                      <span 
                        key={i}
                        className={`revision-badge ${
                          conv.id === currentConversationId && i === activeRevision ? 'active' : ''
                        }`}
                        onClick={(e) => handleRevisionClick(e, conv.id, i)}
                        title={i === 0 ? 'Original' : `Revision ${i}`}
                      >
                        {i === 0 ? 'O' : `R${i}`}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      <div className="sidebar-footer">
        <div 
          className="council-status-header" 
          onClick={() => setShowCouncilStatus(!showCouncilStatus)}
        >
          <span>Council Status {showCouncilStatus ? '▼' : '▲'}</span>
          <span className="strategy-badge">{councilConfig?.consensus_strategy === 'chairman_cut' ? 'Chairman-Cut' : 'Borda'}</span>
        </div>

        {showCouncilStatus && councilConfig && (
          <div className="council-status-content">
            <div className="status-section">
              <div className="status-label">Council Members</div>
              <div className="status-models">
                {councilConfig.council_models.map(modelId => {
                  const meta = modelsMetadata[modelId];
                  return (
                    <div key={modelId} className="status-model-item" title={modelId}>
                      <span className="model-short-name">{getModelShortName(modelId)}</span>
                      <div className="model-stats">
                        <span className="price-tag">{formatPrice(meta?.pricing?.prompt)}</span>
                        {meta?.description?.toLowerCase().includes('thinking') && <span className="stat-cap" title="Thinking">🧠</span>}
                        {meta?.description?.toLowerCase().includes('tool') && <span className="stat-cap" title="Tools">🛠️</span>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="status-section">
              <div className="status-label">Chairman</div>
              <div className="status-model-item chairman" title={councilConfig.chairman_model}>
                <span className="model-short-name">{getModelShortName(councilConfig.chairman_model)}</span>
                <div className="model-stats">
                  <span className="price-tag">{formatPrice(modelsMetadata[councilConfig.chairman_model]?.pricing?.prompt)}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
