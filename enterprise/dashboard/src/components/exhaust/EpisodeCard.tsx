// ─────────────────────────────────────────────────────────────
// EpisodeCard.tsx – Compact card for the left-lane episode stream
// ─────────────────────────────────────────────────────────────

import type { DecisionEpisode, DriftSignal } from "../../types/exhaust";
import ConfidenceBadge from "./ConfidenceBadge";
import DriftBadge from "./DriftBadge";
import SourceBadge from "./SourceBadge";

interface Props {
  episode: DecisionEpisode;
  selected: boolean;
  onClick: (id: string) => void;
}

function gradeFor(score: number): string {
  if (score >= 85) return "A";
  if (score >= 75) return "B";
  if (score >= 65) return "C";
  return "D";
}

function gradeColor(g: string): string {
  switch (g) {
    case "A": return "text-emerald-400";
    case "B": return "text-sky-400";
    case "C": return "text-amber-400";
    default:  return "text-red-400";
  }
}

function shortId(id: string): string {
  return id.length > 8 ? id.slice(0, 8) : id;
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return mins + "m ago";
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return hrs + "h ago";
  return Math.floor(hrs / 24) + "d ago";
}

export default function EpisodeCard({ episode, selected, onClick }: Props) {
  const e = episode;
  const score = e.coherence_score ?? 0;
  const grade = gradeFor(score);
  const driftCount = e.drift_signals?.length ?? 0;
  const maxDrift =
    driftCount > 0
      ? e.drift_signals!.reduce(
                                  (worst: "green" | "yellow" | "red", d: DriftSignal) =>
            d.severity === "red"
              ? "red"
              : d.severity === "yellow" && worst !== "red"
                ? "yellow"
                : worst,
          "green" as "green" | "yellow" | "red",
        )
      : "green";

  return (
    <button
      type="button"
      onClick={() => onClick(e.episode_id)}
      className={`w-full text-left rounded-lg border p-3 transition-colors ${
        selected
          ? "border-indigo-500/60 bg-indigo-950/30"
          : "border-zinc-800 bg-zinc-900/50 hover:border-zinc-600"
      }`}
    >
      {/* top row: id + time */}
      <div className="flex items-center justify-between text-[10px] text-zinc-500 mb-1">
        <span className="font-mono">{shortId(e.episode_id)}</span>
        <span>{relativeTime(e.started_at)}</span>
      </div>

      {/* project / team */}
      <div className="text-sm font-medium text-zinc-200 truncate">
        {e.project ?? "—"}
        {e.team && <span className="text-zinc-500 font-normal"> / {e.team}</span>}
      </div>

      {/* badges row */}
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        {/* grade */}
        <span
          className={`inline-flex items-center justify-center w-5 h-5 rounded text-xs font-bold ${gradeColor(grade)} bg-zinc-800`}
          title={`Coherence: ${score}`}
        >
          {grade}
        </span>

        <ConfidenceBadge score={score / 100} />

        {driftCount > 0 && (
          <DriftBadge severity={maxDrift} count={driftCount} />
        )}

        <SourceBadge source={e.source ?? "unknown"} />
      </div>

      {/* event count */}
      <div className="mt-1.5 text-[10px] text-zinc-500">
        {e.events?.length ?? 0} events
        {e.refined_at && " · refined"}
        {e.committed && " · committed"}
      </div>
    </button>
  );
}
