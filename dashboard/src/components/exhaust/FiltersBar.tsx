// ─────────────────────────────────────────────────────────────
// FiltersBar.tsx – Filter controls for the episode stream
// ─────────────────────────────────────────────────────────────

import type { FilterState } from "../../types/exhaust";

interface Props {
  filters: FilterState;
  onChange: (next: FilterState) => void;
}

const input =
  "rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-200 placeholder-zinc-500 focus:border-zinc-500 focus:outline-none";
const toggle =
  "rounded border px-2 py-1 text-xs font-medium transition-colors cursor-pointer select-none";

export default function FiltersBar({ filters, onChange }: Props) {
  const set = <K extends keyof FilterState>(key: K, val: FilterState[K]) =>
    onChange({ ...filters, [key]: val });

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900/60 p-2">
      {/* text filters */}
      <input
        className={input}
        placeholder="Project"
        value={filters.project}
        onChange={(e) => set("project", e.target.value)}
      />
      <input
        className={input}
        placeholder="Team"
        value={filters.team}
        onChange={(e) => set("team", e.target.value)}
      />
      <input
        className={input}
        placeholder="Source"
        value={filters.source}
        onChange={(e) => set("source", e.target.value)}
      />

      {/* coherence range */}
      <div className="flex items-center gap-1 text-xs text-zinc-400">
        <span>Score</span>
        <input
          type="number"
          min={0}
          max={100}
          className={`${input} w-14 text-center`}
          placeholder="0"
          value={filters.minScore || ""}
          onChange={(e) => set("minScore", Number(e.target.value) || 0)}
        />
        <span>–</span>
        <input
          type="number"
          min={0}
          max={100}
          className={`${input} w-14 text-center`}
          placeholder="100"
          value={filters.maxScore || ""}
          onChange={(e) => set("maxScore", Number(e.target.value) || 100)}
        />
      </div>

      {/* toggles */}
      <button
        className={`${toggle} ${
          filters.driftOnly
            ? "border-amber-600 bg-amber-900/60 text-amber-300"
            : "border-zinc-700 text-zinc-400 hover:text-zinc-200"
        }`}
        onClick={() => set("driftOnly", !filters.driftOnly)}
      >
        Drift only
      </button>

      <button
        className={`${toggle} ${
          filters.lowConfidenceOnly
            ? "border-red-600 bg-red-900/60 text-red-300"
            : "border-zinc-700 text-zinc-400 hover:text-zinc-200"
        }`}
        onClick={() => set("lowConfidenceOnly", !filters.lowConfidenceOnly)}
      >
        Low confidence
      </button>
    </div>
  );
}
