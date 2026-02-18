// Mock Data Generator for Σ OVERWATCH Dashboard
// Generates realistic demo data for DecisionEpisodes, DriftEvents, AgentMetrics,
// and IRIS query responses.

// ---------------------------------------------------------------------------
// Existing interfaces
// ---------------------------------------------------------------------------

export interface DecisionEpisode {
    episodeId: string;
    agentName: string;
    timestamp: number;
    deadline: number;
    actualDuration: number;
    status: 'success' | 'timeout' | 'degraded' | 'failed';
    freshness: number;
    dataAge: number;
    distance: number;
    variability: number;
    drag: number;
    decision: string;
    verification: string;
    outcome: string;
    actionContract: string;
    al6Score: number;
}

export interface DriftEvent {
    driftId: string;
    episodeId: string;
    type: 'time' | 'freshness' | 'fallback' | 'bypass' | 'verify' | 'outcome';
    severity: 'low' | 'medium' | 'high';
    timestamp: number;
    patchHint: string;
    delta: number;
    threshold: number;
}

export interface AgentMetrics {
    agentName: string;
    successRate: number;
    avgLatency: number;
    p95Latency: number;
    p99Latency: number;
    timeoutRate: number;
    degradedRate: number;
    averageFreshness: number;
    episodeCount: number;
    driftCount: number;
}

// ---------------------------------------------------------------------------
// IRIS interfaces (mirrors coherence_ops/iris.py data models)
// ---------------------------------------------------------------------------

export type IRISQueryType = 'WHY' | 'WHAT_CHANGED' | 'WHAT_DRIFTED' | 'RECALL' | 'STATUS';
export type IRISResolutionStatus = 'RESOLVED' | 'PARTIAL' | 'NOT_FOUND' | 'ERROR';

export interface IRISProvenanceLink {
    artifact: string;   // "DLR" | "MG" | "DS" | "RS" | "PRIME"
  ref_id: string;
    role: string;        // "source" | "evidence" | "context"
  detail: string;
}

export interface IRISResponse {
    query_id: string;
    query_type: IRISQueryType;
    status: IRISResolutionStatus;
    summary: string;
    data: Record<string, any>;
    provenance_chain: IRISProvenanceLink[];
    confidence: number;
    resolved_at: string;
    elapsed_ms: number;
    warnings: string[];
}

export interface IRISQueryInput {
    query_type: IRISQueryType;
    text: string;
    episode_id: string;
    limit: number;
}

// ---------------------------------------------------------------------------
// Constants (existing)
// ---------------------------------------------------------------------------

const agents = ['ReasoningAgent', 'PlannerAgent', 'ExecutorAgent', 'VerifierAgent'];
const decisions = [
    'Execute trade', 'Approve transaction', 'Route request',
    'Generate response', 'Allocate resources', 'Validate schema',
    'Schedule task', 'Aggregate results'
  ];
const actionContracts = [
    'AC-001:ExecutionWindow', 'AC-002:DataFreshness', 'AC-003:FallbackPolicy',
    'AC-004:BypassGuard', 'AC-005:VerifyChain', 'AC-006:OutcomeLock'
  ];
const driftTypes: Array<'time' | 'freshness' | 'fallback' | 'bypass' | 'verify' | 'outcome'> =
    ['time', 'freshness', 'fallback', 'bypass', 'verify', 'outcome'];
const patchHints = [
    'Review TTL policy', 'Adjust deadline configuration',
    'Update fallback strategy', 'Tighten bypass conditions',
    'Re-validate verification chain', 'Recalibrate outcome thresholds'
  ];

// IRIS-specific constants
const decisionTypes = [
    'AccountQuarantine', 'TradeExecution', 'ResourceAllocation',
    'SchemaValidation', 'ResponseGeneration', 'TaskScheduling'
  ];
