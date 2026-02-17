"""Exhaust Refiner — extract Truth/Reasoning/Memory from DecisionEpisodes.

This module takes assembled DecisionEpisodes and produces RefinedEpisodes
with structured buckets, confidence scoring, dedup, and drift detection.

MVP uses rule-based extraction. Optional LLM-based extraction is marked.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import models (works when run from repo root)
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard.server.models_exhaust import (
    CoherenceBreakdown,
    DecisionEpisode,
    DriftSeverity,
    DriftSignal,
    DriftType,
    Grade,
    MemoryItem,
    ReasoningItem,
    RefinedEpisode,
    TruthItem,
)


# ── Slug / Canonicalization ──────────────────────────────────────

def _slug(text: str) -> str:
    """Normalize entity name to slug form."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _stable_hash(*parts: str) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── Truth Extraction ─────────────────────────────────────────────

def extract_truth(episode: DecisionEpisode) -> List[TruthItem]:
    """Extract atomic claims from episode events.

    MVP: rule-based extraction from completion and metric events.
    OPTIONAL: Replace with LLM-based extraction using constrained prompts.
    """
    items: List[TruthItem] = []
    seen_claims: Dict[str, TruthItem] = {}

    for event in episode.events:
        payload = event.payload

        if event.event_type.value == "metric":
            # Metrics are direct truth claims
            name = payload.get("name", "")
            value = str(payload.get("value", ""))
            unit = payload.get("unit", "")
            claim = f"{name} = {value}" + (f" {unit}" if unit else "")
            slug_key = _slug(claim)

            if slug_key in seen_claims:
                seen_claims[slug_key].support_count += 1
                seen_claims[slug_key].provenance.append(event.event_id)
            else:
                item = TruthItem(
                    claim=claim,
                    evidence=f"metric from {event.source.value}",
                    confidence=0.9,
                    truth_type="empirical",
                    entity=_slug(name),
                    property_name=name,
                    value=value,
                    unit=unit,
                    provenance=[event.event_id],
                )
                seen_claims[slug_key] = item

        elif event.event_type.value == "completion":
            # Extract factual statements from completions (MVP: simple heuristic)
            text = payload.get("text", payload.get("content", ""))
            if not text:
                continue
            # Simple: lines that look like assertions
            for line in text.split("\n"):
                line = line.strip()
                if len(line) > 20 and any(w in line.lower() for w in
                    ["is ", "are ", "was ", "has ", "equals", "total", "count", "average"]):
                    slug_key = _slug(line[:80])
                    if slug_key not in seen_claims:
                        item = TruthItem(
                            claim=line[:200],
                            evidence=f"completion from {event.source.value}",
                            confidence=0.6,
                            truth_type="derived",
                            provenance=[event.event_id],
                        )
                        seen_claims[slug_key] = item

    items = list(seen_claims.values())
    return items


# ── Reasoning Extraction ─────────────────────────────────────────

def extract_reasoning(episode: DecisionEpisode) -> List[ReasoningItem]:
    """Extract decisions, assumptions, and rationale from episode events."""
    items: List[ReasoningItem] = []
    seen: Dict[str, ReasoningItem] = {}

    for event in episode.events:
        payload = event.payload

        if event.event_type.value == "completion":
            text = payload.get("text", payload.get("content", ""))
            if not text:
                continue

            # Detect reasoning patterns
            for line in text.split("\n"):
                line = line.strip()
                lower = line.lower()

                decision = ""
                if any(p in lower for p in ["i recommend", "we should", "the best", "i chose", "decision:"]):
                    decision = line[:200]
                elif any(p in lower for p in ["because ", "therefore ", "assuming ", "given that"]):
                    decision = line[:200]

                if decision:
                    slug_key = _slug(decision[:80])
                    if slug_key not in seen:
                        item = ReasoningItem(
                            decision=decision,
                            rationale="",
                            confidence=0.55,
                            provenance=[event.event_id],
                        )
                        seen[slug_key] = item

        elif event.event_type.value == "tool":
            tool_name = payload.get("tool_name", payload.get("name", "unknown"))
            tool_input = str(payload.get("input", ""))[:200]
            decision = f"Used tool: {tool_name}"
            slug_key = _slug(decision)
            if slug_key not in seen:
                item = ReasoningItem(
                    decision=decision,
                    rationale=f"Tool invocation with input: {tool_input}",
                    confidence=0.75,
                    provenance=[event.event_id],
                )
                seen[slug_key] = item

    return list(seen.values())


