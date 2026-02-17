// ─────────────────────────────────────────────────────────────
// BucketItem.tsx – Single item inside a bucket (truth / reasoning / memory)
// ─────────────────────────────────────────────────────────────
import React from "react";
import ConfidenceBadge from "./ConfidenceBadge";
import AcceptRejectBar from "./AcceptRejectBar";

interface Props {
  id: string;
  bucket: "truth" | "reasoning" | "memory";
  content: string;
  confidence: number;
  status: "pending" | "accepted" | "rejected";
  provenance?: string;
  onAccept: (id: string) => void;
  onReject: (id: string) => void;
  onEdit?: (id: string) => void;
}

const BUCKET_ICON: Record<string, string> = {
  truth: "◉",
  reasoning: "◇",
  memory: "⬡",
};

export default function BucketItem({
  id,
  bucket,
  content: text,
  confidence,
  status,
  provenance,
  onAccept,
  onReject,
  onEdit,
}: Props) {
  const accepted = status === "accepted";
  const rejected = status === "rejected";
  const muted = accepted || rejected;

  return (
    <div
      className={`group flex items-start gap-2 rounded-md border border-zinc-700/50 p-2 text-sm transition-colors ${
        rejected
          ? "opacity-40 line-through"
          : accepted
            ? "border-emerald-800/40 bg-emerald-950/20"
            : "hover:border-zinc-600 bg-zinc-900/40"
      }`}
    >
      {/* icon */}
      <span className="mt-0.5 text-xs text-zinc-500" title={bucket}>
        {BUCKET_ICON[bucket] ?? "•"}
      </span>

      {/* body */}
      <div className="flex-1 min-w-0">
        <p className="text-zinc-200 break-words">{text}</p>
        <div className="mt-1 flex items-center gap-2 text-[10px] text-zinc-500">
          <ConfidenceBadge score={confidence} />
          {provenance && <span title="Provenance">{provenance}</span>}
          {status !== "pending" && (
            <span className="uppercase tracking-wider font-semibold">
              {status}
            </span>
          )}
        </div>
      </div>

      {/* actions (visible on hover for pending items) */}
      {!muted && (
        <div className="opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
          <AcceptRejectBar
            compact
            onAccept={() => onAccept(id)}
            onReject={() => onReject(id)}
            onEdit={onEdit ? () => onEdit(id) : undefined}
          />
        </div>
      )}
    </div>
  );
}