const outcomeCodes = ['COMMIT', 'ROLLBACK', 'DEGRADE', 'ABSTAIN'];
const degradeSteps = ['none', 'fallback_cache', 'circuit_breaker', 'manual_review', 'abstain'];
const driftFingerprints = [
    'fp:time:deadline_breach', 'fp:freshness:ttl_expired',
    'fp:fallback:cache_stale', 'fp:bypass:guard_skip',
    'fp:verify:chain_incomplete', 'fp:outcome:threshold_miss'
  ];
const mgNodeLabels = [
    'AccountQuarantine decision', 'TradeExecution decision',
    'ResourceAllocation decision', 'SchemaValidation decision',
    'ResponseGeneration decision', 'TaskScheduling decision'
  ];

// ---------------------------------------------------------------------------
// Existing generators (unchanged)
// ---------------------------------------------------------------------------

export function generateMockEpisodes(count: number = 50): DecisionEpisode[] {
    const episodes: DecisionEpisode[] = [];
    const now = Date.now();
    for (let i = 0; i < count; i++) {
          const deadline = 500 + Math.random() * 4500;
          const actualDuration = deadline * (0.5 + Math.random() * 0.9);
          const status: DecisionEpisode['status'] =
                  actualDuration > deadline ? 'timeout'
                  : Math.random() > 0.9 ? 'degraded'
                  : Math.random() > 0.95 ? 'failed'
                  : 'success';
          const al6Score =
                  status === 'success' ? 0.85 + Math.random() * 0.15
                  : status === 'degraded' ? 0.5 + Math.random() * 0.3
                  : Math.random() * 0.5;
          episodes.push({
                  episodeId: `ep_${Date.now()}_${i}`,
                  agentName: agents[Math.floor(Math.random() * agents.length)],
                  timestamp: now - (count - i) * 5000,
                  deadline,
                  actualDuration,
                  status,
                  freshness: 95 + Math.random() * 5,
                  dataAge: Math.random() * 5000,
                  distance: Math.floor(Math.random() * 15),
                  variability: 100 + Math.random() * 50,
                  drag: Math.random() * 200,
                  decision: decisions[Math.floor(Math.random() * decisions.length)],
                  verification: Math.random() > 0.1 ? 'Verified' : 'Skipped',
                  outcome: status === 'success' ? 'Committed' : 'Rolled back',
                  actionContract: actionContracts[Math.floor(Math.random() * actionContracts.length)],
                  al6Score: parseFloat(al6Score.toFixed(3)),
          });
    }
    return episodes;
}

export function generateMockDrifts(episodeCount: number = 50): DriftEvent[] {
    const drifts: DriftEvent[] = [];
    const now = Date.now();
    for (let i = 0; i < episodeCount * 0.15; i++) {
          const type = driftTypes[Math.floor(Math.random() * driftTypes.length)];
          const threshold = type === 'time' ? 5000 : type === 'freshness' ? 95 : 0.8;
          const delta = threshold * (0.1 + Math.random() * 0.4);
          drifts.push({
                  driftId: `drift_${Date.now()}_${i}`,
                  episodeId: `ep_${Date.now()}_${Math.floor(Math.random() * episodeCount)}`,
                  type,
                  severity: Math.random() > 0.7 ? 'high' : Math.random() > 0.5 ? 'medium' : 'low',
                  timestamp: now - (episodeCount - i) * 500,
                  patchHint: patchHints[Math.floor(Math.random() * patchHints.length)],
                  delta: parseFloat(delta.toFixed(2)),
                  threshold,
          });
    }
    return drifts;
}

export function generateAgentMetrics(): AgentMetrics[] {
    return agents.map(agent => ({
          agentName: agent,
          successRate: 85 + Math.random() * 14,
          avgLatency: 150 + Math.random() * 200,
          p95Latency: 300 + Math.random() * 300,
          p99Latency: 450 + Math.random() * 350,
          timeoutRate: Math.random() * 8,
          degradedRate: Math.random() * 5,
          averageFreshness: 92 + Math.random() * 8,
          episodeCount: 20 + Math.floor(Math.random() * 30),
          driftCount: Math.floor(Math.random() * 5),
    }));
}

