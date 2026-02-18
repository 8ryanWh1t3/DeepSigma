import { useMemo, useState } from 'react';
import { useOverwatchStore, type MGNode } from '../store';

const KIND_COLORS: Record<string, string> = {
  EPISODE: '#3b82f6',   // blue
  ACTION: '#10b981',    // green
  DRIFT: '#f59e0b',     // yellow
  PATCH: '#a855f7',     // purple
  EVIDENCE: '#64748b',  // gray
  CLAIM: '#06b6d4',     // cyan
};

const EDGE_COLORS: Record<string, string> = {
  PRODUCED: '#475569',
  TRIGGERED: '#ef4444',
  RESOLVED_BY: '#10b981',
  EVIDENCE_OF: '#64748b',
  RECURRENCE: '#f59e0b',
  CAUSED: '#ef4444',
  CLAIM_SUPPORTS: '#06b6d4',
  CLAIM_CONTRADICTS: '#ef4444',
};

function getColor(kind: string): string {
  return KIND_COLORS[kind] || '#94a3b8';
}

function getEdgeColor(kind: string): string {
  return EDGE_COLORS[kind] || '#475569';
}

interface NodePosition {
  x: number;
  y: number;
}

/**
 * Simple force-directed-ish layout via circle packing.
 * For a full d3-force simulation, add react-force-graph dependency.
 */
function computeLayout(nodes: MGNode[]): Map<string, NodePosition> {
  const positions = new Map<string, NodePosition>();
  const cx = 400, cy = 300;
  const radius = Math.min(250, nodes.length * 8);

  nodes.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / Math.max(nodes.length, 1);
    positions.set(node.node_id, {
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
    });
  });

  return positions;
}

export function MGGraphView() {
  const mgNodes = useOverwatchStore((s) => s.mgNodes);
  const mgEdges = useOverwatchStore((s) => s.mgEdges);
  const [selectedNode, setSelectedNode] = useState<MGNode | null>(null);

  const positions = useMemo(() => computeLayout(mgNodes), [mgNodes]);

  // Group nodes by kind for legend
  const kindCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    mgNodes.forEach((n) => {
      counts[n.kind] = (counts[n.kind] || 0) + 1;
    });
    return counts;
  }, [mgNodes]);

  if (mgNodes.length === 0) {
    return (
      <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 text-center">
        <h3 className="text-lg font-semibold mb-2">Memory Graph</h3>
        <p className="text-slate-400 text-sm">
          No graph data available. Connect to the API server to see the live Memory Graph.
        </p>
        <p className="text-slate-500 text-xs mt-2">
          Start the API: <code className="text-blue-400">python dashboard/api_server.py</code>
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Stats bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4 text-center">
          <div className="text-2xl font-bold text-blue-400">{mgNodes.length}</div>
          <div className="text-xs text-slate-400">Nodes</div>
        </div>
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4 text-center">
          <div className="text-2xl font-bold text-purple-400">{mgEdges.length}</div>
          <div className="text-xs text-slate-400">Edges</div>
        </div>
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4 text-center">
          <div className="text-2xl font-bold text-green-400">{Object.keys(kindCounts).length}</div>
          <div className="text-xs text-slate-400">Node Types</div>
        </div>
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4 text-center">
          <div className="text-2xl font-bold text-yellow-400">
            {mgNodes.filter((n) => n.kind === 'DRIFT').length}
          </div>
          <div className="text-xs text-slate-400">Drift Nodes</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Graph SVG */}
        <div className="lg:col-span-2 bg-slate-900 rounded-lg border border-slate-800 p-4">
          <h3 className="text-lg font-semibold mb-3">Memory Graph</h3>
          <svg viewBox="0 0 800 600" className="w-full h-auto bg-slate-950 rounded">
            {/* Edges */}
            {mgEdges.map((edge, i) => {
              const from = positions.get(edge.source_id);
              const to = positions.get(edge.target_id);
              if (!from || !to) return null;
              return (
                <line
                  key={`e-${i}`}
                  x1={from.x} y1={from.y}
                  x2={to.x} y2={to.y}
                  stroke={getEdgeColor(edge.kind)}
                  strokeWidth={1}
                  strokeOpacity={0.5}
                />
              );
            })}
            {/* Nodes */}
            {mgNodes.map((node) => {
              const pos = positions.get(node.node_id);
              if (!pos) return null;
              const isSelected = selectedNode?.node_id === node.node_id;
              return (
                <g key={node.node_id} onClick={() => setSelectedNode(node)} style={{ cursor: 'pointer' }}>
                  <circle
                    cx={pos.x} cy={pos.y}
                    r={isSelected ? 8 : 5}
                    fill={getColor(node.kind)}
                    stroke={isSelected ? '#fff' : 'none'}
                    strokeWidth={2}
                  />
                  <title>{`${node.kind}: ${node.label}`}</title>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Details panel */}
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
          <h3 className="text-lg font-semibold mb-3">
            {selectedNode ? 'Node Details' : 'Legend'}
          </h3>

          {selectedNode ? (
            <div className="space-y-3 text-sm">
              <div>
                <span className="text-slate-400">ID:</span>{' '}
                <span className="font-mono text-xs">{selectedNode.node_id}</span>
              </div>
              <div>
                <span className="text-slate-400">Kind:</span>{' '}
                <span
                  className="px-2 py-0.5 rounded text-xs font-medium"
                  style={{ backgroundColor: getColor(selectedNode.kind) + '33', color: getColor(selectedNode.kind) }}
                >
                  {selectedNode.kind}
                </span>
              </div>
              <div>
                <span className="text-slate-400">Label:</span> {selectedNode.label}
              </div>
              {selectedNode.timestamp && (
                <div>
                  <span className="text-slate-400">Timestamp:</span>{' '}
                  <span className="text-xs">{selectedNode.timestamp}</span>
                </div>
              )}
              <div>
                <span className="text-slate-400">Properties:</span>
                <pre className="mt-1 text-xs bg-slate-800 p-2 rounded overflow-auto max-h-48">
                  {JSON.stringify(selectedNode.properties, null, 2)}
                </pre>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-xs text-blue-400 hover:text-blue-300"
              >
                Clear selection
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {Object.entries(kindCounts).map(([kind, count]) => (
                <div key={kind} className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: getColor(kind) }}
                  />
                  <span className="text-sm">{kind}</span>
                  <span className="text-xs text-slate-500 ml-auto">{count}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
