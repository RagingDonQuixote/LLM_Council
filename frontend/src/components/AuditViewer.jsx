import React, { useState, useEffect } from 'react';
import { api } from '../api';

const AuditViewer = ({ conversationId, onClose }) => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [analysis, setAnalysis] = useState('');
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    fetchLogs();
  }, [conversationId]);

  const fetchLogs = async () => {
    try {
      const data = await fetch(`/api/audit/${conversationId}`).then(res => res.json());
      setLogs(data);
      setLoading(false);
    } catch (err) {
      console.error("Failed to fetch audit logs", err);
      setLoading(false);
    }
  };

  const handleSaveAnalysis = async () => {
    setSaving(true);
    try {
      await fetch(`/api/audit/${conversationId}/analysis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ analysis })
      });
      alert('Analysis saved successfully!');
    } catch (err) {
      alert('Failed to save analysis');
    }
    setSaving(false);
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const res = await fetch(`/api/audit/${conversationId}/export`, { method: 'POST' }).then(res => res.json());
      alert(`Archive created: ${res.archive_path}`);
    } catch (err) {
      alert('Failed to export archive');
    }
    setExporting(false);
  };

  if (loading) return <div className="p-4">Loading audit logs...</div>;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-8">
      <div className="bg-gray-900 w-full h-full rounded-lg flex flex-col shadow-2xl border border-gray-700">
        <div className="p-4 border-b border-gray-700 flex justify-between items-center bg-gray-800 rounded-t-lg">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <span>🔍</span> Mission Audit & Analysis
          </h2>
          <div className="flex gap-2">
            <button 
              onClick={handleExport}
              disabled={exporting}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm disabled:opacity-50"
            >
              {exporting ? 'Exporting...' : '📦 Create Archive'}
            </button>
            <button 
              onClick={onClose}
              className="text-gray-400 hover:text-white text-2xl"
            >
              &times;
            </button>
          </div>
        </div>

        <div className="flex-1 flex overflow-hidden">
          {/* Logs Timeline */}
          <div className="w-2/3 overflow-y-auto p-4 border-r border-gray-700">
            <h3 className="text-sm font-semibold text-gray-400 mb-4 uppercase tracking-wider">Event Timeline</h3>
            <div className="space-y-4">
              {logs.map((log, i) => (
                <div key={i} className="bg-gray-800 p-4 rounded border border-gray-700 hover:border-blue-500 transition-colors">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-xs font-mono text-blue-400">{new Date(log.timestamp).toLocaleString()}</span>
                    <span className="px-2 py-0.5 rounded bg-gray-700 text-[10px] text-gray-300 font-mono uppercase">
                      {log.step}
                    </span>
                  </div>
                  <div className="text-sm font-bold text-gray-200 mb-1">{log.log_message}</div>
                  <div className="text-xs text-gray-500 mb-2">Model: {log.model_id?.split('/').pop() || 'N/A'} | Task: {log.task_id || 'N/A'}</div>
                  
                  {log.raw_data && (
                    <details className="mt-2">
                      <summary className="text-xs text-blue-400 cursor-pointer hover:underline">View Raw Response Data</summary>
                      <pre className="mt-2 p-2 bg-black rounded text-[10px] text-green-400 overflow-x-auto max-h-64">
                        {JSON.stringify(JSON.parse(log.raw_data), null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              ))}
              {logs.length === 0 && <div className="text-gray-500 text-center py-8 italic">No audit logs found for this session.</div>}
            </div>
          </div>

          {/* Analysis Sidebar */}
          <div className="w-1/3 p-4 flex flex-col bg-gray-800">
            <h3 className="text-sm font-semibold text-gray-400 mb-4 uppercase tracking-wider">Post-Mission Analysis</h3>
            <p className="text-xs text-gray-400 mb-4 italic">
              Record your observations here. What went well? Where did the models fail? Was the chair's planning optimal?
            </p>
            <textarea
              className="flex-1 bg-gray-900 text-gray-100 p-3 rounded border border-gray-700 focus:border-blue-500 outline-none resize-none text-sm mb-4"
              placeholder="Enter your analysis results here..."
              value={analysis}
              onChange={(e) => setAnalysis(e.target.value)}
            />
            <button
              onClick={handleSaveAnalysis}
              disabled={saving}
              className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-2 rounded transition-colors disabled:opacity-50"
            >
              {saving ? 'Saving...' : '💾 Save Analysis Result'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuditViewer;