// ---------------------------------------------------------------------------
// IRIS mock resolver — mirrors coherence_ops/iris.py IRISEngine.resolve()
// ---------------------------------------------------------------------------

function makeQueryId(query: IRISQueryInput): string {
    const payload = JSON.stringify({
          type: query.query_type,
          episode_id: query.episode_id,
          text: query.text,
          ts: Date.now(),
    });
    // Simple hash (not crypto — just for demo IDs)
  let hash = 0;
    for (let i = 0; i < payload.length; i++) {
          hash = ((hash << 5) - hash + payload.charCodeAt(i)) | 0;
    }
    return `iris-${Math.abs(hash).toString(16).padStart(8, '0')}`;
}

function pick<T>(arr: T[]): T {
    return arr[Math.floor(Math.random() * arr.length)];
}

function randomEpisodeId(): string {
    return `ep_${Date.now()}_${Math.floor(Math.random() * 100)}`;
}

function resolveWhy(query: IRISQueryInput, queryId: string): IRISResponse {
    const episodeId = query.episode_id || randomEpisodeId();
    const hasMgNode = Math.random() > 0.15;
    const hasDlr = Math.random() > 0.2;
    const provenance: IRISProvenanceLink[] = [];
    const data: Record<string, any> = {};
    const parts: string[] = [];
    let confidence = 0;

  if (hasMgNode) {
        const label = pick(mgNodeLabels);
        const evidenceRefs = Array.from({ length: 1 + Math.floor(Math.random() * 4) }, (_, i) => `ev-ref-${i}`);
        const actions = Array.from({ length: 1 + Math.floor(Math.random() * 3) }, (_, i) => `action-${i}`);
        data.mg_provenance = { node: { label }, evidence_refs: evidenceRefs, actions };
        provenance.push({ artifact: 'MG', ref_id: episodeId, role: 'source', detail: `Memory Graph node: ${label}` });
        evidenceRefs.forEach(ref =>
                provenance.push({ artifact: 'MG', ref_id: ref, role: 'evidence', detail: 'Evidence reference from Memory Graph' })
                                 );
        parts.push(`Episode '${episodeId}' found in Memory Graph with ${evidenceRefs.length} evidence ref(s) and ${actions.length} action(s).`);
        confidence += 0.4;

      // Drift context
      if (Math.random() > 0.4) {
              const driftEvents = Array.from({ length: 1 + Math.floor(Math.random() * 3) }, () => ({
                        type: pick(driftTypes), severity: pick(['low', 'medium', 'high']),
              }));
              data.mg_drift = driftEvents;
              provenance.push({ artifact: 'MG', ref_id: episodeId, role: 'context', detail: `${driftEvents.length} drift event(s) linked` });
              parts.push(`${driftEvents.length} drift event(s) associated with this episode.`);
              confidence += 0.1;
      }
  } else {
        parts.push(`Episode '${episodeId}' not found in Memory Graph.`);
  }

  if (hasDlr) {
        const dlrId = `dlr-${Math.abs((Date.now() * 7) | 0).toString(16).slice(0, 8)}`;
        const decisionType = pick(decisionTypes);
        const outcomeCode = pick(outcomeCodes);
        const policyStamp = Math.random() > 0.3;
        const degradeStep = pick(degradeSteps);
        data.dlr_entry = { dlr_id: dlrId, decision_type: decisionType, outcome_code: outcomeCode, policy_stamp: policyStamp, degrade_step: degradeStep };
        provenance.push({ artifact: 'DLR', ref_id: dlrId, role: 'context', detail: `Policy stamp: ${policyStamp}, outcome: ${outcomeCode}` });
        parts.push(`DLR record '${dlrId}' shows decision type '${decisionType}' with outcome '${outcomeCode}'.`);
        if (policyStamp) parts.push('Policy stamp present — decision was policy-governed.');
        if (degradeStep !== 'none') parts.push(`Degrade step active: ${degradeStep}.`);
        confidence += 0.3;
  } else {
        parts.push('No DLR entry found for this episode.');
  }

  provenance.push({ artifact: 'RS', ref_id: 'session:demo', role: 'context', detail: 'Reflection session available for broader context' });
    confidence += 0.1;
    confidence = Math.min(confidence, 1.0);

  const status: IRISResolutionStatus = confidence >= 0.5 ? 'RESOLVED' : confidence > 0 ? 'PARTIAL' : 'NOT_FOUND';

  return {
        query_id: queryId,
        query_type: 'WHY',
        status,
        summary: parts.join(' ') || `No data found for episode '${episodeId}'.`,
        data,
        provenance_chain: provenance,
        confidence: parseFloat(confidence.toFixed(3)),
        resolved_at: new Date().toISOString(),
        elapsed_ms: 45 + Math.random() * 400,
        warnings: [],
  };
}

