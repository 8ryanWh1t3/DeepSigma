// ─────────────────────────────────────────────────────────────
// AcceptRejectBar.tsx – Action bar for accept / reject / edit / escalate
// ─────────────────────────────────────────────────────────────
import React from "react";

interface Props {
  onAccept: () => void;
  onReject: () => void;
  onEdit?: () => void;
  onEscalate?: () => void;
  onAcceptAll?: () => void;
  disabled?: boolean;
  compact?: boolean;
}

const btn =
  "rounded px-3 py-1 text-xs font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed";

export default function AcceptRejectBar({
  onAccept,
  onReject,
  onEdit,
  onEscalate,
  onAcceptAll,
  disabled = false,
  compact = false,
}: Props) {
  return (
    <div className={`flex items-center ${compact ? "gap-1" : "gap-2"}`}>
      {onAcceptAll && (
        <button
          className={`${btn} bg-emerald-700 hover:bg-emerald-600 text-white`}
          onClick={onAcceptAll}
          disabled={disabled}
          title="Accept all items"
        >
          Accept All
        </button>
      )}

      <button
        className={`${btn} bg-emerald-800/80 hover:bg-emerald-700 text-emerald-200`}
        onClick={onAccept}
        disabled={disabled}
        title="Accept"
      >
        {compact ? "✓" : "Accept"}
      </button>

      <button
        className={`${btn} bg-red-800/80 hover:bg-red-700 text-red-200`}
        onClick={onReject}
        disabled={disabled}
        title="Reject"
      >
        {compact ? "✗" : "Reject"}
      </button>

      {onEdit && (
        <button
          className={`${btn} bg-zinc-700 hover:bg-zinc-600 text-zinc-200`}
          onClick={onEdit}
          disabled={disabled}
          title="Edit"
        >
          {compact ? "✎" : "Edit"}
        </button>
      )}

      {onEscalate && (
        <button
          className={`${btn} bg-amber-800/80 hover:bg-amber-700 text-amber-200`}
          onClick={onEscalate}
          disabled={disabled}
          title="Escalate for human review"
        >
          {compact ? "⚑" : "Escalate"}
        </button>
      )}
    </div>
  );
}