# ── Memory Extraction ────────────────────────────────────────────

def extract_memory(episode: DecisionEpisode) -> List[MemoryItem]:
    """Extract entities, relations, and artifacts from episode events."""
    items: List[MemoryItem] = []
    seen: Dict[str, MemoryItem] = {}

    for event in episode.events:
        payload = event.payload

        if event.event_type.value == "tool":
            tool_name = payload.get("tool_name", payload.get("name", ""))
            if tool_name:
                key = _slug(f"tool_{tool_name}")
                if key not in seen:
                    seen[key] = MemoryItem(
                        entity=tool_name,
                        relation="used_by",
                        target=episode.user_hash,
                        context=f"In episode {episode.episode_id}",
                        artifact_type="tool",
                        confidence=0.85,
                        provenance=[event.event_id],
                    )

        if event.event_type.value in ("prompt", "completion"):
            text = payload.get("text", payload.get("content", ""))
            model = payload.get("model", "")
            if model:
                key = _slug(f"model_{model}")
                if key not in seen:
                    seen[key] = MemoryItem(
                        entity=model,
                        relation="used_in",
                        target=episode.episode_id,
                        context=f"Model used for {event.event_type.value}",
                        artifact_type="model",
                        confidence=0.9,
                        provenance=[event.event_id],
                    )

    # Always record the episode itself
    seen[f"ep_{episode.episode_id}"] = MemoryItem(
        entity=episode.episode_id,
        relation="belongs_to",
        target=episode.project,
        context=f"Session {episode.session_id}",
        artifact_type="episode",
        confidence=1.0,
        provenance=[e.event_id for e in episode.events[:3]],
    )

    return list(seen.values())


# ── Drift Detection ──────────────────────────────────────────────

