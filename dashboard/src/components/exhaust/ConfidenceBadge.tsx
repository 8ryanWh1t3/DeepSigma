// ─────────────────────────────────────────────────────────────
// ConfidenceBadge.tsx – Confidence score pill with color coding
// ─────────────────────────────────────────────────────────────


interface Props {
  score: number;       // 0–1 float
  showLabel?: boolean;
}

/**
 * Renders a coloured pill showing confidence as a percentage.
 *   >= 0.85  → green  (auto-commit tier)
 *   0.65–0.84 → amber (review tier)
 *   < 0.65   → red   (hold tier)
 */
export default function ConfidenceBadge({ score, showLabel = false }: Props) {
  const pct = Math.round(score * 100);

  let bg: string;
  let text: string;
  let label: string;

  if (score >= 0.85) {
    bg = "bg-emerald-900/60 border-emerald-500/40";
    text = "text-emerald-300";
    label = "auto";
  } else if (score >= 0.65) {
    bg = "bg-amber-900/60 border-amber-500/40";
    text = "text-amber-300";
    label = "review";
  } else {
    bg = "bg-red-900/60 border-red-500/40";
    text = "text-red-300";
    label = "hold";
  }

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${bg} ${text}`}
      title={`Confidence: ${pct}% (${label})`}
    >
      {pct}%
      {showLabel && (
        <span className="opacity-70 text-[10px] uppercase">{label}</span>
      )}
    </span>
  );
}