function resolveWhatChanged(_query: IRISQueryInput, queryId: string): IRISResponse {
    const totalEntries = 20 + Math.floor(Math.random() * 80);
    const provenance: IRISProvenanceLink[] = [];
    const parts: string[] = [];
    let confidence = 0;

  const outcomes: Record<string, number> = {};
    outcomeCodes.forEach(code => { outcomes[code] = Math.floor(Math.random() * (totalEntries / 3)); });
    const degradedCount = Math.floor(Math.random() * 8);
    const policyMissing = Math.floor(Math.random() * 5);

  const data: Record<string, any> = {
        total_entries: totalEntries,
        outcome_distribution: outcomes,
        degraded_episodes: Array.from({ length: degradedCount }, () => randomEpisodeId()),
        policy_missing: Array.from({ length: policyMissing }, () => randomEpisodeId()),
  };

  provenance.push({ artifact: 'DLR', ref_id: 'all', role: 'source', detail: `Analysed ${totalEntries} DLR entries` });
    parts.push(`Analysed ${totalEntries} DLR entries.`);
    if (degradedCount > 0) parts.push(`${degradedCount} episode(s) had active degrade steps.`);
    if (policyMissing > 0) parts.push(`${policyMissing} episode(s) missing policy stamps.`);
    Object.entries(outcomes).forEach(([code, count]) => parts.push(`Outcome '${code}': ${count} episode(s).`));
    confidence += 0.5;

  // Patch data from MG
  const patchCount = Math.floor(Math.random() * 12);
    if (patchCount > 0) {
          data.patch_count = patchCount;
          provenance.push({ artifact: 'MG', ref_id: 'stats', role: 'context', detail: `${patchCount} patch node(s) in Memory Graph` });
          parts.push(`${patchCount} patch(es) recorded in Memory Graph.`);
          confidence += 0.2;
    }

  // Drift summary from DS
  const totalSignals = 5 + Math.floor(Math.random() * 30);
    const bySeverity: Record<string, number> = { red: Math.floor(Math.random() * 5), yellow: Math.floor(Math.random() * 10), green: totalSignals - Math.floor(Math.random() * 15) };
    data.drift_summary = { total_signals: totalSignals, by_severity: bySeverity };
    provenance.push({ artifact: 'DS', ref_id: 'summary', role: 'context', detail: `${totalSignals} drift signal(s)` });
    parts.push(`${totalSignals} drift signal(s) detected (red: ${bySeverity.red}).`);
    confidence += 0.2;

  confidence = Math.min(confidence, 1.0);

  return {
        query_id: queryId,
        query_type: 'WHAT_CHANGED',
        status: 'RESOLVED',
        summary: parts.join(' '),
        data,
        provenance_chain: provenance,
        confidence: parseFloat(confidence.toFixed(3)),
        resolved_at: new Date().toISOString(),
        elapsed_ms: 80 + Math.random() * 300,
        warnings: [],
  };
}

