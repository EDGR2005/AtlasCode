import { useMemo, useCallback } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ReactFlowProvider,
  type Node,
  type Edge,
  type NodeProps,
  Handle,
  Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { DatabaseSchema, DbTable, DbColumn } from '../types/knowledge';

interface Props {
  schema: DatabaseSchema;
}

// ---------------------------------------------------------------------------
// Custom table node
// ---------------------------------------------------------------------------

interface TableNodeData {
  table: DbTable;
  [key: string]: unknown;
}

function TableNode({ data }: NodeProps) {
  const { table } = data as TableNodeData;
  return (
    <div className="db-table-node">
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <div className="db-table-header">
        <span className="db-table-name">{table.name}</span>
        <span className="db-table-source">{table.source_type}</span>
      </div>
      <div className="db-table-columns">
        {table.columns.map((col: DbColumn) => (
          <div key={col.name} className={`db-col-row${col.primary_key ? ' db-col-pk' : ''}`}>
            <span className="db-col-badges">
              {col.primary_key && <span className="db-badge db-badge-pk">PK</span>}
              {col.foreign_key && <span className="db-badge db-badge-fk">FK</span>}
              {col.unique && !col.primary_key && <span className="db-badge db-badge-u">U</span>}
            </span>
            <span className="db-col-name">{col.name}</span>
            <span className="db-col-type">{col.data_type ?? '—'}</span>
            {col.nullable && <span className="db-col-null" title="nullable">?</span>}
          </div>
        ))}
        {table.columns.length === 0 && (
          <div className="db-col-row db-col-empty">no columns detected</div>
        )}
      </div>
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
}

const nodeTypes = { tableNode: TableNode };

// ---------------------------------------------------------------------------
// Layout: simple grid with spacing proportional to column count
// ---------------------------------------------------------------------------

const TABLE_WIDTH = 260;
const TABLE_BASE_HEIGHT = 80;
const COL_ROW_HEIGHT = 24;
const H_GAP = 80;
const V_GAP = 60;
const COLS = 3;

function computeHeight(table: DbTable): number {
  return TABLE_BASE_HEIGHT + table.columns.length * COL_ROW_HEIGHT;
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function DatabasePanel({ schema }: Props) {
  if (!schema.detected || schema.tables.length === 0) {
    return (
      <div className="db-placeholder">
        <p>No database schema detected in this repository.</p>
        <p className="db-placeholder-hint">
          Supported sources: SQL files, SQLAlchemy, Django ORM, Prisma.
        </p>
      </div>
    );
  }

  return (
    <ReactFlowProvider>
      <DatabaseGraph schema={schema} />
    </ReactFlowProvider>
  );
}

function DatabaseGraph({ schema }: Props) {
  const { fitView } = useReactFlow();

  const initialNodes = useMemo<Node[]>(() => {
    let yOffset = 0;
    let colHeights: number[] = Array(COLS).fill(0);

    return schema.tables.map((table, i) => {
      const col = i % COLS;
      if (col === 0 && i > 0) {
        yOffset += Math.max(...colHeights) + V_GAP;
        colHeights = Array(COLS).fill(0);
      }
      const h = computeHeight(table);
      colHeights[col] = h;

      const x = col * (TABLE_WIDTH + H_GAP);
      const y = yOffset;

      return {
        id: table.name,
        type: 'tableNode',
        position: { x, y },
        data: { table },
        style: { width: TABLE_WIDTH },
      };
    });
  }, [schema.tables]);

  const initialEdges = useMemo<Edge[]>(() => {
    return schema.relationships.map((r, i) => ({
      id: `dbe-${i}`,
      source: r.from_table,
      target: r.to_table,
      label: r.relationship_type !== 'unknown' ? r.relationship_type.replace('_', ':') : undefined,
      animated: false,
      style: r.inferred
        ? { stroke: 'var(--text-muted)', strokeDasharray: '5,4' }
        : { stroke: 'var(--accent)' },
      labelStyle: { fill: 'var(--text-muted)', fontSize: '10px' },
      labelBgStyle: { fill: 'var(--surface)', fillOpacity: 0.9 },
    }));
  }, [schema.relationships]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const onInit = useCallback(() => {
    setTimeout(() => fitView({ padding: 0.15 }), 50);
  }, [fitView]);

  return (
    <div className="db-panel">
      <div className="db-stats">
        <span>{schema.tables.length} table{schema.tables.length !== 1 ? 's' : ''}</span>
        <span>{schema.relationships.length} relationship{schema.relationships.length !== 1 ? 's' : ''}</span>
      </div>
      <div className="db-graph-wrap">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          onInit={onInit}
          colorMode="dark"
          minZoom={0.2}
          maxZoom={2}
        >
          <Background color="var(--border)" gap={24} />
          <Controls />
          <MiniMap
            nodeColor="var(--surface)"
            maskColor="rgba(0,0,0,0.4)"
            style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
          />
        </ReactFlow>
      </div>
    </div>
  );
}
