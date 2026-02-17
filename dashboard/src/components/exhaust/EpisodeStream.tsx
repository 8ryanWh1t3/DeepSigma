// ─────────────────────────────────────────────────────────────
// EpisodeStream.tsx – Left lane: scrollable list of episode cards
// ─────────────────────────────────────────────────────────────
import React, { useEffect, useState, useCallback } from "react";
import type { DecisionEpisode, FilterState } from "../../types/exhaust";
import { listEpisodes } from "../../lib/api";
import EpisodeCard from "./EpisodeCard";
import FiltersBar from "./FiltersBar";

interface Props {
  selectedId: string | null;
  onSelect: (id: string) => void;
}

const EMPTY_FILTERS: FilterState = {
  project: "",
  team: "",
  source: "",
  driftOnly: false,
  lowConfidenceOnly: false,
  minScore: 0,
  maxScore: 100,
};

const PAGE_SIZE = 30;

export default function EpisodeStream({ selectedId, onSelect }: Props) {
  const [episodes, setEpisodes] = useState<DecisionEpisode[]>([]);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listEpisodes(filters, 0, PAGE_SIZE);
      setEpisodes(res.episodes);
      setTotal(res.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load episodes");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="flex flex-col h-full">
      {/* header */}
      <div className="shrink-0 px-3 pt-3 pb-2">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold text-zinc-200">
            Episodes
            <span className="ml-1.5 text-zinc-500 font-normal text-xs">
              {total}
            </span>
          </h2>
          <button
            onClick={load}
            disabled={loading}
            className="text-xs text-zinc-400 hover:text-zinc-200 disabled:opacity-40"
            title="Refresh"
          >
            ↻
          </button>
        </div>
        <FiltersBar filters={filters} onChange={setFilters} />
      </div>

      {/* list */}
      <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-2">
        {loading && episodes.length === 0 && (
          <p className="text-xs text-zinc-500 py-8 text-center">Loading…</p>
        )}
        {error && (
          <p className="text-xs text-red-400 py-4 text-center">{error}</p>
        )}
        {!loading && !error && episodes.length === 0 && (
          <p className="text-xs text-zinc-500 py-8 text-center">
            No episodes found. Ingest some events first.
          </p>
        )}
        {episodes.map((ep) => (
          <EpisodeCard
            key={ep.episode_id}
            episode={ep}
            selected={ep.episode_id === selectedId}
            onClick={onSelect}
          />
        ))}
      </div>
    </div>
  );
}
