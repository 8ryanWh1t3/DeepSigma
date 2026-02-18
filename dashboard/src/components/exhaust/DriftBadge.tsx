// ─────────────────────────────────────────────────────────────
// DriftBadge.tsx – Drift severity indicator (Green / Yellow / Red)
// ─────────────────────────────────────────────────────────────


type Severity = "green" | "yellow" | "red";

interface Props {
  severity: Severity;
  count?: number;
}

const STYLE: Record<Severity, { bg: string; text: string; icon: string }> = {
  green: {
    bg: "bg-emerald-900/50 border-emerald-600/30",
    text: "text-emerald-400",
    icon: "●",
  },
  yellow: {
    bg: "bg-amber-900/50 border-amber-600/30",
    text: "text-amber-400",
    icon: "▲",
  },
  red: {
    bg: "bg-red-900/50 border-red-600/30",
    text: "text-red-400",
    icon: "◆",
  },
};

/**
 * Shows drift severity with an icon and optional count.
 * Green = no drift, Yellow = minor, Red = critical.
 */
export default function DriftBadge({ severity, count }: Props) {
  const s = STYLE[severity];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-xs font-medium ${s.bg} ${s.text}`}
      title={`Drift: ${severity}${count !== undefined ? ` (${count})` : ""}`}
    >
      <span className="text-[10px]">{s.icon}</span>
      {severity.charAt(0).toUpperCase()}
      {count !== undefined && count > 0 && (
        <span className="ml-0.5 opacity-70">×{count}</span>
      )}
    </span>
  );
}
