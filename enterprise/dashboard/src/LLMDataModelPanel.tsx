/**
 * LLM Data Model Panel — canonical record schema overview.
 * Displays record types, field coverage, and validation status.
 */
import React, { useState, useEffect } from "react";

interface RecordType {
  name: string;
  description: string;
  fieldCount: number;
  exampleCount: number;
  status: "validated" | "draft" | "planned";
}

const recordTypes: RecordType[] = [
  { name: "Claim Record", description: "Truth assertions with evidence chains and confidence", fieldCount: 12, exampleCount: 1, status: "validated" },
  { name: "Decision Episode", description: "Sealed DTE-governed decision with outcome and verification", fieldCount: 18, exampleCount: 1, status: "validated" },
  { name: "Document Record", description: "Source document metadata with provenance and TTL", fieldCount: 14, exampleCount: 1, status: "validated" },
  { name: "Event Record", description: "Timestamped system events with causal links", fieldCount: 10, exampleCount: 1, status: "validated" },
  { name: "Entity Record", description: "Domain entity with attributes and relationships", fieldCount: 11, exampleCount: 1, status: "validated" },
  { name: "Metric Record", description: "Quantitative measurements with dimensions and thresholds", fieldCount: 9, exampleCount: 1, status: "validated" },
];

const modules = [
  { name: "01 Overview", files: 2, status: "complete" },
  { name: "02 Schema", files: 3, status: "complete" },
  { name: "03 Examples", files: 6, status: "complete" },
  { name: "04 Mappings", files: 4, status: "complete" },
  { name: "05 Validation", files: 2, status: "complete" },
  { name: "06 Ontology", files: 2, status: "complete" },
  { name: "07 Retrieval", files: 2, status: "complete" },
  { name: "08 Governance", files: 2, status: "complete" },
  { name: "09 Connectors", files: 2, status: "complete" },
  { name: "10 Changelog", files: 1, status: "complete" },
];

const statusBadge = (s: string) => {
  if (s === "validated" || s === "complete") return "bg-green-900/50 text-green-300";
  if (s === "draft") return "bg-yellow-900/50 text-yellow-300";
  return "bg-slate-700 text-slate-300";
};

export const LLMDataModelPanel: React.FC = () => {
  const totalFields = recordTypes.reduce((s, r) => s + r.fieldCount, 0);
  const totalExamples = recordTypes.reduce((s, r) => s + r.exampleCount, 0);
  const [stats, setStats] = useState<{ total_records: number; sealed_count: number; seal_rate: number; by_type: Record<string, number> } | null>(null);

  useEffect(() => {
    fetch('/api/records/stats')
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setStats(data); })
      .catch(() => {});
  }, []);

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">LLM Data Model — Canonical Records</h2>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
          <div className="text-sm text-slate-400">Record Types</div>
          <div className="text-2xl font-bold">{recordTypes.length}</div>
        </div>
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
          <div className="text-sm text-slate-400">Total Fields</div>
          <div className="text-2xl font-bold">{totalFields}</div>
        </div>
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
          <div className="text-sm text-slate-400">Examples</div>
          <div className="text-2xl font-bold">{totalExamples}</div>
        </div>
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
          <div className="text-sm text-slate-400">Modules</div>
          <div className="text-2xl font-bold">{modules.length}</div>
        </div>
        {stats && (
          <>
            <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
              <div className="text-sm text-slate-400">Live Records</div>
              <div className="text-2xl font-bold">{stats.total_records}</div>
            </div>
            <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
              <div className="text-sm text-slate-400">Sealed</div>
              <div className="text-2xl font-bold">{Math.round(stats.seal_rate * 100)}%</div>
            </div>
          </>
        )}
      </div>

      {/* Record types table */}
      <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
        <h3 className="text-base font-semibold mb-4">Canonical Record Types</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-700">
              <tr>
                <th className="text-left py-2 px-3 text-slate-300">Record Type</th>
                <th className="text-left py-2 px-3 text-slate-300">Description</th>
                <th className="text-left py-2 px-3 text-slate-300">Fields</th>
                <th className="text-left py-2 px-3 text-slate-300">Examples</th>
                <th className="text-left py-2 px-3 text-slate-300">Status</th>
              </tr>
            </thead>
            <tbody>
              {recordTypes.map((rt) => (
                <tr key={rt.name} className="border-b border-slate-800 hover:bg-slate-800 transition-colors">
                  <td className="py-2 px-3 font-medium">{rt.name}</td>
                  <td className="py-2 px-3 text-slate-400">{rt.description}</td>
                  <td className="py-2 px-3">{rt.fieldCount}</td>
                  <td className="py-2 px-3">{rt.exampleCount}</td>
                  <td className="py-2 px-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${statusBadge(rt.status)}`}>
                      {rt.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Module status */}
      <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
        <h3 className="text-base font-semibold mb-4">Module Structure</h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {modules.map((m) => (
            <div key={m.name} className="bg-slate-800 rounded-lg p-3 border border-slate-700">
              <div className="text-xs text-slate-400">{m.name}</div>
              <div className="flex items-center justify-between mt-1">
                <span className="font-bold">{m.files} files</span>
                <span className={`px-1.5 py-0.5 rounded text-xs ${statusBadge(m.status)}`}>{m.status}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Design principles */}
      <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
        <h3 className="text-base font-semibold mb-3">Design Principles</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
          <div className="bg-slate-800 rounded p-3">
            <div className="font-semibold text-blue-400 mb-1">Provenance</div>
            <div className="text-slate-400">Every record traces back to its source with evidence chains</div>
          </div>
          <div className="bg-slate-800 rounded p-3">
            <div className="font-semibold text-emerald-400 mb-1">TTL &amp; Freshness</div>
            <div className="text-slate-400">Records carry time-to-live and expiry for staleness detection</div>
          </div>
          <div className="bg-slate-800 rounded p-3">
            <div className="font-semibold text-purple-400 mb-1">Sealing</div>
            <div className="text-slate-400">Immutable seals with SHA-256 hashes for tamper evidence</div>
          </div>
          <div className="bg-slate-800 rounded p-3">
            <div className="font-semibold text-yellow-400 mb-1">Patching</div>
            <div className="text-slate-400">Version-controlled patches with lineage tracking</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LLMDataModelPanel;
