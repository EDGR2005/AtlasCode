import { useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { Component, Relationship } from '../types/knowledge';

interface Props {
  components: Component[];
  relationships: Relationship[];
}

const NODE_WIDTH = 160;
const NODE_HEIGHT = 48;
const COLS = 4;
const COL_GAP = 200;
const ROW_GAP = 100;

export default function ArchitectureGraph({ components, relationships }: Props) {
  const hasData = components.length > 0 || relationships.length > 0;

  // When no components are explicitly detected, synthesise nodes from relationship endpoints
  const effectiveComponents = useMemo<Component[]>(() => {
    if (components.length > 0) return components;
    const seen = new Set<string>();
    const synth: Component[] = [];
    for (const r of relationships) {
      for (const id of [r.from_component, r.to_component]) {
        if (!seen.has(id)) {
          seen.add(id);
          // Use the last path segment as a readable label
          const name = id.split('/').pop() ?? id;
          synth.push({ name, path: id, type: 'unknown' });
        }
      }
    }
    return synth;
  }, [components, relationships]);

  const initialNodes = useMemo<Node[]>(() => {
    return effectiveComponents.map((c, i) => ({
      id: c.path || c.name,
      position: {
        x: (i % COLS) * COL_GAP,
        y: Math.floor(i / COLS) * ROW_GAP,
      },
      data: { label: c.name },
      style: {
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        color: 'var(--text)',
        borderRadius: 'var(--radius)',
        fontSize: '12px',
        width: NODE_WIDTH,
        height: NODE_HEIGHT,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      },
    }));
  }, [effectiveComponents]);

  const initialEdges = useMemo<Edge[]>(() => {
    return relationships.map((r, i) => ({
      id: `e-${i}`,
      source: r.from_component,
      target: r.to_component,
      label: r.type,
      animated: false,
      style: r.inferred
        ? { stroke: 'var(--text-muted)', strokeDasharray: '5,4' }
        : { stroke: 'var(--accent)' },
      labelStyle: { fill: 'var(--text-muted)', fontSize: '11px' },
      labelBgStyle: { fill: 'var(--surface)', fillOpacity: 0.85 },
    }));
  }, [relationships]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  if (!hasData) {
    return (
      <div className="arch-placeholder">
        <p>No architecture data detected.</p>
        <p className="arch-placeholder-hint">
          Add TypeScript or Python files with imports to see relationships.
        </p>
      </div>
    );
  }

  return (
    <div className="arch-graph-wrap">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        colorMode="dark"
      >
        <Background color="var(--border)" gap={24} />
        <Controls />
      </ReactFlow>
    </div>
  );
}
