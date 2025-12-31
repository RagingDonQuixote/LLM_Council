import { useState, useEffect } from 'react';
import { api } from '../api';
import './PromptExplorer.css';

export default function PromptExplorer({ onSelect, currentConfig }) {
  const [prompts, setPrompts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState('tiles'); // 'tiles' or 'fullscreen'
  const [activeTags, setActiveTags] = useState([]);
  const [filterLogic, setFilterLogic] = useState('OR'); // 'OR' or 'AND'
  const [searchQuery, setSearchQuery] = useState('');

  const allAvailableTags = [
    "stocks", "creative", "low thinking", "heavy thinking", 
    "coding", "visual input", "visual output"
  ];

  useEffect(() => {
    loadPrompts();
  }, []);

  const loadPrompts = async () => {
    try {
      const data = await api.listPrompts();
      setPrompts(data);
    } catch (error) {
      console.error('Failed to load prompts:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleTag = (tag) => {
    setActiveTags(prev => 
      prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
    );
  };

  const filteredPrompts = prompts.filter(p => {
    // Search filter
    if (searchQuery && !p.title.toLowerCase().includes(searchQuery.toLowerCase()) && 
        !p.content.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }

    // Tag filter
    if (activeTags.length === 0) return true;
    
    if (filterLogic === 'OR') {
      return activeTags.some(tag => p.tags?.includes(tag));
    } else {
      return activeTags.every(tag => p.tags?.includes(tag));
    }
  });

  const handleSelect = async (prompt) => {
    try {
      await api.trackPromptUsage(prompt.id);
      onSelect(prompt.content);
    } catch (error) {
      console.error('Failed to track prompt usage:', error);
      onSelect(prompt.content); // Still select even if tracking fails
    }
  };

  if (loading) return <div className="prompt-explorer-loading">Loading Prompt Library...</div>;

  return (
    <div className={`prompt-explorer ${viewMode}`}>
      <div className="explorer-header">
        <div className="explorer-title">
          <h3>Prompt Library</h3>
          <span className="count">{filteredPrompts.length} prompts found</span>
        </div>
        
        <div className="explorer-controls">
          <input 
            type="text" 
            placeholder="Search prompts..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
          <div className="view-toggles">
            <button 
              className={viewMode === 'tiles' ? 'active' : ''} 
              onClick={() => setViewMode('tiles')}
              title="Tile View"
            >
              田
            </button>
            <button 
              className={viewMode === 'fullscreen' ? 'active' : ''} 
              onClick={() => setViewMode('fullscreen')}
              title="Full View"
            >
              ⛶
            </button>
          </div>
        </div>
      </div>

      <div className="filter-bar">
        <div className="tags-row">
          {allAvailableTags.map(tag => (
            <button 
              key={tag}
              className={`tag-pill ${activeTags.includes(tag) ? 'active' : ''}`}
              onClick={() => toggleTag(tag)}
            >
              {tag}
            </button>
          ))}
        </div>
        <div className="logic-toggle">
          <span className="label">Filter:</span>
          <button 
            className={filterLogic === 'OR' ? 'active' : ''} 
            onClick={() => setFilterLogic('OR')}
          >
            OR
          </button>
          <button 
            className={filterLogic === 'AND' ? 'active' : ''} 
            onClick={() => setFilterLogic('AND')}
          >
            AND
          </button>
        </div>
      </div>

      <div className="prompts-container">
        {filteredPrompts.length === 0 ? (
          <div className="no-prompts">No prompts match your filters.</div>
        ) : (
          <div className={viewMode === 'tiles' ? 'prompts-grid' : 'prompts-list'}>
            {filteredPrompts.map(p => (
              <div key={p.id} className="explorer-card" onClick={() => handleSelect(p)}>
                <div className="card-header">
                  <h4>{p.title}</h4>
                  <div className="card-meta">
                    <span className="stars">{'★'.repeat(p.rating || 0)}</span>
                    <span className="usage">🔥 {p.usage_count || 0}</span>
                  </div>
                </div>
                <p className="preview">{p.content.substring(0, 120)}...</p>
                <div className="card-tags">
                  {p.tags?.map(t => (
                    <span key={t} className="tag-mini">{t}</span>
                  ))}
                </div>
                <div className="use-hint">Click to use</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