function resolveWhatDrifted(_query: IRISQueryInput, queryId: string): IRISResponse {
    const totalSignals = 8 + Math.floor(Math.random() * 40);
    const provenance: IRISProvenanceLink[] = [];
    const parts: string[] = [];
    let confidence = 0;

  const redCount = Math.floor(Math.random() * 6);
    const yellowCount = Math.floor(Math.random() * 12);
    const greenCount = Math.max(0, totalSignals - redCount - yellowCount);

  const buckets = driftFingerprints.slice(0, 3 + Math.floor(Math.random() * 4)).map(fp => ({
        fingerprint: fp,
        count: 1 + Math.floor(Math.random() * 8),
        severity: pick(['red', 'yellow', 'green']),
  }));

  const topRecurring = driftFingerprints.slice(0, 2 + Math.floor(Math.random() * 3));

  const data: Record<string, any> = {
        total_signals: totalSignals,
        by_type: { time: Math.floor(Math.random() * 10), freshness: Math.floor(Math.random() * 10), fallback: Math.floor(Math.random() * 5), bypass: Math.floor(Math.random() * 3), verify: Math.floor(Math.random() * 5), outcome: Math.floor(Math.random() * 5) },
        by_severity: { red: redCount, yellow: yellowCount, green: greenCount },
        top_buckets: buckets,
        top_recurring: topRecurring,
  };

  provenance.push({ artifact: 'DS', ref_id: 'summary', role: 'source', detail: `Drift scan: ${totalSignals} signals, ${buckets.length} fingerprints` });
    parts.push(`${totalSignals} drift signal(s) across ${buckets.length} fingerprint(s).`);
    parts.push(`Severity breakdown: red=${redCount}, yellow=${yellowCount}, green=${greenCount}.`);
    if (topRecurring.length) parts.push(`Top recurring patterns: ${topRecurring.join(', ')}.`);
    confidence += 0.6;

  // MG cross-reference
  const driftNodes = 5 + Math.floor(Math.random() * 20);
    const patchNodes = Math.floor(driftNodes * (0.3 + Math.random() * 0.5));
    const resolutionRatio = patchNodes / driftNodes;
    data.mg_drift_nodes = driftNodes;
    data.mg_patch_nodes = patchNodes;
    data.resolution_ratio = parseFloat(resolutionRatio.toFixed(4));
    provenance.push({ artifact: 'MG', ref_id: 'stats', role: 'context', detail: `Drift resolution ratio: ${(resolutionRatio * 100).toFixed(1)}% (${patchNodes}/${driftNodes})` });
    parts.push(`Memory Graph shows ${patchNodes}/${driftNodes} drift(s) resolved (${Math.round(resolutionRatio * 100)}%).`);
    confidence += 0.2;

  confidence = Math.min(confidence, 1.0);

  return {
        query_id: queryId,
        query_type: 'WHAT_DRIFTED',
        status: 'RESOLVED',
        summary: parts.join(' '),
        data,
        provenance_chain: provenance,
        confidence: parseFloat(confidence.toFixed(3)),
        resolved_at: new Date().toISOString(),
        elapsed_ms: 60 + Math.random() * 250,
        warnings: redCount > 3 ? [`${redCount} red-severity signals detected — review recommended`] : [],
  };
}

