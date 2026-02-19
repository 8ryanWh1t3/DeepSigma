import { create } from 'zustand';
import type { DecisionEpisode, DriftEvent, AgentMetrics, TrustScorecard } from './mockData';
import { fetchRealTrustScorecard, generateMockTrustScorecard } from './mockData';

export interface MGNode {
  node_id: string;
  kind: string;
  label: string;
  timestamp?: string;
  properties: Record<string, unknown>;
}

export interface MGEdge {
  source_id: string;
  target_id: string;
  kind: string;
  label: string;
  properties: Record<string, unknown>;
}

export type ConnectionStatus = 'connected' | 'reconnecting' | 'disconnected' | 'polling';
export type DataSource = 'sse' | 'api' | 'mock';

interface ConnectionState {
  status: ConnectionStatus;
  lastEvent: string;
  dataSource: DataSource;
}

interface OverwatchStore {
  // Data slices
  episodes: DecisionEpisode[];
  drifts: DriftEvent[];
  agents: AgentMetrics[];
  coherence: Record<string, unknown> | null;
  mgNodes: MGNode[];
  mgEdges: MGEdge[];
  trustScorecard: TrustScorecard | null;
  trustScorecardLoading: boolean;
  trustScorecardError: string | null;

  // Connection state
  connection: ConnectionState;

  // Actions
  setEpisodes: (eps: DecisionEpisode[]) => void;
  setDrifts: (drifts: DriftEvent[]) => void;
  setAgents: (agents: AgentMetrics[]) => void;
  setCoherence: (report: Record<string, unknown>) => void;
  setMGGraph: (nodes: MGNode[], edges: MGEdge[]) => void;
  setConnection: (state: Partial<ConnectionState>) => void;
  setTrustScorecard: (sc: TrustScorecard | null) => void;
  fetchTrustScorecard: () => Promise<void>;
}

export const useOverwatchStore = create<OverwatchStore>((set) => ({
  episodes: [],
  drifts: [],
  agents: [],
  coherence: null,
  mgNodes: [],
  mgEdges: [],
  trustScorecard: null,
  trustScorecardLoading: false,
  trustScorecardError: null,
  connection: { status: 'disconnected', lastEvent: '', dataSource: 'mock' },

  setEpisodes: (episodes) => set({ episodes }),
  setDrifts: (drifts) => set({ drifts }),
  setAgents: (agents) => set({ agents }),
  setCoherence: (coherence) => set({ coherence }),
  setMGGraph: (mgNodes, mgEdges) => set({ mgNodes, mgEdges }),
  setConnection: (state) =>
    set((prev) => ({
      connection: { ...prev.connection, ...state },
    })),
  setTrustScorecard: (trustScorecard) => set({ trustScorecard, trustScorecardError: null }),
  fetchTrustScorecard: async () => {
    set({ trustScorecardLoading: true, trustScorecardError: null });
    const real = await fetchRealTrustScorecard();
    if (real) {
      set({ trustScorecard: real, trustScorecardLoading: false });
    } else {
      set({ trustScorecard: generateMockTrustScorecard(), trustScorecardLoading: false });
    }
  },
}));
