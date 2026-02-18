// ─────────────────────────────────────────────────────────────
// BucketPanel.tsx – Right lane: tabbed view of TRUTH / REASONING / MEMORY
// ─────────────────────────────────────────────────────────────
import { useState } from "react";
import type { RefinedEpisode } from "../../types/exhaust";
import BucketItem from "./BucketItem";
import AcceptRejectBar from "./AcceptRejectBar";

type Bucket = "truth" | "reasoning" | "memory";

interface BucketEntry {
  id: string;
  content: string;
  confidence: number;
  status: "pending" | "accepted" | "rejected";
  provenance?: string;
}

interface Props {
  refined: RefinedEpisode | null;
  onItemAction: (
    itemId: string,
    bucket: Bucket,
    action: "accept" | "reject" | "edit",
  ) => void;
  onAcceptAll: () => void;
  onCommit: () => void;
}

const TABS: { key: Bucket; label: string; icon: string }[] = [
  { key: "truth", label: "Truth", icon: "◉" },
  { key: "reasoning", label: "Reasoning", icon: "◇" },
  { key: "memory", label: "Memory", icon: "⬡" },
];

function toBucketEntries(
  items: Array<Record<string, unknown>> | undefined,
): BucketEntry[] {
  if (!items) return [];
  return items.map((it, i) => ({
    id: (it.id as string) ?? String(i),
    content:
      (it.claim as string) ??
      (it.decision as string) ??
      (it.entity as string) ??
      (it.content as string) ??
      JSON.stringify(it),
    confidence: (it.confidence as number) ?? 0.5,
    status: (it.status as "pending" | "accepted" | "rejected") ?? "pending",
    provenance: it.provenance as string | undefined,
  }));
}

export default function BucketPanel({
  refined,
  onItemAction,
  onAcceptAll,
  onCommit,
}: Props) {
  const [tab, setTab] = useState<Bucket>("truth");

  if (!refined) {
    return (
      <div className="flex items-center justify-center h-full text-zinc-500 text-sm">
        Select an episode and refine it to see bucket items.
      </div>
    );
  }

  const bucketData: Record<Bucket, BucketEntry[]> = {
    truth: toBucketEntries(refined.truth as unknown as Record<string, unknown>[]),
    reasoning: toBucketEntries(refined.reasoning as unknown as Record<string, unknown>[]),
    memory: toBucketEntries(refined.memory as unknown as Record<string, unknown>[]),
  };

  const items = bucketData[tab];
  const counts = {
    truth: bucketData.truth.length,
    reasoning: bucketData.reasoning.length,
    memory: bucketData.memory.length,
  };

  return (
    <div className="flex flex-col h-full">
      {/* tabs */}
      <div className="shrink-0 flex items-center border-b border-zinc-800 px-3 pt-2">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
              tab === t.key
                ? "border-indigo-500 text-indigo-300"
                : "border-transparent text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {t.icon} {t.label}
            <span className="ml-1 text-[10px] opacity-60">{counts[t.key]}</span>
          </button>
        ))}

        <div className="ml-auto flex items-center gap-2 pb-1">
          <AcceptRejectBar
            compact
            onAcceptAll={onAcceptAll}
            onAccept={() => {}}
            onReject={() => {}}
          />
          <button
            onClick={onCommit}
            className="rounded bg-indigo-700 hover:bg-indigo-600 px-3 py-1 text-xs font-medium text-white transition-colors"
            title="Commit refined episode"
          >
            Commit
          </button>
        </div>
      </div>

      {/* items */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {items.length === 0 ? (
          <p className="text-xs text-zinc-500 py-4 text-center">
            No {tab} items extracted.
          </p>
        ) : (
          items.map((item) => (
            <BucketItem
              key={item.id}
              id={item.id}
              bucket={tab}
              content={item.content}
              confidence={item.confidence}
              status={item.status}
              provenance={item.provenance}
              onAccept={(id) => onItemAction(id, tab, "accept")}
              onReject={(id) => onItemAction(id, tab, "reject")}
              onEdit={(id) => onItemAction(id, tab, "edit")}
            />
          ))
        )}
      </div>
    </div>
  );
}