function resolveRecall(query: IRISQueryInput, queryId: string): IRISResponse {
    const episodeId = query.episode_id || randomEpisodeId();
    const provenance: IRISProvenanceLink[] = [];
    const data: Record<string, any> = {};
    const parts: string[] = [];
    let confidence = 0;

  const hasMgNode = Math.random() > 0.1;
    if (hasMgNode) {
          const label = pick(mgNodeLabels);
          const evidenceRefs = Array.from({ length: 1 + Math.floor(Math.random() * 5) }, (_, i) => `ev-ref-${i}`);
          const actions = Array.from({ length: 1 + Math.floor(Math.random() * 3) }, (_, i) => `action-${i}`);
          const driftEvents = Array.from({ length: Math.floor(Math.random() * 4) }, () => ({
                  type: pick(driftTypes), severity: pick(['low', 'medium', 'high']),
          }));
          const patches = Array.from({ length: Math.floor(Math.random() * 3) }, (_, i) => ({
                  patch_id: `patch-${i}`, status: pick(['applied', 'pending', 'rejected']),
          }));

      data.provenance = { node: { label }, evidence_refs: evidenceRefs, actions };
          data.drift_events = driftEvents;
          data.patches = patches;

      provenance.push({ artifact: 'MG', ref_id: episodeId, role: 'source', detail: `Full recall: node label='${label}'` });
          parts.push(`Recalled episode '${episodeId}' (type: ${label}).`);
          parts.push(`Graph context: ${evidenceRefs.length} evidence ref(s), ${actions.length} action(s), ${driftEvents.length} drift(s), ${patches.length} patch(es).`);
          evidenceRefs.forEach(ref => provenance.push({ artifact: 'MG', ref_id: ref, role: 'evidence', detail: 'Evidence reference' }));
          actions.forEach(act => provenance.push({ artifact: 'MG', ref_id: act, role: 'context', detail: 'Action node' }));
          confidence += 0.6;
    } else {
          parts.push(`Episode '${episodeId}' not found in Memory Graph.`);
    }

  // DLR enrichment
  if (Math.random() > 0.2) {
        const dlrId = `dlr-${Math.abs((Date.now() * 3) | 0).toString(16).slice(0, 8)}`;
        const decisionType = pick(decisionTypes);
        const outcomeCode = pick(outcomeCodes);
        data.dlr_entry = { dlr_id: dlrId, decision_type: decisionType, outcome_code: outcomeCode };
        provenance.push({ artifact: 'DLR', ref_id: dlrId, role: 'context', detail: `Decision type: ${decisionType}, outcome: ${outcomeCode}` });
        parts.push(`DLR record confirms decision type '${decisionType}'.`);
        confidence += 0.2;
  }

  confidence = Math.min(confidence, 1.0);
    const status: IRISResolutionStatus = confidence >= 0.5 ? 'RESOLVED' : confidence > 0 ? 'PARTIAL' : 'NOT_FOUND';

  return {
        query_id: queryId,
        query_type: 'RECALL',
        status,
        summary: parts.join(' ') || `No recall data for '${episodeId}'.`,
        data,
        provenance_chain: provenance,
        confidence: parseFloat(confidence.toFixed(3)),
        resolved_at: new Date().toISOString(),
        elapsed_ms: 50 + Math.random() * 350,
        warnings: [],
  };
}

function resolveStatus(_query: IRISQueryInput, queryId: string): IRISResponse {
    const provenance: IRISProvenanceLink[] = [];
    const parts: string[] = [];

  const overallScore = 55 + Math.floor(Math.random() * 40);
    const grade = overallScore >= 90 ? 'A' : overallScore >= 75 ? 'B' : overallScore >= 60 ? 'C' : overallScore >= 40 ? 'D' : 'F';

  const dimensions = [
    { name: 'Policy Adherence', score: parseFloat((50 + Math.random() * 50).toFixed(1)), weight: 0.3 },
    { name: 'Outcome Health', score: parseFloat((60 + Math.random() * 40).toFixed(1)), weight: 0.25 },
    { name: 'Drift Control', score: parseFloat((40 + Math.random() * 55).toFixed(1)), weight: 0.25 },
    { name: 'Memory Completeness', score: parseFloat((55 + Math.random() * 45).toFixed(1)), weight: 0.2 },
      ];

  const data: Record<string, any> = {
        overall_score: overallScore,
        grade,
        dimensions,
  };

  provenance.push({ artifact: 'DLR', ref_id: 'scorer', role: 'source', detail: 'Policy adherence dimension' });
    provenance.push({ artifact: 'RS', ref_id: 'scorer', role: 'source', detail: 'Outcome health dimension' });
    provenance.push({ artifact: 'DS', ref_id: 'scorer', role: 'source', detail: 'Drift control dimension' });
    provenance.push({ artifact: 'MG', ref_id: 'scorer', role: 'source', detail: 'Memory completeness dimension' });

  parts.push(`System coherence: ${overallScore}/100 (grade ${grade}).`);
    dimensions.forEach(dim => parts.push(`${dim.name}: ${dim.score}/100 (weight ${Math.round(dim.weight * 100)}%).`));

  // MG stats
  const totalNodes = 30 + Math.floor(Math.random() * 200);
    const totalEdges = Math.floor(totalNodes * (1.5 + Math.random()));
    data.mg_stats = { total_nodes: totalNodes, total_edges: totalEdges };
    provenance.push({ artifact: 'MG', ref_id: 'stats', role: 'context', detail: `Graph: ${totalNodes} nodes, ${totalEdges} edges` });

  // Drift headline
  const driftTotal = 5 + Math.floor(Math.random() * 25);
    const driftRed = Math.floor(Math.random() * 5);
    const driftRecurring = Math.floor(Math.random() * 4);
    data.drift_headline = { total: driftTotal, red: driftRed, recurring: driftRecurring };

  const confidence = Math.min(overallScore / 100, 1.0);

  return {
        query_id: queryId,
        query_type: 'STATUS',
        status: 'RESOLVED',
        summary: parts.join(' '),
        data,
        provenance_chain: provenance,
        confidence: parseFloat(confidence.toFixed(3)),
        resolved_at: new Date().toISOString(),
        elapsed_ms: 100 + Math.random() * 500,
        warnings: overallScore < 60 ? [`System coherence below threshold (${overallScore}/100) — review recommended`] : [],
  };
}

