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


# ── Entity Type Inference ────────────────────────────────────────

_ENTITY_TYPE_MAP = {
    "cpu": "infrastructure", "memory": "infrastructure", "disk": "infrastructure",
    "network": "infrastructure", "node": "infrastructure", "pod": "infrastructure",
    "latency": "performance", "p95": "performance", "p99": "performance",
    "throughput": "performance", "qps": "performance", "rps": "performance",
    "error": "reliability", "failure": "reliability", "timeout": "reliability",
    "uptime": "reliability", "availability": "reliability",
    "user": "business", "revenue": "business", "conversion": "business",
    "order": "business", "customer": "business",
    "token": "cost", "cost": "cost", "usage": "cost", "spend": "cost",
}


def _infer_entity_type(name: str) -> str:
    """Infer entity type from metric/entity name using keyword matching."""
    lower = name.lower()
    for keyword, etype in _ENTITY_TYPE_MAP.items():
        if keyword in lower:
            return etype
    return ""


# ── Confidence Calibration ───────────────────────────────────────

_BOOST_WORDS = {"observed", "measured", "confirmed", "verified", "actual", "recorded"}
_HEDGE_WORDS = {"possibly", "might", "uncertain", "maybe", "approximately", "estimated", "roughly"}


def _calibrate_confidence(base: float, text: str) -> float:
    """Adjust confidence based on certainty/hedging language in text."""
    lower = text.lower()
    boost = any(w in lower for w in _BOOST_WORDS)
    hedge = any(w in lower for w in _HEDGE_WORDS)
    if boost and not hedge:
        return min(base + 0.1, 1.0)
    if hedge and not boost:
        return max(base - 0.1, 0.1)
    return base


# ── Assumption / Alternative Patterns ────────────────────────────

_ASSUMPTION_PATTERNS = ["assuming ", "given that ", "if we assume", "under the assumption"]
_ALTERNATIVE_PATTERNS = ["alternatively", "or we could", "another option", "we could also", "instead of"]


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
                    entity_type=_infer_entity_type(name),
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
                        conf = _calibrate_confidence(0.6, line)
                        item = TruthItem(
                            claim=line[:200],
                            evidence=f"completion from {event.source.value}",
                            confidence=conf,
                            truth_type="derived",
                            provenance=[event.event_id],
                        )
                        seen_claims[slug_key] = item

    items = list(seen_claims.values())
    return items


# ── Reasoning Extraction ─────────────────────────────────────────

def extract_reasoning(episode: DecisionEpisode) -> List[ReasoningItem]:
    """Extract decisions, assumptions, alternatives, and rationale from episode events."""
    seen: Dict[str, ReasoningItem] = {}
    # Collect assumptions and alternatives from all text for attachment
    all_assumptions: List[str] = []
    all_alternatives: List[str] = []
    # Track last completion text for tool rationale enrichment
    last_completion_text = ""

    for event in episode.events:
        payload = event.payload

        if event.event_type.value == "completion":
            text = payload.get("text", payload.get("content", ""))
            if not text:
                continue
            last_completion_text = text

            # Detect reasoning patterns
            for line in text.split("\n"):
                line = line.strip()
                lower = line.lower()

                # Extract assumptions
                if any(p in lower for p in _ASSUMPTION_PATTERNS) and len(line) > 15:
                    all_assumptions.append(line[:200])

                # Extract alternatives
                if any(p in lower for p in _ALTERNATIVE_PATTERNS) and len(line) > 15:
                    all_alternatives.append(line[:200])

                decision = ""
                if any(p in lower for p in ["i recommend", "we should", "the best", "i chose", "decision:"]):
                    decision = line[:200]
                elif any(p in lower for p in ["because ", "therefore ", "assuming ", "given that"]):
                    decision = line[:200]

                if decision:
                    slug_key = _slug(decision[:80])
                    if slug_key not in seen:
                        conf = _calibrate_confidence(0.55, line)
                        item = ReasoningItem(
                            decision=decision,
                            rationale="",
                            confidence=conf,
                            provenance=[event.event_id],
                        )
                        seen[slug_key] = item

        elif event.event_type.value == "tool":
            tool_name = payload.get("tool_name", payload.get("name", "unknown"))
            tool_input = str(payload.get("input", ""))[:200]
            decision = f"Used tool: {tool_name}"
            slug_key = _slug(decision)
            if slug_key not in seen:
                # Enrich rationale from preceding completion context
                rationale = f"Tool invocation with input: {tool_input}"
                if last_completion_text:
                    # Extract the last line of the preceding completion as context
                    context_lines = [ln.strip() for ln in last_completion_text.split("\n") if ln.strip()]
                    if context_lines:
                        rationale = f"{context_lines[-1][:150]} → {rationale}"
                item = ReasoningItem(
                    decision=decision,
                    rationale=rationale,
                    confidence=0.75,
                    provenance=[event.event_id],
                )
                seen[slug_key] = item

    # Attach assumptions and alternatives to reasoning items
    items = list(seen.values())
    for item in items:
        if all_assumptions and not item.assumptions:
            item.assumptions = all_assumptions[:]
        if all_alternatives and not item.alternatives:
            item.alternatives = all_alternatives[:]

    return items


