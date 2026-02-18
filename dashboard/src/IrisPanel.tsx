/**
 * IrisPanel.tsx — IRIS Query Panel for the Σ OVERWATCH Dashboard.
 *
 * Provides an interactive operator interface for querying the IRIS
 * (Interface for Resolution, Insight, and Status) engine.  The operator
 * types a natural-language question, selects a query type, and receives
 * a structured response with full provenance chain and decision lineage.
 *
 * Wired to coherence_ops/iris.py via mock data in dev mode.
 */

import React, { useState, useMemo, useCallback } from 'react';
import { Search, ChevronRight, AlertCircle, CheckCircle, Info, XCircle, Clock, Shield, Link2, Eye, Activity } from 'lucide-react';
import {
    IRISQueryType,
    IRISResolutionStatus,
    IRISProvenanceLink,
    IRISResponse,
    resolveIRISQuery,
} from './mockData';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const QUERY_TYPE_META: Record<IRISQueryType, { label: string; icon: React.ReactNode; hint: string; color: string }> = {
    WHY:            { label: 'Why',           icon: <Eye size={16} />,      hint: 'Why did we decide X?',       color: 'blue'   },
    WHAT_CHANGED:   { label: 'What Changed',  icon: <Activity size={16} />, hint: 'What changed recently?',     color: 'purple' },
    WHAT_DRIFTED:   { label: 'What Drifted',  icon: <AlertCircle size={16} />, hint: "What's drifting?",        color: 'yellow' },
    RECALL:         { label: 'Recall',        icon: <Search size={16} />,   hint: 'What do we know about…?',   color: 'emerald'},
    STATUS:         { label: 'Status',        icon: <Shield size={16} />,   hint: 'How healthy are we?',       color: 'cyan'   },
};

const STATUS_STYLE: Record<IRISResolutionStatus, { bg: string; text: string; icon: React.ReactNode }> = {
    RESOLVED:  { bg: 'bg-green-900/30 border-green-700', text: 'text-green-400', icon: <CheckCircle size={16} className="text-green-400" /> },
    PARTIAL:   { bg: 'bg-yellow-900/30 border-yellow-700', text: 'text-yellow-400', icon: <Info size={16} className="text-yellow-400" /> },
    NOT_FOUND: { bg: 'bg-slate-800/50 border-slate-600', text: 'text-slate-400', icon: <XCircle size={16} className="text-slate-400" /> },
    ERROR:     { bg: 'bg-red-900/30 border-red-700', text: 'text-red-400', icon: <AlertCircle size={16} className="text-red-400" /> },
};

