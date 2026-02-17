// ─────────────────────────────────────────────────────────────
// EpisodeDetail.tsx – Center lane: timeline view of an episode
// ─────────────────────────────────────────────────────────────
import React, { useEffect, useState, useCallback } from "react";
import type {
  EpisodeDetail as EpisodeDetailType,
  EpisodeEvent,
  RefinedEpisode,
} from "../../types/exhaust";
import { getEpisode, refineEpisode } from "../../lib/api";
import ConfidenceBadge from "./ConfidenceBadge";
import DriftBadge from "./DriftBadge";
import SourceBadge from "./SourceBadge";

interface Props {
  episodeId: string | null;
  onRefined: (refined: RefinedEpisode) => void;
}

const EVENT_COLORS: Record<string, string> = {
  prompt: "border-sky-700 bg-sky-950/30",
  response: "border-indigo-700 bg-indigo-950/30",
  tool_call: "border-amber-700 bg-amber-950/30",
  tool_result: "border-amber-800 bg-amber-950/20",
  model: "border-violet-700 bg-violet-950/30",
  metric: "border-emerald-700 bg-emerald-950/30",
  error: "border-red-700 bg-red-950/30",
};

function chipColor(type: string): string {
  return EVENT_COLORS[type] ?? "border-zinc-700 bg-zinc-900/40";
}

export default function EpisodeDetail({ episodeId, onRefined }: Props) {
  const [detail, setDetail] = useState<EpisodeDetailType | null>(null);
  const [loading, setLoading] = useState(false);
  const [refining, setRefining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!episodeId) return;
    setLoading(true);
    setError(null);
    try {
      const d = await getEpisode(episodeId);
      setDetail(d);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [episodeId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleRefine = async () => {
    if (!episodeId) return;
    setRefining(true);
    try {
      const r = await refineEpisode(episodeId);
      onRefined(r);
      await load(); // reload detail to show refined_at
    } catch (err) {
      setError(err instanceof Error ? err.message : "Refine failed");
    } finally {
      setRefining(false);
    }
  };

  if (!episodeId) {
    return (
      <div className="flex items-center justify-center h-full text-zinc-500 text-sm">
        Select an episode from the left panel.
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-zinc-500 text-sm">
        Loading…
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-red-400 text-sm">
        {error}
      </div>
    );
  }

  if (!detail) return null;

  const ep = detail.episode;
  const events: EpisodeEvent[] = ep.events ?? [];
  const score = ep.coherence_score ?? 0;
  const driftCount = ep.drift_signals?.length ?? 0;

  return (
    <div className="flex flex-col h-full">
      {/* header */}
      <div className="shrink-0 border-b border-zinc-800 px-4 py-3">
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-sm font-semibold text-zinc-200 font-mono">
            {ep.episode_id.slice(0, 12)}…
          </h2>
          <button
            onClick={handleRefine}
            disabled={refining}
            className="rounded bg-indigo-700 hover:bg-indigo-600 px-3 py-1 text-xs font-medium text-white disabled:opacity-40 transition-colors"
          >
            {refining ? "Refining…" : "Refine"}
          </button>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-400">
          <span>{ep.project ?? "—"}</span>
          {ep.team && <span>/ {ep.team}</span>}
          <SourceBadge source={ep.source ?? "unknown"} />
          <ConfidenceBadge score={score / 100} showLabel />
          {driftCount > 0 && (
            <DriftBadge
              severity={
                ep.drift_signals!.some((d) => d.severity === "red")
                  ? "red"
                  : ep.drift_signals!.some((d) => d.severity === "yellow")
                    ? "yellow"
                    : "green"
              }
              count={driftCount}
            />
          )}
          <span className="text-zinc-600">
            {new Date(ep.started_at).toLocaleString()}
          </span>
        </div>
      </div>

      {/* timeline */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        <div className="relative border-l-2 border-zinc-800 ml-3 space-y-3">
          {events.map((ev, i) => (
            <div key={ev.event_id ?? i} className="relative pl-6">
              {/* dot */}
              <div className="absolute left-[-5px] top-2 w-2 h-2 rounded-full bg-zinc-600" />

              <div
                className={`rounded-md border p-3 ${chipColor(ev.event_type)}`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-zinc-400">
                    {ev.event_type}
                  </span>
                  <span className="text-[10px] text-zinc-600">
                    {new Date(ev.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <pre className="text-xs text-zinc-300 whitespace-pre-wrap break-words max-h-40 overflow-y-auto">
                  {typeof ev.payload === "string"
                    ? ev.payload
                    : JSON.stringify(ev.payload, null, 2)}
                </pre>
              </div>
            </div>
          ))}

          {events.length === 0 && (
            <p className="pl-6 text-xs text-zinc-500 py-4">
              No events in this episode.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
