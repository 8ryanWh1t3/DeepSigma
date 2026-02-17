// ─────────────────────────────────────────────────────────────
// SourceBadge.tsx – Shows the ingestion source of an episode
// ─────────────────────────────────────────────────────────────
import React from "react";

interface Props {
  source: string; // e.g. "langchain", "azure_openai", "cli_import"
}

const COLORS: Record<string, string> = {
  langchain: "bg-violet-900/50 border-violet-500/30 text-violet-300",
  azure_openai: "bg-sky-900/50 border-sky-500/30 text-sky-300",
  openai: "bg-teal-900/50 border-teal-500/30 text-teal-300",
  cli_import: "bg-zinc-800/60 border-zinc-500/30 text-zinc-300",
};

const FALLBACK = "bg-zinc-800/60 border-zinc-500/30 text-zinc-400";

export default function SourceBadge({ source }: Props) {
  const cls = COLORS[source] ?? FALLBACK;
  const label = source.replace(/_/g, " ");
  return (
    <span
      className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${cls}`}
      title={`Source: ${source}`}
    >
      {label}
    </span>
  );
}
