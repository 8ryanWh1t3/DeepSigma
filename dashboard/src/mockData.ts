// Mock Data Generator for \u03A3 OVERWATCH Dashboard
// Generates realistic demo data for DecisionEpisodes, DriftEvents, and AgentMetrics

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

function seededRandom(seed: number): () => number {
  let s = seed;
  return () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };
}

export function generateMockEpisodes(count: number = 50): DecisionEpisode[] {
  const episodes: DecisionEpisode[] = [];
  const now = Date.now();

  for (let i = 0; i < count; i++) {
    const deadline = 500 + Math.random() * 4500;
    const actualDuration = deadline * (0.5 + Math.random() * 0.9);
    const status: DecisionEpisode['status'] =
      actualDuration > deadline ? 'timeout' :
      Math.random() > 0.9 ? 'degraded' :
      Math.random() > 0.95 ? 'failed' : 'success';

    const al6Score = status === 'success' ? 0.85 + Math.random() * 0.15 :
                     status === 'degraded' ? 0.5 + Math.random() * 0.3 :
                     Math.random() * 0.5;

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
