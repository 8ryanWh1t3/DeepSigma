// ─────────────────────────────────────────────────────────────
// dashboard/src/lib/api.ts – Typed API client for Exhaust Inbox
// ─────────────────────────────────────────────────────────────
import type {
  EpisodeEvent,
  RefinedEpisode,
  EpisodesListResponse,
  DriftListResponse,
  HealthResponse,
  EpisodeDetail,
  ItemAction,
  FilterState,
} from "../types/exhaust";

const BASE = "/api/exhaust";

// ── helpers ──────────────────────────────────────────────────

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${body || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

// ── events ───────────────────────────────────────────────────

export async function ingestEvents(
  events: EpisodeEvent[],
): Promise<{ ingested: number }> {
  return request("/events", {
    method: "POST",
    body: JSON.stringify(events),
  });
}

// ── episodes ─────────────────────────────────────────────────

export async function assembleEpisodes(): Promise<{
  assembled: number;
  episode_ids: string[];
}> {
  return request("/episodes/assemble", { method: "POST" });
}

export async function listEpisodes(
  filters?: Partial<FilterState>,
  skip?: number,
  limit?: number,
): Promise<EpisodesListResponse> {
  const params = new URLSearchParams();
  if (filters?.project) params.set("project", filters.project);
  if (filters?.team) params.set("team", filters.team);
  if (filters?.source) params.set("source", filters.source);
  if (filters?.driftOnly) params.set("drift_only", "true");
  if (filters?.lowConfidenceOnly) params.set("low_confidence_only", "true");
  if (filters?.minScore !== undefined)
    params.set("min_score", String(filters.minScore));
  if (filters?.maxScore !== undefined)
    params.set("max_score", String(filters.maxScore));
  if (skip !== undefined) params.set("skip", String(skip));
  if (limit !== undefined) params.set("limit", String(limit));
  const qs = params.toString();
  return request(`/episodes${qs ? "?" + qs : ""}`);
}

export async function getEpisode(
  episodeId: string,
): Promise<EpisodeDetail> {
  return request(`/episodes/${episodeId}`);
}

// ── refine / commit ──────────────────────────────────────────

export async function refineEpisode(
  episodeId: string,
): Promise<RefinedEpisode> {
  return request(`/episodes/${episodeId}/refine`, { method: "POST" });
}

export async function commitEpisode(
  episodeId: string,
): Promise<{ committed: boolean; episode_id: string }> {
  return request(`/episodes/${episodeId}/commit`, { method: "POST" });
}

// ── item-level actions ───────────────────────────────────────

export async function itemAction(
  episodeId: string,
  action: ItemAction,
): Promise<{ updated: boolean }> {
  return request(`/episodes/${episodeId}/item`, {
    method: "POST",
    body: JSON.stringify(action),
  });
}

// ── drift ────────────────────────────────────────────────────

export async function listDrift(
  severity?: "green" | "yellow" | "red",
  limit?: number,
): Promise<DriftListResponse> {
  const params = new URLSearchParams();
  if (severity) params.set("severity", severity);
  if (limit !== undefined) params.set("limit", String(limit));
  const qs = params.toString();
  return request(`/drift${qs ? "?" + qs : ""}`);
}

// ── health ───────────────────────────────────────────────────

export async function getHealth(): Promise<HealthResponse> {
  return request("/health");
}

// ── schema ───────────────────────────────────────────────────

export async function getSchema(): Promise<Record<string, unknown>> {
  return request("/schema");
}
