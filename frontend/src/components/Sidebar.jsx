import { useState } from 'react';
import './Sidebar.css';

export default function Sidebar({
  conversations,
  currentConversationId,
  activeRevision,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onOpenSettings,
  versionInfo,
}) {
  const handleDeleteClick = async (e, id) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this conversation?')) {
      await onDeleteConversation(id);
    }
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
                
                {conv.revision_count > 1 && (
                  <div className="revision-badges">
                    {[...Array(conv.revision_count)].map((_, i) => (
                      <span 
                        key={i}
                        className={`revision-badge ${
                          conv.id === currentConversationId && i === activeRevision ? 'active' : ''
                        }`}
                        onClick={(e) => handleRevisionClick(e, conv.id, i)}
                        title={`Revision ${i + 1}`}
                      >
                        {i + 1}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