// ---------------------------------------------------------------------------
// Real-data API fetch helpers (http://localhost:8000)
// Falls back to mock data when the API server is not running.
// ---------------------------------------------------------------------------

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

async function apiFetch<T>(path: string): Promise<T | null> {
    try {
        const res = await fetch(`${API_BASE}${path}`, { signal: AbortSignal.timeout(2000) });
        if (!res.ok) return null;
        return (await res.json()) as T;
    } catch {
        return null;
    }
}

/** Fetch real episodes from the API; returns null if the server is offline. */
export async function fetchRealEpisodes(): Promise<DecisionEpisode[] | null> {
    return apiFetch<DecisionEpisode[]>('/api/episodes');
}

/** Fetch real drift events from the API; returns null if the server is offline. */
export async function fetchRealDrifts(): Promise<DriftEvent[] | null> {
    return apiFetch<DriftEvent[]>('/api/drifts');
}

/** Fetch real agent metrics from the API; returns null if the server is offline. */
export async function fetchRealAgents(): Promise<AgentMetrics[] | null> {
    return apiFetch<AgentMetrics[]>('/api/agents');
}

/** Resolve an IRIS query via the real API; falls back to mock resolver. */
export async function fetchRealIRIS(query: IRISQueryInput): Promise<IRISResponse | null> {
    try {
        const res = await fetch(`${API_BASE}/api/iris`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(query),
            signal: AbortSignal.timeout(5000),
        });
        if (!res.ok) return null;
        return (await res.json()) as IRISResponse;
    } catch {
        return null;
    }
}

/**
 * Resolve an IRIS query using mock data.
 *
 * This mirrors the behaviour of coherence_ops/iris.py IRISEngine.resolve().
 * In production, the dashboard would call a backend API that delegates to
 * the real IRISEngine.
 */
export function resolveIRISQuery(query: IRISQueryInput): IRISResponse {
    const queryId = makeQueryId(query);
    switch (query.query_type) {
      case 'WHY':           return resolveWhy(query, queryId);
      case 'WHAT_CHANGED':  return resolveWhatChanged(query, queryId);
      case 'WHAT_DRIFTED':  return resolveWhatDrifted(query, queryId);
      case 'RECALL':        return resolveRecall(query, queryId);
      case 'STATUS':        return resolveStatus(query, queryId);
      default:
              return {
                        query_id: queryId,
                        query_type: query.query_type,
                        status: 'ERROR',
                        summary: `Unsupported query type: ${query.query_type}`,
                        data: {},
                        provenance_chain: [],
                        confidence: 0,
                        resolved_at: new Date().toISOString(),
                        elapsed_ms: 0,
                        warnings: [],
              };
    }
}
