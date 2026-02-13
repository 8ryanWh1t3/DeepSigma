/**
 * CoherenceOps Panel — DLR/RS/DS/MG pipeline health dashboard.
 * Keyboard shortcut: 5
 */
import React from "react";

interface PillarStatus {
  name: string;
  status: "active" | "degraded" | "offline";
  label: string;
  count: number;
  lastRun?: string;
}

interface CoherencePanelProps {
  pillars?: PillarStatus[];
  knowledgeGraph?: {
    nodeCount: number;
    edgeCount: number;
    nodesByKind: Record<string, number>;
    edgesByKind: Record<string, number>;
  };
}

const defaultPillars: PillarStatus[] = [
  { name: "DLR", status: "active", label: "Decision Log Records", count: 47, lastRun: "2m ago" },
  { name: "RS", status: "active", label: "Reflection Sessions", count: 12, lastRun: "5m ago" },
  { name: "DS", status: "active", label: "Drift Signals", count: 23, lastRun: "1m ago" },
  { name: "MG", status: "active", label: "Memory Graph", count: 156, lastRun: "30s ago" },
];

const defaultGraph = {
  nodeCount: 156,
  edgeCount: 234,
  nodesByKind: { episode: 47, action: 52, drift: 23, patch: 8, evidence: 26 },
  edgesByKind: { produced: 52, triggered: 23, resolved_by: 8, evidence_of: 26, recurrence: 5 },
};

const statusColor = (s: string) =>
  s === "active" ? "#22c55e" : s === "degraded" ? "#eab308" : "#ef4444";

export const CoherencePanel: React.FC<CoherencePanelProps> = ({
  pillars = defaultPillars,
  knowledgeGraph = defaultGraph,
}) => {
  return (
    <div style={{ padding: "1.5rem" }}>
      <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "1rem" }}>
        CoherenceOps Pipeline Status
      </h2>

      {/* Pillar cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "2rem" }}>
        {pillars.map((p) => (
          <div key={p.name} style={{
            border: "1px solid #374151", borderRadius: "0.5rem", padding: "1rem",
            background: "#1f2937",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontWeight: 700, fontSize: "1.1rem" }}>{p.name}</span>
              <span style={{
                width: 10, height: 10, borderRadius: "50%",
                background: statusColor(p.status), display: "inline-block",
              }} />
            </div>
            <div style={{ color: "#9ca3af", fontSize: "0.85rem" }}>{p.label}</div>
            <div style={{ marginTop: "0.5rem", fontSize: "1.5rem", fontWeight: 700 }}>{p.count}</div>
            {p.lastRun && <div style={{ color: "#6b7280", fontSize: "0.75rem" }}>Last run: {p.lastRun}</div>}
          </div>
        ))}
      </div>

      {/* Knowledge Graph Summary */}
      <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.75rem" }}>
        Knowledge Graph Summary
      </h3>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        <div style={{ border: "1px solid #374151", borderRadius: "0.5rem", padding: "1rem", background: "#1f2937" }}>
          <div style={{ fontSize: "0.85rem", color: "#9ca3af" }}>Nodes</div>
          <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{knowledgeGraph.nodeCount}</div>
          <div style={{ marginTop: "0.5rem" }}>
            {Object.entries(knowledgeGraph.nodesByKind).map(([k, v]) => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: "#d1d5db" }}>
                <span>{k}</span><span>{v}</span>
              </div>
            ))}
          </div>
        </div>
        <div style={{ border: "1px solid #374151", borderRadius: "0.5rem", padding: "1rem", background: "#1f2937" }}>
          <div style={{ fontSize: "0.85rem", color: "#9ca3af" }}>Edges</div>
          <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{knowledgeGraph.edgeCount}</div>
          <div style={{ marginTop: "0.5rem" }}>
            {Object.entries(knowledgeGraph.edgesByKind).map(([k, v]) => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: "#d1d5db" }}>
                <span>{k}</span><span>{v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CoherencePanel;