# ── Memory Extraction ────────────────────────────────────────────

def extract_memory(episode: DecisionEpisode) -> List[MemoryItem]:
    """Extract entities, relations, and artifacts from episode events."""
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
            _text = payload.get("text", payload.get("content", ""))
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

    Checks:
    1. Same entity+property with different value -> contradiction
    2. Low claim coverage (no truth from multi-event episode)
    3. Stale reference (memory item references an episode not in canon)
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

    # Build known episode IDs from canon
    known_episode_ids: set = {
        c.get("entity", "")
        for c in canon
        if c.get("artifact_type") == "episode" or c.get("node_type") == "memory"
        and c.get("artifact_type") == "episode"
    }

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

    # Check stale references: memory items whose context references an unknown episode
    if known_episode_ids:
        for item in memory:
            if item.artifact_type == "episode":
                continue  # episode nodes are self-referential
            context = item.context or ""
            if context.startswith("In episode "):
                ref_ep_id = context.removeprefix("In episode ").strip()
                if ref_ep_id and ref_ep_id not in known_episode_ids:
                    signals.append(DriftSignal(
                        drift_type=DriftType.stale_reference,
                        severity=DriftSeverity.yellow,
                        description=(
                            f"Memory item '{item.entity}' references episode "
                            f"'{ref_ep_id}' not found in memory graph"
                        ),
                        entity=item.entity,
                        episode_id=episode.episode_id,
                        recommended_patch={
                            "action": "verify_episode_reference",
                            "referenced_episode": ref_ep_id,
                        },
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

    # Evidence quality: avg confidence of truth items (0.0 when no truth)
    evidence_quality = (
        sum(t.confidence for t in truth) / len(truth) if truth else 0.0
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
    use_llm: bool = False,
) -> RefinedEpisode:
    """Full refinement pipeline: extract -> dedup -> drift -> score.

    Args:
        episode:     Assembled DecisionEpisode to refine.
        policy_pack: Optional policy constraints for scoring.
        use_llm:     When True and ANTHROPIC_API_KEY is set, use the
                     LLM-based extractor in place of rule-based extraction.
                     Falls back to rule-based on any failure.
    """
    if use_llm and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            from engine.exhaust_llm_extractor import LLMExtractor
            buckets = LLMExtractor().extract(episode)
            truth = buckets.get("truth") or []
            reasoning = buckets.get("reasoning") or []
            # Always merge in the episode memory node from rule-based
            llm_memory = buckets.get("memory") or []
            rule_memory = extract_memory(episode)
            # Deduplicate: rule_memory episode node + LLM entities
            ep_nodes = [m for m in rule_memory if m.artifact_type == "episode"]
            memory = ep_nodes + [m for m in llm_memory if m.artifact_type != "episode"]
        except Exception:  # noqa: BLE001
            use_llm = False  # fall through to rule-based

    if not use_llm:
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
