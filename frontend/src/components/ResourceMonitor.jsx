import { useMemo } from 'react';

export default function ResourceMonitor({ config, modelsMetadata }) {
  const models = useMemo(() => {
    if (!config) return [];
    const all = [...(config.council_models || [])];
    if (config.chairman_model && !all.includes(config.chairman_model)) {
      all.push(config.chairman_model);
    }
    return all.map(id => ({
      id,
      name: id.split('/').pop(),
      isChairman: id === config.chairman_model,
      metadata: modelsMetadata?.[id] || {}
    }));
  }, [config, modelsMetadata]);

  return (
    <div className="resource-monitor">
      <div className="monitor-section">
        <h6>COUNCIL MEMBERS</h6>
        {models.map(model => (
          <div key={model.id} className={`resource-card ${model.isChairman ? 'chairman' : ''}`}>
            <div className="card-header">
              <h5>{model.name} {model.isChairman && '👑'}</h5>
            </div>
            <div className="card-skills">
              {model.metadata.tags?.map(tag => (
                <span key={tag} className="skill-tag">{tag}</span>
              ))}
            </div>
            <div className="card-footer">
              <span className="cost-info">Cost: {model.metadata.pricing?.prompt || '0.00'}/1k</span>
            </div>
          </div>
        ))}
      </div>

      <div className="monitor-section">
        <h6>ACTIVE STRATEGY</h6>
        <div className="resource-card strategy">
          <h5>{config?.consensus_strategy || 'Default'}</h5>
          <p style={{ fontSize: '11px', color: '#666', margin: 0 }}>
            {config?.consensus_strategy === 'consensus' 
              ? 'Members reach agreement via voting.' 
              : 'Chairman makes final decision.'}
          </p>
        </div>
      </div>
    </div>
  );
}
