import React, { useEffect, useCallback } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

export default function BlueprintTree({ sessionState }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    if (!sessionState || !sessionState.blueprint || !sessionState.blueprint.tasks) {
      // Default initial state
      setNodes([
        {
          id: 'start',
          type: 'input',
          data: { label: '🚀 Start Mission' },
          position: { x: 250, y: 5 },
          style: { background: '#007bff', color: '#fff', borderRadius: '8px', fontWeight: 'bold' }
        }
      ]);
      setEdges([]);
      return;
    }

    const { tasks } = sessionState.blueprint;
    const currentIndex = sessionState.current_task_index || 0;

    const newNodes = [
      {
        id: 'start',
        type: 'input',
        data: { label: '🚀 Start Mission' },
        position: { x: 250, y: 5 },
        style: { background: '#28a745', color: '#fff', borderRadius: '8px', fontWeight: 'bold' }
      }
    ];

    const newEdges = [];

    tasks.forEach((task, index) => {
      const isCompleted = index < currentIndex;
      const isActive = index === currentIndex;
      
      const nodeStyle = {
        background: isActive ? '#007bff' : (isCompleted ? '#28a745' : '#6c757d'),
        color: '#fff',
        borderRadius: '8px',
        border: isActive ? '3px solid #ffc107' : 'none',
        opacity: isCompleted || isActive ? 1 : 0.6,
        padding: '10px',
        width: 180,
        textAlign: 'center'
      };

      newNodes.push({
        id: task.id,
        data: { 
          label: (
            <div>
              <div style={{ fontSize: '10px', opacity: 0.8 }}>{task.type}</div>
              <div style={{ fontWeight: 'bold' }}>{task.label}</div>
              {task.breakpoint && <div style={{ fontSize: '10px', color: '#ffc107' }}>🛑 Breakpoint</div>}
            </div>
          )
        },
        position: { x: 250, y: (index + 1) * 100 + 5 },
        style: nodeStyle
      });

      // Connect to previous task or start
      const sourceId = index === 0 ? 'start' : tasks[index - 1].id;
      newEdges.push({
        id: `e-${sourceId}-${task.id}`,
        source: sourceId,
        target: task.id,
        animated: isActive,
        style: { stroke: isCompleted ? '#28a745' : (isActive ? '#007bff' : '#ccc') },
        markerEnd: { type: MarkerType.ArrowClosed, color: isCompleted ? '#28a745' : (isActive ? '#007bff' : '#ccc') }
      });
    });

    setNodes(newNodes);
    setEdges(newEdges);
  }, [sessionState]);

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge({ ...params, markerEnd: { type: MarkerType.ArrowClosed } }, eds)),
    [setEdges],
  );

  return (
    <div style={{ width: '100%', height: '100%', background: '#1e1e1e' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        fitView
      >
        <Controls />
        <MiniMap />
        <Background variant="dots" gap={12} size={1} color="#333" />
      </ReactFlow>
    </div>
  );
}