const ARTIFACT_COLORS: Record<string, string> = {
    MG:    'text-purple-400 bg-purple-900/30 border-purple-700',
    DLR:   'text-blue-400 bg-blue-900/30 border-blue-700',
    DS:    'text-yellow-400 bg-yellow-900/30 border-yellow-700',
    RS:    'text-emerald-400 bg-emerald-900/30 border-emerald-700',
    PRIME: 'text-cyan-400 bg-cyan-900/30 border-cyan-700',
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ConfidenceBar({ value }: { value: number }) {
    const pct = Math.round(value * 100);
    const color = pct >= 70 ? '#10b981' : pct >= 40 ? '#f59e0b' : '#ef4444';
    return (
          <div className="flex items-center gap-3">
                <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
                        <div
                                    className="h-full rounded-full transition-all duration-500"
                                    style={{ width: `${pct}%`, backgroundColor: color }}
                                  />
                </div>
                <span className="text-sm font-mono" style={{ color }}>{pct}%</span>
          </div>
        );
}

function ProvenanceChain({ chain }: { chain: IRISProvenanceLink[] }) {
    if (!chain.length) return null;
    return (
          <div className="space-y-2">
                <h4 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                        <Link2 size={14} className="text-slate-500" />
                        Provenance Chain ({chain.length} link{chain.length !== 1 ? 's' : ''})
                </h4>
                <div className="relative ml-3 border-l-2 border-slate-700 pl-4 space-y-3">
                  {chain.map((link, i) => {
                      const artStyle = ARTIFACT_COLORS[link.artifact] || 'text-slate-400 bg-slate-800 border-slate-600';
                      return (
                                    <div key={i} className="relative">
                                      {/* connector dot */}
                                                  <div className="absolute -left-[21px] top-1.5 w-2.5 h-2.5 rounded-full bg-slate-600 border-2 border-slate-900" />
                                                  <div className="flex items-start gap-2 flex-wrap">
                                                                  <span className={`px-1.5 py-0.5 rounded text-xs font-mono border ${artStyle}`}>
                                                                    {link.artifact}
                                                                  </span>
                                                                  <span className="text-xs text-slate-500 font-mono">{link.ref_id}</span>
                                                                  <span className="text-xs px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">{link.role}</span>
                                                  </div>
                                      {link.detail && (
                                                      <p className="text-xs text-slate-500 mt-0.5 ml-1">{link.detail}</p>
                                                  )}
                                    </div>
                                  );
          })}
                </div>
          </div>
        );
}

function DataSection({ title, children }: { title: string; children: React.ReactNode }) {
    return (
          <div className="bg-slate-800/50 rounded-lg border border-slate-700 p-4">
                <h4 className="text-sm font-semibold text-slate-300 mb-3">{title}</h4>
            {children}
          </div>
        );
}

function KeyValueRow({ label, value, mono }: { label: string; value: string | number; mono?: boolean }) {
    return (
          <div className="flex justify-between items-center py-1 border-b border-slate-700/50 last:border-0">
                <span className="text-xs text-slate-500">{label}</span>
                <span className={`text-sm text-slate-200 ${mono ? 'font-mono' : ''}`}>{value}</span>
          </div>
        );
}

// ---------------------------------------------------------------------------
// Response detail renderers (per query type)
// ---------------------------------------------------------------------------

function WhyDetail({ data }: { data: Record<string, any> }) {
    const mgProv = data.mg_provenance || {};
    const dlrEntry = data.dlr_entry || {};
    return (
          <div className="space-y-4">
            {mgProv.node && (
                    <DataSection title="Memory Graph Node">
                              <KeyValueRow label="Label" value={mgProv.node.label || '—'} />
                              <KeyValueRow label="Evidence Refs" value={(mgProv.evidence_refs || []).length} mono />
                              <KeyValueRow label="Actions" value={(mgProv.actions || []).length} mono />
                    </DataSection>
                )}
            {dlrEntry.dlr_id && (
                    <DataSection title="Decision Lineage Record">
                              <KeyValueRow label="DLR ID" value={dlrEntry.dlr_id} mono />
                              <KeyValueRow label="Decision Type" value={dlrEntry.decision_type || '—'} />
                              <KeyValueRow label="Outcome" value={dlrEntry.outcome_code || '—'} />
                              <KeyValueRow label="Policy Stamp" value={dlrEntry.policy_stamp ? 'Present' : 'Missing'} />
                              <KeyValueRow label="Degrade Step" value={dlrEntry.degrade_step || 'none'} />
                    </DataSection>
                )}
            {data.mg_drift && data.mg_drift.length > 0 && (
                    <DataSection title={`Linked Drift Events (${data.mg_drift.length})`}>
                      {data.mg_drift.slice(0, 5).map((d: any, i: number) => (
                                  <KeyValueRow key={i} label={d.type || `Drift ${i + 1}`} value={d.severity || 'unknown'} />
                                ))}
                    </DataSection>
                )}
          </div>
        );
}

function WhatChangedDetail({ data }: { data: Record<string, any> }) {
    const dist = data.outcome_distribution || {};
    return (
          <div className="space-y-4">
                <DataSection title="Change Summary">
                        <KeyValueRow label="Total Entries" value={data.total_entries || 0} mono />
                        <KeyValueRow label="Degraded Episodes" value={(data.degraded_episodes || []).length} mono />
                        <KeyValueRow label="Missing Policy" value={(data.policy_missing || []).length} mono />
                  {data.patch_count != null && <KeyValueRow label="Patches" value={data.patch_count} mono />}
                </DataSection>
            {Object.keys(dist).length > 0 && (
                    <DataSection title="Outcome Distribution">
                      {Object.entries(dist).map(([code, count]) => (
                                  <KeyValueRow key={code} label={code} value={count as number} mono />
                                ))}
                    </DataSection>
                )}
            {data.drift_summary && (
                    <DataSection title="Drift Summary">
                              <KeyValueRow label="Total Signals" value={data.drift_summary.total_signals || 0} mono />
                      {Object.entries(data.drift_summary.by_severity || {}).map(([sev, n]) => (
                                  <KeyValueRow key={sev} label={sev} value={n as number} mono />
                                ))}
                    </DataSection>
                )}
          </div>
        );
}

function WhatDriftedDetail({ data }: { data: Record<string, any> }) {
    return (
          <div className="space-y-4">
                <DataSection title="Drift Overview">
                        <KeyValueRow label="Total Signals" value={data.total_signals || 0} mono />
                  {Object.entries(data.by_severity || {}).map(([sev, n]) => (
                      <KeyValueRow key={sev} label={`Severity: ${sev}`} value={n as number} mono />
                    ))}
                  {data.resolution_ratio != null && (
                      <KeyValueRow label="Resolution Ratio" value={`${(data.resolution_ratio * 100).toFixed(1)}%`} />
                    )}
                </DataSection>
            {(data.top_buckets || []).length > 0 && (
                    <DataSection title={`Top Drift Fingerprints (${data.top_buckets.length})`}>
                      {data.top_buckets.slice(0, 5).map((b: any, i: number) => (
                                  <KeyValueRow key={i} label={b.fingerprint || `Bucket ${i + 1}`} value={`${b.count || 0} signal(s)`} />
                                ))}
                    </DataSection>
                )}
            {(data.top_recurring || []).length > 0 && (
                    <DataSection title="Top Recurring Patterns">
                      {data.top_recurring.slice(0, 5).map((pat: string, i: number) => (
                                  <div key={i} className="text-xs text-slate-400 py-0.5 font-mono">{pat}</div>
                                ))}
                    </DataSection>
                )}
          </div>
        );
}

function RecallDetail({ data }: { data: Record<string, any> }) {
    const prov = data.provenance || {};
    const dlrEntry = data.dlr_entry || {};
    return (
          <div className="space-y-4">
            {prov.node && (
                    <DataSection title="Memory Graph Recall">
                              <KeyValueRow label="Node Label" value={prov.node.label || '—'} />
                              <KeyValueRow label="Evidence Refs" value={(prov.evidence_refs || []).length} mono />
                              <KeyValueRow label="Actions" value={(prov.actions || []).length} mono />
                    </DataSection>
                )}
            {(data.drift_events || []).length > 0 && (
                    <DataSection title={`Drift Events (${data.drift_events.length})`}>
                      {data.drift_events.slice(0, 5).map((d: any, i: number) => (
                                  <KeyValueRow key={i} label={d.type || `Event ${i + 1}`} value={d.severity || 'unknown'} />
                                ))}
                    </DataSection>
                )}
            {(data.patches || []).length > 0 && (
                    <DataSection title={`Patches (${data.patches.length})`}>
                      {data.patches.slice(0, 5).map((p: any, i: number) => (
                                  <KeyValueRow key={i} label={p.patch_id || `Patch ${i + 1}`} value={p.status || 'applied'} />
                                ))}
                    </DataSection>
                )}
            {dlrEntry.dlr_id && (
                    <DataSection title="Decision Lineage Record">
                              <KeyValueRow label="DLR ID" value={dlrEntry.dlr_id} mono />
                              <KeyValueRow label="Decision Type" value={dlrEntry.decision_type || '—'} />
                              <KeyValueRow label="Outcome" value={dlrEntry.outcome_code || '—'} />
                    </DataSection>
                )}
          </div>
        );
}

function StatusDetail({ data }: { data: Record<string, any> }) {
    const dims = data.dimensions || [];
    return (
          <div className="space-y-4">
                <DataSection title="Coherence Score">
                        <KeyValueRow label="Overall Score" value={`${data.overall_score || 0}/100`} mono />
                        <KeyValueRow label="Grade" value={data.grade || '—'} />
                </DataSection>
            {dims.length > 0 && (
                    <DataSection title="Dimensions">
                      {dims.map((d: any, i: number) => (
                                  <div key={i} className="flex items-center justify-between py-1.5 border-b border-slate-700/50 last:border-0">
                                                <span className="text-xs text-slate-400">{d.name}</span>
                                                <div className="flex items-center gap-3">
                                                                <div className="w-20 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                                                                                  <div
                                                                                                        className="h-full rounded-full"
                                                                                                        style={{
                                                                                                                                width: `${d.score}%`,
                                                                                                                                background: d.score >= 70 ? '#10b981' : d.score >= 40 ? '#f59e0b' : '#ef4444',
                                                                                                          }}
                                                                                                      />
                                                                </div>
                                                                <span className="text-xs font-mono text-slate-300 w-12 text-right">{d.score.toFixed(1)}</span>
                                                </div>
                                  </div>
                                ))}
                    </DataSection>
                )}
            {data.mg_stats && (
                    <DataSection title="Memory Graph Stats">
                              <KeyValueRow label="Total Nodes" value={data.mg_stats.total_nodes || 0} mono />
                              <KeyValueRow label="Total Edges" value={data.mg_stats.total_edges || 0} mono />
                    </DataSection>
                )}
            {data.drift_headline && (
                    <DataSection title="Drift Headline">
                              <KeyValueRow label="Total" value={data.drift_headline.total || 0} mono />
                              <KeyValueRow label="Red" value={data.drift_headline.red || 0} mono />
                              <KeyValueRow label="Recurring" value={data.drift_headline.recurring || 0} mono />
                    </DataSection>
                )}
          </div>
        );
}

const DETAIL_RENDERERS: Record<IRISQueryType, React.FC<{ data: Record<string, any> }>> = {
    WHY: WhyDetail,
    WHAT_CHANGED: WhatChangedDetail,
    WHAT_DRIFTED: WhatDriftedDetail,
    RECALL: RecallDetail,
    STATUS: StatusDetail,
};

// ---------------------------------------------------------------------------
// Response display
// ---------------------------------------------------------------------------

function IRISResponseView({ response }: { response: IRISResponse }) {
    const sts = STATUS_STYLE[response.status];
    const DetailRenderer = DETAIL_RENDERERS[response.query_type];
    const meta = QUERY_TYPE_META[response.query_type];
  
    return (
          <div className="space-y-5 animate-fadeIn">
            {/* Header band */}
                <div className={`rounded-lg border p-4 ${sts.bg}`}>
                        <div className="flex items-center justify-between flex-wrap gap-3">
                                  <div className="flex items-center gap-3">
                                    {sts.icon}
                                              <div>
                                                            <div className={`text-sm font-semibold ${sts.text}`}>{response.status}</div>
                                                            <div className="text-xs text-slate-500 font-mono">Query ID: {response.query_id}</div>
                                              </div>
                                  </div>
                                  <div className="flex items-center gap-4 text-xs text-slate-500">
                                              <span className="flex items-center gap-1"><Clock size={12} />{response.elapsed_ms.toFixed(0)} ms</span>
                                              <span>{meta.label} query</span>
                                              <span>{new Date(response.resolved_at).toLocaleTimeString()}</span>
                                  </div>
                        </div>
                </div>
          
            {/* Confidence */}
                <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
                        <div className="text-xs text-slate-500 mb-1.5">Confidence</div>
                        <ConfidenceBar value={response.confidence} />
                </div>
          
            {/* Summary */}
                <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
                        <div className="text-xs text-slate-500 mb-1.5">Summary</div>
                        <p className="text-sm text-slate-200 leading-relaxed">{response.summary}</p>
                </div>
          
            {/* Warnings */}
            {response.warnings.length > 0 && (
                    <div className="bg-yellow-900/20 rounded-lg border border-yellow-800 p-4">
                              <div className="text-xs text-yellow-400 font-semibold mb-2">Warnings</div>
                      {response.warnings.map((w, i) => (
                                  <div key={i} className="text-xs text-yellow-300 flex items-start gap-2 py-0.5">
                                                <AlertCircle size={12} className="mt-0.5 shrink-0" />
                                    {w}
                                  </div>
                                ))}
                    </div>
                )}
          
            {/* Data detail */}
            {DetailRenderer && Object.keys(response.data).length > 0 && (
                    <DetailRenderer data={response.data} />
                  )}
          
            {/* Provenance chain */}
            {response.provenance_chain.length > 0 && (
                    <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
                              <ProvenanceChain chain={response.provenance_chain} />
                    </div>
                )}
          
            {/* Raw JSON toggle */}
                <RawJsonToggle response={response} />
          </div>
        );
}

function RawJsonToggle({ response }: { response: IRISResponse }) {
    const [open, setOpen] = useState(false);
    const json = useMemo(() => JSON.stringify(response, null, 2), [response]);
    return (
          <div className="bg-slate-900 rounded-lg border border-slate-800">
                <button
                          onClick={() => setOpen(o => !o)}
                          className="w-full flex items-center justify-between px-4 py-3 text-xs text-slate-500 hover:text-slate-300 transition-colors"
                        >
                        <span>Raw JSON Response</span>
                        <ChevronRight size={14} className={`transform transition-transform ${open ? 'rotate-90' : ''}`} />
                </button>
            {open && (
                    <pre className="px-4 pb-4 text-xs text-slate-400 font-mono overflow-x-auto max-h-80 overflow-y-auto whitespace-pre-wrap">
                      {json}
                    </pre>
                )}
          </div>
        );
}

// ---------------------------------------------------------------------------
// Query history sidebar
// ---------------------------------------------------------------------------

interface HistoryEntry {
    id: string;
    queryType: IRISQueryType;
    text: string;
    status: IRISResolutionStatus;
    confidence: number;
    timestamp: string;
    response: IRISResponse;
}

function QueryHistory({ entries, selected, onSelect }: { entries: HistoryEntry[]; selected: string | null; onSelect: (id: string) => void }) {
    if (!entries.length) {
          return (
                  <div className="text-xs text-slate-600 text-center py-8">
                          No queries yet. Ask IRIS a question above.
                  </div>
                );
    }
    return (
          <div className="space-y-2 max-h-[600px] overflow-y-auto">
            {entries.map(entry => {
                    const meta = QUERY_TYPE_META[entry.queryType];
                    const active = selected === entry.id;
                    return (
                                <button
                                              key={entry.id}
                                              onClick={() => onSelect(entry.id)}
                                              className={`w-full text-left p-3 rounded-lg border transition-colors ${
                                                              active
                                                                ? 'bg-blue-900/30 border-blue-700'
                                                                : 'bg-slate-800/50 border-slate-700 hover:bg-slate-800'
                                              }`}
                                            >
                                            <div className="flex items-center gap-2 mb-1">
                                                          <span className={`text-${meta.color}-400`}>{meta.icon}</span>
                                                          <span className="text-xs font-semibold text-slate-300">{meta.label}</span>
                                                          <span className={`ml-auto text-xs ${STATUS_STYLE[entry.status].text}`}>{entry.status}</span>
                                            </div>
                                            <div className="text-xs text-slate-500 truncate">{entry.text || `${meta.hint}`}</div>
                                            <div className="text-xs text-slate-600 mt-1">{entry.timestamp}</div>
                                </button>
                              );
          })}
          </div>
        );
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

export function IrisPanel() {
    const [queryType, setQueryType] = useState<IRISQueryType>('STATUS');
    const [queryText, setQueryText] = useState('');
    const [episodeId, setEpisodeId] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [currentResponse, setCurrentResponse] = useState<IRISResponse | null>(null);
    const [history, setHistory] = useState<HistoryEntry[]>([]);
    const [selectedHistoryId, setSelectedHistoryId] = useState<string | null>(null);
  
    const needsEpisodeId = queryType === 'WHY' || queryType === 'RECALL';
  
    const handleSubmit = useCallback(async (e?: React.FormEvent) => {
          if (e) e.preventDefault();
          setIsLoading(true);

          // Try real API first, fall back to mock
          let response: IRISResponse;
          try {
              const res = await fetch('/api/iris', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                      query_type: queryType,
                      text: queryText,
                      episode_id: episodeId,
                      limit: 20,
                  }),
              });
              if (res.ok) {
                  const data = await res.json();
                  if (data.status !== 'ERROR') {
                      response = data as IRISResponse;
                  } else {
                      response = resolveIRISQuery({ query_type: queryType, text: queryText, episode_id: episodeId, limit: 20 });
                  }
              } else {
                  response = resolveIRISQuery({ query_type: queryType, text: queryText, episode_id: episodeId, limit: 20 });
              }
          } catch {
              response = resolveIRISQuery({ query_type: queryType, text: queryText, episode_id: episodeId, limit: 20 });
          }
      
          const entry: HistoryEntry = {
                  id: response.query_id,
                  queryType: response.query_type,
                  text: queryText || episodeId || QUERY_TYPE_META[queryType].hint,
                  status: response.status,
                  confidence: response.confidence,
                  timestamp: new Date().toLocaleTimeString(),
                  response,
          };
      
          setCurrentResponse(response);
          setHistory(prev => [entry, ...prev].slice(0, 50));
          setSelectedHistoryId(response.query_id);
          setIsLoading(false);
    }, [queryType, queryText, episodeId]);
  
    const handleHistorySelect = useCallback((id: string) => {
          setSelectedHistoryId(id);
          const entry = history.find(h => h.id === id);
          if (entry) setCurrentResponse(entry.response);
    }, [history]);
  
    const displayedResponse = currentResponse;
  
    return (
          <div className="space-y-6">
            {/* Query input card */}
                <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
                        <div className="flex items-center gap-3 mb-5">
                                  <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-600/20 text-blue-400">
                                              <Eye size={18} />
                                  </div>
                                  <div>
                                              <h3 className="text-lg font-semibold">IRIS Query Panel</h3>
                                              <p className="text-xs text-slate-500">Interface for Resolution, Insight, and Status</p>
                                  </div>
                        </div>
                
                  {/* Query type selector */}
                        <div className="flex flex-wrap gap-2 mb-4">
                          {(Object.keys(QUERY_TYPE_META) as IRISQueryType[]).map(qt => {
                        const meta = QUERY_TYPE_META[qt];
                        const active = queryType === qt;
                        return (
                                        <button
                                                          key={qt}
                                                          onClick={() => setQueryType(qt)}
                                                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                                                                              active
                                                                                ? `bg-${meta.color}-900/30 border-${meta.color}-600 text-${meta.color}-400`
                                                                                : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-300 hover:border-slate-600'
                                                          }`}
                                                        >
                                          {meta.icon}
                                          {meta.label}
                                        </button>
                                      );
          })}
                        </div>
                
                  {/* Input form */}
                        <form onSubmit={handleSubmit} className="space-y-3">
                          {/* Natural language input */}
                                  <div className="relative">
                                              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                                              <input
                                                              type="text"
                                                              placeholder={QUERY_TYPE_META[queryType].hint}
                                                              value={queryText}
                                                              onChange={e => setQueryText(e.target.value)}
                                                              className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
                                                            />
                                  </div>
                        
                          {/* Episode ID field (conditional) */}
                          {needsEpisodeId && (
                        <div className="relative">
                                      <Link2 size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                                      <input
                                                        type="text"
                                                        placeholder="Episode ID (e.g. ep_1234567890_0)"
                                                        value={episodeId}
                                                        onChange={e => setEpisodeId(e.target.value)}
                                                        className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
                                                      />
                        </div>
                                  )}
                        
                          {/* Submit */}
                                  <button
                                                type="submit"
                                                disabled={isLoading || (needsEpisodeId && !episodeId)}
                                                className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:text-slate-500 text-white font-semibold py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2"
                                              >
                                    {isLoading ? (
                                                              <>
                                                                              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                                                              Resolving…
                                                              </>
                                                            ) : (
                                                              <>
                                                                              <Search size={16} />
                                                                              Query IRIS
                                                              </>
                                                            )}
                                  </button>
                        </form>
                </div>
          
            {/* Results grid: history sidebar + response */}
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                  {/* History sidebar */}
                        <div className="lg:col-span-1 bg-slate-900 rounded-lg border border-slate-800 p-4">
                                  <h4 className="text-sm font-semibold text-slate-300 mb-3">Query History</h4>
                                  <QueryHistory entries={history} selected={selectedHistoryId} onSelect={handleHistorySelect} />
                        </div>
                
                  {/* Response area */}
                        <div className="lg:col-span-3">
                          {displayedResponse ? (
                        <IRISResponseView response={displayedResponse} />
                      ) : (
                        <div className="bg-slate-900 rounded-lg border border-slate-800 p-12 text-center">
                                      <Eye size={48} className="mx-auto text-slate-700 mb-4" />
                                      <p className="text-slate-500 text-sm">Submit a query to see IRIS results</p>
                                      <p className="text-slate-600 text-xs mt-2">
                                                      IRIS resolves operator questions against MG, DLR, DS, and RS artifacts
                                                      with full provenance chains and decision lineage.
                                      </p>
                        </div>
                                  )}
                        </div>
                </div>
          </div>
        );
}
