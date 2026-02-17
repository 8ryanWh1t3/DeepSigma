// ─────────────────────────────────────────────────────────────
// ExhaustInbox.tsx – Main page: three-lane layout for Exhaust Inbox
// ─────────────────────────────────────────────────────────────
import React, { useState, useCallback } from "react";
import type { RefinedEpisode } from "../types/exhaust";
import { commitEpisode, itemAction } from "../lib/api";
import EpisodeStream from "../components/exhaust/EpisodeStream";
import EpisodeDetail from "../components/exhaust/EpisodeDetail";
import BucketPanel from "../components/exhaust/BucketPanel";

type Bucket = "truth" | "reasoning" | "memory";

export default function ExhaustInbox() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [refined, setRefined] = useState<RefinedEpisode | null>(null);

  // ── callbacks ────────────────────────────────────────────

  const handleSelect = useCallback((id: string) => {
    setSelectedId(id);
    setRefined(null); // clear bucket panel until re-refined
  }, []);

  const handleRefined = useCallback((r: RefinedEpisode) => {
    setRefined(r);
  }, []);

  const handleItemAction = useCallback(
    async (
      itemId: string,
      bucket: Bucket,
      action: "accept" | "reject" | "edit",
    ) => {
      if (!selectedId) return;
      try {
        await itemAction(selectedId, {
          item_id: itemId,
          bucket,
          action,
        });
        // optimistic update
        if (refined) {
          const updateBucket = (items: unknown[]) =>
            items.map((it: Record<string, unknown>) =>
              (it.id as string) === itemId
                ? { ...it, status: action === "edit" ? "pending" : action + "ed" }
                : it,
            );
          setRefined({
            ...refined,
            truth:
              bucket === "truth"
                ? (updateBucket(refined.truth as unknown[]) as typeof refined.truth)
                : refined.truth,
            reasoning:
              bucket === "reasoning"
                ? (updateBucket(refined.reasoning as unknown[]) as typeof refined.reasoning)
                : refined.reasoning,
            memory:
              bucket === "memory"
                ? (updateBucket(refined.memory as unknown[]) as typeof refined.memory)
                : refined.memory,
          });
        }
      } catch (err) {
        console.error("Item action failed:", err);
      }
    },
    [selectedId, refined],
  );

  const handleAcceptAll = useCallback(async () => {
    if (!selectedId || !refined) return;
    // Accept every pending item across all buckets
    const pending = (items: unknown[]) =>
      (items as Array<Record<string, unknown>>).filter(
        (it) => (it.status as string) !== "accepted",
      );
    for (const bucket of ["truth", "reasoning", "memory"] as Bucket[]) {
      const items = pending(
        (refined[bucket] as unknown[]) ?? [],
      );
      for (const it of items) {
        try {
          await itemAction(selectedId, {
            item_id: it.id as string,
            bucket,
            action: "accept",
          });
        } catch {
          // continue with next
        }
      }
    }
    // reload – crude but effective for MVP
    if (refined) {
      const markAll = (items: unknown[]) =>
        (items as Array<Record<string, unknown>>).map((it) => ({
          ...it,
          status: "accepted",
        }));
      setRefined({
        ...refined,
        truth: markAll(refined.truth as unknown[]) as typeof refined.truth,
        reasoning: markAll(refined.reasoning as unknown[]) as typeof refined.reasoning,
        memory: markAll(refined.memory as unknown[]) as typeof refined.memory,
      });
    }
  }, [selectedId, refined]);

  const handleCommit = useCallback(async () => {
    if (!selectedId) return;
    try {
      await commitEpisode(selectedId);
    } catch (err) {
      console.error("Commit failed:", err);
    }
  }, [selectedId]);

  // ── render ───────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full">
      {/* page header */}
      <header className="shrink-0 flex items-center justify-between border-b border-zinc-800 px-4 py-2">
        <h1 className="text-base font-semibold text-zinc-100">
          Exhaust Inbox
        </h1>
        <span className="text-[10px] text-zinc-500 uppercase tracking-widest">
          DeepSigma RAL
        </span>
      </header>

      {/* three-lane grid */}
      <div className="flex-1 grid grid-cols-[280px_1fr_340px] min-h-0">
        {/* left: episode stream */}
        <div className="border-r border-zinc-800 overflow-hidden">
          <EpisodeStream selectedId={selectedId} onSelect={handleSelect} />
        </div>

        {/* center: episode detail timeline */}
        <div className="border-r border-zinc-800 overflow-hidden">
          <EpisodeDetail episodeId={selectedId} onRefined={handleRefined} />
        </div>

        {/* right: bucket panel */}
        <div className="overflow-hidden">
          <BucketPanel
            refined={refined}
            onItemAction={handleItemAction}
            onAcceptAll={handleAcceptAll}
            onCommit={handleCommit}
          />
        </div>
      </div>
    </div>
  );
}
