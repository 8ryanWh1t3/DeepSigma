// Mock Data Generator for Σ OVERWATCH Dashboard
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
}

export interface DriftEvent {
    driftId: string;
    episodeId: string;
    type: 'time' | 'freshness' | 'fallback' | 'bypass' | 'verify' | 'outcome';
    severity: 'low' | 'medium' | 'high';
    timestamp: number;
    patchHint: string;
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
}

const agents = ['ReasoningAgent', 'PlannerAgent', 'ExecutorAgent', 'VerifierAgent'];
const decisions = [
    'Execute trade',
    'Approve transaction',
    'Route request',
    'Generate response',
    'Allocate resources'
  ];

export function generateMockEpisodes(count: number = 50): DecisionEpisode[] {
    const episodes: DecisionEpisode[] = [];
    const now = Date.now();

  for (let i = 0; i < count; i++) {
        const deadline = 500 + Math.random() * 4500;
        const actualDuration = deadline * (0.5 + Math.random() * 0.9);
        const status = actualDuration > deadline ? 'timeout' : 
                             Math.random() > 0.9 ? 'degraded' :
                             Math.random() > 0.95 ? 'failed' : 'success';

      episodes.push({
              episodeId: `ep_${Date.now()}_${i}`,
              agentName: agents[Math.floor(Math.random() * agents.length)],
              timestamp: now - (count - i) * 5000,
              deadline: deadline,
              actualDuration: actualDuration,
              status: status,
              freshness: 95 + Math.random() * 5,
              dataAge: Math.random() * 5000,
              distance: Math.floor(Math.random() * 15),
              variability: 100 + Math.random() * 50,
              drag: Math.random() * 200,
              decision: decisions[Math.floor(Math.random() * decisions.length)],
              verification: Math.random() > 0.1 ? 'Verified' : 'Skipped',
              outcome: status === 'success' ? 'Committed' : 'Rolled back'
      });
  }

  return episodes;
}

export function generateMockDrifts(episodeCount: number = 50): DriftEvent[] {
    const drifts: DriftEvent[] = [];
    const now = Date.now();

  for (let i = 0; i < episodeCount * 0.15; i++) {
        const driftTypes: Array<'time' | 'freshness' | 'fallback' | 'bypass' | 'verify' | 'outcome'> = 
          ['time', 'freshness', 'fallback', 'bypass', 'verify', 'outcome'];

      drifts.push({
              driftId: `drift_${Date.now()}_${i}`,
              episodeId: `ep_${Date.now()}_${Math.floor(Math.random() * episodeCount)}`,
              type: driftTypes[Math.floor(Math.random() * driftTypes.length)],
              severity: Math.random() > 0.7 ? 'high' : Math.random() > 0.5 ? 'medium' : 'low',
              timestamp: now - (episodeCount - i) * 500,
              patchHint: `Review ${['TTL policy', 'deadline configuration', 'fallback strategy', 'bypass conditions'][Math.floor(Math.random() * 4)]}`
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
          averageFreshness: 92 + Math.random() * 8
    }));
}