def detect_drift(
    episode: DecisionEpisode,
    truth: List[TruthItem],
    memory: List[MemoryItem],
    canon_path: Optional[Path] = None,
) -> List[DriftSignal]:
    """Detect drift by comparing extracted claims against local canon.

    MVP checks:
    1. Same entity+property with different value -> contradiction
    2. Missing policy flags
    3. Low claim coverage
    """
    signals: List[DriftSignal] = []

    # Load existing memory graph as canon
    canon: List[Dict[str, Any]] = []
    mg_path = canon_path or Path(os.environ.get("DATA_DIR", "/app/data")) / "mg" / "memory_graph.jsonl"
    if mg_path.exists():
        with open(mg_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        canon.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

    # Build canon lookup: entity+property -> value
    canon_map: Dict[str, str] = {}
    for c in canon:
        if c.get("node_type") == "truth":
            key = f"{_slug(c.get('entity', ''))}:{_slug(c.get('property_name', ''))}"
            if key and key != ":":
                canon_map[key] = c.get("value", "")

    # Check contradictions
    for item in truth:
        if item.entity and item.property_name:
            key = f"{_slug(item.entity)}:{_slug(item.property_name)}"
            if key in canon_map and canon_map[key] != item.value:
                signals.append(DriftSignal(
                    drift_type=DriftType.contradiction,
                    severity=DriftSeverity.yellow,
                    description=f"Contradiction: {item.property_name} was '{canon_map[key]}', now '{item.value}'",
                    entity=item.entity,
                    property_name=item.property_name,
                    expected_value=canon_map[key],
                    actual_value=item.value,
                    episode_id=episode.episode_id,
                    recommended_patch={
                        "action": "update_claim",
                        "entity": item.entity,
                        "property": item.property_name,
                        "old_value": canon_map[key],
                        "new_value": item.value,
                    },
                ))

    # Check low claim coverage
    if len(truth) == 0 and len(episode.events) > 2:
        signals.append(DriftSignal(
            drift_type=DriftType.low_claim_coverage,
            severity=DriftSeverity.yellow,
            description="No truth claims extracted from episode with multiple events",
            episode_id=episode.episode_id,
        ))

    return signals


# ── Coherence Scoring ────────────────────────────────────────────

def score_coherence(
    truth: List[TruthItem],
    reasoning: List[ReasoningItem],
    memory: List[MemoryItem],
    drift: List[DriftSignal],
    policy_pack: Optional[Dict[str, Any]] = None,
) -> Tuple[float, Grade, CoherenceBreakdown]:
    """Compute coherence score 0-100 from weighted dimensions."""

    # Claim coverage: ratio of high-confidence claims
    total_claims = len(truth)
    high_conf_claims = sum(1 for t in truth if t.confidence >= 0.7)
    claim_coverage = min(high_conf_claims / max(total_claims, 1), 1.0)

    # Evidence quality: avg confidence of truth items
    evidence_quality = (
        sum(t.confidence for t in truth) / max(len(truth), 1)
    )

    # Reasoning completeness: have decisions + rationale
    reasoning_with_rationale = sum(1 for r in reasoning if r.rationale)
    reasoning_completeness = min(
        reasoning_with_rationale / max(len(reasoning), 1), 1.0
    ) if reasoning else 0.3

    # Memory linkage: fraction of memory items with targets
    linked = sum(1 for m in memory if m.target)
    memory_linkage = min(linked / max(len(memory), 1), 1.0) if memory else 0.2

    # Policy adherence
    policy_adherence = 0.8 if policy_pack else 0.5

    # Penalty for drift
    drift_penalty = len([d for d in drift if d.severity == DriftSeverity.red]) * 0.1
    drift_penalty += len([d for d in drift if d.severity == DriftSeverity.yellow]) * 0.05

    breakdown = CoherenceBreakdown(
        claim_coverage=round(claim_coverage, 3),
        evidence_quality=round(evidence_quality, 3),
        reasoning_completeness=round(reasoning_completeness, 3),
        memory_linkage=round(memory_linkage, 3),
        policy_adherence=round(policy_adherence, 3),
    )

    # Weighted score
    score = (
        claim_coverage * 25
        + evidence_quality * 25
        + reasoning_completeness * 20
        + memory_linkage * 15
        + policy_adherence * 15
    )
    score = max(0, min(100, score - drift_penalty * 100))
    score = round(score, 1)

    if score >= 85:
        grade = Grade.A
    elif score >= 75:
        grade = Grade.B
    elif score >= 65:
        grade = Grade.C
    else:
        grade = Grade.D

    return score, grade, breakdown


# ── Main Refiner ─────────────────────────────────────────────────

def refine_episode(
    episode: DecisionEpisode,
    policy_pack: Optional[Dict[str, Any]] = None,
) -> RefinedEpisode:
    """Full refinement pipeline: extract -> dedup -> drift -> score."""

    truth = extract_truth(episode)
    reasoning = extract_reasoning(episode)
    memory = extract_memory(episode)
    drift = detect_drift(episode, truth, memory)
    score, grade, breakdown = score_coherence(
        truth, reasoning, memory, drift, policy_pack
    )

    return RefinedEpisode(
        episode_id=episode.episode_id,
        truth=truth,
        reasoning=reasoning,
        memory=memory,
        drift_signals=drift,
        coherence_score=score,
        grade=grade,
        breakdown=breakdown,
    )
