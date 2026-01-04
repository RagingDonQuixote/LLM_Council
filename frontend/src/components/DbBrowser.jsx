import { useState, useEffect } from 'react';
import { api } from '../api';
import './DbBrowser.css';

const DbBrowser = ({ isOpen, onClose }) => {
  const [tables, setTables] = useState([]);
  const [currentTable, setCurrentTable] = useState('');
  const [tableData, setTableData] = useState([]);
  const [columns, setColumns] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // View Mode: 'table' or 'single'
  const [viewMode, setViewMode] = useState('table');
  const [currentRecordIndex, setCurrentRecordIndex] = useState(0);

  // Inspector Mode State
  const [inspectorMode, setInspectorMode] = useState(false);
  const [allModels, setAllModels] = useState([]);
  const [filteredModels, setFilteredModels] = useState([]);
  const [inspectorPage, setInspectorPage] = useState(1);
  const [inspectorFilters, setInspectorFilters] = useState({
    view: 'unified', // 'unified', 'raw', 'all'
    search: '',
    provider: 'all',
    variable: 'all', // Second selection: Column
    value: 'all'     // Third selection: Value
  });
  const [uniqueProviders, setUniqueProviders] = useState([]);
  const [uniqueVariables, setUniqueVariables] = useState([]);
  const [uniqueValues, setUniqueValues] = useState([]);
  
  // Compare Mode State
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [showCompare, setShowCompare] = useState(false);
  const [diffOnly, setDiffOnly] = useState(false);

  const [tableFilters, setTableFilters] = useState({ column: '', value: '' });

  useEffect(() => {
    if (isOpen) {
      loadTables();
    }
  }, [isOpen]);

  // Load Inspector Data
  useEffect(() => {
    if (inspectorMode && allModels.length === 0) {
      loadInspectorData();
    }
  }, [inspectorMode]);

  // Filter Inspector Data
  useEffect(() => {
    if (!inspectorMode || allModels.length === 0) return;

    let result = [...allModels];

    // 1. Text Search
    if (inspectorFilters.search) {
      const q = inspectorFilters.search.toLowerCase();
      result = result.filter(m => 
        (m.id && m.id.toLowerCase().includes(q)) ||
        (m.base_model_name && m.base_model_name.toLowerCase().includes(q)) ||
        (m.variant_name && m.variant_name.toLowerCase().includes(q))
      );
    }

    // 2. Provider Filter
    if (inspectorFilters.provider !== 'all') {
      result = result.filter(m => m.access_provider_id === inspectorFilters.provider);
    }

    // 3. Variable Filter
    if (inspectorFilters.variable !== 'all' && inspectorFilters.value !== 'all') {
        result = result.filter(m => String(m[inspectorFilters.variable]) === inspectorFilters.value);
    }

    setFilteredModels(result);
    setInspectorPage(1); // Reset to first page on filter change
  }, [inspectorFilters, allModels, inspectorMode]);

  // Update Unique Values when Variable changes
  useEffect(() => {
    if (inspectorFilters.variable === 'all' || !allModels.length) {
        setUniqueValues([]);
        return;
    }
    
    const values = [...new Set(allModels.map(m => String(m[inspectorFilters.variable] || '')))].sort();
    setUniqueValues(values);
    
    // Reset value selection if it's no longer valid (though usually we want to reset it on variable change anyway)
    // But we handle that in the onChange handler
  }, [inspectorFilters.variable, allModels]);

  const loadInspectorData = async () => {
    try {
      setLoading(true);
      const data = await api.getAllUnifiedModels();
      setAllModels(data);
      setFilteredModels(data);
      
      // Extract unique providers
      const providers = [...new Set(data.map(m => m.access_provider_id).filter(Boolean))].sort();
      setUniqueProviders(providers);

      // Extract all unique keys for variable filter
      if (data.length > 0) {
        const keys = Object.keys(data[0]).sort();
        setUniqueVariables(keys);
      }
    } catch (err) {
      setError('Failed to load inspector data: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadTables = async () => {
    try {
      setLoading(true);
      const data = await api.getDbTables();
      setTables(data.tables || []);
    } catch (err) {
      setError('Failed to load tables: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadTableData = async (tableName, pageNum = 1, filters = tableFilters) => {
    try {
      setLoading(true);
      const data = await api.getDbTableContent(tableName, pageNum, filters);
      
      setTableData(data.data || []);
      setPage(data.page);
      setTotalPages(data.total_pages);
      setTotalCount(data.total_count);
      
      if (data.data && data.data.length > 0) {
        setColumns(Object.keys(data.data[0]));
      } else if (tableName !== currentTable) {
        // Only reset columns if we switched tables
        setColumns([]);
      }
      
      setError(null);
    } catch (err) {
      setError('Failed to load table content: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTableChange = (e) => {
    const table = e.target.value;
    setCurrentTable(table);
    setPage(1);
    setViewMode('table');
    setTableFilters({ column: '', value: '' });
    if (table) {
      loadTableData(table, 1, { column: '', value: '' });
    } else {
      setTableData([]);
    }
  };

  const handleFilterChange = (key, value) => {
    setTableFilters(prev => ({ ...prev, [key]: value }));
  };

  const applyFilter = () => {
    setPage(1);
    loadTableData(currentTable, 1, tableFilters);
  };

  const clearFilter = () => {
    const newFilters = { column: '', value: '' };
    setTableFilters(newFilters);
    setPage(1);
    loadTableData(currentTable, 1, newFilters);
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      loadTableData(currentTable, newPage, tableFilters);
    }
  };

  const handleRecordClick = (index) => {
    setCurrentRecordIndex(index);
    setViewMode('single');
  };

  const handleNextRecord = () => {
    jumpToRecord(1);
  };

  const handlePrevRecord = () => {
    jumpToRecord(-1);
  };

  const jumpToRecord = async (delta) => {
    if (inspectorMode) {
      const newIndex = currentRecordIndex + delta;
      if (newIndex >= 0 && newIndex < filteredModels.length) {
        setCurrentRecordIndex(newIndex);
      }
    } else {
      const pageSize = 50;
      const globalIndex = (page - 1) * pageSize + currentRecordIndex;
      const targetGlobalIndex = globalIndex + delta;
      
      if (targetGlobalIndex >= 0 && targetGlobalIndex < totalCount) {
        const newPage = Math.floor(targetGlobalIndex / pageSize) + 1;
        const newLocalIndex = targetGlobalIndex % pageSize;
        
        if (newPage !== page) {
          await loadTableData(currentTable, newPage);
          setCurrentRecordIndex(newLocalIndex);
        } else {
          setCurrentRecordIndex(newLocalIndex);
        }
      }
    }
  };

  const handleInspectorRecordClick = (index) => {
      // Index in the current page slice? No, let's use global index in filteredModels
      // But the table renders a slice.
      // The table row index 'i' is 0-49.
      // So global index = (inspectorPage - 1) * 50 + i.
      const globalIndex = (inspectorPage - 1) * 50 + index;
      setCurrentRecordIndex(globalIndex);
      setViewMode('single');
  };

  const toggleSelection = (id, e) => {
    if (e) e.stopPropagation();
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setSelectedIds(newSet);
  };

  const getCompareData = () => {
    if (!allModels.length || selectedIds.size === 0) return { models: [], keys: [] };
    const models = allModels.filter(m => selectedIds.has(m.id));
    const allKeys = Array.from(new Set(models.flatMap(Object.keys))).sort();
    
    let displayKeys = allKeys;
    if (diffOnly) {
        displayKeys = allKeys.filter(key => {
            const values = models.map(m => String(m[key]));
            return new Set(values).size > 1;
        });
    }
    
    return { models, keys: displayKeys };
  };

  // --- Origin Trace Helper ---
  const renderOriginTrace = (umtItem) => {
    // We expect raw_base_model_data and raw_endpoint_data to be present
    let baseData = {};
    let endpointData = {};
    
    try {
        baseData = typeof umtItem.raw_base_model_data === 'string' 
            ? JSON.parse(umtItem.raw_base_model_data) 
            : umtItem.raw_base_model_data || {};
            
        endpointData = typeof umtItem.raw_endpoint_data === 'string' 
            ? JSON.parse(umtItem.raw_endpoint_data) 
            : umtItem.raw_endpoint_data || {};
    } catch (e) {
        console.error("Error parsing raw data for trace:", e);
    }

    // Define keys we want to trace
    const traceKeys = [
        { label: 'Context Length', umtKey: 'technical', subKey: 'context_tokens', baseKey: 'context_length', epKey: 'context_length' },
        { label: 'Pricing (Prompt)', umtKey: 'cost', subKey: 'cost_1mT_input_USD', baseKey: 'pricing.prompt', epKey: 'pricing.prompt' },
        { label: 'Provider Name', umtKey: 'hosting_provider_id', baseKey: null, epKey: 'provider_name' },
        { label: 'Quantization', umtKey: 'technical', subKey: 'quantization', baseKey: null, epKey: 'quantization' },
        { label: 'Reasoning', umtKey: 'capabilities', subKey: 'reasoning', baseKey: 'supported_parameters', epKey: 'supported_parameters' }
    ];

    return (
        <div className="origin-trace-view">
            <h4>Origin Trace Analysis</h4>
            <table className="trace-table">
                <thead>
                    <tr>
                        <th>Field</th>
                        <th className="trace-col-base">Base Model (Raw)</th>
                        <th className="trace-col-endpoint">Endpoint (Raw)</th>
                        <th className="trace-col-umt">UMT Result (Final)</th>
                    </tr>
                </thead>
                <tbody>
                    {traceKeys.map((k, idx) => {
                        // Extract Values
                        let baseVal = k.baseKey ? getNestedVal(baseData, k.baseKey) : '-';
                        let epVal = k.epKey ? getNestedVal(endpointData, k.epKey) : '-';
                        
                        // UMT Value extraction is tricky because of JSON strings in DB columns
                        let umtValRaw = umtItem[k.umtKey];
                        if (typeof umtValRaw === 'string' && (umtValRaw.startsWith('{') || umtValRaw.startsWith('['))) {
                            try { umtValRaw = JSON.parse(umtValRaw); } catch {}
                        }
                        let umtVal = k.subKey ? (umtValRaw ? umtValRaw[k.subKey] : '-') : umtValRaw;

                        // Formatting for display
                        const formatVal = (v) => {
                            if (v === undefined || v === null) return <span className="val-missing">null</span>;
                            if (typeof v === 'boolean') return v ? 'TRUE' : 'FALSE';
                            if (Array.isArray(v)) return `[${v.length} items]`;
                            if (typeof v === 'object') return '{...}';
                            // Price normalization for comparison
                            if (k.label.includes('Pricing')) return parseFloat(v).toFixed(8);
                            return String(v);
                        };

                        // Logic Check for highlighting
                        const baseStr = String(baseVal);
                        const epStr = String(epVal);
                        const umtStr = String(umtVal);

                        let umtClass = "";
                        // If UMT matches Endpoint AND Endpoint differs from Base (or Base is missing) -> GREEN (Override)
                        if (epVal !== undefined && epVal !== null && epVal !== '-') {
                             // Loose comparison for numbers/strings
                             if (String(epVal) == String(umtVal)) {
                                 umtClass = "trace-match-endpoint"; 
                             }
                        } else if (baseVal !== undefined && baseVal !== null && baseVal !== '-') {
                             if (String(baseVal) == String(umtVal)) {
                                 umtClass = "trace-match-base";
                             }
                        }

                        return (
                            <tr key={idx}>
                                <td className="trace-label">{k.label}</td>
                                <td className="trace-val-base">{formatVal(baseVal)}</td>
                                <td className="trace-val-endpoint">{formatVal(epVal)}</td>
                                <td className={`trace-val-umt ${umtClass}`}>
                                    {k.label.includes('Pricing') && k.subKey === 'cost_1mT_input_USD' 
                                        ? (umtVal / 1000000).toFixed(8)  // De-normalize UMT price for comparison
                                        : formatVal(umtVal)
                                    }
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
            <div className="trace-legend">
                <span className="legend-item match-ep">Green = Endpoint Source (Preferred)</span>
                <span className="legend-item match-base">Grey = Base Source (Fallback)</span>
            </div>
        </div>
    );
  };

  // Helper to get nested properties like "pricing.prompt"
  const getNestedVal = (obj, path) => {
      if (!obj || !path) return undefined;
      const parts = path.split('.');
      let current = obj;
      for (const part of parts) {
          if (current === undefined || current === null) return undefined;
          current = current[part];
      }
      // Special case for arrays (checking existence of value)
      if (Array.isArray(current) && path === 'supported_parameters') {
          return current.includes('reasoning') || current.includes('include_reasoning');
      }
      return current;
  };

  const renderSingleView = () => {
    const singleData = inspectorMode ? filteredModels[currentRecordIndex] : tableData[currentRecordIndex];
    if (!singleData) return <div className="loading">Loading details...</div>;
    
    return (
      <div className="single-view-container">
        <button className="back-btn" onClick={() => setViewMode('table')}>← Back to Table</button>
        <h3>Record Details (ID: {singleData.id})</h3>
        
        {/* Origin Trace View if available */}
        {(singleData.raw_base_model_data || singleData.raw_endpoint_data) && renderOriginTrace(singleData)}

        <div className="json-viewer">
          {Object.entries(singleData).map(([k, v]) => {
              // ... existing json viewer logic ...
              // if (k === 'raw_base_model_data' || k === 'raw_endpoint_data') return null; // Show all fields including raw data
              
              let displayVal = v;
              try {
                  if (typeof v === 'string' && (v.startsWith('{') || v.startsWith('['))) {
                      displayVal = <pre>{JSON.stringify(JSON.parse(v), null, 2)}</pre>;
                  }
              } catch {}
              
              return (
                <div key={k} className="field-row">
                    <span className="field-key">{k}:</span>
                    <span className="field-val">{displayVal}</span>
                </div>
              );
          })}
        </div>
      </div>
    );
  };

  if (!isOpen) return null;

  // Inspector Render Helpers
  const getDisplayedColumns = () => {
    if (!allModels.length) return [];
    
    // 1. All Variables
    if (inspectorFilters.view === 'all') return Object.keys(allModels[0]).sort();

    // 2. Unified View (Curated)
    if (inspectorFilters.view === 'unified') {
      return [
        'id', 'base_model_name', 'variant_name', 'access_provider_id', 
        'context_length', 'latency_ms', 'latency_live', 'pricing'
      ].filter(k => Object.keys(allModels[0]).includes(k));
    }

    // 3. Raw Data (Everything else / Provider specific)
    if (inspectorFilters.view === 'raw') {
       // Exclude our main unified columns to show "raw" underlying data
       const unifiedCols = ['base_model_name', 'variant_name', 'access_provider_id', 'base_model_id', 'provider_model_id'];
       return Object.keys(allModels[0]).filter(k => !unifiedCols.includes(k)).sort();
    }
    
    return Object.keys(allModels[0]);
  };

  const getInspectorPageData = () => {
    const pageSize = 50;
    const start = (inspectorPage - 1) * pageSize;
    return filteredModels.slice(start, start + pageSize);
  };

  const inspectorColumns = getDisplayedColumns();
  const inspectorDataSlice = getInspectorPageData();
  const inspectorTotalPages = Math.ceil(filteredModels.length / 50);

  return (
    <div className="db-browser-content">
      <div className="db-controls">
        <div className="mode-toggle-group">
            <button 
                className={!inspectorMode ? 'active' : ''}
                onClick={() => { setInspectorMode(false); setViewMode('table'); }}
            >
                DB Tables
            </button>
            <button 
                className={inspectorMode ? 'active' : ''}
                onClick={() => { setInspectorMode(true); setViewMode('table'); }}
            >
                ✨ Data Inspector
            </button>
        </div>

        {!inspectorMode ? (
            <>
                <select value={currentTable} onChange={handleTableChange} className="table-select">
                <option value="">Select Table...</option>
                {tables.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                
                <div className="view-toggle">
                    <button 
                        className={viewMode === 'table' ? 'active' : ''} 
                        onClick={() => setViewMode('table')}
                        disabled={!currentTable}
                    >
                        Table View
                    </button>
                    <button 
                        className={viewMode === 'single' ? 'active' : ''} 
                        onClick={() => {
                            if(tableData.length > 0) setViewMode('single');
                        }}
                        disabled={!currentTable || tableData.length === 0}
                    >
                        Single Record
                    </button>
                </div>

                <span className="record-count">
                {totalCount} rows found
                </span>

                {/* Filter Controls */}
                {currentTable && columns.length > 0 && (
                  <div className="table-filter-controls" style={{ marginLeft: '20px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <select 
                          value={tableFilters.column} 
                          onChange={(e) => handleFilterChange('column', e.target.value)}
                          className="table-select"
                          style={{ minWidth: '150px', padding: '6px' }}
                      >
                          <option value="">Filter Column...</option>
                          {columns.map(col => <option key={col} value={col}>{col}</option>)}
                      </select>
                      <input 
                          type="text" 
                          placeholder="Value..." 
                          value={tableFilters.value}
                          onChange={(e) => handleFilterChange('value', e.target.value)}
                          onKeyDown={(e) => e.key === 'Enter' && applyFilter()}
                          style={{ padding: '6px', borderRadius: '4px', border: '1px solid #ced4da', width: '150px' }}
                      />
                      <button onClick={applyFilter} style={{ padding: '6px 12px', cursor: 'pointer' }}>Filter</button>
                      {(tableFilters.column || tableFilters.value) && (
                          <button onClick={clearFilter} style={{ padding: '6px 12px', cursor: 'pointer', background: '#e9ecef', border: 'none' }}>Clear</button>
                      )}
                  </div>
                )}
            </>
        ) : (
            // Inspector Toolbar
            <div className="inspector-toolbar">
                <select 
                    value={inspectorFilters.view}
                    onChange={(e) => setInspectorFilters(prev => ({...prev, view: e.target.value}))}
                    className="inspector-select"
                >
                    <option value="unified">Unified View</option>
                    <option value="raw">Raw Data View</option>
                    <option value="all">All Variables</option>
                </select>

                <select
                    value={inspectorFilters.provider}
                    onChange={(e) => setInspectorFilters(prev => ({...prev, provider: e.target.value}))}
                    className="inspector-select"
                >
                    <option value="all">All Providers</option>
                    {uniqueProviders.map(p => <option key={p} value={p}>{p}</option>)}
                </select>

                 {/* Variable Filter (Filter 2) */}
                 <select 
                    className="inspector-select"
                    value={inspectorFilters.variable}
                    onChange={(e) => setInspectorFilters(prev => ({...prev, variable: e.target.value, value: 'all'}))}
                 >
                    <option value="all">Filter by Variable...</option>
                    {uniqueVariables.map(v => <option key={v} value={v}>{v}</option>)}
                 </select>

                 {/* Value Filter (Filter 3) */}
                 {inspectorFilters.variable !== 'all' && (
                     <select 
                        className="inspector-select"
                        value={inspectorFilters.value}
                        onChange={(e) => setInspectorFilters(prev => ({...prev, value: e.target.value}))}
                     >
                        <option value="all">Select Value...</option>
                        {uniqueValues.map(v => <option key={v} value={v}>{v}</option>)}
                     </select>
                 )}

                <input 
                    type="text" 
                    placeholder="Search models..." 
                    value={inspectorFilters.search}
                    onChange={(e) => setInspectorFilters(prev => ({...prev, search: e.target.value}))}
                    className="inspector-search"
                />
                
                <span className="record-count">
                    {filteredModels.length} models
                </span>
                
                <button 
                    disabled={selectedIds.size < 2} 
                    onClick={() => setShowCompare(true)}
                    style={{padding: '8px 16px', cursor: 'pointer'}}
                >
                    Compare ({selectedIds.size})
                </button>
            </div>
        )}
      </div>

      {error && <div className="db-error">{error}</div>}
      
      {loading && <div className="db-loading">Loading...</div>}

      {/* Legacy DB Table View */}
      {!inspectorMode && !loading && currentTable && tableData.length === 0 && (
        <div className="db-empty">Table is empty</div>
      )}

      {!inspectorMode && !loading && tableData.length > 0 && viewMode === 'table' && (
        <>
          <div className="table-container">
            <table className="db-table">
              <thead>
                <tr>
                  {columns.map(col => <th key={col}>{col}</th>)}
                </tr>
              </thead>
              <tbody>
                {tableData.map((row, i) => (
                  <tr key={i} onClick={() => handleRecordClick(i)} className="clickable-row">
                    {columns.map(col => (
                      <td key={`${i}-${col}`}>
                        <div className="cell-content">
                            {row[col] === null ? 'NULL' : String(row[col])}
                        </div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <button disabled={page <= 1} onClick={() => handlePageChange(page - 1)}>Previous</button>
            <span>Page {page} of {totalPages}</span>
            <button disabled={page >= totalPages} onClick={() => handlePageChange(page + 1)}>Next</button>
          </div>
        </>
      )}

      {!inspectorMode && !loading && tableData.length > 0 && viewMode === 'single' && (
        <div className="single-record-view">
          {/* ... existing single record view code ... */}
          <div className="record-navigation">
            <button onClick={() => jumpToRecord(-100)} title="-100 Records">-100</button>
            <button onClick={() => jumpToRecord(-10)} title="-10 Records">-10</button>
            <button onClick={handlePrevRecord} disabled={page === 1 && currentRecordIndex === 0}>
              &larr; Previous Record
            </button>
            <span>
                Record {((page - 1) * 50) + currentRecordIndex + 1} of {totalCount}
            </span>
            <button onClick={handleNextRecord} disabled={page === totalPages && currentRecordIndex === tableData.length - 1}>
              Next Record &rarr;
            </button>
            <button onClick={() => jumpToRecord(10)} title="+10 Records">+10</button>
            <button onClick={() => jumpToRecord(100)} title="+100 Records">+100</button>
          </div>
          
          <div className="record-details-container">
             <div className="record-details">
                {columns.map(col => (
                  <div key={col} className="record-field">
                    <div className="field-label">{col}</div>
                    <div className="field-value">
                        {tableData[currentRecordIndex][col] === null ? 
                            <span className="null-value">NULL</span> : 
                            String(tableData[currentRecordIndex][col])}
                    </div>
                  </div>
                ))}
             </div>
          </div>
        </div>
      )}

      {/* Inspector View - Table */}
      {inspectorMode && !loading && !showCompare && viewMode === 'table' && (
          <>
            <div className="table-container">
                <table className="db-table inspector-table">
                    <thead>
                        <tr>
                            <th style={{width: '40px'}}></th>
                            {inspectorColumns.map(col => <th key={col}>{col}</th>)}
                        </tr>
                    </thead>
                    <tbody>
                        {inspectorDataSlice.map((row, i) => (
                            <tr key={i} onClick={() => handleInspectorRecordClick(i)} className="clickable-row">
                                <td onClick={(e) => e.stopPropagation()}>
                                    <input 
                                        type="checkbox" 
                                        checked={selectedIds.has(row.id)} 
                                        onChange={(e) => toggleSelection(row.id, e)}
                                    />
                                </td>
                                {inspectorColumns.map(col => (
                                    <td key={col}>
                                        <div className="cell-content">
                                            {typeof row[col] === 'object' && row[col] !== null 
                                                ? JSON.stringify(row[col]) 
                                                : String(row[col] || '')}
                                        </div>
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            <div className="pagination inspector-pagination">
                <button 
                    disabled={inspectorPage <= 1} 
                    onClick={() => setInspectorPage(1)}
                    title="First Page"
                >
                    &lt;&lt;
                </button>
                <button 
                    disabled={inspectorPage <= 1} 
                    onClick={() => setInspectorPage(prev => prev - 1)}
                >
                    Previous
                </button>
                
                <span className="page-info">Page {inspectorPage} of {inspectorTotalPages}</span>
                
                <button 
                    disabled={inspectorPage >= inspectorTotalPages} 
                    onClick={() => setInspectorPage(prev => prev + 1)}
                >
                    Next
                </button>
            </div>
          </>
      )}

      {/* Inspector Compare View */}
      {inspectorMode && !loading && showCompare && (
          <div className="compare-view-container" style={{display: 'flex', flexDirection: 'column', height: '100%'}}>
              <div className="record-navigation">
                  <button onClick={() => setShowCompare(false)}>Back to List</button>
                  <label style={{marginLeft: '20px', display: 'flex', alignItems: 'center', cursor: 'pointer'}}>
                      <input 
                          type="checkbox" 
                          checked={diffOnly} 
                          onChange={(e) => setDiffOnly(e.target.checked)}
                          style={{marginRight: '5px'}}
                      /> 
                      Show Diff Only
                  </label>
              </div>
              <div className="table-container">
                  <table className="db-table">
                      <thead>
                          <tr>
                              <th style={{width: '150px', background: '#f8f9fa'}}>Field</th>
                              {getCompareData().models.map(m => (
                                  <th key={m.id}>{m.base_model_name || m.variant_name || m.id}</th>
                              ))}
                          </tr>
                      </thead>
                      <tbody>
                          {getCompareData().keys.map(key => (
                              <tr key={key}>
                                  <td style={{fontWeight: '600', background: '#f8f9fa'}}>{key}</td>
                                  {getCompareData().models.map(m => (
                                      <td key={`${m.id}-${key}`}>
                                           <div className="cell-content" style={{whiteSpace: 'pre-wrap'}}>
                                              {typeof m[key] === 'object' && m[key] !== null 
                                                  ? JSON.stringify(m[key], null, 2) 
                                                  : String(m[key] === null || m[key] === undefined ? '' : m[key])}
                                           </div>
                                      </td>
                                  ))}
                              </tr>
                          ))}
                      </tbody>
                  </table>
              </div>
          </div>
      )}

      {/* Inspector Single Record View */}
      {inspectorMode && !loading && !showCompare && filteredModels.length > 0 && viewMode === 'single' && (
        <div className="single-record-view">
          <div className="record-navigation">
            <button onClick={() => setViewMode('table')}>Back to Table</button>
            <div style={{flex: 1}}></div>
            <button onClick={() => jumpToRecord(-100)} title="-100 Records">-100</button>
            <button onClick={() => jumpToRecord(-10)} title="-10 Records">-10</button>
            <button onClick={() => jumpToRecord(-1)} disabled={currentRecordIndex === 0}>
              &larr; Previous
            </button>
            <span style={{margin: '0 10px'}}>
                Record {currentRecordIndex + 1} of {filteredModels.length}
            </span>
            <button onClick={() => jumpToRecord(1)} disabled={currentRecordIndex >= filteredModels.length - 1}>
              Next &rarr;
            </button>
            <button onClick={() => jumpToRecord(10)} title="+10 Records">+10</button>
            <button onClick={() => jumpToRecord(100)} title="+100 Records">+100</button>
          </div>
          
          <div className="record-details-container">
             <div className="record-details">
                {Object.keys(filteredModels[currentRecordIndex] || {}).sort().map(col => (
                  <div key={col} className="record-field">
                    <div className="field-label">{col}</div>
                    <div className="field-value">
                        {typeof filteredModels[currentRecordIndex][col] === 'object' && filteredModels[currentRecordIndex][col] !== null ?
                            JSON.stringify(filteredModels[currentRecordIndex][col], null, 2) :
                            (filteredModels[currentRecordIndex][col] === null ? 
                                <span className="null-value">NULL</span> : 
                                String(filteredModels[currentRecordIndex][col]))}
                    </div>
                  </div>
                ))}
             </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default DbBrowser;
