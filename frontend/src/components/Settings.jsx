import { useState, useEffect, useRef } from 'react';
import { api } from '../api';
import SearchableSelect from './SearchableSelect';
import './Settings.css';
import './UnifiedModelSelection.css';

function PromptManager({ prompts, onSave, onDelete }) {
  const [editingPrompt, setEditingPrompt] = useState(null);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [tags, setTags] = useState([]);
  const [rating, setRating] = useState(0);

  const availableTags = [
    "stocks", "creative", "low thinking", "heavy thinking", 
    "coding", "visual input", "visual output"
  ];

  const handleEdit = (prompt) => {
    setEditingPrompt(prompt);
    setTitle(prompt.title);
    setContent(prompt.content);
    setTags(prompt.tags || []);
    setRating(prompt.rating || 0);
  };

  const handleAddNew = () => {
    setEditingPrompt({ id: `p_${Date.now()}` });
    setTitle('');
    setContent('');
    setTags([]);
    setRating(0);
  };

  const handleSave = () => {
    if (!title || !content) return;
    onSave({
      id: editingPrompt.id,
      title,
      content,
      tags,
      rating,
      usage_count: editingPrompt.usage_count || 0,
      created_at: editingPrompt.created_at
    });
    setEditingPrompt(null);
  };

  const handleRate = (id, newRating) => {
    const prompt = prompts.find(p => p.id === id);
    if (prompt) {
      onSave({ ...prompt, rating: newRating });
    }
  };

  const toggleTag = (tag) => {
    if (tags.includes(tag)) {
      setTags(tags.filter(t => t !== tag));
    } else {
      setTags([...tags, tag]);
    }
  };

  return (
    <div className="prompt-manager">
      {!editingPrompt ? (
        <>
          <div className="prompt-list-header">
            <h3>Prompt Library</h3>
            <button className="add-prompt-btn" onClick={handleAddNew}>+ Add Prompt</button>
          </div>
          <div className="prompt-grid">
            {prompts.map(p => (
              <div key={p.id} className="prompt-card">
                <div className="prompt-card-header">
                  <div className="title-area">
                    <h4>{p.title}</h4>
                    <div className="prompt-meta-mini">
                      <span className="rating">{'★'.repeat(p.rating || 0)}{'☆'.repeat(5 - (p.rating || 0))}</span>
                      <span className="usage">Used: {p.usage_count || 0}</span>
                    </div>
                  </div>
                  <div className="prompt-actions">
                    <button onClick={() => handleEdit(p)}>Edit</button>
                    <button onClick={() => onDelete(p.id)} className="delete">Delete</button>
                  </div>
                </div>
                <p className="prompt-preview">{p.content.substring(0, 100)}{p.content.length > 100 ? '...' : ''}</p>
                <div className="prompt-tags">
                  {p.tags?.map(t => (
                    <span key={t} className="prompt-tag-pill">{t}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="prompt-editor">
          <h3>{editingPrompt.id.startsWith('p_') && !prompts.find(p => p.id === editingPrompt.id) ? 'Add Prompt' : 'Edit Prompt'}</h3>
          <div className="editor-field">
            <label>Title:</label>
            <input 
              type="text" 
              value={title} 
              onChange={(e) => setTitle(e.target.value)} 
              placeholder="Prompt Title"
            />
          </div>
          <div className="editor-field">
            <label>Content:</label>
            <textarea 
              value={content} 
              onChange={(e) => setContent(e.target.value)} 
              placeholder="Prompt content... use [Variable] for placeholders."
              className="prompt-textarea"
            />
          </div>
          <div className="editor-field">
            <label>Rating:</label>
            <div className="rating-input">
              {[1, 2, 3, 4, 5].map(star => (
                <span 
                  key={star} 
                  className={`star ${rating >= star ? 'filled' : ''}`}
                  onClick={() => setRating(star)}
                >
                  {rating >= star ? '★' : '☆'}
                </span>
              ))}
            </div>
          </div>
          <div className="editor-field">
            <label>Tags:</label>
            <div className="tag-selector">
              {availableTags.map(tag => (
                <button 
                  key={tag} 
                  className={`tag-btn ${tags.includes(tag) ? 'active' : ''}`}
                  onClick={() => toggleTag(tag)}
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>
          <div className="editor-actions">
            <button className="cancel-btn" onClick={() => setEditingPrompt(null)}>Cancel</button>
            <button className="save-prompt-btn" onClick={handleSave}>Save Prompt</button>
          </div>
        </div>
      )}
    </div>
  );
}

function Settings({ onClose, versionInfo }) {
  const [config, setConfig] = useState(null);
  const [availableModels, setAvailableModels] = useState([]);
  const [modelsMetadata, setModelsMetadata] = useState({});
  const [templates, setTemplates] = useState([]);
  const [boards, setBoards] = useState([]);
  const [prompts, setPrompts] = useState([]);
  
  // Unified model system state
  const [baseModels, setBaseModels] = useState([]);
  const [selectedBaseModel, setSelectedBaseModel] = useState(null);
  const [modelVariants, setModelVariants] = useState([]);
  const [selectedVariant, setSelectedVariant] = useState(null);
  const [unifiedModelsLoading, setUnifiedModelsLoading] = useState(false);
  const [isTestingLiveLatency, setIsTestingLiveLatency] = useState(false);
  const [currentBoardId, setCurrentBoardId] = useState(null);
  const [boardDescription, setBoardDescription] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testingModel, setTestingModel] = useState(null);
  const [latencies, setLatencies] = useState({});
  const [showFreeOnly, setShowFreeOnly] = useState(true);
  const [filters, setFilters] = useState({
    free: true,
    thinking: false,
    vision: false,
    tools: false
  });
  const [activeTab, setActiveTab] = useState('board');
  const [tileModes, setTileModes] = useState({}); // 'main' or 'sub' per tile index
  const [chairmanMode, setChairmanMode] = useState('main');

  // API Key Management State
  const [apiKeys, setApiKeys] = useState([]);
  const [newKey, setNewKey] = useState({
    provider: 'openrouter',
    key_value: '',
    description: '',
    limit_amount: '',
    limit_reset: ''
  });
  const [isAddingKey, setIsAddingKey] = useState(false);
  const [checkingKey, setCheckingKey] = useState(null);

  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [resizeStart, setResizeStart] = useState({ x: 0, y: 0, width: 0, height: 0 });
  const modalRef = useRef(null);
  const headerRef = useRef(null);

  // Persistence of styles across re-renders
  const [modalStyle, setModalStyle] = useState({});

  const [failLists, setFailLists] = useState([]);
  const [isTestingAll, setIsTestingAll] = useState(false);

  useEffect(() => {
    if (modalRef.current && (isDragging || isResizing)) {
      setModalStyle({
        width: modalRef.current.style.width,
        height: modalRef.current.style.height,
        left: modalRef.current.style.left,
        top: modalRef.current.style.top,
        right: modalRef.current.style.right,
        bottom: modalRef.current.style.bottom,
        transform: modalRef.current.style.transform,
        maxWidth: modalRef.current.style.maxWidth,
        maxHeight: modalRef.current.style.maxHeight
      });
    }
  }, [isDragging, isResizing]);

  useEffect(() => {
    loadData();
  }, []); // Only once on mount

  // Use a separate effect for mouse events to avoid re-binding on every state change
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (isDragging && modalRef.current) {
        const newX = Math.max(0, Math.min(window.innerWidth - modalRef.current.offsetWidth, e.clientX - dragOffset.x));
        const newY = Math.max(0, Math.min(window.innerHeight - modalRef.current.offsetHeight, e.clientY - dragOffset.y));
        modalRef.current.style.left = `${newX}px`;
        modalRef.current.style.top = `${newY}px`;
        modalRef.current.style.right = 'auto';
        modalRef.current.style.bottom = 'auto';
        modalRef.current.style.transform = 'none';
      } else if (isResizing && modalRef.current) {
        const deltaX = e.clientX - resizeStart.x;
        const deltaY = e.clientY - resizeStart.y;
        const newWidth = Math.max(600, Math.min(window.innerWidth * 0.9, resizeStart.width + deltaX));
        const newHeight = Math.max(400, Math.min(window.innerHeight * 0.8, resizeStart.height + deltaY));
        modalRef.current.style.width = `${newWidth}px`;
        modalRef.current.style.height = `${newHeight}px`;
        modalRef.current.style.maxHeight = 'none';
        modalRef.current.style.maxWidth = 'none';
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      setIsResizing(false);
    };

    const handleMouseLeave = () => {
      setIsDragging(false);
      setIsResizing(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [isDragging, isResizing, dragOffset, resizeStart]);

  const loadData = async () => {
    try {
      const [configData, modelsData, templatesData, boardsData, promptsData, failListsData, apiKeysData] = await Promise.all([
        api.getConfig(),
        api.getAvailableModels(),
        api.listTemplates(),
        api.listBoards(),
        api.listPrompts(),
        api.getFailLists(),
        api.listApiKeys()
      ]);
      
      setConfig(configData);
      setAvailableModels(modelsData.models);
      setTemplates(templatesData);
      setBoards(boardsData);
      setPrompts(promptsData);
      setFailLists(failListsData);
      setApiKeys(apiKeysData);
      
      // Create a map for quick lookup
      const metadataMap = {};
      modelsData.models.forEach(m => {
        metadataMap[m.id] = m;
      });
      setModelsMetadata(metadataMap);
      
      // Load unified model data
      await loadUnifiedModelData();
      
    } catch (error) {
      console.error('Failed to load settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadUnifiedModelData = async () => {
    try {
      setUnifiedModelsLoading(true);
      // Fetch more models to ensure we see all of them
      const baseModelsData = await api.getBaseModels(null, 1000);
      setBaseModels(baseModelsData);
    } catch (error) {
      console.error('Failed to load unified models:', error);
      // Fallback to empty array if unified models not available
      setBaseModels([]);
    } finally {
      setUnifiedModelsLoading(false);
    }
  };

  // Handler for base model selection
  const handleBaseModelChange = async (baseModelId) => {
    setSelectedBaseModel(baseModelId);
    if (baseModelId) {
      try {
        setUnifiedModelsLoading(true);
        const variants = await api.getModelVariants(baseModelId);
        
        // Preprocess variants for better display
        const processedVariants = variants.map(v => ({
          ...v,
          // Create a composite display name
          formatted_name: `${v.access_provider_short || v.access_provider_id}: ${v.variant_name} ${v.latency_live ? `(Live: ${Math.round(v.latency_live)}ms)` : (v.latency_ms ? `(${Math.round(v.latency_ms)}ms)` : '')}`
        }));
        
        setModelVariants(processedVariants);
        // Auto-select the first variant if available
        if (processedVariants.length > 0) {
          setSelectedVariant(processedVariants[0].id);
        }
      } catch (error) {
        console.error('Failed to load model variants:', error);
        setModelVariants([]);
      } finally {
        setUnifiedModelsLoading(false);
      }
    } else {
      setModelVariants([]);
      setSelectedVariant(null);
    }
  };

  // Handler for variant selection
  const handleVariantChange = (variantId) => {
    setSelectedVariant(variantId);
  };

  const handleTestLiveLatency = async () => {
    if (!selectedVariant) return;
    
    setIsTestingLiveLatency(true);
    try {
      const result = await api.testUnifiedModelLatency(selectedVariant);
      if (result.status === 'success') {
        // Refresh the variant data to show updated latency
        const variants = await api.getModelVariants(selectedBaseModel);
        setModelVariants(variants);
      } else {
        alert('Live latency test failed: ' + (result.message || 'Unknown error'));
      }
    } catch (error) {
      console.error('Failed to test live latency:', error);
      alert('Failed to test live latency: ' + error.message);
    } finally {
      setIsTestingLiveLatency(false);
    }
  };

  const addSelectedToCouncil = () => {
    if (!selectedVariant) return;
    if (config.council_models.length >= 6) {
      alert('Maximum 6 council members allowed.');
      return;
    }
    setConfig(prev => ({
      ...prev,
      council_models: [...prev.council_models, selectedVariant]
    }));
  };

  const setSelectedAsChairman = () => {
    if (!selectedVariant) return;
    setConfig(prev => ({
      ...prev,
      chairman_model: selectedVariant
    }));
  };

  // Refresh unified models
  const handleRefreshModels = async () => {
    try {
      setUnifiedModelsLoading(true);
      const result = await api.refreshUnifiedModels();
      await loadUnifiedModelData();
      
      const count = result.models_refreshed || 0;
      alert(`Models refreshed successfully! ${count} models updated in database.`);
    } catch (error) {
      console.error('Failed to refresh models:', error);
      alert('Failed to refresh models: ' + (error.message || 'Unknown error'));
    } finally {
      setUnifiedModelsLoading(false);
    }
  };

  const handleTestAll = async () => {
    setIsTestingAll(true);
    try {
      // Use currently filtered models to respect user filters if desired, 
      // or all models as the user requested ("gesetzte Filter beachten!").
      const modelIds = filteredModels.map(m => m.id);
      const result = await api.testModelsAvailability(modelIds);
      alert(`Test completed! Failed models: ${result.failed_count}/${result.total_tested}`);
      const updatedFailLists = await api.getFailLists();
      setFailLists(updatedFailLists);
      
      // Refresh available models to see the effects
      const updatedModels = await api.getAvailableModels();
      setAvailableModels(updatedModels.models);
    } catch (error) {
      console.error('Failed to test all models:', error);
      alert('Failed to test models');
    } finally {
      setIsTestingAll(false);
    }
  };

  const handleActivateFailList = async (id) => {
    try {
      await api.activateFailList(id);
      const updatedFailLists = await api.getFailLists();
      setFailLists(updatedFailLists);
      // Refresh available models as well since they might be filtered now
      const modelsData = await api.getAvailableModels();
      setAvailableModels(modelsData.models);
    } catch (error) {
      console.error('Failed to activate fail list:', error);
      alert('Failed to activate fail list');
    }
  };

  // API Key Handlers
  const handleSaveKey = async () => {
    try {
      await api.saveApiKey({
        ...newKey,
        limit_amount: newKey.limit_amount ? parseFloat(newKey.limit_amount) : null
      });
      setIsAddingKey(false);
      setNewKey({ provider: 'openrouter', key_value: '', description: '', limit_amount: '', limit_reset: '' });
      const updatedKeys = await api.listApiKeys();
      setApiKeys(updatedKeys);
      return true;
    } catch (err) {
      alert('Failed to save key');
      return false;
    }
  };

  const handleDeleteKey = async (id) => {
    if (!confirm('Delete this API key?')) return;
    try {
      await api.deleteApiKey(id);
      const updatedKeys = await api.listApiKeys();
      setApiKeys(updatedKeys);
    } catch (err) {
      alert('Failed to delete key');
    }
  };

  const handleCheckKey = async (id) => {
    setCheckingKey(id);
    try {
      const res = await api.checkApiKey(id);
      if (res.status === 'success') {
        const updatedKeys = await api.listApiKeys();
        setApiKeys(updatedKeys);
      } else {
        alert(`Check failed: ${res.message}`);
      }
    } catch (err) {
      alert('Check failed');
    } finally {
      setCheckingKey(null);
    }
  };

  // Drag handlers
  const handleMouseDown = (e) => {
    // Only start dragging if clicking on header and not on interactive elements
    if (headerRef.current && headerRef.current.contains(e.target) &&
        !e.target.closest('button') && !e.target.closest('select') && !e.target.closest('input')) {
      e.preventDefault();
      setIsDragging(true);
      const rect = modalRef.current.getBoundingClientRect();
      setDragOffset({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
      });
    }
  };

  // Resize handler
  const handleResizeMouseDown = (e) => {
    e.preventDefault();
    setIsResizing(true);
    const rect = modalRef.current.getBoundingClientRect();
    setResizeStart({
      x: e.clientX,
      y: e.clientY,
      width: rect.width,
      height: rect.height
    });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // Check for unsaved API Key
      if (activeTab === 'api-keys' && newKey.key_value) {
          const success = await handleSaveKey();
          if (!success) {
              setSaving(false);
              return; // Abort if key save failed
          }
      }

      await api.updateConfig(config);
      alert('Settings saved successfully!');
      onClose();
    } catch (error) {
      console.error('Failed to save settings:', error);
      alert('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const getKeyForModel = (modelId) => {
    const meta = modelsMetadata[modelId];
    const isFreeModel = meta?.free || (modelId && (modelId.includes(':free') || modelId.toLowerCase().includes('free')));
    
    let keyToUse = null;
    
    if (isFreeModel) {
        keyToUse = apiKeys.find(k => 
            k.provider === 'openrouter' && 
            (k.label?.toLowerCase().includes('free') || k.description?.toLowerCase().includes('free') || k.description?.includes('$0'))
        );
        if (!keyToUse && apiKeys.length > 0) keyToUse = apiKeys[0];
    } else {
        const paidKeys = apiKeys.filter(k => 
            k.provider === 'openrouter' && 
            !(k.label?.toLowerCase().includes('free') || k.description?.toLowerCase().includes('free') || k.description?.includes('$0'))
        );
        keyToUse = paidKeys.find(k => k.limit_remaining > 0);
        if (!keyToUse && paidKeys.length > 0) keyToUse = paidKeys[0];
        if (!keyToUse && apiKeys.length > 0) keyToUse = apiKeys[0];
    }
    return keyToUse;
  };

  const handleTestLatency = async (modelId) => {
    setTestingModel(modelId);
    try {
      const keyToUse = getKeyForModel(modelId);
      const apiKey = keyToUse ? keyToUse.key_value : null;
      const result = await api.testLatency(modelId, apiKey);
      setLatencies(prev => ({
        ...prev,
        [modelId]: result.status === 'ok' ? `${result.latency}s` : 'Failed'
      }));
    } catch (error) {
      console.error('Failed to test latency:', error);
      setLatencies(prev => ({
        ...prev,
        [modelId]: 'Error'
      }));
    } finally {
      setTestingModel(null);
    }
  };

  const addCouncilModel = () => {
    if (config.council_models.length >= 6) {
      alert('Maximum 6 council members allowed.');
      return;
    }
    const defaultModel = filteredModels.length > 0 ? filteredModels[0].id : (availableModels[0]?.id || '');
    setConfig(prev => ({
      ...prev,
      council_models: [...prev.council_models, defaultModel]
    }));
  };

  const removeCouncilModel = (index) => {
    if (config.council_models.length <= 1) {
      alert('Minimum 1 council member required.');
      return;
    }
    setConfig(prev => ({
      ...prev,
      council_models: prev.council_models.filter((_, i) => i !== index)
    }));
  };

  const updateCouncilModel = (index, value) => {
    const oldModel = config.council_models[index];
    setConfig(prev => {
      const newSubstitutes = { ...(prev.substitute_models || {}) };
      if (oldModel && newSubstitutes[oldModel]) {
        newSubstitutes[value] = newSubstitutes[oldModel];
        delete newSubstitutes[oldModel];
      }
      return {
        ...prev,
        council_models: prev.council_models.map((model, i) =>
          i === index ? value : model
        ),
        substitute_models: newSubstitutes
      };
    });
  };

  const updateSubstituteModel = (modelId, substituteId) => {
    setConfig(prev => ({
      ...prev,
      substitute_models: {
        ...(prev.substitute_models || {}),
        [modelId]: substituteId
      }
    }));
  };

  const filteredModels = availableModels.filter(m => {
    if (filters.free && !m.free) return false;
    if (filters.thinking && !m.capabilities?.thinking) return false;
    if (filters.vision && !m.capabilities?.vision) return false;
    if (filters.tools && !m.capabilities?.tools) return false;
    return true;
  });

  const updateFilter = (filterKey, value) => {
    setFilters(prev => ({
      ...prev,
      [filterKey]: value
    }));
  };

  const updateChairmanModel = (value) => {
    setConfig(prev => ({
      ...prev,
      chairman_model: value
    }));
  };

  const updatePersonality = (model, value) => {
    setConfig(prev => ({
      ...prev,
      model_personalities: {
        ...prev.model_personalities,
        [model]: value
      }
    }));
  };

  const updateStrategy = (value) => {
    setConfig(prev => ({
      ...prev,
      consensus_strategy: value
    }));
  };

  const generateAutoDescription = (currentConfig) => {
    if (!currentConfig || !currentConfig.council_models) return '';
    
    const getModelLabel = (id) => {
      const meta = modelsMetadata[id];
      if (!meta) return id.split('/').pop();
      
      const caps = [];
      if (meta.capabilities?.thinking) caps.push('Thinking');
      if (meta.capabilities?.vision) caps.push('Vision');
      if (meta.capabilities?.tools) caps.push('Tools');
      
      return `${meta.name}${caps.length > 0 ? ` [${caps.join(', ')}]` : ''}`;
    };

    const councilNames = currentConfig.council_models.map(getModelLabel);
    const chairmanName = currentConfig.chairman_model ? getModelLabel(currentConfig.chairman_model) : 'None';

    return `Council: ${councilNames.join(', ')}\nChairman: ${chairmanName}`;
  };

  useEffect(() => {
    if (config && !boardDescription) {
      setBoardDescription(generateAutoDescription(config));
    }
  }, [config, modelsMetadata]);

  const handleSaveBoard = async (saveAs = false) => {
    const name = prompt('Enter a name for this AI Board:', currentBoardId && !saveAs ? boards.find(b => b.id === currentBoardId)?.name : '');
    if (!name) return;

    const boardId = saveAs || !currentBoardId ? `board_${Date.now()}` : currentBoardId;
    
    const boardData = {
      id: boardId,
      name: name,
      description: boardDescription,
      config: config,
      usage_count: saveAs || !currentBoardId ? 0 : (boards.find(b => b.id === currentBoardId)?.usage_count || 0)
    };

    try {
      setSaving(true);
      await api.saveBoard(boardData);
      setCurrentBoardId(boardId);
      const updatedBoards = await api.listBoards();
      setBoards(updatedBoards);
      alert('AI Board saved!');
    } catch (error) {
      console.error('Failed to save board:', error);
      alert('Failed to save board');
    } finally {
      setSaving(false);
    }
  };

  const handleLoadBoard = (boardId) => {
    const board = boards.find(b => b.id === boardId);
    if (!board) return;

    setConfig(board.config);
    setBoardDescription(board.description);
    setCurrentBoardId(board.id);
    
    // Increment usage count
    api.saveBoard({ id: board.id, usage_only: true });
    
    // Update local state for stats
    setBoards(prev => prev.map(b => b.id === boardId ? { ...b, usage_count: b.usage_count + 1 } : b));
  };

  const handleSavePrompt = async (promptData) => {
    try {
      setSaving(true);
      await api.savePrompt(promptData);
      const updatedPrompts = await api.listPrompts();
      setPrompts(updatedPrompts);
    } catch (error) {
      console.error('Failed to save prompt:', error);
      alert('Failed to save prompt');
    } finally {
      setSaving(false);
    }
  };

  const handleDeletePrompt = async (promptId) => {
    if (!confirm('Are you sure you want to delete this prompt?')) return;
    try {
      setSaving(true);
      await api.deletePrompt(promptId);
      const updatedPrompts = await api.listPrompts();
      setPrompts(updatedPrompts);
    } catch (error) {
      console.error('Failed to delete prompt:', error);
      alert('Failed to delete prompt');
    } finally {
      setSaving(false);
    }
  };

  const createDefaultPrompts = async () => {
    const defaultPrompts = [
      {
        id: 'p_stocks',
        title: 'Stock Analysis',
        content: 'Analyze the current performance and future outlook of [Stock Name]. Consider financial metrics, market trends, and recent news.',
        tags: ['stocks', 'heavy thinking']
      },
      {
        id: 'p_creative',
        title: 'Creative Writing',
        content: 'Write a short story about [Topic] in the style of [Author]. Focus on character development and atmospheric descriptions.',
        tags: ['creative', 'low thinking']
      },
      {
        id: 'p_coding',
        title: 'Code Refactoring',
        content: 'Review and refactor the following [Language] code for better readability, performance, and best practices:\n\n```\n[Code]\n```',
        tags: ['coding', 'heavy thinking']
      },
      {
        id: 'p_vision',
        title: 'Image Description',
        content: 'Describe the contents of this image in detail, focusing on [Specific Aspect].',
        tags: ['visual input']
      }
    ];

    for (const p of defaultPrompts) {
      await api.savePrompt(p);
    }
    const updatedPrompts = await api.listPrompts();
    setPrompts(updatedPrompts);
  };

  useEffect(() => {
    if (!loading && prompts.length === 0) {
      createDefaultPrompts();
    }
  }, [loading, prompts.length]);

  const applyTemplate = (templateId) => {
    const template = templates.find(t => t.id === templateId);
    if (!template) return;

    setConfig(prev => ({
      ...prev,
      council_models: template.council_models,
      chairman_model: template.chairman_model,
      model_personalities: template.model_personalities || prev.model_personalities,
      consensus_strategy: template.consensus_strategy || prev.consensus_strategy
    }));
  };

  const formatPrice = (price) => {
    if (!price || price === 0) return 'Free';
    return `$${(price * 1000000).toFixed(2)}/1M`;
  };

  const [selectedFailListId, setSelectedFailListId] = useState('');

  useEffect(() => {
    if (failLists.length > 0) {
      const active = failLists.find(f => f.active);
      if (active) setSelectedFailListId(active.id);
    }
  }, [failLists]);

  const handleFailListChange = (id) => {
    setSelectedFailListId(id);
    handleActivateFailList(id);
  };

  const activeFailList = failLists.find(f => f.id === parseInt(selectedFailListId));

  const getModelPreview = (modelId) => {
    const meta = modelsMetadata[modelId];
    if (!meta) return <div className="no-preview">No metadata available</div>;
    return (
      <div className="tile-preview">
        {meta.description && (
          <p className="tile-model-desc">{meta.description}</p>
        )}
        <div className="preview-details-grid">
          <div className="preview-stat">
            <span className="label">Context:</span>
            <span className="value">{(meta.context_length / 1024).toFixed(0)}k</span>
          </div>
          <div className="preview-stat">
            <span className="label">Price (In/Out):</span>
            <span className="value">{formatPrice(meta.pricing?.prompt)} / {formatPrice(meta.pricing?.completion)}</span>
          </div>
        </div>
        <div className="preview-caps">
          {meta.capabilities?.thinking && <span className="cap-mini thinking" title="Thinking">Thinking</span>}
          {meta.capabilities?.vision && <span className="cap-mini vision" title="Vision">Vision</span>}
          {meta.capabilities?.tools && <span className="cap-mini tools" title="Tools">Tools</span>}
          {meta.free && <span className="cap-mini free" title="Free">Free</span>}
        </div>
      </div>
    );
  };

  const renderKeyInfo = (modelId) => {
    const meta = modelsMetadata[modelId];
    const isFreeModel = meta?.free || (modelId && (modelId.includes(':free') || modelId.toLowerCase().includes('free')));
    
    const keyToUse = getKeyForModel(modelId);

    if (!keyToUse) return <span className="key-badge warning">No Key</span>;

    const keyLabel = keyToUse.label || keyToUse.key_value.substring(0, 8) + '...';
    const limitDisplay = keyToUse.limit_remaining !== null 
        ? `$${keyToUse.limit_remaining.toFixed(2)}` 
        : '∞';

    return (
        <div className="key-info-row">
            <span className={`key-badge ${isFreeModel ? 'free' : 'paid'}`}>
                {isFreeModel ? 'Free' : 'Paid'}
            </span>
            <span className="key-name" title={keyToUse.description || keyToUse.key_value}>
                {keyLabel}
            </span>
            <span className={`key-limit ${keyToUse.limit_remaining < 1 ? 'low' : ''}`}>
                Limit: {limitDisplay}
            </span>
        </div>
    );
  };

  if (loading) {
    return <div className="settings">Loading...</div>;
  }

  return (
    <div className="settings" onMouseDown={(e) => {
      handleMouseDown(e);
    }}>
      <div ref={modalRef} style={modalStyle}>
        <div className="settings-header" ref={headerRef}>
          <h2>{versionInfo?.printname || 'LLM Council'} Settings</h2>
          <button onClick={onClose} className="close-button">×</button>
        </div>

        <div className="settings-tabs">
          <button 
            className={`settings-tab ${activeTab === 'board' ? 'active' : ''}`}
            onClick={() => setActiveTab('board')}
          >
            AI Board
          </button>
          <button 
            className={`settings-tab ${activeTab === 'strategies' ? 'active' : ''}`}
            onClick={() => setActiveTab('strategies')}
          >
            Strategies
          </button>
          <button 
            className={`settings-tab ${activeTab === 'load-save' ? 'active' : ''}`}
            onClick={() => setActiveTab('load-save')}
          >
            Load/Save
          </button>
          <button 
            className={`settings-tab ${activeTab === 'prompts' ? 'active' : ''}`}
            onClick={() => setActiveTab('prompts')}
          >
            Prompts
          </button>
          <button 
            className={`settings-tab ${activeTab === 'api-keys' ? 'active' : ''}`}
            onClick={() => setActiveTab('api-keys')}
          >
            API Keys
          </button>
        </div>

      <div className="settings-content">
        {activeTab === 'board' ? (
          <>
            <section className="settings-section">
              <h3>Model Filters & Health</h3>
              <div className="filter-health-container">
                <div className="filter-controls">
                  <label className="filter-checkbox">
                    <input
                      type="checkbox"
                      checked={filters.free}
                      onChange={(e) => updateFilter('free', e.target.checked)}
                    />
                    Free
                  </label>
                  <label className="filter-checkbox">
                    <input
                      type="checkbox"
                      checked={filters.thinking}
                      onChange={(e) => updateFilter('thinking', e.target.checked)}
                    />
                    Thinking
                  </label>
                  <label className="filter-checkbox">
                    <input
                      type="checkbox"
                      checked={filters.vision}
                      onChange={(e) => updateFilter('vision', e.target.checked)}
                    />
                    Vision
                  </label>
                  <label className="filter-checkbox">
                    <input
                      type="checkbox"
                      checked={filters.tools}
                      onChange={(e) => updateFilter('tools', e.target.checked)}
                    />
                    Tools
                  </label>
                  <div className="model-count-badge">
                    {filteredModels.length} models selected
                  </div>
                </div>

                <div className="health-integration">
                  <button 
                    className={`test-all-compact-btn ${isTestingAll ? 'testing' : ''}`}
                    onClick={handleTestAll}
                    disabled={isTestingAll}
                  >
                    {isTestingAll ? 'Testing...' : 'Test All Models'}
                  </button>
                  <div className="fail-list-selector">
                    <select 
                      value={selectedFailListId} 
                      onChange={(e) => handleFailListChange(e.target.value)}
                      className="fail-list-dropdown"
                    >
                      <option value="">No Fail List active</option>
                      {failLists.map(list => (
                        <option key={list.id} value={list.id}>
                          {list.name} ({JSON.parse(list.failed_models).length} failed)
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
              {activeFailList && (
                <div className="active-fail-hint">
                  <strong>Deactivated Models:</strong>
                  <div className="failed-models-grid">
                    {JSON.parse(activeFailList.failed_models)
                      .map(id => ({ id, name: id.split('/').pop() }))
                      .sort((a, b) => a.name.localeCompare(b.name))
                      .map(m => (
                        <div key={m.id} className="failed-model-item" title={m.id}>
                          {m.name}
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </section>

            {/* Unified Model Selection Section */}
            <section className="settings-section">
              <div className="section-header-with-btn">
                <h3>Unified Model Selection (Beta)</h3>
                <button 
                  onClick={handleRefreshModels} 
                  className="refresh-models-btn"
                  disabled={unifiedModelsLoading}
                >
                  {unifiedModelsLoading ? 'Refreshing...' : '🔄 Refresh Models'}
                </button>
              </div>
              <p>Search and select base models and their variants across all providers.</p>
              
              <div className="unified-model-selection">
                <div className="model-selection-row">
                  <div className="model-select-group">
                    <label>Base Model:</label>
                    <SearchableSelect
                      options={baseModels}
                      value={selectedBaseModel}
                      onChange={handleBaseModelChange}
                      placeholder="Search base models (e.g., GPT-4, Claude, Llama)"
                      searchFields={['base_model_name', 'developer_id', 'print_name_part1']}
                      displayField="print_name_part1"
                      valueField="base_model_id"
                      className="base-model-select"
                    />
                  </div>
                  
                  <div className="model-select-group">
                    <label>Variant & Provider:</label>
                    <SearchableSelect
                      options={modelVariants}
                      value={selectedVariant}
                      onChange={handleVariantChange}
                      placeholder="Select access method and provider"
                      searchFields={['formatted_name', 'print_name_1', 'print_name_part2', 'access_provider_id']}
                      displayField="formatted_name"
                      valueField="id"
                      className="variant-select"
                      disabled={!selectedBaseModel || unifiedModelsLoading}
                    />
                  </div>
                </div>
                
                {selectedBaseModel && modelVariants.length > 0 && (
                  <div className="selection-info">
                    <p><strong>Selected:</strong> {baseModels.find(b => b.base_model_id === selectedBaseModel)?.print_name_part1 || 'Unknown'}</p>
                    {selectedVariant && (() => {
                      const variant = modelVariants.find(v => (v.id || v.base_model_id) === selectedVariant);
                      return (
                        <>
                          <p><strong>Variant:</strong> {variant?.print_name_part2 || 'Unknown'}</p>
                          <div className="latency-info-container" style={{ marginTop: '8px', fontSize: '13px', color: '#6b7280' }}>
                            {variant?.latency_ms && (
                              <p style={{ margin: '2px 0' }}>
                                <strong>Provider Latency:</strong> {variant.latency_ms.toFixed(0)}ms (avg)
                              </p>
                            )}
                            {variant?.latency_live && (
                              <p style={{ margin: '2px 0', color: '#059669' }}>
                                <strong>Live Latency:</strong> {variant.latency_live.toFixed(0)}ms 
                                <span style={{ fontSize: '11px', color: '#9ca3af', marginLeft: '8px' }}>
                                  ({new Date(variant.latency_live_timestamp).toLocaleString()})
                                </span>
                              </p>
                            )}
                          </div>
                          <div className="selection-actions" style={{ marginTop: '12px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                            <button 
                              onClick={addSelectedToCouncil}
                              className="add-to-council-btn"
                              style={{ 
                                backgroundColor: '#10b981', 
                                color: 'white', 
                                border: 'none', 
                                padding: '6px 12px', 
                                borderRadius: '4px',
                                cursor: 'pointer',
                                fontSize: '13px'
                              }}
                            >
                              Add to Council
                            </button>
                            <button 
                              onClick={setSelectedAsChairman}
                              className="set-as-chairman-btn"
                              style={{ 
                                backgroundColor: '#8b5cf6', 
                                color: 'white', 
                                border: 'none', 
                                padding: '6px 12px', 
                                borderRadius: '4px',
                                cursor: 'pointer',
                                fontSize: '13px'
                              }}
                            >
                              Set as Chairman
                            </button>
                            <button 
                              onClick={handleTestLiveLatency}
                              className="test-live-latency-btn"
                              disabled={isTestingLiveLatency}
                              style={{ 
                                backgroundColor: '#f59e0b', 
                                color: 'white', 
                                border: 'none', 
                                padding: '6px 12px', 
                                borderRadius: '4px',
                                cursor: 'pointer',
                                fontSize: '13px',
                                opacity: isTestingLiveLatency ? 0.7 : 1
                              }}
                            >
                              {isTestingLiveLatency ? 'Testing...' : '⚡ Test Live Latency'}
                            </button>
                          </div>
                        </>
                      );
                    })()}
                  </div>
                )}
                
                {baseModels.length === 0 && !unifiedModelsLoading && (
                  <div className="no-models-message">
                    <p>No unified models available. Click "Refresh Models" to load from providers.</p>
                  </div>
                )}
              </div>
            </section>

            <section className="settings-section">
              <div className="section-header-with-btn">
                <h3>Council Members (1-6)</h3>
                <button 
                  onClick={addCouncilModel} 
                  className="add-member-btn"
                  disabled={config.council_models.length >= 6}
                >
                  + Add Member
                </button>
              </div>
              <div className="member-grid">
                {config.council_models.map((mainModel, index) => {
                  const mode = tileModes[index] || 'main';
                  const subModel = config.substitute_models?.[mainModel] || '';
                  const activeModelId = mode === 'main' ? mainModel : subModel;

                  return (
                    <div key={index} className="member-tile">
                      <div className="tile-mode-switch">
                        <button 
                          className={`mode-btn ${mode === 'main' ? 'active' : ''}`}
                          onClick={() => setTileModes(prev => ({...prev, [index]: 'main'}))}
                        >
                          Main Member
                        </button>
                        <button 
                          className={`mode-btn ${mode === 'sub' ? 'active' : ''}`}
                          onClick={() => setTileModes(prev => ({...prev, [index]: 'sub'}))}
                        >
                          Substitute
                        </button>
                      </div>

                      <div className="tile-body">
                        <div className="tile-left">
                          <div className="model-select-group">
                            <select
                              value={activeModelId}
                              onChange={(e) => {
                                if (mode === 'main') {
                                  updateCouncilModel(index, e.target.value);
                                } else {
                                  updateSubstituteModel(mainModel, e.target.value);
                                }
                              }}
                              className="model-select"
                            >
                              {mode === 'sub' && <option value="">None (No Substitute)</option>}
                              {!filteredModels.find(m => m.id === activeModelId) && activeModelId && availableModels.find(m => m.id === activeModelId) && (
                                <option key={activeModelId} value={activeModelId}>
                                  {availableModels.find(m => m.id === activeModelId).name} (Current)
                                </option>
                              )}
                              {filteredModels.map(m => (
                                <option key={m.id} value={m.id}>{m.name}</option>
                              ))}
                            </select>
                          </div>

                          <textarea
                            placeholder={mode === 'main' ? "Main Member personality..." : "Substitute personality..."}
                            value={config.model_personalities[activeModelId] || ''}
                            onChange={(e) => updatePersonality(activeModelId, e.target.value)}
                            className="personality-textarea"
                          />
                          
                          <div className="tile-actions">
                            <button
                              onClick={() => handleTestLatency(activeModelId)}
                              className="test-btn-small"
                              disabled={testingModel !== null || !activeModelId}
                            >
                              {!activeModelId ? 'Test' : (testingModel === activeModelId ? '...' : (latencies[activeModelId] || 'Test'))}
                            </button>
                            <button
                              onClick={() => removeCouncilModel(index)}
                              className="remove-btn-small"
                              disabled={config.council_models.length <= 1}
                            >
                              Remove Member
                            </button>
                          </div>
                          
                          {/* API Key / Limit Display */}
                          <div className="key-limit-display">
                            {renderKeyInfo(activeModelId)}
                          </div>

                          {mode === 'main' && (
                            <div className="sub-status-hint">
                              Substitute: <span>{subModel ? (availableModels.find(m => m.id === subModel)?.name || subModel.split('/').pop()) : 'none'}</span>
                            </div>
                          )}
                        </div>
                        
                        <div className="tile-right">
                          {activeModelId ? getModelPreview(activeModelId) : <div className="no-preview">No model selected</div>}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            <section className="settings-section">
              <h3>AI Chairman Model</h3>
              <p>Model that synthesizes the final answer.</p>
              {(() => {
                const mainModel = config.chairman_model;
                const subModel = config.substitute_models?.[mainModel] || '';
                const activeModelId = chairmanMode === 'main' ? mainModel : subModel;

                return (
                  <div className="member-tile">
                    <div className="tile-mode-switch">
                      <button 
                        className={`mode-btn ${chairmanMode === 'main' ? 'active' : ''}`}
                        onClick={() => setChairmanMode('main')}
                      >
                        Main Member
                      </button>
                      <button 
                        className={`mode-btn ${chairmanMode === 'sub' ? 'active' : ''}`}
                        onClick={() => setChairmanMode('sub')}
                      >
                        Substitute
                      </button>
                    </div>

                    <div className="tile-body">
                      <div className="tile-left">
                        <div className="model-select-group">
                          <select
                            value={activeModelId}
                            onChange={(e) => {
                              if (chairmanMode === 'main') {
                                updateChairmanModel(e.target.value);
                              } else {
                                updateSubstituteModel(mainModel, e.target.value);
                              }
                            }}
                            className="model-select"
                          >
                            {chairmanMode === 'sub' && <option value="">None (No Substitute)</option>}
                            {!filteredModels.find(m => m.id === activeModelId) && activeModelId && availableModels.find(m => m.id === activeModelId) && (
                              <option key={activeModelId} value={activeModelId}>
                                {availableModels.find(m => m.id === activeModelId).name} (Current)
                              </option>
                            )}
                            {filteredModels.map(m => (
                              <option key={m.id} value={m.id}>{m.name}</option>
                            ))}
                          </select>
                        </div>

                        <textarea
                          placeholder={chairmanMode === 'main' ? "Chairman personality (optional override)..." : "Substitute personality..."}
                          value={config.model_personalities[activeModelId] || ''}
                          onChange={(e) => updatePersonality(activeModelId, e.target.value)}
                          className="personality-textarea"
                        />
                        
                        <div className="tile-actions">
                          <button
                            onClick={() => handleTestLatency(activeModelId)}
                            className="test-btn-small"
                            disabled={testingModel !== null || !activeModelId}
                          >
                            {!activeModelId ? 'Test' : (testingModel === activeModelId ? '...' : (latencies[activeModelId] || 'Test'))}
                          </button>
                        </div>
                        
                        <div className="key-limit-display">
                          {renderKeyInfo(activeModelId)}
                        </div>

                        {chairmanMode === 'main' && (
                          <div className="sub-status-hint">
                            Substitute: <span>{subModel ? (availableModels.find(m => m.id === subModel)?.name || subModel.split('/').pop()) : 'none'}</span>
                          </div>
                        )}
                      </div>
                      
                      <div className="tile-right">
                        {activeModelId ? getModelPreview(activeModelId) : <div className="no-preview">No model selected</div>}
                      </div>
                    </div>
                  </div>
                );
              })()}
            </section>

            <section className="settings-section">
              <h3>Response Timeout</h3>
              <p>Maximum time (in seconds) to wait for each model response.</p>
              <div className="timeout-row">
                <input
                  type="number"
                  min="10"
                  max="300"
                  value={config.response_timeout || 60}
                  onChange={(e) => setConfig(prev => ({...prev, response_timeout: parseInt(e.target.value)}))}
                  className="timeout-input"
                />
                <span>seconds</span>
              </div>
            </section>
          </>
        ) : activeTab === 'strategies' ? (
          <>
            <section className="settings-section">
              <h3>Consensus Strategy</h3>
              <p>Method used to determine the ranking of responses based on peer evaluations.</p>
              <select
                value={config.consensus_strategy || 'borda_count'}
                onChange={(e) => updateStrategy(e.target.value)}
                className="strategy-select"
              >
                <option value="borda_count">Borda Count (Standard Ranking)</option>
                <option value="chairman_cut">Chairman Cut (Top 3 + Chairman choice)</option>
              </select>
              <div className="strategy-info" style={{ marginTop: '10px', fontSize: '14px', color: '#666' }}>
                {config.consensus_strategy === 'chairman_cut' ? (
                  <p><strong>Chairman Cut:</strong> The top 3 models from peer ranking are presented to the chairman. The chairman then makes the final selection from these top candidates.</p>
                ) : (
                  <p><strong>Borda Count:</strong> A mathematical point system where models rank each other. The response with the lowest total rank (highest points) wins automatically.</p>
                )}
              </div>
            </section>
          </>
        ) : activeTab === 'load-save' ? (
          <>
            <section className="settings-section">
              <h3>Task Templates</h3>
              <p>Quickly load a predefined council configuration for specific tasks.</p>
              <div className="template-row">
                <select 
                  onChange={(e) => applyTemplate(e.target.value)}
                  className="template-select"
                  defaultValue=""
                >
                  <option value="" disabled>Select a template...</option>
                  {templates.map(t => (
                    <option key={t.id} value={t.id}>{t.name} - {t.description}</option>
                  ))}
                </select>
              </div>
            </section>

            <section className="settings-section">
              <h3>AI Board Persistence</h3>
              <p>Save and load your favorite council configurations.</p>
              
              <div className="board-persistence-controls">
                <div className="board-persistence-buttons">
                  <button onClick={() => handleSaveBoard(false)} className="persistence-button save" disabled={saving}>
                    {saving ? 'Saving...' : 'Save current Board'}
                  </button>
                  <button onClick={() => handleSaveBoard(true)} className="persistence-button save-as" disabled={saving}>
                    Save As...
                  </button>
                </div>

                <div className="board-load-row">
                  <label>Load existing Board:</label>
                  <select 
                    onChange={(e) => handleLoadBoard(e.target.value)}
                    className="board-select"
                    value={currentBoardId || ''}
                  >
                    <option value="" disabled>Select a board to load...</option>
                    {boards.map(b => (
                      <option key={b.id} value={b.id}>{b.name} (Used: {b.usage_count}x)</option>
                    ))}
                  </select>
                </div>

                <div className="board-description-field">
                  <label>Board Description:</label>
                  <textarea
                    value={boardDescription}
                    onChange={(e) => setBoardDescription(e.target.value)}
                    placeholder="Describe this board configuration..."
                    className="board-desc-textarea"
                  />
                  <button 
                    className="reset-desc-button"
                    onClick={() => setBoardDescription(generateAutoDescription(config))}
                  >
                    Reset to Auto-Description
                  </button>
                </div>

                {currentBoardId && (
                  <div className="board-stats">
                    <h4>Board Statistics</h4>
                    <div className="stats-grid">
                      <div className="stat-item">
                        <span className="stat-label">Usage Count:</span>
                        <span className="stat-value">{boards.find(b => b.id === currentBoardId)?.usage_count || 0}</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Last Used:</span>
                        <span className="stat-value">
                          {boards.find(b => b.id === currentBoardId)?.last_used 
                            ? new Date(boards.find(b => b.id === currentBoardId).last_used).toLocaleString() 
                            : 'Never'}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </section>
          </>
        ) : activeTab === 'prompts' ? (
          <PromptManager 
            prompts={prompts} 
            onSave={handleSavePrompt} 
            onDelete={handleDeletePrompt} 
          />
        ) : activeTab === 'api-keys' ? (
          <div className="api-keys-manager">
            <div className="section-header-with-btn">
              <h3>API Key Management</h3>
              <button 
                className="add-key-btn"
                onClick={() => setIsAddingKey(!isAddingKey)}
              >
                {isAddingKey ? 'Cancel' : '+ Add API Key'}
              </button>
            </div>

            {isAddingKey && (
              <div className="add-key-form">
                <div className="form-group">
                  <label>Provider:</label>
                  <select 
                    value={newKey.provider}
                    onChange={(e) => setNewKey({...newKey, provider: e.target.value})}
                  >
                    <option value="openrouter">OpenRouter</option>
                    <option value="openai">OpenAI (Direct)</option>
                    <option value="anthropic">Anthropic (Direct)</option>
                    <option value="google">Google (Direct)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Key Value:</label>
                  <input 
                    type="password"
                    value={newKey.key_value}
                    onChange={(e) => setNewKey({...newKey, key_value: e.target.value})}
                    placeholder="sk-..."
                  />
                </div>
                <div className="form-group">
                  <label>Label / Description:</label>
                  <input 
                    type="text"
                    value={newKey.description}
                    onChange={(e) => setNewKey({...newKey, description: e.target.value})}
                    placeholder="e.g. My Paid Key"
                  />
                </div>
                <div className="form-group">
                  <label>Monthly Limit ($):</label>
                  <input 
                    type="number"
                    value={newKey.limit_amount}
                    onChange={(e) => setNewKey({...newKey, limit_amount: e.target.value})}
                    placeholder="Optional limit"
                  />
                </div>
                <button onClick={handleSaveKey} disabled={!newKey.key_value} className="save-key-btn">
                  Save Key
                </button>
              </div>
            )}

            <div className="keys-list">
              {apiKeys.length === 0 ? (
                <p className="no-keys">No API keys configured.</p>
              ) : (
                apiKeys.map(key => (
                  <div key={key.id} className={`key-card ${!key.is_active ? 'inactive' : ''}`}>
                    <div className="key-header">
                      <span className="key-provider">{key.provider}</span>
                      <span className={`key-status ${key.is_active ? 'active' : 'inactive'}`}>
                        {key.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <div className="key-body">
                      <h4>{key.description || key.label || 'Unnamed Key'}</h4>
                      <div className="key-preview">
                        {key.key_value.substring(0, 8)}...{key.key_value.substring(key.key_value.length - 4)}
                      </div>
                      <div className="key-stats">
                        <div className="stat">
                          <label>Remaining:</label>
                          <span>{key.limit_remaining !== null ? `$${key.limit_remaining.toFixed(2)}` : '∞'}</span>
                        </div>
                        <div className="stat">
                          <label>Usage:</label>
                          <span>${(key.usage_amount || 0).toFixed(2)}</span>
                        </div>
                      </div>
                    </div>
                    <div className="key-actions">
                      <button onClick={() => handleCheckKey(key.id)} disabled={checkingKey === key.id}>
                        {checkingKey === key.id ? 'Checking...' : 'Check Balance'}
                      </button>
                      <button onClick={() => handleDeleteKey(key.id)} className="delete-btn">
                        Delete
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        ) : null}
      </div>

      <div className="settings-footer">
        <button onClick={onClose} className="cancel-button">
          Cancel
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="save-button"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
      <div className="resize-handle" onMouseDown={handleResizeMouseDown}></div>
      </div>
    </div>
  );
}

export default Settings;