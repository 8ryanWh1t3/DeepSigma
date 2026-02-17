/**
 * TypeScript types for the Exhaust Inbox system.
 * Mirrors the Pydantic models in dashboard/server/models_exhaust.py
 */

// ── Enums ──────────────────────────────────────────────────────

export type EventType = 'prompt' | 'completion' | 'tool' | 'metric' | 'error';
export type Source = 'langchain' | 'openai' | 'azure' | 'manual';
export type DriftSeverity = 'green' | 'yellow' | 'red';
export type DriftType = 'contradiction' | 'missing_policy' | 'low_claim_coverage';
export type ItemStatus = 'pending' | 'accepted' | 'rejected' | 'edited';
export type ConfidenceTier = 'auto_commit' | 'review_required' | 'hold';
export type Grade = 'A' | 'B' | 'C' | 'D';

// ── Episode Event ──────────────────────────────────────────────

export interface EpisodeEvent {
  event_id: string;
  episode_id: string;
  event_type: EventType;
  timestamp: string;
  source: Source;
  user_hash: string;
  session_id: string;
  project: string;
  team: string;
  payload: Record<string, unknown>;
}

// ── Decision Episode ───────────────────────────────────────────

export interface DecisionEpisode {
  episode_id: string;
  events: EpisodeEvent[];
  source: Source;
  user_hash: string;
  session_id: string;
  project: string;
  team: string;
  started_at: string;
  ended_at: string;
  status: string;
  coherence_score: number | null;
  grade: Grade | null;
  refined: boolean;
}

// ── Bucket Items ───────────────────────────────────────────────

export interface TruthItem {
  item_id: string;
  claim: string;
  evidence: string;
  confidence: number;
  truth_type: string;
  entity: string;
  property_name: string;
  value: string;
  unit: string;
  support_count: number;
  provenance: string[];
  status: ItemStatus;
}

export interface ReasoningItem {
  item_id: string;
  decision: string;
  rationale: string;
  assumptions: string[];
  alternatives: string[];
  confidence: number;
  provenance: string[];
  status: ItemStatus;
}

export interface MemoryItem {
  item_id: string;
  entity: string;
  relation: string;
  target: string;
  context: string;
  artifact_type: string;
  confidence: number;
  provenance: string[];
  status: ItemStatus;
}

// ── Drift Signal ───────────────────────────────────────────────

export interface DriftSignal {
  drift_id: string;
  drift_type: DriftType;
  severity: DriftSeverity;
  fingerprint: string;
  description: string;
  entity: string;
  property_name: string;
  expected_value: string;
  actual_value: string;
  episode_id: string;
  recommended_patch: Record<string, unknown>;
  timestamp: string;
}

// ── Coherence Breakdown ────────────────────────────────────────

export interface CoherenceBreakdown {
  claim_coverage: number;
  evidence_quality: number;
  reasoning_completeness: number;
  memory_linkage: number;
  policy_adherence: number;
}

// ── Refined Episode ────────────────────────────────────────────

export interface RefinedEpisode {
  episode_id: string;
  truth: TruthItem[];
  reasoning: ReasoningItem[];
  memory: MemoryItem[];
  drift_signals: DriftSignal[];
  coherence_score: number;
  grade: Grade;
  breakdown: CoherenceBreakdown;
  confidence_tier: ConfidenceTier;
  refined_at: string;
  committed: boolean;
}

// ── API types ──────────────────────────────────────────────────

export interface EpisodeDetail {
  episode: DecisionEpisode;
  refined: RefinedEpisode | null;
}

export interface EpisodesListResponse {
  total: number;
  count: number;
  episodes: DecisionEpisode[];
}

export interface DriftListResponse {
  count: number;
  drift_signals: DriftSignal[];
}

export interface HealthResponse {
  status: string;
  events_count: number;
  episodes_count: number;
  refined_count: number;
  drift_count: number;
}

export interface ItemAction {
  item_id: string;
  bucket: 'truth' | 'reasoning' | 'memory';
  action: 'accept' | 'reject' | 'edit';
  edited_data?: Record<string, unknown>;
}

export interface FilterState {
  project: string;
  team: string;
  source: string;
  driftOnly: boolean;
  lowConfidenceOnly: boolean;
  minScore: number;
  maxScore: number;
}
