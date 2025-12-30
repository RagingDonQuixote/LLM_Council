import { useState, useEffect, useRef } from 'react';
import { api } from '../api';
import './Settings.css';

function Settings({ onClose }) {
  const [config, setConfig] = useState(null);
  const [availableModels, setAvailableModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testingModel, setTestingModel] = useState(null);
  const [latencies, setLatencies] = useState({});
  const [showFreeOnly, setShowFreeOnly] = useState(true);

  // Drag and resize state
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [resizeStart, setResizeStart] = useState({ x: 0, y: 0, width: 0, height: 0 });
  const modalRef = useRef(null);
  const headerRef = useRef(null);

  // Persistence of styles across re-renders
  const [modalStyle, setModalStyle] = useState({});

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
      const [configData, modelsData] = await Promise.all([
        api.getConfig(),
        api.getAvailableModels()
      ]);
      setConfig(configData);
      setAvailableModels(modelsData.models);
    } catch (error) {
      console.error('Failed to load settings:', error);
    } finally {
      setLoading(false);
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

  const handleTestLatency = async (modelId) => {
    setTestingModel(modelId);
    try {
      const result = await api.testLatency(modelId);
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
    setConfig(prev => ({
      ...prev,
      council_models: [...prev.council_models, availableModels[0]?.id || '']
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
    setConfig(prev => ({
      ...prev,
      council_models: prev.council_models.map((model, i) =>
        i === index ? value : model
      )
    }));
  };

  const filteredModels = showFreeOnly
    ? availableModels.filter(m => m.free)
    : availableModels;

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

  if (loading) {
    return <div className="settings">Loading...</div>;
  }

  return (
    <div className="settings" onMouseDown={handleMouseDown}>
      <div ref={modalRef} style={modalStyle}>
        <div className="settings-header" ref={headerRef}>
          <h2>LLM Council Settings</h2>
          <button onClick={onClose} className="close-button">×</button>
        </div>

      <div className="settings-content">
        <section className="settings-section">
          <h3>Model Filter</h3>
          <label>
            <input
              type="checkbox"
              checked={showFreeOnly}
              onChange={(e) => setShowFreeOnly(e.target.checked)}
            />
            Show only FREE models
          </label>
        </section>

        <section className="settings-section">
          <h3>Council Members (1-6)</h3>
          <p>Models that participate in the discussion and voting.</p>
          {config.council_models.map((model, index) => (
            <div key={index} className="model-row">
              <select
                value={model}
                onChange={(e) => updateCouncilModel(index, e.target.value)}
                className="model-select"
              >
                {filteredModels.map(m => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
              <input
                type="text"
                placeholder="Personality description"
                value={config.model_personalities[model] || ''}
                onChange={(e) => updatePersonality(model, e.target.value)}
                className="personality-input"
              />
              <button
                onClick={() => removeCouncilModel(index)}
                className="remove-button"
                disabled={config.council_models.length <= 1}
              >
                Remove
              </button>
              <button
                onClick={() => handleTestLatency(model)}
                className="test-button"
                disabled={testingModel !== null}
              >
                {testingModel === model ? '...' : (latencies[model] || 'Test')}
              </button>
            </div>
          ))}
          <button 
            onClick={addCouncilModel} 
            className="add-button"
            disabled={config.council_models.length >= 6}
          >
            Add Model
          </button>
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

        <section className="settings-section">
          <h3>AI Chairman Model</h3>
          <p>Model that synthesizes the final answer.</p>
          <div className="model-row">
            <select
              value={config.chairman_model}
              onChange={(e) => updateChairmanModel(e.target.value)}
              className="model-select"
            >
              {filteredModels.map(m => (
                <option key={m.id} value={m.id}>{m.name}</option>
              ))}
            </select>
            <button
              onClick={() => handleTestLatency(config.chairman_model)}
              className="test-button"
              disabled={testingModel !== null}
            >
              {testingModel === config.chairman_model ? '...' : (latencies[config.chairman_model] || 'Test')}
            </button>
          </div>
        </section>

        <section className="settings-section">
          <h3>Human Chairman</h3>
          <p>You (the user) act as the Human Chairman in Stage 4 to review and provide final feedback.</p>
        </section>
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